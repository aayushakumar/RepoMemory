"""Embedding generation and FAISS index management.

Supports two providers:
- "local": sentence-transformers (all-MiniLM-L6-v2) — runs on-device, no API key needed
- "huggingface": HuggingFace Inference API — free tier, no GPU needed
"""

import json
import logging
import time
from pathlib import Path
from typing import Protocol

import faiss
import numpy as np
from tqdm import tqdm

from repomemory.config import settings
from repomemory.models.db import get_session
from repomemory.models.tables import Chunk

logger = logging.getLogger(__name__)


# ── Embedding provider protocol ──


class EmbeddingProvider(Protocol):
    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray: ...


class LocalEmbeddingProvider:
    """sentence-transformers running locally."""

    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(settings.embedding_model)
            logger.info("Loaded local embedding model: %s", settings.embedding_model)

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        self._load()
        embeddings = self._model.encode(
            texts,
            batch_size=settings.embedding_batch_size,
            show_progress_bar=True,
            normalize_embeddings=normalize,
        )
        return np.array(embeddings, dtype=np.float32)


class HuggingFaceAPIProvider:
    """HuggingFace Inference API — free tier, no local GPU needed."""

    API_URL = "https://api-inference.huggingface.co/pipeline/feature-extraction"

    def __init__(self):
        if not settings.hf_api_key:
            raise ValueError("REPOMEMORY_HF_API_KEY is required for huggingface embedding provider")
        self._headers = {"Authorization": f"Bearer {settings.hf_api_key}"}
        self._model = settings.embedding_model

    def encode(self, texts: list[str], normalize: bool = True) -> np.ndarray:
        import httpx

        url = f"{self.API_URL}/{self._model}"
        all_embeddings = []
        batch_size = 32  # HF API handles batches well

        for i in tqdm(range(0, len(texts), batch_size), desc="HF API embedding"):
            batch = texts[i : i + batch_size]
            # Truncate very long texts to avoid API errors
            batch = [t[:512] for t in batch]

            for attempt in range(3):
                try:
                    resp = httpx.post(
                        url,
                        json={"inputs": batch, "options": {"wait_for_model": True}},
                        headers=self._headers,
                        timeout=60.0,
                    )
                    resp.raise_for_status()
                    embeddings = resp.json()
                    all_embeddings.extend(embeddings)
                    break
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:
                        wait = 2**attempt * 5
                        logger.warning("HF rate limited, waiting %ds...", wait)
                        time.sleep(wait)
                    elif e.response.status_code == 503:
                        logger.info("HF model loading, waiting 20s...")
                        time.sleep(20)
                    else:
                        raise
                except httpx.TimeoutException:
                    if attempt < 2:
                        logger.warning("HF API timeout, retrying...")
                        time.sleep(2)
                    else:
                        raise

        result = np.array(all_embeddings, dtype=np.float32)

        if normalize and result.size > 0:
            norms = np.linalg.norm(result, axis=1, keepdims=True)
            norms = np.maximum(norms, 1e-12)
            result = result / norms

        return result


# ── Provider factory ──

_provider: EmbeddingProvider | None = None


def _get_provider() -> EmbeddingProvider:
    global _provider
    if _provider is None:
        if settings.embedding_provider == "huggingface":
            _provider = HuggingFaceAPIProvider()
            logger.info("Using HuggingFace API embedding provider")
        else:
            _provider = LocalEmbeddingProvider()
            logger.info("Using local embedding provider")
    return _provider


# ── Index paths ──


def _get_index_path(repo_id: int) -> Path:
    return settings.get_faiss_index_dir() / f"repo_{repo_id}.faiss"


def _get_mapping_path(repo_id: int) -> Path:
    return settings.get_faiss_index_dir() / f"repo_{repo_id}_mapping.json"


# ── Public API ──


def embed_chunks(repo_id: int) -> int:
    """Generate embeddings for all chunks of a repo and build FAISS index.
    Returns number of embeddings generated.
    """
    provider = _get_provider()

    with get_session() as session:
        chunks = session.query(Chunk).join(Chunk.file).filter(Chunk.file.has(repo_id=repo_id)).order_by(Chunk.id).all()

        if not chunks:
            logger.warning("No chunks to embed for repo %d", repo_id)
            return 0

        chunk_ids = [c.id for c in chunks]
        texts = [c.content for c in chunks]

    # Batch encode via provider
    logger.info("Embedding %d chunks...", len(texts))
    embeddings = provider.encode(texts, normalize=True)

    # Build FAISS index (inner product = cosine similarity after normalization)
    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    # Save index + mapping
    index_path = _get_index_path(repo_id)
    mapping_path = _get_mapping_path(repo_id)

    faiss.write_index(index, str(index_path))

    # mapping: faiss_position -> chunk_id
    mapping = {str(i): cid for i, cid in enumerate(chunk_ids)}
    mapping_path.write_text(json.dumps(mapping))

    # Update chunk faiss_index references
    with get_session() as session:
        for i, cid in enumerate(chunk_ids):
            session.query(Chunk).filter(Chunk.id == cid).update({"faiss_index": i})
        session.commit()

    logger.info("Built FAISS index with %d vectors (dim=%d)", len(chunk_ids), dim)
    return len(chunk_ids)


def load_faiss_index(repo_id: int) -> tuple[faiss.Index, dict[int, int]] | None:
    """Load FAISS index and mapping for a repo.
    Returns (index, {faiss_pos: chunk_id}) or None.
    """
    index_path = _get_index_path(repo_id)
    mapping_path = _get_mapping_path(repo_id)

    if not index_path.exists() or not mapping_path.exists():
        return None

    index = faiss.read_index(str(index_path))
    raw_mapping = json.loads(mapping_path.read_text())
    mapping = {int(k): v for k, v in raw_mapping.items()}

    return index, mapping


def encode_query(query: str) -> np.ndarray:
    """Encode a query string to a normalized embedding vector."""
    provider = _get_provider()
    vec = provider.encode([query], normalize=True)
    return np.array(vec, dtype=np.float32)
