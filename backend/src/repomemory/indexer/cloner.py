"""Git repository cloning and management."""

import logging
import re
import shutil
from pathlib import Path
from urllib.parse import urlparse

from repomemory.config import settings

logger = logging.getLogger(__name__)

# Pattern for valid Git HTTPS URLs
_GIT_URL_PATTERN = re.compile(
    r"^https?://(?:github\.com|gitlab\.com|bitbucket\.org|codeberg\.org)/[\w.\-]+/[\w.\-]+(?:\.git)?$",
    re.IGNORECASE,
)


def is_git_url(value: str) -> bool:
    """Check if a string looks like a Git HTTPS URL."""
    return bool(_GIT_URL_PATTERN.match(value.strip().rstrip("/")))


def extract_repo_name(url: str) -> str:
    """Extract repository name from a Git URL."""
    parsed = urlparse(url.strip().rstrip("/"))
    path = parsed.path.rstrip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return path.split("/")[-1]


def _build_clone_url(url: str, token: str | None = None) -> str:
    """Build the clone URL, injecting token for private repos."""
    url = url.strip().rstrip("/")
    if not url.endswith(".git"):
        url = url + ".git"

    if token:
        parsed = urlparse(url)
        # Insert token as username for HTTPS auth
        authed = parsed._replace(netloc=f"{token}@{parsed.hostname}")
        return authed.geturl()

    return url


def _get_clone_path(repo_id: int) -> Path:
    """Get the local path where a repo should be cloned."""
    return settings.get_clone_dir() / f"repo_{repo_id}"


def clone_repo(
    url: str,
    repo_id: int,
    branch: str | None = None,
    token: str | None = None,
) -> Path:
    """Clone a remote repository.

    Returns the local path of the clone.
    Raises ValueError for invalid URLs, RuntimeError for clone failures.
    """
    import git

    if not is_git_url(url):
        raise ValueError(f"Invalid Git URL: {url}")

    clone_path = _get_clone_path(repo_id)

    # Clean up any previous clone
    if clone_path.exists():
        shutil.rmtree(clone_path)

    clone_url = _build_clone_url(url, token)

    logger.info("Cloning %s to %s (branch=%s)", url, clone_path, branch or "default")

    clone_kwargs: dict = {
        "depth": 1,  # shallow clone
        "single_branch": True,
    }
    if branch:
        clone_kwargs["branch"] = branch

    try:
        git.Repo.clone_from(
            clone_url,
            str(clone_path),
            **clone_kwargs,
        )
    except git.GitCommandError as e:
        # Strip token from error messages
        err_msg = str(e)
        if token:
            err_msg = err_msg.replace(token, "***")
        raise RuntimeError(f"Git clone failed: {err_msg}") from None

    # Size check
    total_size = sum(f.stat().st_size for f in clone_path.rglob("*") if f.is_file())
    max_bytes = settings.max_clone_size_mb * 1024 * 1024
    if total_size > max_bytes:
        shutil.rmtree(clone_path)
        raise ValueError(
            f"Repository too large ({total_size // (1024*1024)}MB > {settings.max_clone_size_mb}MB limit)"
        )

    logger.info("Clone complete: %s (%d MB)", clone_path, total_size // (1024 * 1024))
    return clone_path


def refresh_repo(repo_id: int) -> Path:
    """Pull latest changes for a previously cloned repo."""
    import git

    clone_path = _get_clone_path(repo_id)
    if not clone_path.exists():
        raise FileNotFoundError(f"Clone not found: {clone_path}")

    repo = git.Repo(str(clone_path))
    origin = repo.remotes.origin
    origin.pull()

    logger.info("Pulled latest for repo %d", repo_id)
    return clone_path


def delete_clone(repo_id: int) -> None:
    """Remove a cloned repository from disk."""
    clone_path = _get_clone_path(repo_id)
    if clone_path.exists():
        shutil.rmtree(clone_path)
        logger.info("Deleted clone for repo %d", repo_id)
