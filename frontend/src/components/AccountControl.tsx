import { Link } from 'react-router-dom'
import { LogIn, UserPlus, UserRound } from 'lucide-react'
import { useAuth } from '../features/auth/AuthProvider'

/** Shared pill geometry; display utility is applied per-use so visibility can
 * differ by breakpoint (the account link is desktop-only, the anonymous
 * sign-in/up actions stay visible on every size). */
const pillBase =
  'min-h-11 items-center gap-2 rounded-full px-3 py-2.5 text-sm font-medium ' +
  'whitespace-nowrap transition-colors sm:px-3.5 ' +
  'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand'

const accountClass = `hidden lg:flex ${pillBase} text-muted hover:text-ink`
/** Secondary action for anonymous visitors. */
const signInClass = `flex ${pillBase} text-ink hover:text-brand`
/** Prominent primary CTA for anonymous visitors. */
const signUpClass = `flex ${pillBase} bg-brand text-white hover:opacity-90`

/**
 * Header account control. Signed in → an Account link (desktop; mobile reaches
 * the account via the bottom nav). Signed out → both Sign in and Sign up, kept
 * visible on desktop and mobile so a logged-out visitor always sees both.
 */
export function AccountControl() {
  const { status, user } = useAuth()

  if (status === 'loading') {
    return <span className="min-h-11 w-px" aria-hidden="true" />
  }

  if (status === 'authenticated') {
    return (
      <Link to="/account" className={accountClass} aria-label="Account">
        <UserRound size={18} strokeWidth={1.9} />
        <span className="hidden max-w-32 truncate sm:inline">
          {user?.identifier ?? 'Account'}
        </span>
      </Link>
    )
  }

  return (
    <div className="flex items-center gap-1">
      <Link to="/signin" className={signInClass}>
        <LogIn size={18} strokeWidth={1.9} className="hidden sm:block" />
        <span>Sign in</span>
      </Link>
      <Link to="/register" className={signUpClass}>
        <UserPlus size={18} strokeWidth={1.9} className="hidden sm:block" />
        <span>Sign up</span>
      </Link>
    </div>
  )
}
