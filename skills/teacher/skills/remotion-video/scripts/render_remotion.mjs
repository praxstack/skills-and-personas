#!/usr/bin/env node
// render_remotion.mjs: render a Remotion project to build/silent.mp4 in resumable segments.
//
// The project layout is the one vstate.py uses: <project>/timing.json, <project>/source (the Remotion project,
// copied from the skill's assets/template), <project>/build. The script:
//   1. uses installed npm dependencies; missing packages need TEACHER_ALLOW_NETWORK=1 setup
//   2. bundles once (`npx remotion bundle`) and re-bundles only when source files change
//   3. renders frame ranges (`npx remotion render <bundle> <Comp> --frames=a-b`) into build/segments/,
//      recording each in build/segments/manifest.json {"segments": [{"from","to","done"}]}; done ones are skipped
//   4. stops cleanly when --max-minutes runs out (exit 3: run the same command again to continue)
//   5. concatenates the segments losslessly (same encoder settings, -c copy) into build/silent.mp4,
//      H.264 yuv420p bt709 (Remotion's default output is yuvj420p; --color-space=bt709 fixes it at the source)
//
// Usage:
//   node render_remotion.mjs --project . [--concurrency 2] [--segment 30] [--max-minutes 100] [--crf 18]
//   node render_remotion.mjs --project . --bench [3]           render 3 s from the middle, print fps and ETA
//   node render_remotion.mjs --project . --stills chapters      one still per chapter  -> <project>/stills/
//   node render_remotion.mjs --project . --stills lines         one still per line (65% into its voice)
//   node render_remotion.mjs --project . --stills busy          the 8 longest lines
//   node render_remotion.mjs --project . --stills 12.5,40       seconds;  --stills f:300,900  frames
// Options: --comp Film  --browser <path>  --force (discard finished segments)  --out build/silent.mp4
//          --stills-dir stills  --scale 1 (stills)  --keep-segments
// Environment: REMOTION_BROWSER_EXECUTABLE overrides the browser. On a laptop with no override and no
// /opt/pw-browsers or a cached headless shell, browser acquisition requires TEACHER_ALLOW_NETWORK=1.
// Cached browsers may also be supplied through --browser or REMOTION_BROWSER_EXECUTABLE.
import {spawn, spawnSync} from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {concatLine} from './segmanifest.mjs';

// ------------------------------------------------------------------ args
const argv = process.argv.slice(2);
const opt = {project: '.', comp: 'Film', concurrency: 2, segment: 30, maxMinutes: 100, crf: 18, jpegQuality: 92, scale: 1};
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  const next = () => argv[++i];
  const peekNum = () => (argv[i + 1] !== undefined && !argv[i + 1].startsWith('--') ? argv[++i] : undefined);
  if (a === '--project') opt.project = next();
  else if (a === '--comp') opt.comp = next();
  else if (a === '--concurrency') opt.concurrency = Number(next());
  else if (a === '--segment') opt.segment = Number(next());
  else if (a === '--max-minutes') opt.maxMinutes = Number(next());
  else if (a === '--crf') opt.crf = Number(next());
  else if (a === '--browser') opt.browser = next();
  else if (a === '--bench') opt.bench = Number(peekNum() ?? 3);
  else if (a === '--stills') opt.stills = next();
  else if (a === '--stills-dir') opt.stillsDir = next();
  else if (a === '--scale') opt.scale = Number(next());
  else if (a === '--out') opt.out = next();
  else if (a === '--force') opt.force = true;
  else if (a === '--keep-segments') opt.keep = true;
  else if (a === '-h' || a === '--help') {
    console.log(fs.readFileSync(new URL(import.meta.url)).toString().split('\n').filter((l) => l.startsWith('//')).map((l) => l.slice(3)).join('\n'));
    process.exit(0);
  } else {
    console.error(`unknown argument ${a} (see --help)`);
    process.exit(2);
  }
}

const log = (...a) => console.log(...a);
const die = (msg, code = 1) => {
  console.error(`error: ${msg}`);
  process.exit(code);
};
const fmtMin = (s) => (s >= 3600 ? `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min` : s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`);

// ------------------------------------------------------------------ project
const project = path.resolve(opt.project);
const statePath = path.join(project, '.video-state.json');
const state = fs.existsSync(statePath) ? JSON.parse(fs.readFileSync(statePath, 'utf8')) : {config: {}};
const cfg = state.config ?? {};
const source = path.resolve(project, cfg.source ?? 'source');
const build = path.join(project, 'build');
const segDir = path.join(build, 'segments');
const bundleDir = path.join(build, 'bundle');
const silent = path.resolve(project, opt.out ?? cfg.silent ?? 'build/silent.mp4');
if (!fs.existsSync(path.join(source, 'package.json'))) die(`no Remotion project at ${source} (copy the skill's assets/template there)`);

const srcTimingPath = path.join(source, 'src', 'timing.json');
if (!fs.existsSync(srcTimingPath)) die(`${srcTimingPath} missing: run voice.py --project . --emit source/src/timing.json`);
const timing = JSON.parse(fs.readFileSync(srcTimingPath, 'utf8'));
const projTimingPath = path.join(project, 'timing.json');
if (fs.existsSync(projTimingPath)) {
  const pt = JSON.parse(fs.readFileSync(projTimingPath, 'utf8'));
  if (pt.hash !== timing.hash) die(`source/src/timing.json (hash ${timing.hash}) is not the project's timing.json (hash ${pt.hash}): re-run voice.py with --emit source/src/timing.json`);
}
const fps = timing.fps || 30;
const total = Math.max(1, Math.round(timing.total * fps)); // same formula as src/lib/timing.ts

// ------------------------------------------------------------------ browser
const networkAllowed = process.env.TEACHER_ALLOW_NETWORK === '1';
const executable = (file) => {
  try { fs.accessSync(file, fs.constants.X_OK); return fs.statSync(file).isFile(); }
  catch { return false; }
};
// Search only Remotion's project-local cache roots, never invoke its downloader.
const cachedBrowser = (dir, depth = 0) => {
  if (depth > 6 || !fs.existsSync(dir)) return null;
  for (const entry of fs.readdirSync(dir, {withFileTypes: true}).sort((a, b) => a.name.localeCompare(b.name))) {
    const file = path.join(dir, entry.name);
    if (entry.isFile() && ['chrome-headless-shell', 'headless_shell', 'chrome-headless-shell.exe'].includes(entry.name) && executable(file)) return file;
    if (entry.isDirectory()) {
      const found = cachedBrowser(file, depth + 1);
      if (found) return found;
    }
  }
  return null;
};
const findBrowser = () => {
  if (opt.browser) return opt.browser;
  if (process.env.REMOTION_BROWSER_EXECUTABLE) return process.env.REMOTION_BROWSER_EXECUTABLE;
  const base = '/opt/pw-browsers';
  if (fs.existsSync(base)) {
    const shells = fs.readdirSync(base).filter((d) => d.startsWith('chromium_headless_shell-')).sort().reverse();
    for (const d of shells) {
      const p = path.join(base, d, 'chrome-linux', 'headless_shell');
      if (fs.existsSync(p)) return p;
    }
  }
  for (const root of [source, project]) {
    const cached = cachedBrowser(path.join(root, 'node_modules', '.remotion'));
    if (cached) return cached;
  }
  return null; // Only explicit network opt-in permits Remotion to acquire one.
};
const browser = findBrowser();
if (browser && !executable(browser)) die(`browser is not an executable file: ${browser}`);
const browserArgs = browser ? [`--browser-executable=${browser}`] : [];

// ------------------------------------------------------------------ helpers
const run = (args, {cwd = source, quiet = false} = {}) =>
  new Promise((resolve, reject) => {
    if (['render', 'still'].includes(args[0]) && !browser && !networkAllowed) {
      return reject(new Error('No cached browser found. Supply an installed browser with --browser or '
        + 'REMOTION_BROWSER_EXECUTABLE, or explicitly allow browser acquisition with TEACHER_ALLOW_NETWORK=1.'));
    }
    const p = spawn('npx', ['--no-install', 'remotion', ...args], {cwd, env: {...process.env, FORCE_COLOR: '0',
      ...(networkAllowed ? {} : {npm_config_offline: 'true', npm_config_yes: 'false'})}});
    let last = 0;
    let tail = '';
    const onData = (d) => {
      const s = d.toString();
      tail = (tail + s).slice(-4000);
      if (quiet) return;
      for (const line of s.split(/\r|\n/)) {
        const t = line.trim();
        if (!t) continue;
        if (/error|warn/i.test(t)) log('   ' + t);
        else if (/Rendered|Encoded|Stitch/i.test(t) && Date.now() - last > 15000) {
          last = Date.now();
          log('   ' + t);
        }
      }
    };
    p.stdout.on('data', onData);
    p.stderr.on('data', onData);
    p.on('close', (code) => (code === 0 ? resolve(tail) : reject(new Error(`remotion ${args[0]} exited ${code}\n${tail}`))));
  });

const hashTree = () => {
  const h = crypto.createHash('sha256');
  const walk = (dir) => {
    if (!fs.existsSync(dir)) return;
    for (const name of fs.readdirSync(dir).sort()) {
      const p = path.join(dir, name);
      const st = fs.statSync(p);
      if (st.isDirectory()) walk(p);
      else h.update(path.relative(source, p)).update(fs.readFileSync(p));
    }
  };
  walk(path.join(source, 'src'));
  walk(path.join(source, 'public'));
  for (const f of ['package.json', 'remotion.config.ts']) if (fs.existsSync(path.join(source, f))) h.update(f).update(fs.readFileSync(path.join(source, f)));
  return h.digest('hex').slice(0, 16);
};

const ensureDeps = () => {
  if (fs.existsSync(path.join(source, 'node_modules', 'remotion'))) return;
  if (!networkAllowed) die('Missing npm dependencies. Install them separately or explicitly opt in with TEACHER_ALLOW_NETWORK=1.');
  log(`installing npm dependencies in ${source} ...`);
  const t0 = Date.now();
  const lock = fs.existsSync(path.join(source, 'package-lock.json'));
  const r = spawnSync('npm', [lock ? 'ci' : 'install', '--no-audit', '--no-fund'], {cwd: source, stdio: 'inherit'});
  if (r.status !== 0) die('npm install failed (see above); check the network/proxy and retry');
  log(`installed in ${fmtMin((Date.now() - t0) / 1000)}`);
};

const ensureBundle = async (stamp) => {
  const stampFile = path.join(bundleDir, '.stamp');
  if (fs.existsSync(stampFile) && fs.readFileSync(stampFile, 'utf8') === stamp) return;
  log('bundling ...');
  const t0 = Date.now();
  fs.rmSync(bundleDir, {recursive: true, force: true});
  await run(['bundle', 'src/index.ts', '--out-dir', bundleDir], {quiet: true});
  fs.writeFileSync(stampFile, stamp);
  log(`bundled in ${fmtMin((Date.now() - t0) / 1000)}`);
};

const renderArgs = (from, to, out) => [
  'render', bundleDir, opt.comp, out, `--frames=${from}-${to}`, `--concurrency=${opt.concurrency}`, ...browserArgs,
  '--codec=h264', `--crf=${opt.crf}`, '--pixel-format=yuv420p', '--color-space=bt709', '--muted', '--image-format=jpeg', `--jpeg-quality=${opt.jpegQuality}`, '--log=info',
];

const probe = (file) => {
  const r = spawnSync('ffprobe', ['-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=pix_fmt,nb_read_packets,width,height,r_frame_rate:format=duration', '-of', 'json', file]);
  if (r.status !== 0) return null;
  const j = JSON.parse(r.stdout.toString());
  const s = j.streams?.[0] ?? {};
  return {pix: s.pix_fmt, frames: Number(s.nb_read_packets), w: s.width, h: s.height, dur: Number(j.format?.duration)};
};

// ------------------------------------------------------------------ stills
const stillFrames = (spec) => {
  const slug = (s) => String(s).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const clampF = (x) => Math.max(0, Math.min(total - 1, Math.round(x)));
  // 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
  // previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
  const offSwap = (t) => { const l = timing.lines.find((x) => Math.abs(t - x.voiceAt) < 0.3); return !l ? t : timing.lines.find((x) => x.chapter === l.chapter) === l ? l.voiceAt + 0.4 : l.voiceAt - 0.35; };
  if (spec === 'chapters') return timing.chapters.map((c) => [`ch${c.n}-${slug(c.name)}`, clampF(offSwap(c.start + 0.45 * (c.end - c.start)) * fps)]);
  if (spec === 'lines') return timing.lines.map((l) => [`${l.start.toFixed(1).padStart(6, '0')}-${l.id}`, clampF((l.voiceAt + 0.65 * l.voiceDur) * fps)]);
  if (spec === 'busy') return [...timing.lines].sort((a, b) => b.dur - a.dur).slice(0, 8).map((l) => [`busy-${l.id}`, clampF((l.voiceAt + 0.8 * l.voiceDur) * fps)]);
  if (spec.startsWith('f:')) return spec.slice(2).split(',').map((x) => [`f${x.padStart(5, '0')}`, clampF(Number(x))]);
  return spec.split(',').map((x) => [`t${Number(x).toFixed(2).padStart(7, '0')}`, clampF(Number(x) * fps)]);
};

const doStills = async () => {
  const dir = path.resolve(project, opt.stillsDir ?? cfg.stills ?? 'stills');
  fs.mkdirSync(dir, {recursive: true});
  const shots = stillFrames(opt.stills);
  const t0 = Date.now();
  const queue = [...shots];
  const worker = async () => {
    while (queue.length) {
      const [name, frame] = queue.shift();
      const out = path.join(dir, `${name}.png`);
      await run(['still', bundleDir, opt.comp, out, `--frame=${frame}`, `--scale=${opt.scale}`, ...browserArgs, '--log=error'], {quiet: true});
      log(`still ${name}  frame ${frame} (${(frame / fps).toFixed(2)} s)  -> ${path.relative(project, out)}`);
    }
  };
  await Promise.all(Array.from({length: Math.max(1, Math.min(2, opt.concurrency))}, worker));
  log(`${shots.length} stills in ${fmtMin((Date.now() - t0) / 1000)} -> ${dir}  (open every one before attesting)`);
};

// ------------------------------------------------------------------ bench
const doBench = async () => {
  const n = Math.max(1, Math.round(opt.bench * fps));
  const from = Math.max(0, Math.min(total - n, Math.floor(total * 0.45)));
  const to = Math.min(total - 1, from + n - 1);
  fs.mkdirSync(build, {recursive: true});
  const out = path.join(build, 'bench.mp4');
  log(`bench: frames ${from}-${to} at concurrency ${opt.concurrency} ...`);
  const t0 = Date.now();
  await run(renderArgs(from, to, out));
  const sec = (Date.now() - t0) / 1000;
  const rate = (to - from + 1) / sec;
  log(`bench: ${to - from + 1} frames in ${sec.toFixed(1)} s = ${rate.toFixed(2)} fps (includes ~5 s browser start)`);
  log(`estimate for the full film (${total} frames, ${(total / fps / 60).toFixed(2)} min): ${fmtMin(total / rate)} at --concurrency ${opt.concurrency}`);
  const m = path.join(build, 'bench.json');
  fs.writeFileSync(m, JSON.stringify({frames: to - from + 1, seconds: sec, fps: rate, concurrency: opt.concurrency, total, at: new Date().toISOString()}, null, 1));
};

// ------------------------------------------------------------------ full render
const doRender = async (stamp) => {
  const t0 = Date.now();
  const budget = opt.maxMinutes * 60;
  fs.mkdirSync(segDir, {recursive: true});
  const manPath = path.join(segDir, 'manifest.json');
  const segFrames = Math.max(fps, Math.round(opt.segment * fps));
  let man = fs.existsSync(manPath) ? JSON.parse(fs.readFileSync(manPath, 'utf8')) : null;
  const fresh = !man || opt.force || man.stamp !== stamp || man.total !== total || man.segFrames !== segFrames || man.comp !== opt.comp || man.crf !== opt.crf;
  if (fresh) {
    if (man && !opt.force) log(`source, timing or settings changed since the last render: starting over (old segments discarded)`);
    for (const f of fs.readdirSync(segDir)) if (f.endsWith('.mp4')) fs.rmSync(path.join(segDir, f));
    const segments = [];
    for (let a = 0, i = 0; a < total; a += segFrames, i++) segments.push({from: a, to: Math.min(total, a + segFrames) - 1, done: false, file: `seg_${String(i).padStart(4, '0')}.mp4`});
    man = {stamp, comp: opt.comp, total, fps, segFrames, crf: opt.crf, segments};
  }
  const save = () => fs.writeFileSync(manPath, JSON.stringify(man, null, 1));
  if (!fresh && man.segments.every((s) => s.done && s.pruned)) {
    const p = fs.existsSync(silent) ? probe(silent) : null;
    if (p && p.frames === total && man.silentStamp === stamp) {
      log(`already rendered: ${path.relative(project, silent)} matches the current source and timing; nothing to do (--force to redo)`);
      return;
    }
    log('segments were pruned after the last concat and the silent render is missing or stale: rendering again');
    man.segments.forEach((s) => Object.assign(s, {done: false, pruned: false}));
  }
  save();
  const todo = man.segments.filter((s) => !s.done || !fs.existsSync(path.join(segDir, s.file)));
  log(`render: ${total} frames (${(total / fps).toFixed(2)} s) in ${man.segments.length} segments; ${man.segments.length - todo.length} done, ${todo.length} to go; concurrency ${opt.concurrency}; budget ${opt.maxMinutes} min`);
  let framesThisRun = 0;
  let secsThisRun = 0;
  for (const s of todo) {
    const n = s.to - s.from + 1;
    const elapsed = (Date.now() - t0) / 1000;
    const rate = secsThisRun > 0 ? framesThisRun / secsThisRun : man.lastFps ?? null;
    const est = rate ? n / rate + 8 : 0;
    if (elapsed + est > budget) {
      log(`budget: ${fmtMin(elapsed)} used of ${opt.maxMinutes} min; the next segment needs ~${fmtMin(est)}. Stopping cleanly.`);
      log('re-run the same command to continue; finished segments are kept.');
      process.exit(3);
    }
    const out = path.join(segDir, s.file);
    const part = out.replace(/\.mp4$/, '.part.mp4');
    log(`segment ${s.file}: frames ${s.from}-${s.to}`);
    const st = Date.now();
    await run(renderArgs(s.from, s.to, part));
    const p = probe(part);
    if (!p || p.frames !== n) die(`segment ${s.file} has ${p?.frames} frames, expected ${n}`);
    fs.renameSync(part, out);
    const sec = (Date.now() - st) / 1000;
    framesThisRun += n;
    secsThisRun += sec;
    Object.assign(s, {done: true, seconds: +sec.toFixed(1), fps: +(n / sec).toFixed(2), pix: p.pix});
    man.lastFps = +(framesThisRun / secsThisRun).toFixed(2);
    save();
    const left = man.segments.filter((x) => !x.done).reduce((a, x) => a + x.to - x.from + 1, 0);
    log(`  done in ${fmtMin(sec)} (${(n / sec).toFixed(2)} fps). ${left} frames left, ETA ${fmtMin(left / man.lastFps)}`);
  }

  // concat: identical encoder settings per segment, so stream copy is lossless
  const list = path.join(segDir, 'concat.txt');
  fs.writeFileSync(list, man.segments.map((s) => concatLine(path.join(segDir, s.file))).join('\n') + '\n');
  fs.mkdirSync(path.dirname(silent), {recursive: true});
  const tmp = silent.replace(/\.mp4$/, '.tmp.mp4');
  let r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-c', 'copy', '-movflags', '+faststart', tmp], {stdio: 'inherit'});
  if (r.status !== 0) die('ffmpeg concat failed');
  let p = probe(tmp);
  if (p.pix !== 'yuv420p') {
    // fallback (an older Remotion that ignores --color-space): convert full-range yuvj420p to tv-range yuv420p
    log(`concat is ${p.pix}; re-encoding once to yuv420p (bt709, tv range)`);
    const tmp2 = silent.replace(/\.mp4$/, '.yuv.mp4');
    r = spawnSync('ffmpeg', ['-v', 'error', '-y', '-i', tmp, '-vf', 'scale=in_range=pc:out_range=tv,format=yuv420p', '-c:v', 'libx264', '-preset', 'medium', '-crf', String(opt.crf),
      '-color_range', 'tv', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-movflags', '+faststart', tmp2], {stdio: 'inherit'});
    if (r.status !== 0) die('ffmpeg re-encode failed');
    fs.renameSync(tmp2, tmp);
    p = probe(tmp);
  }
  fs.renameSync(tmp, silent);
  log(`silent render: ${path.relative(project, silent)}  ${p.w}x${p.h}  ${p.frames} frames  ${p.dur.toFixed(3)} s  ${p.pix}  (timing total ${timing.total.toFixed(3)} s)`);
  if (p.frames !== total) die(`frame count ${p.frames} != ${total}`);
  const secs = (Date.now() - t0) / 1000;
  if (framesThisRun) log(`this run: ${framesThisRun} frames in ${fmtMin(secs)} (${(framesThisRun / secsThisRun).toFixed(2)} fps while rendering)`);
  man.silentStamp = stamp;
  save();
  if (!opt.keep) {
    // keep the manifest (the render gate reads it), drop the bulky pieces
    for (const s of man.segments) fs.rmSync(path.join(segDir, s.file), {force: true});
    man.segments.forEach((s) => (s.pruned = true));
    save();
  }
};

// ------------------------------------------------------------------ main
ensureDeps();
const stamp = hashTree();
await ensureBundle(stamp);
if (opt.stills) await doStills();
else if (opt.bench) await doBench();
else await doRender(stamp);
