import { describe, expect, it } from 'vitest'
import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'

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

const authenticatedBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
  'GET /me/': () => jsonResponse(USER),
  'GET /me/profile/': () => jsonResponse(PROFILE),
}

describe('AI Coach', () => {
  it('sends a direct question with the selected skill and renders the reply', async () => {
    const user = userEvent.setup()
    const fetchSpy = installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/ai-coach/': () => jsonResponse({ messages: [] }),
      'POST /me/ai-coach/': () => jsonResponse({
        user_message: {
          id: 'user-1',
          role: 'user',
          content: 'How should I structure a CELPIP email?',
          skill: 'writing',
          created_at: '2026-09-17T12:00:00Z',
        },
        coach_message: {
          id: 'coach-1',
          role: 'assistant',
          content: 'Open with the purpose, add the key details, and close with a clear action.',
          skill: 'writing',
          created_at: '2026-09-17T12:00:01Z',
        },
      }, 201),
    })

    renderApp('/coach?skill=writing')

    expect(await screen.findByRole('heading', { level: 1, name: /ask before your next attempt/i })).toBeInTheDocument()
    await user.click(await screen.findByRole('button', { name: 'How should I structure a CELPIP email?' }))
    await user.click(screen.getByRole('button', { name: 'Send question' }))

    expect(await screen.findByText('Open with the purpose, add the key details, and close with a clear action.')).toBeInTheDocument()
    const post = fetchSpy.mock.calls.find(
      ([url, init]) => init?.method === 'POST' && String(url).includes('/me/ai-coach/'),
    )
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      message: 'How should I structure a CELPIP email?',
      skill: 'writing',
    })
    expect(screen.getByLabelText('Message the AI Coach')).toHaveValue('')
  })

  it('clears the saved conversation after explicit confirmation', async () => {
    const user = userEvent.setup()
    let history = {
      messages: [
        {
          id: 'coach-old',
          role: 'assistant',
          content: 'Use one clear reason and one specific example.',
          skill: 'writing',
          created_at: '2026-09-17T12:00:00Z',
        },
      ],
    }
    const fetchSpy = installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/ai-coach/': () => jsonResponse(history),
      'DELETE /me/ai-coach/': () => {
        history = { messages: [] }
        return new Response(null, { status: 204 })
      },
    })

    renderApp('/coach')

    expect(await screen.findByText('Use one clear reason and one specific example.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'New chat' }))
    expect(screen.getByRole('dialog', { name: 'Clear this conversation?' })).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Clear chat' }))

    await waitFor(() => expect(screen.getByText('What would you like to improve?')).toBeInTheDocument())
    expect(fetchSpy.mock.calls.some(([, init]) => init?.method === 'DELETE')).toBe(true)
  })

  it('opens a compact floating coach from any signed-in page', async () => {
    const user = userEvent.setup()
    const fetchSpy = installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/ai-coach/': () => jsonResponse({ messages: [] }),
      'POST /me/ai-coach/': () => jsonResponse({
        user_message: {
          id: 'widget-user',
          role: 'user',
          content: 'How can I improve my reading speed?',
          skill: 'reading',
          created_at: '2026-09-17T12:00:00Z',
        },
        coach_message: {
          id: 'widget-coach',
          role: 'assistant',
          content: 'Start by reading the question stems before the passage.',
          skill: 'reading',
          created_at: '2026-09-17T12:00:01Z',
        },
      }, 201),
    })

    renderApp('/study')

    await user.click(await screen.findByRole('button', { name: 'Open AI Coach' }))
    const dialog = await screen.findByRole('dialog', { name: 'AI Coach' })
    await user.click(within(dialog).getByRole('button', { name: 'Reading' }))
    await user.click(within(dialog).getByRole('button', { name: 'How can I find the right evidence faster?' }))
    const composer = within(dialog).getByLabelText('Message the AI Coach')
    await user.clear(composer)
    await user.type(composer, 'How can I improve my reading speed?')
    await user.click(within(dialog).getByRole('button', { name: 'Send question' }))

    expect(await within(dialog).findByText('Start by reading the question stems before the passage.')).toBeInTheDocument()
    const post = fetchSpy.mock.calls.find(
      ([url, init]) => init?.method === 'POST' && String(url).includes('/me/ai-coach/'),
    )
    expect(JSON.parse(String(post?.[1]?.body))).toEqual({
      message: 'How can I improve my reading speed?',
      skill: 'reading',
    })
  })

  it('opens the floating coach with context from How to Answer', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/ai-coach/': () => jsonResponse({ messages: [] }),
      'GET /content/task-types/': () => jsonResponse([]),
    })

    renderApp('/how-to-answer')

    await user.click(await screen.findByRole('button', { name: 'Ask AI Coach' }))
    const dialog = await screen.findByRole('dialog', { name: 'AI Coach' })

    expect(within(dialog).getByLabelText('Message the AI Coach')).toHaveValue(
      'Help me answer Listening tasks at a level 11-12 standard.',
    )
    expect(within(dialog).getByText('Listening focus')).toBeInTheDocument()
  })

  it('redirects anonymous visitors to sign in', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => errorResponse('invalid_refresh_token', 401),
    })

    renderApp('/coach')

    expect(await screen.findByRole('heading', { name: /sign in/i })).toBeInTheDocument()
  })
})
