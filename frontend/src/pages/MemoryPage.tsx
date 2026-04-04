import { useState, useEffect } from "react";
import {
  Brain,
  Trash2,
  Loader2,
  FileCode2,
  BarChart3,
  History,
} from "lucide-react";
import { useRepos, useMemoryStats, useClearMemory } from "../api/hooks";

export default function MemoryPage() {
  const { data: repos } = useRepos();
  const [repoId, setRepoId] = useState<number>(0);
  const clearMemory = useClearMemory();

  // auto-select first repo
  useEffect(() => {
    if (repos?.length && repoId === 0) {
      setRepoId(repos[0].id);
    }
  }, [repos]);

  const { data: stats, isLoading } = useMemoryStats(repoId);

  return (
    <div className="max-w-4xl mx-auto px-6 py-8">
      <div className="flex items-center justify-between mb-8">
        <div className="flex items-center gap-3">
          <Brain className="w-6 h-6 text-cyan" />
          <h1 className="text-2xl font-mono font-bold">Memory</h1>
        </div>

        <div className="flex items-center gap-3">
          <select
            value={repoId}
            onChange={(e) => setRepoId(Number(e.target.value))}
            className="h-9 px-3 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary font-mono focus:outline-none focus:border-cyan/50"
          >
            {!repos?.length && <option value={0}>No repos</option>}
            {repos?.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>

          <button
            onClick={() => {
              if (
                repoId &&
                confirm("Clear all memory data for this repository?")
              )
                clearMemory.mutate(repoId);
            }}
            disabled={clearMemory.isPending || !repoId}
            className="h-9 px-3 flex items-center gap-2 bg-bg-tertiary hover:bg-red/10 border border-border hover:border-red/30 rounded-lg text-sm text-text-secondary hover:text-red transition-colors disabled:opacity-40"
          >
            <Trash2 className="w-3.5 h-3.5" />
            Clear Memory
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-6 h-6 animate-spin text-text-dim" />
        </div>
      ) : !stats ? (
        <div className="flex flex-col items-center justify-center py-16 text-text-dim">
          <Brain className="w-12 h-12 mb-3 opacity-20" />
          <p className="font-mono">No memory data yet</p>
          <p className="text-sm mt-1">
            Memory builds up as you search and interact with results
          </p>
        </div>
      ) : (
        <div className="space-y-6">
          {/* Stats cards */}
          <div className="grid grid-cols-3 gap-4">
            <div className="border border-border rounded-lg p-4 bg-bg-card">
              <div className="flex items-center gap-2 mb-2">
                <History className="w-4 h-4 text-cyan" />
                <span className="text-xs text-text-dim">Queries</span>
              </div>
              <span className="text-2xl font-mono font-bold text-text-primary">
                {stats.total_queries}
              </span>
            </div>
            <div className="border border-border rounded-lg p-4 bg-bg-card">
              <div className="flex items-center gap-2 mb-2">
                <BarChart3 className="w-4 h-4 text-green" />
                <span className="text-xs text-text-dim">Actions</span>
              </div>
              <span className="text-2xl font-mono font-bold text-text-primary">
                {stats.total_actions}
              </span>
            </div>
            <div className="border border-border rounded-lg p-4 bg-bg-card">
              <div className="flex items-center gap-2 mb-2">
                <FileCode2 className="w-4 h-4 text-yellow" />
                <span className="text-xs text-text-dim">Top Files</span>
              </div>
              <span className="text-2xl font-mono font-bold text-text-primary">
                {stats.top_files?.length ?? 0}
              </span>
            </div>
          </div>

          {/* Recent queries */}
          {stats.recent_queries && stats.recent_queries.length > 0 && (
            <div className="border border-border rounded-lg p-4 bg-bg-card">
              <h3 className="text-sm font-mono font-bold text-text-primary mb-3">
                Recent Queries
              </h3>
              <div className="space-y-2">
                {stats.recent_queries.map((q, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-1"
                  >
                    <span className="text-xs font-mono text-text-secondary truncate flex-1 mr-4">
                      {q.text}
                    </span>
                    <span className="text-[10px] text-text-dim shrink-0">
                      {new Date(q.timestamp).toLocaleDateString(undefined, {
                        month: "short",
                        day: "numeric",
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Top files */}
          {stats.top_files && stats.top_files.length > 0 && (
            <div className="border border-border rounded-lg p-4 bg-bg-card">
              <h3 className="text-sm font-mono font-bold text-text-primary mb-3">
                Top Files by Actions
              </h3>
              <div className="space-y-2">
                {stats.top_files.map((f, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between py-1"
                  >
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-text-dim w-4">
                        {i + 1}.
                      </span>
                      <FileCode2 className="w-3.5 h-3.5 text-text-dim" />
                      <span className="text-xs font-mono text-text-secondary">
                        {f.path}
                      </span>
                    </div>
                    <span className="text-xs font-mono text-cyan">
                      {f.action_count}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
