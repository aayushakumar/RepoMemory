import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import Sidebar from '../components/Sidebar'

function renderSidebar(path = '/') {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Sidebar />
    </MemoryRouter>
  )
}

describe('Sidebar', () => {
  it('renders the RepoMemory brand name', () => {
    renderSidebar()
    expect(screen.getByText('RepoMemory')).toBeInTheDocument()
  })

  it('renders tagline', () => {
    renderSidebar()
    expect(screen.getByText('AI code retrieval engine')).toBeInTheDocument()
  })

  it('renders all three navigation links', () => {
    renderSidebar()
    expect(screen.getByText('Search')).toBeInTheDocument()
    expect(screen.getByText('Repositories')).toBeInTheDocument()
    expect(screen.getByText('Memory')).toBeInTheDocument()
  })

  it('marks the Search link as active on /', () => {
    renderSidebar('/')
    const link = screen.getByRole('link', { name: /search/i })
    // active links get the cyan border class
    expect(link.className).toContain('text-cyan')
  })

  it('marks the Repositories link as active on /repos', () => {
    renderSidebar('/repos')
    const link = screen.getByRole('link', { name: /repositories/i })
    expect(link.className).toContain('text-cyan')
  })

  it('marks the Memory link as active on /memory', () => {
    renderSidebar('/memory')
    const link = screen.getByRole('link', { name: /memory/i })
    expect(link.className).toContain('text-cyan')
  })

  it('renders version badge', () => {
    renderSidebar()
    expect(screen.getByText('v0.2.0')).toBeInTheDocument()
  })
})
