export type ReadingTaskType = {
  code: string
  skill: 'reading' | 'listening'
  title: string
  part_number: number
  description: string
  strategy: string[]
  common_mistakes: string[]
}

export type ReadingCatalogItem = {
  id: number
  slug: string
  version: number
  title: string
  topic: string
  difficulty: 1 | 2 | 3
  estimated_level: number
  task_type: string
}

export type Choice = { id: number; order: number; text: string }
export type Question = {
  id: number
  order: number
  stem: string
  skill_focus: string
  choices: Choice[]
}

export type ReadingContent = ReadingCatalogItem & {
  skill: 'reading' | 'listening'
  instructions: string
  stimulus: Record<string, unknown>
  learning_notes?: string
  questions: Question[]
}

export type SavedResponse = {
  question_id: number
  selected_choice_id: number | null
  revision: number
  saved_at: string
}

export type SessionMode = 'learn' | 'practice'

export type ReadingSession = {
  id: string
  mode: SessionMode
  state: 'active' | 'submitted'
  started_at: string
  deadline_at: string | null
  submitted_at: string | null
  server_now: string
  is_guest: boolean
  guest_token?: string
  guest_expires_at?: string
  content: ReadingContent
  responses: SavedResponse[]
  audio?: {
    asset_id: string
    duration_ms: number
    voice_label: string
    playback_policy: 'one_play' | 'unlimited_learning'
  }
}

export type LearningFeedback = {
  is_correct: boolean
  correct_choice_id: number
  evidence: string
  explanation: string
  selected_choice_explanation: string
  transcript?: string
}

export type SaveResult = SavedResponse & {
  replayed: boolean
  feedback?: LearningFeedback
}

export type QuestionOutcome = {
  question_id: number
  selected_choice_id: number | null
  correct_choice_id: number
  is_correct: boolean
  evidence: string
  explanation: string
  choice_explanations: Record<string, string>
}

export type SessionResult = {
  session_id: string
  raw_correct: number
  raw_possible: number
  accuracy_percent: number
  outcomes: QuestionOutcome[]
  scored_at: string
  score_label: string
  disclaimer: string
  replayed?: boolean
  transcript?: string
}

export type AudioAccess = {
  url: string
  expires_in_seconds: number
  plays_remaining: number | null
}

export type Paginated<T> = {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
