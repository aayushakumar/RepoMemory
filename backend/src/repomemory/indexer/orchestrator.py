"""Indexing orchestrator — coordinates the full indexing pipeline."""

import logging
import time
from datetime import datetime, timezone
from pathlib import Path

from repomemory.indexer.scanner import scan_repository
from repomemory.indexer.metadata import extract_and_store_metadata
from repomemory.indexer.symbols import extract_and_store_symbols
from repomemory.indexer.chunker import chunk_and_store
from repomemory.indexer.embedder import embed_chunks
from repomemory.models.db import get_session
from repomemory.models.tables import Repository
from repomemory.models.schemas import IndexingStats

logger = logging.getLogger(__name__)


def index_repository(
    repo_id: int,
    repo_path: str,
    force: bool = False,
) -> IndexingStats:
    """Run the full indexing pipeline for a repository."""
    start = time.perf_counter()
    repo_root = Path(repo_path).resolve()

    logger.info("Starting indexing for %s (repo_id=%d, force=%s)", repo_root, repo_id, force)

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

        duration = time.perf_counter() - start

        # Update repository status
        with get_session() as session:
            repo = session.get(Repository, repo_id)
            repo.status = "ready"
            repo.indexed_at = datetime.now(timezone.utc)
            repo.file_count = len(db_files)
            repo.symbol_count = symbol_count
            repo.chunk_count = chunk_count

            # Build language summary
            ext_counts: dict[str, int] = {}
            for f in db_files:
                ext_counts[f.extension] = ext_counts.get(f.extension, 0) + 1
            sorted_exts = sorted(ext_counts.items(), key=lambda x: -x[1])
            repo.language_summary = ", ".join(f"{ext}({count})" for ext, count in sorted_exts[:5])

            session.commit()

        logger.info(
            "Indexing complete: %d files, %d symbols, %d chunks, %d embeddings in %.1fs",
            len(db_files), symbol_count, chunk_count, embedding_count, duration,
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
