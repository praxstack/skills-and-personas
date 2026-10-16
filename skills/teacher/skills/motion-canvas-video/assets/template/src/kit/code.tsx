// Code panel: a window with syntax colours, ligatures off, chunked reveal and an active-line highlight.
// Focus is shown by the bar and by colour: the active lines keep their full syntax colours, the others turn
// a muted grey that still reads at 5.5:1 or more (quality bar: 4.5:1). Never fade context lines out.
//
//   const cp = new CodePanel({position: [-430, -40], width: 980, height: 700, title: 'solution.cpp', code: CPP});
//   w.hud.add(cp.node);
//   yield* cp.show();
//   yield* cp.reveal(5);            // show the first 5 lines (lines animate in)
//   yield* cp.focus(3);             // highlight bar on line 3 (0-based), other lines recede
//   yield* cp.focus([6, 11]);       // a block
//   yield* cp.clearFocus();
//
// Ligatures: JetBrains Mono turns != <= ++ into single glyphs. Any non-zero letterSpacing makes the canvas
// draw them as separate characters; the panel always sets letterSpacing 0.01.
import {Circle, Code, Node, Rect, Txt, lines as codeLines, type NodeProps} from '@motion-canvas/2d';
import {Color, Vector2, all, createSignal, easeInOutCubic, easeOutCubic, type ThreadGenerator} from '@motion-canvas/core';
import {C, F, S, alpha, cpp, glow} from './theme';
import {panel} from './cards';

/** the grey that unfocused code recedes to (original: 5.1:1 on the panel by itself; a theme: `muted`) */
const RECEDE = C.recede;

export class CodePanel {
  public readonly node: Rect;
  public readonly code: Code;
  private readonly bar: Rect;
  private readonly full: string[];
  private readonly padX = 34;
  private readonly padTop = 72;
  private shown = 0;

  public constructor(
    props: NodeProps & {width: number; height: number; code: string; title?: string; fontSize?: number; highlighter?: typeof cpp},
  ) {
    const {width, height, code, title = 'solution.cpp', fontSize = S.code, highlighter = cpp, ...rest} = props;
    this.full = code.replace(/\s+$/, '').split('\n');
    this.node = panel({width, height, opacity: 0, clip: false, ...rest});
    const left = -width / 2 + this.padX;
    const topY = -height / 2 + this.padTop;
    // window chrome
    this.node.add(new Circle({position: [-width / 2 + 30, -height / 2 + 30], size: 14, fill: C.winRed}));
    this.node.add(new Circle({position: [-width / 2 + 54, -height / 2 + 30], size: 14, fill: C.winAmber}));
    this.node.add(new Circle({position: [-width / 2 + 78, -height / 2 + 30], size: 14, fill: C.winGreen}));
    this.node.add(new Txt({position: [0, -height / 2 + 30], text: title, fontFamily: F.mono, fontSize: S.small, fill: C.muted, letterSpacing: 0.01}));
    this.node.add(new Rect({position: [0, -height / 2 + 56], width: width - 4, height: 2, fill: C.hair}));
    // active-line bar (behind the code)
    this.bar = new Rect({
      x: 0,
      width: width - 16,
      height: 10,
      radius: 8,
      fill: alpha(C.accent, 0.13),
      stroke: alpha(C.accent, 0.5),
      lineWidth: 1.5,
      opacity: 0,
    });
    this.bar.add(new Rect({x: () => -(width - 16) / 2 + 3, width: 6, height: () => this.bar.height() - 6, radius: 3, fill: C.accent, shadowColor: glow(C.accent), shadowBlur: 12}));
    this.node.add(this.bar);
    this.code = new Code({
      highlighter,
      fontFamily: F.mono,
      fontSize,
      letterSpacing: 0.01, // ligatures off
      code: '',
      // unselected lines recede into a muted grey (colour, not transparency): every syntax colour mixed 60%
      // towards RECEDE stays at 5.5:1 or more on the panel, the active line keeps its full colour
      drawHooks: {
        token(ctx, text, position, color, selection) {
          const k = 0.6 * (1 - Math.max(0, Math.min(1, selection)));
          ctx.fillStyle = k > 0.001 ? Color.lerp(color, RECEDE, k).css() : color;
          ctx.fillText(text, position.x, position.y);
        },
      },
    });
    // keep the code's top-left corner fixed while its size changes
    this.code.position(() => new Vector2(left + this.code.width() / 2, topY + this.code.height() / 2));
    this.node.add(this.code);
  }

  public *show(d = 0.5): ThreadGenerator {
    const x = this.node.x();
    this.node.x(x - 60);
    yield* all(this.node.opacity(1, d, easeOutCubic), this.node.x(x, d + 0.2, easeOutCubic));
  }
  public *hide(d = 0.4): ThreadGenerator {
    yield* this.node.opacity(0, d);
  }
  /** Show the first `n` lines of the code (animated diff; d = 0 sets it at once). reveal(Infinity) shows everything. */
  public *reveal(n: number, d = 0.6): ThreadGenerator {
    this.shown = Math.min(this.full.length, n);
    const text = this.full.slice(0, this.shown).join('\n');
    if (d <= 0) {
      this.code.code(text);
      return;
    }
    yield* this.code.code(text, d);
  }
  /** Highlight line `ln` or the block [a, b] (0-based, inclusive). Other lines recede. */
  public *focus(ln: number | [number, number], d = 0.4): ThreadGenerator {
    const [a, b] = typeof ln === 'number' ? [ln, ln] : ln;
    const boxes = this.code.getSelectionBBox(codeLines(a, b));
    if (!boxes.length) throw new Error(`code panel: lines ${a}-${b} are not revealed yet`);
    const top = Math.min(...boxes.map(x => x.top));
    const bottom = Math.max(...boxes.map(x => x.bottom));
    const cy = this.code.position().y + (top + bottom) / 2;
    const h = bottom - top + 2; // one line pitch: the bar never covers the neighbouring lines
    const first = this.bar.opacity() < 0.5;
    if (first) {
      this.bar.y(cy);
      this.bar.height(h);
    }
    yield* all(
      this.bar.opacity(1, d * 0.6),
      this.bar.y(cy, d, easeInOutCubic),
      this.bar.height(h, d, easeInOutCubic),
      this.code.selection(codeLines(a, b), d),
    );
  }
  public *clearFocus(d = 0.4): ThreadGenerator {
    yield* all(this.bar.opacity(0, d), this.code.selection(codeLines(0, Infinity), d));
  }
  /** number of lines in the full code */
  public get length() {
    return this.full.length;
  }
}

export {codeLines};
export type {Node};
