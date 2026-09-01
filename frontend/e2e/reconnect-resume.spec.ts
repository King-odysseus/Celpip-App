import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId } from './fixtures/attempt'

test('a network interruption while opening a mock recovers cleanly on the next load, no lost or duplicated state', async ({ page }) => {
  const attempt = activeAttemptAt(2, {
    section_deadline_at: new Date(Date.now() + 300_000).toISOString(),
  }) // mid-attempt: Reading is current, Listening already done
  let connected = false

  await mockApi(page, { ...authBootstrap })

  // Every request while `connected` is false is dropped at the network layer
  // (a genuine connection reset, not an HTTP error) to model losing
  // connectivity for the whole initial load — not just a single request,
  // since the dev server's React StrictMode double-invokes the loading
  // effect and a lone failed request would otherwise be masked by its
  // benign duplicate silently succeeding moments later.
  await page.route(`**/api/v1/mocks/${attemptId}/`, async (route) => {
    if (!connected) {
      await route.abort('connectionreset')
      return
    }
    await route.fulfill({ status: 200, json: attempt })
  })

  await page.goto(`/mock/${attemptId}`)
  await expect(page.getByText(/mock unavailable/i)).toBeVisible()
  await expect(page.getByRole('alert')).toHaveText(/could not open this mock attempt/i)

  // The connection is back — reopening the same attempt (e.g. the learner's
  // next visit) reconciles cleanly to the real server state: no lost
  // progress, no duplicated tasks, and the correct task is current.
  connected = true
  await page.reload()
  await expect(page.getByRole('button', { name: /launch task/i })).toBeVisible()
  await expect(page.getByText(/reading · task 2 of 4/i)).toBeVisible()
  await expect(page.getByRole('listitem')).toHaveCount(4)
})
