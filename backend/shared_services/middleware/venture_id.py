"""
VentureIDMiddleware — Zero Trust tenant enforcement.

Every non-exempt request passes through three sequential checks before
being allowed to proceed.  A failure at any gate returns immediately
without touching the downstream handler or database.

┌─────────────────────────────────────────────────────────────────────┐
│  Gate 1 — Presence check                                           │
│  Both X-Venture-ID and X-API-Key headers must be present.          │
│  Missing either → 400 Bad Request                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Gate 2 — Signature check  (HMAC-SHA256)                            │
│  The API key is "{slug}.{base64url_sig}" where sig covers            │
│  "{slug}:{venture_id}".  An Arisole key presented with a Neufin     │
│  venture_id fails here because the HMAC will not match.             │
│  Invalid or tampered key → 401 Unauthorized                         │
├─────────────────────────────────────────────────────────────────────┤
│  Gate 3 — Path scope check  (cross-venture 403)                     │
│  Spoke-specific endpoints live at /api/v1/spokes/{slug}/…           │
│  If the slug embedded in the API key differs from the slug in the   │
│  path, the key does not have authority over that spoke's data.      │
│  Wrong-venture key on scoped endpoint → 403 Forbidden               │
└─────────────────────────────────────────────────────────────────────┘

After all gates pass, the venture_id is stored in a ContextVar so that
get_db() can activate PostgreSQL Row-Level Security for the transaction.

Exempt paths (no checks at all)
--------------------------------
  /docs   /redoc   /openapi.json   /api/v1/health
  /api/v1/spokes/*/billing/webhook  (Stripe sends no auth headers)

Path-scope convention for spoke endpoints
------------------------------------------
Register spoke routes under /api/v1/spokes/{venture_slug}/…
e.g.  /api/v1/spokes/arisole/telemetry
      /api/v1/spokes/neufin/trades

Hub-level endpoints (e.g. /api/v1/chat) have no slug in the path;
Gate 3 is skipped and any valid key may call them.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.api_keys import KNOWN_SLUGS, verify_admin_key, verify_api_key
from core.context import current_venture_id

_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/health",
    "/api/v1/concierge",   # public landing-page chatbot — no venture key required
)

# Stripe webhook paths are exempt because Stripe cannot send X-Venture-ID or
# X-API-Key.  Security is provided by Stripe's own webhook signature instead.
_EXEMPT_SUFFIXES: tuple[str, ...] = (
    "/billing/webhook",
    "/webhooks/supabase-signup",   # Supabase sends no X-Venture-ID
)


def _path_venture_slug(path: str) -> str | None:
    """
    Return the venture slug if the URL path targets a spoke-scoped endpoint,
    otherwise return None (hub-level — any validated venture may access).

    Convention: /api/v1/spokes/{slug}/…
    """
    parts = path.strip("/").split("/")
    try:
        idx = parts.index("spokes")
        candidate = parts[idx + 1] if idx + 1 < len(parts) else None
        if candidate in KNOWN_SLUGS:
            return candidate
    except ValueError:
        pass
    return None


class VentureIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # ── Exempt paths ─────────────────────────────────────────────────
        if any(path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)
        if any(path.endswith(s) for s in _EXEMPT_SUFFIXES):
            return await call_next(request)

        # ── Global Admin bypass ───────────────────────────────────────────
        # A key prefixed with "hub.admin_" grants cross-venture read access
        # without requiring X-Venture-ID.  The HMAC is still verified so a
        # fabricated "hub.admin_something" cannot gain access.
        api_key_early = request.headers.get("X-API-Key", "")
        if api_key_early.startswith("hub.admin_"):
            if not verify_admin_key(api_key_early):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid admin key"},
                )
            return await call_next(request)

        # ── Gate 1: presence ─────────────────────────────────────────────
        venture_id = request.headers.get("X-Venture-ID")
        api_key = request.headers.get("X-API-Key")

        if not venture_id or not api_key:
            missing = []
            if not venture_id:
                missing.append("X-Venture-ID")
            if not api_key:
                missing.append("X-API-Key")
            return JSONResponse(
                status_code=400,
                content={"detail": f"Missing required header(s): {', '.join(missing)}"},
            )

        # ── Gate 2: HMAC signature ────────────────────────────────────────
        # verify_api_key returns the slug embedded in the key, or None.
        # A Neufin key paired with an Arisole venture_id will fail here
        # because HMAC("{neufin}:{arisole_uuid}") ≠ the Neufin key's sig.
        key_slug = verify_api_key(api_key, venture_id)

        if key_slug is None:
            return JSONResponse(
                status_code=401,
                content={"detail": "API key is invalid or does not match X-Venture-ID"},
            )

        # ── Gate 3: path-scope (cross-venture 403) ────────────────────────
        # If the requested path is scoped to a specific spoke, the key's
        # venture must match that spoke's slug.
        path_slug = _path_venture_slug(path)

        if path_slug is not None and path_slug != key_slug:
            return JSONResponse(
                status_code=403,
                content={
                    "detail": (
                        f"Access denied: '{key_slug}' API key cannot access "
                        f"'{path_slug}' endpoints"
                    )
                },
            )

        # ── All gates passed — activate RLS context ───────────────────────
        token = current_venture_id.set(venture_id)
        try:
            response = await call_next(request)
        finally:
            current_venture_id.reset(token)

        return response
