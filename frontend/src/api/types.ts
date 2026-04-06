/* ── TypeScript types matching backend Pydantic schemas ── */

export interface Repo {
  id: number;
  name: string;
  path: string;
  url: string | null;
  branch: string | null;
  status: string;
  error_message: string | null;
  file_count: number;
  symbol_count: number;
  chunk_count: number;
  indexed_at: string | null;
  language_summary: string | null;
}

export interface IndexRepoRequest {
  url?: string;
  path?: string;
  branch?: string;
  token?: string;
}

export interface IndexingStats {
  repo_id: number;
  files_indexed: number;
  symbols_extracted: number;
  chunks_created: number;
  embeddings_generated: number;
  duration_seconds: number;
}

export interface Snippet {
  content: string;
  start_line: number;
  end_line: number;
  symbol_name: string | null;
  token_count: number;
}

export interface ComponentScores {
  lexical: number;
  semantic: number;
  path_match: number;
  symbol_match: number;
  memory_frecency: number;
  git_recency: number;
}

export interface RankedResult {
  file_id: number;
  file_path: string;
  chunk_ids: number[];
  symbol_ids: number[];
  combined_score: number;
  component_scores: ComponentScores;
  explanation: string;
  snippets: Snippet[];
}

export interface ContextFile {
  path: string;
  relevance_score: number;
  reason: string;
  snippets: Snippet[];
}

export interface ContextPack {
  query: string;
  mode: string;
  files: ContextFile[];
  total_tokens: number;
  budget: number;
  budget_used_pct: number;
}

export interface SearchResponse {
  context_pack: ContextPack;
  ranked_results: RankedResult[];
  classified_mode: string;
  query_id: number;
  latency_ms: number;
}

export interface SearchRequest {
  repo_id: number;
  query: string;
  mode?: string | null;
  top_k?: number;
  token_budget?: number;
}

export interface TaskMode {
  name: string;
  description: string;
  keywords: string[];
}

export interface MemoryStats {
  total_queries: number;
  total_actions: number;
  top_files: Array<{ file_id: number; path: string; action_count: number }>;
  recent_queries: Array<{ query_id: number; text: string; mode: string; timestamp: string }>;
}

export interface ExplainRequest {
  query: string;
  context_pack: ContextPack;
}

export interface ExplainResponse {
  summary: string;
  model: string | null;
}
