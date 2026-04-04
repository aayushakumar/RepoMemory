import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ContextPackView from '../components/ContextPackView'
import type { ContextPack } from '../api/types'

const mockPack: ContextPack = {
  query: 'Where is token rotation handled?',
  mode: 'bug_fix',
  files: [
    {
      path: 'auth/token_handler.py',
      relevance_score: 0.92,
      reason: 'High lexical match; contains rotate_token()',
      snippets: [
        {
          content: 'def rotate_token(user_id: str):\n    ...',
          start_line: 45,
          end_line: 60,
          symbol_name: 'rotate_token',
          token_count: 32,
        },
      ],
    },
  ],
  total_tokens: 512,
  budget: 8000,
  budget_used_pct: 6.4,
}

describe('ContextPackView', () => {
  beforeEach(() => {
    Object.assign(navigator, {
      clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
    })
  })

  it('renders the query', () => {
    render(<ContextPackView pack={mockPack} />)
    expect(screen.getByText('Context Pack')).toBeInTheDocument()
  })

  it('shows token usage', () => {
    render(<ContextPackView pack={mockPack} />)
    expect(screen.getByText('512 / 8,000')).toBeInTheDocument()
  })

  it('shows budget percentage', () => {
    render(<ContextPackView pack={mockPack} />)
    expect(screen.getByText('6.4% used')).toBeInTheDocument()
  })

  it('renders file path', () => {
    render(<ContextPackView pack={mockPack} />)
    expect(screen.getByText('auth/token_handler.py')).toBeInTheDocument()
  })

  it('renders relevance reason', () => {
    render(<ContextPackView pack={mockPack} />)
    expect(screen.getByText('High lexical match; contains rotate_token()')).toBeInTheDocument()
  })

  it('copies markdown when MD button clicked', async () => {
    render(<ContextPackView pack={mockPack} />)
    fireEvent.click(screen.getByTitle('Copy as Markdown'))
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('Context Pack: "Where is token rotation handled?"')
    )
  })

  it('copies JSON when JSON button clicked', async () => {
    render(<ContextPackView pack={mockPack} />)
    fireEvent.click(screen.getByTitle('Copy as JSON'))
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining('"query"')
    )
  })

  it('copy button triggers clipboard write', async () => {
    render(<ContextPackView pack={mockPack} />)
    fireEvent.click(screen.getByTitle('Copy to clipboard'))
    expect(navigator.clipboard.writeText).toHaveBeenCalled()
  })
})
