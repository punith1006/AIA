from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import asyncio, uuid

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

# Use an in-memory session service for ADK (no persistence)
session_service = InMemorySessionService()
APP_NAME = "org_research"

# active session context (its primtive for now!)
sessions = {}

# Expected payload for schema for run live agent endpoint (again, its primitive!)
class RunRequest(BaseModel):
    session_id: str
    query: str

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    user_id = f"user_{uuid.uuid4().hex}"
    session_id = str(uuid.uuid4())

    session = await session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )
    print(session)
    # Store the WebSocket connection in the sessions context
    sessions[session_id] = {"ws": ws, "user_id": user_id}
    await ws.send_json({"session_id": session_id})

    try:
        # Keep the connection open indefinitely (or until client disconnects)
        while True:
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        sessions.pop(session_id, None)

@app.post("/run-live-agent")
async def run_live_agent(req: RunRequest):

    session_id = req.session_id
    query_text = req.query

    # Verify that we have an active WebSocket for this session
    if session_id not in sessions:
        raise HTTPException(status_code=400, detail="Invalid or expired session_id")
    ws = sessions[session_id]["ws"]
    user_id = sessions[session_id]["user_id"]

    content = types.Content(role="user", parts=[types.Part(text=query_text)])
    try:
        runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=session_service)
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
            run_config=config.run_config
        ):
            # check for event occurrence
            content = getattr(event, "content", None)
            parts = getattr(content, "parts", None) if content is not None else None
            function_calls = event.get_function_calls() or []
            
            for fc in function_calls:
                if isinstance(fc, dict):
                    name = fc.get("name") or fc.get("function")
                    args = fc.get("args") or fc.get("arguments")
                else:
                    name = getattr(fc, "name", None) or getattr(fc, "function", None)
                    args = getattr(fc, "args", None) or getattr(fc, "arguments", None)
                
                print(f"functionCall:{name}")
                print(f"function event: {event}")
                print("-"*100)
                
                await ws.send_json({
                    "type": "function_call",
                    "name": name,
                    "args": args
                })
            
            #synthensize event action
            if parts:
                for part in parts:
                    text_val = getattr(part, "text", None)
                    if text_val is not None:
                        # print(text_val)
                        continue
                        
            if getattr(event, "is_final_response", lambda: False)():
                if parts and getattr(parts[0], "text", None):
                    final_text = parts[0].text
                    print(event)
                    print("-"*100)
                    
                    await ws.send_json({
                    "type": "text",
                    "is_final": True,
                    "content": final_text
                })
                    
                else:
                    print(str(event))
                    print("-"*100)
                    
    except Exception as e:
        await ws.send_json({"type": "error", "message": str(e)})
    finally:
        # Clean up
        await ws.close()
        sessions.pop(session_id, None)

    return JSONResponse(content={"status": "completed"})

if __name__ == "__main__":
    
    uvicorn.run("agent_exec:app",host="0.0.0.0", port=8001, log_level="info")
