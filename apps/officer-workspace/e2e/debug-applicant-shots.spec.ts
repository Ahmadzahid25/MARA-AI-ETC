import { test } from '@playwright/test';

test('applicant login screenshots', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/applicant', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'applicant-login-desktop.png' });

  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto('/applicant', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'applicant-login-mobile.png' });

  await page.getByRole('button', { name: 'Buka menu' }).click();
  await page.screenshot({ path: 'applicant-login-mobile-drawer.png' });
});
