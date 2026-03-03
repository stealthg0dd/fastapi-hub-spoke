from typing import TypedDict


class ChatState(TypedDict):
    """
    Immutable-by-convention state passed between every node in the chat graph.

    Each node returns a dict with only the keys it mutates; LangGraph merges
    that dict into the running state automatically.
    """

    venture_id: str       # from X-Venture-ID header; set by the endpoint
    prompt: str           # raw user prompt; set by the endpoint

    # ── Router node output ──────────────────────────────────────────────────
    persona: str          # system persona fetched from hub.organizations

    # ── Agent node output ───────────────────────────────────────────────────
    raw_response: str     # LLM reply before any security processing

    # ── Security node output ────────────────────────────────────────────────
    safe_response: str        # PII-scrubbed final reply
    pii_detected: list[str]   # types of PII that were redacted (may be empty)
