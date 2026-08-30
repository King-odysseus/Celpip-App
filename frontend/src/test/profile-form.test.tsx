import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'
import { formatFieldErrors } from '../features/auth/ProfileForm'

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
  updated_at: '2026-08-29T00:00:00Z',
}

const authedBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
  'GET /me/': () => jsonResponse(USER),
  'GET /me/profile/': () => jsonResponse(PROFILE),
}

/** Backend invalid-input envelope with per-field messages (DRF-shaped). */
function invalidInput(fields: Record<string, unknown>) {
  return jsonResponse(
    { code: 'invalid_input', message: 'Some fields were invalid.', fields },
    400,
  )
}

async function renderAccount() {
  const user = userEvent.setup()
  renderApp('/account')
  // Wait for the profile form to mount.
  await screen.findByRole('button', { name: /save profile/i })
  return user
}

function patchCalls(spy: ReturnType<typeof installRouteFetch>) {
  return spy.mock.calls.filter(
    ([url, init]) =>
      (init?.method ?? 'GET').toUpperCase() === 'PATCH' &&
      String(url).includes('/me/profile/'),
  )
}

describe('ProfileForm backend field errors', () => {
  it('surfaces the timezone validation error as an actionable, labelled message', async () => {
    installRouteFetch({
      ...authedBootstrap,
      'PATCH /me/profile/': () =>
        invalidInput({
          timezone: ['Use a valid IANA timezone such as Europe/London.'],
        }),
    })
    const user = await renderAccount()

    await user.click(screen.getByRole('button', { name: /save profile/i }))

    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent('Some fields were invalid.')
    expect(alert).toHaveTextContent(
      'Timezone: Use a valid IANA timezone such as Europe/London.',
    )
    // Never a raw object or JSON dump.
    expect(alert).not.toHaveTextContent('[object Object]')

    // The invalid control is flagged and focused for correction.
    const select = screen.getByLabelText('Timezone')
    expect(select).toHaveAttribute('aria-invalid', 'true')
    expect(select).toHaveFocus()
  })
})

describe('ProfileForm client validation', () => {
  it('blocks the PATCH when daily minutes are invalid', async () => {
    const spy = installRouteFetch({
      ...authedBootstrap,
      'PATCH /me/profile/': () => jsonResponse(PROFILE),
    })
    const user = await renderAccount()

    const minutes = screen.getByLabelText('Daily study minutes')
    await user.clear(minutes)
    await user.type(minutes, '2')
    await user.click(screen.getByRole('button', { name: /save profile/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /whole number between 5 and 600/i,
    )
    expect(patchCalls(spy)).toHaveLength(0)
    expect(minutes).toHaveAttribute('aria-invalid', 'true')
    expect(minutes).toHaveFocus()
  })

  it('does not coerce an emptied minutes field to zero before validating', async () => {
    const spy = installRouteFetch({
      ...authedBootstrap,
      'PATCH /me/profile/': () => jsonResponse(PROFILE),
    })
    const user = await renderAccount()

    const minutes = screen.getByLabelText('Daily study minutes')
    await user.clear(minutes)
    expect(minutes).toHaveValue(null)
    await user.click(screen.getByRole('button', { name: /save profile/i }))

    expect(patchCalls(spy)).toHaveLength(0)
    expect(await screen.findByRole('alert')).toBeInTheDocument()
  })
})

describe('ProfileForm valid save', () => {
  it('sends the edited profile and announces success', async () => {
    const spy = installRouteFetch({
      ...authedBootstrap,
      'PATCH /me/profile/': () => jsonResponse({ ...PROFILE, daily_minutes: 45 }),
    })
    const user = await renderAccount()

    const minutes = screen.getByLabelText('Daily study minutes')
    await user.clear(minutes)
    await user.type(minutes, '45')
    await user.click(screen.getByRole('button', { name: /save profile/i }))

    expect(await screen.findByText('Profile saved.')).toBeInTheDocument()
    const calls = patchCalls(spy)
    expect(calls).toHaveLength(1)
    const body = JSON.parse(calls[0][1]!.body as string)
    expect(body.daily_minutes).toBe(45)
    expect(body.timezone).toBe('America/Toronto')
  })
})

describe('ProfileForm browser timezone', () => {
  it('adds and selects the browser timezone when valid', async () => {
    vi.spyOn(Intl, 'DateTimeFormat').mockReturnValue({
      resolvedOptions: () => ({ timeZone: 'Europe/London' }),
    } as unknown as Intl.DateTimeFormat)

    installRouteFetch(authedBootstrap)
    const user = await renderAccount()

    await user.click(screen.getByRole('button', { name: /use my timezone/i }))

    const select = screen.getByLabelText('Timezone') as HTMLSelectElement
    expect(select.value).toBe('Europe/London')
    expect(
      within(select).getByRole('option', { name: 'Europe/London' }),
    ).toBeInTheDocument()

    vi.restoreAllMocks()
  })
})

describe('formatFieldErrors', () => {
  it('flattens strings, arrays, and nested objects without raw JSON', () => {
    const result = formatFieldErrors({
      timezone: 'Use a valid IANA timezone such as Europe/London.',
      daily_minutes: ['Must be at least 5.', 'Must be at most 600.'],
      preferred_weekdays: { 0: ['Not a valid choice.'] },
    })

    expect(result).toContain(
      'Timezone: Use a valid IANA timezone such as Europe/London.',
    )
    expect(result).toContain('Daily minutes: Must be at least 5. Must be at most 600.')
    expect(result.join(' ')).not.toContain('[object Object]')
    expect(result.some((line) => line.startsWith('Preferred study days:'))).toBe(true)
  })
})
