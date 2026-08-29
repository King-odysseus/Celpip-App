import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse, errorResponse } from './mockFetch'

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

function stubObjectUrl() {
  const createObjectURL = vi.fn(() => 'blob:mock-export')
  const revokeObjectURL = vi.fn()
  Object.defineProperty(URL, 'createObjectURL', {
    configurable: true,
    value: createObjectURL,
  })
  Object.defineProperty(URL, 'revokeObjectURL', {
    configurable: true,
    value: revokeObjectURL,
  })
  return { createObjectURL, revokeObjectURL }
}

async function openDeletePanel() {
  const user = userEvent.setup()
  renderApp('/account')
  await user.click(await screen.findByRole('button', { name: 'Delete account' }))
  return user
}

describe('account data export', () => {
  it('downloads the export as a timestamped JSON file via a Blob URL', async () => {
    const { createObjectURL, revokeObjectURL } = stubObjectUrl()
    let downloaded: string | null = null
    let clickedHref: string | null = null
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(
      function (this: HTMLAnchorElement) {
        downloaded = this.download
        clickedHref = this.href
      },
    )

    installRouteFetch({
      ...authedBootstrap,
      'GET /me/export/': () =>
        jsonResponse({ format_version: '1.0', account: { id: 1 } }),
    })
    const user = userEvent.setup()
    renderApp('/account')

    await user.click(
      await screen.findByRole('button', { name: /download my data/i }),
    )

    expect(await screen.findByText(/your download has started/i)).toBeInTheDocument()
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-export')
    expect(clickedHref).toBe('blob:mock-export')
    expect(downloaded).toMatch(
      /^celpip-data-export-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}\.json$/,
    )
  })

  it('shows an accessible error and stays in control when export fails', async () => {
    installRouteFetch({
      ...authedBootstrap,
      'GET /me/export/': () => errorResponse('export_failed', 500, 'Export unavailable.'),
    })
    const user = userEvent.setup()
    renderApp('/account')

    await user.click(
      await screen.findByRole('button', { name: /download my data/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent('Export unavailable.')
    expect(
      screen.getByRole('button', { name: /download my data/i }),
    ).toBeEnabled()
  })

  it('disables the button while the export is preparing', async () => {
    stubObjectUrl()
    const pending = new Promise<Response>(() => {})

    installRouteFetch({
      ...authedBootstrap,
      'GET /me/export/': () => pending,
    })
    const user = userEvent.setup()
    renderApp('/account')

    await user.click(
      await screen.findByRole('button', { name: /download my data/i }),
    )

    expect(
      await screen.findByRole('button', { name: /preparing…/i }),
    ).toBeDisabled()
  })
})

describe('account deletion', () => {
  it('validates before submitting and never requests both credentials', async () => {
    const fetchSpy = installRouteFetch(authedBootstrap)
    const user = await openDeletePanel()

    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      /enter your password to delete the account/i,
    )
    const deleteCalls = fetchSpy.mock.calls.filter(
      ([, init]) => (init?.method ?? 'GET').toUpperCase() === 'DELETE',
    )
    expect(deleteCalls).toHaveLength(0)

    // Exactly one confirmation field is shown at a time.
    expect(screen.getByLabelText('Your password')).toBeInTheDocument()
    expect(
      screen.queryByLabelText('Your recovery code'),
    ).not.toBeInTheDocument()
  })

  it('submits a password confirmation', async () => {
    const fetchSpy = installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () => new Response(null, { status: 204 }),
    })
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    const deleteCall = fetchSpy.mock.calls.find(
      ([, init]) => init?.method === 'DELETE',
    )
    expect(JSON.parse(deleteCall![1]!.body as string)).toEqual({
      password: 'secret1',
    })
  })

  it('submits a recovery-code confirmation instead of a password', async () => {
    const fetchSpy = installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () => new Response(null, { status: 204 }),
    })
    const user = await openDeletePanel()

    await user.click(screen.getByRole('radio', { name: /recovery code/i }))
    await user.type(
      screen.getByLabelText('Your recovery code'),
      'RECOVER-ABC-123',
    )
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    const deleteCall = fetchSpy.mock.calls.find(
      ([, init]) => init?.method === 'DELETE',
    )
    expect(JSON.parse(deleteCall![1]!.body as string)).toEqual({
      recovery_code: 'RECOVER-ABC-123',
    })
  })

  it('keeps the user in control when the backend rejects the confirmation', async () => {
    installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () =>
        errorResponse('invalid_credentials', 400, 'Invalid password or recovery code.'),
    })
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'wrong')
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Invalid password or recovery code.',
    )
    // Still on the account page and able to retry or cancel.
    expect(screen.getByRole('button', { name: /cancel/i })).toBeEnabled()
    expect(
      screen.getByRole('button', { name: /permanently delete account/i }),
    ).toBeEnabled()
  })

  it('clears auth, navigates to a public page, and announces success', async () => {
    installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () => new Response(null, { status: 204 }),
    })
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    expect(
      await screen.findByRole('heading', { level: 1, name: 'Dashboard' }),
    ).toBeInTheDocument()
    expect(screen.getByText(/your account has been deleted/i)).toBeInTheDocument()
    // The anonymous dashboard prompt confirms the in-memory session was dropped.
    expect(
      await screen.findByText(/browsing without an account/i),
    ).toBeInTheDocument()
  })

  it('disables the confirm button while deletion is in flight', async () => {
    const pending = new Promise<Response>(() => {})

    installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () => pending,
    })
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )

    expect(
      await screen.findByRole('button', { name: /deleting…/i }),
    ).toBeDisabled()
  })

  it('keeps the pending panel mounted and refuses dismissal via Escape', async () => {
    const pending = new Promise<Response>(() => {})

    installRouteFetch({
      ...authedBootstrap,
      'DELETE /me/': () => pending,
    })
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(
      screen.getByRole('button', { name: /permanently delete account/i }),
    )
    expect(
      await screen.findByRole('button', { name: /deleting…/i }),
    ).toBeDisabled()

    // Escape must not close or unmount the panel while deletion is pending.
    await user.keyboard('{Escape}')

    expect(
      screen.getByRole('region', { name: /delete your account\?/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /deleting…/i }),
    ).toBeDisabled()
    expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled()
  })

  it('clears the other confirmation credential when switching methods', async () => {
    installRouteFetch(authedBootstrap)
    const user = await openDeletePanel()

    // A stale password must not resurface after switching away and back.
    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(screen.getByRole('radio', { name: /recovery code/i }))
    await user.click(screen.getByRole('radio', { name: /password/i }))
    expect(screen.getByLabelText('Your password')).toHaveValue('')

    // Likewise a stale recovery code must not resurface.
    await user.click(screen.getByRole('radio', { name: /recovery code/i }))
    await user.type(
      screen.getByLabelText('Your recovery code'),
      'RECOVER-ABC-123',
    )
    await user.click(screen.getByRole('radio', { name: /password/i }))
    await user.click(screen.getByRole('radio', { name: /recovery code/i }))
    expect(screen.getByLabelText('Your recovery code')).toHaveValue('')
  })

  it('clears both credentials when Cancel closes the panel', async () => {
    installRouteFetch(authedBootstrap)
    const user = await openDeletePanel()

    await user.type(screen.getByLabelText('Your password'), 'secret1')
    await user.click(screen.getByRole('button', { name: /cancel/i }))

    // Reopening must not resurface the stale password or recovery code.
    await user.click(screen.getByRole('button', { name: /delete account/i }))
    expect(screen.getByLabelText('Your password')).toHaveValue('')

    await user.click(screen.getByRole('radio', { name: /recovery code/i }))
    expect(screen.getByLabelText('Your recovery code')).toHaveValue('')
  })
})

describe('account deletion accessibility', () => {
  it('reveals an accessible panel and moves focus into it', async () => {
    installRouteFetch(authedBootstrap)
    const user = await openDeletePanel()

    expect(
      screen.getByRole('heading', { level: 3, name: /delete your account\?/i }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('group', { name: /confirm with/i }),
    ).toBeInTheDocument()
    expect(screen.getByRole('radio', { name: /password/i })).toBeChecked()

    const panel = screen.getByRole('region', { name: /delete your account\?/i })
    expect(panel).toHaveFocus()

    // The irreversible warning calls out private recordings and progress.
    expect(panel).toHaveTextContent(/private speaking recordings/i)
    expect(panel).toHaveTextContent(/progress/i)

    await user.click(screen.getByRole('button', { name: /cancel/i }))
    expect(
      screen.getByRole('button', { name: /delete account/i }),
    ).toHaveFocus()
  })
})
