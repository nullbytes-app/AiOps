import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright Configuration for Next.js E2E Tests
 *
 * Following 2025 best practices:
 * - Runs dev server automatically for local development
 * - Uses baseURL to ensure correct navigation
 * - Configured for CI/CD with headless mode
 * - Captures screenshots/videos on failure
 */
export default defineConfig({
  testDir: './e2e',

  /* Maximum time one test can run for. */
  timeout: 30 * 1000,

  /* Run tests in files in parallel */
  fullyParallel: true,

  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: 'html',

  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL: 'http://localhost:3001',

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video on failure */
    video: 'retain-on-failure',

    /* Block Service Workers - critical for Playwright route interception to work!
     * Service Workers (including MSW) can intercept network requests before Playwright's
     * route handlers, making API mocks invisible to the test. Blocking Service Workers
     * ensures Playwright route interception works as expected.
     *
     * Reference: https://playwright.dev/docs/service-workers-experimental
     * Reference: https://github.com/microsoft/playwright/issues/20501
     */
    serviceWorkers: 'block',
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'E2E_TEST=true NEXT_PUBLIC_E2E_TEST=true NEXT_PUBLIC_API_URL=http://localhost:3001 PORT=3001 npm run dev',
    url: 'http://localhost:3001/api/healthz',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
})
