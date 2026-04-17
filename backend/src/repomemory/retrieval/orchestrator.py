"""Retrieval orchestrator — coordinates all retrieval strategies."""

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from repomemory.memory.tracker import get_memory_scores
from repomemory.retrieval.combiner import RankedResult, combine_results
from repomemory.retrieval.graph import graph_search
from repomemory.retrieval.lexical import lexical_search
from repomemory.retrieval.path import path_search
from repomemory.retrieval.semantic import semantic_search
from repomemory.retrieval.symbol import symbol_search
from repomemory.retrieval.task_router import classify_task
from repomemory.retrieval.weight_learner import get_adaptive_weights

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    ranked_results: list[RankedResult]
    classified_mode: str


def retrieve(
    query: str,
    repo_id: int,
    mode: str | None = None,
    top_k: int = 20,
) -> RetrievalResult:
    """Main retrieval entry point. Runs all retrievers and combines results."""

    # Classify task mode
    classified_mode = mode if mode and mode != "auto" else classify_task(query)
    # Use adaptive weights (learned if available, else static + dependency_graph)
    weights = get_adaptive_weights(repo_id, classified_mode)

    # Run retrievers in parallel
    with ThreadPoolExecutor(max_workers=4) as executor:
        lex_future = executor.submit(lexical_search, query, repo_id, top_k=50)
        sem_future = executor.submit(semantic_search, query, repo_id, top_k=50)
        path_future = executor.submit(path_search, query, repo_id, top_k=50)
        sym_future = executor.submit(symbol_search, query, repo_id, top_k=50)

        lexical_results = lex_future.result()
        semantic_results = sem_future.result()
        path_results = path_future.result()
        symbol_results = sym_future.result()

    # Get memory scores
    all_file_ids = set()
    # Collect file_ids from results (will be resolved in combine_results)
    memory_scores = get_memory_scores(repo_id, list(all_file_ids))

    # First pass: combine without graph to identify seed files
    ranked_initial = combine_results(
        lexical_results=lexical_results,
        semantic_results=semantic_results,
        path_results=path_results,
        symbol_results=symbol_results,
        memory_scores=memory_scores,
        weights=weights,
        repo_id=repo_id,
        top_k=top_k,
    )

    # Graph search: boost files connected to top results via dependency graph
    seed_file_ids = {r.file_id for r in ranked_initial[:5]}
    graph_scores = graph_search(seed_file_ids, repo_id, max_hops=2)

    # Final combine with graph scores
    ranked = combine_results(
        lexical_results=lexical_results,
        semantic_results=semantic_results,
        path_results=path_results,
        symbol_results=symbol_results,
        memory_scores=memory_scores,
        weights=weights,
        repo_id=repo_id,
        top_k=top_k,
        graph_scores=graph_scores,
    )

    # Generate explanations and load snippets
    from repomemory.context.explainer import explain_results

    ranked = explain_results(ranked, query)
    ranked = _load_snippets(ranked)

    return RetrievalResult(
        ranked_results=ranked,
        classified_mode=classified_mode,
    )


def _load_snippets(ranked: list[RankedResult]) -> list[RankedResult]:
    """Load snippet content for each ranked result."""
    from repomemory.models.db import get_session
    from repomemory.models.tables import Chunk

    if not ranked:
        return ranked

    all_chunk_ids = set()
    for r in ranked:
        all_chunk_ids.update(r.chunk_ids)

    if not all_chunk_ids:
        return ranked

    with get_session() as session:
        chunks = session.query(Chunk).filter(Chunk.id.in_(all_chunk_ids)).all()
        chunk_map = {c.id: c for c in chunks}

    for r in ranked:
        r.snippets = []
        # Take top 3 chunks for this file by relevance
        for cid in r.chunk_ids[:3]:
            c = chunk_map.get(cid)
            if c:
                r.snippets.append(
                    {
                        "content": c.content,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "symbol_name": None,
                        "token_count": c.token_count,
                    }
                )

    return ranked
