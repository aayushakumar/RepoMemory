"""Tests for the dependency graph builder and graph-based retrieval."""

import textwrap
from pathlib import Path

from repomemory.indexer.dependency_graph import (
    build_dependency_graph,
    extract_imports_from_file,
    get_connected_files,
)
from repomemory.models.db import get_session
from repomemory.models.tables import DependencyEdge, File, Repository
from repomemory.retrieval.graph import graph_search

SAMPLE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


# ---------- extract_imports_from_file ----------


def test_extract_python_imports(tmp_path):
    f = tmp_path / "mod.py"
    f.write_text(
        textwrap.dedent("""\
        import os
        from pathlib import Path
        from mypackage.submod import helper
    """)
    )
    imports = extract_imports_from_file(f, ".py")
    assert "os" in imports
    assert "pathlib" in imports
    assert "mypackage.submod" in imports


def test_extract_js_imports(tmp_path):
    f = tmp_path / "index.js"
    f.write_text(
        textwrap.dedent("""\
        import React from 'react';
        import { useState } from './hooks';
        const lodash = require('lodash');
    """)
    )
    imports = extract_imports_from_file(f, ".js")
    assert "react" in imports
    assert "./hooks" in imports
    assert "lodash" in imports


def test_extract_ts_imports(tmp_path):
    f = tmp_path / "app.ts"
    f.write_text("import { Client } from '../api/client';")
    imports = extract_imports_from_file(f, ".ts")
    assert "../api/client" in imports


def test_extract_unsupported_extension(tmp_path):
    f = tmp_path / "data.json"
    f.write_text('{"key": "value"}')
    assert extract_imports_from_file(f, ".json") == []


def test_extract_nonexistent_file():
    assert extract_imports_from_file(Path("/nonexistent/file.py"), ".py") == []


# ---------- build_dependency_graph ----------


def _setup_repo_with_files(session, tmp_path, file_contents: dict[str, str]) -> tuple[int, Path]:
    """Create a repo + files in DB and on disk. Returns (repo_id, repo_root)."""
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    repo = Repository(path=str(repo_root), name="test_repo", status="ready")
    session.add(repo)
    session.flush()

    for rel_path, content in file_contents.items():
        full = repo_root / rel_path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(content)
        ext = Path(rel_path).suffix
        f = File(
            repo_id=repo.id,
            path=rel_path,
            extension=ext,
            size_bytes=len(content),
            line_count=content.count("\n") + 1,
            last_modified=0.0,
            content_hash="abc",
        )
        session.add(f)

    session.commit()
    return repo.id, repo_root


def test_build_graph_python_imports(test_db, tmp_path):
    with get_session() as session:
        files = {
            "auth/login.py": "from auth.token import validate\n",
            "auth/token.py": "import os\n",
        }
        repo_id, repo_root = _setup_repo_with_files(session, tmp_path, files)

    edges = build_dependency_graph(repo_id, repo_root)
    # login.py imports auth.token -> should resolve to auth/token.py
    assert edges >= 1

    with get_session() as session:
        stored = session.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).all()
        assert len(stored) >= 1
        # Verify at least one edge connects the right files
        src_paths = set()
        tgt_paths = set()
        for e in stored:
            src = session.get(File, e.source_file_id)
            tgt = session.get(File, e.target_file_id)
            src_paths.add(src.path)
            tgt_paths.add(tgt.path)
        assert "auth/login.py" in src_paths


def test_build_graph_clears_old_edges(test_db, tmp_path):
    with get_session() as session:
        files = {"a.py": "import b\n", "b.py": ""}
        repo_id, repo_root = _setup_repo_with_files(session, tmp_path, files)

    # Build twice — second should replace first
    build_dependency_graph(repo_id, repo_root)
    build_dependency_graph(repo_id, repo_root)

    with get_session() as session:
        count = session.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).count()
        # Should not double up
        assert count <= 2


def test_build_graph_js_relative_import(test_db, tmp_path):
    with get_session() as session:
        files = {
            "src/app.js": "import { foo } from './utils/helpers';",
            "src/utils/helpers.js": "export function foo() {}",
        }
        repo_id, repo_root = _setup_repo_with_files(session, tmp_path, files)

    edges = build_dependency_graph(repo_id, repo_root)
    assert edges >= 1


# ---------- get_connected_files / graph_search ----------


def test_get_connected_files_empty(test_db):
    assert get_connected_files(repo_id=999, file_ids=set(), max_hops=2) == {}


def test_get_connected_files_bfs(test_db, tmp_path):
    with get_session() as session:
        files = {
            "a.py": "from b import x\n",
            "b.py": "from c import y\n",
            "c.py": "",
        }
        repo_id, repo_root = _setup_repo_with_files(session, tmp_path, files)

    build_dependency_graph(repo_id, repo_root)

    with get_session() as session:
        file_a = session.query(File).filter(File.repo_id == repo_id, File.path == "a.py").one()
        scores = get_connected_files(repo_id, {file_a.id}, max_hops=2)
        # b.py should be reachable (hop 1), c.py may also be reachable (hop 2)
        assert len(scores) >= 1
        # Scores decay: closest should have highest score
        for fid, score in scores.items():
            assert 0 < score <= 1.0


def test_graph_search_wrapper(test_db, tmp_path):
    with get_session() as session:
        files = {
            "x.py": "import y\n",
            "y.py": "",
        }
        repo_id, repo_root = _setup_repo_with_files(session, tmp_path, files)

    build_dependency_graph(repo_id, repo_root)

    with get_session() as session:
        file_x = session.query(File).filter(File.repo_id == repo_id, File.path == "x.py").one()
        scores = graph_search({file_x.id}, repo_id, max_hops=2)
        assert isinstance(scores, dict)


def test_graph_search_empty_seeds(test_db):
    assert graph_search(set(), repo_id=1, max_hops=2) == {}
