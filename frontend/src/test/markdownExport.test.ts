import { describe, it, expect } from 'vitest'

// ── Pure unit tests for the export helpers inside ContextPackView ──
// We recreate the same functions here since they aren't exported.
// If you ever extract them, import directly.

import type { ContextPack } from '../api/types'

function toMarkdown(pack: ContextPack): string {
  let md = `## Context Pack: "${pack.query}"\nMode: ${pack.mode} | Tokens: ${pack.total_tokens}/${pack.budget} (${pack.budget_used_pct.toFixed(1)}%)\n\n`
  for (const f of pack.files) {
    md += `### ${f.path} (score: ${f.relevance_score.toFixed(2)})\n`
    md += `**Why:** ${f.reason}\n`
    for (const s of f.snippets) {
      const ext = f.path.split('.').pop() ?? ''
      md += `\`\`\`${ext}\n// lines ${s.start_line}-${s.end_line}\n${s.content}\n\`\`\`\n`
    }
    md += '\n'
  }
  return md
}

const pack: ContextPack = {
  query: 'token rotation bug',
  mode: 'bug_fix',
  files: [
    {
      path: 'auth/token_handler.py',
      relevance_score: 0.92,
      reason: 'Contains rotate_token()',
      snippets: [
        { content: 'def rotate_token(): pass', start_line: 10, end_line: 12, symbol_name: 'rotate_token', token_count: 10 },
      ],
    },
  ],
  total_tokens: 200,
  budget: 8000,
  budget_used_pct: 2.5,
}

describe('Markdown export', () => {
  it('includes the query in the header', () => {
    expect(toMarkdown(pack)).toContain('token rotation bug')
  })

  it('includes mode name', () => {
    expect(toMarkdown(pack)).toContain('bug_fix')
  })

  it('includes token count / budget', () => {
    expect(toMarkdown(pack)).toContain('200/8000')
  })

  it('includes file path as section header', () => {
    expect(toMarkdown(pack)).toContain('### auth/token_handler.py')
  })

  it('includes relevance score', () => {
    expect(toMarkdown(pack)).toContain('score: 0.92')
  })

  it('includes reason text', () => {
    expect(toMarkdown(pack)).toContain('Contains rotate_token()')
  })

  it('includes code fence with file extension', () => {
    expect(toMarkdown(pack)).toContain('```py')
  })

  it('includes line range comment', () => {
    expect(toMarkdown(pack)).toContain('// lines 10-12')
  })

  it('includes snippet content', () => {
    expect(toMarkdown(pack)).toContain('def rotate_token(): pass')
  })
})
