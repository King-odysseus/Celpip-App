import { describe, expect, it } from 'vitest'
import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'
import { primaryNav } from '../app/navigation'

const USER = { id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }
const PROFILE = {
  identifier: 'learner',
  exam_date: null,
  target_level: 9,
  target_listening: null,
  target_reading: null,
  target_writing: null,
  target_speaking: null,
  daily_minutes: 30,
  preferred_weekdays: [1, 2, 3, 4, 5],
  timezone: 'America/Toronto',
  practice_narration_voice: 'automatic',
  updated_at: '2026-08-29T00:00:00Z',
}

describe('AppShell', () => {
  it('renders the brand and a skip-to-content link', () => {
    renderApp()
    expect(screen.getByText('CELPIP Practice')).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /skip to main content/i }),
    ).toBeInTheDocument()
  })

  it('exposes all seven primary destinations in the desktop nav', () => {
    renderApp()
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    for (const item of primaryNav) {
      expect(
        within(nav).getByRole('link', { name: item.label }),
      ).toBeInTheDocument()
    }
  })

  it('marks the current destination as active', () => {
    renderApp('/practice')
    const nav = screen.getByRole('navigation', { name: 'Primary' })
    const active = within(nav).getByRole('link', { name: 'Practice' })
    expect(active).toHaveClass('bg-brand-soft')
  })

  it('renders the mobile bar with four primary items plus More', () => {
    renderApp()
    const mobileNav = screen.getByRole('navigation', { name: 'Primary mobile' })
    // Home, Practice, Mock, Progress links + the More button = 5 controls.
    expect(within(mobileNav).getAllByRole('link')).toHaveLength(4)
    expect(within(mobileNav).getByRole('button', { name: 'More' })).toBeInTheDocument()
  })

  it('shows both Sign in and Sign up in the header, with Sign up as the primary CTA', async () => {
    renderApp()
    // Exact-case "Sign in" matches the header CTA; the dashboard's inline link
    // is lowercase "sign in".
    const signIn = await screen.findByRole('link', { name: 'Sign in' })
    const signUp = screen.getByRole('link', { name: 'Sign up' })
    expect(signIn).toBeInTheDocument()
    // Sign up is the prominent primary action; Sign in stays a secondary link.
    expect(signUp).toHaveClass('bg-brand')
    expect(signIn).not.toHaveClass('bg-brand')
  })

  it('replaces the anonymous sign-in/up links with the account control once signed in', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
      'GET /me/': () => jsonResponse(USER),
      'GET /me/profile/': () => jsonResponse(PROFILE),
    })
    renderApp()
    expect(
      await screen.findByRole('link', { name: 'Account' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Sign in' }),
    ).not.toBeInTheDocument()
    expect(
      screen.queryByRole('link', { name: 'Sign up' }),
    ).not.toBeInTheDocument()
  })
})

describe('routing', () => {
  it('renders each primary destination heading', async () => {
    const cases: Array<[string, string]> = [
      ['/', 'Dashboard'],
      ['/learn', 'Reading Learn'],
      ['/practice', 'Reading Practice'],
      ['/mock', 'Mock Tests'],
      ['/mistakes', 'Mistake Bank'],
      ['/progress', 'Progress'],
      ['/study-plan', 'Study Plan'],
    ]
    for (const [path, heading] of cases) {
      const { unmount } = renderApp(path)
      expect(
        await screen.findByRole('heading', { level: 1, name: heading }),
      ).toBeInTheDocument()
      unmount()
    }
  })

  it('shows a 404 page for unknown routes', () => {
    renderApp('/does-not-exist')
    expect(
      screen.getByRole('heading', { level: 1, name: /page not found/i }),
    ).toBeInTheDocument()
  })
})

describe('back button', () => {
  it('is hidden on the dashboard and auth pages', () => {
    for (const path of ['/', '/signin', '/register', '/recovery']) {
      const { unmount } = renderApp(path)
      expect(
        screen.queryByRole('button', { name: 'Go back' }),
      ).not.toBeInTheDocument()
      unmount()
    }
  })

  it('is visible on interior pages', () => {
    renderApp('/learn')
    const back = screen.getByRole('button', { name: 'Go back' })
    expect(back).toBeInTheDocument()
    expect(screen.getByText('Back')).toBeInTheDocument()
  })

  it('is hidden on session and mock workspace pages', () => {
    const { unmount } = renderApp('/reading/session/abc')
    expect(
      screen.queryByRole('button', { name: 'Go back' }),
    ).not.toBeInTheDocument()
    unmount()

    renderApp('/mock/abc')
    expect(
      screen.queryByRole('button', { name: 'Go back' }),
    ).not.toBeInTheDocument()
  })

  it('falls back to the dashboard on a direct entry', async () => {
    const user = userEvent.setup()
    renderApp('/learn')

    await user.click(screen.getByRole('button', { name: 'Go back' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard' }),
    ).toBeInTheDocument()
  })

  it('returns to the previous page after in-app navigation', async () => {
    const user = userEvent.setup()
    const { router } = renderApp('/')

    await act(async () => {
      await router.navigate('/learn')
    })
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Reading Learn' }),
    ).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Go back' }))

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard' }),
    ).toBeInTheDocument()
  })
})

describe('route-state notice', () => {
  it('announces once and clears the notice from history state', async () => {
    const { router } = renderApp('/', {
      state: { notice: 'Your account has been deleted.' },
    })

    // Announced once on arrival.
    expect(
      await screen.findByText(/your account has been deleted/i),
    ).toBeInTheDocument()

    // Consumed: the notice is removed from the history entry's state.
    await waitFor(() => {
      const state = router.state.location.state as { notice?: string } | null
      expect(state?.notice).toBeUndefined()
    })

    // A same-history revisit (away and back) must not re-announce it.
    await act(async () => {
      await router.navigate('/learn')
    })
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Reading Learn' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/your account has been deleted/i),
    ).not.toBeInTheDocument()

    await act(async () => {
      await router.navigate(-1)
    })
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/your account has been deleted/i),
    ).not.toBeInTheDocument()
  })
})

describe('mobile More overflow', () => {
  it('opens a dialog exposing the overflow destinations', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'More' }))
    const dialog = screen.getByRole('dialog', { name: 'Menu' })
    expect(within(dialog).getByRole('link', { name: 'Study' })).toBeInTheDocument()
  })

  it('offers both Sign in and Sign up to anonymous visitors and closes on click', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'More' }))

    const dialog = screen.getByRole('dialog', { name: 'Menu' })
    const signIn = within(dialog).getByRole('link', { name: 'Sign in' })
    const signUp = within(dialog).getByRole('link', { name: 'Sign up' })
    expect(signIn).toBeInTheDocument()
    expect(signUp).toHaveClass('bg-brand')

    await user.click(signUp)
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(
      await screen.findByRole('heading', { level: 1, name: /create your account/i }),
    ).toBeInTheDocument()
  })

  it('shows Account and Sign out (not Sign in/up) when signed in', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
      'GET /me/': () => jsonResponse(USER),
      'GET /me/profile/': () => jsonResponse(PROFILE),
    })
    const user = userEvent.setup()
    renderApp()
    await screen.findByRole('link', { name: 'Account' })
    await user.click(screen.getByRole('button', { name: 'More' }))

    const dialog = screen.getByRole('dialog', { name: 'Menu' })
    expect(
      within(dialog).getByRole('link', { name: 'Account' }),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByRole('button', { name: 'Sign out' }),
    ).toBeInTheDocument()
    expect(
      within(dialog).queryByRole('link', { name: 'Sign in' }),
    ).not.toBeInTheDocument()
    expect(
      within(dialog).queryByRole('link', { name: 'Sign up' }),
    ).not.toBeInTheDocument()
  })

  it('closes the overflow dialog with Escape', async () => {
    const user = userEvent.setup()
    renderApp()
    const trigger = screen.getByRole('button', { name: 'More' })
    await user.click(trigger)
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    await user.keyboard('{Escape}')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(trigger).toHaveFocus()
  })

  it('traps keyboard focus inside the overflow dialog', async () => {
    const user = userEvent.setup()
    renderApp()
    await user.click(screen.getByRole('button', { name: 'More' }))
    const dialog = screen.getByRole('dialog')
    const close = within(dialog).getByRole('button', { name: 'Close menu' })
    expect(close).toHaveFocus()

    await user.tab({ shift: true })
    expect(dialog).toContainElement(document.activeElement as HTMLElement)

    const focusable = dialog.querySelectorAll<HTMLElement>(
      'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
    )
    focusable[focusable.length - 1].focus()
    await user.tab()
    expect(close).toHaveFocus()
  })
})
