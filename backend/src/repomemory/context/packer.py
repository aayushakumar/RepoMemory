"""Context pack builder — assembles token-budget-aware context packs."""

import logging

from repomemory.models.schemas import (
    ContextFileResponse,
    ContextPackResponse,
    SnippetResponse,
)
from repomemory.retrieval.combiner import RankedResult

logger = logging.getLogger(__name__)


def build_context_pack(
    ranked_results: list[RankedResult],
    query: str,
    mode: str,
    budget: int = 8000,
) -> ContextPackResponse:
    """Build a token-budget-aware context pack from ranked results."""
    files: list[ContextFileResponse] = []
    total_tokens = 0

    for result in ranked_results:
        if total_tokens >= budget:
            break

        file_snippets: list[SnippetResponse] = []
        file_tokens = 0

        for snippet_data in result.snippets:
            snippet_tokens = snippet_data.get("token_count", 0)
            if total_tokens + file_tokens + snippet_tokens > budget:
                continue

            file_snippets.append(
                SnippetResponse(
                    content=snippet_data["content"],
                    start_line=snippet_data["start_line"],
                    end_line=snippet_data["end_line"],
                    symbol_name=snippet_data.get("symbol_name"),
                    token_count=snippet_tokens,
                )
            )
            file_tokens += snippet_tokens

        if file_snippets:
            files.append(
                ContextFileResponse(
                    path=result.file_path,
                    relevance_score=result.combined_score,
                    reason=result.explanation,
                    snippets=file_snippets,
                )
            )
            total_tokens += file_tokens

    budget_used_pct = round(total_tokens / budget * 100, 1) if budget > 0 else 0.0

    return ContextPackResponse(
        query=query,
        mode=mode,
        files=files,
        total_tokens=total_tokens,
        budget=budget,
        budget_used_pct=budget_used_pct,
    )


def export_as_markdown(pack: ContextPackResponse) -> str:
    """Export context pack as formatted Markdown for LLM prompts."""
    lines = [
        f'## Context Pack: "{pack.query}"',
        f"Mode: {pack.mode} | Budget: {pack.total_tokens:,}/{pack.budget:,} tokens",
        "",
    ]

    for cf in pack.files:
        lines.append(f"### {cf.path} (score: {cf.relevance_score:.2f})")
        lines.append(f"**Why:** {cf.reason}")
        lines.append("")

        for snippet in cf.snippets:
            ext = cf.path.rsplit(".", 1)[-1] if "." in cf.path else ""
            symbol_label = f" ({snippet.symbol_name})" if snippet.symbol_name else ""
            lines.append(f"```{ext}")
            lines.append(f"# lines {snippet.start_line}-{snippet.end_line}{symbol_label}")
            lines.append(snippet.content.rstrip())
            lines.append("```")
            lines.append("")

    return "\n".join(lines)


def export_as_json(pack: ContextPackResponse) -> dict:
    """Export context pack as JSON-serializable dict."""
    return pack.model_dump()
