import { test } from '@playwright/test';

test('verify brand panel vertical centering + footer pinned', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.goto('/login', { waitUntil: 'networkidle' });
  await page.waitForTimeout(5500);

  const r = await page.evaluate(() => {
    const box = (el: Element | null) => {
      if (!el) return null;
      const r = el.getBoundingClientRect();
      return { top: Math.round(r.top), bottom: Math.round(r.bottom), height: Math.round(r.height) };
    };
    const panel = document.querySelector('[class*="brandPanel"]') as HTMLElement | null;
    const content = panel?.querySelector('[class*="brandPanelContent"]') as HTMLElement | null;
    const header = panel?.querySelector('[class*="brandHeader"]') as HTMLElement | null;
    const list = panel?.querySelector('[class*="featureList"]') as HTMLElement | null;
    const footer = panel?.querySelector('[class*="brandFooter"]') as HTMLElement | null;
    return {
      viewport: window.innerHeight,
      panel: box(panel),
      content: box(content),
      header: box(header),
      list: box(list),
      footer: box(footer),
      footerText: footer?.textContent?.trim(),
      gapHeaderList: list && header ? list.getBoundingClientRect().top - header.getBoundingClientRect().bottom : null,
    };
  });

  console.log(JSON.stringify(r, null, 2));

  const headerTop = r.header?.top ?? 0;
  const footerTop = r.footer?.top ?? 0;
  const footerBottom = r.footer?.bottom ?? 0;
  const panelBottom = r.panel?.bottom ?? 0;
  const contentTop = r.content?.top ?? 0;
  const contentBottom = r.content?.bottom ?? 0;
  const listBottom = r.list?.bottom ?? 0;
  const unitTop = headerTop;
  const unitBottom = listBottom;
  const unitCenter = (unitTop + unitBottom) / 2;
  const contentCenter = (contentTop + contentBottom) / 2;
  const centerOffset = unitCenter - contentCenter;
  const footerGap = panelBottom - footerBottom;
  const overlap = listBottom - footerTop;

  if (overlap > 0) throw new Error(`Footer overlaps feature list: overlap=${overlap}px`);
  if (Math.abs(centerOffset) > 2) throw new Error(`Unit not centered: offset=${centerOffset}px`);
  if (footerGap > 60) throw new Error(`Footer not pinned near bottom: gap=${footerGap}px`);
  console.log(`unitCenter=${Math.round(unitCenter)} vs contentCenter=${Math.round(contentCenter)} (offset ${Math.round(centerOffset)}px)`);
  console.log(`footer pinned: ${footerGap}px above panel bottom, overlap=${overlap}px`);

  await page.screenshot({ path: 'verify-brand-center.png', fullPage: false });
});
