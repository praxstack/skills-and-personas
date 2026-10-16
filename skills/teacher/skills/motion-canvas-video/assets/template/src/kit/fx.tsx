// Small reusable effects: pops, chips, ticking counters, comic bursts, stamps, ripples.
import {Circle, Line, Node, Rect, Txt, type NodeProps} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  chain,
  createSignal,
  delay,
  easeInCubic,
  easeOutBack,
  easeOutCubic,
  easeOutExpo,
  sequence,
  waitFor,
  type PossibleVector2,
  type ThreadGenerator,
} from '@motion-canvas/core';
import {C, F, S, alpha, glow, inkOf, lift, onFill, shade, tint} from './theme';
import {rng} from './world';
import {LIGHT as LIGHT_SHADOW} from './theme';

/** Scale a node in from 0 with an overshoot (the node should start at scale 0). */
export function* pop(node: Node, d = 0.45): ThreadGenerator {
  yield* node.scale(1, d, easeOutBack);
}
/** Fade + rise in (the node should start at opacity 0). */
export function* appear(node: Node, d = 0.45, rise = 24): ThreadGenerator {
  const y = node.y();
  node.y(y + rise);
  yield* all(node.opacity(1, d, easeOutCubic), node.y(y, d, easeOutCubic));
}
/** Fade out and remove. */
export function* vanish(node: Node, d = 0.3): ThreadGenerator {
  yield* node.opacity(0, d);
  node.remove();
}
/** A quick scale bump to say "this changed". */
export function* bump(node: Node, s = 1.15, d = 0.35): ThreadGenerator {
  yield* chain(node.scale(s, d * 0.4, easeOutCubic), node.scale(1, d * 0.6, easeOutCubic));
}

/** A rounded label: chip('1 stop', C.good). Add `.node` to a parent. */
export class Chip {
  public readonly node: Rect;
  public readonly txt: Txt;
  public constructor(text: string, color: string = C.accent, props: NodeProps & {fontSize?: number; mono?: boolean} = {}) {
    const {fontSize = S.label, mono = false, ...rest} = props;
    this.txt = new Txt({
      text,
      fontFamily: mono ? F.mono : F.body,
      fontWeight: mono ? 700 : 600,
      fontSize,
      fill: lift(color),
      letterSpacing: mono ? 0.01 : 0.5,
    });
    this.node = new Rect({
      layout: true,
      padding: [8, 18],
      radius: 999,
      fill: tint(color, 0.14),
      stroke: alpha(color, 0.85),
      lineWidth: 2,
      shadowColor: glow(color, 0.35),
      shadowBlur: 18,
      scale: 0,
      ...rest,
      children: [this.txt],
    });
  }
  public *show(d = 0.4) {
    yield* pop(this.node, d);
  }
  public *hide(d = 0.25) {
    yield* this.node.scale(0, d, easeInCubic);
  }
  /** change text and colour with a little bump */
  public *set(text: string, color?: string) {
    if (color) {
      this.txt.fill(lift(color));
      this.node.stroke(alpha(color, 0.85));
      this.node.fill(tint(color, 0.14));
      this.node.shadowColor(glow(color, 0.35));
    }
    yield* all(this.txt.text(text, 0.25), bump(this.node, 1.08));
  }
}

/** A number that ticks to its new value: new Counter({label: 'cost', x, y}); yield* c.to(700, 0.8). */
export class Counter {
  public readonly node: Rect;
  public readonly value = createSignal(0);
  private readonly num: Txt;
  public constructor(props: {label?: string; prefix?: string; color?: string; fontSize?: number} & NodeProps = {}) {
    const {label = '', prefix = '', color = C.ink, fontSize = 44, ...rest} = props;
    this.num = new Txt({
      text: () => prefix + Math.round(this.value()).toString(),
      fontFamily: F.mono,
      fontWeight: 700,
      fontSize,
      fill: inkOf(color),
      letterSpacing: 0.01,
    });
    this.node = new Rect({
      layout: true,
      direction: 'column',
      alignItems: 'center',
      gap: 2,
      padding: [12, 24],
      radius: 18,
      fill: alpha(C.panel, 0.92),
      stroke: C.line,
      lineWidth: 2,
      shadowColor: shade(0.55),
      shadowBlur: 30,
      shadowOffset: [0, 10],
      opacity: 0,
      ...rest,
      children: [
        ...(label
          ? [new Txt({text: label.toUpperCase(), fontFamily: F.body, fontWeight: 600, fontSize: S.small, letterSpacing: 3, fill: C.muted})]
          : []),
        this.num,
      ],
    });
  }
  public *to(v: number, d = 0.6) {
    yield* all(this.value(v, d, easeOutCubic), bump(this.num, 1.12, Math.max(0.3, d)));
  }
  public *show(d = 0.35) {
    yield* this.node.opacity(1, d);
  }
  public *hide(d = 0.25) {
    yield* this.node.opacity(0, d);
  }
  public color(c: string) {
    this.num.fill(inkOf(c));
  }
}

/** An expanding ring at a point (a node arriving, a value landing). Adds itself to `layer` and cleans up. */
export function* ripple(layer: Node, at: PossibleVector2, color: string = C.accent, size = 110, d = 0.8): ThreadGenerator {
  const ring = new Circle({position: at, size, stroke: color, lineWidth: 6, opacity: 0.95});
  layer.add(ring);
  yield* all(ring.size(size * 2.3, d, easeOutCubic), ring.opacity(0, d, easeOutCubic), ring.lineWidth(1, d));
  ring.remove();
}

function starPoints(spikes: number, rOut: number, rIn: number, seed: number) {
  const r = rng(seed);
  const pts: Vector2[] = [];
  for (let i = 0; i < spikes * 2; i++) {
    const a = (Math.PI * i) / spikes - Math.PI / 2;
    const rad = i % 2 === 0 ? rOut * (0.86 + 0.28 * r()) : rIn * (0.9 + 0.2 * r());
    pts.push(new Vector2(Math.cos(a) * rad, Math.sin(a) * rad * 0.78));
  }
  return pts;
}

let measureCtx: CanvasRenderingContext2D | null = null;
/** Width in px of `text` drawn with a CSS font string (fonts are loaded before the first frame). */
export function measure(text: string, font: string): number {
  measureCtx ??= document.createElement('canvas').getContext('2d');
  measureCtx.font = font;
  return measureCtx.measureText(text).width;
}

export interface BurstOptions {
  at: PossibleVector2;
  color?: string; // burst fill
  ink?: string; // text fill
  size?: number; // outer radius in px
  rotation?: number;
  hold?: number; // seconds fully visible
  fontSize?: number;
  seed?: number;
}

/**
 * Comic onomatopoeia: a jagged starburst with a hard shadow, speed lines and Bangers lettering.
 *   yield* burst(w.top, '700!', {at: [520, -120]});
 * Runs in, holds, and pops out (pair it with an "sfx": [{"kind": "pop"}] cue on the line).
 * Text with a digit is lettered in Inter 800 instead: Bangers' 7 reads as 1 (a "700!" burst read "100!").
 */
export function* burst(layer: Node, text: string, o: BurstOptions): ThreadGenerator {
  const size = o.size ?? 150;
  const color = o.color ?? C.gold;
  const ink = o.ink ?? onFill(color, C.burstInk);
  const seed = o.seed ?? text.length * 31 + Math.round(size);
  const digits = /\d/.test(text);
  const family = digits ? F.display : F.comic;
  const weight = digits ? 800 : 400;
  // Measure the lettering with a plain canvas (a Txt that is not in the scene yet reports no width),
  // then stretch the star sideways to hold it; very long words also get a smaller font.
  let fontSize = o.fontSize ?? Math.round(size * (digits ? 0.56 : 0.62));
  const inner = size * 0.6;
  const textW = measure(text, `${weight} ${fontSize}px ${family}`) + text.length * 2;
  let sx = Math.max(1, (textW / 2 + size * 0.1) / inner);
  if (sx > 1.9) {
    fontSize = Math.floor((fontSize * 1.9) / sx);
    sx = 1.9;
  }
  const label = new Txt({
    text,
    fontFamily: family,
    fontWeight: weight,
    fontSize,
    fill: ink,
    letterSpacing: digits ? 0.5 : 2,
    y: 4,
    rotation: -2,
  });
  const pts = starPoints(13, size, size * 0.66, seed).map(p => new Vector2(p.x * sx, p.y));
  const g = new Node({position: o.at, rotation: o.rotation ?? -7, scale: 0});
  const lines = new Node({});
  const r = rng(seed + 5);
  const speed: Line[] = [];
  for (let i = 0; i < 10; i++) {
    const a = (Math.PI * 2 * i) / 10 + r() * 0.3;
    const dir = new Vector2(Math.cos(a) * sx, Math.sin(a) * 0.8);
    const l = new Line({
      points: [dir.scale(size * 1.05), dir.scale(size * 1.55)],
      stroke: color,
      lineWidth: 6,
      lineCap: 'round',
      end: 0,
    });
    speed.push(l);
    lines.add(l);
  }
  g.add(lines);
  g.add(new Line({points: pts, closed: true, fill: C.shadow, position: [10, 12], opacity: LIGHT_SHADOW ? 0.3 : 0.85}));
  g.add(new Line({points: pts, closed: true, fill: color, stroke: C.burstLine, lineWidth: 6, lineJoin: 'round'}));
  g.add(label);
  layer.add(g);
  yield* all(
    g.scale(1, 0.42, easeOutBack),
    g.rotation((o.rotation ?? -7) + 5, 0.42, easeOutCubic),
    sequence(0.015, ...speed.map(l => chain(l.end(1, 0.18, easeOutExpo), l.start(1, 0.3, easeOutCubic)))),
  );
  yield* waitFor(o.hold ?? 0.9);
  yield* all(g.scale(0, 0.25, easeInCubic), g.opacity(0, 0.25));
  g.remove();
}

/**
 * A rubber stamp that slams down (a verdict: "TOO MANY STOPS", "O(n^(k+1))"). Returns the node so it can stay;
 * remove it later with vanish(). Pair with camera.shake() and a "thud" sfx.
 */
export function stamp(layer: Node, text: string, o: {at: PossibleVector2; color?: string; rotation?: number; fontSize?: number}) {
  const color = o.color ?? C.bad;
  const node = new Rect({
    position: o.at,
    rotation: o.rotation ?? -6,
    layout: true,
    padding: [10, 26],
    radius: 10,
    stroke: color,
    lineWidth: 5,
    fill: alpha(C.bg, 0.9),
    shadowColor: glow(color, 0.45),
    shadowBlur: 24,
    opacity: 0,
    scale: 1.8,
    children: [new Txt({text, fontFamily: F.comic, fontSize: o.fontSize ?? 54, fill: inkOf(color), letterSpacing: 3})],
  });
  layer.add(node);
  return {
    node,
    *slam(d = 0.28): ThreadGenerator {
      yield* all(node.opacity(1, d * 0.6), node.scale(1, d, easeInCubic));
      yield* bump(node, 1.06, 0.25);
    },
  };
}

/** Animate a straight arrow drawing between two points (keeps its arrowhead hidden until it draws). */
export function* drawArrow(layer: Node, from: PossibleVector2, to: PossibleVector2, color: string = C.muted, d = 0.5) {
  const l = new Line({points: [from, to], stroke: color, lineWidth: 4, endArrow: true, arrowSize: 14, end: 0, opacity: 0, lineCap: 'round'});
  layer.add(l);
  l.opacity(1);
  yield* l.end(1, d, easeOutCubic);
  return l;
}

export {delay};

/** A small label that rises and fades from a point ("+100" when a cost is paid). */
export function* floatUp(layer: Node, text: string, at: PossibleVector2, color: string = C.good, d = 1.0): ThreadGenerator {
  const p = new Vector2(at);
  const t = new Txt({position: p, text, fontFamily: F.mono, fontWeight: 700, fontSize: 32, fill: inkOf(color), letterSpacing: 0.01, shadowColor: glow(color, 0.6), shadowBlur: 12, opacity: 0, scale: 0.7});
  layer.add(t);
  yield* all(t.opacity(1, 0.15), t.scale(1, 0.3, easeOutBack), t.y(p.y - 70, d, easeOutCubic), delay(d * 0.6, t.opacity(0, d * 0.4)));
  t.remove();
}
