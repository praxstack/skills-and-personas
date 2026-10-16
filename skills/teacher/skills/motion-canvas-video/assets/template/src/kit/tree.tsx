// Branching fan: the shape of a brute-force search (every choice spawns `branch` more), drawn level by level.
//
//   const fan = new BranchFan({position: [420, -40], branch: 3, depth: 3, width: 760, height: 460});
//   w.hud.add(fan.node);
//   yield* fan.grow(2.0, n => counter.to(n));   // levels draw in turn; the callback gets the path count
//   yield* fan.prune([1, 4]);                   // dim and cross some leaves (pruned paths)
import {Circle, Line, Node, Txt, type NodeProps} from '@motion-canvas/2d';
import {Vector2, all, delay, easeOutBack, easeOutCubic, sequence, type ThreadGenerator} from '@motion-canvas/core';
import {C, F, glow, onFill} from './theme';

export class BranchFan {
  public readonly node: Node;
  public readonly levels: Line[][] = [];
  public readonly leaves: Circle[] = [];
  public readonly root: Circle;
  private readonly b: number;
  private readonly depth: number;

  public constructor(props: NodeProps & {branch?: number; depth?: number; width?: number; height?: number; rootLabel?: string; colors?: string[]}) {
    const {branch = 3, depth = 3, width = 760, height = 460, rootLabel = '', colors = [C.muted, C.accent, C.accent2, C.bad], ...rest} = props;
    this.b = branch;
    this.depth = depth;
    this.node = new Node({...rest});
    const top = -height / 2;
    const x = (l: number, j: number) => -width / 2 + ((j + 0.5) * width) / Math.pow(branch, l);
    const y = (l: number) => top + (l * height) / depth;
    for (let l = 1; l <= depth; l++) {
      const arr: Line[] = [];
      for (let j = 0; j < Math.pow(branch, l); j++) {
        const pj = Math.floor(j / branch);
        const ln = new Line({
          points: [
            [x(l - 1, pj), y(l - 1)],
            [x(l, j), y(l)],
          ],
          stroke: colors[Math.min(colors.length - 1, l - 1)],
          lineWidth: Math.max(1.5, 5 - l * 1.1),
          lineCap: 'round',
          end: 0,
          opacity: 0,
        });
        this.node.add(ln);
        arr.push(ln);
      }
      this.levels.push(arr);
    }
    this.root = new Circle({position: [0, top], size: 60, fill: C.accent, shadowColor: glow(C.accent), shadowBlur: 24, scale: 0});
    if (rootLabel) this.root.add(new Txt({text: rootLabel, fontFamily: F.display, fontWeight: 800, fontSize: 34, fill: onFill(C.accent, C.fanInk)}));
    this.node.add(this.root);
    for (let j = 0; j < Math.pow(branch, depth); j++) {
      const c = new Circle({position: [x(depth, j), y(depth)], size: 12, fill: C.bad, scale: 0});
      this.node.add(c);
      this.leaves.push(c);
    }
  }

  /** Draw the fan level by level in `d` seconds; onLevel(paths) runs as each level lands (e.g. tick a counter). */
  public *grow(d = 2.0, onLevel?: (paths: number, level: number) => ThreadGenerator): ThreadGenerator {
    const per = d / (this.depth + 0.5);
    yield* all(
      this.root.scale(1, 0.4, easeOutBack),
      ...this.levels.map((lv, l) =>
        delay(
          0.25 + l * per,
          all(
            sequence(Math.min(0.03, (per * 0.5) / lv.length), ...lv.map(x => all(x.opacity(1, 0.05), x.end(1, per * 0.8, easeOutCubic)))),
            onLevel ? onLevel(Math.pow(this.b, l + 1), l + 1) : all(),
          ),
        ),
      ),
      delay(0.25 + this.depth * per - per * 0.3, sequence(0.008, ...this.leaves.map(c => c.scale(1, 0.25, easeOutBack)))),
    );
  }
  /** Prune leaves (illegal or dominated paths): each leaf and its last branch dim, a small cross marks it. */
  public *prune(leaves: number[], color: string = C.muted, d = 0.35): ThreadGenerator {
    const last = this.levels[this.levels.length - 1];
    yield* sequence(
      0.05,
      ...leaves.map(j => {
        const p = this.leaves[j].position();
        const s = 9;
        const cross = new Node({position: p, opacity: 0, scale: 1.8});
        for (const k of [1, -1]) cross.add(new Line({points: [[-s, -s * k], [s, s * k]], stroke: color, lineWidth: 4, lineCap: 'round'}));
        this.node.add(cross);
        return all(
          this.leaves[j].fill(color, d),
          this.leaves[j].opacity(0.35, d),
          last[j].opacity(0.25, d),
          cross.opacity(1, d * 0.6),
          cross.scale(1, d, easeOutBack),
        );
      }),
    );
  }
  public *hide(d = 0.35): ThreadGenerator {
    yield* this.node.opacity(0, d);
  }
  /** position of leaf j in the fan's coordinates */
  public leaf(j: number): Vector2 {
    return this.leaves[j].position();
  }
}
