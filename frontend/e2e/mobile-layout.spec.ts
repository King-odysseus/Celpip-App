import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId, makeAttempt } from './fixtures/attempt'

test('the mock hub, preflight, and active workspace all fit a phone viewport without horizontal scroll', async ({ page }) => {
  const attempt = makeAttempt()
  await mockApi(page, {
    ...authBootstrap,
    'GET /mocks/': () => ({ count: 0, results: [] }),
    'POST /mocks/': () => attempt,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto('/mock')
  await expect(page.getByRole('heading', { name: 'Mock Tests' })).toBeVisible()
  await expect(page.getByRole('button', { name: /compact mock/i })).toBeVisible()
  await expectNoHorizontalOverflow(page)

  // The mobile bottom navigation (hidden on desktop) is the primary nav here.
  await expect(page.getByRole('navigation', { name: /primary mobile/i })).toBeVisible()

  await page.getByRole('button', { name: /compact mock/i }).click()
  await expect(page.getByRole('heading', { name: /device check/i })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

test('the active mock workspace fits a phone viewport', async ({ page }) => {
  const attempt = activeAttemptAt(1)
  await mockApi(page, {
    ...authBootstrap,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto(`/mock/${attemptId}`)
  await expect(page.getByRole('button', { name: /launch task/i })).toBeVisible()
  await expectNoHorizontalOverflow(page)
})

async function expectNoHorizontalOverflow(page: import('@playwright/test').Page) {
  const { scrollWidth, clientWidth } = await page.evaluate(() => ({
    scrollWidth: document.documentElement.scrollWidth,
    clientWidth: document.documentElement.clientWidth,
  }))
  expect(scrollWidth).toBeLessThanOrEqual(clientWidth)
}
