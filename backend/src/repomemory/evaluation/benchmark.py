"""Benchmark runner for evaluating retrieval quality."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import yaml

from repomemory.evaluation.metrics import (
    average_precision,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)


@dataclass
class QueryCase:
    query: str
    mode: str | None
    expected_files: list[str]
    expected_symbols: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class QueryResult:
    query: str
    mode: str
    classified_mode: str
    retrieved_files: list[str]
    expected_files: list[str]
    recall_1: float
    recall_5: float
    recall_10: float
    precision_5: float
    mrr_score: float
    ap: float
    ndcg_5: float
    latency_ms: float


@dataclass
class BenchmarkResult:
    name: str
    repo_path: str
    timestamp: str
    query_count: int
    avg_recall_1: float
    avg_recall_5: float
    avg_recall_10: float
    avg_precision_5: float
    avg_mrr: float
    mean_ap: float
    avg_ndcg_5: float
    avg_latency_ms: float
    query_results: list[QueryResult]


def load_query_set(path: str | Path) -> list[QueryCase]:
    """Load benchmark queries from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    cases = []
    for item in data.get("queries", []):
        cases.append(
            QueryCase(
                query=item["query"],
                mode=item.get("mode"),
                expected_files=item.get("expected_files", []),
                expected_symbols=item.get("expected_symbols", []),
                description=item.get("description", ""),
            )
        )
    return cases


def run_benchmark(
    repo_id: int,
    repo_path: str,
    query_set_path: str | Path,
    name: str = "benchmark",
    output_dir: str | Path | None = None,
) -> BenchmarkResult:
    """Run a benchmark suite and compute metrics."""
    from repomemory.retrieval.orchestrator import retrieve

    cases = load_query_set(query_set_path)
    results: list[QueryResult] = []

    for case in cases:
        start = time.perf_counter()
        retrieval = retrieve(
            query=case.query,
            repo_id=repo_id,
            mode=case.mode,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        retrieved_files = [r.file_path for r in retrieval.ranked_results]

        qr = QueryResult(
            query=case.query,
            mode=case.mode or "auto",
            classified_mode=retrieval.classified_mode,
            retrieved_files=retrieved_files[:20],
            expected_files=case.expected_files,
            recall_1=recall_at_k(retrieved_files, case.expected_files, 1),
            recall_5=recall_at_k(retrieved_files, case.expected_files, 5),
            recall_10=recall_at_k(retrieved_files, case.expected_files, 10),
            precision_5=precision_at_k(retrieved_files, case.expected_files, 5),
            mrr_score=mrr(retrieved_files, case.expected_files),
            ap=average_precision(retrieved_files, case.expected_files),
            ndcg_5=ndcg_at_k(retrieved_files, case.expected_files, 5),
            latency_ms=elapsed_ms,
        )
        results.append(qr)

    n = len(results) or 1
    benchmark = BenchmarkResult(
        name=name,
        repo_path=repo_path,
        timestamp=datetime.now(UTC).isoformat(),
        query_count=len(results),
        avg_recall_1=sum(r.recall_1 for r in results) / n,
        avg_recall_5=sum(r.recall_5 for r in results) / n,
        avg_recall_10=sum(r.recall_10 for r in results) / n,
        avg_precision_5=sum(r.precision_5 for r in results) / n,
        avg_mrr=sum(r.mrr_score for r in results) / n,
        mean_ap=sum(r.ap for r in results) / n,
        avg_ndcg_5=sum(r.ndcg_5 for r in results) / n,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        query_results=results,
    )

    # Save results
    if output_dir:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        ts_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        result_file = out_path / f"{name}_{ts_str}.json"
        with open(result_file, "w") as f:
            json.dump(asdict(benchmark), f, indent=2)

    return benchmark


def format_benchmark_table(result: BenchmarkResult) -> str:
    """Format benchmark results as a readable table."""
    lines = [
        f"\n{'=' * 70}",
        f"  Benchmark: {result.name}",
        f"  Repo: {result.repo_path}",
        f"  Queries: {result.query_count}",
        f"  Time: {result.timestamp}",
        f"{'=' * 70}",
        "",
        f"  {'Metric':<25} {'Score':>10}",
        f"  {'-' * 35}",
        f"  {'Recall@1':<25} {result.avg_recall_1:>10.3f}",
        f"  {'Recall@5':<25} {result.avg_recall_5:>10.3f}",
        f"  {'Recall@10':<25} {result.avg_recall_10:>10.3f}",
        f"  {'Precision@5':<25} {result.avg_precision_5:>10.3f}",
        f"  {'MRR':<25} {result.avg_mrr:>10.3f}",
        f"  {'MAP':<25} {result.mean_ap:>10.3f}",
        f"  {'NDCG@5':<25} {result.avg_ndcg_5:>10.3f}",
        f"  {'Avg Latency (ms)':<25} {result.avg_latency_ms:>10.1f}",
        "",
        f"  {'Query':<40} {'R@5':>6} {'MRR':>6} {'ms':>8}",
        f"  {'-' * 60}",
    ]

    for qr in result.query_results:
        q = qr.query[:38] + ".." if len(qr.query) > 40 else qr.query
        lines.append(f"  {q:<40} {qr.recall_5:>6.2f} {qr.mrr_score:>6.2f} {qr.latency_ms:>8.1f}")

    lines.append(f"\n{'=' * 70}\n")
    return "\n".join(lines)
