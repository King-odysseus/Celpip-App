import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId, readingSession, readingSessionId } from './fixtures/attempt'

test('a mock task submit never reveals the correct answer or a score before the mock completes', async ({ page }) => {
  await mockApi(page, {
    ...authBootstrap,
    [`GET /sessions/${readingSessionId}/`]: () => readingSession,
    [`PUT /sessions/${readingSessionId}/responses/910/`]: () => ({
      // The server never sends `feedback` for a mock-mode response — only
      // Learn mode does. This assertion guards the contract from the client
      // side: the frozen fixture already omits it, matching production.
      question_id: 910,
      selected_choice_id: 9101, // deliberately the WRONG choice
      revision: 1,
      saved_at: new Date().toISOString(),
    }),
    [`POST /sessions/${readingSessionId}/submit/`]: () => ({
      session_id: readingSessionId,
      state: 'submitted',
      awaiting_mock_results: true,
      mock: readingSession.mock,
      disclaimer: 'Held until the mock completes.',
    }),
    [`POST /mocks/${attemptId}/advance/`]: () => activeAttemptAt(3),
    [`GET /mocks/${attemptId}/`]: () => activeAttemptAt(3),
  })

  await page.goto(`/reading/session/${readingSessionId}`)

  // Select the wrong answer on purpose, then save.
  await page.getByRole('radio', { name: 'April 5' }).check()
  await page.getByRole('button', { name: /save & continue|save answer/i }).click()

  // No correctness feedback, no evidence, no "correct answer" text appears —
  // the response panel gives no signal either way before the mock finishes.
  await expect(page.getByText(/^correct$/i)).not.toBeVisible()
  await expect(page.getByText(/not quite/i)).not.toBeVisible()
  await expect(page.getByText(/evidence:/i)).not.toBeVisible()

  await page.getByRole('button', { name: /submit task|submit practice/i }).click()

  // The learner lands back on the mock workspace (its next task), not a
  // scored results view — the UI-level guarantee that no early feedback is
  // possible even if a future change accidentally added it server-side.
  await expect(page).toHaveURL(new RegExp(`/mock/${attemptId}$`))
  await expect(page.getByRole('button', { name: /launch task/i })).toBeVisible()
  await expect(page.getByText(/correct answer|accuracy|score/i)).not.toBeVisible()
})
