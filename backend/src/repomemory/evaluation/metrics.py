"""Evaluation metrics for retrieval quality."""

from __future__ import annotations


def recall_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    """Fraction of expected files found in the top-k retrieved results."""
    if not expected:
        return 1.0
    top_k = set(retrieved[:k])
    hits = sum(1 for e in expected if e in top_k)
    return hits / len(expected)


def precision_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    """Fraction of top-k retrieved results that are in the expected set."""
    top_k = retrieved[:k]
    if not top_k:
        return 0.0
    hits = sum(1 for r in top_k if r in set(expected))
    return hits / len(top_k)


def mrr(retrieved: list[str], expected: list[str]) -> float:
    """Mean Reciprocal Rank — 1/(rank of first expected file found)."""
    expected_set = set(expected)
    for i, r in enumerate(retrieved):
        if r in expected_set:
            return 1.0 / (i + 1)
    return 0.0


def average_precision(retrieved: list[str], expected: list[str]) -> float:
    """Average precision for a single query."""
    if not expected:
        return 1.0
    expected_set = set(expected)
    hits = 0
    score = 0.0
    for i, r in enumerate(retrieved):
        if r in expected_set:
            hits += 1
            score += hits / (i + 1)
    return score / len(expected) if expected else 0.0


def ndcg_at_k(retrieved: list[str], expected: list[str], k: int) -> float:
    """Normalized Discounted Cumulative Gain at k."""
    import math

    expected_set = set(expected)
    dcg = 0.0
    for i, r in enumerate(retrieved[:k]):
        if r in expected_set:
            dcg += 1.0 / math.log2(i + 2)  # +2 because 1-indexed

    # Ideal DCG: all expected files at top
    ideal_k = min(len(expected), k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_k))
    return dcg / idcg if idcg > 0 else 0.0
