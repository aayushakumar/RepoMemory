"""Search and retrieval routes."""

import time

from fastapi import APIRouter, HTTPException

from repomemory.models.db import get_session
from repomemory.models.schemas import (
    ExplainRequest,
    ExplainResponse,
    SearchRequest,
    SearchResponse,
    TaskModeResponse,
)
from repomemory.models.tables import Repository

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(req: SearchRequest):
    """Main search endpoint — returns ranked results + context pack."""
    with get_session() as session:
        repo = session.get(Repository, req.repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        if repo.status != "ready":
            raise HTTPException(status_code=400, detail=f"Repository not ready (status: {repo.status})")

    start = time.perf_counter()

    from repomemory.context.packer import build_context_pack
    from repomemory.memory.tracker import record_query
    from repomemory.retrieval.orchestrator import retrieve

    query_id = record_query(req.repo_id, req.query, req.mode or "auto")
    retrieval_result = retrieve(
        query=req.query,
        repo_id=req.repo_id,
        mode=req.mode,
        top_k=req.top_k,
    )
    context_pack = build_context_pack(
        ranked_results=retrieval_result.ranked_results,
        query=req.query,
        mode=retrieval_result.classified_mode,
        budget=req.token_budget,
    )

    latency_ms = (time.perf_counter() - start) * 1000

    return SearchResponse(
        context_pack=context_pack,
        ranked_results=retrieval_result.ranked_results,
        classified_mode=retrieval_result.classified_mode,
        query_id=query_id,
        latency_ms=round(latency_ms, 2),
    )


@router.post("/search/explain", response_model=ExplainResponse)
async def explain_context(req: ExplainRequest):
    """Generate an AI summary of search results using Groq LLM."""
    from repomemory.config import settings
    from repomemory.context.llm import summarize_context

    if not settings.llm_enabled:
        raise HTTPException(
            status_code=503,
            detail="LLM not configured. Set REPOMEMORY_GROQ_API_KEY to enable AI explanations.",
        )

    files = req.context_pack.get("files", [])
    summary = summarize_context(req.query, files)

    if not summary:
        raise HTTPException(status_code=502, detail="LLM request failed. Try again later.")

    return ExplainResponse(summary=summary, model=settings.groq_model)


@router.get("/search/modes", response_model=list[TaskModeResponse])
async def list_modes():
    """List available task modes with descriptions."""
    from repomemory.retrieval.task_router import TASK_MODES

    return [
        TaskModeResponse(name=m.name, description=m.description, keywords=m.keywords)
        for m in TASK_MODES.values()
    ]
