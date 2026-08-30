/**
 * Small client-side version marker used to tell returning users when a new
 * frontend build is available. The access token stays in memory, so a hard
 * refresh re-authenticates through the HttpOnly refresh cookie rather than
 * logging the learner out.
 */

export const APP_VERSION = '2026-08-30.1'

const VERSION_STORAGE_KEY = 'celpip-app-version'

export function previousAppVersion(): string | null {
  try {
    return localStorage.getItem(VERSION_STORAGE_KEY)
  } catch {
    return null
  }
}

export function rememberAppVersion(): void {
  try {
    localStorage.setItem(VERSION_STORAGE_KEY, APP_VERSION)
  } catch {
    // Storage may be unavailable in private or locked-down contexts.
  }
}

export async function hardRefresh(): Promise<void> {
  if ('caches' in window) {
    try {
      const keys = await caches.keys()
      await Promise.all(keys.map((key) => caches.delete(key)))
    } catch {
      // Cache clearing is best effort; the reload below still runs.
    }
  }
  rememberAppVersion()
  window.location.reload()
}
