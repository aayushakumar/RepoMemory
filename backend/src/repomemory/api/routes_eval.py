"""Evaluation/benchmark routes."""

from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class BenchmarkRequest(BaseModel):
    repo_id: int
    query_set: str = "sample_repo"  # name of YAML file in benchmarks/queries/


@router.post("/eval/run")
async def run_evaluation(req: BenchmarkRequest):
    """Run a benchmark suite against an indexed repository."""
    from repomemory.models.db import get_session
    from repomemory.models.tables import Repository
    from repomemory.evaluation.benchmark import (
        run_benchmark,
        format_benchmark_table,
    )

    with get_session() as session:
        repo = session.get(Repository, req.repo_id)
        if not repo:
            raise HTTPException(404, "Repository not found")
        repo_path = repo.path

    # Find query set
    base = Path(__file__).resolve().parent.parent.parent.parent / "benchmarks" / "queries"
    query_file = base / f"{req.query_set}.yaml"
    if not query_file.exists():
        raise HTTPException(404, f"Query set '{req.query_set}' not found")

    output_dir = base.parent / "results"

    result = run_benchmark(
        repo_id=req.repo_id,
        repo_path=repo_path,
        query_set_path=str(query_file),
        name=req.query_set,
        output_dir=str(output_dir),
    )

    return {
        "name": result.name,
        "repo_path": result.repo_path,
        "query_count": result.query_count,
        "avg_recall_1": round(result.avg_recall_1, 3),
        "avg_recall_5": round(result.avg_recall_5, 3),
        "avg_recall_10": round(result.avg_recall_10, 3),
        "avg_precision_5": round(result.avg_precision_5, 3),
        "avg_mrr": round(result.avg_mrr, 3),
        "mean_ap": round(result.mean_ap, 3),
        "avg_ndcg_5": round(result.avg_ndcg_5, 3),
        "avg_latency_ms": round(result.avg_latency_ms, 1),
        "table": format_benchmark_table(result),
        "query_results": [
            {
                "query": qr.query,
                "mode": qr.mode,
                "classified_mode": qr.classified_mode,
                "recall_5": round(qr.recall_5, 3),
                "mrr": round(qr.mrr_score, 3),
                "latency_ms": round(qr.latency_ms, 1),
                "retrieved_files": qr.retrieved_files[:5],
                "expected_files": qr.expected_files,
            }
            for qr in result.query_results
        ],
    }


@router.get("/eval/query-sets")
async def list_query_sets():
    """List available benchmark query sets."""
    base = Path(__file__).resolve().parent.parent.parent.parent / "benchmarks" / "queries"
    if not base.exists():
        return []
    return [p.stem for p in base.glob("*.yaml")]
