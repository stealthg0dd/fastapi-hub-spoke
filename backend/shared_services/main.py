import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from core.config import settings
from core.database import create_tables
from core.redis import close_redis
from middleware.venture_id import VentureIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await create_tables()
    except Exception as exc:
        # Log but don't crash — tables may already exist, or the DB
        # may become reachable after startup (Railway cold-start).
        logger.error("create_tables failed at startup: %s", exc)
    yield
    await close_redis()

app = FastAPI(
    title=f"{settings.hub_name} API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --- MIDDLEWARE ---
app.add_middleware(VentureIDMiddleware)

_STATIC_ORIGINS: list[str] = [
    "http://localhost:3000",
    "http://localhost:3001",
    "https://neufin.vercel.app",
    "https://neufinfinalbuild1.vercel.app",
    "https://neufin.ai",
    "https://www.neufin.ai",
]

_extra_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
_ALL_ORIGINS = list(dict.fromkeys(_STATIC_ORIGINS + _extra_origins))

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALL_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)