import { describe, expect, it } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'

const USER = { id: 1, identifier: 'learner', email: '', date_joined: '2026-08-29T00:00:00Z' }
const PROFILE = {
  identifier: 'learner', exam_date: null, target_level: 9,
  target_listening: null, target_reading: null, target_writing: null,
  target_speaking: null, daily_minutes: 30, preferred_weekdays: [1, 2, 3, 4, 5],
  timezone: 'America/Toronto', practice_narration_voice: 'automatic',
  updated_at: '2026-08-29T00:00:00Z',
}

const authenticatedBootstrap = {
  'GET /auth/csrf/': () => jsonResponse({ detail: 'ok' }),
  'POST /auth/refresh/': () => jsonResponse({ access: 'access-token' }),
  'GET /me/': () => jsonResponse(USER),
  'GET /me/profile/': () => jsonResponse(PROFILE),
}

describe('learning loop', () => {
  it('keeps objective accuracy separate from AI-assisted estimates', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/progress/': () => jsonResponse({
        skills: [
          { skill: 'reading', attempts: 2, questions_correct: 6, questions_total: 8, accuracy_percent: 75, estimate_low: null, estimate_high: null, target: 9, last_activity: '2026-08-28T12:00:00Z' },
          { skill: 'writing', attempts: 1, questions_correct: 0, questions_total: 0, accuracy_percent: null, estimate_low: 6, estimate_high: 7, target: 9, last_activity: '2026-08-29T12:00:00Z' },
          { skill: 'listening', attempts: 0, questions_correct: 0, questions_total: 0, accuracy_percent: null, estimate_low: null, estimate_high: null, target: 9, last_activity: null },
          { skill: 'speaking', attempts: 0, questions_correct: 0, questions_total: 0, accuracy_percent: null, estimate_low: null, estimate_high: null, target: 9, last_activity: null },
        ],
        task_types: [], trends: [], coverage: { practised_skills: 2, total_skills: 4 },
        overall_readiness: null,
        readiness_explanation: 'An overall CELPIP score is not calculated because each skill is reported separately.',
        disclaimer: 'AI-assisted ranges are unofficial practice estimates.',
      }),
    })
    renderApp('/progress')
    expect(await screen.findByText('75% practice accuracy')).toBeInTheDocument()
    expect(screen.getByText('Estimated 6–7')).toBeInTheDocument()
    expect(screen.getByText(/overall CELPIP score is not calculated/i)).toBeInTheDocument()
  })

  it('lets a learner resolve a mistake without changing its evidence', async () => {
    const mistake = {
      id: 4, skill: 'reading', task_type: 'reading_correspondence', task_title: 'Reading Correspondence',
      stem: 'Why is Priya writing?', selected: 'To complain', correct: 'To request information',
      explanation: 'The final paragraph explicitly asks for the schedule.', occurrences: 2,
      state: 'open', first_seen_at: '2026-08-20T12:00:00Z', last_seen_at: '2026-08-28T12:00:00Z', resolved_at: null,
    }
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/mistakes/': () => jsonResponse({ results: [mistake] }),
      'PATCH /me/mistakes/4/': () => jsonResponse({ ...mistake, state: 'resolved', resolved_at: '2026-08-29T12:00:00Z' }),
    })
    const user = userEvent.setup()
    renderApp('/mistakes')
    expect(await screen.findByText('Why is Priya writing?')).toBeInTheDocument()
    expect(screen.getByText('Seen 2×')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /mark reviewed/i }))
    await waitFor(() => expect(screen.queryByText('Why is Priya writing?')).not.toBeInTheDocument())
  })

  it('shows why a study task was chosen and records completion', async () => {
    let task = {
      id: 8, scheduled_date: '2026-08-31', order: 1, skill: 'listening',
      task_type: 'listening_problem_solving', title: 'Listening to Problem Solving', minutes: 30,
      reason: 'Prioritised because this skill has not been practised yet.', destination: '/practice/listening',
      state: 'pending', completed_at: null,
    }
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => jsonResponse({
        id: 3, version: 2, generated_at: '2026-08-29T12:00:00Z', name: '',
        reason_summary: { priorities: { listening: 100, reading: 30, writing: 40, speaking: 100 }, rule: 'Weaker or unpractised skills come first.', source_attempts: 3 },
        tasks: [task],
        consistency: {
          streak: { days: 0, active_today: false, anchor: null },
          window_days: 14,
          days: [],
        },
      }),
      // The page refetches the plan after the PATCH so the streak refreshes;
      // reflect the completed state so the "Undo" button survives that refetch.
      'PATCH /me/study-plan/tasks/8/': () => {
        task = { ...task, state: 'completed', completed_at: '2026-08-29T12:00:00Z' }
        return jsonResponse({ state: 'completed', completed_at: '2026-08-29T12:00:00Z' })
      },
    })
    const user = userEvent.setup()
    renderApp('/study-plan')
    expect(await screen.findByText(task.reason)).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: /mark complete/i }))
    expect(await screen.findByRole('button', { name: 'Undo' })).toBeInTheDocument()
  })
})
