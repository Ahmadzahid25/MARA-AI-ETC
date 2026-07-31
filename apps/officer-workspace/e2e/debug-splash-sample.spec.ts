import { test } from '@playwright/test';

test('sample splash video background colors via canvas', async ({ page }) => {
  await page.goto('http://localhost:4000/mara-ai-etc.mp4', { waitUntil: 'load' });
  const r = await page.evaluate(async () => {
    const v = document.createElement('video');
    v.src = '/mara-ai-etc.mp4';
    v.muted = true;
    v.crossOrigin = 'anonymous';
    await v.play();
    await new Promise<void>((res) => {
      if (v.currentTime >= 0.5) res();
      else v.addEventListener('seeked', () => res());
      v.currentTime = 0.5;
      setTimeout(res, 3000);
    });
    const c = document.createElement('canvas');
    c.width = v.videoWidth;
    c.height = v.videoHeight;
    const ctx = c.getContext('2d')!;
    ctx.drawImage(v, 0, 0, c.width, c.height);
    const pts: Array<[number, number, string]> = [
      [10, 10, 'top-left'],
      [640, 10, 'top-mid'],
      [1270, 10, 'top-right'],
      [10, 360, 'mid-left'],
      [640, 360, 'mid-center'],
      [1270, 360, 'mid-right'],
      [10, 710, 'bottom-left'],
      [640, 710, 'bottom-mid'],
      [1270, 710, 'bottom-right'],
    ];
    const out: Array<{ name: string; rgb: string; hex: string }> = [];
    for (const [x, y, name] of pts) {
      const d = ctx.getImageData(x, y, 1, 1).data;
      const hex = '#' + [d[0], d[1], d[2]].map((n) => n.toString(16).padStart(2, '0')).join('');
      out.push({ name, rgb: `rgb(${d[0]},${d[1]},${d[2]})`, hex });
    }
    return { videoSize: { w: v.videoWidth, h: v.videoHeight }, samples: out };
  });
  console.log(JSON.stringify(r, null, 2));
  for (const s of r.samples) console.log(`${s.name.padEnd(13)} ${s.rgb}  ${s.hex}`);
});
