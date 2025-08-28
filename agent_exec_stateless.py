from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio, uuid
import logging

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

async def run_agent_task(session_id: str, user_id: str, query_text: str):
    """Run the agent task independently of WebSocket connection"""
    content = types.Content(role="user", parts=[types.Part(text=query_text)])
    
    try:
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=config.run_config
        ):
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
                    
    except Exception as e:
        logger.error(f"Error in agent task: {str(e)}")
        session_data = sessions.get(session_id)
        ws = session_data.get("ws") if session_data else None
        if ws:
            await send_safe(ws, {"type": "error", "message": str(e)})
    finally:
        if session_id in running_tasks:
            del running_tasks[session_id]
        logger.info(f"Agent task completed for session {session_id}")

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
        while True:
            data = await websocket.receive_json()
            
            if "query" not in data:
                await websocket.send_json({
                    "type": "error", 
                    "message": "Missing 'query' field in message"
                })
                continue
            
            query_text = data["query"]
            
            if session_id in running_tasks:
                await websocket.send_json({
                    "type": "error",
                    "message": "A task is already running for this session"
                })
                continue
            
            # Start the agent task
            task = asyncio.create_task(run_agent_task(session_id, user_id, query_text))
            running_tasks[session_id] = task
            
            await websocket.send_json({
                "type": "task_started",
                "message": "Agent task started"
            })
            
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
    return {"status": "healthy", "active_sessions": len(sessions), "running_tasks": len(running_tasks)}

@app.get("/sessions")
async def get_sessions():
    """Debug endpoint to see active sessions and tasks"""
    session_info = {}
    for sid, data in sessions.items():
        session_info[sid] = {
            "user_id": data["user_id"],
            "has_websocket": data["ws"] is not None,
            "has_running_task": sid in running_tasks,
            "created_at": data.get("created_at", "unknown")
        }
    return {
        "sessions": session_info,
        "total_sessions": len(sessions),
        "total_running_tasks": len(running_tasks)
    }

if __name__ == "__main__":
    uvicorn.run("agent_exec_stateless:app", host="0.0.0.0", port=8052, ssl_keyfile="/opt/sales_agent/SSLCerts/key.pem", ssl_certfile="/opt/sales_agent/SSLCerts/cert.pem", log_level="info")