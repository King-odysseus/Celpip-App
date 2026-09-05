import { api } from '../../lib/api'
import type { MockAttempt, MockListResponse, MockResults } from './types'

export function listMocks(): Promise<MockListResponse> {
  return api.get<MockListResponse>('/mocks/')
}

export type CompactFocus = {
  mode: 'balanced' | 'recommended' | 'custom'
  skills?: string[]
  task_types?: string[]
}

export function createMock(scope?: string, focus?: CompactFocus, scheduledFor?: string): Promise<MockAttempt> {
  return api.post<MockAttempt>('/mocks/', scope ? { scope, ...(focus ? {
    focus_mode: focus.mode,
    skills: focus.skills,
    task_types: focus.task_types,
  } : {}), ...(scheduledFor ? { scheduled_for: scheduledFor } : {}) } : undefined)
}

export function getMock(attemptId: string): Promise<MockAttempt> {
  return api.get<MockAttempt>(`/mocks/${attemptId}/`)
}

export function updateMockSchedule(attemptId: string, scheduledFor: string | null): Promise<MockAttempt> {
  return api.patch<MockAttempt>(`/mocks/${attemptId}/`, { scheduled_for: scheduledFor })
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
