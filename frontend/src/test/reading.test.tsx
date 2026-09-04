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

  it('marks lessons completed in an earlier study plan', async () => {
    installRouteFetch({
      'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
      'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
      'GET /me/': () => jsonResponse({ id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }),
      'GET /me/profile/': () => jsonResponse({ identifier: 'learner', exam_date: null, target_level: 9, target_listening: null, target_reading: null, target_writing: null, target_speaking: null, daily_minutes: 30, preferred_weekdays: [1], timezone: 'America/Toronto', practice_narration_voice: 'automatic', updated_at: '2026-08-29T00:00:00Z' }),
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/reading/': () => jsonResponse(catalog),
      'GET /me/study-plan/': () => jsonResponse({
        id: 2, version: 4, generated_at: '2026-08-29T00:00:00Z', name: '',
        difficulty_preference: 'adaptive', reason_summary: { priorities: {}, rule: '', source_attempts: 1 },
        completed_lessons: ['garden-plot-renewal'], tasks: [],
        consistency: { streak: { days: 0, active_today: false, anchor: null }, window_days: 1, today: '2026-08-29', days: [] },
      }),
    })
    renderApp('/practice')

    expect(await screen.findByText('Completed via Study Plan')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Practice again' })).toBeInTheDocument()
  })
})

describe('Reading player', () => {
  it('renders an image when Reading content provides one', async () => {
    const imageSession = {
      ...session,
      content: {
        ...session.content,
        stimulus: {
          ...session.content.stimulus,
          image_url: '/reading/utility-rate-comparison.png',
          image_alt: 'Comparison of household utility plans',
        },
      },
    }
    sessionStorage.setItem(`celpip-guest-${session.id}`, 'guest-token')
    installRouteFetch({
      [`GET /sessions/${session.id}/`]: () => jsonResponse(imageSession),
    })
    renderApp(`/reading/session/${session.id}`)

    expect(await screen.findByRole('img', { name: 'Comparison of household utility plans' })).toHaveAttribute(
      'src',
      '/reading/utility-rate-comparison.png',
    )
  })

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

describe('Study plan completion inside a session', () => {
  const authBootstrap = {
    'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
    'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
    'GET /me/': () => jsonResponse({ id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }),
    'GET /me/profile/': () => jsonResponse({
      identifier: 'learner', exam_date: null, target_level: 9, target_listening: null,
      target_reading: null, target_writing: null, target_speaking: null, daily_minutes: 30,
      preferred_weekdays: [1], timezone: 'America/Toronto', practice_narration_voice: 'automatic',
      updated_at: '2026-08-29T00:00:00Z',
    }),
    [`GET /sessions/${session.id}/`]: () => jsonResponse(session),
  }

  const otherPendingTask = {
    id: 9, scheduled_date: '2026-08-29', order: 2, skill: 'writing', task_type: 'writing_email',
    title: 'Practise Writing an Email', minutes: 30, reason: 'Writing is next.',
    destination: '/practice/writing', state: 'pending', completed_at: null,
  }
  const thisTask = {
    id: 8, scheduled_date: '2026-08-29', order: 1, skill: 'reading', task_type: 'reading_correspondence',
    title: 'Practise Reading Correspondence', minutes: 30, reason: 'Reading is a priority.',
    destination: '/practice', state: 'pending', completed_at: null,
  }

  it('shows and directly links to the next question when another task is still pending that day', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authBootstrap,
      'PATCH /me/study-plan/tasks/8/': () => jsonResponse({ id: 8, state: 'completed', completed_at: '2026-08-29T12:00:00Z' }),
      'GET /me/study-plan/': () => jsonResponse({
        id: 2, version: 4, generated_at: '2026-08-29T00:00:00Z', name: '',
        reason_summary: { priorities: {}, rule: '', source_attempts: 1 },
        tasks: [{ ...thisTask, state: 'completed', completed_at: '2026-08-29T12:00:00Z' }, otherPendingTask],
        consistency: {
          streak: { days: 1, active_today: true, anchor: 'today', at_risk: false, grace_days_remaining: null },
          window_days: 1, today: '2026-08-29', days: [],
        },
      }),
    })
    renderApp(`/reading/session/${session.id}?study_task=8`)

    await user.click(await screen.findByRole('button', { name: 'Mark as complete' }))
    await user.click(await screen.findByRole('button', { name: 'Yes, I understand' }))

    expect(await screen.findByText("Next in today’s Study Plan")).toBeInTheDocument()
    expect(screen.getByText(otherPendingTask.title)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Next question' })).toHaveAttribute('href', otherPendingTask.destination)
    expect(screen.queryByRole('dialog', { name: 'Your improvement recap' })).not.toBeInTheDocument()
    expect(screen.queryByText(/study plan is complete/i)).not.toBeInTheDocument()
  })

  it('celebrates the day as complete once no other task is pending today', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authBootstrap,
      'PATCH /me/study-plan/tasks/8/': () => jsonResponse({ id: 8, state: 'completed', completed_at: '2026-08-29T12:00:00Z' }),
      'GET /me/study-plan/': () => jsonResponse({
        id: 2, version: 4, generated_at: '2026-08-29T00:00:00Z', name: '',
        reason_summary: { priorities: {}, rule: '', source_attempts: 1 },
        tasks: [{ ...thisTask, state: 'completed', completed_at: '2026-08-29T12:00:00Z' }],
        consistency: {
          streak: { days: 5, active_today: true, anchor: 'today', at_risk: false, grace_days_remaining: null },
          window_days: 1, today: '2026-08-29', days: [],
        },
      }),
    })
    renderApp(`/reading/session/${session.id}?study_task=8`)

    await user.click(await screen.findByRole('button', { name: 'Mark as complete' }))
    await user.click(await screen.findByRole('button', { name: 'Yes, I understand' }))

    expect(await screen.findByText(/study plan is complete/i)).toBeInTheDocument()
    expect(screen.getByText('5-day streak')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Next question' })).not.toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Return to Study Plan' })).toHaveAttribute('href', '/study-plan')
  })
})
