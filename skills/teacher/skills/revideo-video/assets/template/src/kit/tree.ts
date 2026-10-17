// Recursion fan: the brute-force picture. A tree that branches `branch` ways per level, growing level by
// level so the viewer sees the work explode. Deeper levels turn the accent colour.
//
//   const fan = new Fan({levels: 5, branch: 3, width: 1000, step: 90, y: -300});
//   st.world.add(fan.root);
//   yield* fan.grow(0.3);                       // levels appear one after another
//   yield* fan.ringRepeats(3, [1, 4, 7], C.mint);  // circle repeated sub-problems on level 3
import {Circle, Line, Node} from '@revideo/2d';
import {all, easeOutCubic, sequence, ThreadGenerator, Vector2} from '@revideo/core';
import {C, glow, lineOf} from './theme';

export class Fan {
  readonly root = new Node({});
  readonly levels: Node[][] = []; // per level: [its edges, its dots]
  readonly points: Vector2[][] = [];
  constructor(o: {levels?: number; branch?: number; width?: number; step?: number; x?: number; y?: number; hot?: number}) {
    const levels = o.levels ?? 5, br = o.branch ?? 3, span = o.width ?? 1000, step = o.step ?? 90, hot = o.hot ?? 2;
    this.root.position([o.x ?? 0, o.y ?? 0]);
    const edges = new Node({}), dots = new Node({}); // dots above every edge, so no line crosses a node
    this.root.add(edges);
    this.root.add(dots);
    let prev = [new Vector2(0, 0)];
    for (let d = 0; d < levels; d++) {
      const E = new Node({opacity: 0}), D = new Node({opacity: 0});
      const cur: Vector2[] = [];
      if (d === 0) {
        D.add(new Circle({position: prev[0], size: 26, fill: C.ink, shadowColor: glow(C.ink), shadowBlur: 14}));
        cur.push(prev[0]);
      } else {
        const count = Math.pow(br, d), sp = span / count;
        for (let i = 0; i < count; i++) {
          const p = new Vector2(-span / 2 + sp / 2 + i * sp, d * step);
          const par = prev[Math.floor(i / br)];
          const isHot = d > hot;
          E.add(new Line({points: [par, p], stroke: isHot ? lineOf(C.acc) : C.edge, lineWidth: d > 3 ? 1.4 : 2.4, opacity: d > 3 ? 0.65 : 0.95}));
          D.add(new Circle({position: p, size: Math.max(7, 22 - d * 3.6), fill: isHot ? lineOf(C.acc) : C.ink,
            ...(isHot ? {shadowColor: glow(C.acc), shadowBlur: 10} : {})}));
          cur.push(p);
        }
      }
      edges.add(E);
      dots.add(D);
      this.levels.push([E, D]);
      this.points.push(cur);
      prev = cur;
    }
  }
  *grow(stagger = 0.3, d = 0.3): ThreadGenerator {
    yield* sequence(stagger, ...this.levels.map(([E, D]) => all(
      E.opacity(1, d), D.opacity(1, d),
      (function* () { E.y(-10); D.y(-10); yield* all(E.y(0, d, easeOutCubic), D.y(0, d, easeOutCubic)); })(),
    )));
  }
  /** Rings around some nodes of a level (the same sub-problem solved again and again). */
  *ringRepeats(level: number, idx: number[], color = C.mint): ThreadGenerator {
    const rings = idx.map(i => new Circle({position: this.points[level][i], size: 10, stroke: lineOf(color), lineWidth: 3, opacity: 0}));
    rings.forEach(r => this.root.add(r));
    yield* sequence(0.1, ...rings.map(r => all(r.opacity(1, 0.2), r.size(40, 0.45, easeOutCubic))));
  }
}
