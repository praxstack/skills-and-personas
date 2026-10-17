#!/usr/bin/env node
// studio-diff.mjs: what did a hand-tweak in @theatre/studio change? Compares a Studio export with the generated
// theatre-state.json, keyframe by keyframe, and prints each change as object.prop, time, nearest narration line, so
// you can port it into src/film/shots.js (the generated keyframes stay the source of truth: re-voicing re-times them).
// The base is the state shots.js generates now; pass a second file to compare against that instead.
//
//   node tools/studio-diff.mjs ~/Downloads/Explainer.theatre-project-state.json [base-state.json]
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const [expFile, baseFile] = process.argv.slice(2);
if (!expFile) { console.error('usage: node tools/studio-diff.mjs <studio-export.json> [base-state.json]'); process.exit(2); }
const exp = JSON.parse(fs.readFileSync(expFile, 'utf8'));
const tsrc = fs.readFileSync(path.join(ROOT, 'timing.js'), 'utf8');
const TIMING = JSON.parse(tsrc.slice(tsrc.indexOf('{'), tsrc.lastIndexOf('}') + 1));
// the base is what shots.js generates now (not theatre-state.json, which may be a pinned export)
let base;
if (baseFile) base = JSON.parse(fs.readFileSync(baseFile, 'utf8'));
else {
  const imp = (p) => import(pathToFileURL(path.join(ROOT, p)).href);
  const { timeline } = await imp('src/theatre/timing.js');
  const { compileFilm } = await imp('src/theatre/keys.js');
  const { default: world } = await imp('src/film/world.js');
  const { default: shots } = await imp('src/film/shots.js');
  const T = timeline(TIMING);
  base = compileFilm({ T, W: world(T), shots }).state;
}

const near = (t) => {
  const L = TIMING.lines.find((l) => t >= l.start - 1e-6 && t <= l.end + (l.think || 0) + 0.05);
  if (L) return `${L.id} +${(t - L.start).toFixed(2)}s`;
  let best = null; for (const l of TIMING.lines) if (!best || Math.abs(l.start - t) < Math.abs(best.start - t)) best = l;
  return best ? `near ${best.id} (${(t - best.start).toFixed(2)}s)` : '';
};
const hex = (c) => '#' + [c.r, c.g, c.b].map((x) => Math.round(x * 255).toString(16).padStart(2, '0')).join('') + (c.a < 1 ? Math.round(c.a * 255).toString(16).padStart(2, '0') : '');
const fmt = (v) => (v && typeof v === 'object' ? ('r' in v ? hex(v) : JSON.stringify(v)) : typeof v === 'number' ? +v.toFixed(4) : JSON.stringify(v));
const tracks = (st) => {
  const out = new Map();
  for (const [sheet, S] of Object.entries(st.sheetsById || {})) {
    for (const [obj, O] of Object.entries(S.sequence?.tracksByObject || {})) {
      for (const [prop, tid] of Object.entries(O.trackIdByPropPath || {})) out.set(`${sheet} :: ${obj}.${JSON.parse(prop).join('.')}`, O.trackData[tid]?.keyframes || []);
    }
  }
  return out;
};
const statics = (st) => {
  const out = new Map();
  for (const [sheet, S] of Object.entries(st.sheetsById || {})) for (const [obj, vals] of Object.entries(S.staticOverrides?.byObject || {})) {
    const walk = (o, p) => { for (const [k, v] of Object.entries(o)) (v && typeof v === 'object' && !('r' in v)) ? walk(v, [...p, k]) : out.set(`${sheet} :: ${obj}.${[...p, k].join('.')}`, v); };
    walk(vals, []);
  }
  return out;
};

const A = tracks(base), B = tracks(exp);
let n = 0;
const say = (s) => { console.log(s); n++; };
for (const key of new Set([...A.keys(), ...B.keys()])) {
  const a = new Map((A.get(key) || []).map((k) => [k.id, k])), b = new Map((B.get(key) || []).map((k) => [k.id, k]));
  for (const [id, k] of b) {
    const o = a.get(id);
    if (!o) { say(`+ ${key} @ ${k.position.toFixed(3)}s = ${fmt(k.value)}  [${k.type || 'bezier'}]  ${near(k.position)}`); continue; }
    const d = [];
    if (Math.abs(o.position - k.position) > 1e-4) d.push(`time ${o.position.toFixed(3)} -> ${k.position.toFixed(3)}s`);
    if (JSON.stringify(o.value) !== JSON.stringify(k.value)) d.push(`value ${fmt(o.value)} -> ${fmt(k.value)}`);
    if (JSON.stringify(o.handles) !== JSON.stringify(k.handles)) d.push(`ease [${o.handles}] -> [${k.handles}]`);
    if ((o.type || 'bezier') !== (k.type || 'bezier')) d.push(`type ${o.type} -> ${k.type}`);
    if (d.length) say(`~ ${key} @ ${o.position.toFixed(3)}s: ${d.join('; ')}  ${near(k.position)}`);
  }
  for (const [id, k] of a) if (!b.has(id)) say(`- ${key} @ ${k.position.toFixed(3)}s (was ${fmt(k.value)})  ${near(k.position)}`);
}
const SA = statics(base), SB = statics(exp);
for (const [k, v] of SB) if (JSON.stringify(SA.get(k)) !== JSON.stringify(v)) say(`= ${k} static value ${fmt(SA.get(k))} -> ${fmt(v)}  (a default: change it in the component's objects() or with s.set at 0)`);
if (!n) console.log('no differences: the export matches the generated state');
else console.log(`\n${n} change(s). Port them into src/film/shots.js as s.to / s.set calls anchored to the line ids shown, then npm run build.`);
