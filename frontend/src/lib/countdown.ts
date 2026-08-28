/**
 * Timezone-aware countdown helpers for the exam date.
 *
 * The exam date is a calendar date (no time). "Days until" is measured between
 * calendar days in the learner's own timezone, so a countdown does not flip a
 * day early or late for learners far from UTC.
 */

/** Return the YYYY-MM-DD calendar date for `instant` in the given IANA zone. */
export function calendarDateInZone(instant: Date, timeZone: string): string {
  try {
    // en-CA formats as YYYY-MM-DD, which sorts and parses cleanly.
    return new Intl.DateTimeFormat('en-CA', {
      timeZone,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(instant)
  } catch {
    // Unknown timezone: fall back to the host's local calendar date.
    return new Intl.DateTimeFormat('en-CA', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
    }).format(instant)
  }
}

function daysFromEpoch(isoDate: string): number {
  const [y, m, d] = isoDate.split('-').map(Number)
  return Math.floor(Date.UTC(y, m - 1, d) / 86_400_000)
}

/**
 * Whole days from "today" (in `timeZone`) until `examDate` (a YYYY-MM-DD string).
 * Returns a positive number before the exam, 0 on exam day, negative after.
 * Returns null when the date is missing or malformed.
 */
export function daysUntilExam(
  examDate: string | null | undefined,
  timeZone: string,
  now: Date = new Date(),
): number | null {
  if (!examDate || !/^\d{4}-\d{2}-\d{2}$/.test(examDate)) return null
  const today = calendarDateInZone(now, timeZone)
  return daysFromEpoch(examDate) - daysFromEpoch(today)
}

/** Human-readable countdown label. */
export function countdownLabel(days: number | null): string {
  if (days === null) return 'No exam date set'
  if (days > 1) return `${days} days to go`
  if (days === 1) return 'Tomorrow'
  if (days === 0) return 'Exam day'
  const past = Math.abs(days)
  return past === 1 ? '1 day ago' : `${past} days ago`
}
