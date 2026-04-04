import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type { SearchRequest } from "./types";

/* ── Repos ── */
export function useRepos() {
  return useQuery({ queryKey: ["repos"], queryFn: api.listRepos });
}

export function useRepo(id: number) {
  return useQuery({
    queryKey: ["repos", id],
    queryFn: () => api.getRepo(id),
    enabled: id > 0,
  });
}

export function useIndexRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (path: string) => api.indexRepo(path),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repos"] }),
  });
}

export function useReindexRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.reindexRepo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repos"] }),
  });
}

export function useDeleteRepo() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api.deleteRepo(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["repos"] }),
  });
}

/* ── Search ── */
export function useSearch() {
  return useMutation({ mutationFn: (req: SearchRequest) => api.search(req) });
}

export function useModes() {
  return useQuery({ queryKey: ["modes"], queryFn: api.getModes });
}

/* ── Memory ── */
export function useMemoryStats(repoId: number) {
  return useQuery({
    queryKey: ["memory", repoId],
    queryFn: () => api.getMemoryStats(repoId),
    enabled: repoId > 0,
  });
}

export function useClearMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (repoId: number) => api.clearMemory(repoId),
    onSuccess: (_d, repoId) =>
      qc.invalidateQueries({ queryKey: ["memory", repoId] }),
  });
}
