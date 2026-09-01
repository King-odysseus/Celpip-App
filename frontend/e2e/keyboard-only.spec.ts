import { expect, test } from '@playwright/test'
import { authBootstrap, mockApi } from './fixtures/mockApi'
import { attemptId, makeAttempt } from './fixtures/attempt'

test('a learner can create a mock and clear the entire preflight using only the keyboard', async ({ page }) => {
  const attempt = makeAttempt()
  await mockApi(page, {
    ...authBootstrap,
    'GET /mocks/': () => ({ count: 0, results: [] }),
    'POST /mocks/': () => attempt,
    [`GET /mocks/${attemptId}/`]: () => attempt,
  })

  await page.goto('/mock')

  // Tab to the "Compact mock" button and activate it with the keyboard —
  // no pointer interaction anywhere in this test.
  const compactMockButton = page.getByRole('button', { name: /compact mock/i })
  await compactMockButton.focus()
  await expect(compactMockButton).toBeFocused()
  await page.keyboard.press('Enter')

  await expect(page.getByRole('heading', { name: /device check/i })).toBeVisible()

  // Play the tone and confirm hearing it, tabbing between the two controls.
  const playTone = page.getByRole('button', { name: /play test tone/i })
  await playTone.focus()
  await page.keyboard.press('Enter')
  const heardIt = page.getByRole('button', { name: /i heard it/i })
  await expect(heardIt).toBeVisible()
  await heardIt.focus()
  await page.keyboard.press('Enter')

  // Test the microphone the same way.
  const testMic = page.getByRole('button', { name: /test microphone/i })
  await testMic.focus()
  await page.keyboard.press('Enter')
  await expect(page.getByText(/microphone connected/i)).toBeVisible()

  // Toggle the rules checkbox with Space, then activate Continue with Enter.
  const checkbox = page.getByLabel(/i understand these rules/i)
  await checkbox.focus()
  await page.keyboard.press('Space')
  await expect(checkbox).toBeChecked()

  const continueButton = page.getByRole('button', { name: /continue to start/i })
  await expect(continueButton).toBeEnabled()
  await continueButton.focus()
  await page.keyboard.press('Enter')

  const startButton = page.getByRole('button', { name: /^start mock$/i })
  await expect(startButton).toBeVisible()
  await startButton.focus()
  await expect(startButton).toBeFocused()
})
