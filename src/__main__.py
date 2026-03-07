import sys
import os
import re
import uuid
import logging
import uvicorn
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agent import Agent
from tools import get_known_person_names

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("HR Agent starting up…")
    yield
    logger.info("HR Agent shutting down.")

app = FastAPI(
    title="Nasiko HR Automation Agent",
    version="1.1.0",
    description="AI-powered HR agent for recruitment, onboarding, leave management, and policy queries.",
    lifespan=lifespan,
)

# Allow cross-origin requests (useful for front-end clients / testing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

hr_agent = Agent()

# In-memory conversation store: thread_id → list of message dicts
CONVERSATION_STORE: dict[str, list] = {}
MAX_HISTORY_MESSAGES = 20  # Keep last 10 turns (20 messages)

# Pronoun patterns that need context resolution
PRONOUN_PATTERN = re.compile(r"\b(him|her|his|their|he|she)\b", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resolve_pronoun_context(user_text: str, history_list: list) -> str:
    """Prepend 'Referring to [Name]:' context when pronouns are detected and a name can be inferred."""
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
        logger.debug("Resolved pronoun context → %s", last_name)
        return f"Referring to {last_name}: {user_text}"
    return user_text


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Simple liveness probe."""
    return {"status": "ok", "service": "Nasiko HR Agent", "timestamp": _now_iso()}


@app.get("/")
async def root():
    return {"message": "Nasiko HR Automation Agent is running. POST to / with JSON-RPC A2A format."}


@app.post("/")
async def handle_request(request: Request):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body.")

    # Validate JSON-RPC A2A format
    if data.get("jsonrpc") != "2.0" or data.get("method") != "message/send":
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid request. Expected jsonrpc='2.0' and method='message/send'."},
        )

    req_id = data.get("id", str(uuid.uuid4()))
    params = data.get("params", {})
    message = params.get("message", {})
    parts = message.get("parts", [])

    # Extract user text from message parts
    user_text = "".join(
        part.get("text", "") for part in parts if part.get("kind") == "text"
    ).strip()

    if not user_text:
        return JSONResponse(
            status_code=400,
            content={"error": "Empty message. Provide at least one text part."},
        )

    # Determine thread/conversation
    thread_id = (
        params.get("thread_id")
        or params.get("conversation_id")
        or data.get("thread_id")
    )

    # Build history from client-sent or server-stored history
    client_history = params.get("messages") or params.get("history") or []
    history_list: list = (
        list(client_history)
        if client_history
        else (CONVERSATION_STORE.get(thread_id, []) if thread_id else [])
    )

    # Truncate to max window
    trimmed_history = history_list[-MAX_HISTORY_MESSAGES:]
    chat_history = [
        HumanMessage(content=h["content"]) if h["role"] == "user" else AIMessage(content=h["content"])
        for h in trimmed_history
        if h.get("role") in ("user", "assistant") and h.get("content")
    ]

    # Resolve pronouns
    user_text_resolved = _resolve_pronoun_context(user_text, trimmed_history)
    logger.info("Request [%s] thread=%s | msg=%s", req_id, thread_id, user_text[:80])

    # Run agent
    agent_response = hr_agent.process_message(user_text_resolved, chat_history=chat_history)

    # Persist to conversation store
    if thread_id:
        if thread_id not in CONVERSATION_STORE:
            CONVERSATION_STORE[thread_id] = []
        CONVERSATION_STORE[thread_id].append({"role": "user", "content": user_text})
        CONVERSATION_STORE[thread_id].append({"role": "assistant", "content": agent_response})
        # Trim stored history to avoid unbounded growth
        CONVERSATION_STORE[thread_id] = CONVERSATION_STORE[thread_id][-MAX_HISTORY_MESSAGES * 2:]

    logger.info("Response [%s] length=%d", req_id, len(agent_response))

    # Build A2A-compliant response
    response = {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "id": str(uuid.uuid4()),
            "kind": "task",
            "status": {
                "state": "completed",
                "timestamp": _now_iso(),
            },
            "artifacts": [
                {
                    "id": str(uuid.uuid4()),
                    "kind": "text",
                    "parts": [{"kind": "text", "text": agent_response}],
                }
            ],
        },
    }
    return JSONResponse(content=response)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import click

    @click.command()
    @click.option("--host", default="0.0.0.0", show_default=True, help="Host to bind to.")
    @click.option("--port", default=5000, show_default=True, help="Port to bind to.")
    @click.option("--reload", is_flag=True, default=False, help="Enable auto-reload (dev mode).")
    def run(host: str, port: int, reload: bool):
        uvicorn.run(
            "app:app" if reload else app,
            host=host,
            port=port,
            reload=reload,
            log_level="info",
        )

    run()