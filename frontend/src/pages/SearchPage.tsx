import { useState, useCallback, type FormEvent } from "react";
import {
  Search as SearchIcon,
  Loader2,
  Zap,
  Clock,
  SlidersHorizontal,
} from "lucide-react";
import { useRepos, useSearch, useModes } from "../api/hooks";
import type { SearchResponse } from "../api/types";
import ResultCard from "../components/ResultCard";
import ContextPackView from "../components/ContextPackView";

const MODE_ICONS: Record<string, string> = {
  bug_fix: "🐛",
  trace_flow: "🔗",
  test_lookup: "🧪",
  config_lookup: "⚙️",
  general: "🔍",
};

export default function SearchPage() {
  const { data: repos } = useRepos();
  const { data: modes } = useModes();
  const search = useSearch();

  const [query, setQuery] = useState("");
  const [repoId, setRepoId] = useState<number>(0);
  const [mode, setMode] = useState<string | null>(null);
  const [budget, setBudget] = useState(8000);
  const [result, setResult] = useState<SearchResponse | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  const effectiveRepoId = repoId || repos?.[0]?.id || 0;

  const handleSearch = useCallback(
    (e: FormEvent) => {
      e.preventDefault();
      if (!query.trim() || !effectiveRepoId) return;
      search.mutate(
        { repo_id: effectiveRepoId, query, mode, token_budget: budget },
        { onSuccess: setResult }
      );
    },
    [query, effectiveRepoId, mode, budget, search]
  );

  return (
    <div className="h-screen flex flex-col">
      {/* Search bar */}
      <div className="border-b border-border bg-bg-secondary/50 backdrop-blur">
        <form onSubmit={handleSearch} className="max-w-6xl mx-auto px-6 py-4">
          <div className="flex items-center gap-3">
            {/* Repo select */}
            <select
              value={effectiveRepoId}
              onChange={(e) => setRepoId(Number(e.target.value))}
              className="h-11 px-3 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary font-mono focus:outline-none focus:border-cyan/50 min-w-[140px]"
            >
              {!repos?.length && (
                <option value={0}>No repos indexed</option>
              )}
              {repos?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>

            {/* Query input */}
            <div className="relative flex-1">
              <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Where is token rotation handled? / Find tests for auth / Trace login flow..."
                className="w-full h-11 pl-10 pr-4 bg-bg-tertiary border border-border rounded-lg text-sm text-text-primary placeholder:text-text-dim font-mono focus:outline-none focus:border-cyan/50 transition-colors"
              />
            </div>

            {/* Settings toggle */}
            <button
              type="button"
              onClick={() => setShowSettings(!showSettings)}
              className={`h-11 w-11 flex items-center justify-center rounded-lg border transition-colors ${
                showSettings
                  ? "bg-cyan/10 border-cyan/30 text-cyan"
                  : "bg-bg-tertiary border-border text-text-dim hover:text-text-secondary"
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
            </button>

            {/* Search button */}
            <button
              type="submit"
              disabled={search.isPending || !query.trim() || !effectiveRepoId}
              className="h-11 px-5 bg-cyan hover:bg-cyan-dim disabled:opacity-40 text-bg-primary font-bold text-sm rounded-lg flex items-center gap-2 transition-colors"
            >
              {search.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <SearchIcon className="w-4 h-4" />
              )}
              Search
            </button>
          </div>

          {/* Settings row */}
          {showSettings && (
            <div className="flex items-center gap-4 mt-3 pt-3 border-t border-border">
              <label className="text-xs text-text-dim">Token budget:</label>
              <input
                type="range"
                min={1000}
                max={32000}
                step={1000}
                value={budget}
                onChange={(e) => setBudget(Number(e.target.value))}
                className="w-40 accent-cyan"
              />
              <span className="text-xs font-mono text-text-secondary">
                {budget.toLocaleString()}
              </span>
            </div>
          )}

          {/* Mode chips */}
          <div className="flex items-center gap-2 mt-3">
            <span className="text-[11px] text-text-dim mr-1">Mode:</span>
            <button
              type="button"
              onClick={() => setMode(null)}
              className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
                mode === null
                  ? "bg-cyan/15 text-cyan border border-cyan/30"
                  : "bg-bg-tertiary text-text-dim border border-transparent hover:border-border"
              }`}
            >
              Auto
            </button>
            {modes?.map((m) => (
              <button
                key={m.name}
                type="button"
                onClick={() => setMode(m.name === mode ? null : m.name)}
                className={`px-2.5 py-1 rounded-md text-xs font-mono transition-colors ${
                  mode === m.name
                    ? "bg-cyan/15 text-cyan border border-cyan/30"
                    : "bg-bg-tertiary text-text-dim border border-transparent hover:border-border"
                }`}
                title={m.description}
              >
                {MODE_ICONS[m.name] ?? "📁"} {m.name.replace("_", " ")}
              </button>
            ))}
          </div>
        </form>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {!result && !search.isPending && (
          <div className="flex flex-col items-center justify-center h-full text-text-dim">
            <SearchIcon className="w-16 h-16 mb-4 opacity-20" />
            <p className="text-lg font-mono">Search your codebase</p>
            <p className="text-sm mt-1">
              Index a repository, then query with natural language
            </p>
          </div>
        )}

        {search.isError && (
          <div className="max-w-4xl mx-auto px-6 py-8">
            <div className="p-4 border border-red/30 bg-red/5 rounded-lg text-sm text-red">
              {search.error.message}
            </div>
          </div>
        )}

        {result && (
          <div className="max-w-7xl mx-auto px-6 py-6 grid grid-cols-1 lg:grid-cols-5 gap-6">
            {/* Left: ranked results */}
            <div className="lg:col-span-3 space-y-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                  <h2 className="text-sm font-mono font-bold text-text-primary">
                    Results
                  </h2>
                  <span className="text-xs font-mono px-2 py-0.5 rounded-full bg-cyan/10 text-cyan border border-cyan/20">
                    {MODE_ICONS[result.classified_mode] ?? ""}{" "}
                    {result.classified_mode}
                  </span>
                </div>
                <div className="flex items-center gap-1 text-text-dim text-xs font-mono">
                  <Clock className="w-3 h-3" />
                  {result.latency_ms.toFixed(0)}ms
                  <Zap className="w-3 h-3 ml-2 text-green" />
                  {result.ranked_results.length} files
                </div>
              </div>

              {result.ranked_results.map((r, i) => (
                <ResultCard key={r.file_id} result={r} rank={i} />
              ))}
            </div>

            {/* Right: context pack */}
            <div className="lg:col-span-2">
              <div className="sticky top-6">
                <ContextPackView pack={result.context_pack} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
