"""Adaptive weight learner — learns optimal retrieval weights from user feedback."""

import json
import logging
from datetime import UTC, datetime

from repomemory.models.db import get_session
from repomemory.models.tables import LearnedWeights
from repomemory.retrieval.task_router import get_weights as get_static_weights

logger = logging.getLogger(__name__)

# Minimum interactions before using learned weights
MIN_SAMPLES = 20

# Learning rate for exponential moving average
EMA_ALPHA = 0.1

# Signal names
SIGNALS = ["lexical", "semantic", "path_match", "symbol_match", "memory_frecency", "git_recency", "dependency_graph"]

# Action type -> reward signal
ACTION_REWARDS = {
    "accepted": 1.0,
    "thumbs_up": 0.8,
    "selected": 0.5,
    "opened": 0.3,
    "dismissed": -0.3,
    "thumbs_down": -0.8,
}


def get_learned_weights(repo_id: int, mode: str) -> dict[str, float] | None:
    """Get learned weights for a repo+mode if sufficient data exists.

    Returns None if insufficient data, falling back to static weights.
    """
    with get_session() as session:
        record = (
            session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id, LearnedWeights.mode == mode).first()
        )
        if record and record.sample_count >= MIN_SAMPLES:
            try:
                return json.loads(record.weights_json)
            except (json.JSONDecodeError, TypeError):
                return None
    return None


def update_weights(
    repo_id: int,
    mode: str,
    component_scores: dict[str, float],
    action_type: str,
) -> None:
    """Update learned weights based on a user action.

    Uses EMA to adjust weights: if a user accepted a result,
    boost weights for the signals that contributed most.
    If dismissed/thumbs_down, reduce those signal weights.
    """
    reward = ACTION_REWARDS.get(action_type)
    if reward is None:
        return

    with get_session() as session:
        record = (
            session.query(LearnedWeights).filter(LearnedWeights.repo_id == repo_id, LearnedWeights.mode == mode).first()
        )

        if record:
            current_weights = json.loads(record.weights_json)
        else:
            # Start from static defaults
            current_weights = get_static_weights(mode)
            # Ensure dependency_graph signal exists
            if "dependency_graph" not in current_weights:
                current_weights["dependency_graph"] = 0.05

        # Compute weight update: signals that were high for this result get adjusted
        total_component = sum(abs(v) for v in component_scores.values()) or 1.0
        for signal in SIGNALS:
            if signal not in current_weights:
                current_weights[signal] = 0.05
            contribution = component_scores.get(signal, 0.0) / total_component
            # EMA update: move weight toward contribution * reward_direction
            delta = EMA_ALPHA * reward * contribution
            current_weights[signal] = max(0.01, current_weights[signal] + delta)

        # Normalize weights to sum to 1.0
        total = sum(current_weights.values())
        if total > 0:
            current_weights = {k: v / total for k, v in current_weights.items()}

        # Persist
        if record:
            record.weights_json = json.dumps(current_weights)
            record.sample_count += 1
            record.updated_at = datetime.now(UTC)
        else:
            record = LearnedWeights(
                repo_id=repo_id,
                mode=mode,
                weights_json=json.dumps(current_weights),
                sample_count=1,
            )
            session.add(record)

        session.commit()

    logger.debug(
        "Updated adaptive weights for repo=%d mode=%s (samples=%d)",
        repo_id,
        mode,
        record.sample_count,
    )


def get_adaptive_weights(repo_id: int, mode: str) -> dict[str, float]:
    """Get retrieval weights, preferring learned weights if available.

    Falls back to static weights + dependency_graph default.
    """
    learned = get_learned_weights(repo_id, mode)
    if learned:
        logger.info("Using learned weights for repo=%d mode=%s", repo_id, mode)
        return learned

    # Static defaults + dependency_graph signal
    weights = get_static_weights(mode)
    if "dependency_graph" not in weights:
        weights["dependency_graph"] = 0.05
        # Re-normalize
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}
    return weights
