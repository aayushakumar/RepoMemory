"""Repository indexing routes."""

import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from repomemory.models.db import get_session
from repomemory.models.schemas import RepoCreate, RepoResponse
from repomemory.models.tables import Repository

router = APIRouter()
logger = logging.getLogger(__name__)


def _run_indexing(repo_id: int, repo_path: str, force: bool = False):
    """Background task: run the full indexing pipeline."""
    try:
        from repomemory.indexer.orchestrator import index_repository

        index_repository(repo_id, repo_path, force=force)
    except Exception as e:
        logger.error("Background indexing failed for repo %d: %s", repo_id, e)
        with get_session() as session:
            repo = session.get(Repository, repo_id)
            if repo:
                repo.status = "error"
                repo.error_message = str(e)[:500]
                session.commit()


@router.post("/repos", response_model=RepoResponse)
async def create_repo(req: RepoCreate, background_tasks: BackgroundTasks):
    """Register and index a repository from URL or local path."""
    from repomemory.indexer.cloner import clone_repo, extract_repo_name, is_git_url

    url = req.url
    local_path = req.path

    if not url and not local_path:
        raise HTTPException(status_code=400, detail="Provide either 'url' or 'path'")

    if url and is_git_url(url):
        # Remote repo — clone it
        repo_name = extract_repo_name(url)

        with get_session() as session:
            existing = session.query(Repository).filter(Repository.url == url).first()
            if existing:
                raise HTTPException(status_code=409, detail="Repository already indexed")

            repo = Repository(
                path=url,  # use URL as the display path
                name=repo_name,
                url=url,
                branch=req.branch,
                status="indexing",
            )
            session.add(repo)
            session.commit()
            session.refresh(repo)
            repo_id = repo.id

        # Clone and index in background
        def _clone_and_index(repo_id: int, url: str, branch: str | None, token: str | None):
            try:
                clone_path = clone_repo(url, repo_id, branch=branch, token=token)
                with get_session() as session:
                    repo = session.get(Repository, repo_id)
                    repo.clone_path = str(clone_path)
                    session.commit()
                _run_indexing(repo_id, str(clone_path))
            except Exception as e:
                logger.error("Clone+index failed for repo %d: %s", repo_id, e)
                with get_session() as session:
                    repo = session.get(Repository, repo_id)
                    if repo:
                        repo.status = "error"
                        repo.error_message = str(e)[:500]
                        session.commit()

        background_tasks.add_task(_clone_and_index, repo_id, url, req.branch, req.token)

    elif local_path:
        # Local path — backward compatible
        from pathlib import Path

        repo_path = Path(local_path).resolve()
        if not repo_path.is_dir():
            raise HTTPException(status_code=400, detail=f"Directory not found: {local_path}")

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

        background_tasks.add_task(_run_indexing, repo_id, str(repo_path))

    else:
        raise HTTPException(status_code=400, detail="Invalid URL format. Use a GitHub/GitLab HTTPS URL.")

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
async def reindex_repo(repo_id: int, background_tasks: BackgroundTasks):
    """Force re-index a repository."""
    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")
        repo.status = "indexing"
        repo.error_message = None
        session.commit()
        repo_path = repo.clone_path or repo.path

    background_tasks.add_task(_run_indexing, repo_id, repo_path, True)

    with get_session() as session:
        repo = session.get(Repository, repo_id)
        return RepoResponse.model_validate(repo)


@router.delete("/repos/{repo_id}")
async def delete_repo(repo_id: int):
    """Remove a repository from the index."""
    from repomemory.indexer.cloner import delete_clone

    with get_session() as session:
        repo = session.get(Repository, repo_id)
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        # Clean up clone if it exists
        if repo.url:
            delete_clone(repo_id)

        session.delete(repo)
        session.commit()
    return {"detail": "Repository deleted"}
