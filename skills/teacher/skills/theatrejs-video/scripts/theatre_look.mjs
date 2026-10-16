#!/usr/bin/env node
// theatre_look.mjs: the review loop for the Theatre.js template in one command.
//   1. source/: node tools/build.mjs   (timing.js + shots.js -> theatre-state.json, bundle; prints the coverage
//      report: lines on which nothing moves, tweens that interrupt each other)
//   2. capture.mjs --stills <at> into stills/   (one JPG per chapter, per line, or per time)
//   3. stills/sheet-<set>-N.png contact sheets (16 stills each) for a first overview
// Then open the sheets AND the single stills with the Read tool; the sheets are too small to check text.
//
// Usage (from the project folder):
//   node $S/theatre_look.mjs                      chapters, then lines (the full review set)
//   node $S/theatre_look.mjs --at lines           one still 65% into every narration line
//   node $S/theatre_look.mjs --at 12.5,31,44.2    exact times (seconds)
//   node $S/theatre_look.mjs --page index-3d.html --webgl    the Three.js variant
import fs from 'node:fs';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { concatLine } from './segmanifest.mjs';
import { fileURLToPath } from 'node:url';

const S = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 && i + 1 < argv.length ? argv[i + 1] : d; };
const PROJECT = path.resolve(opt('project', '.'));
const SRC = path.join(PROJECT, 'source');
const PAGE = path.join(SRC, opt('page', 'index.html'));
const OUT = path.resolve(PROJECT, opt('out', 'stills'));
const sets = opt('at') ? [opt('at')] : ['chapters', 'lines'];
const run = (cmd, args, cwd) => {
  const r = spawnSync(cmd, args, { cwd, stdio: 'inherit' });
  if (r.status !== 0) { console.error(`failed: ${cmd} ${args.join(' ')}`); process.exit(r.status || 1); }
};

if (!fs.existsSync(path.join(SRC, 'node_modules'))) run('npm', ['ci', '--no-audit', '--no-fund'], SRC);
run('node', ['tools/build.mjs', ...(argv.includes('--webgl') ? ['--3d'] : [])], SRC);

// everything goes straight into stills/ (the visuals gate counts the images there): chapter stills are ch<n>-*.jpg,
// line stills <start>-<id>.jpg, time stills t<secs>.jpg; each set replaces its own previous files only
const PREFIX = { chapters: /^ch\d/, lines: /^\d/, times: /^t\d/ };
fs.mkdirSync(OUT, { recursive: true });
for (const at of sets) {
  const set = /^[a-z]+$/.test(at) ? at : 'times', mine = (f) => PREFIX[set]?.test(f) && f.endsWith('.jpg');
  for (const f of fs.readdirSync(OUT)) if (mine(f) || f.startsWith(`sheet-${set}-`)) fs.rmSync(path.join(OUT, f));
  const cap = ['--page', PAGE, '--stills', at, '--stills-dir', OUT];
  if (set !== 'times') cap.push('--timing', path.join(PROJECT, 'timing.json'));
  if (argv.includes('--webgl')) cap.push('--webgl');
  run('node', [path.join(S, 'capture.mjs'), ...cap], PROJECT);
  const jpgs = fs.readdirSync(OUT).filter(mine).sort();
  const sheets = [];
  for (let i = 0; i < jpgs.length; i += 16) {
    const chunk = jpgs.slice(i, i + 16), list = path.join(OUT, '.sheet.txt'), name = `sheet-${set}-${i / 16 + 1}.png`;
    fs.writeFileSync(list, chunk.map((f) => concatLine(path.join(OUT, f)) + '\n').join(''));
    run('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', list, '-vf',
      `scale=640:-1,tile=4x${Math.ceil(chunk.length / 4)}:padding=6:color=0x111111`, '-frames:v', '1', path.join(OUT, name)], PROJECT);
    fs.rmSync(list); sheets.push(name);
  }
  console.log(`${set}: ${jpgs.length} stills in ${path.relative(PROJECT, OUT) || '.'}/  sheets (16 per sheet, name order): ${sheets.join(', ')}`);
}
