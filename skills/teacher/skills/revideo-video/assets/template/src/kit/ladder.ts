// Complexity ladder: one rung per approach with time, space and a cost bar whose length reflects the cost.
// The interview pick is marked; worse rungs dim.
//
//   const lad = new Ladder({rungs: [
//     {name: 'Brute-force DFS', time: ['n', 'k+1'], space: 'O(k)', cost: 1, color: C.rose},
//     {name: 'Bellman-Ford, k+1 rounds', time: ['k·E'], space: 'O(n)', cost: 0.3},
//   ], y: -40});
//   st.fg.add(lad.root);
//   yield* lad.show(0); yield* lad.show(1); yield* lad.pick(1);
import {Node, Rect, Txt} from '@revideo/2d';
import {all, easeOutBack, easeOutCubic, ThreadGenerator, waitFor} from '@revideo/core';
import {C, drop, F, glow, lineOf, onOf, S, textOf} from './theme';
import {bigO, label} from './text';

export interface Rung {name: string; time: [string, string?]; space?: string; cost: number; color?: string}

export class Ladder {
  readonly root = new Node({});
  readonly rows: {root: Rect; bar: Rect; name: Txt; tag?: Rect; space: Txt}[] = [];
  readonly heads: Node;
  private barMax: number;

  constructor(readonly o: {rungs: Rung[]; x?: number; y?: number; width?: number; rowH?: number}) {
    const width = o.width ?? 1560, rowH = o.rowH ?? 92;
    this.root.position([o.x ?? 0, o.y ?? 0]);
    const n = o.rungs.length;
    const top = -((n - 1) * rowH) / 2;
    const colName = -width / 2 + 34, colTime = -width / 2 + 640, colSpace = -width / 2 + 930, colBar = -width / 2 + 1130;
    this.barMax = width / 2 - 40 - colBar;
    this.heads = new Node({y: top - rowH * 0.85, opacity: 0});
    [['APPROACH', colName], ['TIME', colTime], ['SPACE', colSpace], ['COST', colBar]].forEach(([t, x]) =>
      this.heads.add(label(t as string, {x: x as number, anchor: 'left'})));
    this.root.add(this.heads);
    o.rungs.forEach((r, i) => {
      const y = top + i * rowH;
      const row = new Rect({y, width, height: rowH - 14, radius: 14, fill: C.row, stroke: C.line, lineWidth: 2,
        opacity: 0, shadowColor: drop(0.45), shadowBlur: 20, shadowOffset: [0, 8]});
      const name = new Txt({text: r.name, fontFamily: F.text, fontWeight: 600, fontSize: 36, fill: C.ink, x: colName, offset: [-1, 0]});
      const t = bigO(r.time[0], r.time[1] ?? '', {size: 40, fill: textOf(r.color ?? C.acc), anchor: 'left'});
      t.x(colTime);
      const sp = new Txt({text: r.space ?? '', fontFamily: F.mono, fontWeight: 600, fontSize: 32, fill: C.muted, x: colSpace,
        offset: [-1, 0], letterSpacing: 0.01});
      const track = new Rect({x: colBar, width: this.barMax, height: 14, radius: 7, fill: C.track, offset: [-1, 0]});
      const bar = new Rect({x: colBar, width: 0, height: 14, radius: 7, fill: lineOf(r.color ?? C.acc), offset: [-1, 0],
        shadowColor: glow(r.color ?? C.acc), shadowBlur: 14});
      row.add(name); row.add(t); row.add(sp); row.add(track); row.add(bar);
      this.root.add(row);
      this.rows.push({root: row, bar, name, space: sp});
    });
  }

  /** Rung i slides in; its bar grows to its cost. */
  *show(i: number, d = 0.55): ThreadGenerator {
    const r = this.rows[i], rung = this.o.rungs[i];
    if (this.heads.opacity() < 0.5) yield* this.heads.opacity(1, 0.3);
    const x = r.root.x();
    r.root.x(x - 60);
    yield* all(r.root.opacity(1, d * 0.6), r.root.x(x, d, easeOutCubic), r.bar.width(this.barMax * rung.cost, d * 1.6, easeOutCubic));
  }
  /** Mark rung i as the pick: mint outline and glow, a stamp; the others turn quieter by colour (their text stays >= 7:1). */
  *pick(i: number, tag = 'INTERVIEW PICK'): ThreadGenerator {
    const r = this.rows[i];
    const stamp = new Rect({x: r.root.width() / 2 - 20, y: -r.root.height() / 2 - 4, offset: [1, 0], fill: C.mint, radius: 8,
      padding: [6, 14], layout: true, scale: 0, rotation: -3});
    stamp.add(new Txt({text: tag, fontFamily: F.mono, fontWeight: 800, fontSize: S.tiny, fill: onOf(C.mint), letterSpacing: 2}));
    r.root.add(stamp);
    r.root.shadowColor(glow(C.mint));
    yield* all(
      r.root.stroke(lineOf(C.mint), 0.3), r.root.shadowBlur(36, 0.4), r.root.scale(1.03, 0.25).to(1, 0.3),
      r.bar.fill(lineOf(C.mint), 0.3), r.bar.shadowColor(glow(C.mint), 0.3),
      stamp.scale(1, 0.45, easeOutBack),
      ...this.rows.map((x, j) => (j === i ? waitFor(0) : all(x.name.fill(C.muted, 0.4), x.bar.opacity(0.35, 0.4),
        x.root.stroke(C.line, 0.4)))),
    );
  }
}
