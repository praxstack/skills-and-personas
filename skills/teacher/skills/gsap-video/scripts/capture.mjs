#!/usr/bin/env node
// capture.mjs: turn any web page that can draw itself at time t into an MP4, frame by frame, in headless Chromium.
//
// Page contract (the templates implement it):
//   window.READY            true, or a Promise that resolves when fonts/assets are loaded
//   window.TOTAL            film length in seconds
//   window.renderFrame(t)   draw the exact frame for time t (sync or async; deterministic, no wall clock)
//   window.CAPTURE_SELECTOR optional, e.g. '#c': grab that canvas with toDataURL (fast) instead of a page screenshot
//
// Rendering is split into segments (default 20 s) recorded in <out dir>/segments/manifest.json. A finished
// segment is never rendered again, so if the job is killed (crash, 2-hour cap) just run the same command again.
// A page file edited while it renders stops it before the join (exit 4): run it again to render the current version.
//
// Usage:
//   node capture.mjs --page source/index.html --out build/silent.mp4 [--fps 30] [--width 1920 --height 1080]
//                    [--workers 4] [--segment 20] [--from 0 --to 60] [--max-minutes 100] [--webgl] [--prime 0.25]
//   node capture.mjs --page source/index.html --stills 1.5,12,40 [--stills-dir stills]
//   node capture.mjs --page source/index.html --stills chapters --timing timing.json      (one still per chapter)
//   node capture.mjs --page source/index.html --stills lines --timing timing.json         (one still per line)
//   node capture.mjs --page source/index.html --bench 3     (time 3 s of frames, print fps and the full-film ETA)
//   node capture.mjs --page source/index.html --footage-map footage-map.json [--map-fps 4]
//                    (a film with recorded footage: where it is on the frame over time, for qa.py's moving-text)
//   --page 'source/index.html?q=final' passes the query through to the page (render=1 is appended)
// Env: CHROMIUM=/path/to/chrome (auto-detected), GPU=1 (use the real GPU for WebGL on a laptop)
import http from 'node:http';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawn, execFileSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';
import { resolveUnder, contentType } from './servepath.mjs';
import { manifestOk, concatLine, sourceStamp } from './segmanifest.mjs';

const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length && !argv[i + 1].startsWith('--') ? argv[i + 1] : d; };
const flag = (k) => argv.includes('--' + k);
const PAGE_ARG = opt('page'); if (!PAGE_ARG) { console.error('--page <index.html> is required'); process.exit(2); }
// --page may carry a query string (index.html?q=final); it is passed through to the page
const [PAGE, QUERY = ''] = PAGE_ARG.split('?');
const ROOT = path.resolve(opt('root', path.dirname(PAGE)));
const OUT = path.resolve(opt('out', 'build/silent.mp4'));
const FPS = +opt('fps', 30), W = +opt('width', 1920), H = +opt('height', 1080);
const WORKERS = +opt('workers', Math.max(1, Math.min(4, os.cpus().length)));
const SEG = +opt('segment', 20), QUALITY = +opt('quality', 92), CRF = opt('crf', '20');
const PRIME = +opt('prime', 0), MAXMIN = +opt('max-minutes', 100), WEBGL = flag('webgl');
const MODE = opt('mode', 'auto');
// with no worker no segment is ever rendered, and a re-run would report the same unfinished film forever
if (!(Number.isInteger(WORKERS) && WORKERS >= 1)) { console.error(`--workers ${opt('workers')} must be a whole number of 1 or more, e.g. --workers 2`); process.exit(2); }
// priming walks the page from the start in --prime second steps: a negative, tiny or non-number step never arrives
if (PRIME !== 0 && !(Number.isFinite(PRIME) && PRIME >= 0.01)) { console.error(`--prime ${PRIME} must be 0 (off) or a step of at least 0.01 s, e.g. --prime 0.25`); process.exit(2); }

// ------------------------------------------------------------------ playwright + chromium discovery
async function loadChromium() {
  const bases = [process.cwd(), path.dirname(path.resolve(PAGE)), ROOT, path.dirname(new URL(import.meta.url).pathname)];
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
  throw new Error('Playwright not found. In the project\'s source/ folder run: npm i -D playwright-core@1.56.1   (then, on a laptop without Chrome: npx playwright install chromium)');
}
// Ubuntu's /usr/bin/chromium-browser is often a script that hands over to the snap, which Playwright cannot drive
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

// ------------------------------------------------------------------ tiny static server (no file:// font/CORS surprises)
function serve() {
  return new Promise((res) => {
    const srv = http.createServer((req, rsp) => {
      if (req.url.startsWith('/favicon')) { rsp.writeHead(204); rsp.end(); return; }
      // only real files inside ROOT (servepath.mjs resolves symlinks on both sides before comparing)
      const p = resolveUnder(ROOT, req.url);
      if (!p) { rsp.writeHead(404); rsp.end(); return; }
      // same-origin page: no CORS header, so other pages in a browser on this machine cannot read these files
      rsp.writeHead(200, { 'Content-Type': contentType(p) });
      fs.createReadStream(p).pipe(rsp);
    });
    srv.listen(0, '127.0.0.1', () => res(srv));
  });
}

const chromium = await loadChromium();
const exe = chromiumPath(chromium);
const srv = await serve();
const URL_ = `http://127.0.0.1:${srv.address().port}/${path.relative(ROOT, path.resolve(PAGE)).split(path.sep).join('/')}?${QUERY ? QUERY + '&' : ''}render=1`;
const gl = WEBGL && !process.env.GPU ? ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] : ['--ignore-gpu-blocklist'];
const ARGS = ['--no-sandbox', '--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows', '--font-render-hinting=none', ...gl];

async function openPage() {
  const browser = await chromium.launch({ executablePath: exe, args: ARGS });
  const page = await browser.newPage({ viewport: { width: W, height: H }, deviceScaleFactor: 1 });
  page.on('pageerror', (e) => console.error('page error:', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('console:', m.text()); });
  await page.goto(URL_, { waitUntil: 'load' });
  await page.waitForFunction(() => window.READY !== undefined && window.renderFrame !== undefined, null, { timeout: 120000 });
  await page.evaluate(async () => { await window.READY; await document.fonts.ready; });
  const info = await page.evaluate(() => ({ total: window.TOTAL, sel: window.CAPTURE_SELECTOR || null }));
  return { browser, page, info };
}
async function grab(page, t, sel) {
  if (sel && MODE !== 'screenshot') {
    const data = await page.evaluate(async ({ t, sel, q }) => { await window.renderFrame(t); return document.querySelector(sel).toDataURL('image/jpeg', q); }, { t, sel, q: QUALITY / 100 });
    return Buffer.from(data.slice(data.indexOf(',') + 1), 'base64');
  }
  await page.evaluate(async (t) => { await window.renderFrame(t); }, t);
  return page.screenshot({ type: 'jpeg', quality: QUALITY });
}
async function prime(page, from, to) {
  if (!PRIME || to <= from) return;
  await page.evaluate(async ({ from, to, step }) => { for (let x = from; x < to; x += step) await window.renderFrame(x); }, { from, to, step: PRIME });
}
function timingTimes(kind) {
  const tp = opt('timing', 'timing.json');
  const tm = JSON.parse(fs.readFileSync(tp, 'utf8'));
  const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  // 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
  // previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
  const offSwap = (t) => { const l = tm.lines.find((x) => t > x.voiceAt - 0.3 && t < x.voiceAt + 0.3); return !l ? t : tm.lines.find((x) => x.chapter === l.chapter) === l ? l.voiceAt + 0.4 : l.voiceAt - 0.35; };
  if (kind === 'chapters') return tm.chapters.map((c) => [`ch${c.n}-${slug(c.name)}`, offSwap(c.start + 0.45 * (c.end - c.start))]);
  return tm.lines.map((l) => [`${String(l.start.toFixed(1)).padStart(6, '0')}-${l.id}`, l.voiceAt + 0.65 * l.voiceDur]);
}

// ------------------------------------------------------------------ stills / bench
if (opt('stills')) {
  const s = opt('stills');
  const list = (s === 'chapters' || s === 'lines') ? timingTimes(s) : s.split(',').map((x) => [`t${(+x).toFixed(2).padStart(7, '0')}`, +x]);
  const dir = path.resolve(opt('stills-dir', 'stills')); fs.mkdirSync(dir, { recursive: true });
  const { browser, page, info } = await openPage();
  let last = 0;
  for (const [name, t] of list.sort((a, b) => a[1] - b[1])) {
    await prime(page, last, t); last = t;
    fs.writeFileSync(path.join(dir, `${name}.jpg`), await grab(page, t, info.sel));
    // a film that shows recorded footage (window.FOOTAGE: {rects, keep} in frame px) says where it is, beside the
    // still, so legibility.py reports the recording's own text apart from the text the film draws
    const fp = await page.evaluate(() => (window.FOOTAGE ? window.FOOTAGE() : null));
    const side = path.join(dir, `${name}.footage.json`);
    if (fp && fp.rects && fp.rects.length) fs.writeFileSync(side, JSON.stringify({ t, ...fp }));
    else if (fs.existsSync(side)) fs.unlinkSync(side);
    console.log('still', name, t.toFixed(2));
  }
  await browser.close(); srv.close(); process.exit(0);
}
if (opt('footage-map')) {
  // where recorded footage is on the frame through the whole film, a few times a second, for qa.py's moving-text
  // check (the same rule as the stills: the recording's own text is reported, the film's own text is held to the bar)
  const out = path.resolve(opt('footage-map')), step = 1 / +opt('map-fps', 4);
  const { browser, page, info } = await openPage();
  const frames = [];
  for (let t = 0; t < info.total; t += step) {
    frames.push({ t: +t.toFixed(3), ...(await page.evaluate(async (t) => { await window.renderFrame(t); return window.FOOTAGE ? window.FOOTAGE() : { rects: [], keep: [] }; }, t)) });
  }
  fs.writeFileSync(out, JSON.stringify({ total: info.total, step, frames }));
  console.log(`footage map: ${frames.length} times, ${frames.filter((f) => f.rects.length).length} with footage on screen -> ${out}`);
  await browser.close(); srv.close(); process.exit(0);
}
if (opt('bench')) {
  const secs = +opt('bench', 3);
  const { browser, page, info } = await openPage();
  const t0s = Math.max(0, info.total / 2 - secs / 2); await prime(page, 0, t0s);
  const n = Math.round(secs * FPS), t0 = Date.now();
  for (let f = 0; f < n; f++) await grab(page, t0s + f / FPS, info.sel);
  const fps1 = n / ((Date.now() - t0) / 1000), frames = Math.round(info.total * FPS);
  const eff = WEBGL && !process.env.GPU ? 0.35 : 0.8; // SwiftShader shares the CPU: extra workers help little
  const etaMin = frames / (fps1 * Math.max(1, WORKERS * eff)) / 60;
  console.log(`one worker: ${fps1.toFixed(2)} frames/s. Film: ${frames} frames, ~${etaMin.toFixed(0)} min with ${WORKERS} workers.`);
  if (etaMin > 100) console.log(`Longer than one 2-hour job: run with --max-minutes 100 and re-run the same command until it says done.`);
  await browser.close(); srv.close(); process.exit(0);
}

// ------------------------------------------------------------------ segmented render
const probe = await openPage();
const TOTAL = +opt('to', probe.info.total), FROM = +opt('from', 0);
await probe.browser.close();
if (!(TOTAL > FROM)) { console.error('window.TOTAL is missing or zero'); process.exit(2); }
// a segment shorter than one frame would never move the render forward
if (!(Math.round(SEG * FPS) >= 1)) { console.error(`--segment ${SEG} at --fps ${FPS} is shorter than one frame; give seconds, e.g. --segment 20`); process.exit(2); }
const segDir = path.join(path.dirname(OUT), 'segments'); fs.mkdirSync(segDir, { recursive: true });
const manPath = path.join(segDir, 'manifest.json');
// any change to the page's files invalidates finished segments (a half-old film is worse than a slow one)
const stamp = sourceStamp(ROOT);
const key = { fps: FPS, width: W, height: H, from: FROM, to: +TOTAL.toFixed(3), segment: SEG, page: path.resolve(PAGE) + (QUERY ? '?' + QUERY : ''), stamp };
let man = null;
try { man = fs.existsSync(manPath) ? JSON.parse(fs.readFileSync(manPath, 'utf8')) : null; } catch { man = null; }
// a resumed manifest is accepted only if this script could have written it (see segmanifest.mjs)
if (man && !manifestOk(man, Math.round(TOTAL * FPS), Math.round(FROM * FPS))) { console.log('segments/manifest.json is not one this script wrote: starting the segments over'); man = null; }
if (man && JSON.stringify(man.key) !== JSON.stringify(key) && man.segments.some((x) => x.done)) console.log('page, timing or settings changed since the last run: starting the segments over');
if (!man || JSON.stringify(man.key) !== JSON.stringify(key)) {
  const N0 = Math.round(FROM * FPS), N1 = Math.round(TOTAL * FPS), per = Math.round(SEG * FPS), segs = [];
  for (let a = N0, i = 0; a < N1; a += per, i++) segs.push({ i, a, b: Math.min(N1, a + per), file: `seg_${String(i).padStart(4, '0')}.mp4`, done: false });
  man = { key, segments: segs };
  for (const f of fs.readdirSync(segDir)) if (f.startsWith('seg_')) fs.unlinkSync(path.join(segDir, f));
}
// a setting that changes the pictures (JPEG quality, encoder CRF, grab mode, priming, WebGL, the GPU) starts the
// segments over too: a resumed film would otherwise join segments made one way to segments made another
const look = { quality: QUALITY, crf: String(CRF), mode: MODE, prime: PRIME, webgl: WEBGL, gpu: WEBGL && !!process.env.GPU };
if (JSON.stringify(man.look) !== JSON.stringify(look)) {
  if (man.segments.some((x) => x.done)) console.log('render settings changed since the last run: starting the segments over');
  man.segments.forEach((x) => { x.done = false; });
  for (const f of fs.readdirSync(segDir)) if (f.startsWith('seg_')) fs.unlinkSync(path.join(segDir, f));
  man.look = look;
}
// a finished segment counts only while its file is there with all its frames: one deleted or cut short since the
// last run (a cleanup, a full disk) is rendered again, instead of breaking the join or joining a damaged file
for (const s of man.segments.filter((x) => x.done)) {
  let n = -1;
  try {
    n = +execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
      '-of', 'csv=p=0', path.join(segDir, s.file)], { stdio: ['ignore', 'pipe', 'ignore'] }).toString().trim();
  } catch { n = -1; }
  if (n !== s.b - s.a) { console.log(`${s.file} is ${!(n >= 0) ? 'missing or unreadable' : `${n} of ${s.b - s.a} frames`}: rendering it again`); s.done = false; }
}
const saveMan = () => { fs.writeFileSync(manPath + '.tmp', JSON.stringify(man, null, 1)); fs.renameSync(manPath + '.tmp', manPath); };
saveMan();
const todo = man.segments.filter((s) => !s.done);
const totalFrames = todo.reduce((n, s) => n + s.b - s.a, 0);
console.log(`${man.segments.length} segments, ${todo.length} to render (${totalFrames} frames), ${WORKERS} workers${WEBGL ? ', WebGL' : ''}; chromium ${exe || '(playwright default)'}`);
const started = Date.now(); let doneFrames = 0, stopped = false;
async function worker(w) {
  let ctx = null;
  while (todo.length) {
    if ((Date.now() - started) / 60000 > MAXMIN) { stopped = true; break; }
    const s = todo.shift();
    if (!ctx) ctx = await openPage();
    const tmp = path.join(segDir, s.file + '.part.mp4');
    const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'medium', '-crf', String(CRF), '-pix_fmt', 'yuv420p', '-r', String(FPS), tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
    await prime(ctx.page, 0, s.a / FPS);
    for (let f = s.a; f < s.b; f++) {
      const buf = await grab(ctx.page, f / FPS, ctx.info.sel);
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (++doneFrames % 150 === 0) {
        const el = (Date.now() - started) / 1000, rate = doneFrames / el;
        console.log(`  ${doneFrames}/${totalFrames} frames  ${rate.toFixed(1)} fps  eta ${((totalFrames - doneFrames) / rate / 60).toFixed(1)} min`);
      }
    }
    ff.stdin.end(); const code = await new Promise((r) => ff.on('close', r));
    if (code !== 0) throw new Error(`ffmpeg failed on ${s.file}`);
    fs.renameSync(tmp, path.join(segDir, s.file));
    man.segments[s.i].done = true; saveMan();
  }
  if (ctx) await ctx.browser.close();
}
await Promise.all(Array.from({ length: WORKERS }, (_, w) => worker(w)));
srv.close();
const left = man.segments.filter((s) => !s.done).length;
if (left) { console.log(`stopped at the ${MAXMIN}-minute budget: ${left} segments left. Run the same command again to resume.`); process.exit(3); }
// a page file edited while the segments rendered: workers that opened the page before and after the edit made two
// versions of the film, so nothing is joined (the stamp in the manifest no longer matches: the next run starts over)
if (sourceStamp(ROOT) !== stamp) {
  console.error(`the page's files changed while it rendered, so the segments would join two versions of the film; ${OUT} was not written. Run the same command again to render the current version.`);
  process.exit(4);
}
const list = path.join(segDir, 'list.txt');
fs.writeFileSync(list, man.segments.map((s) => concatLine(path.join(segDir, s.file))).join('\n') + '\n');
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', OUT]);
console.log(`wrote ${OUT}: ${(TOTAL - FROM).toFixed(2)} s in ${((Date.now() - started) / 60000).toFixed(1)} min`);
