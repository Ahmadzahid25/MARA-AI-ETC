import { test } from '@playwright/test';

async function splashInspect(page: import('@playwright/test').Page) {
  await page.goto('/login', { waitUntil: 'networkidle' });
  await page.waitForSelector('video', { timeout: 8000 });
  await page.waitForTimeout(1200);
  return page.evaluate(() => {
    const v = document.querySelector('video') as HTMLVideoElement | null;
    const overlay = document.querySelector('[class*="splashOverlay"]') as HTMLElement | null;
    if (!v || !overlay) return { error: 'splash not present' };
    const vr = v.getBoundingClientRect();
    const ovr = overlay.getBoundingClientRect();
    const W = window.innerWidth;
    const H = window.innerHeight;
    const c = document.createElement('canvas');
    c.width = W;
    c.height = H;
    const ctx = c.getContext('2d')!;
    const overlayBg = getComputedStyle(overlay).backgroundColor;
    ctx.fillStyle = overlayBg;
    ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(v, vr.left, vr.top, vr.width, vr.height);
    const sample = (x: number, y: number) => {
      const d = ctx.getImageData(x, y, 1, 1).data;
      return { x, y, rgb: `rgb(${d[0]},${d[1]},${d[2]})`, hex: '#' + [d[0], d[1], d[2]].map((n) => n.toString(16).padStart(2, '0')).join('') };
    };
    const midX = Math.floor(W / 2);
    const midY = Math.floor(H / 2);
    const hasLeft = vr.left > 10;
    const hasRight = vr.left + vr.width < W - 10;
    const hasTop = vr.top > 10;
    const hasBottom = vr.top + vr.height < H - 10;
    const skip = overlay.querySelector('button') as HTMLElement | null;
    const skipRect = skip ? skip.getBoundingClientRect() : null;
    return {
      viewport: { w: W, h: H },
      videoRect: { left: Math.round(vr.left), top: Math.round(vr.top), w: Math.round(vr.width), h: Math.round(vr.height) },
      videoFillsViewport: vr.left <= 0.5 && vr.top <= 0.5 && vr.right >= W - 0.5 && vr.bottom >= H - 0.5,
      overlayBg,
      bands: {
        left: hasLeft ? sample(10, midY) : null,
        right: hasRight ? sample(W - 10, midY) : null,
        top: hasTop ? sample(midX, 10) : null,
        bottom: hasBottom ? sample(midX, H - 10) : null,
      },
      videoCorners: {
        topLeft: sample(Math.ceil(vr.left) + 4, Math.ceil(vr.top) + 4),
        topRight: sample(Math.floor(vr.right) - 4, Math.ceil(vr.top) + 4),
        bottomLeft: sample(Math.ceil(vr.left) + 4, Math.floor(vr.bottom) - 4),
        bottomRight: sample(Math.floor(vr.right) - 4, Math.floor(vr.bottom) - 4),
      },
      skip: skipRect ? { w: Math.round(skipRect.width), h: Math.round(skipRect.height), bottom: Math.round(skipRect.bottom), right: Math.round(skipRect.right) } : null,
    };
  });
}

function delta(a: { rgb: string }, b: { rgb: string }) {
  const pa = a.rgb.match(/\d+/g)!.map(Number);
  const pb = b.rgb.match(/\d+/g)!.map(Number);
  return Math.max(...pa.map((n, i) => Math.abs(n - pb[i])));
}

function assertContainNoCrop(r: any, label: string) {
  const vr = r.videoRect;
  const ratio = vr.w / vr.h;
  const target = 1280 / 720;
  if (Math.abs(ratio - target) > 0.05) throw new Error(`${label}: video cropped/not 16:9 (ratio ${ratio.toFixed(3)} vs ${target.toFixed(3)})`);
  if (vr.left < -0.5 || vr.top < -0.5 || vr.left + vr.w > r.viewport.w + 0.5 || vr.top + vr.h > r.viewport.h + 0.5)
    throw new Error(`${label}: video extends beyond viewport: ${JSON.stringify(vr)}`);
  let maxD = 0;
  const corners: Record<string, string[]> = {
    left: ['topLeft', 'bottomLeft'],
    right: ['topRight', 'bottomRight'],
    top: ['topLeft', 'topRight'],
    bottom: ['bottomLeft', 'bottomRight'],
  };
  const present: string[] = [];
  for (const s of Object.keys(corners)) {
    const band = r.bands[s];
    if (!band) continue;
    present.push(s);
    for (const ck of corners[s]) maxD = Math.max(maxD, delta(band, r.videoCorners[ck]));
  }
  console.log(`${label}: ratio=${ratio.toFixed(3)} bands=${present.join(',')} max band-vs-corner delta=${maxD}`);
  if (maxD > 10) throw new Error(`${label}: visible seam, delta=${maxD}`);
  return vr;
}

test.describe('splash contain + seamless letterbox', () => {
  test('desktop ultrawide 1920x720', async ({ page }) => {
    await page.setViewportSize({ width: 1920, height: 720 });
    const r = await splashInspect(page);
    console.log('DESKTOP', JSON.stringify(r, null, 2));
    assertContainNoCrop(r, 'DESKTOP');
  });

  test('mobile portrait 375x667', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    const r = await splashInspect(page);
    console.log('MOBILE', JSON.stringify(r, null, 2));
    const vr = assertContainNoCrop(r, 'MOBILE');
    if (r.skip && r.skip.h < 44) throw new Error(`skip tap target too small: ${r.skip.h}px`);
    if (r.skip && r.skip.w < 44) throw new Error(`skip tap target too narrow: ${r.skip.w}px`);
    if (r.skip && r.skip.bottom > r.viewport.h - 20) throw new Error(`skip flush bottom edge: ${r.skip.bottom}`);
    if (r.skip && r.skip.right > r.viewport.w - 20) throw new Error(`skip flush right edge: ${r.skip.right}`);
    console.log(`MOBILE: video top=${vr.top} bottom=${vr.top + vr.h} (letterbox top/bottom blended)`);
  });

  test('mobile landscape 667x375', async ({ page }) => {
    await page.setViewportSize({ width: 667, height: 375 });
    const r = await splashInspect(page);
    console.log('MOBILE-LANDSCAPE', JSON.stringify(r, null, 2));
    assertContainNoCrop(r, 'MOBILE-LANDSCAPE');
  });

  test('tablet 769x1024', async ({ page }) => {
    await page.setViewportSize({ width: 769, height: 1024 });
    const r = await splashInspect(page);
    console.log('TABLET', JSON.stringify(r, null, 2));
    assertContainNoCrop(r, 'TABLET');
  });
});
