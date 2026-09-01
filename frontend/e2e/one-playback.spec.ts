import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { listeningSession, listeningSessionId } from './fixtures/attempt'
import { SILENT_WAV_DATA_URI } from './fixtures/silence'

test('the one-play Listening recording can be started only once', async ({ page }) => {
  const session = {
    ...listeningSession,
    deadline_at: new Date(Date.now() + 60_000).toISOString(),
  }
  await mockApi(page, {
    ...authBootstrap,
    [`GET /sessions/${listeningSessionId}/`]: () => session,
    [`POST /sessions/${listeningSessionId}/media/501/access/`]: () => ({
      url: SILENT_WAV_DATA_URI,
      expires_in_seconds: 300,
      plays_remaining: 1,
    }),
  })

  await page.goto(`/reading/session/${listeningSessionId}`)

  const playButton = page.getByRole('button', { name: /play practice audio/i })
  await expect(playButton).toBeEnabled()
  await playButton.click()

  // Let the short clip finish, then confirm it cannot be started again.
  await expect(page.getByText(/the one-play recording has ended/i)).toBeVisible({ timeout: 10_000 })
  const disabledButton = page.getByRole('button', { name: /replay practice audio/i })
  await expect(disabledButton).toBeDisabled()
})
