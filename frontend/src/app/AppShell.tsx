import { useEffect, useRef, useState, type RefObject } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { ArrowLeft, ChevronDown, ChevronRight, GraduationCap, LayoutDashboard, LogIn, MoreHorizontal, Timer, UserPlus, UserRound, X } from 'lucide-react'
import {
  mobileOverflowNav,
  mobilePrimaryNav,
} from './navigation'
import { ThemeToggle } from '../components/ThemeToggle'
import { AccountControl } from '../components/AccountControl'
import { AppUpdateNotice } from '../components/AppUpdateNotice'
import { HardRefreshButton } from '../components/HardRefreshButton'
import { useAuth } from '../features/auth/AuthProvider'

// Destinations that manage their own navigation chrome (splash/auth pages, and
// session/workspace screens that already render an Exit control) omit the
// shared Back button. Everything else is an interior page that gets one.
const BACK_HIDDEN_PATHS = new Set(['/', '/signin', '/register', '/recovery'])
const BACK_HIDDEN_PREFIXES = [
  '/reading/session/',
  '/writing/session/',
  '/speaking/session/',
]

function showBackButton(pathname: string): boolean {
  if (BACK_HIDDEN_PATHS.has(pathname)) return false
  if (BACK_HIDDEN_PREFIXES.some((prefix) => pathname.startsWith(prefix))) return false
  if (/^\/mock\/[^/]+/.test(pathname)) return false
  return true
}

function MoreMenu({
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

  // Lock body scroll while the full-screen menu is open.
  useEffect(() => {
    if (!open) return
    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previous
    }
  }, [open])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 lg:hidden">
      <button
        className="absolute inset-0 bg-black/40 animate-fade-in"
        aria-label="Close menu"
        tabIndex={-1}
        onClick={onClose}
      />
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="more-menu-title"
        className="absolute inset-0 flex flex-col bg-surface animate-slide-up"
      >
        <div className="flex items-center justify-between px-5 pt-4 pb-3">
          <h2 id="more-menu-title" className="text-lg font-semibold tracking-tight text-ink">
            Menu
          </h2>
          <button
            ref={closeRef}
            onClick={onClose}
            aria-label="Close menu"
            className="flex h-11 w-11 items-center justify-center rounded-full text-muted hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
          >
            <X size={22} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 pb-[calc(1.5rem+env(safe-area-inset-bottom))]">
          <section aria-labelledby="more-explore-title">
            <h3 id="more-explore-title" className="eyebrow px-3 pt-4 pb-2">
              Explore
            </h3>
            <ul className="space-y-1">
              {mobileOverflowNav.map((item) => (
                <li key={item.to}>
                  <NavLink
                    to={item.to}
                    end={item.end}
                    onClick={onClose}
                    className={({ isActive }) =>
                      `flex min-h-14 items-center gap-3 rounded-2xl px-3 py-2.5 text-base font-semibold transition-colors ${
                        isActive
                          ? 'bg-brand-soft text-brand'
                          : 'text-ink hover:bg-surface-secondary'
                      }`
                    }
                  >
                    <item.icon size={22} strokeWidth={1.9} />
                    <span className="flex-1">{item.label}</span>
                    <ChevronRight size={18} className="text-muted" aria-hidden="true" />
                  </NavLink>
                </li>
              ))}
            </ul>
          </section>

          <section aria-labelledby="more-account-title">
            <h3 id="more-account-title" className="eyebrow px-3 pt-5 pb-2">
              Account
            </h3>
            {status === 'authenticated' ? (
              <NavLink
                to="/account"
                onClick={onClose}
                className={({ isActive }) =>
                  `flex min-h-14 items-center gap-3 rounded-2xl px-3 py-2.5 text-base font-semibold transition-colors ${
                    isActive
                      ? 'bg-brand-soft text-brand'
                      : 'text-ink hover:bg-surface-secondary'
                  }`
                }
              >
                <UserRound size={22} strokeWidth={1.9} />
                <span className="flex-1">Account</span>
                <ChevronRight size={18} className="text-muted" aria-hidden="true" />
              </NavLink>
            ) : (
              <div className="grid grid-cols-2 gap-2 px-1">
                <NavLink
                  to="/signin"
                  onClick={onClose}
                  className="flex min-h-12 items-center justify-center gap-2 rounded-2xl px-3 text-sm font-semibold text-ink transition-colors hover:bg-surface-secondary"
                >
                  <LogIn size={20} strokeWidth={1.9} />
                  <span>Sign in</span>
                </NavLink>
                <NavLink
                  to="/register"
                  onClick={onClose}
                  className="flex min-h-12 items-center justify-center gap-2 rounded-2xl px-3 text-sm font-semibold text-white transition-opacity hover:opacity-90 bg-brand"
                >
                  <UserPlus size={20} strokeWidth={1.9} />
                  <span>Sign up</span>
                </NavLink>
              </div>
            )}
          </section>

          <section aria-labelledby="more-preferences-title">
            <h3 id="more-preferences-title" className="eyebrow px-3 pt-5 pb-2">
              Preferences
            </h3>
            <div className="space-y-1 px-1">
              <div className="flex items-center justify-between rounded-2xl border border-line-light px-3 py-2.5">
                <span className="text-sm font-medium text-ink">Theme</span>
                <ThemeToggle />
              </div>
              <div className="[&>button]:w-full">
                <HardRefreshButton variant="labeled" />
              </div>
            </div>
          </section>

          {status === 'authenticated' && (
            <button
              type="button"
              onClick={() => {
                onClose()
                void logout()
              }}
              className="mt-6 flex min-h-12 w-full items-center justify-center rounded-2xl border border-line px-3 text-sm font-semibold text-muted transition-colors hover:bg-surface-secondary hover:text-ink"
            >
              Sign out
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

const desktopGroups = [
  {
    label: 'Study',
    to: '/study',
    items: [
      { to: '/study-plan', label: 'Study Plan' },
      { to: '/learn', label: 'Reading Learn' },
      { to: '/learn/listening', label: 'Listening Learn' },
      { to: '/learn/writing', label: 'Writing Learn' },
      { to: '/learn/speaking', label: 'Speaking Learn' },
    ],
  },
  {
    label: 'Practice',
    to: '/practice',
    items: [
      { to: '/practice', label: 'Reading Practice' },
      { to: '/practice/listening', label: 'Listening Practice' },
      { to: '/practice/writing', label: 'Writing Practice' },
      { to: '/practice/speaking', label: 'Speaking Practice' },
    ],
  },
  {
    label: 'Review',
    to: '/review',
    items: [
      { to: '/progress', label: 'Progress' },
      { to: '/mistakes', label: 'Mistakes' },
    ],
  },
] as const

function DesktopNavGroup({
  group,
  open,
  onToggle,
}: {
  group: (typeof desktopGroups)[number]
  open: boolean
  onToggle: () => void
}) {
  const location = useLocation()
  const active = location.pathname === group.to || group.items.some((item) => location.pathname === item.to)
  return (
    <div className="relative flex items-center">
      <NavLink
        to={group.to}
        className={`flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${active ? 'bg-brand-soft text-brand' : 'text-muted hover:text-ink'}`}
      >
        {group.label}
      </NavLink>
      <button
        type="button"
        aria-label={`${group.label} menu`}
        aria-expanded={open}
        aria-haspopup="menu"
        onClick={onToggle}
        className="-ml-2 flex min-h-11 items-center rounded-full px-2 text-muted hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
      >
        <ChevronDown size={15} className={open ? 'rotate-180 transition-transform' : 'transition-transform'} />
      </button>
      {open && (
        <div role="menu" className="absolute top-full right-0 z-50 mt-2 min-w-52 rounded-2xl border border-line bg-surface p-2 shadow-elevated">
          {group.items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              role="menuitem"
              onClick={onToggle}
              className={({ isActive }) => `block rounded-xl px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-brand-soft text-brand' : 'text-ink hover:bg-surface-secondary'}`}
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      )}
    </div>
  )
}

export function AppShell() {
  const location = useLocation()
  const navigate = useNavigate()
  const [moreOpen, setMoreOpen] = useState(false)
  const [desktopMenu, setDesktopMenu] = useState<string | null>(null)
  const moreTriggerRef = useRef<HTMLButtonElement>(null)

  // Close the overflow sheet whenever navigation happens.
  useEffect(() => {
    setMoreOpen(false)
    setDesktopMenu(null)
  }, [location.pathname])

  const moreActive = mobileOverflowNav.some(
    (item) => location.pathname === item.to || location.pathname.startsWith(`${item.to}/`),
  )

  const showBack = showBackButton(location.pathname)
  const handleBack = () => {
    // In-app entries carry a router-generated key; direct/refreshed entries use
    // the sentinel 'default' key, so there is no previous in-app page to return
    // to and the button falls back to the dashboard instead.
    if (location.key !== 'default') {
      navigate(-1)
    } else {
      navigate('/', { replace: true })
    }
  }

  // One-shot confirmation notices (e.g. after account deletion) are carried in
  // the route state so a public destination can announce them for assistive
  // tech. They are consumed exactly once: capture the text for display, then
  // clear the state from the history entry so a later revisit of that entry
  // (back/forward/refresh) cannot re-announce a stale notice.
  const [notice, setNotice] = useState<{ path: string; text: string } | null>(null)

  useEffect(() => {
    const incoming = (location.state as { notice?: string } | null)?.notice
    if (!incoming) return
    setNotice({ path: location.pathname, text: incoming })
    navigate(location.pathname + location.search, {
      replace: true,
      state: null,
    })
  }, [location, navigate])

  useEffect(() => {
    if (notice && location.pathname !== notice.path) {
      setNotice(null)
    }
  }, [location.pathname, notice])

  const visibleNotice =
    notice && notice.path === location.pathname ? notice.text : null

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
            <NavLink
              to="/"
              end
              className={({ isActive }) =>
                `flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:text-ink'}`
              }
            >
              <LayoutDashboard size={18} strokeWidth={1.9} />
              Dashboard
            </NavLink>
            {desktopGroups.map((group) => (
              <DesktopNavGroup
                key={group.to}
                group={group}
                open={desktopMenu === group.to}
                onToggle={() => setDesktopMenu((current) => (current === group.to ? null : group.to))}
              />
            ))}
            <NavLink
              to="/mock"
              className={({ isActive }) =>
                `flex min-h-11 items-center gap-2 rounded-full px-3.5 py-2.5 text-sm font-medium whitespace-nowrap transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${isActive ? 'bg-brand-soft text-brand' : 'text-muted hover:text-ink'}`
              }
            >
              <Timer size={18} strokeWidth={1.9} />
              Mock Test
            </NavLink>
          </nav>

          <div className="ml-auto flex items-center gap-1 lg:ml-2">
            <span className="hidden lg:inline">
              <AccountControl />
            </span>
            <HardRefreshButton />
            <ThemeToggle />
          </div>
        </div>
      </header>

      <main
        id="main-content"
        className="w-full px-4 pt-5 pb-[calc(7rem+env(safe-area-inset-bottom))] sm:px-6 lg:px-8 lg:py-8 lg:pb-8"
      >
        <AppUpdateNotice />
        {visibleNotice && (
          <div
            role="status"
            className="mx-auto mb-5 w-full rounded-xl border border-good/40 bg-good-soft px-4 py-3 text-sm text-good"
          >
            {visibleNotice}
          </div>
        )}
        {showBack && (
          <div className="mx-auto mb-4 w-full">
            <button
              type="button"
              onClick={handleBack}
              aria-label="Go back"
              className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:bg-surface-secondary hover:text-ink focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand"
            >
              <ArrowLeft size={16} aria-hidden="true" />
              <span>Back</span>
            </button>
          </div>
        )}
        <div key={location.pathname} className="mx-auto w-full max-w-7xl animate-fade-up">
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

      <MoreMenu
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        triggerRef={moreTriggerRef}
      />
    </div>
  )
}
