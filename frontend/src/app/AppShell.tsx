import { useEffect, useRef, useState, type RefObject } from 'react'
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom'
import { GraduationCap, LogIn, MoreHorizontal, UserRound, X } from 'lucide-react'
import {
  mobileOverflowNav,
  mobilePrimaryNav,
  primaryNav,
} from './navigation'
import { ThemeToggle } from '../components/ThemeToggle'
import { AccountControl } from '../components/AccountControl'
import { useAuth } from '../features/auth/AuthProvider'

function MoreSheet({
  open,
  onClose,
  triggerRef,
}: {
  open: boolean
  onClose: () => void
  triggerRef: RefObject<HTMLButtonElement | null>
}) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const { status, logout } = useAuth()

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
        return
      }
      if (e.key !== 'Tab' || !panelRef.current) return

      const focusable = Array.from(
        panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      )
      if (!focusable.length) return
      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement

      if (e.shiftKey && (active === first || !panelRef.current.contains(active))) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && active === last) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('keydown', onKey)
      triggerRef.current?.focus()
    }
  }, [open, onClose, triggerRef])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        className="absolute inset-0 bg-black/40"
        aria-label="Close menu"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="more-sheet-title"
        className="absolute right-3 bottom-[calc(6rem+env(safe-area-inset-bottom))] left-3 mx-auto max-w-lg animate-scale-in rounded-3xl border border-line bg-surface p-3 shadow-elevated"
      >
        <div className="mb-1 flex items-center justify-between px-2">
          <span id="more-sheet-title" className="eyebrow">More destinations</span>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close menu"
            className="flex h-11 w-11 items-center justify-center rounded-full text-muted hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <X size={20} />
          </button>
        </div>
        <div className="grid grid-cols-2 gap-2">
          {mobileOverflowNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={onClose}
              className={({ isActive }) =>
                `flex min-h-16 flex-col items-center justify-center gap-1.5 rounded-2xl px-2 text-sm font-semibold transition-colors ${
                  isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-surface-secondary hover:text-ink'
                }`
              }
            >
              <item.icon size={22} strokeWidth={1.9} />
              <span>{item.label}</span>
            </NavLink>
          ))}
          {status === 'authenticated' ? (
            <NavLink
              to="/account"
              onClick={onClose}
              className={({ isActive }) =>
                `col-span-2 flex min-h-16 flex-col items-center justify-center gap-1.5 rounded-2xl px-2 text-sm font-semibold transition-colors ${
                  isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:bg-surface-secondary hover:text-ink'
                }`
              }
            >
              <UserRound size={22} strokeWidth={1.9} />
              <span>Account</span>
            </NavLink>
          ) : (
            <NavLink
              to="/signin"
              onClick={onClose}
              className="col-span-2 flex min-h-16 flex-col items-center justify-center gap-1.5 rounded-2xl px-2 text-sm font-semibold text-muted transition-colors hover:bg-surface-secondary hover:text-ink"
            >
              <LogIn size={22} strokeWidth={1.9} />
              <span>Sign in</span>
            </NavLink>
          )}
          <div className="col-span-2 flex items-center justify-between rounded-2xl border border-line-light px-3 py-2">
            <span className="text-sm font-medium text-ink">Theme</span>
            <ThemeToggle />
          </div>
          {status === 'authenticated' && (
            <button
              type="button"
              onClick={() => {
                onClose()
                void logout()
              }}
              className="col-span-2 flex min-h-11 items-center justify-center rounded-2xl px-2 text-sm font-semibold text-muted transition-colors hover:bg-surface-secondary hover:text-ink"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export function AppShell() {
  const location = useLocation()
  const [moreOpen, setMoreOpen] = useState(false)
  const moreTriggerRef = useRef<HTMLButtonElement>(null)

  // Close the overflow sheet whenever navigation happens.
  useEffect(() => {
    setMoreOpen(false)
  }, [location.pathname])

  const moreActive = mobileOverflowNav.some(
    (item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
  )

  return (
    <div className="min-h-dvh">
      <a
        href="#main-content"
        className="sr-only rounded-full bg-brand px-4 py-2 text-white focus:not-sr-only focus:absolute focus:top-3 focus:left-3 focus:z-50"
      >
        Skip to main content
      </a>

      <header className="sticky top-0 z-30 border-b border-line bg-surface/90 backdrop-blur">
        <div className="flex min-h-16 w-full items-center gap-3 px-4 sm:px-6 lg:min-h-20 lg:gap-4 lg:px-8">
          <Link
            to="/"
            className="flex items-center gap-2.5 text-lg font-semibold tracking-tight text-navy focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand lg:text-xl"
          >
            <GraduationCap size={24} className="shrink-0 text-accent" />
            <span className="whitespace-nowrap">CELPIP Practice</span>
          </Link>

          <nav aria-label="Primary" className="ml-auto hidden items-center gap-1 lg:flex">
            {primaryNav.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) =>
                  `flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                    isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:text-ink'
                  }`
                }
              >
                <item.icon size={18} strokeWidth={1.9} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-1 lg:ml-2">
            <span className="hidden lg:inline">
              <AccountControl />
            </span>
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main
        id="main-content"
        className="w-full px-4 pt-5 pb-[calc(7rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8 lg:py-8 lg:pb-8"
      >
        <div key={location.pathname} className="mx-auto max-w-5xl animate-fade-up">
          <Outlet />
        </div>
      </main>

      <nav
        aria-label="Primary mobile"
        className="fixed right-3 bottom-[calc(0.75rem+env(safe-area-inset-bottom))] left-3 z-40 mx-auto grid max-w-lg grid-cols-5 gap-1.5 rounded-3xl border border-line bg-surface/95 p-2 shadow-elevated backdrop-blur-md lg:hidden"
      >
        {mobilePrimaryNav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            aria-label={item.label}
            className={({ isActive }) =>
              `flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 rounded-2xl px-1 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
                isActive ? 'bg-brand-soft text-brand' : 'text-muted active:bg-surface-secondary'
              }`
            }
          >
            <item.icon size={22} strokeWidth={1.9} />
            <span className="max-w-full truncate">{item.mobileLabel ?? item.label}</span>
          </NavLink>
        ))}
        <button
          ref={moreTriggerRef}
          onClick={() => setMoreOpen((v) => !v)}
          aria-label="More"
          aria-expanded={moreOpen}
          aria-haspopup="dialog"
          className={`flex min-h-16 min-w-0 flex-col items-center justify-center gap-1 rounded-2xl px-1 text-xs font-semibold transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${
            moreActive || moreOpen ? 'bg-brand-soft text-brand' : 'text-muted active:bg-surface-secondary'
          }`}
        >
          <MoreHorizontal size={22} strokeWidth={1.9} />
          <span>More</span>
        </button>
      </nav>

      <MoreSheet
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        triggerRef={moreTriggerRef}
      />
    </div>
  )
}
