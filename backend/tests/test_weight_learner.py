"""Tests for the adaptive weight learner."""

import json

from repomemory.models.db import get_session
from repomemory.models.tables import LearnedWeights, Repository
from repomemory.retrieval.weight_learner import (
    MIN_SAMPLES,
    SIGNALS,
    get_adaptive_weights,
    get_learned_weights,
    update_weights,
)


def _create_repo(name: str = "test_repo") -> int:
    with get_session() as session:
        repo = Repository(path=f"/tmp/{name}", name=name, status="ready")
        session.add(repo)
        session.commit()
        session.refresh(repo)
        return repo.id


# ---------- get_learned_weights ----------


def test_get_learned_weights_returns_none_when_empty(test_db):
    repo_id = _create_repo()
    assert get_learned_weights(repo_id, "general") is None


def test_get_learned_weights_returns_none_when_insufficient_samples(test_db):
    repo_id = _create_repo()
    with get_session() as session:
        record = LearnedWeights(
            repo_id=repo_id,
            mode="general",
            weights_json=json.dumps({"lexical": 0.5, "semantic": 0.5}),
            sample_count=MIN_SAMPLES - 1,
        )
        session.add(record)
        session.commit()

    assert get_learned_weights(repo_id, "general") is None


def test_get_learned_weights_returns_weights_when_sufficient(test_db):
    repo_id = _create_repo()
    weights = {"lexical": 0.3, "semantic": 0.7}
    with get_session() as session:
        record = LearnedWeights(
            repo_id=repo_id,
            mode="general",
            weights_json=json.dumps(weights),
            sample_count=MIN_SAMPLES,
        )
        session.add(record)
        session.commit()

    result = get_learned_weights(repo_id, "general")
    assert result is not None
    assert abs(result["lexical"] - 0.3) < 1e-6


# ---------- update_weights ----------


def test_update_weights_creates_new_record(test_db):
    repo_id = _create_repo()
    scores = {"lexical": 0.8, "semantic": 0.2, "path_match": 0.0}
    update_weights(repo_id, "general", scores, "accepted")

    with get_session() as session:
        record = session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id).first()
        assert record is not None
        assert record.sample_count == 1
        stored = json.loads(record.weights_json)
        # Weights should sum to ~1.0
        assert abs(sum(stored.values()) - 1.0) < 1e-6


def test_update_weights_increments_sample_count(test_db):
    repo_id = _create_repo()
    scores = {"lexical": 0.5, "semantic": 0.5}
    update_weights(repo_id, "general", scores, "accepted")
    update_weights(repo_id, "general", scores, "selected")

    with get_session() as session:
        record = session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id).first()
        assert record.sample_count == 2


def test_update_weights_ignores_unknown_action(test_db):
    repo_id = _create_repo()
    update_weights(repo_id, "general", {"lexical": 1.0}, "unknown_action")

    with get_session() as session:
        count = session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id).count()
        assert count == 0


def test_update_weights_negative_reward(test_db):
    repo_id = _create_repo()
    scores = {"lexical": 0.9, "semantic": 0.1}
    update_weights(repo_id, "general", scores, "thumbs_down")

    with get_session() as session:
        record = session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id).first()
        assert record is not None
        stored = json.loads(record.weights_json)
        # All weights should still be > 0 (clamped at 0.01)
        assert all(v >= 0.01 for v in stored.values())


# ---------- get_adaptive_weights ----------


def test_get_adaptive_weights_falls_back_to_static(test_db):
    repo_id = _create_repo()
    weights = get_adaptive_weights(repo_id, "general")
    assert isinstance(weights, dict)
    assert "lexical" in weights
    assert "semantic" in weights
    assert "dependency_graph" in weights
    assert abs(sum(weights.values()) - 1.0) < 0.01


def test_get_adaptive_weights_uses_learned_when_available(test_db):
    repo_id = _create_repo()
    learned = {s: 1.0 / len(SIGNALS) for s in SIGNALS}
    with get_session() as session:
        record = LearnedWeights(
            repo_id=repo_id,
            mode="general",
            weights_json=json.dumps(learned),
            sample_count=MIN_SAMPLES,
        )
        session.add(record)
        session.commit()

    result = get_adaptive_weights(repo_id, "general")
    # Should use learned weights, not static
    expected = 1.0 / len(SIGNALS)
    assert abs(result["lexical"] - expected) < 1e-6


def test_signals_constant_has_all_expected():
    """Verify SIGNALS list is complete."""
    expected = {
        "lexical",
        "semantic",
        "path_match",
        "symbol_match",
        "memory_frecency",
        "git_recency",
        "dependency_graph",
    }
    assert set(SIGNALS) == expected
