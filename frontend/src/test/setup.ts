import '@testing-library/jest-dom/vitest'
import { afterEach, beforeEach, vi } from 'vitest'
import { cleanup } from '@testing-library/react'
import { setAccessToken, setRefreshHandler } from '../lib/api'

/**
 * Default network stub: every request 401s, so the AuthProvider bootstrap
 * resolves to "anonymous" without touching the real network. Tests that need
 * specific responses override `global.fetch` with their own mock.
 */
function unauthorizedResponse() {
  return new Response(
    JSON.stringify({ code: 'not_authenticated', message: 'No session.', fields: {} }),
    { status: 401, headers: { 'Content-Type': 'application/json' } },
  )
}

beforeEach(() => {
  vi.stubGlobal('fetch', vi.fn(async () => unauthorizedResponse()))
})

afterEach(() => {
  cleanup()
  localStorage.clear()
  document.documentElement.removeAttribute('data-theme')
  // Reset the module-level auth state shared by the API client.
  setAccessToken(null)
  setRefreshHandler(null)
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
})

// jsdom does not implement matchMedia; provide a light stub so components that
// read prefers-color-scheme / reduced-motion do not throw under test.
if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
}

// jsdom does not implement rAF timing used by the Meter animation.
if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = ((cb: FrameRequestCallback) =>
    setTimeout(() => cb(performance.now()), 0)) as unknown as typeof requestAnimationFrame
  window.cancelAnimationFrame = ((id: number) =>
    clearTimeout(id)) as unknown as typeof cancelAnimationFrame
}
