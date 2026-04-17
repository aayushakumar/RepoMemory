"""Tests for the git cloner module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from repomemory.indexer.cloner import (
    _build_clone_url,
    clone_repo,
    delete_clone,
    extract_repo_name,
    is_git_url,
)


class TestIsGitUrl:
    def test_github_url(self):
        assert is_git_url("https://github.com/owner/repo")

    def test_github_url_with_git(self):
        assert is_git_url("https://github.com/owner/repo.git")

    def test_gitlab_url(self):
        assert is_git_url("https://gitlab.com/owner/repo")

    def test_bitbucket_url(self):
        assert is_git_url("https://bitbucket.org/owner/repo")

    def test_local_path_not_url(self):
        assert not is_git_url("/home/user/myrepo")

    def test_random_https_not_url(self):
        assert not is_git_url("https://example.com/not-a-repo")

    def test_empty(self):
        assert not is_git_url("")

    def test_trailing_slash(self):
        assert is_git_url("https://github.com/owner/repo/")


class TestExtractRepoName:
    def test_simple(self):
        assert extract_repo_name("https://github.com/owner/my-repo") == "my-repo"

    def test_with_git_suffix(self):
        assert extract_repo_name("https://github.com/owner/my-repo.git") == "my-repo"

    def test_trailing_slash(self):
        assert extract_repo_name("https://github.com/owner/my-repo/") == "my-repo"


class TestBuildCloneUrl:
    def test_without_token(self):
        url = _build_clone_url("https://github.com/owner/repo")
        assert url == "https://github.com/owner/repo.git"

    def test_with_token(self):
        url = _build_clone_url("https://github.com/owner/repo", token="ghp_abc123")
        assert "ghp_abc123@github.com" in url
        assert url.endswith(".git")

    def test_already_has_git_suffix(self):
        url = _build_clone_url("https://github.com/owner/repo.git")
        assert url == "https://github.com/owner/repo.git"


class TestCloneRepo:
    @patch("git.Repo")
    def test_clone_success(self, mock_repo_cls, tmp_path):
        from repomemory.config import settings

        settings.clone_dir = tmp_path / "repos"

        # Mock clone_from to create the directory
        def fake_clone(url, path, **kwargs):
            p = Path(path)
            p.mkdir(parents=True, exist_ok=True)
            (p / "README.md").write_text("hello")
            return MagicMock()

        mock_repo_cls.clone_from.side_effect = fake_clone

        result = clone_repo("https://github.com/owner/repo", repo_id=1)
        assert result.exists()

        mock_repo_cls.clone_from.assert_called_once()
        call_kwargs = mock_repo_cls.clone_from.call_args
        assert call_kwargs.kwargs["depth"] == 1

        # Cleanup
        settings.clone_dir = None

    def test_clone_invalid_url(self):
        with pytest.raises(ValueError, match="Invalid Git URL"):
            clone_repo("/not/a/url", repo_id=1)

    @patch("git.Repo")
    def test_clone_strips_token_from_error(self, mock_repo_cls, tmp_path):
        import git as gitmodule

        from repomemory.config import settings

        settings.clone_dir = tmp_path / "repos"

        mock_repo_cls.clone_from.side_effect = gitmodule.GitCommandError("clone", "secret_token failed")

        with pytest.raises(RuntimeError) as exc_info:
            clone_repo("https://github.com/owner/repo", repo_id=1, token="secret_token")

        assert "secret_token" not in str(exc_info.value)
        settings.clone_dir = None


class TestDeleteClone:
    def test_delete_existing(self, tmp_path):
        from repomemory.config import settings

        settings.clone_dir = tmp_path / "repos"

        clone_path = tmp_path / "repos" / "repo_1"
        clone_path.mkdir(parents=True)
        (clone_path / "file.txt").write_text("test")

        delete_clone(1)
        assert not clone_path.exists()

        settings.clone_dir = None

    def test_delete_nonexistent_is_noop(self, tmp_path):
        from repomemory.config import settings

        settings.clone_dir = tmp_path / "repos"
        (tmp_path / "repos").mkdir(parents=True, exist_ok=True)

        delete_clone(999)  # should not raise

        settings.clone_dir = None
