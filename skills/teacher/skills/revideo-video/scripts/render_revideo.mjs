#!/usr/bin/env node
// render_revideo.mjs: render a Revideo project (<project>/source) to build/silent.mp4 in resumable segments,
// render review stills, or benchmark. Wraps @revideo/renderer's renderVideo with the settings that work in a
// headless sandbox: the FFmpeg exporter (the default WebCodecs exporter fails with "Encoder creation error"),
// a local Chromium, --no-sandbox, telemetry off.
//
// Segments are time ranges recorded in build/segments/manifest.json ({"segments": [{"from","to","done"}]}).
// A finished segment is never rendered again; any change to source/src, the timing or the settings starts
// them over. Each segment renders in its own child process, so a crashed or stalled page is killed cleanly.
//
// Usage (from the project folder, or pass --project):
//   node render_revideo.mjs --project . [--workers 2] [--segment 20] [--max-minutes 100] [--out build/silent.mp4]
//   node render_revideo.mjs --project . --stills lines|chapters|busy|12.5,40.2 [--stills-dir stills] [--workers 2]
//   node render_revideo.mjs --project . --bench 3          (renders 3 s from the middle; prints fps and the ETA)
//   node render_revideo.mjs --project . --range 10,20      (renders a time range to build/preview.mp4; a quick look)
// Options: --source <dir> (default <project>/source)  --stall 240 (kill a segment with no progress for N s)
//          --allow-page-errors (do not fail on console errors in the page)  --crf 18 (H.264 quality, lower = better)
// Env: CHROMIUM=/path/to/chrome (default /opt/pw-browsers/chromium when present, else puppeteer's own Chrome)
// Exit codes: 0 done, 1 error, 3 stopped at the --max-minutes budget (run the same command again to resume).
import {spawn, execFileSync} from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {createRequire} from 'node:module';

import { manifestOk, concatLine } from './segmanifest.mjs';
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length && !argv[i + 1].startsWith('--') ? argv[i + 1] : d; };
const flag = k => argv.includes('--' + k);
const log = (...a) => console.log(...a);

// ------------------------------------------------------------------ child mode: one renderVideo call
if (flag('child')) {
  const job = JSON.parse(Buffer.from(opt('child'), 'base64').toString());
  const req = createRequire(path.join(job.src, 'package.json'));
  const {renderVideo} = req('@revideo/renderer');
  process.chdir(job.src);
  try {
    const out = await renderVideo({
      projectFile: './src/project.ts',
      settings: {
        outFile: job.outFile, outDir: job.outDir, workers: 1, logProgress: false,
        progressCallback: (_id, p) => console.log(`@@PROGRESS ${Number(p).toFixed(4)}`),
        projectSettings: {exporter: {name: '@revideo/core/ffmpeg', options: {format: 'mp4'}}, range: [job.from, job.to]},
        puppeteer: {...(job.chrome ? {executablePath: job.chrome} : {}), args: ['--no-sandbox', '--disable-dev-shm-usage']},
        viteBasePort: job.port,
      },
    });
    console.log(`@@DONE ${out}`);
    process.exit(0);
  } catch (e) {
    console.log(`@@FAIL ${e?.message ?? e}`);
    process.exit(1);
  }
}

// ------------------------------------------------------------------ parent
const PROJECT = path.resolve(opt('project', '.'));
const SRC = path.resolve(opt('source', path.join(PROJECT, 'source')));
const WORKERS = Math.max(1, +opt('workers', Math.max(1, Math.min(4, os.cpus().length - 2))));
const SEG = +opt('segment', 20);
const MAXMIN = +opt('max-minutes', 100);
const STALL = +opt('stall', 240);
const CRF = opt('crf', '18');
const ALLOW_ERR = flag('allow-page-errors');
const SELF = new URL(import.meta.url).pathname;
const CHROME = process.env.CHROMIUM || process.env.CHROME ||
  ['/opt/pw-browsers/chromium', '/usr/bin/chromium', '/usr/bin/chromium-browser', '/usr/bin/google-chrome',
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(p => fs.existsSync(p));

if (!fs.existsSync(path.join(SRC, 'src', 'project.ts'))) die(`no Revideo project at ${SRC} (expected src/project.ts)`);
if (!fs.existsSync(path.join(SRC, 'node_modules', '@revideo', 'renderer'))) {
  die(`dependencies are not installed: (cd ${SRC} && PUPPETEER_SKIP_DOWNLOAD=1 npm install)`);
}
const TIMING = readTiming();
const FPS = TIMING.fps, TOTAL = TIMING.total, FRAMES = Math.round(TOTAL * FPS);
const BUILD = path.join(PROJECT, 'build');
fs.mkdirSync(BUILD, {recursive: true});

// x264 quality: Revideo's FFmpeg exporter uses ffmpeg's default (CRF 23), which bands on dark gradients.
// A tiny wrapper adds -crf/-preset to its encodes; everything else passes through unchanged.
const FFMPEG = which('ffmpeg');
const FFPROBE = which('ffprobe');
const wrapper = path.join(BUILD, 'ffmpeg-hq.sh');
if (FFMPEG) {
  fs.writeFileSync(wrapper, `#!/bin/sh
# written by render_revideo.mjs: Revideo's exporter encodes at ffmpeg's default CRF 23; add -crf/-preset to
# the encode whose output is visuals.mp4 (the last argument) and pass every other call through unchanged.
last=""; for a in "$@"; do last="$a"; done
case "$last" in
  *visuals.mp4)
    n=$#; i=0
    for a in "$@"; do
      i=$((i+1))
      if [ $i -eq 1 ]; then set --; fi
      if [ $i -lt $n ]; then set -- "$@" "$a"; fi
    done
    exec "${FFMPEG}" "$@" -crf ${CRF} -preset medium "$last" ;;
  *) exec "${FFMPEG}" "$@" ;;
esac
`);
  fs.chmodSync(wrapper, 0o755);
}
const ENV = {
  ...process.env, DISABLE_TELEMETRY: 'true', PUPPETEER_SKIP_DOWNLOAD: '1',
  ...(FFMPEG ? {FFMPEG_PATH: wrapper} : {}), ...(FFPROBE ? {FFPROBE_PATH: FFPROBE} : {}),
};

function die(msg, code = 1) { console.error(`render_revideo: ${msg}`); process.exit(code); }
function which(bin) {
  try { return execFileSync('sh', ['-c', `command -v ${bin}`]).toString().trim() || null; } catch { return null; }
}
function readTiming() {
  const tp = path.join(SRC, 'src', 'timing.ts');
  if (!fs.existsSync(tp)) die(`missing ${tp}: run voice.py --emit source/src/timing.ts`);
  const txt = fs.readFileSync(tp, 'utf8');
  const m = txt.match(/export const TIMING = (\{[\s\S]*\});\s*export default/);
  if (!m) die(`cannot parse ${tp}`);
  const t = JSON.parse(m[1]);
  const pj = path.join(PROJECT, 'timing.json');
  if (fs.existsSync(pj)) {
    const h = JSON.parse(fs.readFileSync(pj, 'utf8')).hash;
    if (h && h !== t.hash) log(`warning: source/src/timing.ts (hash ${t.hash}) is not the project's timing.json (hash ${h}); re-run voice.py --emit source/src/timing.ts`);
  }
  return t;
}
function srcHash() {
  const h = crypto.createHash('sha1');
  const walk = d => {
    for (const e of fs.readdirSync(d, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else { h.update(path.relative(SRC, p)); h.update(fs.readFileSync(p)); }
    }
  };
  walk(path.join(SRC, 'src'));
  for (const f of ['package.json', 'package-lock.json']) if (fs.existsSync(path.join(SRC, f))) h.update(fs.readFileSync(path.join(SRC, f)));
  return h.digest('hex').slice(0, 16);
}
const sec = f => (f - 0.5) / FPS; // a time that Revideo's ceil(t * fps) maps exactly to frame f
const fmtMin = s => `${(s / 60).toFixed(1)} min`;

/** Render frames [a, b] (inclusive) to `file` in a child process. Resolves {ok, secs, late[]}. */
let portSlot = 0;
function renderRange(a, b, file, onProgress) {
  return new Promise(resolve => {
    const outDir = path.dirname(file), outFile = path.basename(file);
    const slot = portSlot++ % 16;
    const job = {src: SRC, outDir, outFile, from: sec(a), to: sec(b), chrome: CHROME, port: 9500 + slot * 12};
    const child = spawn(process.execPath, [SELF, '--child', Buffer.from(JSON.stringify(job)).toString('base64')],
      {env: ENV, detached: true, stdio: ['ignore', 'pipe', 'pipe']});
    const t0 = Date.now();
    let last = Date.now(), done = false, failed = '', buf = '';
    const late = [];
    const kill = why => {
      if (done) return;
      failed = failed || why;
      try { process.kill(-child.pid, 'SIGKILL'); } catch { /* gone */ }
    };
    const onLine = line => {
      if (line.startsWith('@@PROGRESS ')) { last = Date.now(); onProgress?.(+line.slice(11)); return; }
      if (line.startsWith('@@DONE')) { done = true; return; }
      if (line.startsWith('@@FAIL')) { failed = line.slice(7); return; }
      const lm = line.match(/LATE\|([^|]*)\|([\d.]+)/);
      if (lm) { const s = `${lm[1]} +${lm[2]}s`; if (!late.includes(s)) late.push(s); return; }
      if (/\[Unhandled error\]|Rendering failed|\[console\.error\]|Error:/.test(line) && !/posthog|telemetry/i.test(line)) {
        console.error(`  page: ${line.slice(0, 400)}`);
        if (!ALLOW_ERR) kill('page error (fix the scene, or pass --allow-page-errors)');
      }
    };
    for (const s of [child.stdout, child.stderr]) {
      s.on('data', d => {
        buf += d.toString();
        let i;
        while ((i = buf.indexOf('\n')) >= 0) { onLine(buf.slice(0, i)); buf = buf.slice(i + 1); }
      });
    }
    const wd = setInterval(() => { if (Date.now() - last > STALL * 1000) kill(`no progress for ${STALL} s`); }, 5000);
    child.on('exit', code => {
      clearInterval(wd);
      const ok = code === 0 && !failed && fs.existsSync(file);
      // renderVideo leaves its intermediates next to the output (<name>-0.mp4, -visuals.mp4, -audio.wav): 3x the disk
      const stem = outFile.replace(/\.mp4$/, '') + '-';
      for (const f of fs.readdirSync(outDir)) if (f.startsWith(stem) && /^(\d+|visuals)\.mp4$|^audio\.wav$/.test(f.slice(stem.length))) {
        try { fs.rmSync(path.join(outDir, f), {force: true}); } catch { /* ignore */ }
      }
      if (!ok) {
        for (const d of fs.readdirSync(os.tmpdir())) if (d.startsWith(`revideo-${outFile.replace(/\.mp4$/, '')}`)) {
          try { fs.rmSync(path.join(os.tmpdir(), d), {recursive: true, force: true}); } catch { /* ignore */ }
        }
      }
      resolve({ok, secs: (Date.now() - t0) / 1000, late, why: failed || (code !== 0 ? `exit ${code}` : '')});
    });
  });
}
function probeFrames(file) {
  try {
    return +execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
      '-of', 'csv=p=0', file]).toString().trim();
  } catch { return 0; }
}
function probeDuration(file) {
  try {
    return +execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', file]).toString().trim();
  } catch { return 0; }
}
async function pool(items, n, fn) {
  const queue = [...items];
  await Promise.all(Array.from({length: Math.min(n, queue.length)}, async () => {
    while (queue.length) await fn(queue.shift());
  }));
}

// ------------------------------------------------------------------ stills
if (opt('stills')) {
  const kind = opt('stills');
  const slug = s => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  let shots;
  // 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
  // previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
  const offSwap = (t) => { const l = TIMING.lines.find((x) => Math.abs(t - x.voiceAt) < 0.3); return !l ? t : TIMING.lines.find((x) => x.chapter === l.chapter) === l ? l.voiceAt + 0.4 : l.voiceAt - 0.35; };
  if (kind === 'chapters') shots = TIMING.chapters.map(c => [`ch${c.n}-${slug(c.name)}`, offSwap(c.start + 0.45 * (c.end - c.start))]);
  else if (kind === 'lines') shots = TIMING.lines.map(l => [`${l.start.toFixed(1).padStart(6, '0')}-${l.id}`, l.voiceAt + 0.65 * l.voiceDur]);
  else if (kind === 'busy') shots = [...TIMING.lines].sort((a, b) => b.dur - a.dur).slice(0, 8)
    .map(l => [`${l.start.toFixed(1).padStart(6, '0')}-${l.id}`, l.voiceAt + 0.8 * l.voiceDur]);
  else shots = kind.split(',').map(x => [`t${(+x).toFixed(2).padStart(7, '0')}`, +x]);
  const dir = path.resolve(PROJECT, opt('stills-dir', 'stills'));
  const tmp = path.join(BUILD, 'stills-tmp');
  fs.mkdirSync(dir, {recursive: true});
  fs.mkdirSync(tmp, {recursive: true});
  const t0 = Date.now();
  let failures = 0;
  const lateAll = new Set();
  log(`${shots.length} stills, ${WORKERS} at a time -> ${dir}`);
  await pool(shots, WORKERS, async ([name, t]) => {
    const f = Math.min(FRAMES - 1, Math.max(0, Math.round(t * FPS)));
    const mp4 = path.join(tmp, `still_${f}.mp4`);
    let r = await renderRange(f, f, mp4);
    // Revideo 0.11 sometimes loses a single-frame render's temp folder ("The thread is not available in the
    // current context", then ffmpeg cannot open .../visuals.mp4); seen on unchanged projects too, and the same
    // still renders on its own. One retry, said out loud; a second failure is real.
    if (!r.ok) { console.error(`  still ${name} failed (${r.why}); retrying once`); r = await renderRange(f, f, mp4); }
    if (!r.ok) { failures++; console.error(`  still ${name} failed: ${r.why}`); return; }
    execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', mp4, '-frames:v', '1', path.join(dir, `${name}.png`)]);
    fs.rmSync(mp4, {force: true});
    r.late.forEach(x => lateAll.add(x));
    log(`  still ${name}  t=${t.toFixed(2)}  (${r.secs.toFixed(0)} s)`);
  });
  if (lateAll.size) log(`LATE cues (line@time +seconds late: an animation ran past the next cue; shorten it or schedule it with when()): ${[...lateAll].join(', ')}`);
  log(`stills done in ${fmtMin((Date.now() - t0) / 1000)}${failures ? `, ${failures} failed` : ''}. Now open them (Read the PNGs).`);
  process.exit(failures ? 1 : 0);
}

// ------------------------------------------------------------------ bench
if (opt('bench')) {
  const secs = +opt('bench', 3);
  const a = Math.max(0, Math.round((TOTAL / 2 - secs / 2) * FPS)), b = Math.min(FRAMES - 1, a + Math.round(secs * FPS) - 1);
  const file = path.join(BUILD, 'bench.mp4');
  let first = 0, firstP = 0, lastT = 0, lastP = 0;
  const r = await renderRange(a, b, file, p => {
    const now = Date.now();
    if (!first && p > 0) { first = now; firstP = p; }
    lastT = now; lastP = p;
  });
  if (!r.ok) die(`bench render failed: ${r.why}`);
  const n = b - a + 1;
  const steady = first && lastT > first && lastP > firstP ? (n * (lastP - firstP)) / ((lastT - first) / 1000) : n / r.secs;
  const overhead = Math.max(0, r.secs - n / steady);
  const segs = Math.ceil(TOTAL / SEG);
  const etaS = FRAMES / (steady * WORKERS * 0.85) + (segs * overhead) / WORKERS + 5;
  log(`one worker: ${steady.toFixed(1)} frames/s steady, ${overhead.toFixed(0)} s start-up per segment.`);
  log(`film: ${FRAMES} frames (${TOTAL.toFixed(1)} s) -> about ${fmtMin(etaS)} with ${WORKERS} workers and ${SEG} s segments.`);
  if (etaS / 60 > 100) log('longer than one 2-hour job: run with --max-minutes 100 and re-run the same command until it says done.');
  fs.rmSync(file, {force: true});
  process.exit(0);
}

// ------------------------------------------------------------------ preview range
if (opt('range')) {
  const [t0, t1] = opt('range').split(',').map(Number);
  const out = path.resolve(PROJECT, opt('out', 'build/preview.mp4'));
  const a = Math.max(0, Math.round(t0 * FPS)), b = Math.min(FRAMES - 1, Math.round(t1 * FPS) - 1);
  const r = await renderRange(a, b, out, null);
  if (!r.ok) die(`preview failed: ${r.why}`);
  log(`wrote ${out} (${(b - a + 1)} frames in ${r.secs.toFixed(0)} s)${r.late.length ? '\nLATE: ' + r.late.join(', ') : ''}`);
  process.exit(0);
}

// ------------------------------------------------------------------ segmented full render
const OUT = path.resolve(PROJECT, opt('out', 'build/silent.mp4'));
const segDir = path.join(BUILD, 'segments');
fs.mkdirSync(segDir, {recursive: true});
const manPath = path.join(segDir, 'manifest.json');
const key = {fps: FPS, width: TIMING.width, height: TIMING.height, frames: FRAMES, segment: SEG, timing: TIMING.hash, src: srcHash(), crf: CRF};
// a resumed manifest is accepted only if this script could have written it (see segmanifest.mjs)
let man = fs.existsSync(manPath) ? JSON.parse(fs.readFileSync(manPath, 'utf8')) : null;
if (man && !manifestOk(man, FRAMES)) { log('segments/manifest.json is not one this script wrote: starting the segments over'); man = null; }
if (!man || JSON.stringify(man.key) !== JSON.stringify(key)) {
  if (man && man.segments.some(s => s.done)) log('scenes, timing or settings changed since the last run: starting the segments over');
  for (const f of fs.readdirSync(segDir)) if (f.startsWith('seg_')) fs.rmSync(path.join(segDir, f), {force: true});
  const per = Math.max(1, Math.round(SEG * FPS)), segs = [];
  for (let a = 0, i = 0; a < FRAMES; a += per, i++) {
    const b = Math.min(FRAMES, a + per);
    segs.push({i, from: +(a / FPS).toFixed(3), to: +(b / FPS).toFixed(3), a, b, file: `seg_${String(i).padStart(4, '0')}.mp4`, done: false});
  }
  man = {key, total: TOTAL, segments: segs};
}
const saveMan = () => { fs.writeFileSync(manPath + '.tmp', JSON.stringify(man, null, 1)); fs.renameSync(manPath + '.tmp', manPath); };
saveMan();
const todo = man.segments.filter(s => !s.done);
const todoFrames = todo.reduce((n, s) => n + s.b - s.a, 0);
log(`${man.segments.length} segments of ${SEG} s, ${todo.length} to render (${todoFrames} frames), ${WORKERS} workers; chromium ${CHROME ?? "(puppeteer's own)"}`);
const started = Date.now();
const inflight = new Map();
let doneFrames = 0, stopped = false, errors = 0;
const allLate = [];
const tick = setInterval(() => {
  const partial = [...inflight.values()].reduce((n, x) => n + x.p * x.n, 0);
  const got = doneFrames + partial, el = (Date.now() - started) / 1000;
  if (got > 0) log(`  ${Math.round(got)}/${todoFrames} frames  ${(got / el).toFixed(1)} fps  eta ${fmtMin((todoFrames - got) / (got / el))}`);
}, 20000);
await pool(todo, WORKERS, async s => {
  if ((Date.now() - started) / 60000 > MAXMIN) { stopped = true; return; }
  const n = s.b - s.a, state = {p: 0, n};
  inflight.set(s.i, state);
  const tmp = path.join(segDir, s.file.replace(/\.mp4$/, '.part.mp4'));
  const r = await renderRange(s.a, s.b - 1, tmp, p => { state.p = p; });
  inflight.delete(s.i);
  if (!r.ok) { errors++; console.error(`  segment ${s.i} failed: ${r.why}`); return; }
  const got = probeFrames(tmp);
  if (got !== n) log(`  warning: segment ${s.i} has ${got} frames, expected ${n}`);
  fs.renameSync(tmp, path.join(segDir, s.file));
  man.segments[s.i].done = true;
  man.segments[s.i].secs = +r.secs.toFixed(1);
  saveMan();
  doneFrames += n;
  allLate.push(...r.late);
  log(`  segment ${s.i + 1}/${man.segments.length} done (${s.from}-${s.to} s) in ${r.secs.toFixed(0)} s, ${(n / r.secs).toFixed(1)} fps`);
});
clearInterval(tick);
if (allLate.length) log(`LATE cues (line@time +seconds late: an animation ran past the next cue; shorten it or schedule it with when()): ${[...new Set(allLate)].join(', ')}`);
const left = man.segments.filter(s => !s.done).length;
if (errors) die(`${errors} segment(s) failed; fix the error above and run the same command again (finished segments are kept)`);
if (left) { log(`stopped at the ${MAXMIN}-minute budget: ${left} segments left. Run the same command again to resume.`); process.exit(3); }
const list = path.join(segDir, 'list.txt');
fs.writeFileSync(list, man.segments.map(s => concatLine(path.join(segDir, s.file))).join('\n') + '\n');
fs.mkdirSync(path.dirname(OUT), {recursive: true});
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-map', '0:v:0', '-c', 'copy', '-an', '-movflags', '+faststart', OUT]);
const dur = probeDuration(OUT);
const el = (Date.now() - started) / 1000;
log(`wrote ${OUT}: ${dur.toFixed(2)} s (timing total ${TOTAL.toFixed(2)} s) in ${fmtMin(el)}, ${(todoFrames / Math.max(1, el)).toFixed(1)} fps overall`);
if (Math.abs(dur - TOTAL) > 0.5) die(`duration ${dur.toFixed(2)} s differs from the timing total ${TOTAL.toFixed(2)} s`);
