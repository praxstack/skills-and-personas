// Complexity ladder: one rung per approach, a bar whose length shows its cost, O(...) chips, the pick marked.
//
//   const lad = new Ladder({position: [120, -20], width: 1300, rungs: [
//     {name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1.0},
//     {name: 'DFS + memo', time: 'O(k·E)', space: 'O(n·k)', cost: 0.45},
//     {name: 'Bellman-Ford, k + 1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.4}]});
//   w.hud.add(lad.node);
//   yield* lad.show(0);          // a rung slides in, its cost bar grows
//   yield* lad.pick(2);          // the interview pick glows, the others recede
import {Gradient, Layout, Line, Node, Rect, Txt, type NodeProps} from '@motion-canvas/2d';
import {all, delay, easeOutBack, easeOutCubic, type ThreadGenerator} from '@motion-canvas/core';
import {C, F, S, alpha, glow, inkOf} from './theme';
import {Chip} from './fx';
import {panel} from './cards';

export interface Rung {
  name: string;
  time: string;
  space: string;
  /** 0..1: relative cost (bar length); 1 = the slowest */
  cost: number;
  note?: string;
}

export class Ladder {
  public readonly node: Node;
  public readonly rows: {card: Rect; bar: Rect; barMax: number; chips: Rect[]}[] = [];
  private readonly star: Chip;
  private readonly rail: Line;
  private readonly railLabel: Txt;

  public constructor(props: NodeProps & {rungs: Rung[]; width?: number; rungH?: number; gap?: number}) {
    const {rungs, width = 1540, rungH = 116, gap = 30, ...rest} = props;
    this.node = new Node({...rest});
    const totalH = rungs.length * rungH + (rungs.length - 1) * gap;
    const y = (i: number) => -totalH / 2 + rungH / 2 + i * (rungH + gap);
    // the rail on the left: cheaper as you go down
    this.rail = new Line({
      points: [
        [-width / 2 - 40, y(0) - rungH / 2],
        [-width / 2 - 40, y(rungs.length - 1) + rungH / 2],
      ],
      stroke: railGradient(totalH),
      lineWidth: 6,
      lineCap: 'round',
      endArrow: true,
      arrowSize: 16,
      end: 0,
      opacity: 0,
    });
    this.node.add(this.rail);
    // hidden until the first rung shows (with the rail), so nothing of the ladder sits under a chapter card
    this.railLabel = new Txt({text: 'FASTER', rotation: -90, position: [-width / 2 - 78, 0], fontFamily: F.body, fontWeight: 700, fontSize: S.small, letterSpacing: 6, fill: C.muted, opacity: 0});
    this.node.add(this.railLabel);
    const barMaxW = 170;
    rungs.forEach((r, i) => {
      const costColor = r.cost > 0.75 ? C.bad : r.cost > 0.45 ? C.accent : C.good;
      const bar = new Rect({width: 0, height: 14, radius: 7, fill: costColor, shadowColor: glow(costColor, 0.6), shadowBlur: 14});
      const chipT = new Rect({
        layout: true,
        padding: [8, 16],
        radius: 12,
        fill: alpha(C.ink, 0.04),
        stroke: C.stroke,
        lineWidth: 2,
        children: [
          new Txt({fontFamily: F.mono, fontSize: S.label, fill: C.muted, letterSpacing: 0.01, text: 'time\u00A0'}),
          new Txt({fontFamily: F.mono, fontWeight: 700, fontSize: S.label, fill: inkOf(costColor), letterSpacing: 0.01, text: r.time}),
        ],
      });
      const chipS = new Rect({
        layout: true,
        padding: [8, 16],
        radius: 12,
        fill: alpha(C.ink, 0.04),
        stroke: C.stroke,
        lineWidth: 2,
        children: [
          new Txt({fontFamily: F.mono, fontSize: S.label, fill: C.muted, letterSpacing: 0.01, text: 'space\u00A0'}),
          new Txt({fontFamily: F.mono, fontWeight: 700, fontSize: S.label, fill: C.ink, letterSpacing: 0.01, text: r.space}),
        ],
      });
      const card = panel({
        position: [0, y(i)],
        width,
        height: rungH,
        radius: 20,
        layout: true,
        direction: 'row',
        alignItems: 'center',
        gap: 24,
        padding: [0, 28],
        opacity: 0,
        children: [
          new Rect({
            width: 56,
            height: 56,
            radius: 28,
            fill: C.cell,
            stroke: C.stroke,
            lineWidth: 2,
            layout: true,
            justifyContent: 'center',
            alignItems: 'center',
            children: [new Txt({text: String(i + 1), fontFamily: F.display, fontWeight: 800, fontSize: S.label, fill: C.ink})],
          }),
          new Layout({
            direction: 'column',
            gap: 6,
            grow: 1,
            children: [
              new Txt({text: r.name, fontFamily: F.display, fontWeight: 700, fontSize: 38, fill: C.ink}),
              ...(r.note ? [new Txt({text: r.note, fontFamily: F.body, fontSize: S.small, fill: C.muted})] : []),
            ],
          }),
          new Layout({width: barMaxW, height: 14, alignItems: 'center', children: [bar]}),
          new Layout({direction: 'row', gap: 12, children: [chipT, chipS]}),
        ],
      });
      this.node.add(card);
      this.rows.push({card, bar, barMax: barMaxW * Math.max(0.06, Math.min(1, r.cost)), chips: [chipT, chipS]});
    });
    this.star = new Chip('★  INTERVIEW PICK', C.gold, {fontSize: S.small});
    this.node.add(this.star.node);
  }

  /** Rung i slides in from the right and its cost bar grows. */
  public *show(i: number, d = 0.55): ThreadGenerator {
    const r = this.rows[i];
    const x = r.card.x();
    r.card.x(x + 120);
    yield* all(
      this.rail.opacity(1, 0.3),
      this.railLabel.opacity(1, 0.3),
      this.rail.end(Math.max(this.rail.end(), (i + 1) / this.rows.length), d + 0.3, easeOutCubic),
      r.card.opacity(1, d * 0.8),
      r.card.x(x, d, easeOutCubic),
      delay(d * 0.5, r.bar.width(r.barMax, 0.7, easeOutCubic)),
      r.card.stroke(C.accent, 0.2),
    );
    yield* r.card.stroke(C.border, 0.6);
  }
  /** Mark rung i as the pick: gold outline and glow, a star chip; the others' cost bars recede (their text stays readable). */
  public *pick(i: number, label = '★  INTERVIEW PICK', d = 0.5): ThreadGenerator {
    const r = this.rows[i];
    this.star.txt.text(label);
    // a solid tab on the (slightly scaled-up) card's edge, so the gold outline never runs through it: under the
    // last rung (nothing below it but the caption gap), above any other rung
    const below = i === this.rows.length - 1 && this.rows.length > 1;
    this.star.node.fill(C.panelHi);
    this.star.node.position(() => {
      const off = (r.card.height() * r.card.scale().y) / 2 + this.star.node.height() / 2 - 2;
      return [r.card.x() + r.card.width() / 2 - this.star.node.width() / 2 - 24, r.card.y() + (below ? off : -off)];
    });
    yield* all(
      r.card.stroke(C.gold, d),
      r.card.lineWidth(3, d),
      r.card.shadowColor(glow(C.gold, 0.45), d),
      r.card.shadowBlur(50, d),
      r.card.scale(1.03, d, easeOutBack),
      delay(0.15, this.star.show()),
      ...this.rows.filter((_, k) => k !== i).map(o => all(o.bar.opacity(0.35, d), o.card.stroke(C.hair, d))),
    );
  }
  public *hide(d = 0.35): ThreadGenerator {
    yield* this.node.opacity(0, d);
  }
}

/** The rail's vertical gradient (slow at the top, fast at the bottom). */
function railGradient(h: number) {
  return new Gradient({
    from: [0, -h / 2],
    to: [0, h / 2],
    stops: [
      {offset: 0, color: C.bad},
      {offset: 0.5, color: C.accent},
      {offset: 1, color: C.good},
    ],
  });
}
