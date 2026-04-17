"""Dependency graph builder — extracts import relationships between files."""

import logging
import re
from pathlib import Path

from repomemory.models.db import get_session
from repomemory.models.tables import DependencyEdge, File

logger = logging.getLogger(__name__)

# Python import resolution patterns
_PY_IMPORT_RE = re.compile(r"^(?:from\s+([\w.]+)\s+import|import\s+([\w.]+))", re.MULTILINE)

# JS/TS import resolution patterns
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?\s+from\s+['"]([^'"]+)['"]|require\s*\(\s*['"]([^'"]+)['"]\s*\))""",
    re.MULTILINE,
)


def _resolve_python_import(import_path: str, source_dir: str, file_paths: dict[str, int]) -> int | None:
    """Resolve a Python dotted import path to a file_id."""
    parts = import_path.split(".")
    # Try as direct module: a.b.c -> a/b/c.py or a/b/c/__init__.py
    candidates = [
        "/".join(parts) + ".py",
        "/".join(parts) + "/__init__.py",
    ]
    # Try relative: if source is in auth/, and import is "token_handler", look for auth/token_handler.py
    if len(parts) == 1:
        candidates.append(f"{source_dir}/{parts[0]}.py")

    for candidate in candidates:
        if candidate in file_paths:
            return file_paths[candidate]
    return None


def _resolve_js_import(import_path: str, source_dir: str, file_paths: dict[str, int]) -> int | None:
    """Resolve a JS/TS import path to a file_id."""
    # Handle relative imports
    if import_path.startswith("."):
        # Resolve relative to source file's directory
        parts = import_path.split("/")
        resolved_parts = source_dir.split("/") if source_dir else []
        for part in parts:
            if part == "..":
                if resolved_parts:
                    resolved_parts.pop()
            elif part != ".":
                resolved_parts.append(part)
        base = "/".join(resolved_parts)
    else:
        base = import_path

    # Try with various extensions
    extensions = ["", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"]
    for ext in extensions:
        candidate = base + ext
        if candidate in file_paths:
            return file_paths[candidate]
    return None


def extract_imports_from_file(filepath: Path, extension: str) -> list[str]:
    """Extract raw import strings from a source file."""
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    imports = []
    if extension == ".py":
        for match in _PY_IMPORT_RE.finditer(content):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.append(imp)
    elif extension in (".js", ".jsx", ".ts", ".tsx"):
        for match in _JS_IMPORT_RE.finditer(content):
            imp = match.group(1) or match.group(2)
            if imp:
                imports.append(imp)
    return imports


def build_dependency_graph(repo_id: int, repo_root: Path) -> int:
    """Build the import dependency graph for a repository.

    Parses import statements from all files and resolves them to other files
    in the same repository. Stores edges in the DependencyEdge table.

    Returns the number of edges created.
    """
    with get_session() as session:
        # Clear old edges
        session.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).delete()
        session.commit()

        # Get all files for this repo
        db_files = session.query(File).filter(File.repo_id == repo_id).all()
        file_paths: dict[str, int] = {f.path: f.id for f in db_files}

        edges_created = 0
        for db_file in db_files:
            filepath = repo_root / db_file.path
            source_dir = str(Path(db_file.path).parent)
            if source_dir == ".":
                source_dir = ""

            imports = extract_imports_from_file(filepath, db_file.extension)

            for imp in imports:
                if db_file.extension == ".py":
                    target_id = _resolve_python_import(imp, source_dir, file_paths)
                    kind = "from_import" if imp in [m.group(1) for m in _PY_IMPORT_RE.finditer("")] else "import"
                else:
                    target_id = _resolve_js_import(imp, source_dir, file_paths)
                    kind = "require" if "require" in imp else "import"

                if target_id and target_id != db_file.id:
                    edge = DependencyEdge(
                        repo_id=repo_id,
                        source_file_id=db_file.id,
                        target_file_id=target_id,
                        import_name=imp[:512],
                        kind=kind,
                    )
                    session.add(edge)
                    edges_created += 1

        session.commit()

    logger.info("Built dependency graph: %d edges for repo %d", edges_created, repo_id)
    return edges_created


def get_connected_files(
    repo_id: int,
    file_ids: set[int],
    max_hops: int = 2,
) -> dict[int, float]:
    """BFS from seed files through the dependency graph.

    Returns {file_id: score} where score decays with hop distance.
    Files at hop 0 (seed files) are not included.
    """
    if not file_ids:
        return {}

    with get_session() as session:
        # Load all edges for repo
        edges = session.query(DependencyEdge).filter(DependencyEdge.repo_id == repo_id).all()

        # Build adjacency lists (bidirectional: imports and imported-by)
        forward: dict[int, set[int]] = {}  # file -> imports
        backward: dict[int, set[int]] = {}  # file -> imported by

        for edge in edges:
            forward.setdefault(edge.source_file_id, set()).add(edge.target_file_id)
            backward.setdefault(edge.target_file_id, set()).add(edge.source_file_id)

    # BFS
    visited: dict[int, int] = {}  # file_id -> hop_distance
    frontier = set(file_ids)
    hop = 0

    while hop < max_hops and frontier:
        next_frontier: set[int] = set()
        for fid in frontier:
            # Get neighbors (both directions)
            neighbors = forward.get(fid, set()) | backward.get(fid, set())
            for nid in neighbors:
                if nid not in visited and nid not in file_ids:
                    visited[nid] = hop + 1
                    next_frontier.add(nid)
        frontier = next_frontier
        hop += 1

    # Score: decay by hop distance
    scores: dict[int, float] = {}
    for fid, dist in visited.items():
        scores[fid] = 1.0 / (1.0 + dist)  # hop 1 -> 0.5, hop 2 -> 0.33

    return scores
