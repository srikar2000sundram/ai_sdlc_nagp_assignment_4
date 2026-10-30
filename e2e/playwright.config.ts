/**
 * Playwright configuration for the end-to-end tests.
 * Run with `npm test` in this folder; the app is started automatically (see webServer below).
 */
import { defineConfig, devices } from '@playwright/test';

// The address the app is served on during tests.
const baseURL = 'http://127.0.0.1:5000';

export default defineConfig({
  // Where the test files live.
  testDir: './tests',
  // One test at a time: the app keeps its data in memory, so parallel tests would see each other's changes.
  workers: 1,
  // Retry once on CI only, so a flaky machine does not hide real failures when running locally.
  retries: process.env.CI ? 1 : 0,
  // A readable list in the terminal plus an HTML report (not opened automatically).
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    // Record a trace on the first retry to help diagnose a failure.
    trace: 'on-first-retry',
  },
  // One browser is enough for this demo.
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  // Start the Python app before the tests and stop it afterwards.
  webServer: {
    command: 'python -m uvicorn invoice_app.api.main:app --app-dir ../backend/src --host 127.0.0.1 --port 5000',
    url: baseURL,
    // If something is already listening on the port it is reused, so its data is whatever that server holds.
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
