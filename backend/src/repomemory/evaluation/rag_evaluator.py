"""RAG quality evaluator — measures how retrieval quality impacts LLM answer quality."""

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from repomemory.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RAGQueryCase:
    query: str
    expected_answer_keywords: list[str]
    expected_files: list[str] = field(default_factory=list)
    description: str = ""


@dataclass
class RAGQueryResult:
    query: str
    retrieved_files: list[str]
    context_tokens: int
    answer: str | None
    relevance_score: float  # 1-5 scale from LLM judge
    completeness_score: float  # 1-5 scale
    faithfulness_score: float  # 1-5 scale (no hallucinations = 5)
    keyword_recall: float  # fraction of expected keywords in answer
    latency_ms: float


@dataclass
class RAGBenchmarkResult:
    name: str
    query_count: int
    avg_relevance: float
    avg_completeness: float
    avg_faithfulness: float
    avg_keyword_recall: float
    avg_latency_ms: float
    query_results: list[RAGQueryResult]


def load_rag_query_set(path: str | Path) -> list[RAGQueryCase]:
    """Load RAG evaluation queries from a YAML file."""
    with open(path) as f:
        data = yaml.safe_load(f)

    cases = []
    for item in data.get("rag_queries", []):
        cases.append(
            RAGQueryCase(
                query=item["query"],
                expected_answer_keywords=item.get("expected_keywords", []),
                expected_files=item.get("expected_files", []),
                description=item.get("description", ""),
            )
        )
    return cases


def _judge_answer(query: str, answer: str, context_summary: str) -> dict[str, float]:
    """Use LLM as judge to score answer quality.

    Returns dict with relevance, completeness, faithfulness scores (1-5 each).
    Falls back to heuristic scoring if LLM is unavailable.
    """
    if not settings.llm_enabled:
        return _heuristic_judge(query, answer)

    try:
        from repomemory.context.llm import _get_client

        client = _get_client()
        if not client:
            return _heuristic_judge(query, answer)

        prompt = (
            "You are an expert code answer quality evaluator. "
            "Rate the following answer to a code question on three dimensions.\n\n"
            f"Question: {query}\n\n"
            f"Context provided: {context_summary[:1000]}\n\n"
            f"Answer: {answer}\n\n"
            "Rate each dimension from 1-5:\n"
            "- Relevance: Does the answer address the question? (1=completely off-topic, 5=directly answers)\n"
            "- Completeness: Is the answer thorough? (1=missing key info, 5=comprehensive)\n"
            "- Faithfulness: Is the answer grounded in the context? (1=hallucinated, 5=fully grounded)\n\n"
            'Respond ONLY with JSON: {"relevance": N, "completeness": N, "faithfulness": N}'
        )

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50,
            temperature=0.0,
        )

        text = response.choices[0].message.content.strip()
        scores = json.loads(text)
        return {
            "relevance": float(scores.get("relevance", 3)),
            "completeness": float(scores.get("completeness", 3)),
            "faithfulness": float(scores.get("faithfulness", 3)),
        }
    except Exception as e:
        logger.warning("LLM judge failed: %s", e)
        return _heuristic_judge(query, answer)


def _heuristic_judge(query: str, answer: str) -> dict[str, float]:
    """Heuristic scoring when LLM is unavailable."""
    query_words = set(query.lower().split())
    answer_words = set(answer.lower().split())

    # Simple overlap-based scoring
    overlap = len(query_words & answer_words) / max(len(query_words), 1)
    length_score = min(len(answer) / 200, 1.0)  # longer answers up to 200 chars

    return {
        "relevance": min(1 + overlap * 4, 5.0),
        "completeness": min(1 + length_score * 4, 5.0),
        "faithfulness": 3.0,  # can't assess without LLM
    }


def _compute_keyword_recall(answer: str, expected_keywords: list[str]) -> float:
    """Fraction of expected keywords found in the answer."""
    if not expected_keywords:
        return 1.0
    answer_lower = answer.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in answer_lower)
    return hits / len(expected_keywords)


def evaluate_rag_quality(
    repo_id: int,
    query_set_path: str | Path,
    name: str = "rag_eval",
) -> RAGBenchmarkResult:
    """Run RAG quality evaluation: retrieve -> generate answer -> judge quality."""
    from repomemory.context.packer import build_context_pack, export_as_markdown
    from repomemory.retrieval.orchestrator import retrieve

    cases = load_rag_query_set(query_set_path)
    results: list[RAGQueryResult] = []

    for case in cases:
        start = time.perf_counter()

        # Retrieve context
        retrieval = retrieve(query=case.query, repo_id=repo_id, top_k=20)
        context_pack = build_context_pack(
            ranked_results=retrieval.ranked_results,
            query=case.query,
            mode=retrieval.classified_mode,
            budget=8000,
        )

        context_md = export_as_markdown(context_pack)

        # Generate answer using LLM
        answer = _generate_answer(case.query, context_md)

        elapsed_ms = (time.perf_counter() - start) * 1000

        if answer:
            # Judge answer quality
            context_summary = "; ".join(f.path for f in context_pack.files)
            scores = _judge_answer(case.query, answer, context_summary)
            keyword_recall = _compute_keyword_recall(answer, case.expected_answer_keywords)
        else:
            scores = {"relevance": 0, "completeness": 0, "faithfulness": 0}
            keyword_recall = 0.0

        results.append(
            RAGQueryResult(
                query=case.query,
                retrieved_files=[f.path for f in context_pack.files],
                context_tokens=context_pack.total_tokens,
                answer=answer,
                relevance_score=scores["relevance"],
                completeness_score=scores["completeness"],
                faithfulness_score=scores["faithfulness"],
                keyword_recall=keyword_recall,
                latency_ms=elapsed_ms,
            )
        )

    n = len(results) or 1
    return RAGBenchmarkResult(
        name=name,
        query_count=len(results),
        avg_relevance=sum(r.relevance_score for r in results) / n,
        avg_completeness=sum(r.completeness_score for r in results) / n,
        avg_faithfulness=sum(r.faithfulness_score for r in results) / n,
        avg_keyword_recall=sum(r.keyword_recall for r in results) / n,
        avg_latency_ms=sum(r.latency_ms for r in results) / n,
        query_results=results,
    )


def _generate_answer(query: str, context_markdown: str) -> str | None:
    """Generate an answer using LLM with retrieved context."""
    if not settings.llm_enabled:
        return None

    try:
        from repomemory.context.llm import _get_client

        client = _get_client()
        if not client:
            return None

        prompt = (
            "You are a code assistant. Answer the developer's question using ONLY the "
            "provided context. If the context doesn't contain enough information, say so.\n\n"
            f"Context:\n{context_markdown[:6000]}\n\n"
            f"Question: {query}\n\n"
            "Answer concisely (3-5 sentences):"
        )

        response = client.chat.completions.create(
            model=settings.groq_model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=300,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.warning("Answer generation failed: %s", e)
        return None
