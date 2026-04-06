"""Tests for the embedding provider abstraction."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from repomemory.indexer.embedder import HuggingFaceAPIProvider, LocalEmbeddingProvider


class TestLocalEmbeddingProvider:
    @patch("repomemory.indexer.embedder.settings")
    def test_encode_returns_numpy_array(self, mock_settings):
        mock_settings.embedding_model = "all-MiniLM-L6-v2"
        mock_settings.embedding_batch_size = 32

        provider = LocalEmbeddingProvider()

        # Mock the model
        mock_model = MagicMock()
        mock_model.encode.return_value = np.random.randn(2, 384).astype(np.float32)
        provider._model = mock_model

        result = provider.encode(["hello world", "test query"])
        assert result.shape == (2, 384)
        assert result.dtype == np.float32


class TestHuggingFaceAPIProvider:
    @patch("repomemory.indexer.embedder.settings")
    def test_init_requires_api_key(self, mock_settings):
        mock_settings.hf_api_key = None
        with pytest.raises(ValueError, match="HF_API_KEY"):
            HuggingFaceAPIProvider()

    @patch("repomemory.indexer.embedder.settings")
    def test_encode_calls_api(self, mock_settings):
        mock_settings.hf_api_key = "test-key"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        provider = HuggingFaceAPIProvider()

        mock_embeddings = np.random.randn(2, 384).tolist()

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_embeddings
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = provider.encode(["hello", "world"])
            assert result.shape == (2, 384)
            mock_post.assert_called_once()

    @patch("repomemory.indexer.embedder.settings")
    def test_normalization(self, mock_settings):
        mock_settings.hf_api_key = "test-key"
        mock_settings.embedding_model = "all-MiniLM-L6-v2"

        provider = HuggingFaceAPIProvider()

        # Non-normalized vectors
        raw = [[3.0, 4.0], [1.0, 0.0]]

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.json.return_value = raw
            mock_response.raise_for_status = MagicMock()
            mock_post.return_value = mock_response

            result = provider.encode(["a", "b"], normalize=True)
            norms = np.linalg.norm(result, axis=1)
            np.testing.assert_allclose(norms, [1.0, 1.0], atol=1e-5)
