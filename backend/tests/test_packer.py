"""Tests for context pack builder."""

from repomemory.context.packer import build_context_pack, export_as_markdown
from repomemory.retrieval.combiner import RankedResult


def _make_mock_results() -> list[RankedResult]:
    return [
        RankedResult(
            file_id=1,
            file_path="auth/token_handler.py",
            chunk_ids=[1, 2],
            symbol_ids=[1],
            combined_score=0.92,
            component_scores={
                "lexical": 0.8,
                "semantic": 0.7,
                "path_match": 0.3,
                "symbol_match": 0.6,
                "memory_frecency": 0.0,
                "git_recency": 0.0,
                "dependency_graph": 0.0,
            },
            explanation="High lexical match; contains rotate_token() symbol",
            snippets=[
                {
                    "content": "def rotate_token(self, old_token: str) -> str:\n    ...\n",
                    "start_line": 35,
                    "end_line": 45,
                    "symbol_name": "rotate_token",
                    "token_count": 30,
                },
                {
                    "content": "def validate_token(self, token: str) -> dict:\n    ...\n",
                    "start_line": 20,
                    "end_line": 34,
                    "symbol_name": "validate_token",
                    "token_count": 40,
                },
            ],
        ),
        RankedResult(
            file_id=2,
            file_path="tests/test_auth.py",
            chunk_ids=[3],
            symbol_ids=[],
            combined_score=0.78,
            component_scores={
                "lexical": 0.5,
                "semantic": 0.6,
                "path_match": 0.4,
                "symbol_match": 0.0,
                "memory_frecency": 0.0,
                "git_recency": 0.0,
                "dependency_graph": 0.0,
            },
            explanation="Test file for auth module",
            snippets=[
                {
                    "content": "def test_rotate_token():\n    ...\n",
                    "start_line": 30,
                    "end_line": 40,
                    "symbol_name": "test_rotate_token",
                    "token_count": 25,
                },
            ],
        ),
    ]


def test_pack_respects_budget():
    results = _make_mock_results()
    pack = build_context_pack(results, "token rotation", "bug_fix", budget=50)
    assert pack.total_tokens <= 50


def test_pack_includes_files():
    results = _make_mock_results()
    pack = build_context_pack(results, "token rotation", "bug_fix", budget=8000)
    assert len(pack.files) > 0
    assert pack.files[0].path == "auth/token_handler.py"


def test_pack_budget_percentage():
    results = _make_mock_results()
    pack = build_context_pack(results, "token rotation", "bug_fix", budget=8000)
    assert 0 <= pack.budget_used_pct <= 100


def test_export_markdown():
    results = _make_mock_results()
    pack = build_context_pack(results, "token rotation", "bug_fix", budget=8000)
    md = export_as_markdown(pack)
    assert "token rotation" in md
    assert "auth/token_handler.py" in md
    assert "score:" in md
