"""Tests for the LLM integration module."""

from unittest.mock import MagicMock, patch


class TestExplainCode:
    @patch("repomemory.context.llm.settings")
    def test_returns_none_when_disabled(self, mock_settings):
        mock_settings.llm_enabled = False
        from repomemory.context.llm import explain_code

        result = explain_code("test query", "def foo(): pass", "test.py")
        assert result is None

    @patch("repomemory.context.llm._get_client")
    @patch("repomemory.context.llm.settings")
    def test_returns_explanation_on_success(self, mock_settings, mock_get_client):
        mock_settings.llm_enabled = True
        mock_settings.groq_model = "test-model"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "This function handles auth."
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        from repomemory.context.llm import explain_code

        result = explain_code("how does auth work", "def authenticate(): pass", "auth.py")
        assert result == "This function handles auth."

    @patch("repomemory.context.llm._get_client")
    @patch("repomemory.context.llm.settings")
    def test_returns_none_on_api_error(self, mock_settings, mock_get_client):
        mock_settings.llm_enabled = True
        mock_settings.groq_model = "test-model"

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_get_client.return_value = mock_client

        from repomemory.context.llm import explain_code

        result = explain_code("test", "code", "file.py")
        assert result is None

    @patch("repomemory.context.llm._get_client")
    @patch("repomemory.context.llm.settings")
    def test_returns_none_when_no_client(self, mock_settings, mock_get_client):
        mock_settings.llm_enabled = True
        mock_get_client.return_value = None

        from repomemory.context.llm import explain_code

        result = explain_code("test", "code", "file.py")
        assert result is None


class TestSummarizeContext:
    @patch("repomemory.context.llm._get_client")
    @patch("repomemory.context.llm.settings")
    def test_returns_summary(self, mock_settings, mock_get_client):
        mock_settings.llm_enabled = True
        mock_settings.groq_model = "test-model"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "The auth module handles user login."
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_client.return_value = mock_client

        from repomemory.context.llm import summarize_context

        files = [{"path": "auth.py", "relevance_score": 0.9, "snippets": [{"content": "def login()"}]}]
        result = summarize_context("how does login work", files)
        assert "auth" in result.lower()

    @patch("repomemory.context.llm.settings")
    def test_returns_none_when_disabled(self, mock_settings):
        mock_settings.llm_enabled = False
        from repomemory.context.llm import summarize_context

        result = summarize_context("test", [])
        assert result is None
