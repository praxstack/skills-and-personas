#!/usr/bin/env node
// motion_check.mjs: load a motion-video clip in headless Chromium and lint it before any still or render.
//
// Reports (exit 1 on errors, 0 with warnings):
//   errors    page errors, failed loads, a film.json that does not build (every message names the shot, block
//             and field), window.TOTAL missing, timing.js without a hash
//   warnings  the engine's own (overlapping tweens on one element+property, text that only fits at the floor,
//             unknown fields), a line longer than 2.5 s where nothing on screen changes, and a layout audit at
//             every line (65% into its voice) and every cue: text off the frame or outside the safe area,
//             block text reaching into the caption band, text that renders under 26 px, text of one block
//             overlapping another block's text or the caption
//   prints    the shots with their times, every cue time as a ready --stills list for capture.mjs, and any ink the
//             engine darkened (or lightened) so it holds 4.6:1 on the lit backdrop
// Usage: node motion_check.mjs --page source/index.html [--at lines|cues|12.5,40] [--aspect 9:16] [--quiet]
//   --aspect previews the clip at another frame size (the layout only; timing stays the voiced one)
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { resolveUnder, contentType } from './servepath.mjs';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d; };
const PAGE = path.resolve(opt('page', 'source/index.html'));
const ROOT = path.dirname(PAGE);
const AT = opt('at', 'lines');
const ASPECT = opt('aspect', '');
const QUIET = argv.includes('--quiet');

// the same module search as capture.mjs, so the lint runs wherever the render does
async function loadChromium() {
  const bases = [process.cwd(), ROOT, path.dirname(new URL(import.meta.url).pathname)];
  for (const b of bases) for (const name of ['playwright-core', 'playwright']) {
    try { const req = createRequire(path.join(b, 'x.js')); const m = await import(pathToFileURL(req.resolve(name)).href); const c = m.chromium || m.default?.chromium; if (c) return c; } catch { /* next */ }
  }
  // a global install: npm's own global folder (nvm, Homebrew, system), then the usual fixed places
  const roots = [];
  try { roots.push(execFileSync('npm', ['root', '-g'], { encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim()); } catch { /* no npm */ }
  roots.push('/opt/node22/lib/node_modules', '/opt/homebrew/lib/node_modules', '/usr/local/lib/node_modules', '/usr/lib/node_modules');
  for (const r of roots) for (const name of ['playwright-core', 'playwright']) {
    const p = path.join(r, name, 'index.mjs');
    if (r && fs.existsSync(p)) { const m = await import(pathToFileURL(p).href); const c = m.chromium || m.default?.chromium; if (c) return c; }
  }
  throw new Error('Playwright not found: npm ci (in source/; playwright-core is a devDependency)');
}
// the same browser choice as capture.mjs: Ubuntu's /usr/bin/chromium-browser is often a script that hands over to the
// snap, which Playwright cannot drive, so Playwright's own browser comes before any system one and a snap shim is skipped
function snapShim(p) {
  try {
    if (fs.realpathSync(p).startsWith('/snap/')) return true;
    const fd = fs.openSync(p, 'r'), b = Buffer.alloc(4096), n = fs.readSync(fd, b, 0, 4096, 0); fs.closeSync(fd);
    const head = b.subarray(0, n).toString('latin1');
    return head.startsWith('#!') && head.includes('snap');
  } catch { return false; }
}
function chromiumPath(chromium) {
  if (process.env.CHROMIUM || process.env.CHROME) return process.env.CHROMIUM || process.env.CHROME;
  const c = ['/opt/pw-browsers/chromium'];
  try { for (const d of fs.readdirSync('/opt/pw-browsers')) if (/^chromium-\d+$/.test(d)) c.push(`/opt/pw-browsers/${d}/chrome-linux/chrome`); } catch { /* none */ }
  const pinned = c.find((p) => fs.existsSync(p));
  if (pinned) return pinned;
  try { if (fs.existsSync(chromium.executablePath())) return undefined; } catch { /* not downloaded */ } // Playwright's own
  return ['/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    .find((p) => fs.existsSync(p) && !snapShim(p)); // undefined -> Playwright's default (npx playwright install chromium)
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
const browser = await chromium.launch({ executablePath: chromiumPath(chromium), args: ['--no-sandbox', '--font-render-hinting=none'] });
const page = await browser.newPage({ viewport: { width: 1920, height: 1920 } });
const errors = [], warnings = [];
page.on('pageerror', (e) => errors.push(`page error: ${e.message}`));
page.on('console', (m) => { if (m.type() === 'error' && !/clip build failed/.test(m.text())) errors.push(`console: ${m.text()}`); });
page.on('requestfailed', (r) => errors.push(`failed to load ${r.url()}`));
page.on('response', (r) => { if (r.status() >= 400 && !r.url().includes('narration.wav')) errors.push(`HTTP ${r.status()} ${r.url()}`); });
// render=1 (no preview bar); aspect=… is honoured by core.js only without render, so use embed for that case
const q = ASPECT ? `embed=1&aspect=${encodeURIComponent(ASPECT)}` : 'render=1';
await page.goto(`http://127.0.0.1:${srv.address().port}/${path.basename(PAGE)}?${q}`, { waitUntil: 'load' });
let info = null, cueTimes = [];
try {
  await page.waitForFunction(() => window.READY !== undefined, null, { timeout: 30000 });
  await page.evaluate(async () => { await window.READY; });
  info = await page.evaluate(() => ({
    total: window.TOTAL, dur: M.tl.duration(), hash: window.TIMING.hash, warnings: M.warnings.slice(), W: M.W, H: M.H, aspect: M.aspect,
    G: M.G, events: M.events.slice(), notes: (M.notes || []).slice(),
    lines: M.lines.map((l) => ({ id: l.id, t: l.voiceAt + 0.65 * l.voiceDur, start: l.start, end: l.end, ch: l.chapter })),
    shots: M.shots.map((s) => ({ at: s.at, t0: s.t0, t1: s.t1, blocks: s.blocks.map((b) => b.type + (b.id ? ` ${b.id}` : '')) })),
  }));
} catch (e) {
  const msg = await page.evaluate(() => (document.getElementById('err') || {}).textContent || '').catch(() => '');
  errors.push(msg ? msg.trim() : `the clip did not build: ${e.message.split('\n')[0]}`);
}
if (info) {
  await page.setViewportSize({ width: info.W, height: info.H });
  if (!(info.total > 0)) errors.push('window.TOTAL is missing or zero');
  if (!info.hash) errors.push('timing.js has no hash: emit it with voice.py --emit source/timing.js');
  warnings.push(...info.warnings);
  // every line should change something on screen (quality-bar.md); captions alone do not count
  for (const l of info.lines) {
    if (l.end - l.start < 2.5) continue;
    const n = info.events.filter((e) => e.t >= l.start - 0.3 && e.t < l.end).length;
    if (!n) warnings.push(`line ${l.id} (${(l.end - l.start).toFixed(1)} s): nothing on screen changes; add a cue on it or start a shot there`);
  }
  // a cue still is taken 1.5 s after the cue, when its motion has settled, but before its line's caption fades and
  // before its shot hands over (a fade is not a frame to judge); a cue that plays on (a long count, a route's hops
  // and chip) is taken once it has landed, at its end, which the stage keeps before its block leaves
  const settle = (t, end = t) => {
    const l = info.lines.find((x) => t >= x.start && t < x.end), s = info.shots.find((x) => t >= x.t0 && t < x.t1);
    let at = t + 1.5;
    if (l) at = Math.min(at, l.end - 0.3);
    if (s) at = Math.min(at, s.t1 - 0.4);
    at = Math.max(at, end);
    return Math.min(info.total - 0.05, Math.max(t + 0.3, at));
  };
  cueTimes = info.events.filter((e) => !/^enter |^move /.test(e.what) && e.t < info.total)
    .map((e) => ({ id: e.what.replace(/\s+/g, '-'), t: settle(e.t, Number.isFinite(e.end) ? e.end : e.t) }));
  const times = AT === 'lines' ? [...info.lines, ...cueTimes].sort((a, b) => a.t - b.t)
    : AT === 'cues' ? cueTimes : AT.split(',').map((x) => ({ id: `t${x}`, t: +x }));
  const G = info.G;
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
      // text: every element that holds its own text (HTML) and every SVG <text>, with its rendered size
      const own = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
      for (const el of document.querySelectorAll('#stage .world *, #stage .caps *, #stage .chrome *')) {
        if (!own(el) || vis(el) < 0.35) continue;
        // HTML: the glyphs' extent (a block-level element's own box can be wider than its text)
        let r = el.getBoundingClientRect();
        if (!(el instanceof SVGElement)) { const rg = document.createRange(); rg.selectNodeContents(el); const rr = rg.getBoundingClientRect(); if (rr.width >= 2) r = rr; }
        if (r.width < 2 || r.height < 2) continue;
        let fs = parseFloat(getComputedStyle(el).fontSize);
        if (el instanceof SVGElement) fs *= Math.abs(el.getScreenCTM().a);
        else if (el.offsetWidth) fs *= el.getBoundingClientRect().width / el.offsetWidth;
        const blk = el.closest('.blk');
        items.push({ kind: el.closest('.caps') ? 'caption' : el.closest('.chrome') ? 'chrome' : 'block', block: blk ? blk.dataset.k : '',
          fs: Math.round(fs * 10) / 10, ...r4(r), text: el.textContent.trim().slice(0, 40) });
      }
      return items;
    });
    const where = `${times[k].id} @ ${t.toFixed(2)}s`;
    const S = G.safe, capTop = G.cap ? G.cap.y : info.H;
    for (const it of found) {
      // block text rides the camera's slow breath (up to ~15 px at the frame's edge), so it gets that much slack
      const tol = it.kind === 'block' ? 16 * Math.min(info.W, info.H) / 1080 : 2;
      if (it.x < 0 || it.y < 0 || it.r > info.W || it.b > info.H) warnings.push(`${where}: "${it.text}" runs off the frame (${it.x},${it.y})-(${it.r},${it.b})`);
      else if (it.x < S.x - tol || it.y < S.y - tol || it.r > S.x + S.w + tol || it.b > S.y + S.h + tol) warnings.push(`${where}: "${it.text}" is outside the safe area (${it.x},${it.y})-(${it.r},${it.b}); on 9:16 the platform draws over the bottom and right`);
      if (it.kind === 'block' && it.b > capTop + tol) warnings.push(`${where}: ${it.block} text "${it.text}" reaches into the caption band (bottom ${it.b} > ${Math.round(capTop)})`);
      if (it.fs < 26) warnings.push(`${where}: "${it.text}" renders at ${it.fs} px, under the 26 px floor (legibility.py fails it): give the block more room or less text`);
    }
    const ov = (a, b) => Math.min(a.r, b.r) - Math.max(a.x, b.x) > 4 && Math.min(a.b, b.b) - Math.max(a.y, b.y) > 4;
    for (let i = 0; i < found.length; i++) for (let j = i + 1; j < found.length; j++) {
      const a = found[i], b = found[j];
      if (a.block && a.block === b.block) continue;   // inside one block, the block owns its layout
      if (a.kind === 'caption' && b.kind === 'caption') continue;   // two caption lines cross-fade on purpose
      if (ov(a, b)) warnings.push(`${where}: "${a.text}" (${a.block || a.kind}) overlaps "${b.text}" (${b.block || b.kind})`);
    }
  }
}
await browser.close();
srv.close();
const uniq = [...new Set(warnings)];
if (info && !QUIET) {
  console.log(`clip ${info.W}x${info.H} (${info.aspect}), ${info.total.toFixed(2)} s, timing ${info.hash}`);
  for (const s of info.shots) console.log(`  shot ${s.at.padEnd(6)} ${s.t0.toFixed(2).padStart(6)}-${s.t1.toFixed(2).padStart(6)}  ${s.blocks.join(' + ')}`);
  const cs = cueTimes.map((c) => c.t.toFixed(2));
  if (cs.length) console.log(`cue stills (each cue once it settles): --stills ${[...new Set(cs)].sort((a, b) => a - b).join(',')}`);
  for (const n of info.notes) console.log(`note  ${n}`);
}
for (const e of errors) console.log(`ERROR ${e}`);
for (const w of uniq) console.log(`WARN  ${w}`);
console.log(errors.length ? `${errors.length} errors, ${uniq.length} warnings` : uniq.length ? `ok with ${uniq.length} warnings` : 'ok');
process.exit(errors.length ? 1 : 0);
