"""Pydantic request/response schemas for the API."""

from datetime import datetime

from pydantic import BaseModel, Field


# --- Repository ---

class RepoCreate(BaseModel):
    url: str | None = None
    path: str | None = None  # backward compat for local paths
    branch: str | None = None
    token: str | None = None  # GitHub personal access token for private repos


class RepoResponse(BaseModel):
    id: int
    path: str
    name: str
    url: str | None = None
    branch: str | None = None
    status: str
    error_message: str | None = None
    language_summary: str | None = None
    file_count: int = 0
    symbol_count: int = 0
    chunk_count: int = 0
    indexed_at: datetime | None = None

    model_config = {"from_attributes": True}


class IndexingStats(BaseModel):
    repo_id: int
    files_indexed: int
    symbols_extracted: int
    chunks_created: int
    embeddings_generated: int
    duration_seconds: float


# --- Search ---

class SearchRequest(BaseModel):
    repo_id: int
    query: str = Field(min_length=1, max_length=2000)
    mode: str | None = None  # auto-detected if None
    top_k: int = Field(default=20, ge=1, le=100)
    token_budget: int = Field(default=8000, ge=100, le=100000)


class ComponentScores(BaseModel):
    lexical: float = 0.0
    semantic: float = 0.0
    path_match: float = 0.0
    symbol_match: float = 0.0
    memory_frecency: float = 0.0
    git_recency: float = 0.0


class SnippetResponse(BaseModel):
    content: str
    start_line: int
    end_line: int
    symbol_name: str | None = None
    token_count: int


class RankedResultResponse(BaseModel):
    file_id: int
    file_path: str
    chunk_ids: list[int]
    symbol_ids: list[int]
    combined_score: float
    component_scores: ComponentScores
    explanation: str
    snippets: list[SnippetResponse] = []

    model_config = {"from_attributes": True}


class ContextFileResponse(BaseModel):
    path: str
    relevance_score: float
    reason: str
    snippets: list[SnippetResponse]


class ContextPackResponse(BaseModel):
    query: str
    mode: str
    files: list[ContextFileResponse]
    total_tokens: int
    budget: int
    budget_used_pct: float


class SearchResponse(BaseModel):
    context_pack: ContextPackResponse
    ranked_results: list[RankedResultResponse]
    classified_mode: str
    query_id: int
    latency_ms: float


# --- Memory ---

class ActionRequest(BaseModel):
    query_id: int
    target_type: str  # file, symbol, chunk
    target_id: int
    action: str  # opened, selected, accepted, dismissed, thumbs_up, thumbs_down


class MemoryStatsResponse(BaseModel):
    total_queries: int
    total_actions: int
    top_files: list[dict]
    recent_queries: list[dict]


# --- Task modes ---

class TaskModeResponse(BaseModel):
    name: str
    description: str
    keywords: list[str]


# --- Export ---

class ExportFormat(BaseModel):
    format: str = "markdown"  # markdown or json


# --- AI Explain ---

class ExplainRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    context_pack: dict  # serialized ContextPackResponse


class ExplainResponse(BaseModel):
    summary: str
    model: str | None = None
