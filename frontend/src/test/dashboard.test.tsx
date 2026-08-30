import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'
import type { Dashboard } from '../features/learning/types'

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

const baseSkills: Dashboard['skills'] = [
  {
    skill: 'listening', attempts: 0, questions_correct: 0, questions_total: 0,
    accuracy_percent: null, estimate_low: null, estimate_high: null,
    target: 9, last_activity: null,
  },
  {
    skill: 'reading', attempts: 2, questions_correct: 6, questions_total: 8,
    accuracy_percent: 75, estimate_low: null, estimate_high: null,
    target: 9, last_activity: '2026-08-29T12:00:00Z',
  },
  {
    skill: 'writing', attempts: 1, questions_correct: 0, questions_total: 0,
    accuracy_percent: null, estimate_low: 6, estimate_high: 8,
    target: 9, last_activity: '2026-08-28T12:00:00Z',
  },
  {
    skill: 'speaking', attempts: 0, questions_correct: 0, questions_total: 0,
    accuracy_percent: null, estimate_low: null, estimate_high: null,
    target: 9, last_activity: null,
  },
]

function makeDashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    skills: baseSkills,
    task_types: [],
    trends: [],
    coverage: { practised_skills: 2, total_skills: 4 },
    totals: { objective_questions_completed: 8, completed_attempts: 3 },
    streak: {
      days: 4, active_today: true, anchor: 'today',
      timezone: 'America/Toronto', rule: 'Unique submitted/completed activity dates.',
    },
    recent_results: [
      {
        date: '2026-08-29T12:00:00Z', skill: 'reading',
        task_type: 'reading_correspondence', title: 'Garden Plot Renewal',
        measure: 'accuracy_percent', value: 75, label: 'Practice accuracy',
        destination: '/practice',
      },
    ],
    signals: {
      strongest: {
        skill: 'reading', measure: 'accuracy_percent', value: 75,
        planning_signal: 75, attempts: 2, basis: '75% practice accuracy',
      },
      needs_attention: {
        skill: 'listening', measure: null, value: null,
        planning_signal: null, attempts: 0, basis: 'No practice recorded yet',
      },
      note: 'Cross-skill comparison uses an unofficial practice planning indicator.',
    },
    readiness: {
      label: 'Practice planning indicator',
      indicator: 58,
      state: 'estimated',
      is_official: false,
      formula: '0.30 × coverage + 0.25 × recency + 0.25 × volume + 0.20 × performance',
      components: [
        { key: 'coverage', label: 'Skill coverage', weight: 0.3, value: 50, raw: '2 of 4 skills practised', explanation: 'Share of the four skills with an attempt.' },
        { key: 'recency', label: 'Recency', weight: 0.25, value: 100, raw: 'Most recent activity 0 day(s) ago', explanation: '100 for activity today.' },
        { key: 'volume', label: 'Practice volume', weight: 0.25, value: 30, raw: '3 completed attempt(s)', explanation: '10 points per attempt.' },
        { key: 'performance', label: 'Performance signal', weight: 0.2, value: 66, raw: '2 skill(s) with evidence', explanation: 'Average of per-skill signals.' },
      ],
      explanation: 'A weighted planning aid, not a score.',
      disclaimer: 'This is an unofficial practice planning indicator, not a CELPIP score or a score prediction.',
    },
    today: {
      date: '2026-08-29',
      timezone: 'America/Toronto',
      tasks: [
        {
          id: 8, scheduled_date: '2026-08-29', order: 1, skill: 'listening',
          task_type: 'listening_problem_solving', title: 'Listening to Problem Solving',
          minutes: 30, reason: 'Prioritised skill.', destination: '/practice/listening',
          state: 'pending', completed_at: null,
        },
      ],
    },
    next_upcoming_task: null,
    disclaimer: 'Practice analytics are not official CELPIP results.',
    ...overrides,
  }
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
    expect(screen.getByText('75% practice accuracy')).toBeInTheDocument()

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
})
