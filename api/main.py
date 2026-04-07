"""
api/main.py
-----------
FastAPI application — the HTTP entry point for NeuroFlow AI.

Endpoints:
  POST /query          — send a message, get an agent response
  GET  /health         — liveness probe for Cloud Run
  GET  /tasks          — convenience REST: list all tasks
  GET  /notes          — convenience REST: list recent notes

The ADK agent is driven via InMemoryRunner which manages session state.
Each HTTP request uses an isolated session identified by a session_id
(from header or auto-generated), enabling multi-turn conversations.
"""

import logging
import os
import uuid
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from adk_agent.neuroflow_app import root_agent
from config.settings import GEMINI_MODEL, HOST, PORT
from database.db import get_notes, get_tasks

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── ADK runner (module-level singleton) ───────────────────────────────────────
session_service = InMemorySessionService()
runner = InMemoryRunner(
    agent=root_agent,
    app_name="neuroflow_ai",
    session_service=session_service,
)

APP_NAME = "neuroflow_ai"
USER_ID = "api_user"           # single-user for now; extend with auth later


# ── Lifespan ──────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("NeuroFlow AI API starting up …")
    yield
    logger.info("NeuroFlow AI API shutting down.")


# ── FastAPI app ───────────────────────────────────────────────────────────────
app = FastAPI(
    title="NeuroFlow AI",
    description="Multi-agent productivity assistant powered by Google ADK & Gemini.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────
class QueryRequest(BaseModel):
    user_input: str = Field(..., min_length=1, max_length=4096,
                            description="The user's natural-language message.")


class QueryResponse(BaseModel):
    session_id: str
    response: str


# ── Helper: run one ADK turn ──────────────────────────────────────────────────
async def _run_agent_turn(session_id: str, user_input: str) -> str:
    """
    Execute a single conversational turn with the ADK runner.
    Creates the session on first use; reuses existing session for multi-turn.
    """
    # Ensure the session exists
    existing = await session_service.get_session(
        app_name=APP_NAME, user_id=USER_ID, session_id=session_id
    )
    if existing is None:
        await session_service.create_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=session_id
        )

    # Build the user message
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=user_input)],
    )

    # Collect all text parts from the agent's response events
    response_parts: list[str] = []

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        # ADK emits various event types; we want final text responses
        if event.is_final_response() and event.content:
            for part in event.content.parts:
                if hasattr(part, "text") and part.text:
                    response_parts.append(part.text)

    return "\n".join(response_parts) if response_parts else "I couldn't generate a response."


# ════════════════════════════════════════════════════════════════════════════════
# ENDPOINTS
# ════════════════════════════════════════════════════════════════════════════════

@app.get("/health", tags=["System"])
async def health_check():
    """Liveness probe — Cloud Run checks this."""
    return {"status": "ok", "service": "NeuroFlow AI", "model": GEMINI_MODEL}


@app.post("/query", response_model=QueryResponse, tags=["Agent"])
async def query(
    body: QueryRequest,
    x_session_id: str = Header(default=None, alias="X-Session-Id"),
):
    """
    Send a natural-language message to NeuroFlow AI.

    Supply `X-Session-Id` header to continue an existing conversation.
    A new session id is created automatically if the header is absent.

    Example:
        curl -X POST http://localhost:8080/query \\
             -H "Content-Type: application/json" \\
             -d '{"user_input": "Add a task: finish the report by Friday"}'
    """
    session_id = x_session_id or str(uuid.uuid4())
    logger.info("Query | session=%s | input=%r", session_id, body.user_input[:80])

    try:
        response_text = await _run_agent_turn(session_id, body.user_input)
    except Exception as exc:
        logger.exception("Agent runner error: %s", exc)
        raise HTTPException(status_code=500, detail=f"Agent error: {exc}") from exc

    return QueryResponse(session_id=session_id, response=response_text)


@app.get("/tasks", tags=["Data"])
async def list_tasks(status: str | None = None):
    """
    Convenience endpoint — directly query AlloyDB for tasks.
    Useful for dashboards or debugging without going through the agent.
    """
    try:
        tasks = get_tasks(status=status)
        return {"tasks": tasks, "count": len(tasks)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/notes", tags=["Data"])
async def list_notes(limit: int = 10):
    """
    Convenience endpoint — directly query AlloyDB for recent notes.
    """
    try:
        notes = get_notes(limit=limit)
        return {"notes": notes, "count": len(notes)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ── Entrypoint (local dev & Cloud Run) ───────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=HOST,
        port=PORT,
        reload=os.environ.get("RELOAD", "false").lower() == "true",
        log_level="info",
    )
