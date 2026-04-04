"""Repository indexing routes."""

from fastapi import APIRouter, HTTPException
from repomemory.models.schemas import RepoCreate, RepoResponse, IndexingStats
from repomemory.models.db import get_session
from repomemory.models.tables import Repository

router = APIRouter()


@router.post("/repos", response_model=RepoResponse)
async def create_repo(req: RepoCreate):
    """Register and index a repository."""
    from pathlib import Path

    repo_path = Path(req.path).resolve()
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Directory not found: {req.path}")

    with get_session() as session:
        existing = session.query(Repository).filter(Repository.path == str(repo_path)).first()
        if existing:
            raise HTTPException(status_code=409, detail="Repository already indexed")

        repo = Repository(
            path=str(repo_path),
            name=repo_path.name,
            status="indexing",
        )
        session.add(repo)
        session.commit()
        session.refresh(repo)
        repo_id = repo.id

    # Run indexing
    from repomemory.indexer.orchestrator import index_repository

    stats = index_repository(repo_id, str(repo_path), force=False)

    with get_session() as session:
        repo = session.get(Repository, repo_id)
        return RepoResponse.model_validate(repo)


@router.get("/repos", response_model=list[RepoResponse])
async def list_repos():
    """List all indexed repositories."""
    with get_session() as session:
        repos = session.query(Repository).all()
        return [RepoResponse.model_validate(r) for r in repos]


@router.get("/repos/{repo_id}", response_model=RepoResponse)
async def get_repo(repo_id: int):
    """Get repository details."""
    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        return RepoResponse.model_validate(repo)


@router.post("/repos/{repo_id}/reindex", response_model=RepoResponse)
async def reindex_repo(repo_id: int):
    """Force re-index a repository."""
    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        repo.status = "indexing"
        session.commit()
        repo_path = repo.path

    from repomemory.indexer.orchestrator import index_repository

    index_repository(repo_id, repo_path, force=True)

    with get_session() as session:
        repo = session.get(Repository, repo_id)
        return RepoResponse.model_validate(repo)


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: int):
    """Remove a repository from the index."""
    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        session.delete(repo)
        session.commit()
    return {"detail": "Repository deleted"}