import { useState, type FormEvent } from "react";
import {
  Database,
  Globe,
  RefreshCw,
  Trash2,
  Loader2,
  CheckCircle2,
  AlertCircle,
  FileCode2,
  Braces,
  Box,
  GitBranch,
  Lock,
  ChevronDown,
  ChevronUp,
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
  const [url, setUrl] = useState("");
  const [branch, setBranch] = useState("");
  const [token, setToken] = useState("");
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleIndex = (e: FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    indexRepo.mutate(
      {
        url: url.trim(),
        branch: branch.trim() || undefined,
        token: token.trim() || undefined,
      },
      { onSuccess: () => { setUrl(""); setBranch(""); setToken(""); } }
    );
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
        className="mb-8 p-4 border border-border rounded-lg bg-bg-secondary/50 space-y-3"
      >
        <div className="flex gap-3">
          <div className="relative flex-1">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
            <input
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repo"
              className="w-full h-10 pl-10 pr-4 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-dim font-mono focus:outline-none focus:border-cyan/50 transition-colors"
            />
          </div>
          <button
            type="submit"
            disabled={indexRepo.isPending || !url.trim()}
            className="h-10 px-4 bg-green hover:bg-green-dim disabled:opacity-40 text-bg-primary font-bold text-sm rounded-lg flex items-center gap-2 transition-colors"
          >
            {indexRepo.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Database className="w-4 h-4" />
            )}
            Index Repository
          </button>
        </div>

        {/* Advanced options toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="flex items-center gap-1 text-xs text-text-dim hover:text-text-secondary transition-colors"
        >
          {showAdvanced ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          Advanced options
        </button>

        {showAdvanced && (
          <div className="flex gap-3">
            <div className="relative flex-1">
              <GitBranch className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
              <input
                value={branch}
                onChange={(e) => setBranch(e.target.value)}
                placeholder="Branch (default: main)"
                className="w-full h-9 pl-10 pr-4 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-dim font-mono focus:outline-none focus:border-cyan/50 transition-colors"
              />
            </div>
            <div className="relative flex-1">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
              <input
                type="password"
                value={token}
                onChange={(e) => setToken(e.target.value)}
                placeholder="GitHub token (private repos)"
                className="w-full h-9 pl-10 pr-4 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-dim font-mono focus:outline-none focus:border-cyan/50 transition-colors"
              />
            </div>
          </div>
        )}
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
          Repository queued for indexing! It will appear as &quot;ready&quot; when complete.
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
            Enter a GitHub URL above to index your first repository
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
                    {repo.branch && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full font-mono bg-cyan/10 text-cyan border border-cyan/20">
                        {repo.branch}
                      </span>
                    )}
                    <span
                      className={`text-[10px] px-1.5 py-0.5 rounded-full font-mono ${
                        repo.status === "ready"
                          ? "bg-green/10 text-green border border-green/20"
                          : repo.status === "indexing"
                          ? "bg-yellow/10 text-yellow border border-yellow/20"
                          : "bg-red/10 text-red border border-red/20"
                      }`}
                    >
                      {repo.status === "indexing" && (
                        <Loader2 className="w-3 h-3 inline animate-spin mr-1" />
                      )}
                      {repo.status}
                    </span>
                  </div>
                  <p className="text-xs text-text-dim font-mono truncate max-w-lg">
                    {repo.url || repo.path}
                  </p>
                  {repo.error_message && (
                    <p className="text-xs text-red font-mono mt-1">
                      {repo.error_message}
                    </p>
                  )}
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
              {repo.status === "ready" && (
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
              )}

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
