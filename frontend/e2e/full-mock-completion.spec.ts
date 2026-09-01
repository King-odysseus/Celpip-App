import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import {
  activeAttemptAt,
  attemptId,
  listeningSession,
  listeningSessionId,
  makeAttempt,
  mockResults,
  readingSession,
  readingSessionId,
  speakingSession,
  speakingSessionId,
  writingSession,
  writingSessionId,
} from './fixtures/attempt'

async function clearPreflight(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: /play test tone/i }).click()
  await page.getByRole('button', { name: /i heard it/i }).click()
  await page.getByRole('button', { name: /test microphone/i }).click()
  await expect(page.getByText(/microphone connected/i)).toBeVisible()
  await page.getByLabel(/i understand these rules/i).check()
  await page.getByRole('button', { name: /continue to start/i }).click()
}

test('completes every skill of a full mock in official order and reaches results with no fake overall level', async ({ page }) => {
  let attempt = makeAttempt()

  await mockApi(page, {
    ...authBootstrap,
    'GET /mocks/': () => ({ count: 0, results: [] }),
    'POST /mocks/': () => attempt,
    [`GET /mocks/${attemptId}/`]: () => attempt,
    [`POST /mocks/${attemptId}/start/`]: () => {
      attempt = activeAttemptAt(1)
      return attempt
    },
    [`POST /mocks/${attemptId}/advance/`]: async (route) => {
      const body = route.request().postDataJSON() as { expected_order: number }
      const nextOrder = body.expected_order + 1
      attempt = nextOrder > 4 ? makeAttempt({ state: 'completed', completed_at: new Date().toISOString() }) : activeAttemptAt(nextOrder)
      return attempt
    },
    [`GET /mocks/${attemptId}/results/`]: () => mockResults,

    // Listening
    [`GET /sessions/${listeningSessionId}/`]: () => listeningSession,
    [`PUT /sessions/${listeningSessionId}/responses/900/`]: () => ({
      question_id: 900,
      selected_choice_id: 9000,
      revision: 1,
      saved_at: new Date().toISOString(),
    }),
    [`POST /sessions/${listeningSessionId}/submit/`]: () => ({
      session_id: listeningSessionId,
      state: 'submitted',
      awaiting_mock_results: true,
      mock: listeningSession.mock,
      disclaimer: 'Held until the mock completes.',
    }),

    // Reading
    [`GET /sessions/${readingSessionId}/`]: () => readingSession,
    [`PUT /sessions/${readingSessionId}/responses/910/`]: () => ({
      question_id: 910,
      selected_choice_id: 9100,
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

    // Writing
    [`GET /sessions/${writingSessionId}/writing/`]: () => writingSession,
    [`PUT /sessions/${writingSessionId}/writing/`]: () => ({
      text: 'Sure, you can borrow my ladder this weekend. Just return it by Monday, thanks.',
      word_count: 14,
      revision: 1,
      saved_at: new Date().toISOString(),
      replayed: false,
    }),
    [`POST /sessions/${writingSessionId}/writing/submit/`]: () => ({
      session_id: writingSessionId,
      state: 'submitted',
      awaiting_mock_results: true,
      mock: writingSession.mock,
      disclaimer: 'Held until the mock completes.',
    }),

    // Speaking
    [`GET /sessions/${speakingSessionId}/speaking/`]: () => speakingSession,
    [`PUT /sessions/${speakingSessionId}/speaking/`]: () => ({
      duration_ms: 4800,
      byte_size: 12000,
      revision: 1,
      saved_at: new Date().toISOString(),
      replayed: false,
    }),
    [`POST /sessions/${speakingSessionId}/speaking/submit/`]: () => ({
      session_id: speakingSessionId,
      state: 'submitted',
      awaiting_mock_results: true,
      mock: speakingSession.mock,
      disclaimer: 'Held until the mock completes.',
    }),
  })

  await page.goto('/mock')
  await page.getByRole('button', { name: /compact mock/i }).click()
  await clearPreflight(page)
  await page.getByRole('button', { name: /^start mock$/i }).click()

  // Listening
  await page.getByRole('button', { name: /launch task/i }).click()
  await expect(page).toHaveURL(new RegExp(`/reading/session/${listeningSessionId}`))
  await page.getByRole('radio').first().check()
  await page.getByRole('button', { name: /save & continue|save answer/i }).click()
  await page.getByRole('button', { name: /submit task|submit practice/i }).click()

  // Reading
  await expect(page).toHaveURL(new RegExp(`/mock/${attemptId}$`))
  await page.getByRole('button', { name: /launch task/i }).click()
  await expect(page).toHaveURL(new RegExp(`/reading/session/${readingSessionId}`))
  await page.getByRole('radio').first().check()
  await page.getByRole('button', { name: /save & continue|save answer/i }).click()
  await page.getByRole('button', { name: /submit task|submit practice/i }).click()

  // Writing
  await expect(page).toHaveURL(new RegExp(`/mock/${attemptId}$`))
  await page.getByRole('button', { name: /launch task/i }).click()
  await expect(page).toHaveURL(new RegExp(`/writing/session/${writingSessionId}`))
  await page.getByRole('textbox').fill('Sure, you can borrow my ladder this weekend. Just return it by Monday, thanks.')
  await page.getByRole('button', { name: /submit/i }).click()

  // Speaking — real fake-device recording via Chromium's fake media stream.
  await expect(page).toHaveURL(new RegExp(`/mock/${attemptId}$`))
  await page.getByRole('button', { name: /launch task/i }).click()
  await expect(page).toHaveURL(new RegExp(`/speaking/session/${speakingSessionId}`))
  await page.getByRole('button', { name: /allow microphone and start preparation/i }).click()
  await expect(page.getByRole('button', { name: /submit recording/i })).toBeVisible({ timeout: 20_000 })
  await page.getByRole('button', { name: /submit recording/i }).click()

  // Completion — every component visible, no fake overall CELPIP level.
  await expect(page).toHaveURL(new RegExp(`/mock/${attemptId}$`))
  await expect(page.getByRole('heading', { name: /four component results/i })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Listening', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Reading', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Writing', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Speaking', exact: true })).toBeVisible()
  await expect(page.getByText(/no overall score is calculated/i)).toBeVisible()
  await expect(page.getByRole('heading', { name: /recommended next steps/i })).toBeVisible()
})
