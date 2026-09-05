import { screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from './renderApp'
import { errorResponse, installRouteFetch, jsonResponse } from './mockFetch'

const sessionId = '44444444-4444-4444-8444-444444444444'

const taskTypes = [
  {
    code: 'writing_email',
    skill: 'writing',
    title: 'Writing an Email',
    part_number: 1,
    description: 'Write a complete email that responds to the reader and purpose.',
    strategy: ['Choose a matching level of formality.'],
    common_mistakes: ['Leaving a requested point unanswered.'],
  },
  {
    code: 'writing_survey',
    skill: 'writing',
    title: 'Responding to Survey Questions',
    part_number: 2,
    description: 'Choose one option and support your choice.',
    strategy: ['State your choice clearly first.'],
    common_mistakes: ['Never committing to one option.'],
  },
]

const catalog = {
  count: 2,
  next: null,
  previous: null,
  results: [
    {
      id: 1,
      slug: 'email-noisy-renovation',
      version: 1,
      title: 'Email About Ongoing Renovation Noise',
      topic: 'Housing and tenancy',
      difficulty: 1,
      estimated_level: 6,
      task_type: 'writing_email',
    },
    {
      id: 2,
      slug: 'survey-library-weekend-hours',
      version: 1,
      title: 'Survey: Extending Public Library Hours',
      topic: 'Community services',
      difficulty: 1,
      estimated_level: 6,
      task_type: 'writing_survey',
    },
  ],
}

const rubric = {
  dimensions: [
    { key: 'content_coherence', label: 'Content/Coherence', prompt: 'Did you address every point?' },
    { key: 'vocabulary', label: 'Vocabulary', prompt: 'Did you use varied word choices?' },
    { key: 'readability', label: 'Readability', prompt: 'Are sentences easy to follow?' },
    { key: 'task_fulfillment', label: 'Task Fulfillment', prompt: 'Does it match the task?' },
  ],
}

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: sessionId,
    mode: 'practice',
    state: 'active',
    started_at: '2026-08-29T00:00:00Z',
    deadline_at: null,
    submitted_at: null,
    server_now: '2026-08-29T00:00:00Z',
    is_guest: true,
    content: {
      slug: 'email-noisy-renovation',
      title: 'Email About Ongoing Renovation Noise',
      topic: 'Housing and tenancy',
      difficulty: 1,
      estimated_level: 6,
      task_type: 'writing_email',
      skill: 'writing',
      instructions: 'Read the situation and write an email of about 150 to 200 words.',
      stimulus: {
        type: 'writing_prompt',
        task_kind: 'email',
        scenario: 'Renovations above your unit run early and late.',
        audience: 'Your building manager (semi-formal)',
        requested_points: ['Explain the problem.', 'Describe the impact.', 'Suggest a solution.'],
        target_words: { min: 150, max: 200 },
        suggested_duration_seconds: 1620,
        guidance: ['Keep the tone polite and firm.'],
      },
      questions: [],
    },
    rubric,
    submission: null,
    ...overrides,
  }
}

function saveResult(revision: number) {
  return {
    text: 'unused',
    word_count: 3,
    revision,
    saved_at: '2026-08-29T00:01:00Z',
    submitted_at: null,
    replayed: false,
  }
}

describe('Writing catalog', () => {
  it('shows both task guides and prompt cards in Learn mode', async () => {
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/writing/': () => jsonResponse(catalog),
    })
    renderApp('/learn/writing')

    expect(
      await screen.findByRole('heading', { name: 'Email About Ongoing Renovation Noise' }),
    ).toBeInTheDocument()
    expect(screen.getAllByText('Task 1: Writing an Email').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Task 2: Responding to Survey Questions').length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Target 150–200 words/).length).toBeGreaterThan(0)
  })

  it('starts a guest session and navigates to the writing session', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/writing/': () => jsonResponse(catalog),
      'POST /sessions/': () => jsonResponse({ id: sessionId, guest_token: 'guest-abc' }, 201),
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession({ mode: 'practice' })),
    })
    renderApp('/practice/writing')

    const cards = await screen.findAllByRole('button', { name: 'Start timed practice' })
    await user.click(cards[0])
    await user.click(await screen.findByRole('button', { name: 'Start practice' }))

    expect(await screen.findByLabelText('Your response')).toBeInTheDocument()
    expect(sessionStorage.getItem(`celpip-guest-${sessionId}`)).toBe('guest-abc')
  })
})

describe('Writing editor', () => {
  it('renders the frozen prompt and updates the live word count', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession()),
    })
    const user = userEvent.setup()
    renderApp(`/writing/session/${sessionId}`)

    expect(await screen.findByText('Renovations above your unit run early and late.')).toBeInTheDocument()
    expect(screen.getByText('Explain the problem.')).toBeInTheDocument()

    const editor = screen.getByLabelText('Your response')
    await user.type(editor, 'Hello there manager')
    expect(screen.getByText('3').closest('p')).toHaveTextContent('3 words')
  })

  it('debounces autosave with a UUID key and advances the revision', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    let revision = 0
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${sessionId}/writing/`]: () => jsonResponse(saveResult(++revision)),
    })
    const user = userEvent.setup()
    renderApp(`/writing/session/${sessionId}`)

    const editor = await screen.findByLabelText('Your response')
    await user.type(editor, 'First draft sentence')

    await waitFor(
      () => {
        const put = fetchSpy.mock.calls.find(([, init]) => init?.method === 'PUT')
        expect(put).toBeTruthy()
        const headers = put?.[1]?.headers as Record<string, string>
        expect(headers['X-Guest-Token']).toBe('guest-token')
        expect(headers['Idempotency-Key']).toBeTruthy()
        expect(JSON.parse(String(put?.[1]?.body)).expected_revision).toBe(0)
      },
      { timeout: 2500 },
    )
    expect(await screen.findByText('Saved')).toBeInTheDocument()

    await user.type(editor, ' and more')
    await waitFor(
      () => {
        const puts = fetchSpy.mock.calls.filter(([, init]) => init?.method === 'PUT')
        expect(puts.length).toBeGreaterThanOrEqual(2)
        expect(JSON.parse(String(puts[puts.length - 1]?.[1]?.body)).expected_revision).toBe(1)
      },
      { timeout: 2500 },
    )
  })

  it('resumes an existing draft from the server', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () =>
        jsonResponse(
          makeSession({
            submission: {
              text: 'A saved draft from earlier.',
              word_count: 5,
              revision: 4,
              saved_at: '2026-08-29T00:05:00Z',
              submitted_at: null,
            },
          }),
        ),
    })
    renderApp(`/writing/session/${sessionId}`)

    const editor = (await screen.findByLabelText('Your response')) as HTMLTextAreaElement
    expect(editor.value).toBe('A saved draft from earlier.')
  })
})

describe('Writing autosave error recovery', () => {
  it('re-syncs the revision after a stale conflict and saves again', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    let puts = 0
    installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${sessionId}/writing/`]: () => {
        puts += 1
        if (puts === 1) return errorResponse('stale_revision', 409)
        return jsonResponse(saveResult(2))
      },
    })
    const user = userEvent.setup()
    renderApp(`/writing/session/${sessionId}`)

    const editor = await screen.findByLabelText('Your response')
    await user.type(editor, 'Text that conflicts once')

    expect(await screen.findByText('Saved', {}, { timeout: 3000 })).toBeInTheDocument()
    expect(puts).toBeGreaterThanOrEqual(2)
  })

  it('surfaces an offline state with a retry action', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    let failNext = true
    installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${sessionId}/writing/`]: () => {
        if (failNext) {
          failNext = false
          throw new Error('network down')
        }
        return jsonResponse(saveResult(1))
      },
    })
    const user = userEvent.setup()
    renderApp(`/writing/session/${sessionId}`)

    const editor = await screen.findByLabelText('Your response')
    await user.type(editor, 'Some offline text')

    const retry = await screen.findByRole('button', { name: /retry saving/i }, { timeout: 3000 })
    await user.click(retry)
    expect(await screen.findByText('Saved', {}, { timeout: 3000 })).toBeInTheDocument()
  })
})

describe('Writing submission', () => {
  it('confirms an out-of-range submit, then shows an immutable self-review', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    const fetchSpy = installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () => jsonResponse(makeSession()),
      [`PUT /sessions/${sessionId}/writing/`]: () => jsonResponse(saveResult(1)),
      [`POST /sessions/${sessionId}/writing/submit/`]: () =>
        jsonResponse({
          word_count: 3,
          target_words: { min: 150, max: 200 },
          within_target: false,
          score_label: 'Editorial self-review',
          rubric: { ...rubric, note: 'These dimensions mirror how CELPIP Writing is assessed.' },
          estimated_level: null,
          disclaimer: 'This is practice self-review, not an official CELPIP score or level.',
          session_id: sessionId,
          state: 'submitted',
          submission: {
            text: 'Too short here',
            word_count: 3,
            revision: 2,
            saved_at: '2026-08-29T00:02:00Z',
            submitted_at: '2026-08-29T00:03:00Z',
          },
          replayed: false,
        }),
    })
    const user = userEvent.setup()
    renderApp(`/writing/session/${sessionId}`)

    const editor = await screen.findByLabelText('Your response')
    await user.type(editor, 'Too short here')
    await user.click(screen.getByRole('button', { name: /submit response/i }))

    // Out-of-range warning appears instead of an immediate submit.
    const dialog = await screen.findByRole('alertdialog', { name: 'Confirm submission' })
    await user.click(within(dialog).getByRole('button', { name: /submit anyway/i }))

    await waitFor(() => {
      const submitted = fetchSpy.mock.calls.find(
        ([url, init]) => String(url).endsWith('/writing/submit/') && init?.method === 'POST',
      )
      expect(JSON.parse(String(submitted?.[1]?.body)).text).toBe('Too short here')
    })

    expect(await screen.findByRole('heading', { name: 'Guided self-review' })).toBeInTheDocument()
    expect(screen.getByText('Content/Coherence')).toBeInTheDocument()
    expect(screen.getByText('Task Fulfillment')).toBeInTheDocument()
    expect(screen.getByText(/not an official CELPIP score or level/)).toBeInTheDocument()
    expect(screen.queryByLabelText('Your response')).not.toBeInTheDocument()
  })

  it('renders a submitted session as an immutable review on resume', async () => {
    sessionStorage.setItem(`celpip-guest-${sessionId}`, 'guest-token')
    installRouteFetch({
      [`GET /sessions/${sessionId}/writing/`]: () =>
        jsonResponse(
          makeSession({
            state: 'submitted',
            submitted_at: '2026-08-29T00:03:00Z',
            submission: {
              text: 'The final submitted response.',
              word_count: 4,
              revision: 5,
              saved_at: '2026-08-29T00:02:00Z',
              submitted_at: '2026-08-29T00:03:00Z',
            },
            review: {
              word_count: 4,
              target_words: { min: 150, max: 200 },
              within_target: false,
              score_label: 'Editorial self-review',
              rubric: { ...rubric, note: 'Guided self-review, not an official rating.' },
              estimated_level: null,
              disclaimer: 'This is practice self-review, not an official CELPIP score or level.',
            },
          }),
        ),
    })
    renderApp(`/writing/session/${sessionId}`)

    expect(await screen.findByRole('heading', { name: 'Guided self-review' })).toBeInTheDocument()
    expect(screen.getByText('The final submitted response.')).toBeInTheDocument()
    expect(screen.queryByLabelText('Your response')).not.toBeInTheDocument()
  })
})
