// Покадровый рендер сцены в PNG + сборка видео через ffmpeg.
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
const getArg = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };

const FPS   = parseFloat(getArg('fps', '60'));
const SCALE = parseFloat(getArg('scale', '3'));
const OUTDIR = getArg('frames', '/tmp/frames');
const PREVIEW = getArg('preview', null); // "0.5,2.6,..." -> отдельные кадры

(async () => {
  fs.mkdirSync(OUTDIR, { recursive: true });
  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
  const page = await browser.newPage({
    viewport: { width: 400, height: 600 },
    deviceScaleFactor: SCALE,
  });
  await page.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await page.evaluate(() => document.fonts.ready);
  const DUR = await page.evaluate(() => window.__DUR);

  if (PREVIEW) {
    for (const s of PREVIEW.split(',')) {
      const t = parseFloat(s);
      await page.evaluate(tt => window.__render(tt), t);
      await page.screenshot({ path: path.join(OUTDIR, `t${s.replace('.', '_')}.png`) });
    }
    console.log('preview frames ->', OUTDIR);
    await browser.close();
    return;
  }

  const total = Math.round(DUR * FPS);
  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = i / FPS;
    await page.evaluate(tt => window.__render(tt), t);
    await page.screenshot({ path: path.join(OUTDIR, String(i).padStart(5, '0') + '.png') });
    if (i % 60 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${i}/${total}  ${el.toFixed(0)}s  eta ${(el / Math.max(i, 1) * (total - i)).toFixed(0)}s`);
    }
  }
  console.log(`done ${total} frames in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await browser.close();
})();
