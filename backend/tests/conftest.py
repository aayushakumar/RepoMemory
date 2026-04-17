"""Shared test fixtures."""

from pathlib import Path

import pytest

from repomemory.config import settings
from repomemory.models.db import init_db, reset_engine

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_REPO = FIXTURES_DIR / "sample_repo"


@pytest.fixture(autouse=True)
def test_db(tmp_path):
    """Create a fresh temp DB for each test."""
    db_path = tmp_path / "test.db"
    settings.db_path = db_path
    settings.faiss_index_dir = tmp_path / "faiss"
    settings.data_dir = tmp_path

    reset_engine()
    settings.ensure_dirs()
    init_db()

    yield db_path

    reset_engine()
    # Restore defaults
    settings.db_path = None
    settings.faiss_index_dir = None
