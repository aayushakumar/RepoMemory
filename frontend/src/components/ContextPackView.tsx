import { Copy, FileJson, FileText } from "lucide-react";
import type { ContextPack } from "../api/types";

interface Props {
  pack: ContextPack;
}

function toMarkdown(pack: ContextPack): string {
  let md = `## Context Pack: "${pack.query}"\nMode: ${pack.mode} | Tokens: ${pack.total_tokens}/${pack.budget} (${pack.budget_used_pct.toFixed(1)}%)\n\n`;
  for (const f of pack.files) {
    md += `### ${f.path} (score: ${f.relevance_score.toFixed(2)})\n`;
    md += `**Why:** ${f.reason}\n`;
    for (const s of f.snippets) {
      const ext = f.path.split(".").pop() ?? "";
      md += `\`\`\`${ext}\n// lines ${s.start_line}-${s.end_line}\n${s.content}\n\`\`\`\n`;
    }
    md += "\n";
  }
  return md;
}

function toJson(pack: ContextPack): string {
  return JSON.stringify(pack, null, 2);
}

async function copyText(text: string) {
  await navigator.clipboard.writeText(text);
}

export default function ContextPackView({ pack }: Props) {
  const pct = pack.budget_used_pct;
  const barColor =
    pct > 90 ? "bg-red" : pct > 70 ? "bg-yellow" : "bg-green";

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-mono font-bold text-text-primary">
          Context Pack
        </h3>
        <div className="flex gap-1">
          <button
            onClick={() => copyText(toMarkdown(pack))}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-bg-tertiary hover:bg-bg-hover border border-border rounded-md text-text-secondary hover:text-text-primary transition-colors"
            title="Copy as Markdown"
          >
            <FileText className="w-3 h-3" />
            MD
          </button>
          <button
            onClick={() => copyText(toJson(pack))}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-bg-tertiary hover:bg-bg-hover border border-border rounded-md text-text-secondary hover:text-text-primary transition-colors"
            title="Copy as JSON"
          >
            <FileJson className="w-3 h-3" />
            JSON
          </button>
          <button
            onClick={() => copyText(toMarkdown(pack))}
            className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs bg-cyan/10 hover:bg-cyan/20 border border-cyan/20 rounded-md text-cyan transition-colors"
            title="Copy to clipboard"
          >
            <Copy className="w-3 h-3" />
            Copy
          </button>
        </div>
      </div>

      {/* Budget bar */}
      <div className="space-y-1">
        <div className="flex justify-between text-xs font-mono">
          <span className="text-text-dim">Token Budget</span>
          <span className="text-text-secondary">
            {pack.total_tokens.toLocaleString()} / {pack.budget.toLocaleString()}
          </span>
        </div>
        <div className="h-2 bg-bg-tertiary rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barColor}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
        <div className="text-right text-[10px] text-text-dim font-mono">
          {pct.toFixed(1)}% used
        </div>
      </div>

      {/* Files */}
      <div className="space-y-3">
        {pack.files.map((f, i) => (
          <div
            key={i}
            className="border border-border rounded-lg p-3 bg-bg-primary/50"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-mono text-xs text-cyan truncate">
                {f.path}
              </span>
              <span className="text-[10px] font-mono text-text-dim">
                {(f.relevance_score * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-[11px] text-text-dim italic mb-2">{f.reason}</p>
            {f.snippets.map((s, j) => (
              <div
                key={j}
                className="font-mono text-[12px] text-text-secondary bg-bg-secondary rounded p-2 mt-1 overflow-x-auto whitespace-pre"
              >
                {s.content.length > 500
                  ? s.content.slice(0, 500) + "\n// ... truncated"
                  : s.content}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
