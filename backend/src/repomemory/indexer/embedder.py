"""Embedding generation and FAISS index management."""

import json
import logging
from pathlib import Path

import faiss
import numpy as np
from tqdm import tqdm

from repomemory.config import settings
from repomemory.models.db import get_session
from repomemory.models.tables import Chunk

logger = logging.getLogger(__name__)

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(settings.embedding_model)
        logger.info("Loaded embedding model: %s", settings.embedding_model)
    return _model


def _get_index_path(repo_id: int) -> Path:
    return settings.get_faiss_index_dir() / f"repo_{repo_id}.faiss"


def _get_mapping_path(repo_id: int) -> Path:
    return settings.get_faiss_index_dir() / f"repo_{repo_id}_mapping.json"


def embed_chunks(repo_id: int) -> int:
    """Generate embeddings for all chunks of a repo and build FAISS index.
    Returns number of embeddings generated.
    """
    model = _get_model()

    with get_session() as session:
        chunks = (
            session.query(Chunk)
            .join(Chunk.file)
            .filter(Chunk.file.has(repo_id=repo_id))
            .order_by(Chunk.id)
            .all()
        )

        if not chunks:
            logger.warning("No chunks to embed for repo %d", repo_id)
            return 0

        chunk_ids = [c.id for c in chunks]
        texts = [c.content for c in chunks]

    # Batch encode
    logger.info("Embedding %d chunks...", len(texts))
    embeddings = model.encode(
        texts,
        batch_size=settings.embedding_batch_size,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.array(embeddings, dtype=np.float32)

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
    model = _get_model()
    vec = model.encode([query], normalize_embeddings=True)
    return np.array(vec, dtype=np.float32)
