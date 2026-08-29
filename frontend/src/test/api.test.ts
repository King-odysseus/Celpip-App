import { describe, expect, it, vi } from 'vitest'
import { api, setAccessToken, setRefreshHandler } from '../lib/api'
import { jsonResponse } from './mockFetch'

describe('api client', () => {
  it('attaches the in-memory access token and includes credentials', async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ ok: true }),
    )
    vi.stubGlobal('fetch', fetchMock)
    setAccessToken('tok-123')

    await api.get('/me/')

    const init = fetchMock.mock.calls[0][1] as RequestInit
    const headers = init.headers as Record<string, string>
    expect(headers.Authorization).toBe('Bearer tok-123')
    expect(init.credentials).toBe('include')
  })

  it('sends the CSRF header on unsafe requests', async () => {
    document.cookie = 'csrftoken=csrf-xyz'
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      jsonResponse({ ok: true }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.post('/auth/logout/')

    const lastCall = fetchMock.mock.calls.at(-1)!
    const headers = (lastCall[1] as RequestInit).headers as Record<string, string>
    expect(headers['X-CSRFToken']).toBe('csrf-xyz')
  })

  it('serializes an optional DELETE body and sends the CSRF header', async () => {
    document.cookie = 'csrftoken=csrf-xyz'
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      new Response(null, { status: 204 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.del('/me/', { password: 'secret1' })

    const lastCall = fetchMock.mock.calls.at(-1)!
    const init = lastCall[1] as RequestInit
    expect(init.method).toBe('DELETE')
    expect(init.body).toBe(JSON.stringify({ password: 'secret1' }))
    const headers = init.headers as Record<string, string>
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['X-CSRFToken']).toBe('csrf-xyz')
  })

  it('still calls DELETE without a body for existing callers', async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) =>
      new Response(null, { status: 204 }),
    )
    vi.stubGlobal('fetch', fetchMock)

    await api.del('/some/resource/')

    const init = fetchMock.mock.calls.at(-1)![1] as RequestInit
    expect(init.method).toBe('DELETE')
    expect(init.body).toBeUndefined()
  })

  it('refreshes once and retries after a 401', async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(jsonResponse({ code: 'x', message: 'x' }, 401))
      .mockResolvedValueOnce(jsonResponse({ id: 1 }))
    vi.stubGlobal('fetch', fetchMock)

    const refresh = vi.fn(async () => {
      setAccessToken('refreshed')
      return true
    })
    setRefreshHandler(refresh)

    const result = await api.get<{ id: number }>('/me/')

    expect(refresh).toHaveBeenCalledOnce()
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(result).toEqual({ id: 1 })
  })

  it('does not retry when refresh fails', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ code: 'y', message: 'y' }, 401))
    vi.stubGlobal('fetch', fetchMock)
    setRefreshHandler(async () => false)

    await expect(api.get('/me/')).rejects.toMatchObject({ status: 401 })
    // One original call + no successful retry.
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('throws a typed ApiError carrying the backend code', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({ code: 'invalid_credentials', message: 'bad' }, 401)),
    )
    await expect(api.get('/me/')).rejects.toMatchObject({
      code: 'invalid_credentials',
      status: 401,
    })
  })
})
