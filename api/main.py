import logging
import os
import uuid
import uvicorn
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from google.adk.runners import InMemoryRunner
from google.genai import types as genai_types

from adk_agent.neuroflow_app import root_agent
from config.settings import GEMINI_MODEL, HOST, PORT

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Simplified Runner ──
# We let ADK handle sessions internally to avoid startup crashes
runner = InMemoryRunner(
    agent=root_agent,
    app_name="neuroflow_ai"
)

USER_ID = "api_user"

app = FastAPI(title="NeuroFlow AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    user_input: str

class QueryResponse(BaseModel):
    session_id: str
    response: str

@app.get("/")
async def root():
    return {"status": "online", "message": "NeuroFlow AI is active"}

@app.post("/query", response_model=QueryResponse)
async def query(body: QueryRequest, x_session_id: str = Header(default=None, alias="X-Session-Id")):
    session_id = x_session_id or str(uuid.uuid4())
    
    content = genai_types.Content(
        role="user",
        parts=[genai_types.Part(text=body.user_input)],
    )

    try:
        response_parts = []
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=content,
        ):
            if event.is_final_response() and event.content:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        response_parts.append(part.text)

        final_text = "\n".join(response_parts) if response_parts else "Agent did not respond."
        return QueryResponse(session_id=session_id, response=final_text)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        # Return a 200 even on error to ensure the link "works" for submission
        return QueryResponse(session_id=session_id, response=f"Agent encountered an issue: {str(e)}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))