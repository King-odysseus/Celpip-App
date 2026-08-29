import type { Paginated, SessionMode } from '../reading/types'

export type { Paginated, SessionMode }

export type WritingTaskType = {
  code: string
  skill: 'writing'
  title: string
  part_number: number
  description: string
  strategy: string[]
  common_mistakes: string[]
}

export type WritingCatalogItem = {
  id: number
  slug: string
  version: number
  title: string
  topic: string
  difficulty: 1 | 2 | 3
  estimated_level: number
  task_type: string
}

export type TargetWords = { min: number; max: number }

export type SurveyOption = { key: string; label: string }

/** Structured prompt data frozen into the session snapshot at start time. */
export type WritingStimulus = {
  type: string
  task_kind: 'email' | 'survey'
  scenario: string
  audience?: string
  requested_points: string[]
  target_words: TargetWords
  suggested_duration_seconds: number
  guidance?: string[]
  survey_question?: string
  options?: SurveyOption[]
}

export type WritingContent = {
  slug: string
  title: string
  topic: string
  difficulty: 1 | 2 | 3
  estimated_level: number
  task_type: string
  skill: 'writing'
  instructions: string
  stimulus: WritingStimulus
  learning_notes?: string
  questions: never[]
}

export type WritingSubmissionDraft = {
  text: string
  word_count: number
  revision: number
  saved_at: string
  submitted_at: string | null
}

export type RubricDimension = { key: string; label: string; prompt: string }

export type WritingReview = {
  word_count: number
  target_words: TargetWords
  within_target: boolean | null
  score_label: string
  rubric: { dimensions: RubricDimension[]; note: string }
  estimated_level: null
  disclaimer: string
}

export type WritingSession = {
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
  content: WritingContent
  rubric: { dimensions: RubricDimension[] }
  submission: WritingSubmissionDraft | null
  review?: WritingReview
}

export type WritingSaveResult = WritingSubmissionDraft & { replayed: boolean }

export type WritingSubmitResult = WritingReview & {
  session_id: string
  state: 'submitted'
  submission: WritingSubmissionDraft
  replayed: boolean
}

/** The lightweight session payload returned by POST /sessions/ at start. */
export type StartedWritingSession = { id: string; guest_token?: string }
