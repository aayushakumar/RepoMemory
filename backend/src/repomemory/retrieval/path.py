"""Path/filename fuzzy matching search."""

import logging

from rapidfuzz import fuzz

from repomemory.models.db import get_session
from repomemory.models.tables import File

logger = logging.getLogger(__name__)


def _extract_path_tokens(query: str) -> list[str]:
    """Extract potential file/path fragments from query."""
    tokens = []
    for word in query.split():
        # Path-like tokens
        if "/" in word or "." in word or "_" in word:
            tokens.append(word.lower())
        # Also keep individual words for partial matching
        tokens.append(word.lower())
    return tokens


def path_search(
    query: str,
    repo_id: int,
    top_k: int = 50,
) -> list[tuple[int, float]]:
    """Search files by path fuzzy match. Returns list of (file_id, normalized_score)."""
    tokens = _extract_path_tokens(query)

    with get_session() as session:
        files = session.query(File).filter(File.repo_id == repo_id).all()

        scored = []
        for f in files:
            path_lower = f.path.lower()
            # Best score across all query tokens
            best_score = 0.0
            for token in tokens:
                # Partial ratio handles substring matching
                s = fuzz.partial_ratio(token, path_lower) / 100.0
                best_score = max(best_score, s)

                # Bonus for exact directory/filename component match
                parts = path_lower.split("/")
                for part in parts:
                    name_score = fuzz.ratio(token, part) / 100.0
                    best_score = max(best_score, name_score)

            if best_score > 0.3:  # threshold
                scored.append((f.id, best_score))

    scored.sort(key=lambda x: -x[1])
    return scored[:top_k]
