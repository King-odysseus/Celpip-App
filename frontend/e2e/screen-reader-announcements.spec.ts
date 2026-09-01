import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId } from './fixtures/attempt'

test('the section timer announces only at meaningful thresholds via an ARIA live region', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-29T09:00:00.000Z') })

  const attempt = activeAttemptAt(1, {
    section_deadline_at: new Date('2026-08-29T09:05:05.000Z').toISOString(), // 5:05 remaining
    server_now: new Date('2026-08-29T09:00:00.000Z').toISOString(),
  })

  await mockApi(page, {
    ...authBootstrap,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto(`/mock/${attemptId}`)
  const timer = page.getByLabel(/minutes.*seconds remaining/i)
  await expect(timer).toBeVisible()

  // The live region is present but silent at an arbitrary moment.
  const liveRegion = page.locator('[aria-live="polite"]')
  await expect(liveRegion).toHaveText('')

  // Advance to exactly 5 minutes remaining — the threshold announcement.
  await page.clock.fastForward('00:05')
  await expect(liveRegion).toHaveText(/five minutes remaining/i)

  // Advance to exactly 1 minute remaining — the next threshold.
  await page.clock.fastForward('03:59')
  await expect(liveRegion).toHaveText(/one minute remaining/i)

  // Between thresholds the region does not narrate every passing second —
  // only the two labelled moments and the end ever populate it.
  await page.clock.fastForward('00:30')
  await expect(liveRegion).not.toHaveText(/one minute remaining/i)
  await expect(liveRegion).not.toHaveText(/five minutes remaining/i)
})
