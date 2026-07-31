import { test } from '@playwright/test'

test('scan video frames for dark-teal top strips', async ({ page }) => {
  await page.goto('/login')
  const video = page.locator('video')
  await video.waitFor({ state: 'visible', timeout: 10000 })

  const scan = async (t: number) => {
    return page.evaluate(async (time) => {
      const v = document.querySelector('video') as HTMLVideoElement
      await new Promise<void>((resolve) => {
        const onSeek = () => resolve()
        v.onseeked = onSeek
        v.currentTime = time
        setTimeout(resolve, 2500)
      })
      const w = v.videoWidth
      const h = v.videoHeight
      const canvas = document.createElement('canvas')
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d')!
      ctx.drawImage(v, 0, 0, w, h)
      const img = ctx.getImageData(0, 0, w, h).data

      const bands: string[] = []
      for (let y = 0; y < h; y += 6) {
        const colors: Record<string, number> = {}
        for (let x = 0; x < w; x += 6) {
          const i = (y * w + x) * 4
          const key = `${img[i]},${img[i + 1]},${img[i + 2]}`
          colors[key] = (colors[key] ?? 0) + 1
        }
        const sorted = Object.entries(colors).sort((a, b) => b[1] - a[1])
        const top = sorted.slice(0, 2).map(([k]) => k).join('|')
        const tealCount = sorted
          .filter(([k]) => {
            const [r, g, b] = k.split(',').map(Number)
            return r + g + b < 200 && g > b
          })
          .reduce((s, [, n]) => s + n, 0)
        bands.push(`y=${String(y).padStart(3)} top2=[${top}] tealDark=${tealCount}`)
      }
      return { t: time, w, h, bands }
    }, t)
  }

  for (const t of [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5]) {
    const r = await scan(t)
    const nonGray = r.bands.filter((b) => !b.includes('tealDark=0') || !b.includes('244,244,247'))
    console.log(`===== t=${t}s =====`)
    console.log(nonGray.slice(0, 40).join('\n'))
  }
})
