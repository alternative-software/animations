// Покадровый рендер сцены. Кадры идут прямо в ffmpeg (без тысяч PNG на диске).
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const args = process.argv.slice(2);
const getArg = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 ? args[i + 1] : d; };

const FPS     = parseFloat(getArg('fps', '60'));
const SCALE   = parseFloat(getArg('scale', '3'));
const OUT     = getArg('out', null);            // путь к mp4 (режим конвейера)
const OUTDIR  = getArg('frames', null);         // либо папка с PNG
const PREVIEW = getArg('preview', null);        // "0.5,2.6,..." — отдельные кадры
const FROM    = parseFloat(getArg('from', '0'));
const TO      = parseFloat(getArg('to', '0')) || null;
const AUDIO   = getArg('audio', null);
const CRF     = getArg('crf', '17');

(async () => {
  const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
  const page = await browser.newPage({ viewport: { width: 400, height: 600 }, deviceScaleFactor: SCALE });
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  await page.goto('file://' + path.resolve(__dirname, 'scene.html'));
  await page.evaluate(() => document.fonts.ready);
  const DUR = TO || await page.evaluate(() => window.__DUR);

  if (PREVIEW) {
    const dir = OUTDIR || '/tmp/prev';
    fs.mkdirSync(dir, { recursive: true });
    for (const s of PREVIEW.split(',')) {
      const t = parseFloat(s);
      await page.evaluate(tt => window.__render(tt), t);
      await page.screenshot({ path: path.join(dir, `t${s.replace('.', '_')}.png`) });
    }
    console.log('preview ->', dir);
    await browser.close();
    return;
  }

  const total = Math.round((DUR - FROM) * FPS);
  let ff = null, dir = null;
  if (OUT) {
    const a = ['-y', '-f', 'image2pipe', '-framerate', String(FPS), '-i', '-'];
    if (AUDIO) a.push('-i', AUDIO, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-c:a', 'aac', '-b:a', '192k', '-shortest');
    a.push('-c:v', 'libx264', '-preset', 'medium', '-crf', CRF, '-pix_fmt', 'yuv420p', '-movflags', '+faststart', OUT);
    ff = spawn('ffmpeg', a, { stdio: ['pipe', 'inherit', 'inherit'] });
  } else {
    dir = OUTDIR || '/tmp/frames';
    fs.mkdirSync(dir, { recursive: true });
  }

  const t0 = Date.now();
  for (let i = 0; i < total; i++) {
    const t = FROM + i / FPS;
    await page.evaluate(tt => window.__render(tt), t);
    const buf = await page.screenshot({ type: 'png' });
    if (ff) {
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    } else {
      fs.writeFileSync(path.join(dir, String(i).padStart(5, '0') + '.png'), buf);
    }
    if (i % 120 === 0) {
      const el = (Date.now() - t0) / 1000;
      console.log(`${i}/${total}  ${el.toFixed(0)}s  eta ${(el / Math.max(i, 1) * (total - i)).toFixed(0)}s`);
    }
  }
  console.log(`frames done: ${total} in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  await browser.close();
  if (ff) { ff.stdin.end(); await new Promise(r => ff.on('close', r)); console.log('video ->', OUT); }
})();
