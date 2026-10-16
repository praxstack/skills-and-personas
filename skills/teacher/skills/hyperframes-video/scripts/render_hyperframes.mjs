#!/usr/bin/env node
// render_hyperframes.mjs: render a HyperFrames explainer to build/silent.mp4 in resumable segments, take review
// stills, or benchmark. Wraps the HyperFrames CLI (pinned in source/package.json).
//
// The CLI has no frame-range flag, so the template's index.html wraps the film timeline and reads two composition
// variables, segFrom and segTo (seconds). Each segment is one `hyperframes render --variables '{"segFrom":a,"segTo":b}'`
// whose length is exactly (b - a) frames; segments are recorded in build/segments/manifest.json, finished ones are
// skipped on the next run, and the pieces are joined losslessly (same encoder settings) into build/silent.mp4.
//
// Usage (from the project folder; the HyperFrames project is <project>/source):
//   node render_hyperframes.mjs --project .                       full render (resumes; re-run until it says done)
//        [--segment 20] [--workers 2] [--quality high] [--max-minutes 100] [--fps 30] [--force]
//   node render_hyperframes.mjs --project . --bench 6             time 6 s from the middle, print fps and the ETA
//   node render_hyperframes.mjs --project . --stills chapters     one PNG per chapter into <project>/stills/
//                                            --stills lines        one per narration line (65% into the voice)
//                                            --stills busy         the 8 longest lines
//                                            --stills 3.5,12,40.2  exact times
//   node render_hyperframes.mjs --project . --range 18,24 [--out build/preview.mp4] [--quality draft]   a quick look at a part
//   node render_hyperframes.mjs --project . --lint                lint only
//   node render_hyperframes.mjs --project . --check               lint + runtime + layout + contrast at every line
// Env (set automatically when unset): HYPERFRAMES_BROWSER_PATH (the sandbox headless shell when present),
// HYPERFRAMES_SKIP_SKILLS=1, HYPERFRAMES_NO_TELEMETRY=1. Exit codes: 0 done, 1 error, 2 setup problem, 3 budget hit.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawn, spawnSync, execFileSync } from 'node:child_process';

import { manifestOk, concatLine } from './segmanifest.mjs';
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length && !argv[i + 1].startsWith('--') ? argv[i + 1] : d; };
const flag = (k) => argv.includes('--' + k);
const PROJECT = path.resolve(opt('project', '.'));
const SRC = path.resolve(PROJECT, opt('source', 'source'));
const OUT = path.resolve(PROJECT, opt('out', flag('range') || opt('range') ? 'build/preview.mp4' : 'build/silent.mp4'));
const WORKERS = opt('workers', '2');
const QUALITY = opt('quality', opt('range') ? 'draft' : 'high');
const SEG = +opt('segment', 20);
const MAXMIN = +opt('max-minutes', 100);
const HEADLESS = '/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell';

const die = (msg, code = 1) => { console.error(msg); process.exit(code); };
const env = { ...process.env, HYPERFRAMES_SKIP_SKILLS: '1', HYPERFRAMES_NO_TELEMETRY: '1' };
if (!env.HYPERFRAMES_BROWSER_PATH && fs.existsSync(HEADLESS)) env.HYPERFRAMES_BROWSER_PATH = HEADLESS;

// ------------------------------------------------------------------ setup checks
if (!fs.existsSync(path.join(SRC, 'index.html'))) die(`no HyperFrames project at ${SRC} (copy the skill's assets/template there)`, 2);
const BIN = path.join(SRC, 'node_modules', '.bin', 'hyperframes');
if (!fs.existsSync(BIN)) die(`HyperFrames is not installed in ${SRC}. Run:  cd ${SRC} && npm install   (about 10 s)`, 2);
if (!fs.existsSync(path.join(SRC, 'vendor', 'js', 'gsap.min.js')) || !fs.existsSync(path.join(SRC, 'vendor', 'fonts.css'))) {
  console.log('vendor/ missing: running setup.mjs');
  execFileSync(process.execPath, [path.join(SRC, 'setup.mjs')], { stdio: 'inherit' });
}
function readTiming() {
  const p = path.join(SRC, 'timing.js');
  if (!fs.existsSync(p)) die(`no ${p}: run voice.py --emit source/timing.js`, 2);
  const txt = fs.readFileSync(p, 'utf8');
  return JSON.parse(txt.slice(txt.indexOf('{'), txt.lastIndexOf('}') + 1));
}
const TM = readTiming();
const FPS = +opt('fps', TM.fps || 30);
const NFRAMES = Math.round(TM.total * FPS);
const pj = path.join(PROJECT, 'timing.json');
if (fs.existsSync(pj)) {
  const h = JSON.parse(fs.readFileSync(pj, 'utf8')).hash;
  if (h !== TM.hash) console.warn(`warning: source/timing.js (hash ${TM.hash}) is not the project's timing.json (hash ${h}); run voice.py --emit source/timing.js`);
}
const run = (args, o = {}) => spawnSync(BIN, args, { cwd: SRC, env, encoding: 'utf8', maxBuffer: 64 << 20, ...o });
const strip = (s) => String(s || '').replace(/\x1b\[[0-9;]*m/g, '');
const probe = (f) => JSON.parse(execFileSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=codec_name,pix_fmt,nb_frames,width,height,r_frame_rate:format=duration', '-of', 'json', f], { encoding: 'utf8' }));

function lint() {
  const r = run(['lint', '.']);
  const out = strip(r.stdout) + strip(r.stderr);
  const m = out.match(/(\d+) error/);
  if (r.status !== 0 || (m && +m[1] > 0)) { console.error(out); die('hyperframes lint found errors (above); fix them first'); }
  console.log('lint: ' + (out.match(/◇\s*(.*)/) || [, 'ok'])[1].trim());
}
if (flag('lint')) { lint(); process.exit(0); }

// ------------------------------------------------------------------ check (lint + runtime + layout + contrast)
// `hyperframes check` sampled at every line (65% into its voice): overlapping text, text under an opaque panel,
// text overflowing its box, text in the caption band (bottom 1/6) and WCAG contrast. Decorative layers in the kit
// carry data-layout-ignore, so what it reports is about content. Errors exit 1; warnings are for you to judge.
if (flag('check')) {
  const at = [...new Set(TM.lines.map((l) => +(l.voiceAt + 0.65 * l.voiceDur).toFixed(2)))].sort((a, b) => a - b);
  const lineAt = (t) => (TM.lines.find((l) => t >= l.start && t < l.end) || TM.lines[TM.lines.length - 1]).id;
  const t0 = Date.now();
  console.log(`check: sampling ${at.length} line times (about ${Math.round(at.length * 6 + 40)} s)`);
  const r = run(['check', '.', '--json', '--at', at.join(','), '--caption-zone', 'x0=0;y0=.833;x1=1;y1=1;severity=warning'], { timeout: 30 * 60 * 1000 });
  const out = String(r.stdout || '');
  let rep;
  try { rep = JSON.parse(out.slice(out.indexOf('{'), out.lastIndexOf('}') + 1)); } catch (e) { die(`hyperframes check gave no JSON (exit ${r.status}):\n${strip(out + r.stderr).slice(-3000)}`); }
  let errors = 0, warnings = 0, infos = 0;
  for (const sec of ['lint', 'runtime', 'layout', 'contrast', 'motion']) {
    const s = rep[sec];
    if (!s) continue;
    errors += s.errorCount || 0; warnings += s.warningCount || 0; infos += s.infoCount || 0;
    console.log(`${sec.padEnd(8)} ${s.errorCount || 0} errors, ${s.warningCount || 0} warnings` + (s.infoCount ? `, ${s.infoCount} transient (info)` : ''));
    for (const f of s.findings || []) {
      if (f.severity === 'info' && (s.infoCount || 0) > 25) continue; // transient (one sample): listed when few, worth a glance
      const t = typeof f.time === 'number' ? f.time : null;
      console.log(`  [${f.severity === 'info' ? 'transient' : f.severity}] ${t != null ? `${t.toFixed(2)} s (${lineAt(t)})` : ''} ${f.code}: "${String(f.text || '').slice(0, 50)}" ${f.message || ''}` +
        (f.containerSelector ? `\n      ${f.selector} | under/inside ${f.containerSelector}` : f.selector ? `\n      ${f.selector}` : ''));
    }
  }
  console.log(`check: ${errors} errors, ${warnings} warnings, ${infos} transient in ${((Date.now() - t0) / 1000).toFixed(0)} s. ` +
    'Look at the still for each finding; fix real overlaps, or mark a deliberate one (data-layout-allow-overlap / -overflow / -occlusion on the text).');
  process.exit(errors ? 1 : 0);
}

// one segment render: frames [a, b) of the film into file
function renderRange(a, b, file, quality = QUALITY) {
  return new Promise((resolve, reject) => {
    const vars = JSON.stringify({ segFrom: +(a / FPS).toFixed(6), segTo: +(b / FPS).toFixed(6) });
    const args = ['render', '.', '-o', file, '-f', String(FPS), '-q', quality, '-w', String(WORKERS), '--variables', vars, '--quiet'];
    const p = spawn(BIN, args, { cwd: SRC, env, stdio: ['ignore', 'pipe', 'pipe'] });
    let log = '';
    p.stdout.on('data', (d) => { log += d; });
    p.stderr.on('data', (d) => { log += d; });
    p.on('close', (code) => {
      if (code !== 0 || !fs.existsSync(file)) return reject(new Error(`hyperframes render failed (exit ${code}) for frames ${a}-${b}:\n${strip(log).slice(-3000)}`));
      const s = probe(file).streams[0];
      if (+s.nb_frames !== b - a) return reject(new Error(`segment ${file} has ${s.nb_frames} frames, expected ${b - a}`));
      resolve();
    });
  });
}

// ------------------------------------------------------------------ stills
if (opt('stills')) {
  const kind = opt('stills');
  const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  let shots;
  // a chapter still 45% in, moved off a caption swap (the old caption fades out as the next line's comes in: ~0.35 s
  // where both are faint) to just before it, where the previous line is at rest (entrances often start at voiceAt),
  // or, at the chapter's first line (before it is the chapter card), just after it
  const offSwap = (t) => { const l = TM.lines.find((x) => t > x.voiceAt - 0.3 && t < x.voiceAt + 0.3); return !l ? t : TM.lines.find((x) => x.chapter === l.chapter) === l ? l.voiceAt + 0.4 : l.voiceAt - 0.35; };
  if (kind === 'chapters') shots = TM.chapters.map((c) => [`ch${c.n}-${slug(c.name)}`, offSwap(c.start + 0.45 * (c.end - c.start))]);
  else if (kind === 'lines') shots = TM.lines.map((l) => [`${l.start.toFixed(1).padStart(6, '0')}-${l.id}`, l.voiceAt + 0.65 * l.voiceDur]);
  else if (kind === 'busy') shots = [...TM.lines].sort((x, y) => y.dur - x.dur).slice(0, 8).map((l) => [`${l.start.toFixed(1).padStart(6, '0')}-${l.id}`, l.voiceAt + 0.8 * l.voiceDur]);
  else shots = kind.split(',').map((x) => [`t${(+x).toFixed(2).padStart(7, '0')}`, +x]);
  shots = shots.map(([n, t]) => [n, Math.min(Math.max(0, t), TM.total - 0.05)]);
  const dir = path.resolve(PROJECT, opt('stills-dir', 'stills'));
  const tmp = path.join(PROJECT, 'build', 'snap-tmp');
  fs.rmSync(tmp, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  if (!flag('keep')) for (const f of fs.readdirSync(dir)) if (/\.(png|jpe?g)$/i.test(f)) fs.unlinkSync(path.join(dir, f));
  lint();
  const t0 = Date.now();
  const r = run(['snapshot', '.', '--at', shots.map((s) => s[1].toFixed(3)).join(','), '--no-end', '-o', tmp, '--describe', 'false', '--timeout', '20000']);
  if (r.status !== 0) die(strip(r.stdout + r.stderr).slice(-3000));
  const files = fs.readdirSync(tmp).filter((f) => /^frame-\d+-at-.*\.png$/.test(f)).sort((x, y) => +x.split('-')[1] - +y.split('-')[1]);
  if (files.length !== shots.length) die(`snapshot wrote ${files.length} frames, expected ${shots.length}`);
  files.forEach((f, i) => { fs.renameSync(path.join(tmp, f), path.join(dir, `${shots[i][0]}.png`)); console.log('still', shots[i][0], shots[i][1].toFixed(2)); });
  fs.rmSync(tmp, { recursive: true, force: true });
  const nImg = fs.readdirSync(dir).filter((f) => /\.png$/i.test(f)).length, cols = 4, rows = Math.ceil(nImg / cols);
  spawnSync('ffmpeg', ['-v', 'error', '-y', '-pattern_type', 'glob', '-i', path.join(dir, '*.png'), '-vf', `scale=480:-1,tile=${cols}x${rows}:padding=4:color=0x111111`, '-frames:v', '1', path.join(dir, 'sheet.jpg')]);
  console.log(`${shots.length} new stills (${nImg} in all) in ${dir} (${((Date.now() - t0) / 1000).toFixed(1)} s); contact sheet: ${path.join(dir, 'sheet.jpg')}`);
  process.exit(0);
}

// ------------------------------------------------------------------ bench / range preview
if (opt('bench') || flag('bench')) {
  const secs = +(opt('bench', 6)) || 6;
  lint();
  const mid = Math.round((NFRAMES / 2) - (secs * FPS) / 2), a = Math.max(0, mid), b = Math.min(NFRAMES, a + Math.round(secs * FPS));
  const f = path.join(PROJECT, 'build', 'bench.mp4');
  fs.mkdirSync(path.dirname(f), { recursive: true });
  const t0 = Date.now();
  await renderRange(a, b, f).catch((e) => die(e.message));
  const wall = (Date.now() - t0) / 1000, rate = (b - a) / wall;
  const segs = Math.ceil(NFRAMES / (SEG * FPS));
  const eta = NFRAMES / rate / 60;
  console.log(`bench: ${b - a} frames in ${wall.toFixed(1)} s = ${rate.toFixed(2)} frames/s with ${WORKERS} workers (quality ${QUALITY}, includes ~5 s start-up per call)`);
  console.log(`film: ${NFRAMES} frames (${(TM.total / 60).toFixed(2)} min) in ${segs} segments of ${SEG} s: about ${eta.toFixed(1)} min (${(eta / (TM.total / 60)).toFixed(1)} min per film minute)`);
  if (eta > MAXMIN) console.log(`longer than the ${MAXMIN}-minute budget: run the render, and run the same command again until it says done`);
  fs.rmSync(f, { force: true });
  process.exit(0);
}
if (opt('range')) {
  const [x, y] = opt('range').split(',').map(Number);
  const a = Math.max(0, Math.round(x * FPS)), b = Math.min(NFRAMES, Math.round(y * FPS));
  lint();
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const t0 = Date.now();
  await renderRange(a, b, OUT).catch((e) => die(e.message));
  console.log(`wrote ${OUT}: ${((b - a) / FPS).toFixed(2)} s (${b - a} frames) in ${((Date.now() - t0) / 1000).toFixed(1)} s`);
  process.exit(0);
}

// ------------------------------------------------------------------ segmented full render
function treeHash(dir) {
  const h = crypto.createHash('sha1');
  const walk = (d) => {
    for (const e of fs.readdirSync(d, { withFileTypes: true }).sort((a, b) => (a.name < b.name ? -1 : 1))) {
      if (['node_modules', '.git', 'renders', 'snapshots', 'build', '.hyperframes'].includes(e.name) || e.name.endsWith('.mp4')) continue;
      const p = path.join(d, e.name);
      if (e.isDirectory()) walk(p);
      else { h.update(path.relative(dir, p)); h.update(fs.readFileSync(p)); }
    }
  };
  walk(dir);
  return h.digest('hex').slice(0, 16);
}
lint();
const segDir = path.join(path.dirname(OUT), 'segments');
fs.mkdirSync(segDir, { recursive: true });
const manPath = path.join(segDir, 'manifest.json');
const key = { tool: 'hyperframes', fps: FPS, quality: QUALITY, frames: NFRAMES, segment: SEG, timing: TM.hash, source: treeHash(SRC) };
// a resumed manifest is accepted only if this script could have written it (see segmanifest.mjs)
let man = fs.existsSync(manPath) ? JSON.parse(fs.readFileSync(manPath, 'utf8')) : null;
if (man && !manifestOk(man, NFRAMES)) { console.log('segments/manifest.json is not one this script wrote: starting the segments over'); man = null; }
if (man && (flag('force') || JSON.stringify(man.key) !== JSON.stringify(key))) {
  if (man.segments.some((s) => s.done)) console.log(flag('force') ? '--force: starting the segments over' : 'source, timing or settings changed since the last run: starting the segments over');
  man = null;
}
if (!man) {
  for (const f of fs.readdirSync(segDir)) if (f.startsWith('seg_')) fs.rmSync(path.join(segDir, f), { recursive: true, force: true });
  const per = Math.max(1, Math.round(SEG * FPS)), segments = [];
  for (let a = 0, i = 0; a < NFRAMES; a += per, i++) {
    let b = Math.min(NFRAMES, a + per);
    if (NFRAMES - b > 0 && NFRAMES - b < per * 0.35) b = NFRAMES; // no tiny tail segment
    segments.push({ i, from: +(a / FPS).toFixed(3), to: +(b / FPS).toFixed(3), a, b, file: `seg_${String(i).padStart(4, '0')}.mp4`, done: false });
    a = b - per;
  }
  man = { key, total: TM.total, fps: FPS, frames: NFRAMES, segments };
}
const save = () => { fs.writeFileSync(manPath + '.tmp', JSON.stringify(man, null, 1)); fs.renameSync(manPath + '.tmp', manPath); };
save();
const todo = man.segments.filter((s) => !s.done);
const todoFrames = todo.reduce((n, s) => n + s.b - s.a, 0);
console.log(`${man.segments.length} segments of ~${SEG} s, ${todo.length} to render (${todoFrames} of ${NFRAMES} frames), ${WORKERS} workers, quality ${QUALITY}`);
const started = Date.now();
let doneFrames = 0;
for (const s of todo) {
  const el = (Date.now() - started) / 60000;
  const perFrame = doneFrames ? (Date.now() - started) / 1000 / doneFrames : null;
  if (el >= MAXMIN || (perFrame && el + (perFrame * (s.b - s.a)) / 60 > MAXMIN)) {
    console.log(`stopped at the ${MAXMIN}-minute budget: ${man.segments.filter((x) => !x.done).length} segments left. Run the same command again to resume.`);
    process.exit(3);
  }
  const part = path.join(segDir, s.file.replace('.mp4', '.part.mp4'));
  const t0 = Date.now();
  try { await renderRange(s.a, s.b, part); } catch (e) { die(e.message); }
  fs.renameSync(part, path.join(segDir, s.file));
  const secs = (Date.now() - t0) / 1000;
  doneFrames += s.b - s.a;
  Object.assign(man.segments[s.i], { done: true, secs: +secs.toFixed(1) });
  save();
  const rate = doneFrames / ((Date.now() - started) / 1000);
  const left = todoFrames - doneFrames;
  console.log(`  segment ${s.i + 1}/${man.segments.length} [${s.from.toFixed(2)}-${s.to.toFixed(2)} s] ${s.b - s.a} frames in ${secs.toFixed(1)} s (${((s.b - s.a) / secs).toFixed(2)} fps)  ETA ${(left / rate / 60).toFixed(1)} min`);
}
// join (stream copy: every segment comes from the same encoder settings)
const list = path.join(segDir, 'list.txt');
fs.writeFileSync(list, man.segments.map((s) => concatLine(path.join(segDir, s.file))).join('\n') + '\n');
fs.mkdirSync(path.dirname(OUT), { recursive: true });
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', OUT]);
let pr = probe(OUT), st = pr.streams[0];
if (st.codec_name !== 'h264' || st.pix_fmt !== 'yuv420p') {
  console.log(`re-encoding ${st.codec_name}/${st.pix_fmt} to h264/yuv420p`);
  const tmp = OUT.replace(/\.mp4$/, '.reenc.mp4');
  execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', OUT, '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', tmp]);
  fs.renameSync(tmp, OUT);
  pr = probe(OUT); st = pr.streams[0];
}
const dur = +pr.format.duration;
console.log(`wrote ${OUT}: ${st.nb_frames} frames, ${dur.toFixed(3)} s (timing total ${TM.total} s), ${st.width}x${st.height} ${st.codec_name}/${st.pix_fmt}; this run ${((Date.now() - started) / 60000).toFixed(1)} min`);
if (+st.nb_frames !== NFRAMES) die(`frame count ${st.nb_frames} != expected ${NFRAMES}`);
