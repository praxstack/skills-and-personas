// Input decoder: the raw input as text (`flights = [[0,1,100], ...]`) whose entries light up, get annotated
// (FROM / TO / PRICE) and fly into the subject, so the viewer sees the mapping from text to picture.
//
//   const dec = new Decoder({name: 'flights', items: ['[0,1,100]', '[1,2,100]'], y: -330});
//   st.fg.add(dec.root);
//   yield* dec.type();                                   // the text types in, entry by entry
//   yield* dec.annotate(0, ['FROM', 'TO', 'PRICE']);     // tick marks under the numbers of entry 0
//   yield* dec.send(st, 0, g.edge(0, 1).tag!, '100');    // entry 0 flies into the graph
import {Line, Node, Rect, Txt} from '@revideo/2d';
import {all, delay, easeOutBack, easeOutCubic, sequence, ThreadGenerator, waitFor} from '@revideo/core';
import {C, F, inkOf, lineOf, S} from './theme';
import {measure} from './text';
import {fly} from './fx';
import type {Stage} from './stage';

export class Decoder {
  readonly root = new Node({});
  readonly head: Txt;
  readonly tail: Txt;
  readonly items: {txt: Txt; bg: Rect; text: string; col: number; row: number}[] = [];
  readonly cw: number;
  readonly size: number;
  private notes: Node[] = [];

  constructor(o: {name: string; items: string[]; x?: number; y?: number; size?: number; maxWidth?: number; sep?: string}) {
    const size = (this.size = o.size ?? 36);
    this.cw = measure('0', size, F.mono, 600) + 0.01;
    this.root.position([o.x ?? 0, o.y ?? 0]);
    const sep = o.sep ?? ', ';
    const maxCols = Math.floor((o.maxWidth ?? 1640) / this.cw);
    // lay out entries on a monospace grid, wrapping between entries
    const prefix = `${o.name} = [`;
    let col = prefix.length, row = 0;
    const pos: {col: number; row: number}[] = [];
    o.items.forEach((it, i) => {
      const w = it.length + (i < o.items.length - 1 ? sep.length : 1);
      if (col + w > maxCols && i > 0) { row++; col = prefix.length; }
      pos.push({col, row});
      col += it.length + sep.length;
    });
    const rows = row + 1;
    const widest = Math.max(...pos.map((p, i) => p.col + o.items[i].length)) + 1;
    const x0 = -(widest * this.cw) / 2, lh = size * 1.55, y0 = -((rows - 1) * lh) / 2;
    const at = (c: number, r: number) => ({x: x0 + c * this.cw, y: y0 + r * lh});
    this.head = this.mk(prefix, at(0, 0), C.muted);
    o.items.forEach((it, i) => {
      const p = at(pos[i].col, pos[i].row);
      // 4 px past the brackets' cells: the bracket ink has its own side bearing, and the next ',' or ']' starts right after
      const bg = new Rect({x: p.x + (it.length * this.cw) / 2, y: p.y, width: it.length * this.cw + 8, height: size * 1.4,
        radius: 8, fill: C.accSoft, stroke: lineOf(C.acc), lineWidth: 2, opacity: 0});
      this.root.add(bg);
      const txt = this.mk(it, p, C.ink);
      if (i < o.items.length - 1) {
        const s = this.mk(sep.trimEnd(), {x: p.x + it.length * this.cw, y: p.y}, C.muted);
        s.opacity(0);
        (txt as any).__sep = s;
      }
      this.items.push({txt, bg, text: it, col: pos[i].col, row: pos[i].row});
    });
    const last = pos[pos.length - 1];
    const tailAt = at(last.col + o.items[o.items.length - 1].length, last.row);
    // 8 px of air so the last entry's mark box does not touch the closing bracket
    this.tail = this.mk(']', {x: tailAt.x + 8, y: tailAt.y}, C.muted);
    this.head.opacity(0);
    this.tail.opacity(0);
    this.items.forEach(it => it.txt.opacity(0));
  }

  private mk(text: string, p: {x: number; y: number}, fill: string) {
    const t = new Txt({text, fontFamily: F.mono, fontWeight: 600, fontSize: this.size, fill, offset: [-1, 0], x: p.x, y: p.y, letterSpacing: 0.01});
    this.root.add(t);
    return t;
  }

  /** Type the text in, entry by entry. */
  *type(stagger = 0.1, d = 0.3): ThreadGenerator {
    yield* this.head.opacity(1, 0.25);
    yield* sequence(stagger, ...this.items.map(it => all(
      it.txt.opacity(1, d), (function* () { const y = it.txt.y(); it.txt.y(y + 14); yield* it.txt.y(y, d, easeOutCubic); })(),
      (it.txt as any).__sep ? (it.txt as any).__sep.opacity(1, d) : waitFor(0),
    )));
    yield* this.tail.opacity(1, 0.2);
  }
  showAll() {
    this.head.opacity(1);
    this.tail.opacity(1);
    this.items.forEach(it => { it.txt.opacity(1); (it.txt as any).__sep?.opacity(1); });
  }
  /** Highlight entry i (others step back to 0.6 opacity: 6:1, still readable context). */
  *mark(i: number, color = C.acc, d = 0.3): ThreadGenerator {
    const it = this.items[i];
    it.bg.stroke(lineOf(color)).fill(color === C.acc ? C.accSoft : C.mintSoft);
    yield* all(...this.items.map((x, j) => all(x.txt.opacity(j === i ? 1 : 0.6, d), x.bg.opacity(j === i ? 1 : 0, d),
      x.txt.fill(j === i ? inkOf(color) : C.ink, d))));
  }
  *unmark(d = 0.3): ThreadGenerator {
    yield* all(...this.items.map(x => all(x.bg.opacity(0, d), x.txt.opacity(1, d), x.txt.fill(C.ink, d))));
  }
  /**
   * Tick marks + labels under each number of entry i (e.g. FROM / TO / PRICE). Numbers sit a few characters
   * apart, so a label that would touch its left neighbour drops to a second row (a longer tick reaches it).
   */
  *annotate(i: number, labels: string[], color = C.acc, stagger = 0.18): ThreadGenerator {
    const it = this.items[i];
    const nums = [...it.text.matchAll(/-?\d+|∞/g)];
    const group = new Node({});
    this.root.add(group);
    this.notes.push(group);
    const size = S.tiny, rowH = size * 1.3, gapX = 18;
    const rowEnd: number[] = [];
    const marks = nums.slice(0, labels.length).map((m, j) => {
      const cx = it.txt.x() + (m.index! + m[0].length / 2) * this.cw;
      const w = measure(labels[j], size, F.mono, 800) + labels[j].length * 2;
      let row = 0;
      while (rowEnd[row] !== undefined && cx - w / 2 < rowEnd[row] + gapX) row++;
      rowEnd[row] = cx + w / 2;
      const ly = this.size * 2.1 + row * rowH;
      const n = new Node({x: cx, y: it.txt.y(), opacity: 0});
      n.add(new Line({points: [[0, this.size * 0.75], [0, ly - size * 0.62]], stroke: lineOf(color), lineWidth: 3}));
      n.add(new Txt({text: labels[j], fontFamily: F.mono, fontWeight: 800, fontSize: size, fill: inkOf(color), y: ly, letterSpacing: 2}));
      group.add(n);
      return n;
    });
    yield* sequence(stagger, ...marks.map(n => all(n.opacity(1, 0.25), (function* () { n.y(n.y() - 12); yield* n.y(n.y() + 12, 0.35, easeOutBack); })())));
  }
  *clearNotes(d = 0.25): ThreadGenerator {
    yield* all(...this.notes.map(n => n.opacity(0, d)));
    this.notes.forEach(n => n.remove());
    this.notes = [];
  }
  /** The Txt of entry i (a source for fly()). */
  itemNode(i: number) {
    return this.items[i].txt;
  }
  /** Entry i flies into the subject (to a node such as an edge's weight tag). */
  *send(st: Stage, i: number, to: Node, text?: string, color = C.acc, d = 0.8): ThreadGenerator {
    const it = this.items[i];
    const from = st.screenPos(it.bg);
    yield* fly(st, text ?? it.text, from, to, {color, d, size: this.size * 0.9, toSize: S.small});
  }
}

export {delay};
