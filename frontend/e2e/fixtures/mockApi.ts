import type { Page, Route } from '@playwright/test'

type Handler = (route: Route) => unknown | Promise<unknown>

/**
 * Intercept every /api/v1/** request the app makes and answer deterministically,
 * routed by "METHOD /path" (path relative to the API base) — the same
 * convention as frontend/src/test/mockFetch.ts's installRouteFetch, so a
 * fixture reads the same way whether it backs a Vitest or a Playwright test.
 *
 * A handler may return a plain value (sent as 200 JSON), `{ status, body }`,
 * or call `route.fulfill(...)` itself for full control.
 */
export async function mockApi(page: Page, routes: Record<string, Handler>) {
  await page.route('**/api/v1/**', async (route) => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    const path = url.pathname.replace(/^\/api\/v1/, '') || '/'
    const handler = routes[`${method} ${path}`] ?? routes[path]
    if (!handler) {
      await route.fulfill({ status: 404, json: { code: 'not_found', message: 'no fixture', fields: {} } })
      return
    }
    const result = await handler(route)
    if (result === undefined) return // handler already called route.fulfill/continue/abort
    if (result && typeof result === 'object' && 'status' in result && 'body' in result) {
      const { status, body } = result as { status: number; body: unknown }
      await route.fulfill({ status, json: body })
      return
    }
    await route.fulfill({ status: 200, json: result })
  })
}

export const USER = { id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }

export const PROFILE = {
  identifier: 'learner',
  exam_date: null,
  target_level: 9,
  target_listening: null,
  target_reading: null,
  target_writing: null,
  target_speaking: null,
  daily_minutes: 30,
  preferred_weekdays: [1, 2, 3, 4, 5],
  timezone: 'America/Toronto',
  practice_narration_voice: 'automatic',
  updated_at: '2026-08-29T00:00:00Z',
}

/** Routes every authenticated page needs on load, before any page-specific fixture. */
export const authBootstrap: Record<string, Handler> = {
  'GET /auth/csrf/': () => ({ detail: 'ok' }),
  'POST /auth/refresh/': () => ({ access: 'e2e-access-token' }),
  'GET /me/': () => USER,
  'GET /me/profile/': () => PROFILE,
}
