import {
  BookOpen,
  Headphones,
  Mic2,
  PenLine,
  Sparkles,
  type LucideIcon,
} from 'lucide-react'
import type { Skill } from '../auth/types'

export type CoachSkill = 'general' | Skill

export type CoachMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  skill: CoachSkill
  created_at: string
}

export type CoachThread = { messages: CoachMessage[] }
export type CoachReply = { user_message: CoachMessage; coach_message: CoachMessage }

export const COACH_SKILLS: Array<{ value: CoachSkill; label: string; icon: LucideIcon }> = [
  { value: 'general', label: 'All skills', icon: Sparkles },
  { value: 'listening', label: 'Listening', icon: Headphones },
  { value: 'reading', label: 'Reading', icon: BookOpen },
  { value: 'writing', label: 'Writing', icon: PenLine },
  { value: 'speaking', label: 'Speaking', icon: Mic2 },
]

export const STARTERS: Record<CoachSkill, string[]> = {
  general: [
    'What should I focus on to improve my overall score?',
    'How should I review a practice attempt so it actually helps?',
    'What is a realistic weekly practice routine for 30 minutes a day?',
  ],
  listening: [
    'How can I keep up with fast conversations?',
    'What should I write down while listening?',
    'How do I handle a question when I miss one detail?',
  ],
  reading: [
    'How can I find the right evidence faster?',
    'What should I do when two answer choices look correct?',
    'How can I manage the reading time limit?',
  ],
  writing: [
    'How should I structure a CELPIP email?',
    'How can I make my survey response more specific?',
    'How do I improve vocabulary without sounding unnatural?',
  ],
  speaking: [
    'How can I speak for the full response time?',
    'What structure works for a difficult-situation task?',
    'How can I reduce long pauses?',
  ],
}

export function isCoachSkill(value: string | null | undefined): value is CoachSkill {
  return COACH_SKILLS.some((option) => option.value === value)
}
