import type { Dashboard } from '../../features/learning/types'

export const baseSkills: Dashboard['skills'] = [
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

/** A complete, realistic Dashboard payload for tests that need `/me/dashboard/`
 * to succeed (the dashboard only renders CountdownCard/TargetCard/stats once
 * this resolves) — shared so every test doesn't hand-roll the full shape. */
export function makeDashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    skills: baseSkills,
    task_types: [],
    trends: [],
    coverage: { practised_skills: 2, total_skills: 4 },
    totals: { objective_questions_completed: 8, completed_attempts: 3 },
    streak: {
      days: 4, active_today: true, anchor: 'today', at_risk: false, grace_days_remaining: null,
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
