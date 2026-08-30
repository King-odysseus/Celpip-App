/**
 * Typed fetch client for the CELPIP API.
 *
 * Design constraints from the platform plan:
 * - The access token lives only in memory (never localStorage), so it cannot be
 *   read by injected scripts or survive a full reload — a reload re-derives it
 *   from the HttpOnly refresh cookie.
 * - Every request is same-origin with `credentials: 'include'` so the refresh
 *   cookie travels automatically.
 * - Unsafe (state-changing) requests carry the CSRF token as a header, matching
 *   the CSRF cookie the backend sets — required for cookie-mutating endpoints.
 * - A single refresh-and-retry hook lets the AuthProvider recover from one 401.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? '/api/v1').replace(/\/$/, '')

const CSRF_COOKIE = 'csrftoken'
const CSRF_HEADER = 'X-CSRFToken'

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

/** Shape of the backend's consistent error envelope. */
export class ApiError extends Error {
  readonly code: string
  readonly status: number
  readonly fields: Record<string, unknown>

  constructor(status: number, code: string, message: string, fields: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

// ── In-memory access token ────────────────────────────────────────────────────
let accessToken: string | null = null

export function setAccessToken(token: string | null): void {
  accessToken = token
}

export function getAccessToken(): string | null {
  return accessToken
}

// ── Refresh-and-retry hook (registered by the AuthProvider) ──────────────────
type RefreshHandler = () => Promise<boolean>
let refreshHandler: RefreshHandler | null = null

export function setRefreshHandler(handler: RefreshHandler | null): void {
  refreshHandler = handler
}

// ── CSRF ──────────────────────────────────────────────────────────────────────
function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`))
  return match ? decodeURIComponent(match[1]) : null
}

/** Ensure a CSRF cookie exists, fetching one from the bootstrap endpoint if not. */
export async function ensureCsrfToken(): Promise<string | null> {
  let token = readCookie(CSRF_COOKIE)
  if (!token) {
    await fetch(`${BASE_URL}/auth/csrf/`, { method: 'GET', credentials: 'include' })
    token = readCookie(CSRF_COOKIE)
  }
  return token
}

function isAuthPath(path: string): boolean {
  return path.startsWith('/auth/')
}

type RequestOptions = {
  method?: string
  body?: unknown
  headers?: Record<string, string>
  /** Internal: prevents infinite retry loops after a refresh attempt. */
  _retry?: boolean
}

type Paginated<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  const headers: Record<string, string> = { ...options.headers }
  const formBody = options.body instanceof FormData

  if (options.body !== undefined && !formBody) headers['Content-Type'] = 'application/json'
  if (accessToken) headers['Authorization'] = `Bearer ${accessToken}`
  if (UNSAFE_METHODS.has(method)) {
    const csrf = await ensureCsrfToken()
    if (csrf) headers[CSRF_HEADER] = csrf
  }

  const requestBody: BodyInit | undefined = options.body === undefined
    ? undefined
    : formBody
      ? options.body as FormData
      : JSON.stringify(options.body)

  const response = await fetch(`${BASE_URL}${path}`, {
    method,
    headers,
    credentials: 'include',
    body: requestBody,
  })

  // One transparent refresh-and-retry after an access-token expiry.
  if (
    response.status === 401 &&
    !options._retry &&
    !isAuthPath(path) &&
    refreshHandler
  ) {
    const refreshed = await refreshHandler()
    if (refreshed) return request<T>(path, { ...options, _retry: true })
  }

  return parseResponse<T>(response)
}

async function requestBlob(
  path: string,
  headers: Record<string, string> = {},
  retried = false,
): Promise<Blob> {
  const requestHeaders = { ...headers }
  if (accessToken) requestHeaders.Authorization = `Bearer ${accessToken}`
  const url = path.startsWith(BASE_URL) ? path : `${BASE_URL}${path}`
  const response = await fetch(url, {
    method: 'GET',
    headers: requestHeaders,
    credentials: 'include',
  })
  if (response.status === 401 && !retried && !isAuthPath(path) && refreshHandler) {
    const refreshed = await refreshHandler()
    if (refreshed) return requestBlob(path, headers, true)
  }
  if (!response.ok) return parseResponse<never>(response)
  return response.blob()
}

async function parseResponse<T>(response: Response): Promise<T> {
  if (response.status === 204 || response.status === 205) {
    return undefined as T
  }

  let data: unknown = null
  const text = await response.text()
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }

  if (!response.ok) {
    const envelope = (data ?? {}) as {
      code?: string
      message?: string
      fields?: Record<string, unknown>
    }
    throw new ApiError(
      response.status,
      envelope.code ?? 'error',
      envelope.message ?? 'Request failed.',
      envelope.fields ?? {},
    )
  }

  return data as T
}

/**
 * Load a paginated DRF endpoint completely, following ``next`` links until the
 * backend has no further pages. Catalog pages use this so a bank larger than
 * the server page size does not silently drop later items.
 */
export async function fetchAllPages<T>(path: string): Promise<T[]> {
  let current: string | null = path
  const items: T[] = []

  while (current) {
    const page: Paginated<T> = await request<Paginated<T>>(current)
    items.push(...page.results)
    current = page.next ? normalizeNextPage(page.next) : null
  }

  return items
}

function normalizeNextPage(next: string): string {
  const marker = '/api/v1'
  const url = new URL(next, window.location.origin)
  let pathname = url.pathname
  if (pathname.startsWith(marker)) {
    pathname = pathname.slice(marker.length) || '/'
  }
  return pathname + url.search
}

export const api = {
  get: <T>(path: string, headers?: Record<string, string>) => request<T>(path, { headers }),
  post: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>(path, { method: 'POST', body, headers }),
  put: <T>(path: string, body?: unknown, headers?: Record<string, string>) =>
    request<T>(path, { method: 'PUT', body, headers }),
  getBlob: (path: string, headers?: Record<string, string>) => requestBlob(path, headers),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: 'PATCH', body }),
  // DELETE accepts an optional JSON body (e.g. account-deletion confirmation)
  // while remaining backwards-compatible with the common no-body call sites.
  del: <T>(path: string, body?: unknown) => request<T>(path, { method: 'DELETE', body }),
}
