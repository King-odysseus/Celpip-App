import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'
import { AIFeedbackPanel } from '../features/ai/AIFeedbackPanel'

const sessionId = '66666666-6666-4666-8666-666666666666'

const pattern = {
  mnemonic: 'CARE',
  summary: 'Show you care, then give three tips with reasons.',
  plan: '90 sec: Connect 10s · Advise 25s · Add 45s · Reassure 10s',
  steps: [
    { key: 'connect', label: 'Connect', what: 'Show you understand.', phrases: ['I understand how stressful that is.'] },
    { key: 'advise', label: 'Advise', what: 'Give your first tip.', phrases: ['The first thing I would suggest is…'] },
    { key: 'add', label: 'Add', what: 'Add two more tips.', phrases: ['Another thing you could try is…'] },
    { key: 'reassure', label: 'Reassure', what: 'Encourage them.', phrases: ["I'm sure you'll handle it well."] },
  ],
}

const taskTypes = [{
  code: 'speaking_advice',
  skill: 'speaking',
  title: 'Giving Advice',
  part_number: 1,
  description: 'Give useful advice to someone you know.',
  strategy: ['Acknowledge the situation.'],
  common_mistakes: ['Listing ideas without explaining them.'],
  answer_pattern: pattern,
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

describe('answer pattern briefing', () => {
  it('requires recalling the pattern in order before practice starts', async () => {
    const user = userEvent.setup()
    installRouteFetch({
      'GET /content/task-types/': () => jsonResponse(taskTypes),
      'GET /content/speaking/': () => jsonResponse(catalog),
    })
    renderApp('/practice/speaking')

    await user.click(await screen.findByRole('button', { name: 'Open microphone practice' }))
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText('CARE')).toBeInTheDocument()
    const start = within(dialog).getByRole('button', { name: 'Start practice' })
    expect(start).toBeDisabled()

    const drill = within(dialog).getByLabelText('Pattern recall drill')
    await user.click(within(drill).getByRole('button', { name: 'Reassure' }))
    expect(within(drill).getByText(/Not quite/)).toBeInTheDocument()
    expect(start).toBeDisabled()

    await user.click(within(drill).getByRole('button', { name: 'Try again' }))
    for (const label of ['Connect', 'Advise', 'Add', 'Reassure']) {
      await user.click(within(drill).getByRole('button', { name: label }))
    }
    expect(within(drill).getByText(/Correct/)).toBeInTheDocument()
    expect(start).toBeEnabled()
  })
})

describe('AI feedback pattern check', () => {
  it('shows which steps were followed and labels the model answer by step', async () => {
    installRouteFetch({
      [`GET /sessions/${sessionId}/ai-feedback/`]: () => jsonResponse({
        status: 'succeeded',
        kind: 'speaking_feedback',
        example_status: 'succeeded',
        assessment: {
          overall_summary: 'Clear advice.',
          dimensions: [],
          strengths: [],
          priorities: [],
          estimated_level_low: 8,
          estimated_level_high: 9,
          confidence: 'medium',
          disclaimer: 'Practice estimate.',
          pattern_check: [
            { step: 'Connect', followed: true, note: 'You showed understanding.' },
            { step: 'Reassure', followed: false, note: 'You ended without encouragement.' },
          ],
          level_twelve_exemplar: {
            response: 'I know this is hard. First, try a class. You will do great.',
            why_it_is_strong: 'It follows the pattern.',
            highlights: [],
            pattern_map: [
              { step: 'Connect', excerpt: 'I know this' },
              { step: 'Advise', excerpt: 'First, try' },
              { step: 'Reassure', excerpt: 'You will do' },
            ],
          },
        },
      }),
    })
    render(<MemoryRouter><AIFeedbackPanel sessionId={sessionId} /></MemoryRouter>)

    expect(await screen.findByText('Answer pattern check')).toBeInTheDocument()
    expect(screen.getByText('1/2 steps')).toBeInTheDocument()
    expect(screen.getByLabelText('Missing')).toBeInTheDocument()
    // Each step's label chip sits right before the words that begin it.
    expect(
      screen.getByText((_, element) => element?.tagName === 'SPAN' && element.textContent === 'AdviseFirst, try a class. '),
    ).toBeInTheDocument()
  })
})
