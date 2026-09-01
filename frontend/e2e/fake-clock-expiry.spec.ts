import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { activeAttemptAt, attemptId, makeAttempt, makeTasks } from './fixtures/attempt'

test('an expired section deadline auto-advances the mock without any user action', async ({ page }) => {
  await page.clock.install({ time: new Date('2026-08-29T09:00:00.000Z') })

  // Deadline arrives 30 real seconds into the section — the timer's own
  // 1-second tick loop will discover it once the clock is fast-forwarded.
  const attempt = activeAttemptAt(1, {
    section_deadline_at: new Date('2026-08-29T09:00:30.000Z').toISOString(),
    server_now: new Date('2026-08-29T09:00:00.000Z').toISOString(),
  })
  // Flipped explicitly by the test once the deadline has actually been
  // fast-forwarded past — not inferred from call count, which React
  // StrictMode's dev-only double-mount would make unreliable (two GETs can
  // legitimately fire before the deadline is ever reached).
  let expired = false

  await mockApi(page, {
    ...authBootstrap,
    [`GET /mocks/${attemptId}/`]: () => {
      if (!expired) return attempt
      // The client's onExpire refetch reconciles with the server, which has
      // already skipped the unfinished task and moved to the next section —
      // exactly what the real /mocks/{id}/ endpoint does when a section
      // deadline has passed (see mocks.services._expire_locked).
      return makeAttempt({
        state: 'completed',
        completed_at: new Date('2026-08-29T09:00:31.000Z').toISOString(),
        tasks: makeTasks(undefined, { 1: 'skipped', 2: 'skipped', 3: 'skipped', 4: 'skipped' }),
      })
    },
  })

  await page.goto(`/mock/${attemptId}`)
  await expect(page.getByRole('button', { name: /launch task/i })).toBeVisible()

  expired = true
  await page.clock.fastForward('00:35')

  // No click, no navigation triggered by the test — only the timer's own
  // expiry callback refetches and the workspace reconciles to "completed".
  await expect(page.getByRole('heading', { name: /four component results/i })).toBeVisible({ timeout: 10_000 })
})
