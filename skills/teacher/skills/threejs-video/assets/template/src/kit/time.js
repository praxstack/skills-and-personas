// time.js: the film's clock. Everything on screen is a pure function of t (seconds), so any frame can be
// rendered in any order (capture.mjs splits the film across workers and resumes mid-way).
//
//   TIMING          window.TIMING, written by voice.py --emit src/timing.js (never edit by hand)
//   at(id, f)       voice-relative cue: at('p4') voice starts, at('p4', 0.5) halfway through the words, at('p4', 1) voice ends
//   word(id, 'phrase')  the moment a phrase of `say` is spoken (estimated from its character position)
//   start(id) end(id)   the line's slot (end includes the think pause)
//   think(id)       [from, to] of the think pause after a question line
//   E               easing functions;  p(t, a, d, ease) = eased progress 0..1 of [a, a+d]
//   Timeline        a tiny seekable tween engine:  tl.to(obj, {x: 1}, at('p1'), 0.6, 'out')  then  tl.seek(t)
//
// No clock, no Math.random: use rand(seed) for anything random.

export const TIMING = window.TIMING;
if (!TIMING) throw new Error('window.TIMING is missing: src/timing.js was not loaded (run voice.py --emit source/src/timing.js)');
export const TOTAL = TIMING.total;
export const LINES = TIMING.lines;
export const L = Object.fromEntries(LINES.map((l) => [l.id, l]));
export const CHAPTERS = TIMING.chapters;

function line(id) {
  const l = L[id];
  if (!l) throw new Error(`unknown line id "${id}": it is not in timing.js (ids: ${LINES.map((x) => x.id).join(', ')})`);
  return l;
}
export const has = (id) => id in L;
export const at = (id, f = 0) => { const l = line(id); return l.voiceAt + f * l.voiceDur; };
export const start = (id) => line(id).start;
export const end = (id) => line(id).end;
export const dur = (id) => line(id).dur;
export const think = (id) => { const l = line(id); return [l.voiceAt + l.voiceDur, l.voiceAt + l.voiceDur + (l.think || 0)]; };
export function word(id, phrase, f = 0) {
  const l = line(id); const i = l.say.toLowerCase().indexOf(phrase.toLowerCase());
  if (i < 0) throw new Error(`"${phrase}" is not in the say text of ${id}: "${l.say}"`);
  return l.voiceAt + l.voiceDur * (i + f * phrase.length) / l.say.length;
}
export function lineAt(t) { let c = LINES[0]; for (const l of LINES) if (l.start <= t) c = l; return c; }
export function chapterAt(t) { let c = CHAPTERS[0]; for (const ch of CHAPTERS) if (ch.start - 0.8 <= t) c = ch; return c; }
export const chapterStart = (n) => (CHAPTERS.find((c) => c.n === n) || {}).start;

// ------------------------------------------------------------------ math + easing
export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, u) => a + (b - a) * u;
const c1 = 1.70158, c3 = c1 + 1;
export const E = {
  linear: (u) => u,
  in: (u) => u * u * u,
  out: (u) => 1 - Math.pow(1 - u, 3),
  inOut: (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2),
  outExpo: (u) => (u >= 1 ? 1 : 1 - Math.pow(2, -10 * u)),
  inOutExpo: (u) => (u <= 0 ? 0 : u >= 1 ? 1 : u < 0.5 ? Math.pow(2, 20 * u - 10) / 2 : (2 - Math.pow(2, -20 * u + 10)) / 2),
  inOutSine: (u) => -(Math.cos(Math.PI * u) - 1) / 2,
  outBack: (u) => 1 + c3 * Math.pow(u - 1, 3) + c1 * Math.pow(u - 1, 2),
  outElastic: (u) => (u <= 0 ? 0 : u >= 1 ? 1 : Math.pow(2, -10 * u) * Math.sin((u * 10 - 0.75) * (2 * Math.PI) / 3) + 1),
};
const easeFn = (e) => (typeof e === 'function' ? e : E[e] || E.out);
// eased progress of t through [a, a + d]
export const p = (t, a, d = 0.5, e = 'out') => easeFn(e)(clamp(d > 0 ? (t - a) / d : t >= a ? 1 : 0));
// a visibility window: fades in at a, out before b
export const win = (t, a, b, fin = 0.35, fout = 0.3) => Math.min(p(t, a, fin, 'out'), 1 - p(t, b - fout, fout, 'in'));
// deterministic pseudo-random numbers (mulberry32)
export function rand(seed = 1) {
  let s = seed >>> 0;
  return () => { s = (s + 0x6d2b79f5) >>> 0; let x = Math.imul(s ^ (s >>> 15), 1 | s); x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x; return ((x ^ (x >>> 14)) >>> 0) / 4294967296; };
}

// ------------------------------------------------------------------ colours (hex strings tween in sRGB)
const hexToRgb = (h) => { const n = parseInt(h.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const rgbToHex = (r) => '#' + r.map((v) => Math.round(clamp(v, 0, 255)).toString(16).padStart(2, '0')).join('');
export const mixHex = (a, b, u) => { const A = hexToRgb(a), B = hexToRgb(b); return rgbToHex(A.map((v, i) => lerp(v, B[i], u))); };

function mix(a, b, u) {
  if (typeof a === 'number' && typeof b === 'number') return lerp(a, b, u);
  if (Array.isArray(a) && Array.isArray(b) && a.length === b.length) return a.map((v, i) => mix(v, b[i], u));
  if (typeof a === 'string' && typeof b === 'string' && a[0] === '#' && b[0] === '#' && a.length === 7 && b.length === 7) return mixHex(a, b, u);
  return u >= 1 ? b : a; // strings, booleans, objects, arrays of another length switch at the end (use set() to switch at the start)
}
const clone = (v) => (Array.isArray(v) ? v.map(clone) : v);

// ------------------------------------------------------------------ the seekable tween timeline
// Each (object, property) pair is a channel holding its base value and a list of tweens. seek(t) sets every
// channel to the value of the last tween that has started by t (a later tween takes over from wherever the
// earlier one was at that moment, like GSAP's overwrite). Nothing depends on the previous frame.
export class Timeline {
  constructor() { this.channels = new Map(); this.n = 0; this.ready = false; }

  _chan(obj, key) {
    if (obj == null) throw new Error(`tween target is ${obj} (property ${key})`);
    let m = this.channels.get(obj);
    if (!m) { m = new Map(); this.channels.set(obj, m); }
    let c = m.get(key);
    if (!c) {
      if (!(key in obj)) throw new Error(`tween target has no property "${key}" (give it a default value first)`);
      c = { base: clone(obj[key]), tws: [] }; m.set(key, c);
    }
    return c;
  }
  _add(obj, props, time, d, ease, from) {
    if (!Number.isFinite(time)) throw new Error(`tween time is ${time} for ${Object.keys(props).join(',')}`);
    for (const k of Object.keys(props)) {
      this._chan(obj, k).tws.push({ t0: time, d: Math.max(0, d), to: clone(props[k]), from: from && k in from ? clone(from[k]) : undefined, e: easeFn(ease), i: this.n++ });
    }
    this.ready = false; return this;
  }
  /** tween props to values over [time, time + d] */
  to(obj, props, time, d = 0.5, ease = 'out') { return this._add(obj, props, time, d, ease); }
  /** tween from explicit values */
  fromTo(obj, from, to, time, d = 0.5, ease = 'out') { return this._add(obj, to, time, d, ease, from); }
  /** jump to values at time */
  set(obj, props, time) { return this._add(obj, props, time, 0, 'linear'); }
  /** tween up and back: value goes to `peak` and returns to what it was (a pulse, a flash) */
  pulse(obj, props, time, d = 0.6, ease = 'out') {
    const back = {};
    for (const k of Object.keys(props)) back[k] = this.valueAt(obj, k, time);
    this.to(obj, props, time, d * 0.35, ease);
    return this.to(obj, back, time + d * 0.35, d * 0.65, 'inOut');
  }
  /** value a channel will have at time (useful to chain off the current state) */
  valueAt(obj, key, time) { this._prepare(); const c = this.channels.get(obj)?.get(key); return c ? this._eval(c, time) : obj[key]; }

  _prepare() {
    if (this.ready) return;
    for (const m of this.channels.values()) for (const c of m.values()) {
      c.tws.sort((a, b) => a.t0 - b.t0 || a.i - b.i);
      let prev = null;
      for (const tw of c.tws) {
        tw.f = tw.from !== undefined ? tw.from : prev ? this._val(prev, tw.t0) : clone(c.base);
        prev = tw;
      }
    }
    this.ready = true;
  }
  _val(tw, t) { const u = tw.d > 0 ? clamp((t - tw.t0) / tw.d) : t >= tw.t0 ? 1 : 0; return mix(tw.f, tw.to, tw.e(u)); }
  _eval(c, t) {
    let k = -1;
    for (let i = c.tws.length - 1; i >= 0; i--) if (c.tws[i].t0 <= t) { k = i; break; }
    return k < 0 ? clone(c.base) : this._val(c.tws[k], t);
  }
  seek(t) {
    this._prepare();
    for (const [obj, m] of this.channels) for (const [k, c] of m) obj[k] = this._eval(c, t);
  }
}
