from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio, uuid
import logging
import time

from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
from org_research.agent import root_agent
from org_research.config import config
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

session_service = InMemorySessionService()
APP_NAME = "org_research"

# Active sessions and running tasks
sessions = {}
running_tasks = {}
stagnation_tasks = {}  # Track stagnation monitoring tasks

# Stagnation detection configuration
STAGNATION_TIMEOUT = 300  # 5 minutes in seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def send_safe(ws: WebSocket, data: dict):
    """Safely send data through WebSocket, handling connection errors"""
    try:
        await ws.send_json(data)
        return True
    except Exception as e:
        logger.warning(f"Failed to send data through WebSocket: {e}")
        return False

async def monitor_stagnation(session_id: str, last_event_time: dict):
    """Monitor for stagnation and send alert if detected"""
    while session_id in running_tasks:
        await asyncio.sleep(10)  # Check every 10 seconds
        
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
                    logger.warning(f"Stagnation detected for session {session_id}: {int(time_since_last_event)} seconds")
                
            # Reset the timer to avoid spam
            last_event_time["time"] = current_time
            
            # Wait longer before checking again after sending stagnation alert
            await asyncio.sleep(60)

async def run_agent_task(session_id: str, user_id: str, query_text: str):
    """Run the agent task independently of WebSocket connection"""
    content = types.Content(role="user", parts=[types.Part(text=query_text)])
    
    # Initialize last event time tracker
    last_event_time = {"time": time.time()}
    
    # Start stagnation monitoring task
    stagnation_task = asyncio.create_task(monitor_stagnation(session_id, last_event_time))
    stagnation_tasks[session_id] = stagnation_task
    
    try:
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=config.run_config
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
                
                logger.info(f"Function call: {name}")
                logger.info(f"Function event: {event}")
                logger.info("-" * 100)
                message = {
                        "type": "function_call",
                        "name": name,
                        "args": args
                    }
                # Try to send to WebSocket if connection exists
                if ws:
                    success = await send_safe(ws, message)
                    if not success:
                        # WebSocket connection failed, remove it but continue processing
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
                    logger.info(f"Final response: {event}")
                    logger.info("-" * 100)
                    
                    # Try to send final response to WebSocket if connection exists
                    if ws:
                        await send_safe(ws, {
                            "type": "text",
                            "is_final": True,
                            "content": final_text
                        })
                else:
                    logger.info(f"Final event: {str(event)}")
                    logger.info("-" * 100)
                    
        # Agent generator is exhausted - all steps completed
        logger.info(f"Agent task fully completed for session {session_id}")
        session_data = sessions.get(session_id)
        ws = session_data.get("ws") if session_data else None
        
        if ws:
            # Send completion notification
            await send_safe(ws, {
                "type": "agent_completed",
                "message": "Agent has completed all steps"
            })
            
            # Close the WebSocket connection
            try:
                await ws.close(code=1000, reason="Agent task completed")
                logger.info(f"WebSocket closed for completed session {session_id}")
            except Exception as e:
                logger.warning(f"Error closing WebSocket for session {session_id}: {e}")
                    
    except Exception as e:
        logger.error(f"Error in agent task: {str(e)}")
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
            
        logger.info(f"Agent task and session cleanup completed for session {session_id}")

@app.websocket("/run-live-agent")
async def run_live_agent_ws(websocket: WebSocket):
    await websocket.accept()
    
    # Generate session and user IDs
    user_id = f"user_{uuid.uuid4().hex}"
    session_id = str(uuid.uuid4())
    
    # Create ADK session
    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    logger.info(f"Created session: {session}")
    
    # Store session data
    sessions[session_id] = {
        "ws": websocket,
        "user_id": user_id,
        "created_at": asyncio.get_event_loop().time()
    }
    
    # Send session ID to client
    await websocket.send_json({"type": "session_created", "session_id": session_id})
    
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
        
        # Start the agent task (only one per session)
        task = asyncio.create_task(run_agent_task(session_id, user_id, query_text))
        running_tasks[session_id] = task
        
        await websocket.send_json({
            "type": "task_started",
            "message": "Agent task started"
        })
        
        # Wait for the agent task to complete
        await task
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        if session_id in sessions:
            sessions[session_id]["ws"] = None
        logger.info(f"Session {session_id} will continue running in background")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {str(e)}")
    finally:
        if session_id in sessions:
            sessions[session_id]["ws"] = None

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy", 
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

# if __name__ == "__main__":
#     uvicorn.run("agent_exec_stateless:app", host="0.0.0.0", port=8052, ssl_keyfile="/opt/sales_agent/SSLCerts/key.pem", ssl_certfile="/opt/sales_agent/SSLCerts/cert.pem", log_level="info")

if __name__ == "__main__":
    uvicorn.run("agent_exec_stateless:app", host="0.0.0.0", port=8052, log_level="info")