from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api import upload, jobs, results, admin


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    # Auto-create tables in local SQLite/dev mode.
    if settings.debug or settings.database_url.startswith("sqlite"):
        await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    openapi_url=f"{settings.api_prefix}/openapi.json",
    docs_url=f"{settings.api_prefix}/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix=settings.api_prefix)
app.include_router(jobs.router, prefix=settings.api_prefix)
app.include_router(results.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
