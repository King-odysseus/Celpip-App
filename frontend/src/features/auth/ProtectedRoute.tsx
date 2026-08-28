import { type ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from './AuthProvider'

/**
 * Gate for features that persist to the account (e.g. Account settings).
 *
 * Sample Learn/Practice pages stay public; only routes wrapped here require a
 * session. While the initial refresh-on-load is in flight we show a neutral
 * loading state instead of bouncing an authenticated user to sign-in.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth()
  const location = useLocation()

  if (status === 'loading') {
    return (
      <p role="status" className="py-12 text-center text-sm text-muted">
        Checking your session…
      </p>
    )
  }

  if (status === 'anonymous') {
    return <Navigate to="/signin" replace state={{ from: location.pathname }} />
  }

  return <>{children}</>
}
