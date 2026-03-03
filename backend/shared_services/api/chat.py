"""
POST /chat — single-turn Hub chat endpoint.

Flow
----
1. VentureIDMiddleware has already validated X-Venture-ID and set the
   current_venture_id ContextVar before this handler is called.
2. get_db() opens an async transaction and executes
   SET LOCAL app.current_venture_id = '<id>', activating RLS for every
   subsequent query on that session.
3. The session and venture_id are forwarded to the LangGraph pipeline via
   RunnableConfig(configurable={...}).
4. The graph runs: Router → Agent → Security.
5. The sanitised response and any detected PII categories are returned.

The endpoint deliberately does NOT accept the session or venture_id as
path/query parameters — both flow through the middleware + dependency
injection chain to maintain a single source of truth.
"""

import logging

from fastapi import APIRouter, Depends, Header, HTTPException
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from graph.chat_graph import compiled_graph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4096, description="User message")


class ChatResponse(BaseModel):
    venture_id: str = Field(..., description="Venture that processed this request")
    response: str = Field(..., description="PII-scrubbed LLM reply")
    pii_detected: list[str] = Field(
        default_factory=list,
        description="PII categories redacted from the raw response (empty = none found)",
    )


@router.post("", response_model=ChatResponse, summary="Venture-scoped chat")
async def chat(
    body: ChatRequest,
    # The middleware guarantees this header is present; FastAPI reads it for
    # OpenAPI documentation and type-safe access.
    x_venture_id: str = Header(..., alias="X-Venture-ID"),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Submit a prompt to the Hub's LangGraph pipeline.

    The active venture (identified by **X-Venture-ID**) determines:
    - which System Persona the Router node loads from the database, and
    - which rows are visible to the Agent node via PostgreSQL RLS.

    The Security node scrubs PII from the raw LLM output before the
    response is returned.
    """
    initial_state = {
        "venture_id": x_venture_id,
        "prompt": body.prompt,
        "persona": "",
        "raw_response": "",
        "safe_response": "",
        "pii_detected": [],
    }

    config = RunnableConfig(configurable={"db": db})

    try:
        result = await compiled_graph.ainvoke(initial_state, config=config)
    except Exception as exc:
        logger.exception(
            "chat: graph invocation failed for venture=%s error=%s",
            x_venture_id,
            exc,
        )
        raise HTTPException(status_code=502, detail="LLM pipeline error") from exc

    return ChatResponse(
        venture_id=x_venture_id,
        response=result["safe_response"],
        pii_detected=result["pii_detected"],
    )
