// Code panel: monospace on an exact grid, ligatures off (no != -> ≠), syntax colours from the palette,
// chunked reveal and an active-line highlight that follows the narration.
//
//   const code = new CodePanel({code: CPP, x: -330, y: -40});
//   st.fg.add(code.root);
//   yield* code.in();
//   yield* code.reveal(0, 4);              // lines 0..4 slide in
//   yield* code.focus(9, 2);               // highlight lines 9-10; the rest turn a quieter (still 7:1) tone
import {Circle, Node, Rect, Txt} from '@revideo/2d';
import {all, easeInOutCubic, easeOutCubic, sequence, ThreadGenerator, waitFor} from '@revideo/core';
import {C, CODE, contrast, drop, F, glow, lineOf, S, THEMED} from './theme';
import {measure} from './text';

/** Syntax colours (kit/theme.ts `CODE`: the original palette, or a theme's inks). */
export const CODE_COLORS = {
  kw: CODE.kw,         // keywords
  type: CODE.type,     // types
  num: CODE.num,       // numbers
  str: CODE.str,       // strings
  com: CODE.com,       // comments (7.5:1 on the panel; quieter than code, still readable)
  fn: CODE.fn,         // function names
  punct: CODE.punct,   // operators and brackets
  id: CODE.id,         // identifiers
  gutter: CODE.gutter, // line numbers
};
/** Context lines (outside the focus) keep their hue but move 60% toward this grey: every token stays >= 7:1. */
const DIM_TOWARD = CODE.dimToward, DIM_MIX = 0.6;
const hex = (c: string) => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
export function quiet(c: string) {
  const a = hex(c), b = hex(DIM_TOWARD);
  const q = '#' + a.map((v, i) => Math.round(v + (b[i] - v) * DIM_MIX).toString(16).padStart(2, '0')).join('');
  // a theme's inks sit near 4.6:1, and a mix of two hues can dip under it: fall back to the quiet colour itself
  return THEMED && contrast(q, C.code) < 4.6 ? DIM_TOWARD : q;
}
const KW = new Set(['if', 'else', 'for', 'while', 'return', 'const', 'auto', 'break', 'continue', 'new', 'delete', 'class',
  'struct', 'public', 'private', 'static', 'def', 'in', 'not', 'and', 'or', 'lambda', 'None', 'True', 'False', 'let', 'var',
  'function', 'using', 'namespace', 'template', 'typename', 'this', 'nullptr', 'true', 'false', 'do', 'switch', 'case']);
const TYPES = new Set(['int', 'long', 'double', 'float', 'bool', 'char', 'void', 'string', 'vector', 'pair', 'map', 'set',
  'unordered_map', 'unordered_set', 'queue', 'priority_queue', 'deque', 'array', 'size_t', 'List', 'Dict', 'Integer']);

export interface Tok {t: string; c: string; col: number}
/** Split a line into coloured tokens on a column grid. */
export function tokenize(line: string): Tok[] {
  const out: Tok[] = [];
  let ci = line.indexOf('//');
  if (ci < 0 && /^\s*#(?!include|define)/.test(line)) ci = line.indexOf('#');
  const code = ci >= 0 ? line.slice(0, ci) : line;
  const re = /("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|[A-Za-z_]\w*|\d+(?:\.\d+)?(?:e\d+)?|\s+|.)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(code))) {
    const t = m[1];
    if (!t.trim()) continue;
    const next = code.slice(m.index + t.length).trimStart()[0];
    const c = KW.has(t) ? CODE_COLORS.kw : TYPES.has(t) ? CODE_COLORS.type : /^\d/.test(t) ? CODE_COLORS.num
      : /^["']/.test(t) ? CODE_COLORS.str : /^[A-Za-z_]/.test(t) ? (next === '(' ? CODE_COLORS.fn : CODE_COLORS.id) : CODE_COLORS.punct;
    out.push({t, c, col: m.index});
  }
  if (ci >= 0) out.push({t: line.slice(ci), c: CODE_COLORS.com, col: ci});
  return out;
}

export class CodePanel {
  readonly root: Rect;
  readonly lines: Node[] = [];
  /** Per line: each token's Txt with its full and its quiet colour. */
  readonly toks: {txt: Txt; on: string; off: string}[][] = [];
  readonly hl: Rect;
  readonly hlBar: Rect;
  readonly src: string[];
  readonly lh: number;
  readonly top: number;
  readonly left: number;
  private shown = new Set<number>();

  constructor(o: {code: string | string[]; x?: number; y?: number; size?: number; title?: string; width?: number; lineHeight?: number;
    headHeight?: number}) {
    const size = o.size ?? S.code;
    this.src = Array.isArray(o.code) ? o.code : o.code.replace(/\n$/, '').split('\n');
    const cw = measure('M', size, F.mono, 500) + 0.01;
    this.lh = o.lineHeight ?? Math.round(size * 1.48);
    const gutter = cw * 3 + 26;
    const longest = Math.max(...this.src.map(s => s.length));
    const width = o.width ?? Math.ceil(gutter + longest * cw + 64);
    const bodyH = this.src.length * this.lh;
    const headH = o.headHeight ?? 58;
    const height = bodyH + headH + 36;
    this.root = new Rect({
      x: o.x ?? 0, y: o.y ?? 0, width, height, radius: 20, fill: C.code, stroke: C.line, lineWidth: 2,
      shadowColor: drop(0.65), shadowBlur: 60, shadowOffset: [0, 24], clip: true, opacity: 0,
    });
    // header: three dots and a file name
    const head = new Rect({y: -height / 2 + headH / 2, width, height: headH, fill: C.codeHead});
    CODE.dots.forEach((c, i) => head.add(new Circle({size: 14, fill: c, x: -width / 2 + 30 + i * 24, opacity: 0.85})));
    head.add(new Txt({text: o.title ?? 'solution.cpp', fontFamily: F.mono, fontWeight: 600, fontSize: S.tiny, fill: C.muted,
      x: -width / 2 + 116, offset: [-1, 0], letterSpacing: 0.01}));
    this.root.add(head);
    this.top = -height / 2 + headH + 18 + this.lh / 2;
    this.left = -width / 2;
    this.hl = new Rect({x: 0, y: this.top, width: width - 4, height: this.lh, fill: C.accSoft, opacity: 0});
    this.hlBar = new Rect({x: -width / 2 + 4, y: this.top, width: 6, height: this.lh, fill: lineOf(C.acc), opacity: 0,
      shadowColor: glow(C.acc), shadowBlur: 14});
    this.root.add(this.hl);
    this.root.add(this.hlBar);
    this.src.forEach((s, i) => {
      const ln = new Node({y: this.top + i * this.lh, opacity: 0});
      const row: {txt: Txt; on: string; off: string}[] = [];
      const num = new Txt({text: String(i + 1), fontFamily: F.mono, fontWeight: 500, fontSize: Math.max(28, size * 0.9),
        fill: CODE_COLORS.gutter, x: -width / 2 + gutter - 26, offset: [1, 0], letterSpacing: 0.01});
      ln.add(num);
      row.push({txt: num, on: CODE_COLORS.gutter, off: CODE_COLORS.gutter});
      for (const tk of tokenize(s)) {
        const t = new Txt({text: tk.t, fontFamily: F.mono, fontWeight: 500, fontSize: size, fill: tk.c, offset: [-1, 0],
          x: -width / 2 + gutter + tk.col * cw, letterSpacing: 0.01});
        ln.add(t);
        row.push({txt: t, on: tk.c, off: quiet(tk.c)});
      }
      this.root.add(ln);
      this.lines.push(ln);
      this.toks.push(row);
    });
  }

  *in(d = 0.5): ThreadGenerator {
    const y = this.root.y();
    this.root.y(y + 30);
    yield* all(this.root.opacity(1, d), this.root.y(y, d, easeOutCubic));
  }
  *out(d = 0.3): ThreadGenerator {
    yield* this.root.opacity(0, d);
  }
  /** Reveal lines from..to (inclusive), staggered. */
  *reveal(from: number, to: number, stagger = 0.06): ThreadGenerator {
    const idx = [...Array(to - from + 1).keys()].map(i => i + from);
    idx.forEach(i => this.shown.add(i));
    yield* sequence(stagger, ...idx.map(i => {
      const ln = this.lines[i];
      return all(ln.opacity(1, 0.3), (function* () { ln.x(-18); yield* ln.x(0, 0.4, easeOutCubic); })());
    }));
  }
  revealAll() {
    this.lines.forEach((l, i) => { l.opacity(1); this.shown.add(i); });
  }
  /**
   * Highlight lines i..i+n-1 (accent bar + tint, full syntax colours); the other lines turn quieter by colour, not
   * by opacity: a 0.38-opacity line measured 2.4:1, unreadable, while the quiet tones keep every token >= 7:1.
   */
  *focus(i: number, n = 1, d = 0.35): ThreadGenerator {
    const y = this.top + (i + (n - 1) / 2) * this.lh, h = n * this.lh;
    if (this.hl.opacity() < 0.01) { this.hl.y(y).height(h); this.hlBar.y(y).height(h); }
    yield* all(
      this.hl.y(y, d, easeInOutCubic), this.hl.height(h, d, easeInOutCubic), this.hl.opacity(1, d),
      this.hlBar.y(y, d, easeInOutCubic), this.hlBar.height(h, d, easeInOutCubic), this.hlBar.opacity(1, d),
      ...this.toks.flatMap((row, j) => row.map(tk => tk.txt.fill(j >= i && j < i + n ? tk.on : tk.off, d))),
    );
  }
  *unfocus(d = 0.35): ThreadGenerator {
    yield* all(this.hl.opacity(0, d), this.hlBar.opacity(0, d),
      ...this.toks.flatMap(row => row.map(tk => tk.txt.fill(tk.on, d))));
  }
  /** Local y of line i (for annotations next to the panel). */
  lineY(i: number) {
    return this.root.y() + this.top + i * this.lh;
  }
}
