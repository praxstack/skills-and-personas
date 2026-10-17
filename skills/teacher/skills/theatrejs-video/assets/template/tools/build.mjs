#!/usr/bin/env node
// build.mjs: timing.js + src/film/shots.js -> theatre-state.json (Theatre keyframes), then bundle the page.
//
//   node tools/build.mjs            state + dist/film.js + dist/film.css        (npm run build)
//   node tools/build.mjs --3d       also dist/film3d.js (needs: npm i --save-exact three@0.186.1)
//   node tools/build.mjs --studio   also dist/studio.js (laptop only; needs: npm i --save-exact @theatre/studio@0.7.2)
//   node tools/build.mjs --state    only the state (no bundling)
//
// It prints a coverage report: narration lines on which nothing but the camera moves (quality bar: every line
// changes something on screen), and tweens that interrupt each other.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const has = (f) => args.includes(f);

// 1. timing (written by voice.py --emit source/timing.js)
const tsrc = fs.readFileSync(path.join(ROOT, 'timing.js'), 'utf8');
const TIMING = JSON.parse(tsrc.slice(tsrc.indexOf('{'), tsrc.lastIndexOf('}') + 1));

// 2. compile the shots against the world's Theatre objects
const imp = (p) => import(pathToFileURL(path.join(ROOT, p)).href);
const { timeline } = await imp('src/theatre/timing.js');
const { compileFilm } = await imp('src/theatre/keys.js');
const { default: world } = await imp('src/film/world.js');
const { default: shots } = await imp('src/film/shots.js');
const T = timeline(TIMING);
const W = world(T);
const { state: generated, report, schema } = compileFilm({ T, W, shots });
// theatre-state.pinned.json (a Studio export you chose to render as-is) replaces the generated keyframes. It does
// NOT follow a re-voice: delete it to go back to generated timing. See references/theatre-guide.md, Studio.
const pinnedFile = path.join(ROOT, 'theatre-state.pinned.json');
const state = fs.existsSync(pinnedFile) ? { ...JSON.parse(fs.readFileSync(pinnedFile, 'utf8')), pinned: true } : generated;
const out = path.join(ROOT, 'theatre-state.json');
const text = JSON.stringify(state, null, 1);
if (!fs.existsSync(out) || fs.readFileSync(out, 'utf8') !== text) fs.writeFileSync(out, text);
console.log(`theatre-state.json: ${Object.keys(schema).length} objects, ${report.tracks} tracks, ${report.keyframes} keyframes, ` +
  `${TIMING.total.toFixed(2)} s, timing ${TIMING.hash}`);
for (const w of report.warnings) console.log('  warning: ' + w);
if (report.quiet.length) console.log(`  NOTHING changes during lines: ${report.quiet.join(', ')}  (quality bar: animate what the line says)`);
if (report.cameraOnly.length) console.log(`  only the camera moves during lines: ${report.cameraOnly.join(', ')}  (consider a visible change)`);
if (!report.quiet.length && !report.cameraOnly.length) console.log(`  every one of the ${TIMING.lines.length} lines changes something on screen`);
if (state.pinned) console.log('  PINNED: theatre-state.pinned.json is what plays (hand-tweaked; it will not follow a re-voice). Delete it to use the generated keyframes.');
if (has('--state')) process.exit(0);

// 3. bundle
let esbuild;
try { esbuild = await import('esbuild'); } catch { console.error('esbuild missing: run npm install in source/'); process.exit(2); }
const common = {
  bundle: true, format: 'iife', target: 'chrome110', logLevel: 'warning', sourcemap: false, write: false,
  loader: { '.woff2': 'dataurl' }, define: { 'process.env.NODE_ENV': '"production"' }, absWorkingDir: ROOT,
};
// write only files whose bytes changed: capture.mjs restarts a resumed render when anything in source/ changes
const bundle = async (opts) => {
  const r = await esbuild.build({ ...common, ...opts });
  const names = [];
  for (const f of r.outputFiles) {
    names.push(path.relative(ROOT, f.path));
    if (fs.existsSync(f.path) && Buffer.compare(fs.readFileSync(f.path), Buffer.from(f.contents)) === 0) continue;
    fs.mkdirSync(path.dirname(f.path), { recursive: true }); fs.writeFileSync(f.path, f.contents);
  }
  return names.join(', ');
};
console.log(await bundle({ entryPoints: { film: 'src/main.js' }, outdir: 'dist' }));
const installed = (m) => fs.existsSync(path.join(ROOT, 'node_modules', m, 'package.json'));
if (has('--3d')) {
  if (!installed('three')) console.log('--3d: three is not installed (npm i --save-exact three@0.186.1)');
  else console.log(await bundle({ entryPoints: { film3d: 'src/variants/three.js' }, outdir: 'dist' }));
}
if (has('--studio')) {
  if (!installed('@theatre/studio')) console.log('--studio: @theatre/studio is not installed (npm i --save-exact @theatre/studio@0.7.2)');
  else console.log(await bundle({ define: { 'process.env.NODE_ENV': '"development"' }, entryPoints: { studio: 'src/studio.js' }, outdir: 'dist' }) + '  (laptop: serve the project folder, open /source/studio.html)');
}
