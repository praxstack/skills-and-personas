// keys.js: compile a shot list (keyframes keyed to narration line ids) into a Theatre.js project state.
//
// The film's animation lives in src/film/shots.js as calls like
//     s.to('Camera', { z: 220, x: -140 }, T.at('p3'), 1.2, 'inOut')
// This module turns those calls into BasicKeyframedTrack keyframes with bezier handles, exactly the JSON that
// @theatre/studio exports, so getProject(id, { state }) plays it with no studio at render time. Because every time
// comes from TIMING (the voice), re-voicing re-times every keyframe on the next build.
//
// Pure module: runs in node (tools/build.mjs writes theatre-state.json) and in the page (fallback when stale).

/** cubic-bezier control points [x1, y1, x2, y2] (CSS convention) */
export const EASE = {
  linear: [0, 0, 1, 1],
  in: [0.55, 0, 1, 0.45],
  out: [0, 0.55, 0.45, 1],
  inOut: [0.65, 0, 0.35, 1],
  soft: [0.45, 0, 0.55, 1], // sine in-out, for drifts and slow holds
  expoOut: [0.16, 1, 0.3, 1],
  expoInOut: [0.87, 0, 0.13, 1],
  back: [0.34, 1.56, 0.64, 1], // overshoot, for pops
  backIn: [0.36, 0, 0.66, -0.56],
  snap: [0.2, 0.9, 0.1, 1],
};

/** Theatre normalises object keys ("Graph/node 0" -> "Graph / node 0"); the state must use the normalised form. */
export const objectKey = (k) => k.replace(/^[\s/]*/, '').replace(/[\s/]*$/, '').replace(/\s*\/\s*/g, ' / ');

export const kindOf = (v) =>
  typeof v === 'number' ? 'number' : typeof v === 'string' ? 'string' : typeof v === 'boolean' ? 'boolean'
    : v && typeof v === 'object' && 'r' in v && 'g' in v && 'b' in v ? 'rgba' : 'unknown';

function hexToRgba(h) {
  const x = h.replace('#', '');
  const n = (i) => parseInt(x.slice(i, i + 2), 16) / 255;
  return { r: n(0), g: n(2), b: n(4), a: x.length >= 8 ? n(6) : 1 };
}

/** y(x) for a CSS cubic-bezier, used to evaluate a tween that another tween interrupts */
export function bezier([x1, y1, x2, y2]) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const X = (t) => ((ax * t + bx) * t + cx) * t, Y = (t) => ((ay * t + by) * t + cy) * t;
  const dX = (t) => (3 * ax * t + 2 * bx) * t + cx;
  return (x) => {
    let t = x;
    for (let i = 0; i < 8; i++) { const e = X(t) - x, d = dX(t); if (Math.abs(e) < 1e-6 || Math.abs(d) < 1e-6) break; t -= e / d; }
    return Y(Math.min(1, Math.max(0, t)));
  };
}

const EPS = 0.001; // two keyframes never share a position (Theatre would divide by zero); a jump is 1 ms wide

/**
 * Build a shot list against a schema.
 * @param schema  { [objectKey]: { prop: defaultValue } }  (from the kit components; see src/theatre/rig.js)
 * @returns the builder `s` passed to shots(s, T), plus compile()
 */
export function createShots(schema) {
  const S = {};
  for (const [k, props] of Object.entries(schema)) S[objectKey(k)] = props;
  const ops = []; let seq = 0;
  const warnings = [];

  function check(obj, props) {
    const key = objectKey(obj);
    if (!S[key]) {
      const near = Object.keys(S).filter((k) => k.toLowerCase().includes(String(obj).split('/').pop().trim().toLowerCase())).slice(0, 6);
      throw new Error(`shots: no Theatre object "${obj}". ${near.length ? 'Did you mean: ' + near.join(', ') : 'Objects: ' + Object.keys(S).join(', ')}`);
    }
    for (const p of Object.keys(props)) {
      if (!(p in S[key])) throw new Error(`shots: object "${key}" has no prop "${p}". Props: ${Object.keys(S[key]).join(', ')}`);
    }
    return key;
  }
  function norm(key, prop, v) {
    const d = S[key][prop];
    if (kindOf(d) === 'rgba' && typeof v === 'string') return hexToRgba(v);
    if (kindOf(d) === 'number' && typeof v !== 'number') throw new Error(`shots: ${key}.${prop} is a number, got ${JSON.stringify(v)}`);
    if (!Number.isFinite(+v) && kindOf(d) === 'number') throw new Error(`shots: ${key}.${prop} got a non-finite time/value`);
    return v;
  }
  const num = (t, what) => { if (!Number.isFinite(t)) throw new Error(`shots: ${what} is not a number (${t}); check the line id / helper`); return t; };

  const s = {
    /** jump to values at time t (no tween) */
    set(obj, props, t) {
      const key = check(obj, props); num(t, `set(${obj}) time`);
      for (const [p, v] of Object.entries(props)) ops.push({ key, p, kind: 'set', t0: t, t1: t, to: norm(key, p, v), seq: seq++ });
      return s;
    },
    /** tween from the current value to `props` over [t, t + dur] */
    to(obj, props, t, dur = 0.6, ease = 'inOut') {
      const key = check(obj, props); num(t, `to(${obj}) time`); num(dur, `to(${obj}) duration`);
      if (!EASE[ease]) throw new Error(`shots: unknown ease "${ease}". Eases: ${Object.keys(EASE).join(', ')}`);
      for (const [p, v] of Object.entries(props)) {
        const k = kindOf(S[key][p]);
        if (k === 'string' || k === 'boolean') ops.push({ key, p, kind: 'set', t0: t, t1: t, to: v, seq: seq++ });
        else ops.push({ key, p, kind: 'tween', t0: t, t1: t + Math.max(dur, 1 / 60), to: norm(key, p, v), ease, seq: seq++ });
      }
      return s;
    },
    /** set `from` at t, then tween to `to` */
    fromTo(obj, from, to, t, dur = 0.6, ease = 'inOut') { s.set(obj, from, t); return s.to(obj, to, t + EPS * 2, dur, ease); },
    /** go up to `peak` and come back to `base` (glows, rings, flashes, shakes) */
    pulse(obj, prop, t, { peak = 1, base = 0, up = 0.18, hold = 0.25, down = 0.6 } = {}) {
      s.to(obj, { [prop]: peak }, t, up, 'out');
      return s.to(obj, { [prop]: base }, t + up + hold, down, 'inOut');
    },
    /** the same tween on several objects, `gap` seconds apart */
    stagger(objs, props, t, dur = 0.5, gap = 0.1, ease = 'back') {
      objs.forEach((o, i) => s.to(o, props, t + i * gap, dur, ease));
      return s;
    },
    /** shorthand for the camera */
    cam(props, t, dur = 1.2, ease = 'inOut') { return s.to('Camera', props, t, dur, ease); },
    warn(msg) { warnings.push(msg); },
  };

  /** turn the ops into Theatre state */
  function compile({ total, fps = 30, sheet = 'Film', timingHash = '', lines = [] }) {
    const tracks = new Map();
    for (const op of [...ops].sort((a, b) => a.t0 - b.t0 || a.seq - b.seq)) {
      const id = op.key + '\u0000' + op.p;
      if (!tracks.has(id)) tracks.set(id, []);
      tracks.get(id).push(op);
    }
    const tracksByObject = {};
    const touched = []; // [time, objectKey] for the coverage report
    let nKeys = 0;
    for (const [id, list] of tracks) {
      const [key, p] = id.split('\u0000');
      const def = S[key][p];
      const interp = kindOf(def) === 'number' || kindOf(def) === 'rgba';
      let cur = def; const kfs = [];
      const last = () => kfs[kfs.length - 1];
      const push = (pos, value, arrive) => {
        const L = last();
        if (L && pos < L.pos + EPS) {
          if (arrive === null && JSON.stringify(L.value) === JSON.stringify(value)) return; // nothing changes
          pos = L.pos + EPS;
        }
        kfs.push({ pos, value, arrive });
      };
      if (list[0].t0 > EPS) kfs.push({ pos: 0, value: def, arrive: null }); // before the first change: the default
      for (const op of list) {
        touched.push([op.t0, key, op.t1]);
        if (op.kind === 'set') { push(op.t0, op.to, null); cur = op.to; continue; }
        const L = last();
        if (L && L.arrive && L.pos > op.t0 + EPS && interp && kindOf(def) === 'number') {
          // this tween starts before the previous one ended: cut the previous one where it is at t0
          const P = kfs[kfs.length - 2];
          const u = (op.t0 - P.pos) / (L.pos - P.pos);
          const v = P.value + (L.value - P.value) * bezier(EASE[L.arrive])(Math.max(0, Math.min(1, u)));
          warnings.push(`${key}.${p}: tween at ${op.t0.toFixed(2)} s interrupts the one ending ${L.pos.toFixed(2)} s (cut there)`);
          L.pos = Math.max(P.pos + EPS, op.t0); L.value = +v.toFixed(4); cur = L.value;
        } else if (L && L.pos > op.t0 + EPS) {
          warnings.push(`${key}.${p}: tween at ${op.t0.toFixed(2)} s starts before the previous key at ${L.pos.toFixed(2)} s (shifted)`);
        }
        push(op.t0, cur, null);
        push(Math.max(op.t1, last().pos + EPS), op.to, op.ease);
        cur = op.to;
      }
      if (!kfs.length) continue;
      // Theatre keyframes: segment i -> i+1 is cubic-bezier(k[i].handles[2..3], k[i+1].handles[0..1])
      const tid = (key + '__' + p).replace(/[^A-Za-z0-9_]/g, '_');
      const keyframes = kfs.map((k, i) => {
        const next = kfs[i + 1];
        const inE = k.arrive ? EASE[k.arrive] : [0, 0, 0.5, 1];
        const outE = next && next.arrive ? EASE[next.arrive] : [0.5, 0, 1, 1];
        const value = typeof k.value === 'number' ? +k.value.toFixed(4) : k.value;
        return {
          id: `${tid}_${i}`, position: +k.pos.toFixed(4), connectedRight: true,
          handles: [inE[2], inE[3], outE[0], outE[1]],
          type: next && next.arrive && interp ? 'bezier' : 'hold', value,
        };
      });
      nKeys += keyframes.length;
      const o = (tracksByObject[key] ||= { trackData: {}, trackIdByPropPath: {} });
      o.trackIdByPropPath[JSON.stringify([p])] = tid;
      o.trackData[tid] = { type: 'BasicKeyframedTrack', __debugName: `${key}:${p}`, keyframes };
    }
    const state = {
      sheetsById: {
        [sheet]: {
          staticOverrides: { byObject: {} },
          sequence: { type: 'PositionalSequence', length: +total.toFixed(3), subUnitsPerUnit: fps, tracksByObject },
        },
      },
      definitionVersion: '0.4.0',
      revisionHistory: [`generated-${timingHash}`],
      generated: { timingHash, by: 'tools/build.mjs from src/film/shots.js', objects: Object.keys(tracksByObject).length, keyframes: nKeys },
    };
    // coverage: every narration line should change something besides the camera (quality-bar rule)
    const quiet = [], cameraOnly = [];
    for (const ln of lines) {
      const hits = touched.filter(([t0, k, t1]) => t1 >= ln.start - 0.15 && t0 <= ln.end);
      const real = hits.filter(([, k]) => !/^(Camera|Sky)$/.test(k));
      if (!hits.length) quiet.push(ln.id); else if (!real.length) cameraOnly.push(ln.id);
    }
    return { state, report: { tracks: tracks.size, keyframes: nKeys, warnings, quiet, cameraOnly } };
  }

  return { s, compile, schema: S };
}

/** { objectKey: { prop: default } } from the components' objects(); duplicate keys are an error */
export function schemaOf(components) {
  const schema = {};
  for (const c of components) {
    for (const [k, props] of Object.entries(c.objects ? c.objects() : {})) {
      const key = objectKey(k);
      if (schema[key]) throw new Error(`two components declare the Theatre object "${key}"; give one of them another id`);
      schema[key] = props;
    }
  }
  return schema;
}

/** the whole film: world + shots + timing -> { state, report }. Used by tools/build.mjs and by the page. */
export function compileFilm({ T, W, shots }) {
  const schema = schemaOf(W.components);
  const { s, compile } = createShots(schema);
  shots(s, T, W);
  return { schema, ...compile({ total: T.total, fps: T.fps, timingHash: T.hash, lines: T.lines }) };
}
