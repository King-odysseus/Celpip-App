import { RefreshCw } from 'lucide-react'
import { hardRefresh } from '../lib/appUpdate'

const iconClass =
  'flex h-11 w-11 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

const labeledClass =
  'flex min-h-11 items-center justify-center gap-2 rounded-2xl border border-line-light px-3 py-2 text-sm font-semibold text-ink transition-colors hover:bg-surface-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

export function HardRefreshButton({
  variant = 'icon',
}: {
  variant?: 'icon' | 'labeled'
}) {
  if (variant === 'labeled') {
    return (
      <button
        type="button"
        onClick={() => void hardRefresh()}
        aria-label="Hard refresh latest content"
        className={labeledClass}
      >
        <RefreshCw size={19} aria-hidden="true" />
        <span>Refresh latest</span>
      </button>
    )
  }

  return (
    <button
      type="button"
      onClick={() => void hardRefresh()}
      aria-label="Hard refresh latest content"
      title="Hard refresh latest content"
      className={iconClass}
    >
      <RefreshCw size={21} aria-hidden="true" />
    </button>
  )
}
