import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

// ── Pure API client logic tests (no DOM needed) ──

// We test the request helper indirectly by mocking fetch
const mockFetch = vi.fn()
globalThis.fetch = mockFetch

function jsonResponse(body: unknown, status = 200) {
  return Promise.resolve({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as Response)
}

describe('API client', () => {
  beforeEach(() => {
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('listRepos sends GET /api/repos', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse([]))
    const { api } = await import('../api/client')
    const result = await api.listRepos()
    expect(mockFetch).toHaveBeenCalledWith('/api/repos', expect.objectContaining({}))
    expect(result).toEqual([])
  })

  it('indexRepo sends POST /api/repos with body', async () => {
    const fakeRepo = { id: 1, name: 'my-repo', path: '/src/my-repo', status: 'ready' }
    mockFetch.mockReturnValueOnce(jsonResponse(fakeRepo))
    const { api } = await import('../api/client')
    const body = { url: 'https://github.com/owner/my-repo' }
    const result = await api.indexRepo(body)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/repos',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(body),
      })
    )
    expect(result).toEqual(fakeRepo)
  })

  it('deleteRepo sends DELETE /api/repos/{id}', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ detail: 'Deleted' }))
    const { api } = await import('../api/client')
    await api.deleteRepo(42)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/repos/42',
      expect.objectContaining({ method: 'DELETE' })
    )
  })

  it('search sends POST /api/search with body', async () => {
    const fakeResponse = { ranked_results: [], context_pack: {}, classified_mode: 'general', latency_ms: 12, query_id: 1 }
    mockFetch.mockReturnValueOnce(jsonResponse(fakeResponse))
    const { api } = await import('../api/client')
    const req = { repo_id: 1, query: 'find auth handler', mode: null }
    await api.search(req)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/search',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify(req),
      })
    )
  })

  it('throws on non-ok response', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ detail: 'Not Found' }, 404))
    const { api } = await import('../api/client')
    await expect(api.getRepo(999)).rejects.toThrow('404')
  })

  it('getModes sends GET /api/search/modes', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse([{ name: 'general', description: 'General', keywords: [] }]))
    const { api } = await import('../api/client')
    const modes = await api.getModes()
    expect(mockFetch).toHaveBeenCalledWith('/api/search/modes', expect.objectContaining({}))
    expect(modes[0].name).toBe('general')
  })

  it('clearMemory sends DELETE /api/memory/{repoId}', async () => {
    mockFetch.mockReturnValueOnce(jsonResponse({ detail: 'Memory cleared' }))
    const { api } = await import('../api/client')
    await api.clearMemory(7)
    expect(mockFetch).toHaveBeenCalledWith(
      '/api/memory/7',
      expect.objectContaining({ method: 'DELETE' })
    )
  })
})
