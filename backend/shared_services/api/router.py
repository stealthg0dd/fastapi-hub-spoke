from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from api.admin import router as admin_router
from api.chat import router as chat_router
from api.concierge import router as concierge_router
from api.health import router as health_router
from api.market import router as market_router

logger = logging.getLogger(__name__)

api_router = APIRouter()

api_router.include_router(health_router)
api_router.include_router(chat_router, prefix="/chat")
api_router.include_router(concierge_router)
api_router.include_router(admin_router, prefix="/admin")
api_router.include_router(market_router, prefix="/market")

# ── Spoke routers ─────────────────────────────────────────────────────────────
# Each spoke exposes a FastAPI router at  spokes/<slug>/api.py.
# We load spoke modules by absolute file path so they get a unique module name
# (e.g. "spoke_neufin_api") that never collides with the hub's own "api" package.
#
# Challenge: both shared_services/ and spokes/<slug>/ contain a top-level
# "models" package.  shared_services/models/ (hub ORM) and spokes/neufin/models/
# (spoke ORM) would collide if both paths are on sys.path at the same time.
#
# Solution: before exec_module() we temporarily evict hub packages that share
# a name with spoke packages, so the spoke's import resolves to its own copy.
# After exec_module() the hub packages are restored; the spoke module already
# holds the correct class bindings in its __dict__ so the registry state doesn't
# matter.

_root = Path(__file__).resolve().parents[2]   # fastapi-hub-spoke/

# Packages that SPOKE wins — hub copies are evicted before exec_module so the
# spoke can import its own version (e.g. spokes/neufin/models/orm.py).
_SPOKE_WINS: frozenset[str] = frozenset({"models"})

# Packages that HUB wins — pre-loaded into sys.modules before exec_module so
# spoke's identically-named directories (e.g. spokes/neufin/agents/) cannot
# shadow the hub's canonical implementation.
_HUB_WINS: frozenset[str] = frozenset({"agents"})


def _ensure_spoke_path(spoke: str) -> None:
    """
    Insert spokes/<slug>/ at the *front* of sys.path.

    Always moves to position 0 even if the path already appears later so that
    the spoke's packages take priority over same-named hub packages during
    exec_module().
    """
    p = str(_root / "spokes" / spoke)
    if p in sys.path:
        sys.path.remove(p)
    sys.path.insert(0, p)


def _load_spoke_module(spoke: str, filename: str = "api.py") -> types.ModuleType:
    """
    Load a spoke's module from its absolute file path.

    Uses spec_from_file_location so the module gets a unique name in
    sys.modules ("spoke_{slug}_api") and never shadows or is shadowed by the
    hub's "api" package.

    During exec_module() the hub's conflicting top-level packages are evicted
    from sys.modules so the spoke can import its own versions.  They are
    restored afterwards; the spoke module retains its own bindings regardless.
    """
    path = _root / "spokes" / spoke / filename
    module_name = f"spoke_{spoke}_api"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot locate spoke module: {path}")

    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod          # register before exec to handle
                                            # any intra-spoke circular imports

    spoke_root = str(_root / "spokes" / spoke)

    # ── Step 1: evict hub packages that spoke should shadow ───────────────────
    # e.g. shared_services/models/ must yield to spokes/neufin/models/orm.py
    _displaced: dict[str, Any] = {}
    for key in list(sys.modules):
        top = key.split(".")[0]
        if top not in _SPOKE_WINS:
            continue
        m = sys.modules[key]
        origin = getattr(m, "__file__", None) or ""
        if not origin.startswith(spoke_root):   # hub-owned — evict temporarily
            _displaced[key] = sys.modules.pop(key)

    # ── Step 2: pre-load hub packages that must NOT be shadowed by spoke ──────
    # e.g. shared_services/agents/ must win over spokes/neufin/agents/.
    # Temporarily remove spoke path so hub's version is found first.
    for pkg_name in _HUB_WINS:
        if pkg_name not in sys.modules:
            if spoke_root in sys.path:
                sys.path.remove(spoke_root)
            try:
                importlib.import_module(pkg_name)
            except ImportError:
                pass
            finally:
                sys.path.insert(0, spoke_root)  # restore spoke at front

    try:
        spec.loader.exec_module(mod)
    finally:
        # Restore hub packages.  Spoke's class bindings are already captured
        # in mod.__dict__ so overwriting sys.modules doesn't affect them.
        sys.modules.update(_displaced)

    return mod


def _mount_spoke(slug: str, prefix: str) -> None:
    """Load a spoke router and mount it on api_router.  Non-fatal on failure."""
    try:
        _ensure_spoke_path(slug)
        mod = _load_spoke_module(slug)
        api_router.include_router(mod.router, prefix=prefix)
        logger.info("router: %s spoke mounted at %s", slug, prefix)
    except (ImportError, FileNotFoundError, AttributeError) as exc:
        logger.warning("router: %s spoke unavailable (%s)", slug, exc)


# ── Spoke registrations ───────────────────────────────────────────────────────
_mount_spoke("neufin", "/spokes/neufin")
# _mount_spoke("arisole", "/spokes/arisole")   # uncomment when spoke is ready
# _mount_spoke("neumas",  "/spokes/neumas")
# _mount_spoke("apex",    "/spokes/apex")
