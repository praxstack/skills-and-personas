// ptk Playwright runner: one browser per call (E12), all jobs from a JSON file.
// Usage: node shoot.mjs <jobs.json> <results.json>
// Every request that is not file:, data:, blob: or http://127.0.0.1 is aborted and recorded
// (the visual gate turns any recorded request into OutboundRequest, AC-3.6).
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname } from 'node:path';

const prefix = process.env.PTK_NODE_PREFIX;
if (!prefix) { console.error('PTK_NODE_PREFIX not set (run through ptk/node.py)'); process.exit(2); }
const require = createRequire(prefix + '/package.json');
const { chromium } = require('playwright');

const [jobsPath, outPath] = process.argv.slice(2);
const jobs = JSON.parse(readFileSync(jobsPath, 'utf8'));
const results = [];
const outbound = [];

const allowed = (u) => /^(file:|data:|blob:|about:)/.test(u) || /^https?:\/\/127\.0\.0\.1(:\d+)?\//.test(u);

const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });

async function newContext(job) {
  const ctx = await browser.newContext({
    viewport: { width: job.width || 1200, height: job.height || 900 },
    deviceScaleFactor: job.scale || 1,
    colorScheme: job.scheme || 'light',
    reducedMotion: job.reducedMotion || 'no-preference',
    javaScriptEnabled: job.js !== false,
  });
  await ctx.route('**/*', (route) => {
    const u = route.request().url();
    if (allowed(u)) return route.continue();
    outbound.push({ job: job.id, url: u });
    return route.abort('blockedbyclient');
  });
  return ctx;
}

// ---- in-page measurement (runs inside the page) ----
function measureSvg(opts) {
  const minPx = opts.minPx;
  const hex = (c) => {
    const m = c.match(/\d+(\.\d+)?/g); if (!m) return null;
    return m.slice(0, 3).map(Number);
  };
  const lum = (rgb) => {
    const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal;
  const scale = (opts.displayWidth || svg.getBoundingClientRect().width) / vb.width;
  const all = [...svg.querySelectorAll('*')];
  const rects = all.filter((e) => e.tagName === 'rect');
  const texts = all.filter((e) => e.tagName === 'text');
  const box = (el) => { const b = el.getBBox(); return { x: b.x, y: b.y, r: b.x + b.width, b: b.y + b.height }; };
  const problems = [];
  const contrast = [];
  const sizes = [];
  const fontsUsed = new Set();
  for (const t of texts) {
    const a = box(t);
    const cs = getComputedStyle(t);
    fontsUsed.add(cs.fontFamily);
    const px = parseFloat(cs.fontSize) * scale;
    sizes.push(px);
    if (px < minPx - 0.01) problems.push({ kind: 'min-size', text: t.textContent, px: +px.toFixed(2) });
    if (t.dataset.in) {
      const c = document.getElementById(t.dataset.in);
      if (c) {
        const cb = box(c);
        if (a.x < cb.x - 0.5 || a.r > cb.r + 0.5 || a.y < cb.y - 0.5 || a.b > cb.b + 0.5)
          problems.push({ kind: 'overflow', text: t.textContent, container: t.dataset.in,
                          text_box: [a.x, a.r, a.y, a.b].map((v) => +v.toFixed(1)), box: [cb.x, cb.r, cb.y, cb.b] });
      }
    }
    if (a.r > vb.width + 0.5 || a.x < -0.5) problems.push({ kind: 'overflow', text: t.textContent, container: 'svg' });
    // background: last rect before this text in document order that contains its centre
    const cx = (a.x + a.r) / 2, cy = (a.y + a.b) / 2;
    let bg = null;
    for (const r of rects) {
      if (r.compareDocumentPosition(t) & Node.DOCUMENT_POSITION_FOLLOWING) {
        const rb = box(r);
        if (cx >= rb.x && cx <= rb.r && cy >= rb.y && cy <= rb.b && getComputedStyle(r).fill !== 'none') bg = r;
      }
    }
    const fgs = new Set([cs.fill, ...[...t.querySelectorAll('tspan')].map((s) => getComputedStyle(s).fill)]);
    for (const fg of fgs) {
      const bgc = bg ? getComputedStyle(bg).fill : 'rgb(255,255,255)';
      const r = ratio(hex(fg), hex(bgc));
      contrast.push({ kind: 'text', text: t.textContent.slice(0, 40), fg, bg: bgc, ratio: +r.toFixed(2), min: 4.5 });
    }
  }
  for (let i = 0; i < texts.length; i++) {
    for (let j = i + 1; j < texts.length; j++) {
      const a = box(texts[i]), b = box(texts[j]);
      const ix = Math.min(a.r, b.r) - Math.max(a.x, b.x), iy = Math.min(a.b, b.b) - Math.max(a.y, b.y);
      if (ix > 1 && iy > 1) problems.push({ kind: 'overlap', a: texts[i].textContent, b: texts[j].textContent });
    }
  }
  // rules and borders: stroke vs the paper/card under them
  const paper = getComputedStyle(document.getElementById('frame-bg')).fill;
  for (const el of all.filter((e) => (e.tagName === 'rect' && e.getAttribute('stroke')) || e.dataset.role === 'rule')) {
    const st = getComputedStyle(el).stroke;
    const under = el.tagName === 'rect' ? paper : paper;
    contrast.push({ kind: 'rule', el: el.id || el.tagName, fg: st, bg: under, ratio: +ratio(hex(st), hex(under)).toFixed(2), min: 3 });
  }
  const title = document.querySelector('title')?.textContent || '';
  const desc = document.querySelector('desc')?.textContent || '';
  const source = !!document.querySelector('[data-role="source"]');
  return { scale, problems, contrast, minPx: Math.min(...sizes), fonts: [...fontsUsed], title, desc, source,
           fontsReady: document.fonts.status, loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family) };
}

function measurePage(minPx) {
  const problems = [];
  const sw = document.documentElement.scrollWidth, iw = window.innerWidth;
  if (sw > iw + 1) problems.push({ kind: 'page-overflow', scrollWidth: sw, innerWidth: iw });
  for (const el of document.querySelectorAll('body *')) {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') continue;
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height) continue;
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (own && parseFloat(st.fontSize) < minPx - 0.01 && !el.closest('[aria-hidden="true"]'))
      problems.push({ kind: 'min-size', text: el.textContent.trim().slice(0, 40), px: parseFloat(st.fontSize) });
    if (own && el.scrollWidth > el.clientWidth + 1 && st.overflowX !== 'auto' && st.overflowX !== 'scroll' && el.clientWidth > 0)
      problems.push({ kind: 'overflow', text: el.textContent.trim().slice(0, 40), scrollWidth: el.scrollWidth, clientWidth: el.clientWidth });
    if (r.right > iw + 1 && !el.closest('[data-scroll]')) problems.push({ kind: 'offscreen', tag: el.tagName, id: el.id, right: r.right });
  }
  return { problems, fonts: [...new Set([...document.querySelectorAll('body *')].map((e) => getComputedStyle(e).fontFamily))],
           loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family) };
}

for (const job of jobs) {
  const res = { id: job.id, type: job.type };
  try {
    const ctx = await newContext(job);
    const page = await ctx.newPage();
    const consoleMsgs = [];
    page.on('console', (m) => consoleMsgs.push(`${m.type()}: ${m.text()}`));
    page.on('pageerror', (e) => consoleMsgs.push(`pageerror: ${e.message}`));
    await page.goto(job.url, { waitUntil: 'load' });
    await page.evaluate(() => document.fonts.ready);
    if (job.type === 'png') {
      mkdirSync(dirname(job.out), { recursive: true });
      await page.locator('svg').screenshot({ path: job.out, omitBackground: false });
    } else if (job.type === 'svg-measure') {
      res.measure = await page.evaluate(measureSvg, { minPx: job.minPx || 11, displayWidth: job.displayWidth });
    } else if (job.type === 'shot') {
      if (job.shot) { mkdirSync(dirname(job.shot), { recursive: true }); await page.screenshot({ path: job.shot, fullPage: true }); }
      res.measure = await page.evaluate(measurePage, job.minPx || 11);
      res.imagesLoaded = await page.evaluate(() => [...document.images].every((i) => i.complete && i.naturalWidth > 0));
    } else if (job.type === 'ocr-crops') {
      // Elements sharing data-ocr-group are cropped together (a column of line numbers reads far more
      // reliably than single glyphs); the rest are cropped one by one.
      mkdirSync(job.outDir, { recursive: true });
      const items = await page.evaluate(() => [...document.querySelectorAll('[data-ocr]')].map((e) => {
        const b = e.getBoundingClientRect();
        return { expected: e.getAttribute('data-ocr'), group: e.getAttribute('data-ocr-group') || '', x: b.x, y: b.y, w: b.width, h: b.height };
      }));
      const groups = new Map();
      const singles = [];
      for (const it of items) { if (it.group) { if (!groups.has(it.group)) groups.set(it.group, []); groups.get(it.group).push(it); } else singles.push(it); }
      const units = singles.map((it) => ({ expected: it.expected, box: it, multi: false }));
      for (const [name, its] of groups) {
        its.sort((a, b) => a.y - b.y);
        const x0 = Math.min(...its.map((i) => i.x)), y0 = Math.min(...its.map((i) => i.y));
        const x1 = Math.max(...its.map((i) => i.x + i.w)), y1 = Math.max(...its.map((i) => i.y + i.h));
        units.push({ expected: its.map((i) => i.expected).join('\n'), box: { x: x0, y: y0, w: x1 - x0, h: y1 - y0 }, multi: true, group: name });
      }
      res.crops = [];
      let k = 0;
      for (const u of units) {
        const b = u.box;
        const path = `${job.outDir}/crop-${String(k++).padStart(3, '0')}.png`;
        await page.screenshot({ path, fullPage: true, clip: { x: Math.max(0, b.x - 8), y: Math.max(0, b.y - 8), width: b.w + 16, height: b.h + 16 } });
        res.crops.push({ path, expected: u.expected, multi: u.multi, group: u.group || null });
      }
    } else if (job.type === 'script') {
      // job.steps: [{eval: "js expression", as: "name"}, {wait: ms}, {shot: path}]
      res.values = {};
      for (const step of job.steps) {
        if (step.wait) await page.waitForTimeout(step.wait);
        if (step.waitFor) await page.waitForFunction(step.waitFor, null, { timeout: step.timeout || 30000 });
        if (step.eval) res.values[step.as || step.eval] = await page.evaluate(step.eval);
        if (step.press) await page.keyboard.press(step.press);
        if (step.click) await page.click(step.click);
        if (step.shot) { mkdirSync(dirname(step.shot), { recursive: true }); await page.screenshot({ path: step.shot, fullPage: !!step.full }); }
      }
    }
    res.console = consoleMsgs;
    res.ok = true;
    await ctx.close();
  } catch (e) {
    res.ok = false;
    res.error = String(e && e.stack || e);
  }
  results.push(res);
}
await browser.close();
writeFileSync(outPath, JSON.stringify({ results, outbound }, null, 1));
