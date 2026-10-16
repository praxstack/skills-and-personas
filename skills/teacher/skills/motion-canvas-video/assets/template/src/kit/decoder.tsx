// Input decoder: the raw input as code text, whose entries fly into the subject.
//
//   const inp = new InputPanel({position: [0, -380], rows: [
//     {name: 'n', parts: ['4']},
//     {name: 'flights', parts: ['[0,1,100]', '[1,2,100]', ...], list: true},
//   ]});
//   w.hud.add(inp.node);
//   yield* inp.showRow(1);                                    // `flights = [ ... ]` types in
//   yield* inp.fly(1, 0, w.top, graph.edge(0, 1).pill);       // entry 0 flies to the edge's weight pill
//   yield* inp.mark(1, 0, C.good);                            // tint an entry
//
// The flying copy tracks its target while it moves, so a camera move during the flight still lands.
import {Layout, Node, Rect, Txt, type NodeProps} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  createSignal,
  easeInOutCubic,
  easeOutCubic,
  sequence,
  type ThreadGenerator,
} from '@motion-canvas/core';
import {C, F, S, alpha, glow, inkOf, shade} from './theme';
import {bump} from './fx';

function* chainBump(t: Txt) {
  yield* bump(t, 1.18, 0.4);
}
import {posIn} from './world';

export interface InputRow {
  /** `name = [ a, b, c ]` (list: true) or `name = a` */
  name?: string;
  parts?: string[];
  list?: boolean;
  /** several assignments on one row: [['n', '4'], ['src', '0']] -> `n = 4    src = 0`; part i is the i-th value */
  assign?: [string, string][];
}

export class InputPanel {
  public readonly node: Rect;
  public readonly rows: {row: Layout; parts: Txt[]; names: (Txt | null)[]}[] = [];
  private readonly fontSize: number;

  public constructor(props: NodeProps & {rows: InputRow[]; fontSize?: number; title?: string}) {
    const {rows, fontSize = S.mono - 2, title = 'INPUT', ...rest} = props;
    this.fontSize = fontSize;
    const mono = {fontFamily: F.mono, fontSize, letterSpacing: 0.01};
    this.node = new Rect({
      layout: true,
      direction: 'column',
      gap: 10,
      padding: [20, 30],
      radius: 20,
      fill: alpha(C.panel, 0.9),
      stroke: C.line,
      lineWidth: 2,
      shadowColor: shade(0.6),
      shadowBlur: 40,
      shadowOffset: [0, 14],
      opacity: 0,
      ...rest,
    });
    this.node.add(new Txt({text: title, fontFamily: F.body, fontWeight: 600, fontSize: S.small, letterSpacing: 4, fill: C.muted}));
    for (const r of rows) {
      const parts: Txt[] = [];
      const names: (Txt | null)[] = [];
      const row = new Layout({direction: 'row', alignItems: 'center', gap: 0, opacity: 0});
      if (r.assign) {
        r.assign.forEach(([n, v], i) => {
          const nt = new Txt({...mono, text: n, fill: inkOf(C.cool), fontWeight: 700});
          const vt = new Txt({...mono, text: v, fill: C.ink});
          row.add([nt, new Txt({...mono, text: '\u00A0=\u00A0', fill: C.muted}), vt]);
          if (i < r.assign!.length - 1) row.add(new Txt({...mono, text: '\u00A0\u00A0\u00A0\u00A0\u00A0', fill: C.muted}));
          parts.push(vt);
          names.push(nt);
        });
      } else {
        row.add(new Txt({...mono, text: r.name ?? '', fill: inkOf(C.cool), fontWeight: 700}));
        row.add(new Txt({...mono, text: '\u00A0=\u00A0', fill: C.muted}));
        if (r.list) row.add(new Txt({...mono, text: '[', fill: C.muted}));
        (r.parts ?? []).forEach((p, i) => {
          const t = new Txt({...mono, text: p, fill: C.ink});
          parts.push(t);
          names.push(null);
          row.add(t);
          if (r.list && i < r.parts!.length - 1) row.add(new Txt({...mono, text: ',\u00A0', fill: C.muted}));
        });
        if (r.list) row.add(new Txt({...mono, text: ']', fill: C.muted}));
      }
      this.node.add(row);
      this.rows.push({row, parts, names});
    }
  }

  public *show(d = 0.4): ThreadGenerator {
    yield* this.node.opacity(1, d);
  }
  public *hide(d = 0.3): ThreadGenerator {
    yield* this.node.opacity(0, d);
  }
  /** Reveal one row (the panel fades in with the first one). */
  public *showRow(i: number, d = 0.4): ThreadGenerator {
    const r = this.rows[i].row;
    yield* all(this.node.opacity(1, d), r.opacity(1, d, easeOutCubic));
  }
  public part(row: number, i: number): Txt {
    return this.rows[row].parts[i];
  }
  /** Tint an entry (the one being read, or one already placed). */
  public *mark(row: number, i: number, color: string = C.accent, d = 0.25): ThreadGenerator {
    const name = this.rows[row].names[i];
    const t = this.part(row, i);
    yield* all(t.fill(inkOf(color), d), name ? name.fill(inkOf(color), d) : all(), chainBump(t));
  }

  /**
   * Entry (row, i) flies from the text to `target` (any node, e.g. an edge's weight pill) and fades out over
   * the last fifth of the flight, so whatever pops at the target (a weight pill) cross-fades with it instead of
   * the two texts sitting on top of each other. It keeps its size (it never drops under the 26 px floor
   * mid-flight). The source leaves its place in the row while it travels (no double image) and comes back
   * muted, "used", when the flight lands. Pop the target at about 85% of `d`.
   * `layer` is a screen-space layer above everything (w.top).
   */
  public *fly(row: number, i: number, layer: Node, target: Node, d = 0.75, color: string = C.accent): ThreadGenerator {
    const src = this.part(row, i);
    const from = posIn(layer, src);
    const p = createSignal(0);
    const flyer = new Txt({
      text: src.text(),
      fontFamily: F.mono,
      fontWeight: 700,
      fontSize: this.fontSize,
      letterSpacing: 0.01,
      fill: inkOf(color),
      shadowColor: glow(color),
      shadowBlur: 16,
      position: () => {
        const to = posIn(layer, target);
        const k = p();
        // a gentle arc: lift towards the top while travelling
        const lift = Math.sin(Math.PI * k) * -60;
        return Vector2.lerp(from, to, k).add([0, lift]);
      },
      scale: () => 1 + 0.12 * Math.sin(Math.PI * Math.min(1, p() * 1.5)),
      opacity: () => Math.max(0, Math.min(1, (0.9 - p()) / 0.2)), // gone at 90% of the flight: no ghost on the pill
    });
    layer.add(flyer);
    src.opacity(0);
    src.fill(C.muted);
    yield* p(1, d, easeInOutCubic);
    flyer.remove();
    yield* src.opacity(1, 0.3);
  }

  /** Several entries fly one after another (stagger seconds apart), each to its own target. */
  public *flyAll(row: number, layer: Node, targets: Node[], stagger = 0.3, d = 0.7, onLand?: (i: number) => ThreadGenerator) {
    const self = this;
    yield* sequence(
      stagger,
      ...targets.map((t, i) =>
        (function* () {
          yield* self.fly(row, i, layer, t, d);
          if (onLand) yield* onLand(i);
        })(),
      ),
    );
  }
}
