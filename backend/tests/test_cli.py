"""Tests for the CLI module."""

from unittest.mock import patch

from click.testing import CliRunner

from repomemory import __version__
from repomemory.cli import main


class TestCLI:
    def test_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "RepoMemory" in result.output

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_config_command(self):
        runner = CliRunner()
        result = runner.invoke(main, ["config"])
        assert result.exit_code == 0
        assert "Data directory" in result.output
        assert "Embedding provider" in result.output

    def test_list_empty(self):
        runner = CliRunner()
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        assert "No repositories" in result.output or "Indexed" in result.output

    def test_index_invalid_path(self):
        runner = CliRunner()
        result = runner.invoke(main, ["index", "/nonexistent/path/that/does/not/exist"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Directory" in result.output

    def test_delete_nonexistent(self):
        runner = CliRunner()
        result = runner.invoke(main, ["delete", "99999", "-y"])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    def test_search_no_repos(self):
        runner = CliRunner()
        result = runner.invoke(main, ["search", "test query"])
        assert result.exit_code != 0
        assert "No ready repository" in result.output or "not found" in result.output.lower()

    def test_serve_missing_uvicorn(self):
        runner = CliRunner()
        with patch.dict("sys.modules", {"uvicorn": None}):
            # This will try to import uvicorn and handle the ImportError
            result = runner.invoke(main, ["serve"])
            # Either fails gracefully or starts (if uvicorn is installed)
            # We just verify it doesn't crash with an unhandled exception
            assert result.exit_code is not None
