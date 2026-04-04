"""File metadata extraction and DB persistence."""

import logging
from pathlib import Path

from repomemory.indexer.scanner import ScannedFile
from repomemory.models.db import get_session
from repomemory.models.tables import File

logger = logging.getLogger(__name__)


def _count_lines(filepath: Path) -> int:
    try:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def extract_and_store_metadata(
    repo_id: int,
    scanned_files: list[ScannedFile],
) -> list[File]:
    """Insert file metadata into the DB, return list of File ORM objects."""
    db_files: list[File] = []

    with get_session() as session:
        # Get existing files for this repo (for incremental indexing)
        existing = {
            f.path: f
            for f in session.query(File).filter(File.repo_id == repo_id).all()
        }

        new_count = 0
        updated_count = 0
        skipped_count = 0

        for sf in scanned_files:
            line_count = _count_lines(sf.path)

            if sf.relative_path in existing:
                db_file = existing[sf.relative_path]
                if db_file.content_hash == sf.content_hash:
                    db_files.append(db_file)
                    skipped_count += 1
                    continue
                # File changed — update
                db_file.size_bytes = sf.size_bytes
                db_file.last_modified = sf.mtime
                db_file.content_hash = sf.content_hash
                db_file.line_count = line_count
                db_files.append(db_file)
                updated_count += 1
            else:
                db_file = File(
                    repo_id=repo_id,
                    path=sf.relative_path,
                    extension=sf.extension,
                    size_bytes=sf.size_bytes,
                    line_count=line_count,
                    last_modified=sf.mtime,
                    content_hash=sf.content_hash,
                )
                session.add(db_file)
                db_files.append(db_file)
                new_count += 1

        # Remove files that no longer exist
        current_paths = {sf.relative_path for sf in scanned_files}
        for path, db_file in existing.items():
            if path not in current_paths:
                session.delete(db_file)

        session.commit()

        # Refresh to get IDs
        for f in db_files:
            session.refresh(f)

        logger.info(
            "Metadata: %d new, %d updated, %d unchanged",
            new_count,
            updated_count,
            skipped_count,
        )

    return db_files
