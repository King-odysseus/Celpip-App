/** Payload shapes for the full four-component mock orchestration API. */

export type Skill = 'listening' | 'reading' | 'writing' | 'speaking'

export type MockState = 'ready' | 'active' | 'between_sections' | 'completed' | 'abandoned'

export type MockTaskState = 'pending' | 'current' | 'submitted' | 'skipped'

export type ComponentTiming = {
  public_range_minutes: [number, number]
  mock_seconds: number
}

export type TaskStructureRow = {
  skill: Skill
  task_type: string
  part_number: number
  official_question_or_component_count: number
}

export type MockFormat = {
  code: string
  verified_on: string
  official_source_urls: string[]
  component_order: Skill[]
  component_timings: Record<Skill, ComponentTiming>
  task_structure: TaskStructureRow[]
  scope: string
  limitation: string
}

/** The one task the learner may launch right now, when an attempt is active. */
export type MockCurrentTask = {
  order: number
  section: Skill
  task_type: string
  title: string
  session_id: string
  kind: 'objective' | 'writing' | 'speaking'
  launch_url: string
}

export type MockTask = {
  order: number
  section: Skill
  task_type: string
  title: string
  state: MockTaskState
  session_id: string
  kind: 'objective' | 'writing' | 'speaking'
}

export type MockAttempt = {
  id: string
  state: MockState
  scope: string
  created_at: string
  started_at: string | null
  completed_at: string | null
  scheduled_for?: string | null
  server_now: string
  section_started_at: string | null
  section_deadline_at: string | null
  current_section: Skill | null
  current_order: number
  current_task: MockCurrentTask | null
  progress: { completed: number; total: number }
  format: MockFormat
  disclaimer: string
  briefing?: {
    approach: string
    evidence: string
    target: string
    selection_summary: string
    focus_mode: string
  } | null
  /** Present on detail/create/start/advance responses; absent from the list. */
  tasks?: MockTask[]
  replayed?: boolean
}

export type MockListResponse = {
  count: number
  results: MockAttempt[]
}

export type ObjectiveMockComponent = {
  skill: 'listening' | 'reading'
  measure: 'practice_accuracy'
  raw_correct: number
  raw_possible: number
  accuracy_percent: number | null
  items_attempted: number
  items_scored: number
  tasks_unanswered: number
  time_used_seconds: number | null
}

export type AiEstimatedMockComponent = {
  skill: 'writing' | 'speaking'
  measure: 'ai_assisted_practice_estimate'
  feedback_ready: number
  tasks_total: number
  estimate_low: number | null
  estimate_high: number | null
  tasks_unanswered: number
  time_used_seconds: number | null
}

export type MockComponent = ObjectiveMockComponent | AiEstimatedMockComponent

export type NextStep = {
  skill: Skill
  reason: string
  destination: string
}

export type MockResults = {
  attempt_id: string
  completed_at: string
  components: MockComponent[]
  overall_score: null
  time_used_seconds_total: number | null
  tasks_unanswered_total: number
  strongest_skill: Skill | null
  needs_attention_skill: Skill | null
  recommended_next_steps: NextStep[]
  disclaimer: string
}
