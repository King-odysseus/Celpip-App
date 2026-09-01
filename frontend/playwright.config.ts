import { defineConfig, devices } from '@playwright/test'

/**
 * End-to-end journeys for the full mock simulation (Phase 12). These drive a
 * real Chromium/mobile-viewport browser against the real Vite dev server so
 * keyboard focus, ARIA live regions, and layout reflow are genuinely
 * exercised — jsdom (used by the Vitest unit suite) cannot validate any of
 * that. The Django API itself is not required: every /api/v1/** request is
 * intercepted deterministically via each spec's mockApi helper, matching the
 * fetch-mocking approach already used by the Vitest integration tests.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // Speaking's fake-device recording is resource-heavy; too many parallel
  // workers on one machine cause contention flakiness that has nothing to
  // do with correctness (verified: those specs pass reliably in isolation).
  workers: process.env.CI ? 4 : 3,
  reporter: process.env.CI ? [['github'], ['list']] : 'list',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop-chromium',
      testIgnore: [/microphone-denial\.spec\.ts/, /mobile-layout\.spec\.ts/],
      use: {
        ...devices['Desktop Chrome'],
        permissions: ['microphone'],
        // Chromium's fake capture device stands in for a real microphone, so
        // Speaking recording (getUserMedia + MediaRecorder) works exactly as
        // it would for a real user — no per-spec media stubbing needed.
        launchOptions: {
          args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
        },
      },
    },
    {
      name: 'mobile-chromium',
      testMatch: /mobile-layout\.spec\.ts/,
      use: { ...devices['Pixel 7'] },
    },
    {
      // --use-fake-ui-for-media-stream (the default project's launch flag)
      // auto-accepts every getUserMedia prompt regardless of the Permissions
      // API state, so a genuine "denied" microphone can't be simulated
      // there. Plain headless Chromium has no dialog to interact with and
      // denies any permission that isn't explicitly granted, which is
      // exactly the real "user hasn't granted mic access yet" case.
      name: 'desktop-chromium-no-media',
      testMatch: /microphone-denial\.spec\.ts/,
      use: {
        ...devices['Desktop Chrome'],
        // A fake capture device exists (so a later, explicitly-granted retry
        // has a real microphone to connect to) but no fake-ui flag, so the
        // Permissions API — not an auto-accept dialog — decides access.
        launchOptions: { args: ['--use-fake-device-for-media-stream'] },
      },
    },
  ],
  webServer: {
    command: 'npm run dev -- --port 5173 --strictPort',
    url: 'http://localhost:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
})
