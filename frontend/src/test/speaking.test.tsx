import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'

const sessionId = '55555555-5555-4555-8555-555555555555'

const taskTypes = [{
  code: 'speaking_advice',
  skill: 'speaking',
  title: 'Giving Advice',
  part_number: 1,
  description: 'Give useful advice to someone you know.',
  strategy: ['Acknowledge the situation.', 'Give two practical suggestions.'],
  common_mistakes: ['Listing ideas without explaining them.'],
}]

const catalog = {
  count: 1,
  next: null,
  previous: null,
  results: [{
    id: 1,
    slug: 'advice-community-course',
    version: 1,
    title: 'Choosing a Community Course',
    topic: 'Community learning',
    difficulty: 1,
    estimated_level: 6,
    task_type: 'speaking_advice',
  }],
}

const rubric = {
  dimensions: [
    { key: 'content_coherence', label: 'Content/Coherence', prompt: 'Are your ideas connected?' },
    { key: 'vocabulary', label: 'Vocabulary', prompt: 'Is your word choice varied and precise?' },
    { key: 'listenability', label: 'Listenability', prompt: 'Is the response easy to understand?' },
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
  submitted_at: null,
  audio_url: `/api/v1/sessions/${sessionId}/speaking/audio/`,
}

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: sessionId,
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
        audience: 'A close friend',
        guidance: ['Explain why each suggestion would help.'],
      },
      questions: [],
    },
    rubric,
    submission: null,
    attempt: { attempt_number: 1 },
    ...overrides,
  }
}

describe('Speaking catalog', () => {
  it('shows reviewed prompts, exact timing, and task guidance', async () => {
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/speaking/': () => jsonResponse(catalog),
    })
    renderApp('/learn/speaking')

    expect(await screen.findByRole('heading', { name: 'Choosing a Community Course' })).toBeInTheDocument()
    expect(screen.getAllByText('Task 1: Giving Advice').length).toBeGreaterThan(0)
    expect(screen.getByText(/30 sec prep · 90 sec response/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'Speaking' })).toHaveAttribute('aria-current', 'page')
  })

  it('starts a loose guest session and keeps its private token', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/speaking/': () => jsonResponse(catalog),
      'POST /sessions/': () => jsonResponse({ id: sessionId, guest_token: 'guest-speaking' }, 201),
      [`GET /sessions/${sessionId}/speaking/`]: () => jsonResponse(makeSession()),
    })
    renderApp('/practice/speaking')

    await user.click(await screen.findByRole('button', { name: 'Open microphone practice' }))
    await user.click(await screen.findByRole('button', { name: 'Start practice' }))
    expect(await screen.findByRole('heading', { name: 'Private recorder' })).toBeInTheDocument()
    expect(sessionStorage.getItem(`celpip-guest-${sessionId}`)).toBe('guest-speaking')
  })
})

describe('Speaking recorder', () => {
  it('explains a denied microphone permission without uploading anything', async () => {
    const user = userEvent.setup()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockRejectedValue(new Error('denied')) },
    })
    vi.stubGlobal('MediaRecorder', class {
      static isTypeSupported() { return true }
    })
    installRouteFetch({
      [`GET /sessions/${sessionId}/speaking/`]: () => jsonResponse(makeSession()),
    })
    renderApp(`/speaking/session/${sessionId}`)

    await user.click(await screen.findByRole('button', { name: /allow microphone/i }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Microphone permission was not granted')
  })

  it('records, previews, and privately uploads multipart audio', async () => {
    const user = userEvent.setup()
    const stopTrack = vi.fn()
    Object.defineProperty(navigator, 'mediaDevices', {
      configurable: true,
      value: { getUserMedia: vi.fn().mockResolvedValue({ getTracks: () => [{ stop: stopTrack }] }) },
    })
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:local-speaking'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    })
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
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-speaking')
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${sessionId}/speaking/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${sessionId}/speaking/`]: () => jsonResponse({ ...recording, replayed: false }),
    })
    renderApp(`/speaking/session/${sessionId}`)

    await user.click(await screen.findByRole('button', { name: /allow microphone/i }))
    await user.click(await screen.findByRole('button', { name: 'Stop early' }))

    expect(await screen.findByText(/Saved privately/)).toBeInTheDocument()
    const upload = fetchSpy.mock.calls.find(([, init]) => init?.method === 'PUT')
    expect(upload?.[1]?.body).toBeInstanceOf(FormData)
    const headers = upload?.[1]?.headers as Record<string, string>
    expect(headers['Content-Type']).toBeUndefined()
    expect(headers['X-Guest-Token']).toBe('guest-speaking')
    expect(headers['Idempotency-Key']).toBeTruthy()
    expect(stopTrack).toHaveBeenCalled()
  })

  it('restores an immutable submitted review and private playback', async () => {
    Object.defineProperty(URL, 'createObjectURL', {
      configurable: true,
      value: vi.fn(() => 'blob:server-speaking'),
    })
    Object.defineProperty(URL, 'revokeObjectURL', {
      configurable: true,
      value: vi.fn(),
    })
    const review = {
      duration_ms: recording.duration_ms,
      byte_size: recording.byte_size,
      score_label: 'Guided self-review',
      rubric,
      estimated_level: null,
      transcript: null,
      disclaimer: 'This is practice feedback, not an official CELPIP score.',
    }
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${sessionId}/speaking/`]: () => jsonResponse(makeSession({
        state: 'submitted',
        submission: { ...recording, submitted_at: '2026-08-29T08:02:00Z' },
        review,
      })),
      [`GET /sessions/${sessionId}/speaking/audio/`]: () => new Response('private-audio', {
        headers: { 'Content-Type': 'audio/webm' },
      }),
      [`GET /sessions/${sessionId}/ai-feedback/`]: () => jsonResponse({
        status: 'succeeded',
        transcript: 'I would suggest taking the evening course.',
        assessment: {
          overall_summary: 'Clear advice with room for more support.',
          dimensions: [
            { key: 'content_coherence', rating: 3, evidence: 'Two connected ideas.', next_step: 'Add one example.' },
            { key: 'vocabulary', rating: 3, evidence: 'Appropriate everyday words.', next_step: 'Use more precise verbs.' },
            { key: 'delivery', rating: 2, evidence: 'Generally understandable.', next_step: 'Reduce long pauses.' },
            { key: 'task_fulfillment', rating: 3, evidence: 'Advice addressed the friend.', next_step: 'Close with a recommendation.' },
          ],
          strengths: ['Clear recommendation.'],
          priorities: ['Add support.'],
          estimated_level_low: 6,
          estimated_level_high: 7,
          confidence: 'medium',
          disclaimer: 'AI-assisted practice estimate — not an official CELPIP score.',
        },
        audit: { provider: 'fake', model: 'fake-v1', prompt_version: 'v1', created_at: '2026-08-29T08:03:00Z' },
      }),
    })
    renderApp(`/speaking/session/${sessionId}`)

    expect(await screen.findByRole('heading', { name: 'Guided self-review' })).toBeInTheDocument()
    expect(screen.getByText('Content/Coherence')).toBeInTheDocument()
    expect(screen.getAllByText(/not an official CELPIP score/i).length).toBeGreaterThan(0)
    expect(await screen.findByRole('heading', { name: 'Estimated range: 6–7' })).toBeInTheDocument()
    expect(screen.getByText('AI transcript used for feedback')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('Replay your response').parentElement?.querySelector('audio')).toHaveAttribute('src', 'blob:server-speaking'))
    expect(fetchSpy.mock.calls.some(([url]) => String(url).includes('/api/v1/api/v1/'))).toBe(false)
  })
})
