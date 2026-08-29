import { api } from '../../lib/api'
import type { MockAttempt, MockListResponse, MockResults } from './types'

export function listMocks(): Promise<MockListResponse> {
  return api.get<MockListResponse>('/mocks/')
}

export function createMock(): Promise<MockAttempt> {
  return api.post<MockAttempt>('/mocks/')
}

export function getMock(attemptId: string): Promise<MockAttempt> {
  return api.get<MockAttempt>(`/mocks/${attemptId}/`)
}

export function startMock(attemptId: string): Promise<MockAttempt> {
  return api.post<MockAttempt>(`/mocks/${attemptId}/start/`)
}

/**
 * Advance a mock to the task after the one just submitted. The server treats a
 * repeat of an already-advanced order as an idempotent replay, so callers can
 * safely retry on transient failures.
 */
export function advanceMock(attemptId: string, expectedOrder: number): Promise<MockAttempt> {
  return api.post<MockAttempt>(`/mocks/${attemptId}/advance/`, { expected_order: expectedOrder })
}

export function getMockResults(attemptId: string): Promise<MockResults> {
  return api.get<MockResults>(`/mocks/${attemptId}/results/`)
}
