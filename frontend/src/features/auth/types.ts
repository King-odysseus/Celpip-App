/** Shapes returned by the account API. */

export type AuthUser = {
  id: number
  identifier: string
  email: string
  date_joined: string
}

export type LearnerProfile = {
  identifier: string
  exam_date: string | null
  target_level: number
  target_listening: number | null
  target_reading: number | null
  target_writing: number | null
  target_speaking: number | null
  daily_minutes: number
  preferred_weekdays: number[]
  timezone: string
  updated_at: string
}

export type ProfileUpdate = Partial<
  Omit<LearnerProfile, 'identifier' | 'updated_at'>
>

export const SKILLS = ['listening', 'reading', 'writing', 'speaking'] as const
export type Skill = (typeof SKILLS)[number]
