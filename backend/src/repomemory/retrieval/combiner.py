"""Score combiner — fuses results from multiple retrievers using RRF or weighted sum."""

import logging
from dataclasses import dataclass, field

from repomemory.models.db import get_session
from repomemory.models.tables import Chunk, File

logger = logging.getLogger(__name__)

K_RRF = 60  # RRF constant


@dataclass
class RankedResult:
    file_id: int
    file_path: str
    chunk_ids: list[int]
    symbol_ids: list[int]
    combined_score: float
    component_scores: dict[str, float]
    explanation: str = ""
    snippets: list[dict] = field(default_factory=list)


def _rrf_score(rank: int) -> float:
    """Reciprocal Rank Fusion score."""
    return 1.0 / (K_RRF + rank + 1)


def combine_results(
    lexical_results: list[tuple[int, float]],  # (chunk_id, score)
    semantic_results: list[tuple[int, float]],  # (chunk_id, score)
    path_results: list[tuple[int, float]],  # (file_id, score)
    symbol_results: list[tuple[int, int, float]],  # (symbol_id, file_id, score)
    memory_scores: dict[int, float],  # file_id -> frecency score
    weights: dict[str, float],
    repo_id: int,
    top_k: int = 20,
    method: str = "rrf",
    graph_scores: dict[int, float] | None = None,  # file_id -> dependency graph score
) -> list[RankedResult]:
    """Combine results from multiple retrievers into a single ranked list."""

    # Collect all chunk_ids and file_ids involved
    with get_session() as session:
        # Build chunk_id -> file_id mapping
        all_chunk_ids = set()
        for cid, _ in lexical_results:
            all_chunk_ids.add(cid)
        for cid, _ in semantic_results:
            all_chunk_ids.add(cid)

        chunk_to_file: dict[int, int] = {}
        chunk_to_path: dict[int, str] = {}
        if all_chunk_ids:
            chunks = session.query(Chunk.id, Chunk.file_id).filter(Chunk.id.in_(all_chunk_ids)).all()
            for c_id, f_id in chunks:
                chunk_to_file[c_id] = f_id

            file_ids_from_chunks = set(chunk_to_file.values())
            files = session.query(File.id, File.path).filter(File.id.in_(file_ids_from_chunks)).all()
            file_id_to_path = {f_id: path for f_id, path in files}
            for c_id, f_id in chunk_to_file.items():
                chunk_to_path[c_id] = file_id_to_path.get(f_id, "")

        # Also get paths for path_results and symbol_results
        path_file_ids = {fid for fid, _ in path_results}
        sym_file_ids = {fid for _, fid, _ in symbol_results}
        all_file_ids = file_ids_from_chunks if all_chunk_ids else set()
        all_file_ids |= path_file_ids | sym_file_ids

        file_paths: dict[int, str] = {}
        if all_file_ids:
            files = session.query(File.id, File.path).filter(File.id.in_(all_file_ids)).all()
            file_paths = {f_id: path for f_id, path in files}

    # Aggregate scores per file_id
    file_scores: dict[int, dict[str, float]] = {}

    def _ensure_file(fid: int):
        if fid not in file_scores:
            file_scores[fid] = {
                "lexical": 0.0,
                "semantic": 0.0,
                "path_match": 0.0,
                "symbol_match": 0.0,
                "memory_frecency": 0.0,
                "git_recency": 0.0,
                "dependency_graph": 0.0,
            }

    if method == "rrf":
        # RRF: use rank positions
        for rank, (cid, _) in enumerate(lexical_results):
            fid = chunk_to_file.get(cid)
            if fid is None:
                continue
            _ensure_file(fid)
            rrf = _rrf_score(rank)
            file_scores[fid]["lexical"] = max(file_scores[fid]["lexical"], rrf)

        for rank, (cid, _) in enumerate(semantic_results):
            fid = chunk_to_file.get(cid)
            if fid is None:
                continue
            _ensure_file(fid)
            rrf = _rrf_score(rank)
            file_scores[fid]["semantic"] = max(file_scores[fid]["semantic"], rrf)

        for rank, (fid, _) in enumerate(path_results):
            _ensure_file(fid)
            rrf = _rrf_score(rank)
            file_scores[fid]["path_match"] = max(file_scores[fid]["path_match"], rrf)

        for rank, (_, fid, _) in enumerate(symbol_results):
            _ensure_file(fid)
            rrf = _rrf_score(rank)
            file_scores[fid]["symbol_match"] = max(file_scores[fid]["symbol_match"], rrf)
    else:
        # Weighted sum: use raw scores
        for cid, score in lexical_results:
            fid = chunk_to_file.get(cid)
            if fid is None:
                continue
            _ensure_file(fid)
            file_scores[fid]["lexical"] = max(file_scores[fid]["lexical"], score)

        for cid, score in semantic_results:
            fid = chunk_to_file.get(cid)
            if fid is None:
                continue
            _ensure_file(fid)
            file_scores[fid]["semantic"] = max(file_scores[fid]["semantic"], score)

        for fid, score in path_results:
            _ensure_file(fid)
            file_scores[fid]["path_match"] = max(file_scores[fid]["path_match"], score)

        for _, fid, score in symbol_results:
            _ensure_file(fid)
            file_scores[fid]["symbol_match"] = max(file_scores[fid]["symbol_match"], score)

    # Add memory scores
    for fid in file_scores:
        file_scores[fid]["memory_frecency"] = memory_scores.get(fid, 0.0)

    # Add dependency graph scores
    if graph_scores:
        for fid, gscore in graph_scores.items():
            _ensure_file(fid)
            file_scores[fid]["dependency_graph"] = gscore

    # Compute combined scores
    results: list[RankedResult] = []
    for fid, scores_dict in file_scores.items():
        combined = sum(weights.get(k, 0.0) * v for k, v in scores_dict.items())

        # Collect chunk_ids for this file
        file_chunk_ids = [cid for cid, _ in lexical_results if chunk_to_file.get(cid) == fid] + [
            cid for cid, _ in semantic_results if chunk_to_file.get(cid) == fid
        ]
        file_chunk_ids = list(set(file_chunk_ids))

        # Collect symbol_ids
        file_symbol_ids = [sid for sid, sfid, _ in symbol_results if sfid == fid]

        results.append(
            RankedResult(
                file_id=fid,
                file_path=file_paths.get(fid, ""),
                chunk_ids=file_chunk_ids,
                symbol_ids=file_symbol_ids,
                combined_score=round(combined, 4),
                component_scores=scores_dict,
            )
        )

    results.sort(key=lambda r: -r.combined_score)
    return results[:top_k]
