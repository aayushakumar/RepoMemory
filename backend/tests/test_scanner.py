"""Tests for repository scanner."""

from pathlib import Path

from repomemory.indexer.scanner import scan_repository

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def test_scan_finds_python_files(test_db):
    results = scan_repository(SAMPLE_REPO)
    py_files = [f for f in results if f.extension == ".py"]
    assert len(py_files) >= 5  # auth/, routes/, models/, config/, tests/


def test_scan_finds_js_ts_files(test_db):
    results = scan_repository(SAMPLE_REPO)
    js_files = [f for f in results if f.extension in (".js", ".ts")]
    assert len(js_files) >= 2  # helpers.js, api_client.ts


def test_scan_includes_relative_paths(test_db):
    results = scan_repository(SAMPLE_REPO)
    paths = {f.relative_path for f in results}
    assert "auth/token_handler.py" in paths
    assert "routes/api.py" in paths


def test_scan_computes_content_hash(test_db):
    results = scan_repository(SAMPLE_REPO)
    for f in results:
        assert len(f.content_hash) == 64  # SHA256 hex


def test_scan_respects_gitignore(test_db):
    results = scan_repository(SAMPLE_REPO)
    paths = {f.relative_path for f in results}
    # .gitignore should exclude these patterns
    for p in paths:
        assert "node_modules" not in p
        assert "__pycache__" not in p
