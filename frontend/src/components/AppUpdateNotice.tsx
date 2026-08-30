import { useState } from 'react'
import { RefreshCw, X } from 'lucide-react'
import {
  APP_VERSION,
  hardRefresh,
  previousAppVersion,
  rememberAppVersion,
} from '../lib/appUpdate'

/**
 * Shown once after a returning browser has an older app version recorded. The
 * marker is advanced immediately so a dismissed notice does not reappear on
 * every route or reload.
 */
export function AppUpdateNotice() {
  const [visible, setVisible] = useState(() => {
    const previous = previousAppVersion()
    const hasUpdate = previous !== null && previous !== APP_VERSION
    rememberAppVersion()
    return hasUpdate
  })

  if (!visible) return null

  return (
    <div
      role="status"
      className="mx-auto mb-5 flex max-w-5xl flex-wrap items-center gap-3 rounded-xl border border-brand/30 bg-brand-soft px-4 py-3 text-sm text-ink"
    >
      <RefreshCw size={18} className="shrink-0 text-brand" aria-hidden="true" />
      <span className="min-w-0 flex-1 font-medium">
        A new question bank is available. Hard refresh to load the latest content.
      </span>
      <button
        type="button"
        onClick={() => void hardRefresh()}
        className="flex min-h-11 items-center gap-2 rounded-full bg-brand px-4 text-sm font-semibold text-white transition hover:opacity-90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <RefreshCw size={17} aria-hidden="true" />
        Refresh now
      </button>
      <button
        type="button"
        onClick={() => setVisible(false)}
        aria-label="Dismiss update notice"
        className="flex h-11 w-11 items-center justify-center rounded-full text-muted transition hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <X size={19} aria-hidden="true" />
      </button>
    </div>
  )
}
