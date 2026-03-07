import sys
import os
import re
import uuid
import uvicorn
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from langchain_core.messages import HumanMessage, AIMessage

# Ensure local imports work correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import Agent
from tools import get_known_person_names

app = FastAPI()
hr_agent = Agent()

# In-memory conversation history per thread (thread_id -> list of messages)
CONVERSATION_STORE = {}
MAX_HISTORY_MESSAGES = 20  # Keep last 10 turns

# Pronoun patterns (whole words) that need context resolution
PRONOUN_PATTERN = re.compile(r"\b(him|her|his|their|he|she)\b", re.IGNORECASE)


def _resolve_pronoun_context(user_text: str, history_list: list) -> str:
    """If user message has pronouns and history exists, prepend context with the last discussed person."""
    if not history_list or not PRONOUN_PATTERN.search(user_text):
        return user_text
    known = get_known_person_names()
    last_name = None
    for msg in reversed(history_list):
        text = msg.get("content", "")
        for name in known:
            if re.search(rf"\b{re.escape(name)}\b", text, re.IGNORECASE):
                last_name = name
                break
        if last_name:
            break
    if last_name:
        return f"Referring to {last_name}: {user_text}"
    return user_text

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
        # Support client-sent history (e.g. params.messages or params.history)
        client_history = params.get("messages") or params.get("history") or []
        history_list = list(client_history) if client_history else (CONVERSATION_STORE.get(thread_id, []) if thread_id else [])
        chat_history = [
            HumanMessage(content=h["content"]) if h["role"] == "user"
            else AIMessage(content=h["content"])
            for h in history_list[-MAX_HISTORY_MESSAGES:]
        ]

        # Resolve pronouns (him, her, his, etc.) using conversation context
        user_text_resolved = _resolve_pronoun_context(user_text, history_list)

        # Process the message with our Agent (includes chat history for context)
        agent_response = hr_agent.process_message(user_text_resolved, chat_history=chat_history)

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