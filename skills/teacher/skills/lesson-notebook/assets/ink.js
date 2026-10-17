// Hand-drawn stroke geometry: the coach's pencil and pens.
// Pure functions that return SVG path data. Shared by the browser (app.js)
// and the static build (scripts/build.mjs), so a mark drawn at build time and
// the same mark drawn live are identical. Randomness is seeded, never Math.random.

/** FNV-1a hash of a string, as an unsigned 32-bit seed. */
export function seedFrom(text) {
  let h = 0x811c9dc5;
  for (let i = 0; i < text.length; i += 1) {
    h ^= text.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

/** Mulberry32: a small, fast PRNG. Returns a function giving floats in [0, 1). */
export function rng(seed) {
  let a = seed >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const r = (n) => Math.round(n * 100) / 100;
const spread = (rand, amount) => (rand() * 2 - 1) * amount;

/** Smooth open path through points (Catmull-Rom converted to cubic Béziers). */
export function smoothPath(pts) {
  if (pts.length < 2) return '';
  let d = `M${r(pts[0][0])} ${r(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i += 1) {
    const p0 = pts[i - 1] || pts[i];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || p2;
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6];
    const c2 = [p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6];
    d += ` C${r(c1[0])} ${r(c1[1])} ${r(c2[0])} ${r(c2[1])} ${r(p2[0])} ${r(p2[1])}`;
  }
  return d;
}

/**
 * Points for a hand-drawn line from a to b: a gentle bow, a little tremor,
 * and a small overshoot at the end, as a hand does when it doesn't lift early.
 */
export function linePoints(a, b, { seed = 1, bow = 0.035, tremor = 0.01, overshoot = 0.02, steps = 6 } = {}) {
  const rand = rng(seed);
  const dx = b[0] - a[0];
  const dy = b[1] - a[1];
  const len = Math.hypot(dx, dy) || 1;
  const ux = dx / len;
  const uy = dy / len;
  const nx = -uy;
  const ny = ux;
  const bend = spread(rand, bow) * len;
  const pts = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const along = t * (1 + overshoot);
    const off = Math.sin(Math.PI * t) * bend + (i === 0 || i === steps ? 0 : spread(rand, tremor) * len);
    pts.push([a[0] + dx * along + nx * off, a[1] + dy * along + ny * off]);
  }
  // A slightly uneven start: the pen lands a touch off the line.
  pts[0] = [pts[0][0] + spread(rand, tremor) * len, pts[0][1] + spread(rand, tremor) * len];
  return pts;
}

export function line(a, b, opts) {
  return smoothPath(linePoints(a, b, opts));
}

/** A polyline drawn in one stroke (for a knight's L), corners slightly rounded by the hand. */
export function polyline(points, { seed = 1, tremor = 0.012 } = {}) {
  const rand = rng(seed);
  const pts = [];
  for (let i = 0; i < points.length - 1; i += 1) {
    const a = points[i];
    const b = points[i + 1];
    const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
    const steps = 4;
    for (let s = i === 0 ? 0 : 1; s <= steps; s += 1) {
      const t = s / steps;
      const j = s === 0 || s === steps ? 0 : spread(rand, tremor) * len;
      pts.push([a[0] + (b[0] - a[0]) * t + j, a[1] + (b[1] - a[1]) * t + j]);
    }
  }
  return smoothPath(pts);
}

/**
 * A loop around a centre, the way a teacher circles something: it starts
 * off-axis, wobbles, and runs past its own start so the ends overlap.
 */
export function loop(cx, cy, rx, ry, { seed = 1, turns = 1.14, wobble = 0.05, tilt = 0, points = 30 } = {}) {
  const rand = rng(seed);
  const a0 = -Math.PI * (0.55 + rand() * 0.35);
  const phase = rand() * Math.PI * 2;
  const shrink = 0.05 + rand() * 0.05;
  const cosT = Math.cos(tilt);
  const sinT = Math.sin(tilt);
  const pts = [];
  for (let i = 0; i <= points; i += 1) {
    const t = i / points;
    const ang = a0 + t * Math.PI * 2 * turns;
    const k = 1 + Math.sin(ang * 2 + phase) * wobble + spread(rand, wobble * 0.35) - shrink * t;
    const x = Math.cos(ang) * rx * k;
    const y = Math.sin(ang) * ry * k;
    pts.push([cx + x * cosT - y * sinT, cy + x * sinT + y * cosT]);
  }
  return smoothPath(pts);
}

/** Two short strokes making an open arrowhead at `tip`, pointing along unit vector u. */
export function arrowHead(tip, u, size, { seed = 1, spreadAngle = 0.5 } = {}) {
  const rand = rng(seed);
  const strokes = [];
  for (const side of [1, -1]) {
    const ang = Math.atan2(u[1], u[0]) + Math.PI + side * (spreadAngle + spread(rand, 0.08));
    const len = size * (0.9 + rand() * 0.2);
    const end = [tip[0] + Math.cos(ang) * len, tip[1] + Math.sin(ang) * len];
    // Drawn from the barb end into the tip, as a hand does.
    strokes.push(line(end, tip, { seed: seed + side * 7, bow: 0.06, tremor: 0.01, overshoot: 0.04, steps: 3 }));
  }
  return strokes;
}

/** A hand-drawn arrow along a list of points (2 for straight, 3 for a knight's L). */
export function arrow(points, { seed = 1, head = 2.4 } = {}) {
  const shaft = points.length > 2 ? polyline(points, { seed }) : line(points[0], points[1], { seed, overshoot: 0 });
  const a = points[points.length - 2];
  const b = points[points.length - 1];
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
  const u = [(b[0] - a[0]) / len, (b[1] - a[1]) / len];
  return [shaft, ...arrowHead(b, u, head, { seed: seed + 3 })];
}

/** A pencil cross (×) centred on (cx, cy). */
export function cross(cx, cy, size, { seed = 1 } = {}) {
  const s = size / 2;
  return [
    line([cx - s, cy - s], [cx + s, cy + s], { seed, bow: 0.05, overshoot: 0.06, steps: 3 }),
    line([cx + s, cy - s * 1.05], [cx - s * 0.95, cy + s], { seed: seed + 1, bow: 0.05, overshoot: 0.06, steps: 3 }),
  ];
}

/** A teacher's tick in a w × h box: a short stroke down, a long one up. */
export function tick(w, h, { seed = 1 } = {}) {
  const rand = rng(seed);
  const a = [w * 0.08, h * (0.5 + spread(rand, 0.06))];
  const b = [w * 0.36, h * 0.92];
  const c = [w * 0.96, h * (0.06 + spread(rand, 0.04))];
  return [polyline([a, b, c], { seed, tremor: 0.015 })];
}

/** An underline across a w × h box: one slightly wavy stroke. */
export function underline(w, h, { seed = 1, double = false } = {}) {
  const y = h * 0.82;
  const out = [line([w * 0.02, y], [w * 0.98, y - h * 0.06], { seed, bow: 0.012, tremor: 0.004, overshoot: 0.01, steps: 8 })];
  if (double) out.push(line([w * 0.1, y + h * 0.13], [w * 0.92, y + h * 0.1], { seed: seed + 5, bow: 0.012, tremor: 0.004, steps: 8 }));
  return out;
}

/** A highlighter swipe across a w × h box (stroked thick by CSS). */
export function swipe(w, h, { seed = 1 } = {}) {
  return [line([w * 0.01, h * 0.62], [w * 0.99, h * 0.56], { seed, bow: 0.01, tremor: 0.003, overshoot: 0, steps: 6 })];
}

/** A loop around a w × h box (a circled word). */
export function ring(w, h, { seed = 1 } = {}) {
  return [loop(w / 2, h / 2, w * 0.5, h * 0.5, { seed, turns: 1.12, wobble: 0.035, tilt: -0.04 })];
}

/** A bracket down the left of a w × h box. */
export function bracket(w, h, { seed = 1 } = {}) {
  return [polyline([[w * 0.9, h * 0.02], [w * 0.25, h * 0.04], [w * 0.2, h * 0.96], [w * 0.9, h * 0.98]], { seed, tremor: 0.01 })];
}

/** Points along a quadratic curve a → b bending through control c, with a little tremor. */
function curvePoints(a, c, b, { seed = 1, tremor = 0.006, steps = 10 } = {}) {
  const rand = rng(seed);
  const len = Math.hypot(b[0] - a[0], b[1] - a[1]);
  const pts = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const mt = 1 - t;
    const j = i === 0 || i === steps ? 0 : spread(rand, tremor) * len;
    pts.push([mt * mt * a[0] + 2 * mt * t * c[0] + t * t * b[0] + j, mt * mt * a[1] + 2 * mt * t * c[1] + t * t * b[1] + j]);
  }
  return pts;
}

/** A curved arrow a → b through control c, with an open head. */
export function curvedArrow(a, c, b, { seed = 1, head = 6 } = {}) {
  const pts = curvePoints(a, c, b, { seed });
  const p = pts[pts.length - 2];
  const q = pts[pts.length - 1];
  const len = Math.hypot(q[0] - p[0], q[1] - p[1]) || 1;
  return [smoothPath(pts), ...arrowHead(q, [(q[0] - p[0]) / len, (q[1] - p[1]) / len], head, { seed: seed + 11 })];
}

/** The SVG strokes for a mark of a given kind in a w × h box. */
export function markPaths(kind, w, h, seed) {
  const s = Math.min(w, h);
  switch (kind) {
    case 'arrow':
      return arrow([[w * 0.06, h * 0.56], [w * 0.9, h * 0.48]], { seed, head: s * 0.32 });
    case 'hook':
      // From the bottom right, curling up and pointing to the top left.
      return curvedArrow([w * 0.92, h * 0.92], [w * 0.88, h * 0.18], [w * 0.12, h * 0.14], { seed, head: s * 0.22 });
    case 'swoop':
      // From the top right, sweeping down to the bottom left.
      return curvedArrow([w * 0.9, h * 0.08], [w * 0.78, h * 0.82], [w * 0.08, h * 0.84], { seed, head: s * 0.2 });
    case 'return':
      // A U-turn: along, round and back, pointing left.
      return [
        smoothPath([...curvePoints([w * 0.12, h * 0.3], [w * 0.98, h * 0.05], [w * 0.86, h * 0.6], { seed }), ...curvePoints([w * 0.86, h * 0.6], [w * 0.78, h * 0.92], [w * 0.18, h * 0.78], { seed: seed + 2 }).slice(1)]),
        ...arrowHead([w * 0.18, h * 0.78], [-0.98, -0.2], s * 0.34, { seed: seed + 5 }),
      ];
    case 'fork':
      // A trunk with a branch leaving it, like a variation off the main line.
      return [
        line([w * 0.3, h * 0.02], [w * 0.3, h * 0.98], { seed, bow: 0.02, overshoot: 0 }),
        smoothPath(curvePoints([w * 0.3, h * 0.3], [w * 0.32, h * 0.72], [w * 0.92, h * 0.72], { seed: seed + 1 })),
      ];
    case 'plus':
      return [
        line([w * 0.12, h * 0.52], [w * 0.88, h * 0.48], { seed, bow: 0.03, overshoot: 0.03, steps: 3 }),
        line([w * 0.52, h * 0.1], [w * 0.48, h * 0.9], { seed: seed + 1, bow: 0.03, overshoot: 0.03, steps: 3 }),
      ];
    case 'circle':
      return ring(w, h, { seed });
    case 'underline':
      return underline(w, h, { seed });
    case 'double':
      return underline(w, h, { seed, double: true });
    case 'highlight':
      return swipe(w, h, { seed });
    case 'tick':
      return tick(w, h, { seed });
    case 'cross':
      return cross(w / 2, h / 2, Math.min(w, h) * 0.8, { seed });
    case 'bracket':
      return bracket(w, h, { seed });
    default:
      throw new Error(`Unknown mark ${kind}`);
  }
}

/** An inline SVG for a mark. Stretched to its box by CSS; strokes drawn with pathLength=1. */
export function markSVG(kind, w, h, seed, className = 'ink__svg') {
  const paths = markPaths(kind, w, h, seed)
    .map((d) => `<path class="stroke" pathLength="1" d="${d}"/>`)
    .join('');
  return `<svg class="${className}" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true" focusable="false">${paths}</svg>`;
}
