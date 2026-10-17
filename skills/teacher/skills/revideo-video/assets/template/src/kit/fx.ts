// Effects: comic callout bursts ("700!", "POP!"), flying copies (a value travels from A to B),
// numeric counters that tick, and a shake.
import {Line, Node, Rect, Txt} from '@revideo/2d';
import {
  all, createSignal, delay, easeInBack, easeInCubic, easeInOutCubic, easeOutBack, easeOutCubic, sequence,
  ThreadGenerator, tween, Vector2, waitFor,
} from '@revideo/core';
import {burstInkOf, C, drop, F, glow, inkOf, lineOf} from './theme';
import {onFrame, rng} from './time';
import {measure} from './text';
import type {Stage} from './stage';
export {shake} from './graph';

/**
 * Comic burst: a jagged star with a word in a comic face, popping with overshoot and speed lines.
 *   yield* burst(st.fx, '700!', {x: 420, y: -260});
 * It removes itself after `hold` seconds. Spawn it (`yield burst(...)`, no star) to keep animating meanwhile.
 * The speed lines reach about 1.8x the star's half-width; in a crowded frame (code beside a table) pass
 * `rays: false` so they do not cross text, and put the star in an empty corner.
 */
export function* burst(parent: Node, text: string, o: {
  x?: number; y?: number; size?: number; color?: string; ink?: string; rot?: number; hold?: number; seed?: number;
  rays?: boolean;
} = {}): ThreadGenerator {
  const size = o.size ?? 104, color = o.color ?? C.gold, ink = o.ink ?? burstInkOf(color);
  const r = rng(o.seed ?? text.length * 7 + 3);
  // Bangers' 7 reads as a 1 ("700!" looked like "100!"): text with digits is set in Inter Display, heavy
  const digits = /\d/.test(text), face = digits ? F.display : F.comic, weight = digits ? 800 : 400;
  const tw = measure(text, size, face, weight);
  const rx = tw / 2 + size * 0.75, ry = size * 0.95;
  const root = new Node({x: o.x ?? 0, y: o.y ?? 0, rotation: (o.rot ?? -8) - 16, scale: 0});
  const star = (sx: number, sy: number) => {
    const pts: Vector2[] = [];
    const n = 15;
    for (let i = 0; i < n * 2; i++) {
      const a = (i / (n * 2)) * Math.PI * 2;
      const k = i % 2 === 0 ? 1 + r() * 0.22 : 0.68 + r() * 0.08;
      pts.push(new Vector2(Math.cos(a) * rx * k * sx, Math.sin(a) * ry * k * sy));
    }
    return pts;
  };
  const back = new Line({points: star(1.08, 1.12), closed: true, fill: C.acc, x: 10, y: 12, lineJoin: 'round'});
  const front = new Line({points: star(1, 1), closed: true, fill: color, stroke: C.burstLine, lineWidth: 7, lineJoin: 'round',
    shadowColor: drop(0.55), shadowBlur: 26, shadowOffset: [0, 10]});
  const word = new Txt({text, fontFamily: face, fontWeight: weight, fontStyle: digits ? 'italic' : 'normal', fontSize: size, fill: ink,
    y: size * 0.04, letterSpacing: digits ? 0 : 1});
  const rays = new Node({});
  for (let i = 0; i < (o.rays === false ? 0 : 12); i++) {
    const a = (i / 12) * Math.PI * 2 + r() * 0.2;
    const d0 = new Vector2(Math.cos(a) * rx * 1.25, Math.sin(a) * ry * 1.3);
    const d1 = d0.scale(1.45);
    rays.add(new Line({points: [d0, d1], stroke: lineOf(color), lineWidth: 6, lineCap: 'round', end: 0}));
  }
  root.add(rays);
  root.add(back);
  root.add(front);
  root.add(word);
  parent.add(root);
  yield* all(
    root.scale(1, 0.45, easeOutBack),
    root.rotation(o.rot ?? -8, 0.5, easeOutCubic),
    ...rays.children().map((l, i) => delay(0.05 + i * 0.01, all((l as Line).end(1, 0.3, easeOutCubic), delay(0.2, (l as Line).start(1, 0.35, easeInCubic))))),
  );
  yield* root.scale(1.04, (o.hold ?? 0.9) / 2).to(1, (o.hold ?? 0.9) / 2);
  yield* all(root.scale(0, 0.25, easeInBack), root.opacity(0, 0.25));
  root.remove();
}

/**
 * A numeric value shown in a Txt that tweens like a signal:
 *   const cost = counter(costTxt, v => `COST ${Math.round(v)}`); yield* cost(700, 1.2);
 */
export function counter(txt: Txt, fmt: (v: number) => string = v => String(Math.round(v)), start = 0) {
  const v = createSignal(start);
  txt.text(fmt(start));
  onFrame(() => txt.text(fmt(v())));
  return v;
}

/**
 * A copy of a value flies from one node to another along an arc (motion has a source and a destination).
 * Works across camera and layout transforms: positions are taken in screen space.
 *   yield* fly(st, '100', decoder.itemNode(0), graph.edge(0, 1).tag!, {color: C.acc});
 */
export function* fly(st: Stage, text: string, from: Node | Vector2, to: Node | Vector2, o: {
  color?: string; size?: number; toSize?: number; d?: number; arc?: number; family?: string; keep?: boolean;
} = {}): ThreadGenerator {
  const a = from instanceof Vector2 ? from : st.screenPos(from);
  const b = to instanceof Vector2 ? to : st.screenPos(to);
  const size = o.size ?? 34, d = o.d ?? 0.8;
  const pill = new Rect({position: a, layout: true, padding: [4, 12], radius: 10, fill: C.pill,
    stroke: lineOf(o.color ?? C.acc), lineWidth: 2, shadowColor: glow(o.color ?? C.acc), shadowBlur: 22});
  pill.add(new Txt({text, fontFamily: o.family ?? F.mono, fontWeight: 700, fontSize: size, fill: inkOf(o.color ?? C.acc), letterSpacing: 0.01}));
  st.top.add(pill);
  const ctrl = a.add(b).scale(0.5).add([0, -(o.arc ?? 160)]);
  const s1 = (o.toSize ?? size) / size;
  yield* all(
    tween(d, t => {
      const e = easeInOutCubic(t);
      const p = a.scale((1 - e) ** 2).add(ctrl.scale(2 * (1 - e) * e)).add(b.scale(e * e));
      pill.position(p);
    }),
    pill.scale(1.15, d * 0.4, easeOutCubic).to(s1, d * 0.6, easeInOutCubic),
  );
  if (!o.keep) {
    yield* pill.opacity(0, 0.18);
    pill.remove();
  }
}

export {sequence, waitFor};
