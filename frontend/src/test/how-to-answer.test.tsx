import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { renderApp } from './renderApp'
import { installRouteFetch, jsonResponse } from './mockFetch'

function taskType(skill: string, code: string, title: string) {
  return {
    code,
    skill,
    title,
    part_number: 1,
    description: `Description for ${title}.`,
    strategy: [`Strategy step for ${title}.`],
    common_mistakes: [`Common mistake for ${title}.`],
  }
}

describe('How to Answer page', () => {
  it('shows the level-12 guidance and task guides for each skill', async () => {
    // The page requests /content/task-types/?skill=X for each skill in a fixed
    // order (listening, reading, writing, speaking); the shared mock fetch
    // matches on pathname only (query strings are stripped), so respond to
    // each call in that same fixed sequence.
    const responses = [
      [taskType('listening', 'listening_problem_solving', 'Problem Solving')],
      [taskType('reading', 'reading_correspondence', 'Reading Correspondence')],
      [taskType('writing', 'writing_email', 'Writing an Email')],
      [taskType('speaking', 'speaking_advice', 'Giving Advice')],
    ]
    let call = 0
    installRouteFetch({
      'GET /content/task-types/': async () => jsonResponse(responses[call++] ?? []),
    })

    renderApp('/how-to-answer')

    await waitFor(() => expect(screen.getByText('How to Answer')).toBeInTheDocument())
    // Defaults to Listening.
    await waitFor(() =>
      expect(screen.getByText(/Separate what was said from what you inferred/)).toBeInTheDocument(),
    )
    expect(screen.getByText('Part 1: Problem Solving')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: /Writing/ }))
    await waitFor(() =>
      expect(
        screen.getByText(/Complete the task fully, in an organized, appropriately toned response/),
      ).toBeInTheDocument(),
    )
    expect(screen.getByText('Task 1: Writing an Email')).toBeInTheDocument()
  })
})
