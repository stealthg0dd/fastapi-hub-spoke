"""
Security node — validates and sanitises the LLM output.

Responsibilities
----------------
- Runs the raw LLM response through the PII scrubber (graph/pii.py).
- Logs every detected PII category for audit purposes (venture_id is
  included so logs can be correlated per tenant).
- Stores the cleaned text in state["safe_response"] and the list of
  detected PII categories in state["pii_detected"].

No PII is logged — only the category names (e.g. "EMAIL", "PHONE").

Config keys expected (via RunnableConfig["configurable"])
---------------------------------------------------------
None.
"""

import logging

from langchain_core.runnables import RunnableConfig

from graph.pii import scrub
from graph.state import ChatState

logger = logging.getLogger(__name__)


async def security_node(state: ChatState, config: RunnableConfig) -> dict:  # noqa: ARG001
    safe_text, detected = scrub(state["raw_response"])

    if detected:
        logger.warning(
            "security_node: PII redacted for venture=%s types=%s",
            state["venture_id"],
            detected,
        )
    else:
        logger.debug(
            "security_node: no PII detected for venture=%s",
            state["venture_id"],
        )

    return {
        "safe_response": safe_text,
        "pii_detected": detected,
    }
