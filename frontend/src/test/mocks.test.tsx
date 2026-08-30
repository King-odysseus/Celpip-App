import { screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'
import type { MockAttempt, MockFormat, MockTask, Skill } from '../features/mocks/types'

const attemptId = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
const mockSessionId = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'

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

const authBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
  'GET /me/': () => jsonResponse(USER),
  'GET /me/profile/': () => jsonResponse(PROFILE),
}

const anonymousBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => errorResponse('invalid_refresh_token', 401),
}

const mockFormat: MockFormat = {
  code: 'celpip-general-2026-08',
  verified_on: '2026-08-29',
  official_source_urls: ['https://www.celpip.ca/take-celpip/test-format/'],
  component_order: ['listening', 'reading', 'writing', 'speaking'],
  component_timings: {
    listening: { public_range_minutes: [46, 55], mock_seconds: 3300 },
    reading: { public_range_minutes: [43, 56], mock_seconds: 3360 },
    writing: { public_range_minutes: [53, 53], mock_seconds: 3180 },
    speaking: { public_range_minutes: [15, 15], mock_seconds: 900 },
  },
  task_structure: [],
  scope: 'compact_task_family_mock',
  limitation: 'Compact task-family scope.',
}

const currentTask = {
  order: 1,
  section: 'listening' as Skill,
  task_type: 'listening_problem_solving',
  title: 'Listening: Problem Solving',
  session_id: 'cccccccc-cccc-4ccc-8ccc-cccccccccccc',
  kind: 'objective' as const,
  launch_url: `/mock/${attemptId}/task/1`,
}

function makeTasks(currentOrder?: number): MockTask[] {
  const groups: [Skill, number][] = [
    ['listening', 6],
    ['reading', 4],
    ['writing', 2],
    ['speaking', 8],
  ]
  const tasks: MockTask[] = []
  let order = 1
  for (const [section, count] of groups) {
    for (let i = 0; i < count; i++) {
      tasks.push({
        order,
        section,
        task_type: `${section}_task_${i + 1}`,
        title: `${section} task ${i + 1}`,
        state: order === currentOrder ? 'current' : 'pending',
        session_id: `00000000-0000-4000-8000-${String(order).padStart(12, '0')}`,
        kind: section === 'listening' || section === 'reading' ? 'objective' : section,
      })
      order += 1
    }
  }
  return tasks
}

function makeAttempt(overrides: Partial<MockAttempt> = {}): MockAttempt {
  return {
    id: attemptId,
    state: 'ready',
    scope: 'compact_task_family_mock',
    created_at: '2026-08-29T00:00:00Z',
    started_at: null,
    completed_at: null,
    server_now: '2026-08-29T00:00:00Z',
    section_started_at: null,
    section_deadline_at: null,
    current_section: null,
    current_order: 0,
    current_task: null,
    progress: { completed: 0, total: 20 },
    format: mockFormat,
    disclaimer: 'Unofficial practice results only.',
    tasks: makeTasks(),
    ...overrides,
  }
}

const activeAttempt = makeAttempt({
  state: 'active',
  started_at: '2026-08-29T00:00:00Z',
  section_started_at: '2026-08-29T00:00:00Z',
  section_deadline_at: '2026-08-29T00:55:00Z',
  current_section: 'listening',
  current_order: 1,
  current_task: currentTask,
  tasks: makeTasks(1),
})

const mockReadingSession = {
  id: mockSessionId,
  mode: 'mock',
  state: 'active',
  started_at: '2026-08-29T00:00:00Z',
  deadline_at: '2026-08-29T00:55:00Z',
  submitted_at: null,
  server_now: '2026-08-29T00:00:00Z',
  is_guest: false,
  content: {
    slug: 'garden-plot-renewal',
    title: 'Garden Plot Renewal',
    topic: 'Community gardening',
    difficulty: 1,
    estimated_level: 5,
    task_type: 'reading_correspondence',
    skill: 'reading',
    instructions: 'Read the email and answer.',
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
  mock: {
    attempt_id: attemptId,
    task_order: 1,
    section: 'reading',
    results_released: false,
    return_url: `/mock/${attemptId}`,
  },
}

describe('Mock Tests hub', () => {
  it('shows an anonymous account CTA with the honest compact-scope warning', async () => {
    installRouteFetch(anonymousBootstrap)
    renderApp('/mock')

    expect(await screen.findByRole('heading', { name: 'Mock Tests' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /create a free account/i })).toHaveAttribute('href', '/register')
    expect(screen.getAllByRole('link', { name: 'Sign in' }).length).toBeGreaterThan(0)
    expect(screen.getByRole('heading', { name: /honest compact scope/i })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /official component order and timing/i })).toBeInTheDocument()
  })

  it('creates a mock, starts it, and lands on the active workspace', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authBootstrap,
      'GET /mocks/': () => jsonResponse({ count: 0, results: [] }),
      'POST /mocks/': () => jsonResponse(makeAttempt(), 201),
      [`GET /mocks/${attemptId}/`]: () => jsonResponse(makeAttempt()),
      [`POST /mocks/${attemptId}/start/`]: () => jsonResponse(activeAttempt),
    })
    renderApp('/mock')

    await user.click(await screen.findByRole('button', { name: /create mock/i }))
    await user.click(await screen.findByRole('button', { name: /start mock/i }))

    expect(await screen.findByRole('button', { name: /launch task/i })).toBeInTheDocument()
    expect(screen.getByText(/listening · task 1 of 20/i)).toBeInTheDocument()
    expect(screen.getByText(/0 of 20 complete/i)).toBeInTheDocument()
  })

  it('resumes an in-progress attempt from the history list', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authBootstrap,
      'GET /mocks/': () => jsonResponse({ count: 1, results: [activeAttempt] }),
      [`GET /mocks/${attemptId}/`]: () => jsonResponse(activeAttempt),
    })
    renderApp('/mock')

    expect(await screen.findByText(/in progress/i)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /resume/i }))

    expect(await screen.findByRole('button', { name: /launch task/i })).toBeInTheDocument()
  })
})

describe('Mock workspace results', () => {
  it('shows separated component results and no overall score', async () => {
    const completed = makeAttempt({
      state: 'completed',
      completed_at: '2026-08-29T00:30:00Z',
      current_task: null,
      tasks: makeTasks(),
    })
    installRouteFetch({
      ...authBootstrap,
      [`GET /mocks/${attemptId}/`]: () => jsonResponse(completed),
      [`GET /mocks/${attemptId}/results/`]: () =>
        jsonResponse({
          attempt_id: attemptId,
          completed_at: '2026-08-29T00:30:00Z',
          components: [
            { skill: 'listening', measure: 'practice_accuracy', raw_correct: 12, raw_possible: 18, accuracy_percent: 67 },
            { skill: 'reading', measure: 'practice_accuracy', raw_correct: 8, raw_possible: 12, accuracy_percent: 67 },
            { skill: 'writing', measure: 'ai_assisted_practice_estimate', feedback_ready: 2, tasks_total: 2, estimate_low: 6, estimate_high: 7 },
            { skill: 'speaking', measure: 'ai_assisted_practice_estimate', feedback_ready: 8, tasks_total: 8, estimate_low: 5, estimate_high: 6 },
          ],
          overall_score: null,
          disclaimer: 'Unofficial practice results only.',
        }),
    })
    renderApp(`/mock/${attemptId}`)

    expect(await screen.findByRole('heading', { name: /four component results/i })).toBeInTheDocument()
    expect(screen.getByText(/no overall score is calculated/i)).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Listening' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Reading' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Writing' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Speaking' })).toBeInTheDocument()
    expect(screen.getByText(/12\/18/)).toBeInTheDocument()
    expect(screen.getByText(/≈ 6–7/)).toBeInTheDocument()
  })
})

describe('Mock task submit-to-advance', () => {
  it('submits a reading task, advances the mock, and returns to the workspace', async () => {
    const user = userEvent.setup()
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${mockSessionId}/`]: () => jsonResponse(mockReadingSession),
      [`PUT /sessions/${mockSessionId}/responses/10/`]: () =>
        jsonResponse({
          question_id: 10,
          selected_choice_id: 20,
          revision: 1,
          saved_at: '2026-08-29T00:01:00Z',
          replayed: false,
        }),
      [`POST /sessions/${mockSessionId}/submit/`]: () =>
        jsonResponse({
          session_id: mockSessionId,
          state: 'submitted',
          awaiting_mock_results: true,
          mock: {
            attempt_id: attemptId,
            task_order: 1,
            section: 'reading',
            results_released: false,
            return_url: `/mock/${attemptId}`,
          },
          disclaimer: 'Corrections and practice estimates are released after the full mock.',
          replayed: false,
        }),
      [`POST /mocks/${attemptId}/advance/`]: () => jsonResponse(activeAttempt),
      [`GET /mocks/${attemptId}/`]: () => jsonResponse(activeAttempt),
    })
    renderApp(`/reading/session/${mockSessionId}`)

    const question = await screen.findByRole('group', { name: /when is the deadline/i })
    await user.click(within(question).getByRole('radio', { name: 'March 31' }))
    await user.click(screen.getByRole('button', { name: /save & continue/i }))
    await user.click(await screen.findByRole('button', { name: /submit task/i }))

    // The workspace loads after advancing and shows the next current task.
    expect(await screen.findByRole('button', { name: /launch task/i })).toBeInTheDocument()

    const advanceCall = fetchSpy.mock.calls.find(
      ([url, init]) => String(url).endsWith(`/mocks/${attemptId}/advance/`) && init?.method === 'POST',
    )
    expect(advanceCall).toBeTruthy()
    expect(JSON.parse(String(advanceCall?.[1]?.body))).toEqual({ expected_order: 1 })
  })
})

describe('Mock reopened submitted task', () => {
  it('advances the mock before returning to the workspace, avoiding a resume loop', async () => {
    const user = userEvent.setup()
    const fetchSpy = installRouteFetch({
      // The child already submitted; its advance never completed, so reopening
      // lands on the notice instead of the workspace's stale current task.
      [`GET /sessions/${mockSessionId}/`]: () =>
        jsonResponse({ ...mockReadingSession, state: 'submitted' }),
      [`POST /mocks/${attemptId}/advance/`]: () => jsonResponse(activeAttempt),
      [`GET /mocks/${attemptId}/`]: () => jsonResponse(activeAttempt),
    })
    renderApp(`/reading/session/${mockSessionId}`)

    await user.click(await screen.findByRole('button', { name: /return to mock/i }))

    // The idempotent advance lands on the workspace with the next current task.
    expect(await screen.findByRole('button', { name: /launch task/i })).toBeInTheDocument()

    const advanceCall = fetchSpy.mock.calls.find(
      ([url, init]) => String(url).endsWith(`/mocks/${attemptId}/advance/`) && init?.method === 'POST',
    )
    expect(advanceCall).toBeTruthy()
    expect(JSON.parse(String(advanceCall?.[1]?.body))).toEqual({ expected_order: 1 })
  })
})
