import type {
  MockContext,
  MockSubmitResult,
  Paginated,
  SessionMode,
} from '../reading/types'

export type { MockContext, MockSubmitResult, Paginated, SessionMode }

export type SpeakingTaskType = {
  code: string
  skill: 'speaking'
  title: string
  part_number: number
  description: string
  strategy: string[]
  common_mistakes: string[]
}

export type SpeakingCatalogItem = {
  id: number
  slug: string
  version: number
  title: string
  topic: string
  difficulty: 1 | 2 | 3
  estimated_level: number
  task_type: string
}

export type SpeakingOption = {
  key: string
  label: string
  details?: string[]
}

export type SpeakingStimulus = {
  type: 'speaking_prompt'
  task_kind: string
  scenario: string
  prompt: string
  prep_seconds: number
  response_seconds: number
  prep_stages?: { label: string; seconds: number }[]
  audience?: string
  tone?: string
  image_url?: string
  guidance?: string[]
  initial_options?: SpeakingOption[]
  competing_option?: SpeakingOption
  choices?: string[]
}

export type RubricDimension = { key: string; label: string; prompt: string }

export type SpeakingRecording = {
  mime_type: string
  container: string
  byte_size: number
  duration_ms: number
  revision: number
  saved_at: string
  submitted_at: string | null
  audio_url: string
}

export type SpeakingReview = {
  duration_ms: number
  byte_size: number
  score_label: string
  rubric: { dimensions: RubricDimension[]; note: string }
  estimated_level: null
  transcript: null
  disclaimer: string
}

export type SpeakingSession = {
  id: string
  mode: SessionMode
  state: 'active' | 'submitted'
  started_at: string
  deadline_at: string | null
  submitted_at: string | null
  server_now: string
  is_guest: boolean
  content: {
    slug: string
    title: string
    topic: string
    difficulty: 1 | 2 | 3
    estimated_level: number
    task_type: string
    skill: 'speaking'
    instructions: string
    stimulus: SpeakingStimulus
    learning_notes?: string
    questions: never[]
  }
  rubric: { dimensions: RubricDimension[] }
  submission: SpeakingRecording | null
  review?: SpeakingReview
  mock?: MockContext
}

export type SpeakingSaveResult = SpeakingRecording & { replayed: boolean }
export type SpeakingSubmitResult = SpeakingReview & {
  session_id: string
  state: 'submitted'
  submission: SpeakingRecording
  replayed: boolean
}

/** Normal review or, for mock sessions, the neutral embargoed response. */
export type SpeakingSubmitResponse = SpeakingSubmitResult | MockSubmitResult

export type StartedSpeakingSession = { id: string; guest_token?: string }
