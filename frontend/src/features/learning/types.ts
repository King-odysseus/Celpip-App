export type Skill = 'listening' | 'reading' | 'writing' | 'speaking'

export type Progress = {
  skills: Array<{
    skill: Skill
    attempts: number
    questions_correct: number
    questions_total: number
    accuracy_percent: number | null
    estimate_low: number | null
    estimate_high: number | null
    target: number
    last_activity: string | null
  }>
  task_types: Array<{
    task_type: string
    skill: Skill
    title: string
    correct: number
    total: number
    accuracy_percent: number
  }>
  trends: Array<{ date: string; skill: Skill; metric: string; value: number; label: string }>
  coverage: { practised_skills: number; total_skills: number }
  overall_readiness: null
  readiness_explanation: string
  disclaimer: string
}

export type Mistake = {
  id: number
  skill: Skill
  task_type: string
  task_title: string
  stem: string
  selected: string
  correct: string
  explanation: string
  occurrences: number
  state: 'open' | 'resolved'
  first_seen_at: string
  last_seen_at: string
  resolved_at: string | null
}

export type StudyTask = {
  id: number
  scheduled_date: string
  order: number
  skill: Skill
  task_type: string
  title: string
  minutes: number
  reason: string
  destination: string
  state: 'pending' | 'completed' | 'skipped'
  completed_at: string | null
}

export type StudyPlan = {
  id: number
  version: number
  generated_at: string
  reason_summary: { priorities: Record<Skill, number>; rule: string; source_attempts: number }
  tasks: StudyTask[]
}
