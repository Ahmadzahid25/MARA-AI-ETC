import { expect, test } from '@playwright/test';

const PURPLE = 'rgb(108, 92, 231)';

test.describe('applicant login UI', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/applicant', { waitUntil: 'networkidle' });
  });

  test('desktop 1440px: input boxes, purple button, link, gap', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const r = await page.evaluate(() => {
      const labels = Array.from(document.querySelectorAll('label'));
      const find = (text: string) => labels.find((l) => l.textContent?.includes(text)) as HTMLElement | null;
      const box = (label: HTMLElement | null) => label?.querySelector('div.flex.flex-row') as HTMLElement | null;
      const emailBox = box(find('Alamat e-mel'));
      const passBox = box(find('Kata laluan'));
      const submit = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Log masuk') as HTMLElement;
      const link = Array.from(document.querySelectorAll('a')).find((a) => a.textContent?.includes('Lupa kata laluan')) as HTMLElement | null;
      const cs = (el: HTMLElement) => { const s = getComputedStyle(el); const r = el.getBoundingClientRect(); return { top: r.top, bottom: r.bottom, h: r.height, w: r.width, bg: s.backgroundColor, borderColor: s.borderTopColor, radius: s.borderTopLeftRadius, color: s.color, fontSize: s.fontSize }; };
      const email = emailBox ? cs(emailBox) : null;
      const pass = passBox ? cs(passBox) : null;
      const card = document.querySelector('section') as HTMLElement;
      const cardR = card.getBoundingClientRect();
      return {
        htmlDark: document.documentElement.classList.contains('dark'),
        email, pass,
        submit: cs(submit),
        submitSpanColor: submit.querySelector('span') ? getComputedStyle(submit.querySelector('span') as HTMLElement).color : null,
        submitMarginTop: getComputedStyle(submit).marginTop,
        link: link ? cs(link) : null,
        linkBelowPass: link && passBox ? link.getBoundingClientRect().top - passBox.getBoundingClientRect().bottom : null,
        gapLinkToSubmit: link && passBox ? submit.getBoundingClientRect().top - link.getBoundingClientRect().bottom : null,
        cardLeft: cardR.left, cardRight: cardR.right, cardWidth: cardR.width, viewport: window.innerWidth,
        headerLinkFont: getComputedStyle(Array.from(document.querySelectorAll('a')).find((a) => a.textContent?.includes('Log masuk pegawai')) as HTMLElement).fontSize,
        mainLeft: (document.querySelector('main') as HTMLElement).getBoundingClientRect().left,
        mainRight: (document.querySelector('main') as HTMLElement).getBoundingClientRect().right,
      };
    });
    expect(r.email?.bg).toBe('rgba(255, 255, 255, 0.04)');
    expect(r.pass?.bg).toBe('rgba(255, 255, 255, 0.04)');
    expect(r.email?.h).toBeGreaterThanOrEqual(44);
    expect(r.email?.radius).toBe('8px');
    expect(r.submit.bg).toBe(PURPLE);
    expect(r.submit.h).toBeGreaterThanOrEqual(46);
    expect(r.submit.radius).toBe('8px');
    expect(r.submitSpanColor).toBe('rgb(255, 255, 255)');
    expect(r.submitMarginTop).toBe('24px');
    expect(r.link).not.toBeNull();
    expect(r.link!.fontSize).toBe('12px');
    expect(r.gapLinkToSubmit).toBe(24);
    expect(r.linkBelowPass).toBe(8);
    expect(r.cardWidth).toBeLessThanOrEqual(480);
    expect(Math.abs((r.cardLeft - r.mainLeft) - (r.mainRight - r.cardRight))).toBeLessThanOrEqual(1);
    expect(r.headerLinkFont).toBe('14px');
  });

  test('submit button hover darkens to #5B4BD6', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const submit = page.getByRole('button', { name: 'Log masuk', exact: true });
    await expect(submit).toBeVisible();
    await submit.hover();
    const bg = await submit.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(bg).toBe('rgb(91, 75, 214)');
  });

  test('sidebar active item is solid purple, inactive hover, gap 4px', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const active = page.getByRole('button', { name: 'Ringkasan' });
    const bg = await active.evaluate((el) => getComputedStyle(el).backgroundColor);
    const radius = await active.evaluate((el) => getComputedStyle(el).borderTopLeftRadius);
    const paddingTop = await active.evaluate((el) => getComputedStyle(el).paddingTop);
    expect(bg).toBe(PURPLE);
    expect(radius).toBe('8px');
    expect(paddingTop).toBe('10px');
    const inactive = page.getByRole('button', { name: 'Permohonan baharu' });
    await inactive.hover();
    const hoverBg = await inactive.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(hoverBg).not.toBe('rgba(0, 0, 0, 0)');
  });

  test('header: favicon logo in white rounded box, 13px officer link', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const logo = page.locator('header div.h-9.w-9').first();
    const logoBg = await logo.evaluate((el) => getComputedStyle(el).backgroundColor);
    const logoRadius = await logo.evaluate((el) => getComputedStyle(el).borderTopLeftRadius);
    expect(logoBg).toBe('rgb(255, 255, 255)');
    expect(logoRadius).toBe('8px');
    const img = logo.locator('img');
    await expect(img).toHaveAttribute('src', '/favicon.png');
    await expect(img).toHaveAttribute('alt', 'Logo MARA AI-ETC');
    const imgSize = await img.evaluate((el) => ({ w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height, naturalW: (el as HTMLImageElement).naturalWidth, naturalH: (el as HTMLImageElement).naturalHeight }));
    expect(imgSize.w).toBe(22);
    expect(imgSize.h).toBe(22);
    expect(imgSize.naturalW).toBeGreaterThan(0);
    expect(imgSize.naturalH).toBeGreaterThan(0);
    const boxSize = await logo.evaluate((el) => ({ w: el.getBoundingClientRect().width, h: el.getBoundingClientRect().height }));
    expect(boxSize.w).toBe(36);
    expect(boxSize.h).toBe(36);
    await expect(logo).not.toContainText('M');
    const link = page.getByRole('link', { name: 'Log masuk pegawai' });
    await expect(link).toBeVisible();
    await link.hover();
    await expect(link).toHaveCSS('text-decoration-line', 'underline');
  });

  test('mobile 375px: drawer instead of sidebar, card full width, no overflow', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    const r = await page.evaluate(() => {
      const card = document.querySelector('section') as HTMLElement;
      const cr = card.getBoundingClientRect();
      const aside = document.querySelector('aside');
      const overflowX = document.documentElement.scrollWidth - document.documentElement.clientWidth;
      const paddingLeft = getComputedStyle(card).paddingLeft;
      const link = Array.from(document.querySelectorAll('a')).find((a) => a.textContent?.includes('Log masuk pegawai')) as HTMLElement;
      return { cardW: cr.width, viewport: window.innerWidth, asideDisplay: aside ? getComputedStyle(aside).display : null, overflowX, paddingLeft, linkFont: getComputedStyle(link).fontSize };
    });
    expect(r.asideDisplay).toBe('none');
    expect(r.overflowX).toBeLessThanOrEqual(0);
    expect(r.cardW).toBeLessThanOrEqual(375 - 32);
    expect(r.paddingLeft).toBe('20px');
    expect(r.linkFont).toBe('13px');

    const hamburger = page.getByRole('button', { name: 'Buka menu' });
    await expect(hamburger).toBeVisible();
    await hamburger.click();
    const drawerLogo = page.locator('div.fixed img[src="/favicon.png"]').first();
    await expect(drawerLogo).toBeVisible();
    const drawerLogoLoaded = await drawerLogo.evaluate((el) => (el as HTMLImageElement).naturalWidth > 0);
    expect(drawerLogoLoaded).toBe(true);
    const drawerRingkasan = page.getByRole('button', { name: 'Ringkasan' });
    await expect(drawerRingkasan).toBeVisible();
    const bg = await drawerRingkasan.evaluate((el) => getComputedStyle(el).backgroundColor);
    expect(bg).toBe(PURPLE);
    await page.getByRole('button', { name: 'Tutup menu' }).click();
    await expect(drawerRingkasan).not.toBeVisible();
  });

  test('mobile 390px: no overflow, button/inputs keep min-height', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const overflowX = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    expect(overflowX).toBeLessThanOrEqual(0);
    const labels = page.locator('label');
    for (let i = 0; i < await labels.count(); i++) {
      const h = await labels.nth(i).locator('div.flex.flex-row').evaluate((el) => el.getBoundingClientRect().height);
      expect(h).toBeGreaterThanOrEqual(44);
    }
    const submit = page.getByRole('button', { name: 'Log masuk', exact: true });
    const h = await submit.evaluate((el) => el.getBoundingClientRect().height);
    expect(h).toBeGreaterThanOrEqual(46);
  });

  test('typeable: inputs accept text', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    const email = page.getByLabel('Alamat e-mel');
    const pass = page.getByLabel('Kata laluan');
    await email.fill('pemohon@example.com');
    await pass.fill('Secret123!');
    await expect(email).toHaveValue('pemohon@example.com');
    await expect(pass).toHaveValue('Secret123!');
  });
});
