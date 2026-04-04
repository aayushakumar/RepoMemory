"""Tests for evaluation metrics."""

from repomemory.evaluation.metrics import (
    recall_at_k,
    precision_at_k,
    mrr,
    average_precision,
    ndcg_at_k,
)


def test_recall_at_k():
    retrieved = ["a.py", "b.py", "c.py", "d.py", "e.py"]
    expected = ["b.py", "d.py"]
    assert recall_at_k(retrieved, expected, 1) == 0.0
    assert recall_at_k(retrieved, expected, 2) == 0.5
    assert recall_at_k(retrieved, expected, 5) == 1.0


def test_recall_empty_expected():
    assert recall_at_k(["a.py"], [], 5) == 1.0


def test_precision_at_k():
    retrieved = ["a.py", "b.py", "c.py", "d.py", "e.py"]
    expected = ["b.py", "d.py"]
    assert precision_at_k(retrieved, expected, 5) == 0.4
    assert precision_at_k(retrieved, expected, 2) == 0.5


def test_mrr():
    retrieved = ["a.py", "b.py", "c.py"]
    assert mrr(retrieved, ["a.py"]) == 1.0
    assert mrr(retrieved, ["b.py"]) == 0.5
    assert mrr(retrieved, ["c.py"]) == 1 / 3
    assert mrr(retrieved, ["x.py"]) == 0.0


def test_average_precision():
    retrieved = ["a.py", "b.py", "c.py"]
    expected = ["a.py", "c.py"]
    # AP = (1/1 + 2/3) / 2 = 0.833...
    ap = average_precision(retrieved, expected)
    assert abs(ap - 5 / 6) < 1e-9


def test_ndcg_at_k():
    import math

    retrieved = ["a.py", "b.py", "c.py"]
    expected = ["a.py", "c.py"]
    # DCG = 1/log2(2) + 1/log2(4) = 1 + 0.5 = 1.5
    # IDCG = 1/log2(2) + 1/log2(3)
    dcg = 1 / math.log2(2) + 1 / math.log2(4)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    expected_ndcg = dcg / idcg
    assert abs(ndcg_at_k(retrieved, expected, 3) - expected_ndcg) < 1e-9
