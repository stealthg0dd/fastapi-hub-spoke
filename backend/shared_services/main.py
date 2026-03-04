from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.router import api_router
from core.config import settings
from core.database import create_tables
from core.redis import close_redis
from middleware.venture_id import VentureIDMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield
    await close_redis()

app = FastAPI(
    title=f"{settings.hub_name} API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# --- STEP 1: ADD VENTURE ID MIDDLEWARE FIRST ---
# This ensures it's the "inner" layer.
app.add_middleware(VentureIDMiddleware)

# --- STEP 2: ADD CORS MIDDLEWARE LAST ---
# In FastAPI, the last middleware added is the FIRST one to touch the request.
# This ensures CORS handles the 'OPTIONS' preflight before VentureID even looks at it.
_STATIC_ORIGINS: list[str] = [
    # Local development
    "http://localhost:3000",
    "http://localhost:3001",
    # Vercel deployments (add new preview URLs here or via ALLOWED_ORIGINS env var)
    "https://neufin.vercel.app",
    "https://neufinfinalbuild1.vercel.app",
    # Custom domain
    "https://neufin.ai",
    "https://www.neufin.ai",
]

# ALLOWED_ORIGINS env var (comma-separated) lets you add extra origins from
# Railway's dashboard without redeploying — useful for Vercel preview URLs.
_extra_origins = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
_ALL_ORIGINS = list(dict.fromkeys(_STATIC_ORIGINS + _extra_origins))  # deduped

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALL_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

app.include_router(api_router, prefix=settings.api_prefix)