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

export const COMPACT_SCOPE_LIMITATION =
  'This compact task-family mock covers every current CELPIP-General task family and ' +
  'uses official component time boxes. Its original starter bank has fewer objective ' +
  'questions than the live test, so question volume and practice accuracy are not an ' +
  'official test simulation or score conversion.'
