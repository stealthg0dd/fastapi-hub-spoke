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

# chat router defines prefix="/chat" internally, so don't add it again here.
api_router.include_router(health_router)
api_router.include_router(chat_router)
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(market_router, prefix="/market")
api_router.include_router(stripe_router, prefix="/stripe")

# ── SPOKE PATH ────────────────────────────────────────────────────────────────
# _SERVICE_ROOT = the directory that contains main.py (backend/shared_services/ locally, /app on Railway).
# Spokes live as a sibling directory: backend/spokes/ next to backend/shared_services/.
# On Railway (root dir = backend/shared_services) the spokes dir won't exist in the
# container, so _mount_spoke() will log a warning and skip — no crash.
_SERVICE_ROOT = Path(__file__).resolve().parent.parent  # api/ → shared_services/
_SPOKES_DIR = (_SERVICE_ROOT.parent / "spokes").resolve()

logger.info("Router spoke directory: %s (exists=%s)", _SPOKES_DIR, _SPOKES_DIR.exists())

# ── Spoke routers ─────────────────────────────────────────────────────────────
_SPOKE_WINS: frozenset[str] = frozenset({"models"})
_HUB_WINS: frozenset[str] = frozenset({"agents"})

def _ensure_spoke_path(spoke: str) -> None:
    p = str(_SPOKES_DIR / spoke)
    if not os.path.exists(p):
        raise FileNotFoundError(f"Spoke path does not exist: {p}")
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)

def _load_spoke_module(spoke: str, filename: str = "api.py") -> types.ModuleType:
    path = _SPOKES_DIR / spoke / filename
    module_name = f"spoke_{spoke}_api"

    if not path.exists():
        raise FileNotFoundError(f"Cannot locate spoke module file: {path}")

    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Spec loader failed for: {path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod

    spoke_root = str(_SPOKES_DIR / spoke)

    _displaced: dict[str, Any] = {}
    for key in list(sys.modules):
        top = key.split(".")[0]
        if top not in _SPOKE_WINS:
            continue
        m = sys.modules[key]
        origin = getattr(m, "__file__", None) or ""
        if not origin.startswith(spoke_root):
            _displaced[key] = sys.modules.pop(key)

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
        sys.modules.update(_displaced)

    return mod

def _mount_spoke(slug: str, prefix: str) -> None:
    try:
        _ensure_spoke_path(slug)
        mod = _load_spoke_module(slug)
        api_router.include_router(mod.router, prefix=prefix)
        logger.info("router: %s spoke mounted at %s", slug, prefix)
    except (ImportError, FileNotFoundError, AttributeError) as exc:
        logger.warning("router: %s spoke unavailable (%s)", slug, exc)

_mount_spoke("neufin", "/neufin")