"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from repomemory.config import settings
from repomemory.models.db import init_db

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    init_db()
    logger.info(
        "RepoMemory started (embedding=%s, llm=%s)",
        settings.embedding_provider,
        "groq" if settings.llm_enabled else "disabled",
    )
    yield


def create_app() -> FastAPI:
    from repomemory import __version__

    app = FastAPI(
        title="RepoMemory",
        description="AI-powered code retrieval engine — index any GitHub repo and search with natural language",
        version=__version__,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from repomemory.api.routes_eval import router as eval_router
    from repomemory.api.routes_index import router as index_router
    from repomemory.api.routes_memory import router as memory_router
    from repomemory.api.routes_search import router as search_router

    app.include_router(index_router, prefix="/api", tags=["repositories"])
    app.include_router(search_router, prefix="/api", tags=["search"])
    app.include_router(memory_router, prefix="/api", tags=["memory"])
    app.include_router(eval_router, prefix="/api", tags=["evaluation"])

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "version": __version__,
            "llm_enabled": settings.llm_enabled,
            "embedding_provider": settings.embedding_provider,
        }

    return app


app = create_app()
