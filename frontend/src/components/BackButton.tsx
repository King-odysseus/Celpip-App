import { ArrowLeft } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

/**
 * Returns to the previous in-app page. In-app entries carry a router-generated
 * key; direct/refreshed entries use the sentinel 'default' key, so there is no
 * previous in-app page to return to and the button goes to `fallback` instead.
 */
export function BackButton({ fallback = '/', className = '' }: { fallback?: string; className?: string }) {
  const location = useLocation()
  const navigate = useNavigate()

  return (
    <button
      type="button"
      onClick={() => {
        if (location.key !== 'default') navigate(-1)
        else navigate(fallback, { replace: true })
      }}
      aria-label="Go back"
      className={`flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${className}`}
    >
      <ArrowLeft size={16} aria-hidden="true" />
      <span>Back</span>
    </button>
  )
}
