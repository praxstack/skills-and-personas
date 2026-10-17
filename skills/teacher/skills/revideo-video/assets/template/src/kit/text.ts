// Type helpers: measuring, masked word-rise headlines, mono labels, O(...) with a real superscript.
import {Node, Rect, Txt} from '@revideo/2d';
import {all, easeInCubic, easeOutQuart, sequence, ThreadGenerator} from '@revideo/core';
import {C, F, S, textOf} from './theme';

const mctx = document.createElement('canvas').getContext('2d')!;
/** Width of `text` in px (fonts must be loaded; project.ts awaits them). */
export function measure(text: string, size: number, family = F.display, weight = 700) {
  mctx.font = `${weight} ${size}px ${family}`;
  return mctx.measureText(text).width;
}

// Inline colour marks for headlines: *accent*  ~mint~  !rose!  ^muted^
// (a theme sets them in the hue's solved ink: textOf)
const MARK: Record<string, string> = {'*': textOf(C.acc), '~': textOf(C.mint), '!': textOf(C.rose), '^': C.muted};

export interface Kinetic {
  root: Node;
  words: {clip: Rect; txt: Txt; h: number}[];
  width: number;
  in: (dur?: number, stagger?: number) => ThreadGenerator;
  out: (dur?: number, stagger?: number) => ThreadGenerator;
}

/**
 * Masked word-rise headline. Each word rises out of its own clip; `\n` breaks lines.
 *   const h = kinetic('k stops = *k + 1* flights', {size: 72, y: -40}); stage.fg.add(h.root); yield* h.in();
 */
export function kinetic(text: string, o: {
  size?: number; family?: string; weight?: number; fill?: string; x?: number; y?: number;
  align?: 'center' | 'left'; lead?: number; gap?: number; shadow?: boolean;
} = {}): Kinetic {
  const size = o.size ?? S.h2, family = o.family ?? F.display, weight = o.weight ?? 700;
  const lead = o.lead ?? size * 1.1, gap = o.gap ?? size * 0.27, h = size * 1.36;
  const root = new Node({x: o.x ?? 0, y: o.y ?? 0});
  const words: Kinetic['words'] = [];
  let width = 0;
  const lines = text.split('\n');
  lines.forEach((line, li) => {
    // a mark may span words: '*k + 1* flights' colours "k", "+", "1"
    let open: string | null = null;
    const toks = line.split(' ').filter(Boolean).map(raw => {
      let t = raw, c = open ? MARK[open] : (o.fill ?? C.ink);
      if (!open && t.length > 1 && MARK[t[0]]) { open = t[0]; c = MARK[open]; t = t.slice(1); }
      const m = open ? t.match(new RegExp(`^(.*)\\${open}([.,!?:;]?)$`)) : null;
      if (m) { t = m[1] + m[2]; open = null; }
      return {t, c};
    });
    const ws = toks.map(t => measure(t.t, size, family, weight));
    const lw = ws.reduce((a, b) => a + b, 0) + gap * (toks.length - 1);
    width = Math.max(width, lw);
    let x = o.align === 'left' ? 0 : -lw / 2;
    const y = (li - (lines.length - 1) / 2) * lead;
    toks.forEach((t, i) => {
      const clip = new Rect({clip: true, width: ws[i] + size * 0.4, height: h, x: x + ws[i] / 2, y});
      const txt = new Txt({
        text: t.t, fontFamily: family, fontWeight: weight, fontSize: size, fill: t.c, y: h,
        ...(o.shadow !== false ? {shadowColor: C.textShadow, shadowBlur: 24, shadowOffset: [0, 8]} : {}),
      });
      clip.add(txt);
      root.add(clip);
      words.push({clip, txt, h});
      x += ws[i] + gap;
    });
  });
  return {
    root, words, width,
    in: (dur = 0.7, stagger = 0.07) => sequence(stagger, ...words.map(w => w.txt.y(0, dur, easeOutQuart))),
    out: (dur = 0.35, stagger = 0.03) => sequence(stagger, ...words.map(w =>
      all(w.txt.y(-w.h * 1.1, dur, easeInCubic), w.clip.opacity(0, dur, easeInCubic)))),
  };
}

/** Small uppercase mono label (kickers, axis names). 30 px by default, never under 28 (the floor is 26, measured). */
export function label(text: string, o: {x?: number; y?: number; fill?: string; size?: number; weight?: number; anchor?: 'left' | 'right' | 'center'} = {}) {
  const t = new Txt({
    text, x: o.x ?? 0, y: o.y ?? 0, fontFamily: F.mono, fontSize: Math.max(28, o.size ?? S.tiny),
    fontWeight: o.weight ?? 600, fill: o.fill ?? C.muted, letterSpacing: 2,
  });
  if (o.anchor === 'left') t.offset([-1, 0]);
  if (o.anchor === 'right') t.offset([1, 0]);
  return t;
}

/** Code-safe mono text: letterSpacing 0.01 turns JetBrains Mono ligatures off (no != -> ≠). */
export function mono(text: string, o: {x?: number; y?: number; fill?: string; size?: number; weight?: number} = {}) {
  return new Txt({
    text, x: o.x ?? 0, y: o.y ?? 0, fontFamily: F.mono, fontSize: o.size ?? S.body,
    fontWeight: o.weight ?? 600, fill: o.fill ?? C.ink, letterSpacing: 0.01,
  });
}

/**
 * Big-O with a real superscript: bigO('n', 'k+1') draws O(n^(k+1)); bigO('k·E') draws O(k·E).
 * Returns a Node centred on its own middle (anchor: 'left' puts its left edge at x = 0).
 */
export function bigO(base: string, sup = '', o: {size?: number; fill?: string; family?: string; anchor?: 'left' | 'center'} = {}) {
  const size = o.size ?? S.h2, fill = o.fill ?? C.ink, family = o.family ?? F.display;
  const root = new Node({});
  const parts: [string, number, number][] = [[`O(${base}`, size, 0]];
  if (sup) parts.push([sup, size * 0.56, -size * 0.38]);
  parts.push([')', size, 0]);
  const ws = parts.map(([t, s]) => measure(t, s, family, 700));
  const total = ws.reduce((a, b) => a + b, 0) + (sup ? size * 0.08 : 0);
  let x = o.anchor === 'left' ? 0 : -total / 2;
  parts.forEach(([t, s, dy], i) => {
    root.add(new Txt({text: t, fontFamily: family, fontWeight: 700, fontSize: s, fill, offset: [-1, 0], x, y: dy}));
    x += ws[i] + (i === 0 && sup ? size * 0.04 : 0) + (i === 1 ? size * 0.04 : 0);
  });
  return root;
}
