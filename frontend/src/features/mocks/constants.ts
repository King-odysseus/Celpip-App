import type { Skill } from './types'

/**
 * Public CELPIP-General structure (source: celpip.ca). Kept here as an honest
 * frontend display of the official component order and time boxes — it does not
 * drive timing, which always comes from the attempt snapshot.
 */
export const OFFICIAL_SOURCE_URL = 'https://www.celpip.ca/take-celpip/test-format/'

export const COMPONENT_ORDER: Skill[] = ['listening', 'reading', 'writing', 'speaking']

export const COMPONENT_META: Record<Skill, { label: string; timingLabel: string }> = {
  listening: { label: 'Listening', timingLabel: '46–55 minutes' },
  reading: { label: 'Reading', timingLabel: '43–56 minutes' },
  writing: { label: 'Writing', timingLabel: '53 minutes' },
  speaking: { label: 'Speaking', timingLabel: '15 minutes' },
}

export const COMPACT_SCOPE = 'compact_task_family_mock'
export const FULL_LENGTH_SCOPE = 'full_length_simulation'

export const COMPACT_SCOPE_LIMITATION =
  'Compact mocks are approximately one-hour focused rehearsals. They use original ' +
  'practice content and are not an official CELPIP score conversion.'

export const FULL_LENGTH_SCOPE_LIMITATION =
  'Full simulation — unofficial. Uses the current official Listening and Reading question ' +
  'counts and all eight Speaking tasks, assembled from original, human-reviewed content in ' +
  'the official section order and official time boxes. It reproduces official test structure ' +
  'only: content, audio, and scoring are original to this project, not an official CELPIP ' +
  'test, and raw practice accuracy is never converted to an official CELPIP score or level.'
