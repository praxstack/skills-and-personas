// Array rows and small tables for DP state and dry runs, filling cell by cell.
//
//   const dist = new ArrayRow({label: 'dist', values: ['0', '∞', '∞', '∞'], y: 120});
//   st.fg.add(dist.root);
//   yield* dist.in();
//   yield* dist.set(1, '100');                  // flip + flash, mint by default
//   const next = new ArrayRow({label: 'next', values: ['', '', '', ''], y: 240});
//   yield* next.copyFrom(dist);                 // values travel down from dist (read old, write new)
import {Node, Rect, Txt} from '@revideo/2d';
import {all, delay, easeInCubic, easeInOutCubic, easeOutBack, easeOutCubic, sequence, ThreadGenerator, Vector2, waitFor} from '@revideo/core';
import {C, drop, F, glow, lineOf, S, textOf} from './theme';

export class ArrayRow {
  readonly root: Node;
  readonly cells: Rect[] = [];
  readonly txts: Txt[] = [];
  readonly idx: Txt[] = [];
  readonly head?: Txt;
  readonly cell: number;
  readonly xs: number[] = [];

  constructor(o: {label?: string; values: string[]; x?: number; y?: number; cell?: number; gap?: number; index?: boolean;
    labelColor?: string; size?: number}) {
    const cw = (this.cell = o.cell ?? 104), gap = o.gap ?? 12;
    this.root = new Node({x: o.x ?? 0, y: o.y ?? 0});
    const total = o.values.length * cw + (o.values.length - 1) * gap;
    o.values.forEach((v, i) => {
      const x = -total / 2 + cw / 2 + i * (cw + gap);
      this.xs.push(x);
      const c = new Rect({x, width: cw, height: cw * 0.8, radius: 12, fill: C.cell, stroke: C.line, lineWidth: 2,
        scale: 0, opacity: 0, shadowColor: drop(0.45), shadowBlur: 16, shadowOffset: [0, 6]});
      const t = new Txt({text: v, fontFamily: F.mono, fontWeight: 700, fontSize: o.size ?? Math.max(S.small, cw * 0.34),
        fill: v === '∞' ? C.muted : C.ink, letterSpacing: 0.01});
      c.add(t);
      if (o.index !== false) {
        const it = new Txt({text: String(i), fontFamily: F.mono, fontWeight: 600, fontSize: S.tiny, fill: C.muted, x, y: -cw * 0.66, opacity: 0});
        this.root.add(it);
        this.idx.push(it);
      }
      this.root.add(c);
      this.cells.push(c);
      this.txts.push(t);
    });
    if (o.label) {
      this.head = new Txt({text: o.label, fontFamily: F.mono, fontWeight: 700, fontSize: S.small, fill: o.labelColor ?? C.muted,
        offset: [1, 0], x: -total / 2 - 24, opacity: 0, letterSpacing: 0.01});
      this.root.add(this.head);
    }
  }

  *in(stagger = 0.07): ThreadGenerator {
    yield* all(
      this.head ? this.head.opacity(1, 0.3) : waitFor(0),
      sequence(stagger, ...this.cells.map((c, i) => all(c.opacity(1, 0.2), c.scale(1, 0.4, easeOutBack),
        this.idx[i] ? this.idx[i].opacity(1, 0.3) : waitFor(0)))),
    );
  }
  *out(d = 0.3): ThreadGenerator {
    yield* this.root.opacity(0, d);
  }
  /** Change cell i to v with a flip and a coloured flash. */
  *set(i: number, v: string, color = C.mint): ThreadGenerator {
    const t = this.txts[i], c = this.cells[i];
    yield* t.scale(0, 0.12, easeInCubic);
    t.text(v).fill(v === '∞' ? C.muted : textOf(color));
    c.shadowColor(glow(color));
    yield* all(t.scale(1, 0.32, easeOutBack), c.stroke(lineOf(color), 0.12).wait(0.6).to(C.line, 0.5),
      c.shadowBlur(26, 0.12).wait(0.6).to(16, 0.5), c.scale(1.08, 0.12).to(1, 0.25));
  }
  /** Outline cell i (on) or clear it (off). */
  *mark(i: number, color = C.acc, on = true, d = 0.25): ThreadGenerator {
    yield* this.cells[i].stroke(on ? lineOf(color) : C.line, d);
  }
  /** Cell centre in the row's parent coordinates. */
  cellPos(i: number) {
    return new Vector2(this.root.x() + this.xs[i], this.root.y());
  }
  /** Every value of `other` travels into this row (same parent), then lands. */
  *copyFrom(other: ArrayRow, d = 0.6, stagger = 0.06): ThreadGenerator {
    const parent = this.root.parent()!;
    yield* sequence(stagger, ...other.txts.map((src, i) => (function* (self: ArrayRow) {
      const ghost = new Txt({text: src.text(), fontFamily: F.mono, fontWeight: 700, fontSize: src.fontSize(), fill: textOf(C.sky),
        position: other.cellPos(i), letterSpacing: 0.01});
      parent.add(ghost);
      yield* ghost.position(self.cellPos(i), d, easeInOutCubic);
      ghost.remove();
      self.txts[i].text(src.text()).fill(src.text() === '∞' ? C.muted : C.ink);
      yield* self.cells[i].stroke(lineOf(C.sky), 0.1).to(C.line, 0.4);
    })(this)));
  }
}

/** A stack of labelled rows (rounds of a DP, steps of a dry run). */
export class Table {
  readonly root = new Node({});
  readonly rows: ArrayRow[] = [];
  constructor(readonly o: {x?: number; y?: number; cell?: number; rowGap?: number; index?: boolean} = {}) {
    this.root.position([o.x ?? 0, o.y ?? 0]);
  }
  addRow(label: string, values: string[], labelColor?: string) {
    const cell = this.o.cell ?? 96;
    const r = new ArrayRow({label, values, cell, y: this.rows.length * (cell * 0.8 + (this.o.rowGap ?? 22)),
      index: this.rows.length === 0 && this.o.index !== false, labelColor});
    this.root.add(r.root);
    this.rows.push(r);
    return r;
  }
}

export {delay, easeOutCubic};
