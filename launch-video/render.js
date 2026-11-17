// Renders index.html frame by frame with headless Chromium.
//   node render.js stills 1,5,9.5        -> out/still-*.png (quick visual check)
//   node render.js frames [fps] [workers] -> out/frames/f-000000.jpg ...
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
const url = 'file://' + path.join(__dirname, 'index.html');
const out = path.join(__dirname, 'out');

async function page(browser, scale = 1) {
  const p = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: scale });
  p.on('pageerror', e => { console.error('PAGE ERROR', e.message); process.exitCode = 1; });
  await p.goto(url);
  await p.waitForFunction('window.READY === true');
  return p;
}

(async () => {
  const [mode, a, b] = process.argv.slice(2);
  const browser = await chromium.launch();
  if (mode === 'stills') {
    fs.mkdirSync(out, { recursive: true });
    const p = await page(browser, 0.5);
    for (const t of a.split(',').map(Number)) {
      await p.evaluate(t => window.seek(t), t);
      await p.screenshot({ path: path.join(out, `still-${t.toFixed(2).padStart(5, '0')}.png`) });
    }
  } else {
    const fps = +a || 60, workers = +b || 4;
    const dir = path.join(out, 'frames');
    fs.rmSync(dir, { recursive: true, force: true }); fs.mkdirSync(dir, { recursive: true });
    const p0 = await page(browser); const dur = await p0.evaluate('window.DUR'); await p0.close();
    const total = Math.round(dur * fps), per = Math.ceil(total / workers);
    let done = 0; const start = Date.now();
    await Promise.all([...Array(workers)].map(async (_, w) => {
      const p = await page(browser);
      for (let f = w * per; f < Math.min(total, (w + 1) * per); f++) {
        await p.evaluate(t => window.seek(t), f / fps);
        await p.screenshot({ path: path.join(dir, `f-${String(f).padStart(6, '0')}.jpg`), type: 'jpeg', quality: 96 });
        if (++done % 300 === 0) console.log(`${done}/${total} frames, ${((Date.now() - start) / 1000).toFixed(0)}s`);
      }
    }));
    console.log(`done: ${total} frames`);
  }
  await browser.close();
})();
