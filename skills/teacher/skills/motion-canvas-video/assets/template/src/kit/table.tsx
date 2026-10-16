// Table / array rows for DP state and dry runs, filling cell by cell.
//
//   const t = new Table({position: [480, 200], cols: ['0', '1', '2', '3'],
//                        rows: [{label: 'START', values: ['0', '∞', '∞', '∞']}, {label: 'ROUND 0'}, {label: 'ROUND 1'}]});
//   w.hud.add(t.node);
//   yield* t.showHeader();
//   yield* t.showRow(0);                  // cells pop in with a stagger
//   yield* t.copyRow(0, 1);               // row 1 starts as a copy of row 0 (values slide down)
//   yield* t.set(1, 1, '100', C.good);    // one cell changes: flash, bump, new value
//   yield* t.markRow(2, C.good);          // outline the final row
//
// Row labels are 30 px mono. Write plain-word labels in capitals ('NEW', 'ROUND 0'): a label with no
// ascender ('new', 'one') is only x-height tall and legibility.py measures it as about 23 px.
import {Node, Rect, Txt, type NodeProps} from '@motion-canvas/2d';
import {all, chain, delay, easeOutBack, easeOutCubic, sequence, waitFor, type ThreadGenerator} from '@motion-canvas/core';
import {C, F, S, alpha, glow, inkOf, shade, underText} from './theme';

export interface Cell {
  box: Rect;
  txt: Txt;
}
export interface TableRow {
  label: string;
  values?: string[];
}

export class Table {
  public readonly node: Node;
  public readonly cells: Cell[][] = [];
  public readonly labels: Txt[] = [];
  public readonly heads: Txt[] = [];
  private readonly cw: number;
  private readonly ch: number;

  public constructor(
    props: NodeProps & {cols: string[]; rows: TableRow[]; cellW?: number; cellH?: number; gap?: number; labelW?: number; fontSize?: number; headLabel?: string},
  ) {
    const {cols, rows, cellW = 118, cellH = 66, gap = 12, labelW = 150, fontSize = 32, headLabel = '', ...rest} = props;
    this.cw = cellW;
    this.ch = cellH;
    this.node = new Node({...rest});
    const n = cols.length;
    const totalW = labelW + n * cellW + (n - 1) * gap;
    const x0 = -totalW / 2 + labelW + cellW / 2;
    const xs = cols.map((_, j) => x0 + j * (cellW + gap));
    const rowY = (r: number) => (r + 1) * (cellH + gap) - ((rows.length + 1) * (cellH + gap)) / 2 + cellH / 2;
    const headY = rowY(-1) + cellH / 2 - 18;
    if (headLabel) {
      const hl = new Txt({position: [-totalW / 2 + labelW - 24, headY], offset: [1, 0], text: headLabel, fontFamily: F.body, fontWeight: 600, fontSize: S.small, letterSpacing: 2, fill: C.muted, opacity: 0});
      this.heads.push(hl);
      this.node.add(hl);
    }
    cols.forEach((c, j) => {
      const h = new Txt({position: [xs[j], headY], text: c, fontFamily: F.mono, fontWeight: 700, fontSize: S.small, fill: C.muted, opacity: 0, letterSpacing: 0.01});
      this.heads.push(h);
      this.node.add(h);
    });
    rows.forEach((r, i) => {
      const y = rowY(i);
      const lab = new Txt({position: [-totalW / 2 + labelW - 20, y], offset: [1, 0], text: r.label, fontFamily: F.mono, fontWeight: 700, fontSize: S.label, fill: C.muted, opacity: 0, letterSpacing: 0.01});
      this.labels.push(lab);
      this.node.add(lab);
      const row: Cell[] = [];
      cols.forEach((_, j) => {
        const v = r.values?.[j] ?? '';
        const txt = new Txt({text: v, fontFamily: F.mono, fontWeight: 700, fontSize, fill: v === '∞' ? C.muted : C.ink, letterSpacing: 0.01});
        const box = new Rect({
          position: [xs[j], y],
          width: cellW,
          height: cellH,
          radius: 12,
          fill: C.cell,
          stroke: C.border,
          lineWidth: 2,
          opacity: 0,
          scale: 0.85,
          shadowColor: shade(0.5),
          shadowBlur: 16,
          shadowOffset: [0, 6],
          children: [txt],
        });
        this.node.add(box);
        row.push({box, txt});
      });
      this.cells.push(row);
    });
  }

  public cell(r: number, c: number): Cell {
    return this.cells[r][c];
  }
  public *showHeader(d = 0.35): ThreadGenerator {
    yield* all(...this.heads.map(h => h.opacity(1, d)));
  }
  /** Cells pop in left to right. */
  public *showRow(r: number, stagger = 0.07, d = 0.38): ThreadGenerator {
    yield* all(
      this.labels[r].opacity(1, d),
      sequence(stagger, ...this.cells[r].map(c => all(c.box.opacity(1, d * 0.8), c.box.scale(1, d, easeOutBack)))),
    );
  }
  /** Row `to` appears holding row `from`'s values, sliding down from it (the "copy before you update" move). */
  public *copyRow(from: number, to: number, d = 0.55): ThreadGenerator {
    yield* all(
      this.labels[to].opacity(1, d),
      sequence(
        0.06,
        ...this.cells[to].map((c, j) => {
          const src = this.cells[from][j];
          c.txt.text(src.txt.text());
          c.txt.fill(src.txt.fill());
          const y = c.box.y();
          c.box.y(src.box.y());
          c.box.scale(1);
          return all(c.box.opacity(1, d * 0.5), c.box.y(y, d, easeOutCubic));
        }),
      ),
    );
  }
  /** Change one cell: it flashes `color`, bumps, and shows the new value. */
  public *set(r: number, c: number, value: string, color: string = C.good, d = 0.3): ThreadGenerator {
    const cell = this.cells[r][c];
    yield* all(
      cell.txt.text(value, d),
      cell.txt.fill(value === '∞' ? C.muted : C.ink, d),
      chain(
        all(cell.box.stroke(color, 0.12), cell.box.fill(underText(color, 0.24), 0.12), cell.box.scale(1.14, 0.14, easeOutCubic)),
        all(cell.box.scale(1, 0.3, easeOutCubic), delay(0.35, all(cell.box.stroke(C.border, 0.6), cell.box.fill(C.cell, 0.6)))),
      ),
    );
  }
  /** Briefly outline a cell (a read). */
  public *flash(r: number, c: number, color: string = C.cool, hold = 0.3): ThreadGenerator {
    const cell = this.cells[r][c];
    yield* chain(
      all(cell.box.stroke(color, 0.12), cell.box.fill(underText(color, 0.18), 0.12)),
      waitFor(hold),
      all(cell.box.stroke(C.border, 0.3), cell.box.fill(C.cell, 0.3)),
    );
  }
  /** Keep a cell outlined (the answer). */
  public *mark(r: number, c: number, color: string = C.good, d = 0.3): ThreadGenerator {
    const cell = this.cells[r][c];
    yield* all(cell.box.stroke(color, d), cell.box.lineWidth(4, d), cell.box.fill(underText(color, 0.2), d), cell.box.shadowColor(glow(color, 0.6), d), cell.box.shadowBlur(26, d));
  }
  /** Outline a whole row. */
  public *markRow(r: number, color: string = C.good, d = 0.3): ThreadGenerator {
    yield* all(this.labels[r].fill(inkOf(color), d), ...this.cells[r].map(c => all(c.box.stroke(color, d), c.box.lineWidth(3, d))));
  }
  public *hide(d = 0.35): ThreadGenerator {
    yield* this.node.opacity(0, d);
  }
  public get cellSize() {
    return [this.cw, this.ch];
  }
}
