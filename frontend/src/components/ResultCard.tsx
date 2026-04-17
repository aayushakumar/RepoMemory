import { useState } from "react";
import { ChevronDown, ChevronRight, FileCode2, Zap } from "lucide-react";
import type { RankedResult } from "../api/types";
import CodeBlock from "./CodeBlock";

interface Props {
  result: RankedResult;
  rank: number;
}

const EXT_COLORS: Record<string, string> = {
  ".py": "text-yellow",
  ".js": "text-yellow",
  ".jsx": "text-cyan",
  ".ts": "text-cyan",
  ".tsx": "text-cyan",
};

function scoreBar(score: number, color: string) {
  const pct = Math.round(score * 100);
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className="w-20 h-1.5 bg-bg-tertiary rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-text-dim w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function ResultCard({ result, rank }: Props) {
  const [open, setOpen] = useState(rank === 0);
  const ext = "." + (result.file_path.split(".").pop() ?? "");
  const extColor = EXT_COLORS[ext] ?? "text-text-secondary";

  return (
    <div className="border border-border rounded-lg overflow-hidden transition-all hover:border-border-active">
      {/* Header */}
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-bg-hover transition-colors"
      >
        {open ? (
          <ChevronDown className="w-4 h-4 text-text-dim shrink-0" />
        ) : (
          <ChevronRight className="w-4 h-4 text-text-dim shrink-0" />
        )}

        <span className="text-xs font-mono font-bold text-text-dim w-6">
          #{rank + 1}
        </span>

        <FileCode2 className={`w-4 h-4 shrink-0 ${extColor}`} />

        <span className="font-mono text-sm text-text-primary truncate flex-1">
          {result.file_path}
        </span>

        <div className="flex items-center gap-1">
          <Zap className="w-3 h-3 text-cyan" />
          <span className="text-xs font-mono text-cyan">
            {(result.combined_score * 100).toFixed(1)}
          </span>
        </div>
      </button>

      {/* Detail */}
      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-border bg-bg-primary/50">
          {/* Score breakdown */}
          <div className="grid grid-cols-2 gap-x-6 gap-y-1 pt-3">
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Lexical</span>
              {scoreBar(result.component_scores.lexical, "bg-yellow")}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Semantic</span>
              {scoreBar(result.component_scores.semantic, "bg-cyan")}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Path</span>
              {scoreBar(result.component_scores.path_match, "bg-green")}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Symbol</span>
              {scoreBar(result.component_scores.symbol_match, "bg-red")}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Memory</span>
              {scoreBar(result.component_scores.memory_frecency, "bg-green/70")}
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs text-text-dim">Deps</span>
              {scoreBar(result.component_scores.dependency_graph, "bg-purple-400")}
            </div>
          </div>

          {/* Explanation */}
          {result.explanation && (
            <p className="text-xs text-text-secondary italic border-l-2 border-cyan/30 pl-3">
              {result.explanation}
            </p>
          )}

          {/* Snippets */}
          {result.snippets.map((s, i) => (
            <div key={i} className="space-y-1">
              {s.symbol_name && (
                <span className="text-xs font-mono text-green">
                  {s.symbol_name}
                </span>
              )}
              <div className="text-[10px] text-text-dim font-mono">
                Lines {s.start_line}–{s.end_line} · {s.token_count} tokens
              </div>
              <CodeBlock code={s.content} language={ext.replace(".", "")} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
