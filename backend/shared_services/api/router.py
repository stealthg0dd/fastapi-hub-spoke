from __future__ import annotations

import importlib.util
import logging
import sys
import types
import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api.admin import router as admin_router
from api.chat import router as chat_router
from api.health import router as health_router
from api.market import router as market_router
from api.stripe_service import router as stripe_router

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Core routes
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(market_router, prefix="/market")
api_router.include_router(stripe_router, prefix="/stripe")

# ── SPOKE PATH DISCOVERY ──────────────────────────────────────────────────────
# This logic ensures the app finds the 'spokes' folder regardless of Docker 
# structure or local dev paths.
_SERVICE_ROOT = Path(__file__).resolve().parent.parent  # api/ -> shared_services/

def _find_spokes_dir() -> Path:
    """
    Probe candidate locations for the spokes directory, in priority order.

    Priority rationale:
      1. /app/spokes           — Railway (shared_services-root deploy): container is /app,
                                 so spokes land at /app/spokes when the repo ships them there.
      2. /app/backend/spokes   — Railway (repo-root deploy): full repo at /app,
                                 spokes are under /app/backend/spokes.
      3. _SERVICE_ROOT.parent  — Local dev: shared_services/../spokes = backend/spokes.
                                 NOTE: when _SERVICE_ROOT=/app this resolves to /spokes (no
                                 /app prefix) which is why it must come AFTER the explicit
                                 /app paths above.
      4. CWD-relative          — Last resort for unusual working-directory setups.

    A candidate is accepted when the directory itself exists; the neufin
    sub-directory check was removed so a freshly-created but currently-empty
    spokes dir doesn't block the match.
    """
    candidates = [
        Path("/app") / "spokes",                      # Railway: shared_services-root deploy
        Path("/app") / "backend" / "spokes",          # Railway: repo-root deploy
        _SERVICE_ROOT.parent / "spokes",              # Local dev: backend/spokes/
        Path(os.getcwd()) / "spokes",                 # CWD fallback
    ]

    for c in candidates:
        if c.is_dir():
            return c.resolve()

    # Nothing found — return /app/spokes so the warning names the most-likely
    # Railway path rather than the misleading /spokes (filesystem root).
    return Path("/app/spokes")

_SPOKES_DIR = _find_spokes_dir()
logger.info("Router configuration: Spoke directory set to %s (Found=%s)", 
            _SPOKES_DIR, _SPOKES_DIR.exists())

# ── Spoke routers ─────────────────────────────────────────────────────────────
_SPOKE_WINS: frozenset[str] = frozenset({"models"})
_HUB_WINS: frozenset[str] = frozenset({"agents"})

def _ensure_spoke_path(spoke: str) -> None:
    """Injects the spoke path into sys.path to allow internal imports."""
    p = str(_SPOKES_DIR / spoke)
    if not os.path.exists(p):
        raise FileNotFoundError(f"Spoke directory missing at: {p}")
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

def _load_spoke_module(spoke: str, filename: str = "api.py") -> types.ModuleType:
    """Dynamically loads the spoke's api.py while preventing module collisions."""
    path = _SPOKES_DIR / spoke / filename
    module_name = f"spoke_{spoke}_api"

    if not path.exists():
        raise FileNotFoundError(f"Spoke API file missing at: {path}")

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not initialize loader for spoke module: {path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod

    spoke_root = str(_SPOKES_DIR / spoke)

    # Evict conflicting packages (e.g., 'models') to let Spoke's version win
    _displaced: dict[str, Any] = {}
    for key in list(sys.modules):
        top = key.split(".")[0]
        if top not in _SPOKE_WINS:
            continue
        m = sys.modules[key]
        origin = getattr(m, "__file__", None) or ""
        if not origin.startswith(spoke_root):
            _displaced[key] = sys.modules.pop(key)

    # Pre-load hub packages that Hub should win (e.g., 'agents')
    for pkg_name in _HUB_WINS:
        if pkg_name not in sys.modules:
            if spoke_root in sys.path:
                sys.path.remove(spoke_root)
            try:
                importlib.import_module(pkg_name)
            except ImportError:
                pass
            finally:
                sys.path.insert(0, spoke_root)

    try:
        spec.loader.exec_module(mod)
    finally:
        # Restore the hub's displaced modules
        sys.modules.update(_displaced)

    return mod

def _mount_spoke(slug: str, prefix: str) -> None:
    """Mounts the spoke router onto the main API router."""
    try:
        _ensure_spoke_path(slug)
        mod = _load_spoke_module(slug)
        # Ensure the module has a 'router' attribute
        if hasattr(mod, 'router'):
            api_router.include_router(mod.router, prefix=prefix)
            logger.info("Successfully mounted '%s' spoke at prefix %s", slug, prefix)
        else:
            logger.error("Spoke '%s' has no APIRouter named 'router'", slug)
    except Exception as exc:
        logger.warning("Spoke '%s' unavailable: %s", slug, exc)

# Mount Spoke
_mount_spoke("neufin", "/neufin")