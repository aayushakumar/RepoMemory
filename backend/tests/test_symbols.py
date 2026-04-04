"""Tests for symbol extraction."""

from pathlib import Path

from repomemory.indexer.symbols import extract_symbols_from_file

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


def test_extract_python_functions():
    filepath = SAMPLE_REPO / "auth" / "token_handler.py"
    symbols = extract_symbols_from_file(filepath, ".py")
    names = [s.name for s in symbols]
    assert "TokenManager" in names
    assert "hash_password" in names
    assert "verify_password" in names


def test_extract_python_classes_with_methods():
    filepath = SAMPLE_REPO / "auth" / "token_handler.py"
    symbols = extract_symbols_from_file(filepath, ".py")
    cls = [s for s in symbols if s.name == "TokenManager"][0]
    assert cls.kind == "class"
    method_names = [m.name for m in cls.children]
    assert "create_token" in method_names
    assert "validate_token" in method_names
    assert "rotate_token" in method_names


def test_extract_js_functions():
    filepath = SAMPLE_REPO / "utils" / "helpers.js"
    symbols = extract_symbols_from_file(filepath, ".js")
    names = [s.name for s in symbols]
    assert "formatDate" in names or "EventEmitter" in names


def test_extract_ts_classes():
    filepath = SAMPLE_REPO / "services" / "api_client.ts"
    symbols = extract_symbols_from_file(filepath, ".ts")
    names = [s.name for s in symbols]
    assert "ApiClient" in names


def test_extract_handles_imports():
    filepath = SAMPLE_REPO / "auth" / "token_handler.py"
    symbols = extract_symbols_from_file(filepath, ".py")
    imports = [s for s in symbols if s.kind == "import"]
    assert len(imports) > 0


def test_extract_unsupported_extension():
    filepath = SAMPLE_REPO / "README.md"
    symbols = extract_symbols_from_file(filepath, ".md")
    assert symbols == []
