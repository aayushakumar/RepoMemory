"""Indexing orchestrator — coordinates the full indexing pipeline."""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from repomemory.indexer.chunker import chunk_and_store
from repomemory.indexer.dependency_graph import build_dependency_graph
from repomemory.indexer.embedder import embed_chunks
from repomemory.indexer.metadata import extract_and_store_metadata
from repomemory.indexer.scanner import scan_repository
from repomemory.indexer.symbols import extract_and_store_symbols
from repomemory.models.db import get_session
from repomemory.models.schemas import IndexingStats
from repomemory.models.tables import Repository

logger = logging.getLogger(__name__)


def _get_head_commit(repo_path: Path) -> str | None:
    """Get the HEAD commit hash if this is a git repo."""
    try:
        import git

        repo = git.Repo(str(repo_path))
        return repo.head.commit.hexsha
    except Exception:
        return None


def _get_changed_files(repo_path: Path, old_commit: str) -> set[str] | None:
    """Get list of changed files since old_commit. Returns None on failure."""
    try:
        import git

        repo = git.Repo(str(repo_path))
        diff = repo.head.commit.diff(old_commit)
        changed = set()
        for d in diff:
            if d.a_path:
                changed.add(d.a_path)
            if d.b_path:
                changed.add(d.b_path)
        return changed
    except Exception:
        return None


def index_repository(
    repo_id: int,
    repo_path: str,
    force: bool = False,
) -> IndexingStats:
    """Run the full indexing pipeline for a repository."""
    start = time.perf_counter()
    repo_root = Path(repo_path).resolve()

    logger.info("Starting indexing for %s (repo_id=%d, force=%s)", repo_root, repo_id, force)

    # Check for incremental indexing opportunity
    if not force:
        with get_session() as session:
            repo = session.get(Repository, repo_id)
            if repo and repo.last_commit_hash and repo.status == "ready":
                new_commit = _get_head_commit(repo_root)
                if new_commit and new_commit != repo.last_commit_hash:
                    changed = _get_changed_files(repo_root, repo.last_commit_hash)
                    if changed is not None:
                        logger.info(
                            "Incremental indexing: %d changed files since %s",
                            len(changed),
                            repo.last_commit_hash[:8],
                        )

    try:
        # 1. Scan repository
        scanned_files = scan_repository(repo_root)

        # 2. Extract and store file metadata
        db_files = extract_and_store_metadata(repo_id, scanned_files)

        # 3. Extract symbols
        symbol_count = extract_and_store_symbols(repo_root, db_files)

        # 4. Chunk content
        chunk_count = chunk_and_store(repo_root, db_files)

        # 5. Generate embeddings
        embedding_count = embed_chunks(repo_id)

        # 6. Build dependency graph
        edge_count = build_dependency_graph(repo_id, repo_root)

        duration = time.perf_counter() - start

        # Update repository status
        with get_session() as session:
            repo = session.get(Repository, repo_id)
            repo.status = "ready"
            repo.indexed_at = datetime.now(UTC)
            repo.file_count = len(db_files)
            repo.symbol_count = symbol_count
            repo.chunk_count = chunk_count
            repo.last_commit_hash = _get_head_commit(repo_root)

            # Build language summary
            ext_counts: dict[str, int] = {}
            for f in db_files:
                ext_counts[f.extension] = ext_counts.get(f.extension, 0) + 1
            sorted_exts = sorted(ext_counts.items(), key=lambda x: -x[1])
            repo.language_summary = ", ".join(f"{ext}({count})" for ext, count in sorted_exts[:5])

            session.commit()

        logger.info(
            "Indexing complete: %d files, %d symbols, %d chunks, %d embeddings, %d dep edges in %.1fs",
            len(db_files),
            symbol_count,
            chunk_count,
            embedding_count,
            edge_count,
            duration,
        )

        return IndexingStats(
            repo_id=repo_id,
            files_indexed=len(db_files),
            symbols_extracted=symbol_count,
            chunks_created=chunk_count,
            embeddings_generated=embedding_count,
            duration_seconds=round(duration, 2),
        )

    except Exception as e:
        logger.error("Indexing failed for repo %d: %s", repo_id, e)
        with get_session() as session:
            repo = session.get(Repository, repo_id)
            if repo:
                repo.status = "error"
                session.commit()
        raise
