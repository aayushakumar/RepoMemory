"""User action tracking and frecency scoring."""

import logging
from datetime import datetime, timezone

from sqlalchemy import func as sqlfunc

from repomemory.models.db import get_session
from repomemory.models.tables import Query, UserAction, File

logger = logging.getLogger(__name__)

ACTION_WEIGHTS = {
    "opened": 1.0,
    "selected": 2.0,
    "accepted": 3.0,
    "thumbs_up": 4.0,
    "thumbs_down": -3.0,
    "dismissed": -1.0,
}


def record_query(repo_id: int, query_text: str, mode: str) -> int:
    """Record a query and return its ID."""
    with get_session() as session:
        q = Query(repo_id=repo_id, text=query_text, mode=mode)
        session.add(q)
        session.commit()
        session.refresh(q)
        return q.id


def record_action(
    query_id: int,
    target_type: str,
    target_id: int,
    action_type: str,
) -> None:
    """Record a user action."""
    if action_type not in ACTION_WEIGHTS:
        logger.warning("Unknown action type: %s", action_type)
        return

    with get_session() as session:
        action = UserAction(
            query_id=query_id,
            target_type=target_type,
            target_id=target_id,
            action=action_type,
        )
        session.add(action)
        session.commit()


def get_memory_scores(
    repo_id: int,
    file_ids: list[int],
) -> dict[int, float]:
    """Compute frecency scores for given file IDs.
    Returns {file_id: normalized_score}.
    """
    if not file_ids:
        return {}

    now = datetime.now(timezone.utc)

    with get_session() as session:
        actions = (
            session.query(UserAction)
            .join(UserAction.query)
            .filter(Query.repo_id == repo_id)
            .filter(UserAction.target_type == "file")
            .filter(UserAction.target_id.in_(file_ids))
            .all()
        )

        scores: dict[int, float] = {}
        for action in actions:
            fid = action.target_id
            weight = ACTION_WEIGHTS.get(action.action, 0.0)
            days_since = (now - action.timestamp.replace(tzinfo=timezone.utc)).total_seconds() / 86400
            decay = 1.0 / (1.0 + days_since * 0.1)
            scores[fid] = scores.get(fid, 0.0) + weight * decay

    # Normalize to [0, 1]
    if scores:
        max_score = max(abs(v) for v in scores.values()) or 1.0
        scores = {k: max(0.0, v / max_score) for k, v in scores.items()}

    return scores


def get_memory_stats(repo_id: int) -> dict:
    """Get memory statistics for a repository."""
    with get_session() as session:
        total_queries = session.query(Query).filter(Query.repo_id == repo_id).count()
        total_actions = (
            session.query(UserAction)
            .join(UserAction.query)
            .filter(Query.repo_id == repo_id)
            .count()
        )

        # Top files by action count
        top_files_data = (
            session.query(
                UserAction.target_id,
                sqlfunc.count(UserAction.id).label("count"),
            )
            .join(UserAction.query)
            .filter(Query.repo_id == repo_id)
            .filter(UserAction.target_type == "file")
            .group_by(UserAction.target_id)
            .order_by(sqlfunc.count(UserAction.id).desc())
            .limit(10)
            .all()
        )

        top_files = []
        for fid, count in top_files_data:
            f = session.get(File, fid)
            top_files.append({
                "file_id": fid,
                "path": f.path if f else "unknown",
                "action_count": count,
            })

        # Recent queries
        recent = (
            session.query(Query)
            .filter(Query.repo_id == repo_id)
            .order_by(Query.timestamp.desc())
            .limit(20)
            .all()
        )
        recent_queries = [
            {"query_id": q.id, "text": q.text, "mode": q.mode, "timestamp": q.timestamp.isoformat()}
            for q in recent
        ]

    return {
        "total_queries": total_queries,
        "total_actions": total_actions,
        "top_files": top_files,
        "recent_queries": recent_queries,
    }


def clear_memory(repo_id: int) -> None:
    """Clear all memory (queries + actions) for a repository."""
    with get_session() as session:
        queries = session.query(Query).filter(Query.repo_id == repo_id).all()
        for q in queries:
            session.query(UserAction).filter(UserAction.query_id == q.id).delete()
        session.query(Query).filter(Query.repo_id == repo_id).delete()
        session.commit()
    logger.info("Cleared memory for repo %d", repo_id)
