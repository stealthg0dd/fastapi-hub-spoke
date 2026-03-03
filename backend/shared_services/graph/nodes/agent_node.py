"""
Agent node — calls the Anthropic Claude LLM.

Responsibilities
----------------
- Reads the venture-specific system persona set by the Router node.
- Sends the user prompt to claude-sonnet-4-6 using the async Anthropic client.
- Stores the raw (pre-security) response text in state["raw_response"].

The node intentionally does NOT scrub PII — that is the exclusive
responsibility of the downstream Security node.

Config keys expected (via RunnableConfig["configurable"])
---------------------------------------------------------
None — all configuration is read from core.config.settings at import time.
"""

import logging

import anthropic
from langchain_core.runnables import RunnableConfig

from core.config import settings
from graph.state import ChatState

logger = logging.getLogger(__name__)

_MODEL = "claude-sonnet-4-6"
_MAX_TOKENS = 1024


async def agent_node(state: ChatState, config: RunnableConfig) -> dict:  # noqa: ARG001
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    logger.info("agent_node: invoking %s for venture=%s", _MODEL, state["venture_id"])

    message = await client.messages.create(
        model=_MODEL,
        max_tokens=_MAX_TOKENS,
        system=state["persona"],
        messages=[{"role": "user", "content": state["prompt"]}],
    )

    raw_text: str = message.content[0].text  # type: ignore[index]
    logger.debug("agent_node: received %d chars from LLM", len(raw_text))

    return {"raw_response": raw_text}
