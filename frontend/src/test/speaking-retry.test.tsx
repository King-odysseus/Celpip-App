import { act, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'

const attempt1Id = '11111111-1111-4111-8111-111111111111'
const attempt2Id = '22222222-2222-4222-8222-222222222222'

const rubric = {
  dimensions: [
    { key: 'content_coherence', label: 'Content/Coherence', prompt: 'Are your ideas connected?' },
    { key: 'vocabulary', label: 'Vocabulary', prompt: 'Is your word choice varied?' },
    { key: 'listenability', label: 'Listenability', prompt: 'Easy to follow?' },
    { key: 'task_fulfillment', label: 'Task Fulfillment', prompt: 'Did you complete the task?' },
  ],
  note: 'Use the four official Speaking dimensions to review your response.',
}

const recording = {
  mime_type: 'audio/webm',
  container: 'webm',
  byte_size: 8,
  duration_ms: 1400,
  revision: 1,
  saved_at: '2026-08-29T08:00:00Z',
  submitted_at: '2026-08-29T08:02:00Z',
  audio_url: `/api/v1/sessions/${attempt1Id}/speaking/audio/`,
}

const review = {
  duration_ms: recording.duration_ms,
  byte_size: recording.byte_size,
  score_label: 'Guided speaking self-review',
  rubric,
  estimated_level: null,
  transcript: null,
  disclaimer: 'This is practice self-review, not an official CELPIP score or level.',
}

const comparisonDisclaimer =
  'This is an AI-assisted practice comparison, not an official CELPIP score. ' +
  'A midpoint change is not an official score difference.'

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: attempt1Id,
    mode: 'practice',
    state: 'active',
    started_at: '2026-08-29T08:00:00Z',
    deadline_at: null,
    submitted_at: null,
    server_now: '2026-08-29T08:00:00Z',
    is_guest: true,
    content: {
      slug: 'advice-community-course',
      title: 'Choosing a Community Course',
      topic: 'Community learning',
      difficulty: 1,
      estimated_level: 6,
      task_type: 'speaking_advice',
      skill: 'speaking',
      instructions: 'Prepare, then record one complete response.',
      stimulus: {
        type: 'speaking_prompt',
        task_kind: 'advice',
        scenario: 'Your friend wants to learn a useful skill after work.',
        prompt: 'Advise your friend which community course to choose.',
        prep_seconds: 0,
        response_seconds: 60,
      },
      questions: [],
    },
    rubric,
    submission: null,
    attempt: { attempt_number: 1 },
    ...overrides,
  }
}

function submittedAttempt1(overrides: Record<string, unknown> = {}) {
  return {
    ...makeSession(),
    state: 'submitted',
    submitted_at: '2026-08-29T08:02:00Z',
    submission: recording,
    review,
    ...overrides,
  }
}

function submittedAttempt2() {
  return {
    ...makeSession(),
    id: attempt2Id,
    state: 'submitted',
    submitted_at: '2026-08-29T08:12:00Z',
    submission: { ...recording, audio_url: `/api/v1/sessions/${attempt2Id}/speaking/audio/` },
    review,
    attempt: { attempt_number: 2, source_id: attempt1Id },
  }
}

function pendingComparison() {
  return {
    status: 'pending',
    attempts: {
      '1': { session_id: attempt1Id, attempt_number: 1, feedback_status: 'pending', job_status: 'queued' },
      '2': { session_id: attempt2Id, attempt_number: 2, feedback_status: 'pending', job_status: 'running' },
    },
    disclaimer: comparisonDisclaimer,
  }
}

function failedComparison() {
  return {
    status: 'failed',
    attempts: {
      '1': { session_id: attempt1Id, attempt_number: 1, feedback_status: 'ready' },
      '2': {
        session_id: attempt2Id,
        attempt_number: 2,
        feedback_status: 'failed',
        job_status: 'failed',
        error_code: 'evaluation_failed',
        error: 'AI-assisted feedback could not be completed for this attempt.',
      },
    },
    disclaimer: comparisonDisclaimer,
  }
}

function readyComparison(overrides: Record<string, unknown> = {}) {
  return {
    status: 'ready',
    attempts: {
      '1': { session_id: attempt1Id, attempt_number: 1, feedback_status: 'ready' },
      '2': { session_id: attempt2Id, attempt_number: 2, feedback_status: 'ready' },
    },
    disclaimer: comparisonDisclaimer,
    attempt_1: {
      session_id: attempt1Id,
      attempt_number: 1,
      estimated_range: { low: 6, high: 7 },
      estimated_midpoint: 6.5,
      audit: { provider: 'fake', model: 'fake-v1', prompt_version: 'v1' },
    },
    attempt_2: {
      session_id: attempt2Id,
      attempt_number: 2,
      estimated_range: { low: 7, high: 8 },
      estimated_midpoint: 7.5,
      audit: { provider: 'fake', model: 'fake-v1', prompt_version: 'v1' },
    },
    midpoint_delta: 1.0,
    dimension_deltas: [
      { key: 'content_coherence', label: 'Content/Coherence', rating_1: 3, rating_2: 4, delta: 1 },
      { key: 'vocabulary', label: 'Vocabulary', rating_1: 3, rating_2: 3, delta: 0 },
      { key: 'delivery', label: 'Listenability', rating_1: 2, rating_2: 2, delta: 0 },
      { key: 'task_fulfillment', label: 'Task Fulfillment', rating_1: 3, rating_2: 1, delta: -2 },
    ],
    improvements: [
      { kind: 'dimension', label: 'Content/Coherence', evidence: 'Added a clear example.' },
      { kind: 'strength', text: 'A confident opening.' },
    ],
    remaining_priorities: ['Support each suggestion with a reason.'],
    ...overrides,
  }
}

function submittedAttempt1Routes(extra: Record<string, (init: RequestInit) => Response | Promise<Response>> = {}) {
  return {
    [`GET /sessions/${attempt1Id}/speaking/`]: () => jsonResponse(submittedAttempt1()),
    [`GET /sessions/${attempt1Id}/speaking/audio/`]: () =>
      new Response('a', { headers: { 'Content-Type': 'audio/webm' } }),
    [`GET /sessions/${attempt1Id}/ai-feedback/`]: () => jsonResponse({ status: 'failed' }),
    ...extra,
  }
}

function submittedAttempt2Routes(comparison: unknown) {
  return {
    [`GET /sessions/${attempt2Id}/speaking/`]: () => jsonResponse(submittedAttempt2()),
    [`GET /sessions/${attempt2Id}/speaking/audio/`]: () =>
      new Response('a', { headers: { 'Content-Type': 'audio/webm' } }),
    [`GET /sessions/${attempt2Id}/ai-feedback/`]: () => jsonResponse({ status: 'failed' }),
    [`GET /sessions/${attempt2Id}/speaking/comparison/`]: () => jsonResponse(comparison),
  }
}

async function renderReadyComparison(midpointDelta: number) {
  installRouteFetch(submittedAttempt2Routes(readyComparison({ midpoint_delta: midpointDelta })))
  renderApp(`/speaking/session/${attempt2Id}`)
  return screen.findByRole('region', { name: 'Speaking comparison' })
}

describe('Speaking retry', () => {
  it('starts a second attempt, transfers the guest token, and navigates', async () => {
    const user = userEvent.setup()
    const retryId = '33333333-3333-4333-8333-333333333333'
    sessionStorage.setItem(`celpip-guest-${attempt1Id}`, 'guest-speaking')
    const fetchSpy = installRouteFetch(
      submittedAttempt1Routes({
        [`POST /sessions/${attempt1Id}/speaking/retry/`]: () =>
          jsonResponse(
            { id: retryId, attempt_number: 2, replayed: false, launch_url: `/speaking/session/${retryId}` },
            201,
          ),
        [`GET /sessions/${retryId}/speaking/`]: () =>
          jsonResponse(makeSession({ id: retryId, attempt: { attempt_number: 2, source_id: attempt1Id } })),
      }),
    )
    const { router } = renderApp(`/speaking/session/${attempt1Id}`)

    await user.click(await screen.findByRole('button', { name: /try this task again/i }))

    await waitFor(() => expect(router.state.location.pathname).toBe(`/speaking/session/${retryId}`))
    const retryCall = fetchSpy.mock.calls.find(
      ([url, init]) => String(url).endsWith('/speaking/retry/') && init?.method === 'POST',
    )
    const headers = retryCall?.[1]?.headers as Record<string, string> | undefined
    expect(headers?.['X-Guest-Token']).toBe('guest-speaking')
    expect(sessionStorage.getItem(`celpip-guest-${retryId}`)).toBe('guest-speaking')
  })

  it('posts a retry without a guest token for an authenticated session', async () => {
    const user = userEvent.setup()
    const retryId = '44444444-4444-4444-8444-444444444444'
    const fetchSpy = installRouteFetch({
      ...submittedAttempt1Routes({}),
      [`GET /sessions/${attempt1Id}/speaking/`]: () => jsonResponse(submittedAttempt1({ is_guest: false })),
      [`POST /sessions/${attempt1Id}/speaking/retry/`]: () =>
        jsonResponse(
          { id: retryId, attempt_number: 2, replayed: false, launch_url: `/speaking/session/${retryId}` },
          201,
        ),
      [`GET /sessions/${retryId}/speaking/`]: () =>
        jsonResponse(makeSession({ id: retryId, is_guest: false, attempt: { attempt_number: 2, source_id: attempt1Id } })),
    })
    const { router } = renderApp(`/speaking/session/${attempt1Id}`)

    await user.click(await screen.findByRole('button', { name: /try this task again/i }))

    await waitFor(() => expect(router.state.location.pathname).toBe(`/speaking/session/${retryId}`))
    const retryCall = fetchSpy.mock.calls.find(
      ([url, init]) => String(url).endsWith('/speaking/retry/') && init?.method === 'POST',
    )
    const headers = retryCall?.[1]?.headers as Record<string, string> | undefined
    expect(headers?.['X-Guest-Token']).toBeUndefined()
    expect(sessionStorage.getItem(`celpip-guest-${retryId}`)).toBeNull()
  })

  it('disables the retry button while in flight and surfaces the backend error', async () => {
    const user = userEvent.setup()
    let resolveRetry: (response: Response) => void = () => {}
    const retryPromise = new Promise<Response>((resolve) => {
      resolveRetry = resolve
    })
    installRouteFetch(
      submittedAttempt1Routes({
        [`POST /sessions/${attempt1Id}/speaking/retry/`]: () => retryPromise,
      }),
    )
    renderApp(`/speaking/session/${attempt1Id}`)

    const button = await screen.findByRole('button', { name: /try this task again/i })
    await user.click(button)
    expect(button).toBeDisabled()

    await act(async () => {
      resolveRetry(errorResponse('session_not_active', 409, 'Only a submitted speaking session can be retried.'))
    })
    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Only a submitted speaking session can be retried.',
    )
    expect(button).toBeEnabled()
  })
})

describe('Speaking attempt labels and preservation', () => {
  it('labels the active session header with Attempt 2', async () => {
    installRouteFetch({
      [`GET /sessions/${attempt2Id}/speaking/`]: () =>
        jsonResponse(makeSession({ id: attempt2Id, attempt: { attempt_number: 2, source_id: attempt1Id } })),
    })
    renderApp(`/speaking/session/${attempt2Id}`)

    expect(await screen.findByText('Attempt 2')).toBeInTheDocument()
  })

  it('labels the first attempt review and does not offer a retry on Attempt 2', async () => {
    installRouteFetch(submittedAttempt1Routes({}))
    renderApp(`/speaking/session/${attempt1Id}`)

    expect(await screen.findByRole('heading', { name: 'Guided self-review' })).toBeInTheDocument()
    expect(screen.getByText('Attempt 1')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /try this task again/i })).toBeInTheDocument()
  })

  it('tells the learner Attempt 1 is preserved and links back to it via source_id', async () => {
    installRouteFetch(submittedAttempt2Routes(failedComparison()))
    renderApp(`/speaking/session/${attempt2Id}`)

    expect(await screen.findByText(/Attempt 1 is preserved/i)).toBeInTheDocument()
    const link = screen.getByRole('link', { name: 'Open Attempt 1 review' })
    expect(link).toHaveAttribute('href', `/speaking/session/${attempt1Id}`)
  })

  it('relabels the active draft action and explains it does not create Attempt 2', async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }) },
    })
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: vi.fn(() => 'blob:draft') })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: vi.fn() })
    class Recorder {
      static isTypeSupported() { return true }
      state = 'inactive'
      mimeType: string
      ondataavailable: ((event: { data: Blob }) => void) | null = null
      onstop: (() => void) | null = null
      onerror: (() => void) | null = null
      constructor(_stream: unknown, options: { mimeType: string }) { this.mimeType = options.mimeType }
      start() { this.state = 'recording' }
      stop() {
        this.state = 'inactive'
        this.ondataavailable?.({ data: new Blob(['webm-audio'], { type: this.mimeType }) })
        this.onstop?.()
      }
    }
    vi.stubGlobal('MediaRecorder', Recorder)
    installRouteFetch({
      [`GET /sessions/${attempt1Id}/speaking/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${attempt1Id}/speaking/`]: () => jsonResponse({ ...recording, replayed: false }),
    })
    renderApp(`/speaking/session/${attempt1Id}`)

    await user.click(await screen.findByRole('button', { name: /allow microphone/i }))
    await user.click(await screen.findByRole('button', { name: 'Stop early' }))

    expect(await screen.findByRole('button', { name: 'Replace draft' })).toBeInTheDocument()
    expect(screen.getByText(/does not start\s+Attempt 2/i)).toBeInTheDocument()
  })

  it('never shows retry or comparison for a mock speaking session', async () => {
    installRouteFetch({
      [`GET /sessions/${attempt1Id}/speaking/`]: () =>
        jsonResponse(
          submittedAttempt1({
            mode: 'mock',
            mock: {
              attempt_id: 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
              task_order: 1,
              section: 'speaking',
              results_released: true,
              return_url: '/mock/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa',
            },
          }),
        ),
      [`GET /sessions/${attempt1Id}/speaking/audio/`]: () =>
        new Response('a', { headers: { 'Content-Type': 'audio/webm' } }),
      [`GET /sessions/${attempt1Id}/ai-feedback/`]: () => jsonResponse({ status: 'failed' }),
    })
    renderApp(`/speaking/session/${attempt1Id}`)

    expect(await screen.findByRole('heading', { name: 'Guided self-review' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /try this task again/i })).not.toBeInTheDocument()
    expect(screen.queryByText(/comparing your two attempts/i)).not.toBeInTheDocument()
  })
})

describe('Speaking comparison', () => {
  it('polls while pending, naming both evaluation states', async () => {
    vi.useFakeTimers()
    try {
      let polls = 0
      installRouteFetch({
        ...submittedAttempt2Routes(pendingComparison()),
        [`GET /sessions/${attempt2Id}/speaking/comparison/`]: () => {
          polls += 1
          return jsonResponse(polls >= 2 ? readyComparison() : pendingComparison())
        },
      })
      renderApp(`/speaking/session/${attempt2Id}`)

      await act(async () => {
        await vi.advanceTimersByTimeAsync(0)
      })
      expect(screen.getByRole('heading', { name: 'Comparing your two attempts' })).toBeInTheDocument()
      expect(screen.getByText('Queued for evaluation')).toBeInTheDocument()
      expect(screen.getByText('Being evaluated')).toBeInTheDocument()

      await act(async () => {
        await vi.advanceTimersByTimeAsync(3000)
      })
      expect(screen.getByRole('region', { name: 'Speaking comparison' })).toBeInTheDocument()
      expect(polls).toBeGreaterThanOrEqual(2)
    } finally {
      vi.useRealTimers()
    }
  })

  it('shows generic backend messages and codes when the comparison fails', async () => {
    installRouteFetch(submittedAttempt2Routes(failedComparison()))
    renderApp(`/speaking/session/${attempt2Id}`)

    expect(await screen.findByRole('heading', { name: 'Comparison unavailable' })).toBeInTheDocument()
    const alert = screen.getByRole('alert')
    expect(alert).toHaveTextContent('Attempt 2')
    expect(alert).toHaveTextContent('AI-assisted feedback could not be completed for this attempt.')
    expect(alert).toHaveTextContent('code evaluation_failed')
  })

  it('renders an accessible unavailable state for a malformed ready payload', async () => {
    installRouteFetch(
      submittedAttempt2Routes(
        readyComparison({ attempt_1: undefined, attempt_2: undefined }),
      ),
    )
    renderApp(`/speaking/session/${attempt2Id}`)

    expect(await screen.findByRole('heading', { name: 'Comparison unavailable' })).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent('The two attempts could not be compared.')
    expect(screen.queryByRole('region', { name: 'Speaking comparison' })).not.toBeInTheDocument()
  })

  it('shows "Increased" with a signed positive midpoint change', async () => {
    const region = await renderReadyComparison(1)
    const group = within(region).getByRole('group', { name: 'Estimated midpoint change result' })
    expect(within(group).getByText('Increased')).toBeInTheDocument()
    expect(within(group).getByText('+1')).toBeInTheDocument()
    expect(within(region).getByText('A midpoint change is not an official score difference.')).toBeInTheDocument()
  })

  it('shows "No change" with a zero midpoint change', async () => {
    const region = await renderReadyComparison(0)
    const group = within(region).getByRole('group', { name: 'Estimated midpoint change result' })
    expect(within(group).getByText('No change')).toBeInTheDocument()
    expect(within(group).getByText('0')).toBeInTheDocument()
  })

  it('shows "Decreased" with a signed negative midpoint change', async () => {
    const region = await renderReadyComparison(-1)
    const group = within(region).getByRole('group', { name: 'Estimated midpoint change result' })
    expect(within(group).getByText('Decreased')).toBeInTheDocument()
    expect(within(group).getByText('-1')).toBeInTheDocument()
  })

  it('lists dimension ratings with worded deltas, improvements, and empty states', async () => {
    installRouteFetch(submittedAttempt2Routes(readyComparison()))
    renderApp(`/speaking/session/${attempt2Id}`)

    const region = await screen.findByRole('region', { name: 'Speaking comparison' })
    expect(within(region).getByText('6–7')).toBeInTheDocument()
    expect(within(region).getByText('7–8')).toBeInTheDocument()
    expect(within(region).getByText('Increased (+1)')).toBeInTheDocument()
    expect(within(region).getAllByText('No change (0)').length).toBe(2)
    expect(within(region).getByText('Decreased (-2)')).toBeInTheDocument()
    expect(within(region).getByText(/Added a clear example/)).toBeInTheDocument()
    expect(within(region).getByText(/A confident opening/)).toBeInTheDocument()
    expect(within(region).getByText(/Support each suggestion with a reason/)).toBeInTheDocument()
  })

  it('shows honest empty states for improvements and priorities', async () => {
    installRouteFetch(
      submittedAttempt2Routes(readyComparison({ improvements: [], remaining_priorities: [] })),
    )
    renderApp(`/speaking/session/${attempt2Id}`)

    const region = await screen.findByRole('region', { name: 'Speaking comparison' })
    expect(within(region).getByText(/No clear improvements were detected/)).toBeInTheDocument()
    expect(within(region).getByText(/No remaining priorities were identified/)).toBeInTheDocument()
  })

  it('exposes the audit details and disclaimer without touching raw audio paths', async () => {
    const fetchSpy = installRouteFetch(submittedAttempt2Routes(readyComparison()))
    renderApp(`/speaking/session/${attempt2Id}`)

    const region = await screen.findByRole('region', { name: 'Speaking comparison' })
    expect(within(region).getByText(comparisonDisclaimer)).toBeInTheDocument()
    await userEvent.setup().click(within(region).getByText('Comparison audit details'))
    expect(within(region).getAllByText(/fake-v1/).length).toBe(2)
    expect(within(region).getAllByText(/prompt v1/).length).toBe(2)

    // The comparison panel renders no audio element and never fetches the other
    // attempt's private audio.
    expect(region.querySelectorAll('audio')).toHaveLength(0)
    expect(
      fetchSpy.mock.calls.some(([url]) => String(url).includes(`${attempt1Id}/speaking/audio/`)),
    ).toBe(false)
  })
})
