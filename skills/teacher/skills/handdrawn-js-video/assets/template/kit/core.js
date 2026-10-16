// kit/core.js: math, easing, seeded randomness, the timing API, boil, squash-and-stretch, layers and camera.
// Rule for the whole kit: a frame is a pure function of t. No clocks, no Math.random, no state carried
// between frames. That is what lets capture.mjs render any frame, in any order, on any worker.
'use strict';
const W = 1920, H = 1080; // world and screen units (the canvas is scaled if TIMING asks for another size)

// ------------------------------------------------------------------ numbers
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const lerp = (a, b, u) => a + (b - a) * u;
const smooth = (a, b, x) => { const u = clamp((x - a) / (b - a)); return u * u * (3 - 2 * u); };
const TAU = Math.PI * 2;
function mulberry32(a) {
  return function () {
    a |= 0; a = (a + 0x6D2B79F5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
function hashStr(s) { let h = 2166136261; for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return h >>> 0; }
const seedOf = (x) => (typeof x === 'number' ? x | 0 : hashStr(String(x)));
const rnd = (seed, k = 0) => mulberry32((seedOf(seed) * 2654435761 + k * 40503) | 0)();
// smooth 1-D value noise in [-1, 1]
function noise1(seed, x) {
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(rnd(seed, i) * 2 - 1, rnd(seed, i + 1) * 2 - 1, u);
}

const Ease = {
  lin: (u) => u,
  in: (u) => u * u * u,
  out: (u) => 1 - Math.pow(1 - u, 3),
  out5: (u) => 1 - Math.pow(1 - u, 5),
  inOut: (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2),
  expoOut: (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u)),
  expoInOut: (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u < 0.5 ? Math.pow(2, 20 * u - 10) / 2 : (2 - Math.pow(2, -20 * u + 10)) / 2),
  sine: (u) => -(Math.cos(Math.PI * u) - 1) / 2,
  back: (u) => { const c1 = 1.70158, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); },
  backSoft: (u) => { const c1 = 0.9, c3 = c1 + 1; return 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2); },
};
// progress of t through [a, a + d], eased (0 before, 1 after)
function P(t, a, d, e = Ease.inOut) { return d <= 0 ? (t >= a ? 1 : 0) : e(clamp((t - a) / d)); }
// in-hold-out envelope: 0 -> 1 over [a, a + fi], holds 1 until b, -> 0 over [b, b + fo]
function env(t, a, b, fi = 0.4, fo = 0.3) { return Math.min(P(t, a, fi, Ease.out), 1 - P(t, b, fo, Ease.in)); }
// keyframes [[time, v1, v2, ...], ...] -> [v1, v2, ...] eased between neighbours
function track(t, keys, e = Ease.inOut) {
  if (t <= keys[0][0]) return keys[0].slice(1);
  for (let i = 1; i < keys.length; i++) {
    if (t < keys[i][0]) {
      const a = keys[i - 1], b = keys[i], u = (b[0] - a[0]) <= 0 ? 1 : e((t - a[0]) / (b[0] - a[0]));
      return a.slice(1).map((v, j) => lerp(v, b[j + 1], u));
    }
  }
  return keys[keys.length - 1].slice(1);
}
// a number that counts from a to b over [t0, t0 + d] (for tickers); integer by default
function ticker(t, t0, d, a, b, round = true) { const v = lerp(a, b, P(t, t0, d, Ease.out)); return round ? Math.round(v) : v; }

// ------------------------------------------------------------------ timing API (scenes key everything to line ids)
// L.p3.voiceAt, L.p3.voiceDur, L.p3.start, L.p3.end, L.p3.think, L.p3.cap ... An unknown id throws with the list
// of valid ids, and ids no scene ever reads are reported at boot (every line should change something).
const TIMING_ = window.TIMING || { total: 10, lines: [], chapters: [], scenes: [] };
const LINES = Object.fromEntries(TIMING_.lines.map((l) => [l.id, l]));
const USED_IDS = new Set();
const L = new Proxy(LINES, {
  get(o, k) {
    if (typeof k !== 'string' || k === 'then' || k === 'toJSON') return undefined;
    if (!(k in o)) throw new Error(`unknown line id '${k}'. script.json ids: ${Object.keys(o).join(', ')}`);
    USED_IDS.add(k); return o[k];
  },
});
const vAt = (id, f = 0) => L[id].voiceAt + f * L[id].voiceDur;      // f = 0..1 through the spoken words
const vEnd = (id) => L[id].voiceAt + L[id].voiceDur;                 // last word (think pause starts here)
const lStart = (id) => L[id].start, lEnd = (id) => L[id].end;        // the line's whole slot
// estimated moment a phrase is spoken inside a line (character position; lands within a few hundred ms)
function sayAt(id, phrase, off = 0) {
  const s = L[id].say.toLowerCase(), i = s.indexOf(String(phrase).toLowerCase());
  if (i < 0) throw new Error(`phrase '${phrase}' is not in line ${id}: "${L[id].say}"`);
  return L[id].voiceAt + L[id].voiceDur * (i / s.length) + off;
}
const inLine = (t, id) => t >= L[id].start && t < L[id].end;
function lineAt(t) { for (const l of TIMING_.lines) if (t >= l.start && t < l.end) return l; return null; }
function chapterAt(t) { let c = null; for (const ch of TIMING_.chapters) if (t >= ch.start - 0.8) c = ch; return c; }
const chapterStart = (n) => (TIMING_.chapters.find((c) => c.n === n) || { start: 0 }).start;
const chapterEnd = (n) => (TIMING_.chapters.find((c) => c.n === n) || { end: TIMING_.total }).end;

// ------------------------------------------------------------------ hand-made texture of motion
// Line boil: hand-drawn lines are re-drawn 8-12 times a second (S.boilFps), never every frame.
const boilKey = (t) => Math.floor(t * (S.boilFps || 10) + 1e-6);
const boilSeed = (id, t) => (seedOf(id) ^ Math.imul(boilKey(t) + 1, 0x9E3779B1)) >>> 0;
// stop-motion jitter for cut-outs: [dx, dy, rot], changes on boil frames only
function jitter(id, t, amp = S.jitter) {
  if (!amp) return [0, 0, 0];
  const k = boilKey(t), s = seedOf(id);
  return [(rnd(s, k * 3) - 0.5) * 2 * amp, (rnd(s, k * 3 + 1) - 0.5) * 2 * amp, (rnd(s, k * 3 + 2) - 0.5) * 0.004 * amp];
}
// squash-and-stretch pop: scale 0 -> overshoot -> settle, with volume-preserving squash. u = seconds since start.
function pop(t, t0, d = 0.55) {
  if (STYLE.pop) return STYLE.pop(t, t0, d); // a style's own entrance (papercraft-riso: a stepped drop, with .rot)
  const u = (t - t0) / d;
  if (u <= 0) return { s: 0, sx: 0, sy: 0 };
  if (u >= 1) return { s: 1, sx: 1, sy: 1 };
  const s = 1 - Math.exp(-6 * u) * Math.cos(10.5 * u);       // damped spring towards 1
  const k = Math.exp(-5 * u) * Math.sin(10.5 * u + 0.6) * 0.22; // squash/stretch follows the velocity
  return { s, sx: Math.max(0, s * (1 + k)), sy: Math.max(0, s * (1 - k)) };
}
// pop in at a, shrink out at b (exit faster than enter)
function popEnv(t, a, b = Infinity, d = 0.55, fo = 0.22) {
  const p = pop(t, a, d), o = 1 - P(t, b, fo, Ease.in);
  return { s: p.s * o, sx: p.sx * o, sy: p.sy * o, a: clamp(p.s * 3) * o, rot: p.rot };
}

// ------------------------------------------------------------------ layers
// World layers move with the camera; screen layers (captions, chapter labels, question cards) do not.
const LAYERS = { back: [], world: [], screen: [] };
function layer(space, z, draw) { LAYERS[space].push({ z, draw, n: LAYERS[space].length }); LAYERS[space].sort((a, b) => a.z - b.z || a.n - b.n); }
const world = (z, draw) => layer('world', z, draw);
// scenery between the backdrop and the world, moving with the camera at `depth` (0 = fixed, 1 = with the world)
const back = (depth, z, draw) => { LAYERS.back.push({ z, depth, draw, n: LAYERS.back.length }); LAYERS.back.sort((a, b) => a.z - b.z || a.n - b.n); };
const screen = (z, draw) => layer('screen', z, draw);
// a value that may be a constant or a function of t
const val = (v, t) => (typeof v === 'function' ? v(t) : v);

// ------------------------------------------------------------------ camera
// Keys: [time, x, y, zoom, rot] = the world point at the centre of the screen. Eased between keys, plus a
// slow drift so holds never freeze, plus shakes. depth < 1 moves a layer less (parallax for the backdrop).
const CAM = { keys: [[0, W / 2, H / 2, 1, 0]], shakes: [], drift: 1 };
function camera(keys, o = {}) { CAM.keys = keys.map((k) => [k[0], k[1], k[2], k[3] ?? 1, k[4] ?? 0]).sort((a, b) => a[0] - b[0]); if (o.drift != null) CAM.drift = o.drift; }
function shake(at, amp = 10, dur = 0.35) { CAM.shakes.push({ at, amp, dur }); }
// drift = false gives the keyed moves and shakes only: the backdrop and scenery use it, so they hold perfectly
// still between moves (still pixels cost nothing to encode; a drifting paper texture costs a lot).
function camAt(t, drift = true) {
  let [x, y, z, r] = track(t, CAM.keys, Ease.inOut);
  const d = drift ? CAM.drift : 0;
  x += d * (7 * Math.sin(t * 0.29) + 3 * Math.sin(t * 0.71 + 1.3));
  y += d * (5 * Math.sin(t * 0.23 + 0.7) + 2 * Math.sin(t * 0.61 + 2.1));
  z *= 1 + d * 0.006 * Math.sin(t * 0.19 + 0.4);
  r += d * 0.0025 * Math.sin(t * 0.17 + 2.0);
  for (const s of CAM.shakes) {
    const u = (t - s.at) / s.dur; if (u < 0 || u > 1) continue;
    const a = s.amp * (1 - u) * (1 - u), k = Math.floor((t - s.at) * 30);
    x += (rnd(77, k) - 0.5) * 2 * a; y += (rnd(78, k) - 0.5) * 2 * a;
  }
  return { x, y, z, r };
}
function applyCam(ctx, c, depth = 1) {
  const z = 1 + (c.z - 1) * depth, cx = W / 2 + (c.x - W / 2) * depth, cy = H / 2 + (c.y - H / 2) * depth;
  ctx.translate(W / 2, H / 2); ctx.rotate(c.r * depth); ctx.scale(z, z); ctx.translate(-cx, -cy);
}
// a camera that frames a world rectangle [x0, y0, x1, y1] (with margin) -> [x, y, zoom]
function frame(x0, y0, x1, y1, margin = 80) {
  const z = Math.min((W - 2 * margin) / (x1 - x0), (H - 2 * margin - 120) / (y1 - y0));
  return [(x0 + x1) / 2, (y0 + y1) / 2 + 40 / z, z];
}
