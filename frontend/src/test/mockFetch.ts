import { vi } from 'vitest'

type Handler = (init: RequestInit) => Response | Promise<Response>

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

export function errorResponse(code: string, status: number, message = 'error'): Response {
  return jsonResponse({ code, message, fields: {} }, status)
}

/**
 * Install a fetch mock that routes by "METHOD /path" (path relative to the API
 * base). Unmatched routes return 404. Returns the underlying vi.fn spy.
 */
export function installRouteFetch(routes: Record<string, Handler>) {
  const spy = vi.fn(async (url: string, init: RequestInit = {}) => {
    const method = (init.method ?? 'GET').toUpperCase()
    const path = new URL(url, 'http://localhost').pathname.replace(/^\/api\/v1/, '')
    const handler = routes[`${method} ${path}`] ?? routes[path]
    if (!handler) return errorResponse('not_found', 404)
    return handler(init)
  })
  vi.stubGlobal('fetch', spy)
  return spy
}
