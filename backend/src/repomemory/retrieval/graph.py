"""Graph-based retrieval — boosts files connected via dependency graph."""

import logging

from repomemory.indexer.dependency_graph import get_connected_files

logger = logging.getLogger(__name__)


def graph_search(
    seed_file_ids: set[int],
    repo_id: int,
    max_hops: int = 2,
) -> dict[int, float]:
    """Find files connected to seed files via the dependency graph.

    Returns {file_id: score} for connected (non-seed) files.
    Score decays with graph distance.
    """
    if not seed_file_ids:
        return {}

    scores = get_connected_files(repo_id, seed_file_ids, max_hops=max_hops)

    if scores:
        logger.info(
            "Graph search found %d connected files from %d seeds",
            len(scores),
            len(seed_file_ids),
        )

    return scores
