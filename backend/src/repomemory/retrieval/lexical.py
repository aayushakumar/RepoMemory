"""Lexical search using BM25."""

import logging

from rank_bm25 import BM25Okapi

from repomemory.models.db import get_session
from repomemory.models.tables import Chunk, File

logger = logging.getLogger(__name__)

# Cache BM25 index per repo
_bm25_cache: dict[int, tuple[BM25Okapi, list[int]]] = {}


def _tokenize(text: str) -> list[str]:
    return text.lower().split()


def _build_bm25_index(repo_id: int) -> tuple[BM25Okapi, list[int]]:
    with get_session() as session:
        chunks = session.query(Chunk).join(Chunk.file).filter(File.repo_id == repo_id).order_by(Chunk.id).all()
        chunk_ids = [c.id for c in chunks]
        corpus = [_tokenize(c.content) for c in chunks]

    if not corpus:
        return BM25Okapi([[""]]), []

    bm25 = BM25Okapi(corpus)
    return bm25, chunk_ids


def invalidate_cache(repo_id: int):
    _bm25_cache.pop(repo_id, None)


def lexical_search(
    query: str,
    repo_id: int,
    top_k: int = 50,
) -> list[tuple[int, float]]:
    """Search using BM25. Returns list of (chunk_id, normalized_score)."""
    if repo_id not in _bm25_cache:
        _bm25_cache[repo_id] = _build_bm25_index(repo_id)

    bm25, chunk_ids = _bm25_cache[repo_id]
    if not chunk_ids:
        return []

    tokens = _tokenize(query)
    scores = bm25.get_scores(tokens)

    max_score = max(scores) if max(scores) > 0 else 1.0
    scored = [(chunk_ids[i], float(scores[i] / max_score)) for i in range(len(chunk_ids))]
    scored.sort(key=lambda x: -x[1])

    return scored[:top_k]
