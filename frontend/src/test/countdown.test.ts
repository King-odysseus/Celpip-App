import { describe, expect, it } from 'vitest'
import { countdownLabel, daysUntilExam } from '../lib/countdown'

describe('daysUntilExam', () => {
  it('counts whole days until the exam', () => {
    const now = new Date('2026-10-01T12:00:00Z')
    expect(daysUntilExam('2026-10-10', 'America/Toronto', now)).toBe(9)
  })

  it('is 0 on exam day', () => {
    const now = new Date('2026-10-10T15:00:00Z')
    expect(daysUntilExam('2026-10-10', 'UTC', now)).toBe(0)
  })

  it('respects the learner timezone at day boundaries', () => {
    // 02:00 UTC is still the previous evening in Toronto (UTC-4/-5).
    const now = new Date('2026-10-10T02:00:00Z')
    expect(daysUntilExam('2026-10-10', 'America/Toronto', now)).toBe(1)
    expect(daysUntilExam('2026-10-10', 'UTC', now)).toBe(0)
  })

  it('goes negative after the exam', () => {
    const now = new Date('2026-10-12T12:00:00Z')
    expect(daysUntilExam('2026-10-10', 'UTC', now)).toBe(-2)
  })

  it('returns null for missing or malformed dates', () => {
    expect(daysUntilExam(null, 'UTC')).toBeNull()
    expect(daysUntilExam('not-a-date', 'UTC')).toBeNull()
  })
})

describe('countdownLabel', () => {
  it('formats the common cases', () => {
    expect(countdownLabel(9)).toBe('9 days to go')
    expect(countdownLabel(1)).toBe('Tomorrow')
    expect(countdownLabel(0)).toBe('Exam day')
    expect(countdownLabel(-1)).toBe('1 day ago')
    expect(countdownLabel(-3)).toBe('3 days ago')
    expect(countdownLabel(null)).toBe('No exam date set')
  })
})
