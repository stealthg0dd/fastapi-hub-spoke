from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.router import api_router
from core.config import settings
from core.database import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title=f"{settings.spoke_name} API",
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_prefix)
