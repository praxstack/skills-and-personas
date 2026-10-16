#!/usr/bin/env node
// film3d.mjs: build, benchmark, still and render the Three.js film in <project>/source with capture.mjs.
// It reads the planned size and fps from <project>/.video-state.json, rebuilds the bundle first (only rewriting
// dist/film.js when its bytes change, so finished render segments stay valid), and always renders WebGL with
// SwiftShader unless GPU=1 (a laptop with a real GPU: 20 to 50x faster).
//
//   node film3d.mjs build   [--project .]
//   node film3d.mjs bench   [--project .] [--q final|draft] [--secs 2] [--workers 2] [--size 1920x1080]
//   node film3d.mjs stills  [--project .] [chapters|lines|busy|12.5,40] [--q final|draft] [--size 1280x720] [--out stills]
//   node film3d.mjs render  [--project .] [--q final|draft] [--workers 2] [--max-minutes 100] [--size WxH] [--out build/silent.mp4]
//
// render is resumable: segments are recorded in <out dir>/segments/manifest.json; when the budget runs out it
// exits with code 3 and the same command continues where it stopped. A draft render (--q draft) writes
// build/draft/draft.mp4 by default so it never mixes with the final segments.
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const cmd = argv[0];
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d; };
const pos = argv.slice(1).filter((a, i, all) => !a.startsWith('--') && !(i > 0 && all[i - 1].startsWith('--')));
const PROJ = path.resolve(opt('project', '.'));
const SRC = path.join(PROJ, 'source');
if (!['build', 'bench', 'stills', 'render'].includes(cmd)) {
  console.log(fs.readFileSync(fileURLToPath(import.meta.url), 'utf8').split('\n').slice(1, 15).map((l) => l.replace(/^\/\/ ?/, '')).join('\n'));
  process.exit(cmd ? 2 : 0);
}
const die = (m) => { console.error(m); process.exit(2); };
if (!fs.existsSync(path.join(SRC, 'build.mjs'))) die(`no ${SRC}/build.mjs: copy the template first (cp -r $SKILL/assets/template ${SRC})`);
if (!fs.existsSync(path.join(SRC, 'node_modules', 'three'))) die(`dependencies missing: (cd ${SRC} && npm ci)`);
if (!fs.existsSync(path.join(SRC, 'src', 'timing.js'))) die('source/src/timing.js missing: run voice.py --project . --emit source/src/timing.js');

const state = fs.existsSync(path.join(PROJ, '.video-state.json')) ? JSON.parse(fs.readFileSync(path.join(PROJ, '.video-state.json'), 'utf8')) : { config: {} };
const cfg = { width: 1920, height: 1080, fps: 30, ...state.config };
let [W, H] = (opt('size') || `${cfg.width}x${cfg.height}`).split('x').map(Number);
const FPS = +opt('fps', cfg.fps);
const Q = opt('q', 'final');
if (!['final', 'fast', 'draft'].includes(Q)) die('--q must be final, fast or draft');
const PAGE = path.join(SRC, Q === 'final' ? 'index.html' : `${Q}.html`);

function run(bin, args, opts = {}) {
  const r = spawnSync(bin, args, { stdio: 'inherit', cwd: PROJ, ...opts });
  if (r.error) die(String(r.error));
  return r.status ?? 1;
}
// 1. bundle
if (run(process.execPath, [path.join(SRC, 'build.mjs')], { cwd: SRC }) !== 0) die('build failed');
if (cmd === 'build') process.exit(0);

const capture = path.join(HERE, 'capture.mjs');
const gl = process.env.GPU ? [] : ['--webgl'];
const common = ['--page', PAGE, '--width', String(W), '--height', String(H), '--fps', String(FPS), ...gl];
const timing = path.join(PROJ, 'timing.json');

if (cmd === 'bench') {
  process.exit(run(process.execPath, [capture, ...common, '--bench', opt('secs', '2'), '--workers', opt('workers', '2')]));
}
if (cmd === 'stills') {
  let which = pos[0] || 'chapters';
  if (which === 'busy') {
    const tm = JSON.parse(fs.readFileSync(timing, 'utf8'));
    which = [...tm.lines].sort((a, b) => b.dur - a.dur).slice(0, 8).map((l) => (l.voiceAt + 0.8 * l.voiceDur).toFixed(2)).join(',');
  }
  const out = path.resolve(PROJ, opt('out', state.config?.stills || 'stills'));
  process.exit(run(process.execPath, [capture, ...common, '--stills', which, '--timing', timing, '--stills-dir', out]));
}
if (cmd === 'render') {
  const out = path.resolve(PROJ, opt('out', Q === 'draft' ? 'build/draft/draft.mp4' : (state.config?.silent || 'build/silent.mp4')));
  fs.mkdirSync(path.dirname(out), { recursive: true });
  const args = [capture, ...common, '--out', out, '--workers', opt('workers', '2'), '--segment', opt('segment', '10'), '--max-minutes', opt('max-minutes', '100')];
  if (opt('from')) args.push('--from', opt('from'));
  if (opt('to')) args.push('--to', opt('to'));
  const code = run(process.execPath, args);
  if (code === 3) console.log(`\nNot finished yet (budget). Run the same command again to continue:\n  node ${process.argv[1]} ${argv.join(' ')}`);
  process.exit(code);
}
