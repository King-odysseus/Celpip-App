import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'
import { baseSkills, makeDashboard } from './fixtures/dashboard'

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
  'GET /me/ai-feedback/history/': () => jsonResponse({ results: [] }),
}

const feedbackHistoryEntry = {
  created_at: '2026-08-28T12:00:00Z',
  kind: 'writing_feedback',
  skill: 'writing',
  task_type: 'writing_email',
  title: 'Email a landlord about noise',
  estimated_level_low: 6,
  estimated_level_high: 8,
  transcript: '',
  assessment: {
    overall_summary: 'Clear request, but tighten structure.',
    dimensions: [
      { key: 'content_coherence', rating: 3, evidence: 'The request is clear.', next_step: 'Add a closing.' },
      { key: 'vocabulary', rating: 2, evidence: 'Simple word choices.', next_step: 'Use formal verbs.' },
      { key: 'delivery', rating: 3, evidence: 'Easy to read.', next_step: 'Shorten sentences.' },
      { key: 'task_fulfillment', rating: 4, evidence: 'All parts answered.', next_step: 'Keep it up.' },
    ],
    strengths: ['Polite tone'],
    priorities: ['Expand vocabulary'],
    estimated_level_low: 6,
    estimated_level_high: 8,
    confidence: 'high',
    disclaimer: 'AI-assisted practice estimate — not an official CELPIP score.',
  },
}

describe('dashboard', () => {
  it('shows an anonymous preview without fetching learner data', async () => {
    renderApp('/')
    expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument()
    expect(screen.getByText(/browsing without an account/i)).toBeInTheDocument()
    expect(screen.queryByText('Day streak')).not.toBeInTheDocument()
  })

  it('shows a loading state while the dashboard resolves', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () => new Promise(() => {}),
    })
    renderApp('/')
    expect(await screen.findByRole('status')).toHaveTextContent(/loading your dashboard/i)
  })

  it('shows an error state when the dashboard fails', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () => errorResponse('server_error', 500, 'Dashboard unavailable.'),
    })
    renderApp('/')
    expect(await screen.findByRole('alert')).toHaveTextContent('Dashboard unavailable.')
  })

  it('renders an empty dashboard with insufficient-evidence readiness', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () =>
        jsonResponse(
          makeDashboard({
            skills: baseSkills.map((skill) => ({ ...skill, attempts: 0, questions_correct: 0, questions_total: 0, accuracy_percent: null, estimate_low: null, estimate_high: null })),
            coverage: { practised_skills: 0, total_skills: 4 },
            totals: { objective_questions_completed: 0, completed_attempts: 0 },
            streak: { days: 0, active_today: false, anchor: null, timezone: 'America/Toronto', rule: '…' },
            recent_results: [],
            signals: { strongest: null, needs_attention: { skill: 'listening', measure: null, value: null, planning_signal: null, attempts: 0, basis: 'No practice recorded yet' }, note: '…' },
            readiness: {
              ...makeDashboard().readiness,
              indicator: null,
              state: 'insufficient_evidence',
              explanation: 'There is not enough practice evidence yet.',
            },
            today: { date: '2026-08-29', timezone: 'America/Toronto', tasks: [] },
          }),
        ),
    })
    renderApp('/')
    expect(await screen.findByText('Day streak')).toBeInTheDocument()
    // Streak, objective questions, and completed attempts all report zero.
    expect(screen.getAllByText('0').length).toBeGreaterThanOrEqual(3)
    expect(screen.getByText(/no completed attempts yet/i)).toBeInTheDocument()
    expect(screen.getByText(/not enough practice evidence/i)).toBeInTheDocument()
  })

  it('renders stats, today tasks, signals, recent results, and readiness', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () => jsonResponse(makeDashboard()),
    })
    renderApp('/')

    // Stats.
    expect(await screen.findByText('Day streak')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument() // objective questions
    expect(screen.getByText('3')).toBeInTheDocument() // completed attempts

    // Today's study task.
    expect(screen.getByText('Listening to Problem Solving')).toBeInTheDocument()

    // Signals.
    expect(screen.getByText('Strongest skill')).toBeInTheDocument()
    expect(screen.getByText('Needs attention')).toBeInTheDocument()
    expect(screen.getAllByText('75% practice accuracy').length).toBeGreaterThanOrEqual(1)

    // Recent results.
    expect(screen.getByText('Garden Plot Renewal')).toBeInTheDocument()
    expect(screen.getByText('75%')).toBeInTheDocument()

    // Readiness indicator.
    expect(screen.getByText('Practice planning indicator')).toBeInTheDocument()
    expect(screen.getByText(/unofficial · not a celpip score/i)).toBeInTheDocument()
    expect(screen.getByText(/not a celpip score or a score prediction/i)).toBeInTheDocument()
    expect(screen.getByText(/skill coverage/i)).toBeInTheDocument()
    expect(screen.getByText(/practice volume/i)).toBeInTheDocument()
  })

  it('shows the next upcoming task when nothing is scheduled today', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () =>
        jsonResponse(
          makeDashboard({
            today: { date: '2026-08-29', timezone: 'America/Toronto', tasks: [] },
            next_upcoming_task: {
              id: 9, scheduled_date: '2026-08-31', order: 1, skill: 'reading',
              task_type: 'reading_correspondence', title: 'Reading Correspondence',
              minutes: 20, reason: 'Next in rotation.', destination: '/practice',
              state: 'pending', completed_at: null,
            },
          }),
        ),
    })
    renderApp('/')
    expect(await screen.findByText('Nothing scheduled today.')).toBeInTheDocument()
    expect(screen.getByText(/next up: reading correspondence/i)).toBeInTheDocument()
  })

  it('renders AI feedback history and expands an entry to revisit insights', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/dashboard/': () => jsonResponse(makeDashboard()),
      'GET /me/ai-feedback/history/': () =>
        jsonResponse({ results: [feedbackHistoryEntry] }),
    })
    renderApp('/')

    expect(await screen.findByText('Feedback history')).toBeInTheDocument()
    // The card title is static; the entries load async, so wait for them.
    expect(await screen.findByText('Email a landlord about noise')).toBeInTheDocument()
    expect(screen.getAllByText('6–8').length).toBeGreaterThan(0)
    // Analysis is hidden until the entry is expanded (closed <details> keeps
    // its content in the DOM but out of view).
    expect(screen.getByText(/clear request, but tighten structure/i)).not.toBeVisible()

    await user.click(screen.getByText('Email a landlord about noise'))

    expect(
      await waitFor(() => screen.getByText(/clear request, but tighten structure/i)),
    ).toBeVisible()
    expect(screen.getByText('Content/Coherence')).toBeInTheDocument()
    expect(screen.getByText('Expand vocabulary')).toBeInTheDocument()
  })
})
