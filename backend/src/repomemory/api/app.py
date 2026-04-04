"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repomemory.config import settings
from repomemory.models.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="RepoMemory",
        description="Local-first code retrieval engine for AI coding workflows",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from repomemory.api.routes_index import router as index_router
    from repomemory.api.routes_search import router as search_router
    from repomemory.api.routes_memory import router as memory_router
    from repomemory.api.routes_eval import router as eval_router

    app.include_router(index_router, prefix="/api", tags=["repositories"])
    app.include_router(search_router, prefix="/api", tags=["search"])
    app.include_router(memory_router, prefix="/api", tags=["memory"])
    app.include_router(eval_router, prefix="/api", tags=["evaluation"])

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
