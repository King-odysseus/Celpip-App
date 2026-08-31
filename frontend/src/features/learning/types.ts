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

export type StudyConsistency = {
  streak: {
    days: number
    active_today: boolean
    anchor: 'today' | 'yesterday' | null
  }
  window_days: number
  today: string
  days: Array<{
    date: string
    skills: Record<Skill, boolean>
    completed: boolean
  }>
}

export type StudyPlan = {
  id: number
  version: number
  generated_at: string
  name: string
  reason_summary: { priorities: Record<Skill, number>; rule: string; source_attempts: number; mock_interval_days?: number }
  tasks: StudyTask[]
  consistency: StudyConsistency
}

export type SkillSignal = {
  skill: Skill
  measure: 'accuracy_percent' | 'estimated_midpoint' | null
  value: number | null
  planning_signal: number | null
  attempts: number
  basis: string
}

export type ReadinessComponent = {
  key: string
  label: string
  weight: number
  value: number
  raw: string
  explanation: string
}

export type Readiness = {
  label: string
  indicator: number | null
  state: 'estimated' | 'insufficient_evidence'
  is_official: false
  formula: string
  components: ReadinessComponent[]
  explanation: string
  disclaimer: string
}

export type RecentResult = {
  date: string
  skill: Skill
  task_type: string
  title: string
  measure: 'accuracy_percent' | 'estimated_midpoint'
  value: number
  label: string
  destination: string
}

export type Dashboard = {
  skills: Progress['skills']
  task_types: Progress['task_types']
  trends: Progress['trends']
  coverage: Progress['coverage']
  totals: { objective_questions_completed: number; completed_attempts: number }
  streak: {
    days: number
    active_today: boolean
    anchor: 'today' | 'yesterday' | null
    timezone: string
    rule: string
  }
  recent_results: RecentResult[]
  signals: { strongest: SkillSignal | null; needs_attention: SkillSignal | null; note: string }
  readiness: Readiness
  today: { date: string; timezone: string; tasks: StudyTask[] }
  next_upcoming_task: StudyTask | null
  disclaimer: string
}
