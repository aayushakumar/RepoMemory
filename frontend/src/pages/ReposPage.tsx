import { useState, type FormEvent } from "react";
import {
  Database,
  FolderOpen,
  RefreshCw,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode2,
  Braces,
  Box,
} from "lucide-react";
import {
  useRepos,
  useIndexRepo,
  useReindexRepo,
  useDeleteRepo,
} from "../api/hooks";

export default function ReposPage() {
  const { data: repos, isLoading } = useRepos();
  const indexRepo = useIndexRepo();
  const reindexRepo = useReindexRepo();
  const deleteRepo = useDeleteRepo();
  const [path, setPath] = useState("");

  const handleIndex = (e: FormEvent) => {
    e.preventDefault();
    if (!path.trim()) return;
    indexRepo.mutate(path, { onSuccess: () => setPath("") });
  };

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center gap-3 mb-8">
        <Database className="w-6 h-6 text-cyan" />
        <h1 className="text-2xl font-mono font-bold">Repositories</h1>
      </div>

      {/* Index form */}
      <form
        onSubmit={handleIndex}
        className="flex gap-3 mb-8 p-4 border border-border rounded-lg bg-bg-secondary/50"
      >
        <div className="relative flex-1">
          <FolderOpen className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            placeholder="/path/to/your/repo"
            className="w-full h-10 pl-10 pr-4 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-dim font-mono focus:outline-none focus:border-cyan/50 transition-colors"
          />
        </div>
        <button
          type="submit"
          disabled={indexRepo.isPending || !path.trim()}
          className="h-10 px-4 bg-green hover:bg-green-dim disabled:opacity-40 text-bg-primary font-bold text-sm rounded-lg flex items-center gap-2 transition-colors"
        >
          {indexRepo.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <Database className="w-4 h-4" />
          )}
          Index Repository
        </button>
      </form>

      {/* Error/Success */}
      {indexRepo.isError && (
        <div className="mb-4 p-3 border border-red/30 bg-red/5 rounded-lg text-sm text-red flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          {indexRepo.error.message}
        </div>
      )}
      {indexRepo.isSuccess && (
        <div className="mb-4 p-3 border border-green/30 bg-green/5 rounded-lg text-sm text-green flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          Repository indexed successfully!
        </div>
      )}

      {/* Repo list */}
      {isLoading ? (
        <div className="flex items-center justify-center py-16 text-text-dim">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : !repos?.length ? (
        <div className="flex flex-col items-center justify-center py-16 text-text-dim">
          <Database className="w-12 h-12 mb-3 opacity-20" />
          <p className="font-mono">No repositories indexed yet</p>
          <p className="text-sm mt-1">
            Enter a path above to index your first repository
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {repos.map((repo) => (
            <div
              key={repo.id}
              className="border border-border rounded-lg p-4 hover:border-border-active transition-colors bg-bg-card"
            >
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="font-mono font-bold text-text-primary">
                      {repo.name}
                    </h3>
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                        repo.status === "ready"
                          ? "bg-green/10 text-green border border-green/20"
                          : repo.status === "indexing"
                          ? "bg-yellow/10 text-yellow border border-yellow/20"
                          : "bg-red/10 text-red border border-red/20"
                      }`}
                    >
                      {repo.status}
                    </span>
                  </div>
                  <p className="text-xs text-text-dim font-mono">{repo.path}</p>
                </div>

                <div className="flex gap-1">
                  <button
                    onClick={() => reindexRepo.mutate(repo.id)}
                    disabled={reindexRepo.isPending}
                    className="p-2 rounded-md hover:bg-bg-hover text-text-dim hover:text-cyan transition-colors"
                    title="Re-index"
                  >
                    <RefreshCw
                      className={`w-4 h-4 ${
                        reindexRepo.isPending ? "animate-spin" : ""
                      }`}
                    />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm("Delete this repository from the index?"))
                        deleteRepo.mutate(repo.id);
                    }}
                    disabled={deleteRepo.isPending}
                    className="p-2 rounded-md hover:bg-bg-hover text-text-dim hover:text-red transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {/* Stats */}
              <div className="flex gap-6 mt-3 pt-3 border-t border-border">
                <div className="flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5 text-text-dim" />
                  <span className="text-xs font-mono text-text-secondary">
                    {repo.file_count} files
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Braces className="w-3.5 h-3.5 text-text-dim" />
                  <span className="text-xs font-mono text-text-secondary">
                    {repo.symbol_count} symbols
                  </span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Box className="w-3.5 h-3.5 text-text-dim" />
                  <span className="text-xs font-mono text-text-secondary">
                    {repo.chunk_count} chunks
                  </span>
                </div>
                {repo.indexed_at && (
                  <span className="text-xs text-text-dim ml-auto">
                    Indexed:{" "}
                    {new Date(repo.indexed_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
              </div>

              {repo.language_summary && (
                <p className="text-[11px] text-text-dim mt-2 font-mono">
                  {repo.language_summary}
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
