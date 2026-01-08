"""
Unified ADK Agent Server
Combines WebSocket agent execution and ADK Web UI into a single FastAPI server.

Features:
- ADK Web UI mounted at /adk
- WebSocket endpoints for org_research and market_research agents
- Health check and session monitoring endpoints
- Comprehensive logging
- Stagnation detection for long-running tasks
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uuid
import logging
import time
import sys
import os
from datetime import datetime

from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from google.adk.cli.fast_api import get_fast_api_app

import uvicorn
from dotenv import load_dotenv

load_dotenv()

# ==============================================================================
# Logging Configuration
# ==============================================================================
def setup_logging():
    """Setup comprehensive logging to file and console"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    logs_dir = os.path.join(script_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d")
    log_filename = os.path.join(logs_dir, f"unified_server_{timestamp}.log")
    
    log_format = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        datefmt=date_format,
        handlers=[
            logging.FileHandler(log_filename),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Capture uvicorn and ADK logs
    for logger_name in ["uvicorn", "uvicorn.access", "google.adk"]:
        sub_logger = logging.getLogger(logger_name)
        sub_logger.setLevel(logging.INFO)
    
    print(f"Logging initialized. Output saved to: {log_filename}")
    return log_filename

log_file = setup_logging()
logger = logging.getLogger(__name__)

# ==============================================================================
# ADK FastAPI Application Setup (Use ADK app as main app for unified Swagger docs)
# ==============================================================================
try:
    logger.info("Creating ADK FastAPI application...")
    app = get_fast_api_app(agents_dir=".", web=True)
    logger.info("ADK FastAPI application created successfully")
except Exception as e:
    logger.error("Failed to create ADK app: %s, creating fallback app", str(e))
    app = FastAPI(
        title="Unified ADK Agent Server",
        description="Combined WebSocket agent execution and ADK Web UI",
        version="1.0.0"
    )

# Add CORS middleware to the ADK app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Session Management
# ==============================================================================
session_service = InMemorySessionService()

# Active sessions and running tasks for each agent type
sessions = {}  # {session_id: {"ws": WebSocket, "user_id": str, "agent_type": str, "created_at": float}}
running_tasks = {}
stagnation_tasks = {}

# Stagnation detection configuration
STAGNATION_TIMEOUT = 300  # 5 minutes in seconds

# ==============================================================================
# Agent Imports (Lazy Loading)
# ==============================================================================
def get_agent_and_config(agent_type: str):
    """Dynamically import and return agent and config based on type"""
    if agent_type == "org_research":
        from org_research.agent import root_agent
        from org_research.config import config
        return root_agent, config, "org_research"
    elif agent_type == "market_research":
        from market_research.agent import root_agent
        from market_research.config import config
        return root_agent, config, "market_research"
    else:
        raise ValueError(f"Unknown agent type: {agent_type}")

# ==============================================================================
# WebSocket Helper Functions
# ==============================================================================
async def send_safe(ws: WebSocket, data: dict):
    """Safely send data through WebSocket, handling connection errors"""
    try:
        await ws.send_json(data)
        return True
    except Exception as e:
        logger.warning("Failed to send data through WebSocket: %s", e)
        return False

async def monitor_stagnation(session_id: str, last_event_time: dict):
    """Monitor for stagnation and send alert if detected"""
    while session_id in running_tasks:
        await asyncio.sleep(10)
        
        current_time = time.time()
        time_since_last_event = current_time - last_event_time["time"]
        
        if time_since_last_event > STAGNATION_TIMEOUT:
            session_data = sessions.get(session_id)
            ws = session_data.get("ws") if session_data else None
            
            if ws:
                stagnation_message = {
                    "type": "stagnation",
                    "message": f"No activity detected for {int(time_since_last_event)} seconds. The agent may be experiencing delays or processing complex tasks.",
                    "seconds_stagnant": int(time_since_last_event)
                }
                
                success = await send_safe(ws, stagnation_message)
                if success:
                    logger.warning("Stagnation detected for session %s: %d seconds", session_id, int(time_since_last_event))
            
            last_event_time["time"] = current_time
            await asyncio.sleep(60)

async def run_agent_task(session_id: str, user_id: str, query_text: str, agent_type: str):
    """Run the agent task independently of WebSocket connection"""
    content = types.Content(role="user", parts=[types.Part(text=query_text)])
    
    # Initialize last event time tracker
    last_event_time = {"time": time.time()}
    
    # Start stagnation monitoring task
    stagnation_task = asyncio.create_task(monitor_stagnation(session_id, last_event_time))
    stagnation_tasks[session_id] = stagnation_task
    
    try:
        # Get the appropriate agent and config
        root_agent, config, app_name = get_agent_and_config(agent_type)
        
        runner = Runner(agent=root_agent, app_name=app_name, session_service=session_service)
        
        # Determine run_config based on agent type
        run_config = getattr(config, 'run_config', None)
        
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=run_config
        ):
            # Update last event time
            last_event_time["time"] = time.time()
            
            # Check if session still exists and has WebSocket connection
            session_data = sessions.get(session_id)
            ws = session_data.get("ws") if session_data else None
            
            # Process function calls
            function_calls = event.get_function_calls() or []
            for fc in function_calls:
                if isinstance(fc, dict):
                    name = fc.get("name") or fc.get("function")
                    args = fc.get("args") or fc.get("arguments")
                else:
                    name = getattr(fc, "name", None) or getattr(fc, "function", None)
                    args = getattr(fc, "args", None) or getattr(fc, "arguments", None)
                
                logger.info("Function call: %s", name)
                logger.info("Function event: %s", event)
                logger.info("-" * 100)
                message = {
                    "type": "function_call",
                    "name": name,
                    "args": args
                }
                if ws:
                    success = await send_safe(ws, message)
                    if not success:
                        if session_id in sessions:
                            sessions[session_id]["ws"] = None
            
            content_obj = getattr(event, "content", None)
            parts = getattr(content_obj, "parts", None) if content_obj is not None else None
            
            if parts:
                for part in parts:
                    text_val = getattr(part, "text", None)
                    if text_val is not None:
                        continue
                    
            if getattr(event, "is_final_response", lambda: False)():
                if parts and getattr(parts[0], "text", None):
                    final_text = parts[0].text
                    logger.info("Final response: %s", event)
                    logger.info("-" * 100)
                    
                    if ws:
                        await send_safe(ws, {
                            "type": "text",
                            "is_final": True,
                            "content": final_text
                        })
                else:
                    logger.info("Final event: %s", str(event))
                    logger.info("-" * 100)
                    
        # Agent generator is exhausted - all steps completed
        logger.info("Agent task fully completed for session %s", session_id)
        session_data = sessions.get(session_id)
        ws = session_data.get("ws") if session_data else None
        
        if ws:
            await send_safe(ws, {
                "type": "agent_completed",
                "message": "Agent has completed all steps"
            })
            
            try:
                await ws.close(code=1000, reason="Agent task completed")
                logger.info("WebSocket closed for completed session %s", session_id)
            except Exception as e:
                logger.warning("Error closing WebSocket for session %s: %s", session_id, e)
                    
    except Exception as e:
        logger.error("Error in agent task: %s", str(e))
        session_data = sessions.get(session_id)
        ws = session_data.get("ws") if session_data else None
        if ws:
            await send_safe(ws, {"type": "error", "message": str(e)})
    finally:
        # Clean up stagnation monitoring
        if session_id in stagnation_tasks:
            stagnation_tasks[session_id].cancel()
            del stagnation_tasks[session_id]
            
        if session_id in running_tasks:
            del running_tasks[session_id]
            
        # Clean up session data
        if session_id in sessions:
            del sessions[session_id]
            
        logger.info("Agent task and session cleanup completed for session %s", session_id)

# ==============================================================================
# Generic WebSocket Handler
# ==============================================================================
async def handle_agent_websocket(websocket: WebSocket, agent_type: str, app_name: str):
    """Generic handler for agent WebSocket connections"""
    await websocket.accept()
    
    # Generate session and user IDs
    user_id = f"user_{uuid.uuid4().hex}"
    session_id = str(uuid.uuid4())
    
    # Create ADK session
    session = await session_service.create_session(
        app_name=app_name, user_id=user_id, session_id=session_id
    )
    logger.info("Created %s session: %s", agent_type, session)
    
    # Store session data
    sessions[session_id] = {
        "ws": websocket,
        "user_id": user_id,
        "agent_type": agent_type,
        "created_at": asyncio.get_event_loop().time()
    }
    
    # Send session ID to client
    await websocket.send_json({
        "type": "session_created", 
        "session_id": session_id,
        "agent_type": agent_type
    })
    
    try:
        # Wait for the single query from the client
        data = await websocket.receive_json()
        
        if "query" not in data:
            await websocket.send_json({
                "type": "error", 
                "message": "Missing 'query' field in message"
            })
            return
        
        query_text = data["query"]
        
        # Start the agent task
        task = asyncio.create_task(run_agent_task(session_id, user_id, query_text, agent_type))
        running_tasks[session_id] = task
        
        await websocket.send_json({
            "type": "task_started",
            "message": f"{agent_type} agent task started"
        })
        
        # Wait for the agent task to complete
        await task
            
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
        if session_id in sessions:
            sessions[session_id]["ws"] = None
        logger.info("Session %s will continue running in background", session_id)
    except Exception as e:
        logger.error("WebSocket error for session %s: %s", session_id, str(e))
    finally:
        if session_id in sessions:
            sessions[session_id]["ws"] = None

# ==============================================================================
# WebSocket Endpoints
# ==============================================================================
@app.websocket("/ws/org-research")
async def run_org_research_ws(websocket: WebSocket):
    """WebSocket endpoint for org_research agent"""
    await handle_agent_websocket(websocket, "org_research", "org_research")

@app.websocket("/ws/market-research")
async def run_market_research_ws(websocket: WebSocket):
    """WebSocket endpoint for market_research agent"""
    await handle_agent_websocket(websocket, "market_research", "market_research")

# Legacy endpoint for backward compatibility
@app.websocket("/run-live-agent")
async def run_live_agent_ws(websocket: WebSocket):
    """Legacy WebSocket endpoint (defaults to org_research for backward compatibility)"""
    await handle_agent_websocket(websocket, "org_research", "org_research")

# ==============================================================================
# REST Endpoints
# ==============================================================================
@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "server": "Unified ADK Agent Server",
        "version": "1.0.0",
        "endpoints": {
            "adk_apis": "/run, /dev-ui, etc. (ADK at root)",
            "org_research_ws": "/ws/org-research",
            "market_research_ws": "/ws/market-research",
            "legacy_ws": "/run-live-agent",
            "health": "/health",
            "sessions": "/sessions"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "adk_app_active": True,
        "active_sessions": len(sessions),
        "running_tasks": len(running_tasks),
        "stagnation_monitors": len(stagnation_tasks)
    }

@app.get("/sessions")
async def get_sessions():
    """Debug endpoint to see active sessions and tasks"""
    session_info = {}
    for sid, data in sessions.items():
        session_info[sid] = {
            "user_id": data["user_id"],
            "agent_type": data.get("agent_type", "unknown"),
            "has_websocket": data["ws"] is not None,
            "has_running_task": sid in running_tasks,
            "has_stagnation_monitor": sid in stagnation_tasks,
            "created_at": data.get("created_at", "unknown")
        }
    return {
        "sessions": session_info,
        "total_sessions": len(sessions),
        "total_running_tasks": len(running_tasks),
        "total_stagnation_monitors": len(stagnation_tasks),
        "stagnation_timeout_seconds": STAGNATION_TIMEOUT
    }

# ==============================================================================
# Main Entry Point
# ==============================================================================
if __name__ == "__main__":
    logger.info("=== Unified ADK Agent Server Starting ===")
    logger.info("Script location: %s", os.path.abspath(__file__))
    logger.info("Working directory: %s", os.getcwd())
    logger.info("Log file: %s", log_file)
    logger.info("Server configuration:")
    logger.info("  Host: 0.0.0.0")
    logger.info("  Port: 8500")
    logger.info("Endpoints:")
    logger.info("  ADK APIs: http://localhost:8500/run, /dev-ui, etc.")
    logger.info("  Org Research WS: ws://localhost:8500/ws/org-research")
    logger.info("  Market Research WS: ws://localhost:8500/ws/market-research")
    logger.info("  Health Check: http://localhost:8500/health")
    
    uvicorn.run(
        "server:app",
        host="0.0.0.0",  # nosec B104
        port=8500,
        log_level="info",
        access_log=True
    )
