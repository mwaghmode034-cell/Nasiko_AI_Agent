import sys
import os
import uuid
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, AIMessage

# Ensure local imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import Agent

app = FastAPI()
hr_agent = Agent()

# In-memory conversation history per thread (thread_id -> list of messages)
CONVERSATION_STORE = {}
MAX_HISTORY_MESSAGES = 20  # Keep last 10 turns

@app.post("/")
async def handle_request(request: Request):
    try:
        data = await request.json()
        
        # Validate JSON-RPC A2A format 
        if data.get("jsonrpc") != "2.0" or data.get("method") != "message/send":
            return JSONResponse(status_code=400, content={"error": "Invalid request format."})
        
        # Extract user message from the A2A payload
        req_id = data.get("id", str(uuid.uuid4()))
        params = data.get("params", {})
        message = params.get("message", {})
        parts = message.get("parts", [])

        user_text = ""
        for part in parts:
            if part.get("kind") == "text":
                user_text += part.get("text", "")

        # Get thread_id for conversation memory (client should send same id for a chat)
        thread_id = params.get("thread_id") or params.get("conversation_id") or data.get("thread_id")
        chat_history = []
        if thread_id:
            history_list = CONVERSATION_STORE.get(thread_id, [])
            # Convert to LangChain message format
            chat_history = [
                HumanMessage(content=h["content"]) if h["role"] == "user"
                else AIMessage(content=h["content"])
                for h in history_list[-MAX_HISTORY_MESSAGES:]
            ]

        # Process the message with our Agent (includes chat history for context)
        agent_response = hr_agent.process_message(user_text, chat_history=chat_history)

        # Store in conversation history for next turn
        if thread_id:
            if thread_id not in CONVERSATION_STORE:
                CONVERSATION_STORE[thread_id] = []
            CONVERSATION_STORE[thread_id].append({"role": "user", "content": user_text})
            CONVERSATION_STORE[thread_id].append({"role": "assistant", "content": agent_response})
        
        # Build A2A compliant response 
        response = {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "id": str(uuid.uuid4()),
                "kind": "task",
                "status": {
                    "state": "completed",
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "artifacts": [
                    {
                        "id": str(uuid.uuid4()),
                        "kind": "text",
                        "parts": [
                            {
                                "kind": "text",
                                "text": agent_response
                            }
                        ]
                    }
                ]
            }
        }
        return JSONResponse(content=response)
        
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

if __name__ == "__main__":
    import click
    
    @click.command()
    @click.option("--host", default="0.0.0.0", help="Host to bind to")
    @click.option("--port", default=5000, help="Port to bind to")
    def run(host, port):
        uvicorn.run(app, host=host, port=port)
        
    run()