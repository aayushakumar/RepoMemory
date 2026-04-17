"""Tests for the RAG quality evaluator."""

import yaml

from repomemory.evaluation.rag_evaluator import (
    RAGQueryCase,
    _compute_keyword_recall,
    _heuristic_judge,
    load_rag_query_set,
)

# ---------- load_rag_query_set ----------


def test_load_rag_query_set(tmp_path):
    qs = tmp_path / "queries.yaml"
    qs.write_text(
        yaml.dump(
            {
                "rag_queries": [
                    {
                        "query": "How does auth work?",
                        "expected_keywords": ["token", "session"],
                        "expected_files": ["auth/login.py"],
                        "description": "Test query",
                    },
                    {
                        "query": "Database schema",
                        "expected_keywords": ["table"],
                    },
                ]
            }
        )
    )

    cases = load_rag_query_set(qs)
    assert len(cases) == 2
    assert cases[0].query == "How does auth work?"
    assert cases[0].expected_answer_keywords == ["token", "session"]
    assert cases[0].expected_files == ["auth/login.py"]
    assert cases[1].expected_files == []


def test_load_rag_query_set_empty(tmp_path):
    qs = tmp_path / "empty.yaml"
    qs.write_text(yaml.dump({"rag_queries": []}))
    cases = load_rag_query_set(qs)
    assert cases == []


# ---------- _compute_keyword_recall ----------


def test_keyword_recall_all_present():
    assert _compute_keyword_recall("The token is stored in session", ["token", "session"]) == 1.0


def test_keyword_recall_partial():
    assert _compute_keyword_recall("The token is valid", ["token", "session"]) == 0.5


def test_keyword_recall_none_present():
    assert _compute_keyword_recall("Hello world", ["token", "session"]) == 0.0


def test_keyword_recall_empty_keywords():
    assert _compute_keyword_recall("any text", []) == 1.0


def test_keyword_recall_case_insensitive():
    assert _compute_keyword_recall("The TOKEN is here", ["token"]) == 1.0


# ---------- _heuristic_judge ----------


def test_heuristic_judge_returns_three_scores():
    scores = _heuristic_judge("how does auth work", "The authentication module handles login and auth flow")
    assert "relevance" in scores
    assert "completeness" in scores
    assert "faithfulness" in scores
    # All scores between 1 and 5
    for v in scores.values():
        assert 1.0 <= v <= 5.0


def test_heuristic_judge_higher_overlap_gives_higher_relevance():
    low = _heuristic_judge("authentication login flow", "weather forecast for tomorrow")
    high = _heuristic_judge("authentication login flow", "the authentication handles login flow")
    assert high["relevance"] >= low["relevance"]


def test_heuristic_judge_longer_answer_gets_higher_completeness():
    short = _heuristic_judge("explain auth", "auth module")
    long_text = "The authentication module is responsible for " + "validating user credentials " * 10
    long = _heuristic_judge("explain auth", long_text)
    assert long["completeness"] >= short["completeness"]


def test_heuristic_faithfulness_is_neutral():
    # Without LLM, faithfulness is always 3.0
    scores = _heuristic_judge("any query", "any answer")
    assert scores["faithfulness"] == 3.0


# ---------- RAGQueryCase ----------


def test_rag_query_case_defaults():
    case = RAGQueryCase(query="test", expected_answer_keywords=["foo"])
    assert case.expected_files == []
    assert case.description == ""
