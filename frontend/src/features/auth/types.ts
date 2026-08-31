/** Shapes returned by the account API. */

export type AuthUser = {
  id: number
  identifier: string
  email: string
  date_joined: string
}

/** Presentation preference for generated single-narrator practice narration. */
export const NARRATION_VOICES = ['automatic', 'voice_1', 'voice_2'] as const
export type PracticeNarrationVoice = (typeof NARRATION_VOICES)[number]

export type LearnerProfile = {
  identifier: string
  exam_date: string | null
  target_level: number
  target_listening: number | null
  target_reading: number | null
  target_writing: number | null
  target_speaking: number | null
  daily_minutes: number
  mock_interval_days?: number
  preferred_weekdays: number[]
  timezone: string
  practice_narration_voice: PracticeNarrationVoice
  updated_at: string
}

export type ProfileUpdate = Partial<
  Omit<LearnerProfile, 'identifier' | 'updated_at'>
>

export const SKILLS = ['listening', 'reading', 'writing', 'speaking'] as const
export type Skill = (typeof SKILLS)[number]
