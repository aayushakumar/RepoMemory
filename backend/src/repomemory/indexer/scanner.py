"""Repository file scanner — walks a directory tree respecting ignore rules."""

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import pathspec

from repomemory.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ScannedFile:
    path: Path  # absolute path
    relative_path: str  # relative to repo root
    extension: str
    size_bytes: int
    mtime: float
    content_hash: str


def _load_gitignore(repo_root: Path) -> pathspec.PathSpec | None:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.is_file():
        return None
    try:
        patterns = gitignore_path.read_text(encoding="utf-8").splitlines()
        return pathspec.PathSpec.from_lines("gitignore", patterns)
    except Exception:
        logger.warning("Failed to parse .gitignore at %s", gitignore_path)
        return None


def _compute_content_hash(filepath: Path, max_bytes: int = 8192) -> str:
    h = hashlib.sha256()
    try:
        with open(filepath, "rb") as f:
            h.update(f.read(max_bytes))
    except OSError:
        return ""
    return h.hexdigest()


def _should_ignore(relative_path: str, ignore_spec: pathspec.PathSpec | None) -> bool:
    parts = Path(relative_path).parts
    for pattern in settings.ignore_patterns:
        if pattern in parts:
            return True
        if relative_path.endswith(pattern):
            return True
    if ignore_spec and ignore_spec.match_file(relative_path):
        return True
    return False


def _has_supported_extension(filepath: Path) -> bool:
    # Handle extensionless files like Makefile, Dockerfile
    if filepath.name in settings.supported_extensions:
        return True
    return filepath.suffix in settings.supported_extensions


def scan_repository(repo_path: str | Path) -> list[ScannedFile]:
    """Scan a repository directory and return list of indexable files."""
    repo_root = Path(repo_path).resolve()
    if not repo_root.is_dir():
        raise FileNotFoundError(f"Repository path not found: {repo_root}")

    ignore_spec = _load_gitignore(repo_root)
    max_size = settings.max_file_size_kb * 1024
    results: list[ScannedFile] = []

    for filepath in repo_root.rglob("*"):
        if not filepath.is_file():
            continue

        relative = filepath.relative_to(repo_root)
        relative_str = str(relative)

        if _should_ignore(relative_str, ignore_spec):
            continue

        if not _has_supported_extension(filepath):
            continue

        try:
            stat = filepath.stat()
        except OSError:
            continue

        if stat.st_size > max_size:
            logger.debug("Skipping large file: %s (%d KB)", relative_str, stat.st_size // 1024)
            continue

        if stat.st_size == 0:
            continue

        content_hash = _compute_content_hash(filepath)

        results.append(ScannedFile(
            path=filepath,
            relative_path=relative_str,
            extension=filepath.suffix or filepath.name,
            size_bytes=stat.st_size,
            mtime=stat.st_mtime,
            content_hash=content_hash,
        ))

    logger.info("Scanned %d files in %s", len(results), repo_root)
    return results
