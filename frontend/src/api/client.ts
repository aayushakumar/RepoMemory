const BASE = import.meta.env.VITE_API_URL || "";

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${url}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`${res.status}: ${body}`);
  }
  return res.json();
}

/* ── Repos ── */
import type {
  Repo,
  IndexRepoRequest,
  SearchRequest,
  SearchResponse,
  ExplainRequest,
  ExplainResponse,
  TaskMode,
  MemoryStats,
} from "./types";

export const api = {
  /* Repos */
  listRepos: () => request<Repo[]>("/api/repos"),

  getRepo: (id: number) => request<Repo>(`/api/repos/${id}`),

  indexRepo: (body: IndexRepoRequest) =>
    request<Repo>("/api/repos", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  reindexRepo: (id: number) =>
    request<Repo>(`/api/repos/${id}/reindex`, { method: "POST" }),

  deleteRepo: (id: number) =>
    request<{ detail: string }>(`/api/repos/${id}`, { method: "DELETE" }),

  /* Search */
  search: (req: SearchRequest) =>
    request<SearchResponse>("/api/search", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  explain: (req: ExplainRequest) =>
    request<ExplainResponse>("/api/search/explain", {
      method: "POST",
      body: JSON.stringify(req),
    }),

  getModes: () => request<TaskMode[]>("/api/search/modes"),

  /* Memory */
  recordAction: (body: {
    query_id: number;
    target_type: string;
    target_id: number;
    action: string;
  }) =>
    request<{ detail: string }>("/api/actions", {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getMemoryStats: (repoId: number) =>
    request<MemoryStats>(`/api/memory/${repoId}/stats`),

  clearMemory: (repoId: number) =>
    request<{ detail: string }>(`/api/memory/${repoId}`, { method: "DELETE" }),
};
