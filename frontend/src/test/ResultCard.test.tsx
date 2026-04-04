import { describe, it, expect } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import ResultCard from '../components/ResultCard'
import type { RankedResult } from '../api/types'

const scores = {
  lexical: 0.8,
  semantic: 0.6,
  path_match: 0.4,
  symbol_match: 0.9,
  memory_frecency: 0.2,
  git_recency: 0.1,
}

const mockResult: RankedResult = {
  file_id: 1,
  file_path: 'auth/token_handler.py',
  chunk_ids: [10, 11],
  symbol_ids: [5],
  combined_score: 0.87,
  component_scores: scores,
  explanation: 'High lexical match for "token rotation"; contains rotate_token()',
  snippets: [
    {
      content: 'def rotate_token(user_id: str):\n    pass',
      start_line: 45,
      end_line: 60,
      symbol_name: 'rotate_token',
      token_count: 32,
    },
  ],
}

describe('ResultCard', () => {
  it('renders file path', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    expect(screen.getByText('auth/token_handler.py')).toBeInTheDocument()
  })

  it('shows rank number', () => {
    render(<ResultCard result={mockResult} rank={2} />)
    expect(screen.getByText('#3')).toBeInTheDocument()
  })

  it('shows combined score as percentage', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    // 0.87 * 100 = 87.0
    expect(screen.getByText('87.0')).toBeInTheDocument()
  })

  it('is expanded by default when rank is 0', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    expect(screen.getByText(mockResult.explanation)).toBeInTheDocument()
  })

  it('is collapsed by default when rank > 0', () => {
    render(<ResultCard result={mockResult} rank={1} />)
    expect(screen.queryByText(mockResult.explanation)).not.toBeInTheDocument()
  })

  it('expands on click when collapsed', () => {
    render(<ResultCard result={mockResult} rank={1} />)
    const header = screen.getByRole('button')
    fireEvent.click(header)
    expect(screen.getByText(mockResult.explanation)).toBeInTheDocument()
  })

  it('collapses on second click', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    const header = screen.getByRole('button')
    fireEvent.click(header) // collapse
    expect(screen.queryByText(mockResult.explanation)).not.toBeInTheDocument()
  })

  it('shows symbol name when expanded', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    // symbol name appears at least once (may also appear in syntax-highlighted code)
    expect(screen.getAllByText('rotate_token').length).toBeGreaterThan(0)
  })

  it('shows snippet line range when expanded', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    expect(screen.getByText(/Lines 45/)).toBeInTheDocument()
  })

  it('renders score bars for lexical and semantic', () => {
    render(<ResultCard result={mockResult} rank={0} />)
    expect(screen.getByText('Lexical')).toBeInTheDocument()
    expect(screen.getByText('Semantic')).toBeInTheDocument()
  })
})
