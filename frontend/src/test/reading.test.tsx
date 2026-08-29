import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'

const taskTypes = [
  {
    code: 'reading_correspondence',
    skill: 'reading',
    title: 'Reading Correspondence',
    part_number: 1,
    description: 'Read everyday messages.',
    strategy: ['Read the question first.'],
    common_mistakes: ['Choosing a plausible detail.'],
  },
]

const catalog = {
  count: 1,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      slug: 'garden-plot-renewal',
      version: 1,
      title: 'Garden Plot Renewal',
      topic: 'Community gardening',
      difficulty: 1,
      estimated_level: 5,
      task_type: 'reading_correspondence',
    },
  ],
}

const session = {
  id: '11111111-1111-4111-8111-111111111111',
  mode: 'learn',
  state: 'active',
  started_at: '2026-08-29T00:00:00Z',
  deadline_at: null,
  submitted_at: null,
  server_now: '2026-08-29T00:00:00Z',
  is_guest: true,
  content: {
    slug: 'garden-plot-renewal',
    title: 'Garden Plot Renewal',
    topic: 'Community gardening',
    difficulty: 1,
    estimated_level: 5,
    task_type: 'reading_correspondence',
    instructions: 'Read the email and answer.',
    learning_notes: 'Track names and dates.',
    stimulus: {
      type: 'email',
      from: 'Garden Association',
      to: 'Priya',
      subject: 'Renewal',
      body: 'Renew by March 31.',
    },
    questions: [
      {
        id: 10,
        order: 1,
        stem: 'When is the deadline?',
        skill_focus: 'detail',
        choices: [
          { id: 20, order: 1, text: 'March 31' },
          { id: 21, order: 2, text: 'April 5' },
        ],
      },
    ],
  },
  responses: [],
}

describe('Reading catalog', () => {
  it('loads reviewed sets and task guidance', async () => {
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/reading/': () => jsonResponse(catalog),
    })
    renderApp('/learn')

    expect(await screen.findByRole('heading', { name: 'Garden Plot Renewal' })).toBeInTheDocument()
    expect(screen.getAllByText('Part 1: Reading Correspondence')).toHaveLength(2)
    expect(screen.getByRole('button', { name: 'Learn with this set' })).toBeEnabled()
  })

  it('starts a guest session and keeps its token in session storage', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/reading/': () => jsonResponse(catalog),
      'POST /sessions/': () => jsonResponse({ ...session, guest_token: 'one-time-guest-token' }, 201),
    })
    renderApp('/learn')

    await user.click(await screen.findByRole('button', { name: 'Learn with this set' }))
    expect(await screen.findByRole('heading', { name: 'Garden Plot Renewal' })).toBeInTheDocument()
    expect(sessionStorage.getItem(`celpip-guest-${session.id}`)).toBe('one-time-guest-token')
  })
})

describe('Reading player', () => {
  it('saves an answer and shows immediate feedback in Learn mode', async () => {
    const user = userEvent.setup()
    sessionStorage.setItem(`celpip-guest-${session.id}`, 'guest-token')
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${session.id}/`]: () => jsonResponse(session),
      [`PUT /sessions/${session.id}/responses/10/`]: () =>
        jsonResponse({
          question_id: 10,
          selected_choice_id: 20,
          revision: 1,
          saved_at: '2026-08-29T00:01:00Z',
          replayed: false,
          feedback: {
            is_correct: true,
            correct_choice_id: 20,
            evidence: 'The email says March 31.',
            explanation: 'The date is explicit.',
            selected_choice_explanation: 'This matches the email.',
          },
        }),
    })
    renderApp(`/reading/session/${session.id}`)

    const question = await screen.findByRole('group', { name: /when is the deadline/i })
    await user.click(within(question).getByRole('radio', { name: 'March 31' }))
    await user.click(screen.getByRole('button', { name: /save & continue/i }))

    expect(await screen.findByText('Correct')).toBeInTheDocument()
    expect(screen.getByText(/The email says March 31/)).toBeInTheDocument()
    await waitFor(() => {
      const put = fetchSpy.mock.calls.find(([, init]) => init?.method === 'PUT')
      expect((put?.[1]?.headers as Record<string, string>)['X-Guest-Token']).toBe('guest-token')
      expect((put?.[1]?.headers as Record<string, string>)['Idempotency-Key']).toBeTruthy()
    })
  })
})
