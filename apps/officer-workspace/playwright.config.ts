import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright config for the MARA AI-ETC Officer Workspace.
 *
 * Targets the Vite dev server (port 4000).  Auth is bypassed via the
 * dev-mode sessionStorage key injected in the global setup script so
 * AuthGuard lets us straight through to protected pages without Keycloak.
 *
 * Run:
 *   npx playwright test
 *
 * The dev server is started automatically by the `webServer` block below;
 * no separate `npm run dev` required.
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['html', { open: 'never' }], ['list']],

  use: {
    baseURL: 'http://localhost:4000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Spin up the Vite dev server automatically before tests. */
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:4000',
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
