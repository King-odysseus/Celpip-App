/**
 * A small synthetic mock attempt — one task per skill — used to exercise the
 * real orchestration UI (create → preflight → start → launch → submit →
 * advance → … → completed → results) without needing a real 20/33-task bank.
 * The frontend already reads task count from attempt.progress.total rather
 * than assuming 20, so this is exactly as real a workout of that code path
 * as a full attempt, just faster to drive.
 */

export const attemptId = 'e2e00000-0000-4000-8000-000000000001'
export const listeningSessionId = 'e2e00000-0000-4000-8000-0000000000a1'
export const readingSessionId = 'e2e00000-0000-4000-8000-0000000000a2'
export const writingSessionId = 'e2e00000-0000-4000-8000-0000000000a3'
export const speakingSessionId = 'e2e00000-0000-4000-8000-0000000000a4'

export const mockFormat = {
  code: 'celpip-general-2026-08',
  verified_on: '2026-08-29',
  official_source_urls: ['https://www.celpip.ca/take-celpip/test-format/'],
  component_order: ['listening', 'reading', 'writing', 'speaking'],
  component_timings: {
    listening: { public_range_minutes: [46, 55], mock_seconds: 5 },
    reading: { public_range_minutes: [43, 56], mock_seconds: 5 },
    writing: { public_range_minutes: [53, 53], mock_seconds: 5 },
    speaking: { public_range_minutes: [15, 15], mock_seconds: 5 },
  },
  task_structure: [],
  scope: 'compact_task_family_mock',
  limitation: 'Compact task-family scope — end-to-end fixture.',
}

const baseTasks = [
  { order: 1, section: 'listening', task_type: 'listening_problem_solving', title: 'Listening task', session_id: listeningSessionId, kind: 'objective' as const },
  { order: 2, section: 'reading', task_type: 'reading_correspondence', title: 'Reading task', session_id: readingSessionId, kind: 'objective' as const },
  { order: 3, section: 'writing', task_type: 'writing_email', title: 'Writing task', session_id: writingSessionId, kind: 'writing' as const },
  { order: 4, section: 'speaking', task_type: 'speaking_advice', title: 'Speaking task', session_id: speakingSessionId, kind: 'speaking' as const },
]

export function makeTasks(currentOrder?: number, states: Record<number, string> = {}) {
  return baseTasks.map((task) => ({
    ...task,
    state: states[task.order] ?? (task.order === currentOrder ? 'current' : 'pending'),
  }))
}

export function makeAttempt(overrides: Record<string, unknown> = {}) {
  return {
    id: attemptId,
    state: 'ready',
    scope: 'compact_task_family_mock',
    created_at: '2026-08-29T00:00:00.000Z',
    started_at: null,
    completed_at: null,
    server_now: new Date().toISOString(),
    section_started_at: null,
    section_deadline_at: null,
    current_section: null,
    current_order: 0,
    current_task: null,
    progress: { completed: 0, total: 4 },
    format: mockFormat,
    disclaimer: 'Unofficial practice results only.',
    tasks: makeTasks(),
    ...overrides,
  }
}

function currentTaskFor(order: number) {
  const task = baseTasks.find((item) => item.order === order)!
  return {
    order: task.order,
    section: task.section,
    task_type: task.task_type,
    title: task.title,
    session_id: task.session_id,
    kind: task.kind,
    launch_url: `/mock/${attemptId}/task/${task.order}`,
  }
}

export function activeAttemptAt(order: number, overrides: Record<string, unknown> = {}) {
  const section = baseTasks.find((task) => task.order === order)!.section
  return makeAttempt({
    state: 'active',
    started_at: '2026-08-29T00:00:00.000Z',
    section_started_at: new Date().toISOString(),
    section_deadline_at: new Date(Date.now() + 5000).toISOString(),
    current_section: section,
    current_order: order,
    current_task: currentTaskFor(order),
    tasks: makeTasks(order),
    ...overrides,
  })
}

export const listeningSession = {
  id: listeningSessionId,
  mode: 'mock',
  state: 'active',
  started_at: '2026-08-29T00:00:00.000Z',
  deadline_at: new Date(Date.now() + 5000).toISOString(),
  submitted_at: null,
  server_now: new Date().toISOString(),
  is_guest: false,
  content: {
    slug: 'e2e-listening-set',
    title: 'A Quick Workplace Decision',
    topic: 'Workplace',
    difficulty: 1,
    estimated_level: 5,
    task_type: 'listening_problem_solving',
    skill: 'listening',
    instructions: 'Listen once, then answer.',
    stimulus: { type: 'audio_context', introduction: 'Two coworkers discuss a decision.' },
    questions: [
      {
        id: 900,
        order: 1,
        stem: 'What are they deciding?',
        skill_focus: 'gist',
        choices: [
          { id: 9000, order: 1, text: 'Which supplier to use' },
          { id: 9001, order: 2, text: 'When to take a break' },
        ],
      },
    ],
  },
  audio: {
    asset_id: 501,
    duration_ms: 4000,
    playback_policy: 'one_play',
    voice_label: 'Synthetic Canadian-English development voice',
  },
  responses: [],
  mock: {
    attempt_id: attemptId,
    task_order: 1,
    section: 'listening',
    results_released: false,
    return_url: `/mock/${attemptId}`,
  },
}

export const readingSession = {
  id: readingSessionId,
  mode: 'mock',
  state: 'active',
  started_at: '2026-08-29T00:00:00.000Z',
  deadline_at: new Date(Date.now() + 5000).toISOString(),
  submitted_at: null,
  server_now: new Date().toISOString(),
  is_guest: false,
  content: {
    slug: 'e2e-reading-set',
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
      body: 'Please renew your plot by March 31.',
    },
    questions: [
      {
        id: 910,
        order: 1,
        stem: 'When is the deadline?',
        skill_focus: 'detail',
        choices: [
          { id: 9100, order: 1, text: 'March 31' },
          { id: 9101, order: 2, text: 'April 5' },
        ],
      },
    ],
  },
  responses: [],
  mock: {
    attempt_id: attemptId,
    task_order: 2,
    section: 'reading',
    results_released: false,
    return_url: `/mock/${attemptId}`,
  },
}

export const writingSession = {
  id: writingSessionId,
  mode: 'mock',
  state: 'active',
  started_at: '2026-08-29T00:00:00.000Z',
  deadline_at: new Date(Date.now() + 5000).toISOString(),
  submitted_at: null,
  server_now: new Date().toISOString(),
  is_guest: false,
  content: {
    slug: 'e2e-writing-email',
    title: 'Write an Email',
    topic: 'Neighbourhood',
    difficulty: 1,
    estimated_level: 6,
    task_type: 'writing_email',
    skill: 'writing',
    instructions: 'Write an email responding to the scenario.',
    stimulus: {
      type: 'writing_prompt',
      task_kind: 'email',
      scenario: 'Your neighbour asked to borrow your ladder for a weekend project.',
      requested_points: ['Say whether you can lend the ladder', 'Mention when they should return it'],
      target_words: { min: 5, max: 200 },
    },
  },
  rubric: { dimensions: [] },
  submission: null,
  mock: {
    attempt_id: attemptId,
    task_order: 3,
    section: 'writing',
    results_released: false,
    return_url: `/mock/${attemptId}`,
  },
}

export const speakingSession = {
  id: speakingSessionId,
  mode: 'mock',
  state: 'active',
  started_at: '2026-08-29T00:00:00.000Z',
  deadline_at: new Date(Date.now() + 5000).toISOString(),
  submitted_at: null,
  server_now: new Date().toISOString(),
  is_guest: false,
  content: {
    slug: 'e2e-speaking-advice',
    title: 'Giving Advice',
    topic: 'Everyday advice',
    difficulty: 1,
    estimated_level: 6,
    task_type: 'speaking_advice',
    skill: 'speaking',
    instructions: 'Prepare, then respond.',
    stimulus: {
      type: 'speaking_prompt',
      task_kind: 'advice',
      scenario: 'A friend is deciding between two apartments.',
      prompt: 'Give your friend advice about which apartment to choose.',
      prep_seconds: 3,
      response_seconds: 5,
    },
  },
  submission: null,
  attempt: { attempt_number: 1 },
  mock: {
    attempt_id: attemptId,
    task_order: 4,
    section: 'speaking',
    results_released: false,
    return_url: `/mock/${attemptId}`,
  },
}

export const mockResults = {
  attempt_id: attemptId,
  completed_at: new Date().toISOString(),
  components: [
    { skill: 'listening', measure: 'practice_accuracy', raw_correct: 1, raw_possible: 1, accuracy_percent: 100, items_attempted: 1, items_scored: 1, tasks_unanswered: 0, time_used_seconds: 3 },
    { skill: 'reading', measure: 'practice_accuracy', raw_correct: 1, raw_possible: 1, accuracy_percent: 100, items_attempted: 1, items_scored: 1, tasks_unanswered: 0, time_used_seconds: 3 },
    { skill: 'writing', measure: 'ai_assisted_practice_estimate', feedback_ready: 0, tasks_total: 1, estimate_low: null, estimate_high: null, tasks_unanswered: 0, time_used_seconds: 3 },
    { skill: 'speaking', measure: 'ai_assisted_practice_estimate', feedback_ready: 0, tasks_total: 1, estimate_low: null, estimate_high: null, tasks_unanswered: 0, time_used_seconds: 3 },
  ],
  overall_score: null,
  time_used_seconds_total: 12,
  tasks_unanswered_total: 0,
  strongest_skill: 'listening',
  needs_attention_skill: 'writing',
  recommended_next_steps: [
    { skill: 'writing', reason: 'Writing had this attempt’s lowest practice signal.', destination: '/practice/writing' },
  ],
  disclaimer: 'Unofficial practice results only. Immigration decisions use official component results.',
}
