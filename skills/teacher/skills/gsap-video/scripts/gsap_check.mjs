#!/usr/bin/env node
// gsap_check.mjs: load a GSAP film page in headless Chromium and lint it before any still or render.
//
// Reports (exit 1 on errors, 0 with warnings):
//   errors    page errors, console errors, a build failure, window.TOTAL missing, timing.js without a hash
//   warnings  overlapping tweens on one element+property (the cause of single-frame flicker), a timeline
//             longer than TIMING.total, and a layout audit at every line (65% into its voice) and at every
//             comic burst and stamp (K.moments):
//             text off-frame, text outside the 96 px safe area, text in the caption band, world text the
//             camera shrinks below 26 px (the quality bar's floor), panels or labels overlapping each other.
//             And at every chapter card (K.cardWindows): anything in screen space (panels, notes, bursts, the
//             caption, the lower third) or any world-space text (graph labels, decoder) still or already visible
//             under the slab while it is up.
//           Also prints every burst/stamp time (K.moments) as a ready --stills list, since bursts last ~1 s and
//           line stills usually miss them. A decorative screen-space element that is meant to span the frame
//           (a full-frame SVG, a mascot layer) can opt out of the layout audit with data-qa="skip".
// Usage: node gsap_check.mjs --page source/index.html [--at lines|chapters|12.5,40] [--quiet]
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { resolveUnder, contentType } from './servepath.mjs';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d; };
const PAGE = path.resolve(opt('page', 'source/index.html'));
const ROOT = path.dirname(PAGE);
const AT = opt('at', 'lines');
const QUIET = argv.includes('--quiet');

async function loadChromium() {
  for (const b of [process.cwd(), ROOT]) for (const name of ['playwright-core', 'playwright']) {
    try { const req = createRequire(path.join(b, 'x.js')); const m = await import(pathToFileURL(req.resolve(name)).href); if (m.chromium || m.default?.chromium) return m.chromium || m.default.chromium; } catch { /* next */ }
  }
  for (const p of ['/opt/node22/lib/node_modules/playwright/index.mjs', '/usr/local/lib/node_modules/playwright/index.mjs', '/usr/lib/node_modules/playwright/index.mjs'])
    if (fs.existsSync(p)) { const m = await import(pathToFileURL(p).href); return m.chromium || m.default.chromium; }
  throw new Error('Playwright not found: npm i -D playwright-core (in source/)');
}
function chromiumPath() {
  if (process.env.CHROMIUM || process.env.CHROME) return process.env.CHROMIUM || process.env.CHROME;
  const c = ['/opt/pw-browsers/chromium'];
  try { for (const d of fs.readdirSync('/opt/pw-browsers')) if (/^chromium-\d+$/.test(d)) c.push(`/opt/pw-browsers/${d}/chrome-linux/chrome`); } catch { /* none */ }
  c.push('/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome');
  return c.find((p) => fs.existsSync(p));
}
const srv = await new Promise((res) => {
  const s = http.createServer((req, rsp) => {
    if (req.url.startsWith('/favicon')) { rsp.writeHead(204); rsp.end(); return; }
    const p = resolveUnder(ROOT, req.url);  // only real files inside ROOT (symlinks resolved on both sides)
    if (!p) { rsp.writeHead(404); rsp.end(); return; }
    rsp.writeHead(200, { 'Content-Type': contentType(p) });  // servepath.mjs: the renderer's table
    fs.createReadStream(p).pipe(rsp);
  });
  s.listen(0, '127.0.0.1', () => res(s));
});
const chromium = await loadChromium();
const browser = await chromium.launch({ executablePath: chromiumPath(), args: ['--no-sandbox', '--font-render-hinting=none'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
const errors = [], warnings = [];
page.on('pageerror', (e) => errors.push(`page error: ${e.message}`));
page.on('console', (m) => { if (m.type() === 'error') errors.push(`console: ${m.text()}`); });
page.on('requestfailed', (r) => errors.push(`failed to load ${r.url()}`));
page.on('response', (r) => { if (r.status() >= 400 && !r.url().includes('narration.wav')) errors.push(`HTTP ${r.status()} ${r.url()}`); });
await page.goto(`http://127.0.0.1:${srv.address().port}/${path.basename(PAGE)}?render=1`, { waitUntil: 'load' });
let info = null;
try {
  await page.waitForFunction(() => window.READY !== undefined, null, { timeout: 30000 });
  await page.evaluate(async () => { await window.READY; });
  info = await page.evaluate(() => ({
    total: window.TOTAL, dur: window.K.tl.duration(), hash: window.TIMING.hash, warnings: window.K.warnings,
    lines: window.K.lines.map((l) => ({ id: l.id, t: l.voiceAt + 0.65 * l.voiceDur, ch: l.chapter })),
    moments: (window.K.moments || []).filter((m) => m.t < window.TOTAL),
    // 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
    // previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
    chapters: window.TIMING.chapters.map((c) => {
      const t = c.start + 0.45 * (c.end - c.start), l = window.TIMING.lines.find((x) => Math.abs(t - x.voiceAt) < 0.3);
      const first = l && window.TIMING.lines.find((x) => x.chapter === l.chapter) === l;
      return { id: `ch${c.n}`, t: !l ? t : first ? l.voiceAt + 0.4 : l.voiceAt - 0.35 };
    }),
  }));
} catch (e) {
  errors.push(`the film did not build: ${e.message.split('\n')[0]}`);
}
if (info) {
  if (!(info.total > 0)) errors.push('window.TOTAL is missing or zero');
  if (!info.hash) errors.push('timing.js has no hash: emit it with voice.py --emit source/timing.js');
  warnings.push(...info.warnings);
  // lines: each line 65% into its voice, plus every burst/stamp at full size (K.moments)
  const times = AT === 'lines' ? [...info.lines, ...info.moments].sort((a, b) => a.t - b.t)
    : AT === 'chapters' ? info.chapters : AT.split(',').map((x) => ({ id: `t${x}`, t: +x }));
  // prime forward so tweens record their start values the way playback would
  for (let x = 0, k = 0; k < times.length; k++) {
    const t = times[k].t;
    await page.evaluate(async ({ from, to }) => { for (let s = from; s < to; s += 0.25) await window.renderFrame(s); await window.renderFrame(to); }, { from: x, to: t });
    x = t;
    const found = await page.evaluate(() => {
      const vis = (el) => {
        let o = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement || e.parentNode) {
          const cs = getComputedStyle(e);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          o *= +cs.opacity;
        }
        return o;
      };
      const r4 = (r) => ({ x: Math.round(r.left), y: Math.round(r.top), r: Math.round(r.right), b: Math.round(r.bottom) });
      const items = [];
      // screen-space components: each direct child of #ui / #cards / #hud is one block; captions separately
      for (const id of ['ui', 'cards', 'hud']) for (const el of document.getElementById(id).children) {
        if (vis(el) < 0.35 || !el.textContent.trim()) continue;
        if (el.matches('svg.tree, [data-qa="skip"]')) continue;
        if (el.matches('.chap')) continue; // the chapter slab is full-height on purpose
        const r = el.getBoundingClientRect();
        if (r.width < 2) continue;
        items.push({ kind: id, name: (el.className && String(el.className)) || el.tagName, ...r4(r), text: el.textContent.trim().slice(0, 40) });
      }
      // comic bursts and stamps (#fx): a burst is measured by its star, not its padded box
      for (const el of document.getElementById('fx').children) {
        if (vis(el) < 0.35 || !el.textContent.trim()) continue;
        const shape = el.matches('.callout') ? el.querySelectorAll('polygon')[1] : el;
        const r = shape.getBoundingClientRect();
        if (r.width < 2) continue;
        items.push({ kind: 'fx', name: String(el.className), ...r4(r), text: el.textContent.trim().slice(0, 40) });
      }
      const cap = document.querySelector('#caps .cap');
      if (cap && vis(cap) > 0.35) items.push({ kind: 'caption', name: 'caption', ...r4(cap.getBoundingClientRect()), text: cap.textContent.slice(0, 40) });
      // world-space text: SVG text in the scene (labels, weights, badges, decoder lines)
      for (const el of document.querySelectorAll('#world text')) {
        if (vis(el) < 0.35 || !el.textContent.trim()) continue;
        const r = el.getBoundingClientRect();
        if (r.width < 2) continue;
        const fs = Math.round(parseFloat(getComputedStyle(el).fontSize) * Math.abs(el.getScreenCTM().a));
        items.push({ kind: 'world', name: el.closest('[data-k]')?.getAttribute('data-k') || 'text', ...r4(r), fs, text: el.textContent.trim().slice(0, 40) });
      }
      return items;
    });
    const where = `${times[k].id} @ ${t.toFixed(2)}s`;
    const SAFE = 96, BAND = 900;
    for (const it of found) {
      if (it.x < 0 || it.y < 0 || it.r > 1920 || it.b > 1080) warnings.push(`${where}: ${it.kind} "${it.text}" runs off the frame (${it.x},${it.y})-(${it.r},${it.b})`);
      else if (it.kind !== 'caption' && (it.x < SAFE - 2 || it.y < SAFE - 2 || it.r > 1920 - SAFE + 2)) warnings.push(`${where}: ${it.kind} "${it.text}" is outside the 96 px safe area (${it.x},${it.y})-(${it.r},${it.b})`);
      if (it.fs && it.fs < 26) warnings.push(`${where}: world text "${it.text}" renders at ${it.fs}px, under the quality bar's 26 px (frame the subject larger or enlarge the text; legibility.py fails it)`);
      if (it.kind !== 'caption' && it.b > BAND + 2 && it.y < 1080) warnings.push(`${where}: ${it.kind} "${it.text}" reaches into the caption band (bottom ${it.b} > ${BAND})`);
    }
    const ov = (a, b) => Math.min(a.r, b.r) - Math.max(a.x, b.x) > 6 && Math.min(a.b, b.b) - Math.max(a.y, b.y) > 6;
    for (let i = 0; i < found.length; i++) for (let j = i + 1; j < found.length; j++) {
      const a = found[i], b = found[j];
      if (a.kind === 'world' && b.kind === 'world' && a.name === b.name) continue;
      if (/^chip /.test(a.name) || /^chip /.test(b.name)) continue; // chips are in flight on purpose
      if (ov(a, b)) warnings.push(`${where}: "${a.text}" (${a.kind}) overlaps "${b.text}" (${b.kind})`);
    }
  }
}
// chapter cards: the slab covers the left of the frame from K.cardIn(n) to K.cardClear(n). Anything in screen
// space under it at that time is a card drawn over content (old panels still fading, or the new chapter's
// panels and caption arriving early): sample each card while it is up, prime forward like playback.
if (info) {
  const cards = await page.evaluate(() => (window.K.cardWindows || []).map((w, i) => ({ i, n: w.n, in: w.in, out: w.out, clear: w.clear })));
  const samples = [];
  for (const c of cards) for (const f of [0, 0.15, 0.35, 0.55, 0.75, 0.95]) samples.push({ c, t: c.in + 0.06 + f * (c.clear - c.in - 0.14) });
  samples.sort((a, b) => a.t - b.t);
  let x = 0;
  for (const { c, t } of samples) {
    await page.evaluate(async ({ from, to }) => { for (let s = from; s < to; s += 0.25) await window.renderFrame(s); await window.renderFrame(to); }, { from: x, to: t });
    x = t;
    const hits = await page.evaluate((i) => {
      const w = window.K.cardWindows[i];
      const slab = w.el.querySelector('.chap-slab').getBoundingClientRect();
      if (slab.right < 8) return [];
      const vis = (el) => {
        let o = 1;
        for (let e = el; e && e.nodeType === 1; e = e.parentElement || e.parentNode) {
          const cs = getComputedStyle(e);
          if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
          o *= +cs.opacity;
        }
        return o;
      };
      const out = [];
      const els = [];
      for (const id of ['ui', 'fx', 'cards', 'hud']) for (const el of document.getElementById(id).children) {
        if (el.matches('.chap, [data-qa="skip"]')) continue;
        els.push([id, el]);
      }
      const cap = document.querySelector('#caps .cap');
      if (cap) els.push(['caption', cap]);
      // world space too (graph labels, weights, flags, badges, the decoder): every visible text the camera puts there
      for (const el of document.querySelectorAll('#world text')) els.push(['world text', el]);
      for (const [kind, el] of els) {
        const a = vis(el);
        if (a < 0.04 || !el.textContent.trim()) continue;
        let r = el.getBoundingClientRect();
        if (el.matches('svg.tree')) { const b = el.querySelector('g'); if (b) r = b.getBoundingClientRect(); }
        if (r.width < 2 || r.height < 2) continue;
        // the slab's right edge leans: x = left + w at the top, left + 0.84 w at the bottom (its clip-path)
        const edge = slab.left + slab.width * (1 - 0.16 * Math.max(0, r.top) / 1080);
        if (r.left < edge - 6 && r.right > slab.left + 6) out.push({ kind, text: el.textContent.trim().slice(0, 40), a: +a.toFixed(2) });
      }
      return out;
    }, c.i);
    for (const h of hits) warnings.push(`chapter card ${c.n} @ ${t.toFixed(2)}s: ${h.kind} "${h.text}" is visible (opacity ${h.a}) under the slab: ` +
      `hide it so it is gone by K.cardIn(${c.n}) = ${c.in.toFixed(2)}s, or bring it in from K.cardClear(${c.n}) = ${c.clear.toFixed(2)}s`);
  }
}
await browser.close();
srv.close();
const uniq = [...new Set(warnings)];
if (!QUIET || errors.length) {
  console.log(`page: ${PAGE}`);
  if (info) console.log(`TOTAL ${info.total.toFixed(2)} s, timeline ${info.dur.toFixed(2)} s, timing hash ${info.hash}`);
}
if (info && info.moments.length) console.log(`bursts/stamps at full size (for capture.mjs --stills): ${info.moments.map((m) => m.t.toFixed(2)).join(',')}`);
for (const e of errors) console.log(`  XX ${e}`);
for (const w of uniq) console.log(`  !! ${w}`);
console.log(errors.length ? `FAILED: ${errors.length} errors, ${uniq.length} warnings` : `ok: ${uniq.length} warnings (look at each; fix what is real)`);
process.exit(errors.length ? 1 : 0);
