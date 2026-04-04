"""Memory and user action routes."""

from fastapi import APIRouter, HTTPException
from repomemory.models.schemas import ActionRequest, MemoryStatsResponse

router = APIRouter()


@router.post("/actions")
async def record_action(req: ActionRequest):
    """Record a user action (opened, selected, thumbs_up, etc.)."""
    from repomemory.memory.tracker import record_action as _record

    _record(
        query_id=req.query_id,
        target_type=req.target_type,
        target_id=req.target_id,
        action_type=req.action,
    )
    return {"detail": "Action recorded"}


@router.get("/memory/{repo_id}/stats", response_model=MemoryStatsResponse)
async def memory_stats(repo_id: int):
    """Get memory/history statistics for a repository."""
    from repomemory.memory.tracker import get_memory_stats

    return get_memory_stats(repo_id)


@router.delete("/memory/{repo_id}")
async def clear_memory(repo_id: int):
    """Clear all memory for a repository."""
    from repomemory.memory.tracker import clear_memory as _clear

    _clear(repo_id)
    return {"detail": "Memory cleared"}
