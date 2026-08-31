import { describe, expect, it, vi } from 'vitest'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'
import type { StudyConsistency, StudyPlan } from '../features/learning/types'

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

/** 14-day consistency strip ending "today" (2026-08-29), with the final day
 *  completed iff `completedDays >= 1` (all four skills, as in the fixtures). */
function makeConsistency(completedDays: number): StudyConsistency {
  const end = new Date('2026-08-29T12:00:00Z')
  const days = Array.from({ length: 14 }, (_, index) => {
    const date = new Date(end)
    date.setUTCDate(end.getUTCDate() - (13 - index))
    const completed = index === 13 && completedDays >= 1
    return {
      date: date.toISOString().slice(0, 10),
      skills: { listening: completed, reading: completed, writing: completed, speaking: completed },
      completed,
    }
  })
  return {
    streak: {
      days: completedDays >= 1 ? 1 : 0,
      active_today: completedDays >= 1,
      anchor: completedDays >= 1 ? 'today' : null,
    },
    window_days: 14,
    today: '2026-08-29',
    days,
  }
}

function makePlan(overrides: Partial<StudyPlan> = {}): StudyPlan {
  return {
    id: 1,
    version: 3,
    generated_at: '2026-08-15T00:00:00Z',
    name: '',
    reason_summary: {
      priorities: { listening: 120, reading: 120, writing: 120, speaking: 120 },
      rule: 'Unpractised and weaker skills come first.',
      source_attempts: 0,
    },
    tasks: [
      {
        id: 1,
        scheduled_date: '2026-08-29',
        order: 1,
        skill: 'reading',
        task_type: 'reading_correspondence',
        title: 'Practise Reading Correspondence',
        minutes: 30,
        reason: 'Reading is a priority.',
        destination: '/practice',
        state: 'pending',
        completed_at: null,
      },
    ],
    consistency: makeConsistency(0),
    ...overrides,
  }
}

function completedPlan(): StudyPlan {
  return makePlan({
    tasks: [
      {
        id: 1,
        scheduled_date: '2026-08-29',
        order: 1,
        skill: 'reading',
        task_type: 'reading_correspondence',
        title: 'Practise Reading Correspondence',
        minutes: 30,
        reason: 'Reading is a priority.',
        destination: '/practice',
        state: 'completed',
        completed_at: '2026-08-29T12:00:00Z',
      },
    ],
    consistency: makeConsistency(1),
  })
}

describe('study plan', () => {
  it('shows the plan name, tasks, and streak bar', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => jsonResponse(makePlan()),
    })
    renderApp('/study-plan')

    expect(await screen.findByRole('heading', { name: 'Study Plan' })).toBeInTheDocument()
    // Wait for the plan payload so the body (header card, streak, tasks) is flushed.
    expect(await screen.findByRole('heading', { name: 'Study Plan v3' })).toBeInTheDocument()
    expect(screen.getByText('Practise Reading Correspondence')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Mark complete' })).toBeInTheDocument()

    // Streak bar with the 14-day strip and skill legend.
    expect(screen.getByText('Study streak')).toBeInTheDocument()
    expect(screen.getByText('0-day streak')).toBeInTheDocument()
    expect(screen.getByText(/complete a task to start a streak/i)).toBeInTheDocument()
    expect(screen.getByText('Listening')).toBeInTheDocument()
    expect(screen.getByText('Speaking')).toBeInTheDocument()
  })

  it('renames the plan and persists it on blur', async () => {
    const user = userEvent.setup()
    const patchName = vi.fn((init: RequestInit) => {
      const body = JSON.parse(String(init.body))
      return jsonResponse(makePlan({ name: body.name }))
    })
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => jsonResponse(makePlan()),
      'PATCH /me/study-plan/': patchName,
    })
    renderApp('/study-plan')

    const input = await screen.findByLabelText('Plan name')
    expect(input).toHaveValue('')

    await user.clear(input)
    await user.type(input, 'Countdown push')
    await user.tab() // blur the input, which persists

    await waitFor(() => expect(patchName).toHaveBeenCalledTimes(1))
    expect(JSON.parse(String(patchName.mock.calls[0][0].body))).toEqual({ name: 'Countdown push' })
    // The header now shows the saved name.
    expect(await screen.findByRole('heading', { name: 'Countdown push' })).toBeInTheDocument()
  })

  it('marking a task complete persists and refreshes the streak', async () => {
    const user = userEvent.setup()
    let planFetches = 0
    const patchTask = vi.fn((init: RequestInit) => {
      const body = JSON.parse(String(init.body))
      expect(body).toEqual({ state: 'completed' })
      return jsonResponse({ id: 1, state: 'completed', completed_at: '2026-08-29T12:00:00Z' })
    })
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => {
        planFetches += 1
        // First fetch returns the pending plan; the post-patch refetch returns the completed one.
        return jsonResponse(planFetches === 1 ? makePlan() : completedPlan())
      },
      'PATCH /me/study-plan/tasks/1/': patchTask,
    })
    renderApp('/study-plan')

    const button = await screen.findByRole('button', { name: 'Mark complete' })
    await user.click(button)
    await user.click(await screen.findByRole('button', { name: 'Yes, I understand' }))

    await waitFor(() => expect(patchTask).toHaveBeenCalledTimes(1))
    // The completion triggered a refetch, and the streak bar updated.
    await waitFor(() => expect(planFetches).toBe(2))
    expect(await screen.findByRole('button', { name: 'Undo' })).toBeInTheDocument()
    expect(screen.getByText('1-day streak')).toBeInTheDocument()
    expect(screen.getByText(/active today/i)).toBeInTheDocument()
  })

  it('shows an error when the plan fails to load', async () => {
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => errorResponse('server_error', 500, 'Plan unavailable.'),
    })
    renderApp('/study-plan')
    expect(await screen.findByRole('alert')).toHaveTextContent('Plan unavailable.')
  })

  it('shows the performance recap before navigating to a lesson', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => jsonResponse(makePlan()),
      'GET /me/progress/': () => jsonResponse({
        skills: [{ skill: 'reading', attempts: 1, questions_correct: 5, questions_total: 10, accuracy_percent: 50, estimate_low: null, estimate_high: null, target: 9, last_activity: null }],
        task_types: [], trends: [], coverage: { practised_skills: 1, total_skills: 4 },
        overall_readiness: null, readiness_explanation: '', disclaimer: '',
      }),
      'GET /me/mistakes/': () => jsonResponse({ results: [] }),
    })
    renderApp('/study-plan')

    await user.click(await screen.findByRole('button', { name: /open practice/i }))
    const recap = await screen.findByRole('dialog', { name: 'Your improvement recap' })
    expect(recap).toBeInTheDocument()
    expect(await screen.findByText(/reading accuracy is 50%/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /start lesson/i })).toBeInTheDocument()
  })

  it('lets the learner choose a difficulty strategy', async () => {
    const user = userEvent.setup()
    const patchDifficulty = vi.fn((init: RequestInit) => {
      const body = JSON.parse(String(init.body))
      return jsonResponse(makePlan({ difficulty_preference: body.difficulty_preference }))
    })
    installRouteFetch({
      ...authenticatedBootstrap,
      'GET /me/study-plan/': () => jsonResponse(makePlan({ difficulty_preference: 'adaptive' })),
      'PATCH /me/study-plan/': patchDifficulty,
    })
    renderApp('/study-plan')

    await user.selectOptions(await screen.findByLabelText('Lesson difficulty'), 'challenge')
    await waitFor(() => expect(patchDifficulty).toHaveBeenCalledTimes(1))
    expect(JSON.parse(String(patchDifficulty.mock.calls[0][0].body))).toEqual({ difficulty_preference: 'challenge' })
  })
})
