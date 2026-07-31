import { test } from '@playwright/test';

test('inspect applicant login input/button rendering', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto('/applicant', { waitUntil: 'networkidle' });
  const r = await page.evaluate(() => {
    const labels = Array.from(document.querySelectorAll('label'));
    const find = (text: string) => labels.find((l) => l.textContent?.includes(text)) as HTMLElement | null;
    const emailLabel = find('Alamat e-mel');
    const passLabel = find('Kata laluan');
    const wrap = (label: HTMLElement | null) => label?.querySelector('div.flex.flex-row') as HTMLElement | null;
    const cs = (el: HTMLElement | null) => {
      if (!el) return null;
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return { tag: el.tagName, rect: { x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height) }, bg: s.backgroundColor, borderTop: s.borderTopWidth + ' ' + s.borderTopStyle + ' ' + s.borderTopColor, color: s.color, display: s.display, visibility: s.visibility, opacity: s.opacity };
    };
    const emailWrap = wrap(emailLabel);
    const passWrap = wrap(passLabel);
    const input = emailWrap?.querySelector('input');
    const submit = Array.from(document.querySelectorAll('button')).find((b) => b.textContent?.trim().includes('Log masuk')) as HTMLElement | null;
    return {
      htmlDark: document.documentElement.classList.contains('dark'),
      emailWrap: cs(emailWrap),
      passWrap: cs(passWrap),
      input: cs(input as HTMLElement),
      submit: cs(submit),
      submitText: submit?.textContent?.trim(),
      submitClasses: submit?.className,
    };
  });
  console.log(JSON.stringify(r, null, 2));
  await page.screenshot({ path: 'applicant-login-inspect.png' });
});
