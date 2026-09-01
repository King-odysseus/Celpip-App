import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { attemptId, makeAttempt } from './fixtures/attempt'

// A successfully *granted* microphone (the retry's happy path) is already
// exercised end-to-end by full-mock-completion.spec.ts's Speaking task, on
// the default project where the fake device is available from the start.
// This spec covers what that one cannot: a genuine denial.
test('preflight explains a denied microphone and offers a retry that keeps the gate closed', async ({ page }) => {
  const attempt = makeAttempt()
  await mockApi(page, {
    ...authBootstrap,
    'GET /mocks/': () => ({ count: 0, results: [] }),
    'POST /mocks/': () => attempt,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto('/mock')
  await page.getByRole('button', { name: /compact mock/i }).click()

  await page.getByRole('button', { name: /play test tone/i }).click()
  await page.getByRole('button', { name: /i heard it/i }).click()

  await page.getByRole('button', { name: /test microphone/i }).click()
  await expect(page.getByText(/microphone permission was not granted/i)).toBeVisible()
  const retry = page.getByRole('button', { name: /try again/i })
  await expect(retry).toBeVisible()

  // "I understand these rules" and Continue are unavailable without the mic
  // check passing — the gate genuinely blocks progress, not just cosmetics.
  await page.getByLabel(/i understand these rules/i).check()
  await expect(page.getByRole('button', { name: /continue to start/i })).toBeDisabled()

  // Retrying without fixing the permission asks again and stays denied —
  // it doesn't silently let the learner through.
  await retry.click()
  await expect(page.getByText(/microphone permission was not granted/i)).toBeVisible()
  await expect(page.getByRole('button', { name: /continue to start/i })).toBeDisabled()
})
