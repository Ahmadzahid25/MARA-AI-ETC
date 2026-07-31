import { test } from '@playwright/test';

test('verify login card brand row above heading, left-aligned', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5500);

  const r = await page.evaluate(() => {
    const card = document.querySelector('[class*="loginCard"]') as HTMLElement | null;
    const box = (el: Element | null) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { left: Math.round(r.left), right: Math.round(r.right), top: Math.round(r.top), bottom: Math.round(r.bottom), width: Math.round(r.width), height: Math.round(r.height) };
    };
    const row = card?.querySelector('[class*="brandRow"]') as HTMLElement | null;
    const badge = card?.querySelector('[class*="iconBadge"]') as HTMLElement | null;
    const name = card?.querySelector('[class*="brandName"]') as HTMLElement | null;
    const role = card?.querySelector('[class*="brandRole"]') as HTMLElement | null;
    const heading = card?.querySelector('[class*="heading"]') as HTMLElement | null;
    return {
      row: box(row),
      badge: box(badge),
      name: box(name),
      role: box(role),
      heading: box(heading),
      nameText: name?.textContent?.trim(),
      roleText: role?.textContent?.trim(),
      nameFont: name ? getComputedStyle(name).font : null,
    };
  });

  console.log(JSON.stringify(r, null, 2));

  const badge = r.badge!;
  const name = r.name!;
  const role = r.role!;
  const row = r.row!;
  const heading = r.heading!;

  const gap = name.left - badge.right;
  const textBlockCenter = (name.top + role.bottom) / 2;
  const badgeCenter = (badge.top + badge.bottom) / 2;
  const centerOffset = Math.abs(textBlockCenter - badgeCenter);
  const headingGap = heading.top - row.bottom;
  const alignOffset = row.left - heading.left;

  if (gap < 10 || gap > 14) throw new Error(`badge-text gap off: ${gap}px`);
  if (centerOffset > 2) throw new Error(`not vertically centered vs text block: ${centerOffset}px`);
  if (headingGap < 16 || headingGap > 28) throw new Error(`row-to-heading margin off: ${headingGap}px`);
  if (Math.abs(alignOffset) > 1) throw new Error(`not left-aligned with heading: ${alignOffset}px`);
  console.log(`gap=${gap}px centerOffset=${Math.round(centerOffset)}px headingGap=${headingGap}px alignOffset=${alignOffset}px`);

  await page.screenshot({ path: 'verify-brand-card.png' });
});
