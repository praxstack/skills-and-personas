// The persistent subject: a directed weighted graph laid out from data.
//
//   const g = new Graph({nodes: [{id: 0, x: -300, y: 0}, ...], edges: [{from: 0, to: 1, w: 100}, ...]});
//   w.world.add(g.root);
//   yield* g.popNodes();                       // nodes pop in (they start hidden)
//   yield* g.drawEdge(0, 1);                   // arrow draws, weight pill pops (edges start hidden)
//   yield* g.highlightNode(0, C.cool);         // ring + glow
//   const r = g.route([0, 1, 3], C.good);      // a glowing path over the edges with a travelling token
//   yield* r.fly(1.8);                          //   token flies the path, the trail draws behind it
//   yield* g.fire(1, 3, C.accent);             // a pulse runs along an edge (a relaxation, a message)
//   yield* g.setValue(3, '700', C.good);       // value badge next to a node (dist, cost)
//   const t = g.tag(0, 'src', C.cool); yield* t.show();
//
// Undrawn edges stay at opacity 0 (Motion Canvas draws arrowheads and round caps even at end = 0).
import {Circle, Gradient, Line, Node, QuadBezier, Rect, Txt, type Curve} from '@motion-canvas/2d';
import {
  Vector2,
  all,
  chain,
  createSignal,
  delay,
  easeInOutCubic,
  easeOutBack,
  easeOutCubic,
  linear,
  sequence,
  waitFor,
  type ThreadGenerator,
} from '@motion-canvas/core';
import {C, F, alpha, glow, inkOf, lift, shade} from './theme';
import {background} from './clock';
import {Chip, bump, ripple} from './fx';

export type NodeId = number | string;
export interface GraphNodeSpec {
  id: NodeId;
  x: number;
  y: number;
  label?: string;
  /** where value badges go: 'left' | 'right' | 'top' | 'bottom' (default: away from the graph centre) */
  valueSide?: 'left' | 'right' | 'top' | 'bottom';
}
export interface GraphEdgeSpec {
  from: NodeId;
  to: NodeId;
  w?: number | string;
  /** sideways bend in px (use for two-way pairs or edges that would cross a node); 0 = straight */
  bend?: number;
  /** which side of the edge the weight pill sits on: 1 or -1 (default: away from the graph centre) */
  pillSide?: 1 | -1;
}
export interface GraphOptions {
  nodes: GraphNodeSpec[];
  edges: GraphEdgeSpec[];
  radius?: number;
  directed?: boolean;
  /**
   * Font sizes of the small print in world px (weight pills, value badges, tags). The camera scales them:
   * on screen they are fontSize x zoom, which must stay >= 28 px (the bar's floor is 26). The defaults hold
   * down to zoom 0.8 (tags down to 0.85); below that (a corner thumbnail) hide them with labels(false).
   */
  pillFont?: number;
  valueFont?: number;
  tagFont?: number;
}

export interface GNode {
  spec: GraphNodeSpec;
  group: Node;
  circle: Circle;
  halo: Circle;
  label: Txt;
  value: Txt;
}
export interface GEdge {
  spec: GraphEdgeSpec;
  key: string;
  curve: Curve;
  pill: Rect;
  pillTxt: Txt;
  drawn: boolean;
}

const PLANE = [
  [24, 0], [9, -4], [-2, -20], [-9, -20], [-3, -4], [-15, -4], [-20, -11],
  [-25, -11], [-21, 0], [-25, 11], [-20, 11], [-15, 4], [-3, 4], [-9, 20],
  [-2, 20], [9, 4],
].map(([x, y]) => new Vector2(x, y));

export class Graph {
  public readonly root = new Node({});
  public readonly edgeLayer = new Node({});
  public readonly routeLayer = new Node({});
  public readonly pillLayer = new Node({});
  public readonly nodeLayer = new Node({});
  public readonly fxLayer = new Node({});
  public readonly tokenLayer = new Node({});
  public readonly R: number;
  public readonly nodes = new Map<string, GNode>();
  public readonly edges: GEdge[] = [];
  private readonly directed: boolean;
  private readonly mid: Vector2;
  private readonly pillFont: number;
  private readonly valueFont: number;
  public readonly tagFont: number;

  public constructor(o: GraphOptions) {
    this.R = o.radius ?? 58;
    this.directed = o.directed ?? true;
    this.pillFont = o.pillFont ?? 40; // 40 (was 36): a pill caught mid-pop still reads >= 26 px
    this.valueFont = o.valueFont ?? 38;
    this.tagFont = o.tagFont ?? 42; // lowercase-only tags ('src') measure at x-height: 42 x 0.86 zoom reads as 27 px
    this.root.add([this.edgeLayer, this.routeLayer, this.pillLayer, this.nodeLayer, this.fxLayer, this.tokenLayer]);
    const xs = o.nodes.map(n => n.x);
    const ys = o.nodes.map(n => n.y);
    this.mid = new Vector2((Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2);
    for (const n of o.nodes) this.addNode(n);
    for (const e of o.edges) this.addEdge(e);
  }

  // ------------------------------------------------------------------ construction
  private addNode(spec: GraphNodeSpec) {
    const R = this.R;
    const p = new Vector2(spec.x, spec.y);
    const halo = new Circle({size: 2 * R + 34, fill: alpha(C.accent, 0.16), opacity: 0, shadowBlur: 50, shadowColor: glow(C.accent)});
    const circle = new Circle({
      size: 2 * R,
      fill: new Gradient({
        type: 'radial',
        from: [-R * 0.35, -R * 0.45],
        to: [-R * 0.35, -R * 0.45],
        fromRadius: 0,
        toRadius: R * 1.9,
        stops: [
          {offset: 0, color: C.nodeHi},
          {offset: 1, color: C.nodeLo},
        ],
      }),
      stroke: C.stroke,
      lineWidth: 3,
      shadowColor: shade(0.65),
      shadowBlur: 28,
      shadowOffset: [0, 12],
    });
    const label = new Txt({text: spec.label ?? String(spec.id), fontFamily: F.display, fontWeight: 800, fontSize: R * 0.95, fill: C.ink});
    const side = spec.valueSide ?? this.awaySide(p);
    const vf = this.valueFont;
    const off = {left: [-R - 2 * vf, 0], right: [R + 2 * vf, 0], top: [0, -R - 1.2 * vf], bottom: [0, R + 1.25 * vf]}[side];
    const value = new Txt({
      position: off as [number, number],
      text: '',
      fontFamily: F.mono,
      fontWeight: 700,
      fontSize: vf,
      fill: C.muted,
      letterSpacing: 0.01,
      opacity: 0,
    });
    const group = new Node({position: p, scale: 0, children: [halo, circle, label, value]});
    this.nodeLayer.add(group);
    this.nodes.set(String(spec.id), {spec, group, circle, halo, label, value});
  }

  private awaySide(p: Vector2): 'left' | 'right' | 'top' | 'bottom' {
    const d = p.sub(this.mid);
    if (Math.abs(d.x) >= Math.abs(d.y)) return d.x < 0 ? 'left' : 'right';
    return d.y < 0 ? 'top' : 'bottom';
  }

  /** geometry of an edge: trimmed endpoints, control point and the pill position */
  private geometry(e: GraphEdgeSpec) {
    const a = this.pos(e.from);
    const b = this.pos(e.to);
    const dir = b.sub(a).normalized;
    let n = new Vector2(-dir.y, dir.x);
    const bend = e.bend ?? 0;
    const mid = a.add(b).scale(0.5);
    const ctrl = mid.add(n.scale(bend));
    const startDir = ctrl.sub(a).normalized;
    const endDir = b.sub(ctrl).normalized;
    const p0 = a.add(startDir.scale(this.R + 8));
    const p2 = b.sub(endDir.scale(this.R + 12));
    // pill: off the curve's midpoint, on the side away from the graph centre (or the bend side)
    const curveMid = bend ? a.scale(0.25).add(ctrl.scale(0.5)).add(b.scale(0.25)) : mid;
    let side = e.pillSide ?? (bend ? Math.sign(bend) : n.dot(mid.sub(this.mid)) >= 0 ? 1 : -1);
    if (side === 0) side = 1;
    const pill = curveMid.add(n.scale(side * (this.pillFont + 4)));
    return {p0, ctrl, p2, pill, bend};
  }

  private makeCurve(e: GraphEdgeSpec, props: Record<string, unknown>): Curve {
    const g = this.geometry(e);
    if (g.bend) return new QuadBezier({p0: g.p0, p1: g.ctrl, p2: g.p2, ...props});
    return new Line({points: [g.p0, g.p2], ...props});
  }

  private addEdge(spec: GraphEdgeSpec) {
    const curve = this.makeCurve(spec, {
      stroke: C.edge,
      lineWidth: 4,
      endArrow: this.directed,
      arrowSize: 16,
      lineCap: 'round',
      end: 0,
      opacity: 0,
    });
    this.edgeLayer.add(curve);
    const g = this.geometry(spec);
    const pillTxt = new Txt({text: spec.w === undefined ? '' : String(spec.w), fontFamily: F.mono, fontWeight: 700, fontSize: this.pillFont, fill: C.ink, letterSpacing: 0.01});
    const pill = new Rect({
      position: g.pill,
      layout: true,
      padding: [8, 16], // room between the digits and a highlighted (coloured) border
      radius: 12,
      fill: C.pill,
      stroke: C.stroke,
      lineWidth: 2,
      scale: 0,
      shadowColor: shade(0.5),
      shadowBlur: 14,
      shadowOffset: [0, 5],
      children: [pillTxt],
    });
    if (spec.w === undefined) pill.opacity(0);
    this.pillLayer.add(pill);
    this.edges.push({spec, key: `${spec.from}-${spec.to}`, curve, pill, pillTxt, drawn: false});
  }

  // ------------------------------------------------------------------ lookups
  public node(id: NodeId): GNode {
    const n = this.nodes.get(String(id));
    if (!n) throw new Error(`graph has no node ${id}`);
    return n;
  }
  public edge(from: NodeId, to: NodeId): GEdge {
    const e = this.edges.find(x => String(x.spec.from) === String(from) && String(x.spec.to) === String(to));
    if (!e) throw new Error(`graph has no edge ${from} -> ${to}`);
    return e;
  }
  /** position of a node in the graph's coordinates */
  public pos(id: NodeId): Vector2 {
    const n = this.nodes.get(String(id));
    if (!n) throw new Error(`graph has no node ${id}`);
    return new Vector2(n.spec.x, n.spec.y);
  }
  /** centre of the node layout (graph coordinates; the graph root is usually at the world origin) */
  public center(): Vector2 {
    return this.mid.add(this.root.position());
  }
  /** a point along edge from->to at fraction p, in graph coordinates */
  public along(from: NodeId, to: NodeId, p = 0.5): Vector2 {
    return this.edge(from, to).curve.getPointAtPercentage(p).position;
  }

  // ------------------------------------------------------------------ build-in
  public *popNode(id: NodeId, d = 0.5): ThreadGenerator {
    yield* this.node(id).group.scale(1, d, easeOutBack);
  }
  public *popNodes(stagger = 0.12, d = 0.5): ThreadGenerator {
    yield* sequence(stagger, ...[...this.nodes.values()].map(n => n.group.scale(1, d, easeOutBack)));
  }
  /** Draw an edge's arrow (it becomes visible as it starts drawing) and pop its weight pill. */
  public *drawEdge(from: NodeId, to: NodeId, d = 0.6): ThreadGenerator {
    const e = this.edge(from, to);
    e.drawn = true;
    e.curve.opacity(1);
    yield* all(e.curve.end(1, d, easeInOutCubic), delay(d * 0.55, e.pill.scale(1, 0.4, easeOutBack)));
  }
  public *drawEdges(stagger = 0.25, d = 0.6): ThreadGenerator {
    yield* sequence(stagger, ...this.edges.map(e => this.drawEdge(e.spec.from, e.spec.to, d)));
  }
  /** Show everything at once (for a film that starts mid-way, or a chapter that rebuilds the subject). */
  public showAll() {
    for (const n of this.nodes.values()) n.group.scale(1);
    for (const e of this.edges) {
      e.drawn = true;
      e.curve.opacity(1);
      e.curve.end(1);
      e.pill.scale(1);
    }
  }

  /**
   * Show or hide the small print (weight pills and value badges). Hide it when the graph is shown small
   * (a corner thumbnail below zoom 0.8), where the labels would fall under the 26 px minimum on screen.
   */
  public *labels(on: boolean, d = 0.3): ThreadGenerator {
    yield* all(
      ...this.edges.map(e => e.pill.opacity(on && e.spec.w !== undefined ? 1 : 0, d)),
      ...[...this.nodes.values()].map(n => n.value.opacity(on && n.value.text() ? 1 : 0, d)),
    );
  }

  // ------------------------------------------------------------------ state
  public *highlightNode(id: NodeId, color: string = C.accent, d = 0.35): ThreadGenerator {
    const n = this.node(id);
    n.halo.fill(alpha(color, 0.16));
    n.halo.shadowColor(glow(color));
    yield* all(n.circle.stroke(color, d), n.circle.lineWidth(5, d), n.halo.opacity(1, d), n.label.fill(inkOf(color), d));
  }
  public *resetNode(id: NodeId, d = 0.35): ThreadGenerator {
    const n = this.node(id);
    yield* all(n.circle.stroke(C.stroke, d), n.circle.lineWidth(3, d), n.halo.opacity(0, d), n.label.fill(C.ink, d));
  }
  /**
   * Dim every node and edge except the given nodes (and the edges between them). Shapes fade to `dimTo`;
   * their labels and weights turn muted instead of fading, so they stay readable (4.5:1).
   */
  public *focusOn(ids: NodeId[], d = 0.4, dimTo = 0.28): ThreadGenerator {
    const keep = new Set(ids.map(String));
    yield* all(
      ...[...this.nodes.values()].map(n => {
        const k = keep.has(String(n.spec.id));
        return all(n.circle.opacity(k ? 1 : dimTo, d), n.halo.opacity(k ? n.halo.opacity() : 0, d), n.label.fill(k ? C.ink : C.muted, d));
      }),
      ...this.edges.map(e => {
        const k = keep.has(String(e.spec.from)) && keep.has(String(e.spec.to));
        return all(e.curve.opacity(e.drawn ? (k ? 1 : dimTo) : 0, d), e.pillTxt.fill(k ? C.ink : C.muted, d), e.pill.stroke(k ? C.stroke : C.hair, d));
      }),
    );
  }
  public *unfocus(d = 0.4): ThreadGenerator {
    yield* all(
      ...[...this.nodes.values()].map(n => all(n.circle.opacity(1, d), n.label.fill(C.ink, d))),
      ...this.edges.map(e => all(e.curve.opacity(e.drawn ? 1 : 0, d), e.pillTxt.fill(C.ink, d), e.pill.stroke(C.stroke, d))),
    );
  }
  public *highlightEdge(from: NodeId, to: NodeId, color: string = C.accent, d = 0.3): ThreadGenerator {
    const e = this.edge(from, to);
    // the weight takes a lighter tint of the colour: the orange and rose sit near 4.5:1 once the glow is behind them
    const ink = lift(color, 0.35);
    yield* all(
      e.curve.stroke(color, d),
      e.curve.lineWidth(7, d),
      e.curve.shadowColor(glow(color), d),
      e.curve.shadowBlur(18, d),
      e.pill.stroke(color, d),
      e.pillTxt.fill(ink, d),
    );
  }
  public *resetEdge(from: NodeId, to: NodeId, d = 0.4): ThreadGenerator {
    const e = this.edge(from, to);
    yield* all(
      e.curve.stroke(C.edge, d),
      e.curve.lineWidth(4, d),
      e.curve.shadowBlur(0, d),
      e.pill.stroke(C.stroke, d),
      e.pillTxt.fill(C.ink, d),
    );
  }
  public *resetAll(d = 0.4): ThreadGenerator {
    yield* all(
      ...this.edges.map(e => this.resetEdge(e.spec.from, e.spec.to, d)),
      ...[...this.nodes.keys()].map(k => this.resetNode(k, d)),
    );
  }

  /** Value badge next to a node (dist, cost). Pass '' to hide it. */
  public *setValue(id: NodeId, text: string, color: string = C.ink, d = 0.3): ThreadGenerator {
    const v = this.node(id).value;
    if (!text) {
      yield* v.opacity(0, d);
      return;
    }
    const first = v.opacity() < 0.5;
    if (first) v.text(text);
    yield* all(v.opacity(1, d), first ? waitFor(0) : v.text(text, d), v.fill(inkOf(color), d), bump(v, 1.3, 0.45));
  }

  /** A chip pinned to a node: g.tag(0, 'src', C.cool, 'top'). Call .show() / .hide() / .set(). */
  public tag(id: NodeId, text: string, color: string = C.accent, side: 'top' | 'bottom' | 'left' | 'right' = 'top'): Chip {
    const R = this.R;
    const p = this.pos(id);
    const tf = this.tagFont;
    const off = {top: [0, -R - 1.25 * tf], bottom: [0, R + 1.25 * tf], left: [-R - 2.2 * tf, 0], right: [R + 2.2 * tf, 0]}[side];
    const chip = new Chip(text, color, {position: p.add(off as [number, number]), fontSize: tf});
    this.tokenLayer.add(chip.node);
    return chip;
  }

  // ------------------------------------------------------------------ motion
  /** An expanding ring on a node. */
  public *ripple(id: NodeId, color: string = C.accent): ThreadGenerator {
    yield* ripple(this.fxLayer, this.pos(id), color, 2 * this.R);
  }

  /** A pulse of light runs along an edge (a relaxation firing, a message sent); the target node ripples. */
  public *fire(from: NodeId, to: NodeId, color: string = C.accent, d = 0.55, rippleTarget = true): ThreadGenerator {
    const e = this.edge(from, to);
    const p = createSignal(0);
    const comet = this.makeCurve(e.spec, {
      stroke: color,
      lineWidth: 10,
      lineCap: 'round',
      shadowColor: glow(color),
      shadowBlur: 22,
      start: () => Math.max(0, p() - 0.32),
      end: () => Math.min(1, p()),
      opacity: () => (p() <= 0.001 || p() >= 1.3 ? 0 : 1),
    });
    this.routeLayer.add(comet);
    if (rippleTarget) background(delay(d * 0.85, this.ripple(to, color)));
    background(delay(d * 0.8, bump(e.pill, 1.18, 0.3)));
    yield* all(p(1.32, d, linear), chain(waitFor(d * 0.15), this.highlightEdge(from, to, color, 0.15)));
    comet.remove();
  }

  /** A glowing path over the edges with a travelling token (plane). */
  public route(path: NodeId[], color: string = C.good, token: 'plane' | 'dot' | 'none' = 'plane'): Route {
    return new Route(this, path, color, token);
  }

  /** Internal: a curve that follows an edge (used by routes and pulses). */
  public trace(from: NodeId, to: NodeId, props: Record<string, unknown>) {
    return this.makeCurve(this.edge(from, to).spec, props);
  }
  public static readonly PLANE = PLANE;
}

/** A path on the graph: a glowing trail per edge and a token that flies it. Created by graph.route(). */
export class Route {
  public readonly segments: Curve[] = [];
  public readonly token: Node;
  public readonly color: string;
  private readonly progress = createSignal(0); // 0..segments
  private readonly marks: Node[] = []; // crosses and labels added by reject()
  public constructor(
    private readonly g: Graph,
    public readonly path: NodeId[],
    color: string,
    tokenKind: 'plane' | 'dot' | 'none',
  ) {
    this.color = color;
    for (let i = 0; i + 1 < path.length; i++) {
      const k = i;
      const seg = g.trace(path[i], path[i + 1], {
        stroke: color,
        lineWidth: 9,
        lineCap: 'round',
        shadowColor: glow(color),
        shadowBlur: 24,
        end: () => Math.max(0, Math.min(1, this.progress() - k)),
        opacity: () => (this.progress() > k ? 1 : 0),
      });
      g.routeLayer.add(seg);
      this.segments.push(seg);
    }
    const where = () => {
      const p = this.progress();
      const i = Math.max(0, Math.min(this.segments.length - 1, Math.floor(p)));
      const f = Math.max(0.001, Math.min(0.999, p - i));
      return this.segments[i].getPointAtPercentage(f);
    };
    if (tokenKind === 'plane') {
      this.token = new Line({points: PLANE, closed: true, fill: C.ink, stroke: color, lineWidth: 2, shadowColor: glow(color), shadowBlur: 22, scale: 1.25});
    } else if (tokenKind === 'dot') {
      this.token = new Circle({size: 26, fill: C.ink, shadowColor: glow(color), shadowBlur: 22});
    } else {
      this.token = new Node({});
    }
    this.token.position(() => where().position);
    this.token.rotation(() => where().tangent.degrees);
    this.token.opacity(0);
    g.tokenLayer.add(this.token);
  }

  /**
   * Fly the whole path in `d` seconds. `onArrive(i)` runs (in parallel) when the token reaches path[i]
   * (i >= 1): tick a counter there, ripple the node, pop a "+100".
   */
  public *fly(d = 1.8, onArrive?: (i: number) => ThreadGenerator, keepToken = false): ThreadGenerator {
    const n = this.segments.length;
    background(this.token.opacity(1, 0.15));
    const per = d / n;
    const hops: ThreadGenerator[] = [];
    for (let i = 0; i < n; i++) {
      hops.push(this.progress(i + 1, per, i === 0 ? easeOutCubic : easeInOutCubic));
    }
    // arrivals and the final ripple run on (spawned) after the token lands, so fly() takes exactly ~d seconds
    if (onArrive) for (let i = 0; i < n; i++) background(delay(per * (i + 1) - 0.05, onArrive(i + 1)));
    background(delay(d - per * 0.3, this.g.ripple(this.path[n], this.color)));
    yield* chain(...hops);
    if (!keepToken) background(this.token.opacity(0, 0.25));
  }
  /** Show the full trail instantly (no flight). */
  public showAll() {
    this.progress(this.segments.length);
  }
  public *recolor(color: string, d = 0.35): ThreadGenerator {
    yield* all(...this.segments.map(s => all(s.stroke(color, d), s.shadowColor(glow(color), d))));
  }
  public *dim(to = 0.25, d = 0.35): ThreadGenerator {
    yield* all(...this.segments.map(s => s.lineWidth(to < 0.5 ? 5 : 9, d)), this.fadeTo(to, d));
  }
  private *fadeTo(o: number, d: number): ThreadGenerator {
    const p = this.progress();
    yield* all(...this.segments.map((s, k) => s.opacity(p > k ? o : 0, d)));
    // keep the opacity function semantics for later flights
    this.segments.forEach((s, k) => s.opacity(() => (this.progress() > k ? o : 0)));
  }
  /**
   * Reject this path (too many stops, over budget): the trail turns red and a cross slams onto path[at]
   * (default: the last stop) with an optional label under it. fade() removes the cross too.
   *   const bad = g.route([0, 1, 2, 3], C.accent); yield* bad.fly(1.6); yield* bad.reject(2, '2 stops > k');
   */
  public *reject(at = this.path.length - 1, label?: string, d = 0.45): ThreadGenerator {
    const p = this.g.pos(this.path[at]);
    const s = this.g.R * 0.62;
    const cross = new Node({position: p, scale: 1.9, opacity: 0, rotation: -14});
    for (const k of [1, -1]) {
      cross.add(new Line({points: [[-s, -s * k], [s, s * k]], stroke: C.bad, lineWidth: 15, lineCap: 'round', shadowColor: glow(C.bad), shadowBlur: 18}));
    }
    this.g.tokenLayer.add(cross);
    this.marks.push(cross);
    const chip = label ? new Chip(label, C.bad, {position: p.add([0, this.g.R + 1.4 * this.g.tagFont]), fontSize: this.g.tagFont}) : null;
    if (chip) {
      this.g.tokenLayer.add(chip.node);
      this.marks.push(chip.node);
    }
    yield* all(
      this.recolor(C.bad, d * 0.6),
      cross.opacity(1, d * 0.4),
      cross.scale(1, d, easeOutBack),
      cross.rotation(0, d, easeOutBack),
      chip ? delay(d * 0.5, chip.show()) : waitFor(0),
    );
  }
  public *fade(d = 0.4): ThreadGenerator {
    yield* all(this.fadeTo(0, d), this.token.opacity(0, d), ...this.marks.map(m => m.opacity(0, d)));
    this.segments.forEach(s => s.remove());
    this.marks.forEach(m => m.remove());
    this.token.remove();
  }
}
