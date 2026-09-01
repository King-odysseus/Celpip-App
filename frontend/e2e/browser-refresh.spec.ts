import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId } from './fixtures/attempt'

test('refreshing mid-section shows the same server deadline, never a reset or extended one', async ({ page }) => {
  // A deadline comfortably in the future so the countdown reads the same
  // whole minute immediately before and after the reload.
  const deadline = new Date(Date.now() + 300_000).toISOString()
  const attempt = activeAttemptAt(1, { section_deadline_at: deadline })

  await mockApi(page, {
    ...authBootstrap,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto(`/mock/${attemptId}`)
  const timer = page.getByLabel(/minutes.*seconds remaining/i)
  await expect(timer).toBeVisible()
  const before = await timer.textContent()

  await page.reload()

  await expect(page.getByRole('button', { name: /launch task/i })).toBeVisible()
  const after = await page.getByLabel(/minutes.*seconds remaining/i).textContent()

  // Same server-provided deadline before and after — the client never
  // invents its own extended or reset countdown on reload.
  expect(after).toBe(before)
})
