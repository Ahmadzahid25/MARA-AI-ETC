import { test, expect } from '@playwright/test';

/**
 * Helper — inject the dev-mode session into sessionStorage before any
 * navigation so AuthGuard lets us through without Keycloak.
 */
async function loginDevMode(page: import('@playwright/test').Page) {
  await page.addInitScript(() => {
    sessionStorage.setItem(
      'mara_dev_mode_user',
      JSON.stringify({ name: 'Officer Zahid (Dev)', email: 'zahid@mara.gov.my', role: 'officer' }),
    );
  });
}

/**
 * Mock the /api/chat endpoint so Playwright tests are self-contained and
 * do not need the actual API gateway running.  The mock returns the same
 * shape the FastAPI router returns.
 */
async function mockChatBackend(page: import('@playwright/test').Page, response: {
  reply: string; intent: string; workflow?: object | null;
}) {
  await page.route('**/chat', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ workflow: null, ...response }),
    });
  });
}

// ─── Backend path: conversational ─────────────────────────────────────────────

test('backend: "hai" → Planner returns conversational reply', async ({ page }) => {
  await loginDevMode(page);
  await mockChatBackend(page, {
    intent: 'conversational',
    reply: 'Selamat datang! I\'m your MARA AI assistant. How can I help you today?',
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/describe your task/i);
  await expect(input).toBeVisible({ timeout: 15_000 });

  await input.fill('hai');
  await input.press('Enter');

  const reply = page.locator('[class*="rounded-xl"]').filter({ hasText: /selamat datang/i });
  await expect(reply).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/assessment started/i)).not.toBeVisible();
});

// ─── Backend path: clarification ──────────────────────────────────────────────

test('backend: vague message → Planner returns clarification', async ({ page }) => {
  await loginDevMode(page);
  await mockChatBackend(page, {
    intent: 'clarification',
    reply: 'Could you tell me more about what you\'d like to do?',
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/describe your task/i);
  await expect(input).toBeVisible({ timeout: 15_000 });

  await input.fill('help');
  await input.press('Enter');

  const reply = page.locator('[class*="rounded-xl"]').filter({
    hasText: /could you tell me more/i,
  });
  await expect(reply).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/assessment started/i)).not.toBeVisible();
});

// ─── Backend path: workflow intent ────────────────────────────────────────────

test('backend: assessment message → Planner triggers workflow', async ({ page }) => {
  await loginDevMode(page);

  // Step 1: /api/chat says workflow_started.
  await page.route('**/chat', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        intent: 'workflow_started',
        reply: 'Starting loan assessment...',
        workflow: { template_name: 'loan_assessment', confidence: 0.92 },
      }),
    });
  });

  // Step 2: the workflow launch endpoint returns a mock assessment.
  let apiCallMade = false;
  await page.route('**/loans/assessments', (route) => {
    apiCallMade = true;
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        thread_id: 'test-thread-1234',
        status: 'running',
        pending_gate: 'confirm_extraction',
        pending_payload: null,
        stage_log: [],
        acted_gate: null,
      }),
    });
  });

  await page.goto('/');
  const input = page.getByPlaceholder(/describe your task/i);
  await expect(input).toBeVisible({ timeout: 15_000 });

  await input.fill('I need to assess a loan application');
  await input.press('Enter');

  const reply = page.locator('[class*="rounded-xl"]').filter({ hasText: /assessment started/i });
  await expect(reply).toBeVisible({ timeout: 10_000 });
  expect(apiCallMade).toBe(true);
});

// ─── Fallback path: backend unreachable ───────────────────────────────────────

test('fallback: backend down → local keyword detection handles greeting', async ({ page }) => {
  await loginDevMode(page);

  // Simulate backend being down — abort the /api/chat request.
  await page.route('**/chat', (route) => route.abort('failed'));

  await page.goto('/');
  const input = page.getByPlaceholder(/describe your task/i);
  await expect(input).toBeVisible({ timeout: 15_000 });

  await input.fill('selamat pagi');
  await input.press('Enter');

  // The local fallback should still produce a greeting-style reply.
  const reply = page.locator('[class*="rounded-xl"]').filter({ hasText: /selamat datang/i });
  await expect(reply).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(/assessment started/i)).not.toBeVisible();
});

