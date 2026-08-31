import { fireEvent, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'

const sessionId = '22222222-2222-4222-8222-222222222222'
const listeningSession = {
  id: sessionId,
  mode: 'learn',
  state: 'active',
  started_at: '2026-08-29T00:00:00Z',
  deadline_at: null,
  submitted_at: null,
  server_now: '2026-08-29T00:00:00Z',
  is_guest: true,
  audio: {
    asset_id: '33333333-3333-4333-8333-333333333333',
    duration_ms: 86_000,
    voice_label: 'Synthetic Canadian-English development voice',
    playback_policy: 'unlimited_learning',
  },
  content: {
    slug: 'apartment-heating-plan',
    title: 'The Apartment Heating Problem',
    topic: 'Housing maintenance',
    difficulty: 1,
    estimated_level: 5,
    task_type: 'listening_problem_solving',
    skill: 'listening',
    instructions: 'Listen once and answer.',
    learning_notes: 'Track the problem and final decision.',
    stimulus: {
      type: 'audio_context',
      introduction: 'Two neighbours discuss a cold apartment.',
    },
    questions: [
      {
        id: 30,
        order: 1,
        stem: 'What is the main problem?',
        skill_focus: 'gist',
        choices: [
          { id: 40, order: 1, text: 'The apartments are cold' },
          { id: 41, order: 2, text: 'The water is off' },
        ],
      },
    ],
  },
  responses: [],
}

describe('Listening player', () => {
  beforeEach(() => {
    vi.spyOn(HTMLMediaElement.prototype, 'play').mockResolvedValue()
    vi.spyOn(HTMLMediaElement.prototype, 'pause').mockImplementation(() => undefined)
  })

  it('requests a private audio grant with the guest token', async () => {
    const user = userEvent.setup()
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'private-guest-token')
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${sessionId}/`]: () => jsonResponse(listeningSession),
      [`POST /sessions/${sessionId}/media/${listeningSession.audio.asset_id}/access/`]: () =>
        jsonResponse({
          url: '/api/v1/media/audio/asset/stream/?token=signed',
          expires_in_seconds: 600,
          plays_remaining: null,
        }),
    })
    const { container } = renderApp(`/reading/session/${sessionId}`)

    await user.click(await screen.findByRole('button', { name: 'Play practice audio' }))
    await waitFor(() => {
      const accessCall = fetchSpy.mock.calls.find(
        ([url, init]) => String(url).includes('/media/') && init?.method === 'POST',
      )
      expect((accessCall?.[1]?.headers as Record<string, string>)['X-Guest-Token']).toBe(
        'private-guest-token',
      )
      expect(HTMLMediaElement.prototype.play).toHaveBeenCalledTimes(1)
    })
    const audio = container.querySelector('audio')!
    expect(audio.src).toContain('/api/v1/media/audio/asset/stream/?token=signed')
    expect(screen.queryByText(/select play again/i)).not.toBeInTheDocument()
    fireEvent.play(audio)
    expect(screen.getByRole('button', { name: 'Pause practice audio' })).toBeInTheDocument()
    expect(HTMLMediaElement.prototype.play).toHaveBeenCalled()
  })

  it('unlocks the reviewed transcript only after a Learn answer', async () => {
    const user = userEvent.setup()
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'private-guest-token')
    installRouteFetch({
      [`GET /sessions/${sessionId}/`]: () => jsonResponse(listeningSession),
      [`PUT /sessions/${sessionId}/responses/30/`]: () =>
        jsonResponse({
          question_id: 30,
          selected_choice_id: 40,
          revision: 1,
          saved_at: '2026-08-29T00:01:00Z',
          replayed: false,
          feedback: {
            is_correct: true,
            correct_choice_id: 40,
            evidence: 'Both neighbours describe cold apartments.',
            explanation: 'The heating failure is the central issue.',
            selected_choice_explanation: 'This matches the discussion.',
            transcript: 'Nadia: Is your apartment unusually cold too?',
          },
        }),
    })
    renderApp(`/reading/session/${sessionId}`)

    expect(screen.queryByText('Study the transcript')).not.toBeInTheDocument()
    await user.click(await screen.findByRole('radio', { name: 'The apartments are cold' }))
    await user.click(screen.getByRole('button', { name: /save & continue/i }))
    expect(await screen.findByText('Study the transcript')).toBeInTheDocument()
  })
})
