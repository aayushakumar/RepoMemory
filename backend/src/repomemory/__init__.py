"""RepoMemory — AI-powered code retrieval engine.

Index any GitHub repository by URL and search with natural language.

Quick start:
    from repomemory import RepoMemory

    rm = RepoMemory()
    rm.index("https://github.com/owner/repo")
    results = rm.search("how does authentication work?")
"""

__version__ = "0.2.0"


class RepoMemory:
    """Main facade for programmatic usage of RepoMemory."""

    def __init__(self):
        from repomemory.config import settings
        from repomemory.models.db import init_db

        settings.ensure_dirs()
        init_db()

    def index(
        self,
        source: str,
        branch: str | None = None,
        token: str | None = None,
        force: bool = False,
    ) -> dict:
        """Index a repository from a URL or local path.

        Args:
            source: GitHub URL or local filesystem path.
            branch: Branch/tag to clone (URL only).
            token: GitHub personal access token (private repos only).
            force: Force re-index if already indexed.

        Returns:
            dict with indexing statistics.
        """
        from pathlib import Path

        from repomemory.indexer.cloner import clone_repo, extract_repo_name, is_git_url
        from repomemory.indexer.orchestrator import index_repository
        from repomemory.models.db import get_session
        from repomemory.models.tables import Repository

        if is_git_url(source):
            repo_name = extract_repo_name(source)
            with get_session() as session:
                existing = session.query(Repository).filter(Repository.url == source).first()
                if existing and not force:
                    return {"repo_id": existing.id, "status": existing.status, "skipped": True}
                if existing:
                    repo_id = existing.id
                else:
                    repo = Repository(path=source, name=repo_name, url=source, branch=branch, status="indexing")
                    session.add(repo)
                    session.commit()
                    session.refresh(repo)
                    repo_id = repo.id

            clone_path = clone_repo(source, repo_id, branch=branch, token=token)
            with get_session() as session:
                repo = session.get(Repository, repo_id)
                repo.clone_path = str(clone_path)
                session.commit()
            repo_path = str(clone_path)
        else:
            local_path = Path(source).resolve()
            if not local_path.is_dir():
                raise FileNotFoundError(f"Directory not found: {source}")

            with get_session() as session:
                existing = session.query(Repository).filter(Repository.path == str(local_path)).first()
                if existing and not force:
                    return {"repo_id": existing.id, "status": existing.status, "skipped": True}
                if existing:
                    repo_id = existing.id
                else:
                    repo = Repository(path=str(local_path), name=local_path.name, status="indexing")
                    session.add(repo)
                    session.commit()
                    session.refresh(repo)
                    repo_id = repo.id
            repo_path = str(local_path)

        stats = index_repository(repo_id, repo_path, force=force)
        return {
            "repo_id": stats.repo_id,
            "files_indexed": stats.files_indexed,
            "symbols_extracted": stats.symbols_extracted,
            "chunks_created": stats.chunks_created,
            "embeddings_generated": stats.embeddings_generated,
            "duration_seconds": stats.duration_seconds,
        }

    def search(
        self,
        query: str,
        repo: str | int | None = None,
        mode: str | None = None,
        top_k: int = 20,
        token_budget: int = 8000,
    ) -> dict:
        """Search indexed repositories with natural language.

        Args:
            query: Natural language search query.
            repo: Repository name or ID. If None, uses the first ready repo.
            mode: Search mode (bug_fix, trace_flow, test_lookup, config_lookup, or None for auto).
            top_k: Number of results to return.
            token_budget: Token budget for context packing.

        Returns:
            dict with ranked_results, context_pack, and metadata.
        """
        from repomemory.context.packer import build_context_pack
        from repomemory.models.db import get_session
        from repomemory.models.tables import Repository
        from repomemory.retrieval.orchestrator import retrieve

        with get_session() as session:
            if repo is not None:
                if isinstance(repo, int):
                    repo_obj = session.get(Repository, repo)
                else:
                    repo_obj = session.query(Repository).filter(Repository.name == repo).first()
            else:
                repo_obj = session.query(Repository).filter(Repository.status == "ready").first()

            if not repo_obj:
                raise ValueError("No ready repository found")
            repo_id = repo_obj.id

        result = retrieve(query=query, repo_id=repo_id, mode=mode, top_k=top_k)
        context = build_context_pack(
            ranked_results=result.ranked_results,
            query=query,
            mode=result.classified_mode,
            budget=token_budget,
        )

        return {
            "classified_mode": result.classified_mode,
            "ranked_results": [
                {
                    "file_path": r.file_path,
                    "combined_score": r.combined_score,
                    "explanation": r.explanation,
                }
                for r in result.ranked_results
            ],
            "context_pack": {
                "total_tokens": context.total_tokens,
                "budget_used_pct": context.budget_used_pct,
                "files": [f.path for f in context.files],
            },
        }

    def list_repos(self) -> list[dict]:
        """List all indexed repositories."""
        from repomemory.models.db import get_session
        from repomemory.models.tables import Repository

        with get_session() as session:
            repos = session.query(Repository).all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "url": r.url,
                    "status": r.status,
                    "file_count": r.file_count,
                    "symbol_count": r.symbol_count,
                    "chunk_count": r.chunk_count,
                }
                for r in repos
            ]
