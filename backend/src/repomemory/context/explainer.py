"""Relevance explanation generator — template-based explanations for search results."""

from repomemory.retrieval.combiner import RankedResult

SCORE_THRESHOLDS = {
    "lexical": 0.005,
    "semantic": 0.005,
    "path_match": 0.005,
    "symbol_match": 0.005,
    "memory_frecency": 0.005,
    "git_recency": 0.005,
}

EXPLANATION_TEMPLATES = {
    "lexical": "High lexical match for query terms",
    "semantic": "Semantically similar to query",
    "path_match": "File path matches query pattern",
    "symbol_match": "Contains symbols matching query",
    "memory_frecency": "Frequently accessed for similar queries",
    "git_recency": "Recently modified",
}


def _explain_single(result: RankedResult, query: str) -> str:
    """Generate explanation string for a single ranked result."""
    reasons = []

    for component, threshold in SCORE_THRESHOLDS.items():
        score = result.component_scores.get(component, 0.0)
        if score > threshold:
            reasons.append(EXPLANATION_TEMPLATES[component])

    if not reasons:
        reasons.append("Relevant to query")

    return "; ".join(reasons)


def explain_results(ranked: list[RankedResult], query: str) -> list[RankedResult]:
    """Add explanation strings to all ranked results."""
    for result in ranked:
        result.explanation = _explain_single(result, query)
    return ranked
