"""Semantic search using FAISS."""

import logging

import numpy as np

from repomemory.indexer.embedder import encode_query, load_faiss_index

logger = logging.getLogger(__name__)

# Cache loaded indices
_index_cache: dict[int, tuple] = {}


def invalidate_cache(repo_id: int):
    _index_cache.pop(repo_id, None)


def semantic_search(
    query: str,
    repo_id: int,
    top_k: int = 50,
) -> list[tuple[int, float]]:
    """Search using FAISS nearest neighbors. Returns list of (chunk_id, similarity_score)."""
    if repo_id not in _index_cache:
        result = load_faiss_index(repo_id)
        if result is None:
            logger.warning("No FAISS index for repo %d", repo_id)
            return []
        _index_cache[repo_id] = result

    index, mapping = _index_cache[repo_id]

    query_vec = encode_query(query)
    k = min(top_k, index.ntotal)
    if k == 0:
        return []

    distances, indices = index.search(query_vec, k)

    results = []
    for i, idx in enumerate(indices[0]):
        if idx == -1:
            continue
        chunk_id = mapping.get(int(idx))
        if chunk_id is not None:
            score = float(distances[0][i])
            # Clamp to [0, 1] — cosine similarity after normalization
            score = max(0.0, min(1.0, score))
            results.append((chunk_id, score))

    return results
