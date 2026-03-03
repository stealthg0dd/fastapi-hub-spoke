"""
Signed API key utilities — Zero Trust layer.

Key format
----------
    {venture_slug}.{base64url_signature}

The signature is HMAC-SHA256 over the payload ``"{venture_slug}:{venture_id}"``
using ``settings.secret_key`` as the signing secret.  This binds each API key
to exactly one (slug, venture_id) pair, so a Neufin key cannot be presented
alongside an Arisole venture_id — the HMAC won't match.

Slug → venture_id mapping
--------------------------
In production these live in the database (hub.organizations).  For the
middleware — which runs before any DB call — we resolve via the
``VENTURE_SLUGS`` env vars:

    NEUFIN_VENTURE_ID=<uuid>
    ARISOLE_VENTURE_ID=<uuid>
    NEUMAS_VENTURE_ID=<uuid>
    APEX_VENTURE_ID=<uuid>

Set these in .env or docker-compose.  If unset, the middleware will still
verify the HMAC but cannot enforce the slug→UUID mapping at the header level
(the RLS layer remains the final safety net).

Usage
-----
    from core.api_keys import make_api_key, verify_api_key

    # One-time key generation (run from a management script):
    key = make_api_key("neufin", "<neufin-venture-uuid>", settings.secret_key)

    # Middleware verification:
    slug = verify_api_key(raw_key, venture_id_from_header, settings.secret_key)
    if slug is None:
        # tampered or wrong venture — reject 401
"""

import base64
import hashlib
import hmac

from core.config import settings

# Known venture slugs.  Extend when a new spoke is added.
KNOWN_SLUGS: frozenset[str] = frozenset({"neufin", "arisole", "neumas", "apex"})

# Admin key constants
_ADMIN_PREFIX: str = "hub.admin_"
_ADMIN_PAYLOAD: str = "hub:admin"   # payload signed for all admin keys


def _sign(venture_slug: str, venture_id: str, secret: str) -> str:
    """Return the URL-safe base64 HMAC-SHA256 signature (no padding)."""
    payload = f"{venture_slug}:{venture_id}".encode()
    raw = hmac.new(secret.encode(), payload, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def make_api_key(venture_slug: str, venture_id: str, secret: str | None = None) -> str:
    """
    Generate a signed API key for a venture.

    Parameters
    ----------
    venture_slug:
        One of the known slugs (``"neufin"``, ``"arisole"``, etc.).
    venture_id:
        The UUID string of the organization row in ``hub.organizations``.
    secret:
        Signing secret — defaults to ``settings.secret_key``.

    Returns
    -------
    str
        A key in the format ``"{slug}.{base64url_sig}"``.
    """
    if venture_slug not in KNOWN_SLUGS:
        raise ValueError(f"Unknown venture slug: {venture_slug!r}")
    secret = secret or settings.secret_key
    return f"{venture_slug}.{_sign(venture_slug, venture_id, secret)}"


def make_admin_key(secret: str | None = None) -> str:
    """
    Generate a Global Admin API key.

    The key is ``hub.admin_{base64url_sig}`` where the signature covers
    the constant payload ``"hub:admin"``.  All admin keys are identical for
    the same secret — rotate the secret to invalidate all existing admin keys.

    Returns
    -------
    str
        A key in the format ``"hub.admin_{base64url_sig}"``.
    """
    secret = secret or settings.secret_key
    raw = hmac.new(secret.encode(), _ADMIN_PAYLOAD.encode(), hashlib.sha256).digest()
    sig = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    return f"{_ADMIN_PREFIX}{sig}"


def verify_admin_key(api_key: str, secret: str | None = None) -> bool:
    """
    Verify a Global Admin API key.

    Returns True only if the key has the correct ``hub.admin_`` prefix and
    the HMAC signature matches the current secret.
    """
    if not api_key.startswith(_ADMIN_PREFIX):
        return False
    secret = secret or settings.secret_key
    raw = hmac.new(secret.encode(), _ADMIN_PAYLOAD.encode(), hashlib.sha256).digest()
    expected_sig = base64.urlsafe_b64encode(raw).rstrip(b"=").decode()
    provided_sig = api_key[len(_ADMIN_PREFIX):]
    return hmac.compare_digest(expected_sig, provided_sig)


def verify_api_key(
    api_key: str,
    venture_id: str,
    secret: str | None = None,
) -> str | None:
    """
    Verify a signed API key against a claimed venture_id.

    Parameters
    ----------
    api_key:
        Raw value of the ``X-API-Key`` header.
    venture_id:
        Raw value of the ``X-Venture-ID`` header.
    secret:
        Signing secret — defaults to ``settings.secret_key``.

    Returns
    -------
    str | None
        The venture slug embedded in the key if the signature is valid and
        the slug is known; ``None`` if the key is malformed, tampered, or
        belongs to an unknown venture.
    """
    if "." not in api_key:
        return None

    slug, provided_sig = api_key.split(".", 1)

    if slug not in KNOWN_SLUGS:
        return None

    secret = secret or settings.secret_key
    expected_sig = _sign(slug, venture_id, secret)

    # Constant-time comparison prevents timing side-channels.
    if hmac.compare_digest(expected_sig, provided_sig):
        return slug

    return None
