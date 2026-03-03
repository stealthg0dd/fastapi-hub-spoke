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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For local dev, "*" is fine. In Vercel, use specific URLs.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",   # landing dev
        "http://localhost:3001",   # portal dev
        "https://neufin.ai",
        "https://www.neufin.ai",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enforce X-Venture-ID on every non-exempt request and store it in a
# ContextVar that the database session reads to set app.current_venture_id,
# enabling PostgreSQL Row-Level Security to auto-scope queries.
app.add_middleware(VentureIDMiddleware)

app.include_router(api_router, prefix=settings.api_prefix)
