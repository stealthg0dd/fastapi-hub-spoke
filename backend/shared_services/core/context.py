"""
Request-scoped context variables.

These ContextVars are set by middleware at the edge of each request and
read by database dependencies to configure per-request PostgreSQL session
parameters (e.g. for Row-Level Security).
"""

from contextvars import ContextVar

# Holds the raw X-Venture-ID header value for the current request.
# None when no header was provided (e.g. health-check routes).
current_venture_id: ContextVar[str | None] = ContextVar(
    "current_venture_id", default=None
)
