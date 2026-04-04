"""Symbol name fuzzy search."""

import logging
import re

from rapidfuzz import fuzz

from repomemory.models.db import get_session
from repomemory.models.tables import Symbol, File

logger = logging.getLogger(__name__)


def _extract_symbol_tokens(query: str) -> list[str]:
    """Extract potential symbol names from query (CamelCase, snake_case)."""
    tokens = []
    for word in query.split():
        # snake_case tokens
        if "_" in word:
            tokens.append(word.lower())
        # CamelCase tokens
        if any(c.isupper() for c in word[1:]):
            tokens.append(word)
            # Split CamelCase
            parts = re.findall(r"[A-Z][a-z]+|[a-z]+|[A-Z]+", word)
            tokens.extend(p.lower() for p in parts)
        else:
            tokens.append(word.lower())
    return list(set(tokens))


def symbol_search(
    query: str,
    repo_id: int,
    top_k: int = 50,
) -> list[tuple[int, int, float]]:
    """Search symbols by name fuzzy match.
    Returns list of (symbol_id, file_id, normalized_score).
    """
    tokens = _extract_symbol_tokens(query)

    with get_session() as session:
        symbols = (
            session.query(Symbol)
            .join(Symbol.file)
            .filter(File.repo_id == repo_id)
            .filter(Symbol.kind.in_(["function", "class", "method"]))
            .all()
        )

        scored = []
        for sym in symbols:
            name_lower = sym.name.lower()
            best_score = 0.0

            for token in tokens:
                s = fuzz.ratio(token, name_lower) / 100.0
                best_score = max(best_score, s)

                # Partial match for longer names
                ps = fuzz.partial_ratio(token, name_lower) / 100.0
                best_score = max(best_score, ps)

            if best_score > 0.4:  # threshold
                scored.append((sym.id, sym.file_id, best_score))

    scored.sort(key=lambda x: -x[2])
    return scored[:top_k]
