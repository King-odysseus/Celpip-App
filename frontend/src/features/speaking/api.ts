import { api } from '../../lib/api'
import type { SpeakingComparison, SpeakingRetryResult } from './types'

/** Start the single retry for a submitted speaking attempt (idempotent). */
export function createSpeakingRetry(
  sessionId: string,
  headers: Record<string, string>,
): Promise<SpeakingRetryResult> {
  return api.post<SpeakingRetryResult>(
    `/sessions/${sessionId}/speaking/retry/`,
    undefined,
    headers,
  )
}

/** Read the attempt 1 vs attempt 2 comparison; never touches audio paths. */
export function getSpeakingComparison(
  sessionId: string,
  headers: Record<string, string>,
): Promise<SpeakingComparison> {
  return api.get<SpeakingComparison>(
    `/sessions/${sessionId}/speaking/comparison/`,
    headers,
  )
}
