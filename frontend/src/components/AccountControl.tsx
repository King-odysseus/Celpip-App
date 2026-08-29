import { Link } from 'react-router-dom'
import { LogIn, UserRound } from 'lucide-react'
import { useAuth } from '../features/auth/AuthProvider'

const linkClass =
  'flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium ' +
  'whitespace-nowrap text-muted transition-colors hover:text-ink ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

/** Prominent sign-in CTA for anonymous visitors; matches the header pill sizing. */
const signInClass =
  'flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium ' +
  'whitespace-nowrap text-white bg-brand transition-colors hover:opacity-90 ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

/** Header control: Account when signed in, otherwise a Sign in link. */
export function AccountControl() {
  const { status, user } = useAuth()

  if (status === 'loading') {
    return <span className="min-h-11 w-px" aria-hidden="true" />
  }

  if (status === 'authenticated') {
    return (
      <Link to="/account" className={linkClass} aria-label="Account">
        <UserRound size={18} strokeWidth={1.9} />
        <span className="hidden max-w-32 truncate sm:inline">
          {user?.identifier ?? 'Account'}
        </span>
      </Link>
    )
  }

  return (
    <Link to="/signin" className={signInClass}>
      <LogIn size={18} strokeWidth={1.9} />
      <span>Sign in</span>
    </Link>
  )
}
