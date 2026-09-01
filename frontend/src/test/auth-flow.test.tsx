import { describe, expect, it } from 'vitest'
import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse, errorResponse } from './mockFetch'
import { makeDashboard } from './fixtures/dashboard'

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

const USER = { id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }

// Bootstrap routes that leave the app anonymous (refresh fails).
const anonymousBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => errorResponse('invalid_refresh_token', 401),
}

describe('registration flow', () => {
  it('registers and reveals the one-time recovery code', async () => {
    installRouteFetch({
      ...anonymousBootstrap,
      'POST /auth/register/': () =>
        jsonResponse(
          { access: 'access-token', user: USER, recovery_code: 'RECOVER-XYZ-123' },
          201,
        ),
      'GET /me/profile/': () => jsonResponse(PROFILE),
    })

    const user = userEvent.setup()
    renderApp('/register')

    await screen.findByRole('heading', { name: /create your account/i })
    await user.type(screen.getByLabelText(/username or email/i), 'learner')
    await user.type(screen.getByLabelText(/password/i), 'secret1')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByTestId('recovery-code')).toHaveTextContent('RECOVER-XYZ-123')
  })

  it('rejects a short password before calling the API', async () => {
    const fetchSpy = installRouteFetch(anonymousBootstrap)

    const user = userEvent.setup()
    renderApp('/register')

    await screen.findByRole('heading', { name: /create your account/i })
    await user.type(screen.getByLabelText(/username or email/i), 'learner')
    await user.type(screen.getByLabelText(/password/i), '12345')
    await user.click(screen.getByRole('button', { name: /create account/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/at least 6 characters/i)
    expect(
      fetchSpy.mock.calls.some((c) => String(c[0]).includes('/auth/register/')),
    ).toBe(false)
  })
})

describe('protected routes', () => {
  it('redirects an anonymous visitor from Account to sign in', async () => {
    installRouteFetch(anonymousBootstrap)
    renderApp('/account')
    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument()
  })
})

describe('dashboard without an account', () => {
  it('stays viewable and prompts to create an account', async () => {
    installRouteFetch(anonymousBootstrap)
    renderApp('/')
    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/browsing without an account/i)).toBeInTheDocument()
    expect(screen.getByText(/no exam date set yet/i)).toBeInTheDocument()
  })
})

describe('authenticated bootstrap', () => {
  it('signs in on load when the refresh cookie is valid', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
      'GET /me/': () => jsonResponse(USER),
      'GET /me/profile/': () => jsonResponse({ ...PROFILE, exam_date: '2026-10-10' }),
      // CountdownCard (which renders "Exam date:") only appears once the
      // dashboard fetch itself resolves — see DashboardPage's `isAuthed &&
      // dashboard` gate.
      'GET /me/dashboard/': () => jsonResponse(makeDashboard()),
    })

    renderApp('/')

    // The header account control shows the identifier once authenticated.
    await waitFor(() =>
      expect(screen.getAllByText('learner').length).toBeGreaterThan(0),
    )
    // The dashboard's own profile-dependent render lands on a later tick.
    await waitFor(() => expect(screen.getByText(/exam date:/i)).toBeInTheDocument())
  })

  it('drops the in-memory account when another tab signs in as a different user', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => jsonResponse({ access: 'access-token', user_id: USER.id }),
      'GET /me/': () => jsonResponse(USER),
      'GET /me/profile/': () => jsonResponse(PROFILE),
    })

    renderApp('/account')
    expect(await screen.findByRole('heading', { name: /account & profile/i })).toBeInTheDocument()

    act(() => {
      window.dispatchEvent(new StorageEvent('storage', {
        key: 'celpip-auth-account-event',
        newValue: JSON.stringify({ userId: 999, nonce: 'another-tab' }),
      }))
    })

    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument()
  })
})
