"""Relevance explanation generator — template-based with optional LLM enhancement."""

import logging

from repomemory.retrieval.combiner import RankedResult

logger = logging.getLogger(__name__)

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


def _template_explain(result: RankedResult, query: str) -> str:
    """Generate template-based explanation string for a single ranked result."""
    reasons = []

    for component, threshold in SCORE_THRESHOLDS.items():
        score = result.component_scores.get(component, 0.0)
        if score > threshold:
            reasons.append(EXPLANATION_TEMPLATES[component])

    if not reasons:
        reasons.append("Relevant to query")

    return "; ".join(reasons)


def _llm_explain(result: RankedResult, query: str) -> str | None:
    """Try to use LLM for a richer explanation. Returns None to fall back to templates."""
    try:
        from repomemory.context.llm import explain_code

        # Use the first snippet if available
        snippet_content = ""
        if hasattr(result, "snippets") and result.snippets:
            snippet_content = result.snippets[0].content[:1000]
        elif hasattr(result, "_snippet_cache") and result._snippet_cache:
            snippet_content = result._snippet_cache[:1000]

        if not snippet_content:
            return None

        return explain_code(query, snippet_content, result.file_path)
    except Exception as e:
        logger.debug("LLM explain failed, falling back to template: %s", e)
        return None


def explain_results(ranked: list[RankedResult], query: str) -> list[RankedResult]:
    """Add explanation strings to all ranked results.

    Uses LLM for top-3 results if enabled, templates for the rest.
    """
    from repomemory.config import settings

    for i, result in enumerate(ranked):
        explanation = None

        # Use LLM for top 3 results only (rate-limit friendly)
        if settings.llm_enabled and i < 3:
            explanation = _llm_explain(result, query)

        if not explanation:
            explanation = _template_explain(result, query)

        result.explanation = explanation

    return ranked
