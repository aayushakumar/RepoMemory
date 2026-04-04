"""Tests for the retrieval pipeline."""

from pathlib import Path

from repomemory.indexer.orchestrator import index_repository
from repomemory.models.db import get_session
from repomemory.models.tables import Repository
from repomemory.retrieval.task_router import classify_task

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def _create_and_index_repo(test_db) -> int:
    """Helper to create and index the sample repo."""
    with get_session() as session:
        repo = Repository(path=str(SAMPLE_REPO.resolve()), name="sample_repo", status="indexing")
        session.add(repo)
        session.commit()
        session.refresh(repo)
        repo_id = repo.id

    index_repository(repo_id, str(SAMPLE_REPO.resolve()), force=True)
    return repo_id


def test_task_router_bug_fix():
    assert classify_task("fix the authentication error in login") == "bug_fix"


def test_task_router_trace_flow():
    assert classify_task("trace the login API from route to database") == "trace_flow"


def test_task_router_test_lookup():
    assert classify_task("find unit test for the token rotation feature") == "test_lookup"


def test_task_router_config():
    assert classify_task("where is the JWT expiry config setting?") == "config_lookup"


def test_task_router_general():
    assert classify_task("explain user registration logic") == "general"


def test_end_to_end_search(test_db):
    """Full indexing + retrieval pipeline test."""
    repo_id = _create_and_index_repo(test_db)

    from repomemory.retrieval.orchestrator import retrieve

    result = retrieve("token rotation authentication", repo_id)
    assert len(result.ranked_results) > 0

    # The auth/token_handler.py should rank highly
    paths = [r.file_path for r in result.ranked_results]
    assert any("token_handler" in p for p in paths)


def test_search_returns_snippets(test_db):
    repo_id = _create_and_index_repo(test_db)

    from repomemory.retrieval.orchestrator import retrieve

    result = retrieve("database operations", repo_id)
    assert len(result.ranked_results) > 0
    # At least some results should have snippets
    has_snippets = any(len(r.snippets) > 0 for r in result.ranked_results)
    assert has_snippets
