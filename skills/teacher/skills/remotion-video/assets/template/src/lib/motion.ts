// Motion helpers. All take absolute frames (use f('id') / sec(0.4) from ./timing to make them).
// Everything is eased; linear motion only for constant-speed travel.
import {Easing, spring} from 'remotion';
import {FPS} from './timing';

export const clamp01 = (x: number) => Math.max(0, Math.min(1, x));
export const lerp = (a: number, b: number, x: number) => a + (b - a) * x;

export const EASE = {
  out: Easing.bezier(0.16, 1, 0.3, 1), // expo-like out: enters
  inOut: Easing.bezier(0.65, 0, 0.35, 1), // travel, camera
  in: Easing.bezier(0.55, 0, 0.75, 0.2), // exits
  linear: (x: number) => x,
};

/** 0 -> 1 between frame `start` and `start + dur`, eased */
export const ease = (fr: number, start: number, dur = 15, e: (x: number) => number = EASE.out) =>
  dur <= 0 ? (fr >= start ? 1 : 0) : e(clamp01((fr - start) / dur));

export const SPRING = {
  pop: {damping: 12, stiffness: 170, mass: 0.7}, // overshoot, for things that appear
  calm: {damping: 26, stiffness: 120, mass: 1}, // settle, for things that move
  stiff: {damping: 30, stiffness: 260, mass: 0.6},
};
/** spring 0 -> 1 (with overshoot for `pop`) starting at `start` */
export const pop = (fr: number, start: number, cfg = SPRING.pop) =>
  fr < start ? 0 : spring({frame: fr - start, fps: FPS, config: cfg});

/** visible span: fades in at `from`, out by `to` */
export const span = (fr: number, from: number, to: number, inDur = 12, outDur = 9) =>
  ease(fr, from, inDur) * (1 - ease(fr, to - outDur, outDur, EASE.in));

/** rise then fall: a highlight that lands at `start`, holds, then fades */
export const bump = (fr: number, start: number, hold = 18, inDur = 7, outDur = 12) =>
  ease(fr, start, inDur) * (1 - ease(fr, start + inDur + hold, outDur, EASE.in));

type Num = Record<string, number>;
/**
 * Keyframed values. keys: [frame, value][] in time order. Before the first key: keys[0] value. At each key the
 * value travels from wherever it is (even mid-move) to the key's value over `dur` frames. Continuous by design,
 * so camera and layout moves never jump.
 */
export function track<T extends Num>(fr: number, keys: [number, T, number?][], dur = 27, e = EASE.inOut): T {
  let v: T = {...keys[0][1]};
  for (let i = 1; i < keys.length; i++) {
    const [at, target, d] = keys[i];
    if (fr < at) break;
    const k = ease(fr, at, d ?? dur, e);
    const nv = {...v};
    for (const key of Object.keys(target)) (nv as Num)[key] = lerp((v as Num)[key] ?? target[key], target[key], k);
    v = nv as T;
  }
  return v;
}

/** discrete value over time: the last key at or before `fr`, plus a 0..1 pop since it changed */
export function steps<V>(fr: number, keys: [number, V][]): {v: V | undefined; since: number; pop: number; i: number} {
  let i = -1;
  for (let k = 0; k < keys.length; k++) if (fr >= keys[k][0]) i = k;
  if (i < 0) return {v: undefined, since: -1, pop: 0, i};
  return {v: keys[i][1], since: keys[i][0], pop: pop(fr, keys[i][0]), i};
}

/** deterministic pseudo-random in [0, 1) from integers */
export const rand = (a: number, b = 0) => {
  const x = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** slow organic drift for holds (camera, floating things) */
export const drift = (fr: number, amp = 1, speed = 1, seed = 0) => ({
  x: amp * (Math.sin((fr / FPS) * 0.31 * speed + seed) + 0.5 * Math.sin((fr / FPS) * 0.73 * speed + seed * 2)),
  y: amp * (Math.cos((fr / FPS) * 0.27 * speed + seed * 3) + 0.5 * Math.sin((fr / FPS) * 0.61 * speed + seed)),
});

/** a short shake (rejections): decays over `dur` frames */
export const shake = (fr: number, start: number, amp = 10, dur = 14) => {
  if (fr < start || fr > start + dur) return 0;
  const k = 1 - (fr - start) / dur;
  return Math.sin((fr - start) * 2.4) * amp * k;
};
