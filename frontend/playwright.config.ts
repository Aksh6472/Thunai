// E2E (T-044): the full stack in demo mode against the thunai_test database, on ports that
// don't clash with `make dev`. Each spec resets the demo first (TESTING.md §5).
import { defineConfig, devices } from '@playwright/test'

import { API_PORT, TEST_DATABASE_URL, WEB_PORT } from './e2e/env.ts'

export default defineConfig({
  testDir: './e2e',
  timeout: 90_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: `http://localhost:${WEB_PORT}`,
    viewport: { width: 1366, height: 768 },
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1366, height: 768 },
        // Installed Google Chrome by default; set PW_CHANNEL=chromium after `npx playwright install chromium`.
        channel: process.env.PW_CHANNEL ?? 'chrome',
      },
    },
  ],
  webServer: [
    {
      // Migrate and seed the test DB first so admin.demo exists for the per-spec resets.
      command: `cd ../backend && uv run alembic upgrade head && uv run python -m sim.seed --seed 42 && uv run uvicorn app.main:app --port ${API_PORT} --workers 1`,
      url: `http://localhost:${API_PORT}/api/v1/healthz`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATABASE_URL: TEST_DATABASE_URL,
        // test: rate limits off (TESTING.md §2.4); specs log in many times a minute.
        THUNAI_ENV: 'test',
        THUNAI_DEMO_MODE: 'true',
        THUNAI_NOTIFIER: 'console',
        THUNAI_PUBLIC_WEB_URL: `http://localhost:${WEB_PORT}`,
        THUNAI_CORS_ORIGINS: `http://localhost:${WEB_PORT}`,
        THUNAI_LOG_LEVEL: 'WARNING',
      },
    },
    {
      command: `npx vite --port ${WEB_PORT} --strictPort`,
      url: `http://localhost:${WEB_PORT}/login`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: { VITE_API_BASE_URL: `http://localhost:${API_PORT}/api/v1`, VITE_DEMO_MODE: 'true' },
    },
  ],
})
