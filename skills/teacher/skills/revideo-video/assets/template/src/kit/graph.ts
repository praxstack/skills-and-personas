// The persistent subject: a directed weighted graph laid out from data. It is built once, lives in the
// world for the whole film, and every chapter acts on it (routes light up, edges fire, chips show values).
//
//   const g = new Graph({nodes: [{id: 0, x: -420, y: 0}, ...], edges: [{u: 0, v: 1, w: 100}, ...]});
//   st.world.add(g.root);
//   yield* g.popNodes();                       // nodes pop in (stagger)
//   yield* g.drawEdge(0, 1);                   // edge draws from 0 to 1, weight tag pops at the end
//   yield* g.travel([0, 1, 3], C.acc);         // a glowing token flies the route, edges light behind it
//   yield* g.fire(1, 3, C.mint);               // a pulse runs along one edge (a relaxation "fires")
//   yield* g.reject([0, 1, 2, 3], '2 STOPS');  // an illegal route: drawn in rose, shaken, crossed out
//   const d = g.chip(3); yield* d.in(); yield* d.set('700', C.mint);   // a value under a node
import {Circle, Gradient, Line, Node, QuadBezier, Rect, Txt} from '@revideo/2d';
import {
  all, createSignal, delay, easeInCubic, easeInOutCubic, easeOutBack, easeOutCubic, linear, sequence,
  SimpleSignal, ThreadGenerator, tween, Vector2, waitFor,
} from '@revideo/core';
import {C, drop, F, glow, hot, lineOf, onOf, S, textOf} from './theme';
import {clock, onFrame} from './time';

export type Id = string | number;
export interface GraphSpec {
  nodes: {id: Id; x: number; y: number; label?: string}[];
  edges: {u: Id; v: Id; w?: number | string; bend?: number; tagSide?: 1 | -1}[];
  radius?: number;
  directed?: boolean;
}

export interface GNode {
  id: Id; pos: Vector2; group: Node; disc: Circle; halo: Circle; ring: Circle; label: Txt;
}
export interface GEdge {
  key: string; u: Id; v: Id; w?: number | string; p0: Vector2; p1: Vector2; p2: Vector2;
  base: QuadBezier; hi: QuadBezier; pulse: QuadBezier; tag?: Rect; tagTxt?: Txt; tagHold?: Node;
  fade: SimpleSignal<number, void>; pulseAt: SimpleSignal<number, void>;
}

// Weight tags, badges, chips and notes hang in holder nodes. A holder sits at an anchor point (a node, an edge's
// middle) plus an offset, and both its scale and its offset grow by `f = 1 / scale` when the graph is placed
// smaller than 1, so the text keeps its design size on screen (30-32 px) instead of shrinking with the map.
interface Holder {hold: Node; base: Vector2; off: Vector2}

const k = (u: Id, v: Id) => `${u}-${v}`;

export class Graph {
  readonly root = new Node({});
  readonly edgeLayer = new Node({});
  readonly tagLayer = new Node({});
  readonly nodeLayer = new Node({});
  readonly fxLayer = new Node({});
  readonly nodes = new Map<string, GNode>();
  readonly edges = new Map<string, GEdge>();
  readonly token: Circle;
  readonly R: number;
  private center: Vector2;
  private attachments: Holder[] = [];
  private tagHolders: Holder[] = [];
  /** Attachment scale (see Holder). */
  private f = 1;

  constructor(readonly spec: GraphSpec) {
    this.R = spec.radius ?? 54;
    this.root.add(this.edgeLayer);
    this.root.add(this.tagLayer);
    this.root.add(this.nodeLayer);
    this.root.add(this.fxLayer);
    const xs = spec.nodes.map(n => n.x), ys = spec.nodes.map(n => n.y);
    this.center = new Vector2((Math.min(...xs) + Math.max(...xs)) / 2, (Math.min(...ys) + Math.max(...ys)) / 2);
    for (const e of spec.edges) this.makeEdge(e);
    for (const n of spec.nodes) this.makeNode(n);
    this.token = new Circle({size: 30, fill: lineOf(C.acc), opacity: 0, shadowColor: glow(C.acc), shadowBlur: 34});
    this.token.add(new Circle({size: 12, fill: C.tokenCore}));
    this.fxLayer.add(this.token);
  }

  // ------------------------------------------------------------ construction
  private makeNode(n: GraphSpec['nodes'][number]) {
    const R = this.R;
    const pos = new Vector2(n.x, n.y);
    const group = new Node({position: pos});
    const ring = new Circle({size: 2 * R + 46, stroke: lineOf(C.acc), lineWidth: 3, lineDash: [12, 10], opacity: 0});
    ring.rotation(() => clock() * 24);
    const halo = new Circle({size: 2 * R + 20, stroke: lineOf(C.acc), lineWidth: 5, opacity: 0, shadowColor: glow(C.acc), shadowBlur: 28});
    const disc = new Circle({
      size: 2 * R, stroke: C.ink, lineWidth: 3, scale: 0, opacity: 0,
      fill: new Gradient({type: 'linear', from: [0, -R], to: [0, R], stops: [{offset: 0, color: C.discTop}, {offset: 1, color: C.discBottom}]}),
      shadowColor: drop(0.65), shadowBlur: 30, shadowOffset: [0, 12],
    });
    const label = new Txt({text: n.label ?? String(n.id), fontFamily: F.display, fontWeight: 700, fontSize: R * 0.86, fill: C.ink});
    disc.add(label);
    group.add(ring);
    group.add(halo);
    group.add(disc);
    this.nodeLayer.add(group);
    this.nodes.set(String(n.id), {id: n.id, pos, group, disc, halo, ring, label});
  }

  private makeEdge(e: GraphSpec['edges'][number]) {
    const R = this.R;
    const A = this.posOf(e.u), B = this.posOf(e.v);
    const mid = A.add(B).scale(0.5);
    const dir = B.sub(A).normalized;
    const nrm = new Vector2(-dir.y, dir.x);
    const ctrl = mid.add(nrm.scale(e.bend ?? 0));
    const p0 = A.add(ctrl.sub(A).normalized.scale(R + 8));
    const p2 = B.sub(B.sub(ctrl).normalized.scale(R + 10));
    const p1 = ctrl;
    const directed = this.spec.directed !== false;
    const base = new QuadBezier({p0, p1, p2, stroke: C.edge, lineWidth: 4, end: 0, endArrow: directed, arrowSize: 16});
    base.opacity(() => (base.end() > 0.002 ? 1 : 0));
    const fade = createSignal(1);
    const hi = new QuadBezier({p0, p1, p2, stroke: lineOf(C.acc), lineWidth: 8, end: 0, endArrow: directed, arrowSize: 22,
      lineCap: 'round', shadowColor: glow(C.acc), shadowBlur: 22});
    hi.opacity(() => (hi.end() > 0.002 ? fade() : 0));
    const pulseAt = createSignal(-1);
    const pulse = new QuadBezier({p0, p1, p2, stroke: hot(C.acc), lineWidth: 7, lineCap: 'round', shadowColor: glow(C.acc), shadowBlur: 26});
    pulse.start(() => Math.max(0, Math.min(1, pulseAt() - 0.22)));
    pulse.end(() => Math.max(0, Math.min(1, pulseAt())));
    pulse.opacity(() => (pulseAt() > 0 && pulseAt() < 1.22 ? 1 : 0));
    this.edgeLayer.add(base);
    this.edgeLayer.add(hi);
    this.edgeLayer.add(pulse);
    const edge: GEdge = {key: k(e.u, e.v), u: e.u, v: e.v, w: e.w, p0, p1, p2, base, hi, pulse, fade, pulseAt};
    if (e.w !== undefined) {
      const m = p0.scale(0.25).add(p1.scale(0.5)).add(p2.scale(0.25));
      let side = new Vector2(-dir.y, dir.x);
      if (e.tagSide) side = side.scale(e.tagSide);
      else if (side.dot(m.sub(this.center)) < 0) side = side.scale(-1);
      // the tag's centre sits its own half-extent (towards the edge) plus a gap away from the line, so a wide tag
      // beside a vertical edge does not touch it (a fixed 42 px did)
      const halfW = (String(e.w).length * 0.6 * S.small) / 2 + 15, halfH = (S.small * 1.2 + 14) / 2;
      const dist = Math.abs(side.x) * halfW + Math.abs(side.y) * halfH + 8;
      const hold = this.holder(this.tagLayer, m, side.scale(dist), this.tagHolders);
      const tag = new Rect({
        fill: C.tag, stroke: C.line, lineWidth: 2, radius: 12,
        layout: true, padding: [7, 14], alignItems: 'center', justifyContent: 'center', scale: 0, opacity: 0,
        shadowColor: drop(0.5), shadowBlur: 14, shadowOffset: [0, 6],
      });
      const tagTxt = new Txt({text: String(e.w), fontFamily: F.mono, fontWeight: 600, fontSize: S.small, fill: C.ink, letterSpacing: 0.01});
      tag.add(tagTxt);
      hold.add(tag);
      edge.tag = tag;
      edge.tagTxt = tagTxt;
      edge.tagHold = hold;
    }
    this.edges.set(edge.key, edge);
  }

  // ------------------------------------------------------------ lookups
  node(id: Id): GNode {
    const n = this.nodes.get(String(id));
    if (!n) throw new Error(`graph: no node ${id}`);
    return n;
  }
  edge(u: Id, v: Id): GEdge {
    const e = this.edges.get(k(u, v));
    if (!e) throw new Error(`graph: no edge ${u} -> ${v}`);
    return e;
  }
  posOf(id: Id): Vector2 {
    const n = this.spec.nodes.find(x => String(x.id) === String(id));
    if (!n) throw new Error(`graph: no node ${id}`);
    return new Vector2(n.x, n.y);
  }
  /** Point along an edge (0..1), in graph coordinates. */
  pointOn(u: Id, v: Id, t: number): Vector2 {
    return this.edge(u, v).base.getPointAtPercentage(t).position;
  }

  private holder(parent: Node, base: Vector2, off: Vector2, list: Holder[]) {
    const hold = new Node({position: base.add(off.scale(this.f)), scale: this.f});
    parent.add(hold);
    list.push({hold, base, off});
    return hold;
  }

  /**
   * Move/scale the whole graph (d = 0: instantly). Node labels grow to stay at least `minPx` on screen, and
   * weight tags, badges and chips keep their design size (30-32 px) when the graph is shown small (see Holder).
   */
  *place(x: number, y: number, scale = 1, d = 0, minPx = 30): ThreadGenerator {
    const lab = Math.max(this.R * 0.86, minPx / scale);
    const f = (this.f = Math.max(1, 1 / scale));
    const holders = [...this.tagHolders, ...this.attachments];
    if (d <= 0) {
      this.root.position([x, y]);
      this.root.scale(scale);
      for (const n of this.nodes.values()) n.label.fontSize(lab);
      for (const h of holders) { h.hold.scale(f); h.hold.position(h.base.add(h.off.scale(f))); }
      return;
    }
    yield* all(
      this.root.position([x, y], d, easeInOutCubic), this.root.scale(scale, d, easeInOutCubic),
      ...[...this.nodes.values()].map(n => n.label.fontSize(lab, d, easeInOutCubic)),
      ...holders.map(h => all(h.hold.scale(f, d, easeInOutCubic), h.hold.position(h.base.add(h.off.scale(f)), d, easeInOutCubic))),
    );
  }
  /** Show or hide every weight tag at once: hide them on a small decorative thumbnail where the numbers say nothing. */
  showTags(on = true) {
    for (const h of this.tagHolders) h.hold.opacity(on ? 1 : 0);
  }

  // ------------------------------------------------------------ build-up
  *popNode(id: Id, d = 0.5): ThreadGenerator {
    const n = this.node(id);
    yield* all(n.disc.opacity(1, d * 0.5), n.disc.scale(1, d, easeOutBack));
  }
  *popNodes(ids?: Id[], stagger = 0.14): ThreadGenerator {
    const list = ids ?? this.spec.nodes.map(n => n.id);
    yield* sequence(stagger, ...list.map(id => this.popNode(id)));
  }
  *drawEdge(u: Id, v: Id, d = 0.6, tag = true): ThreadGenerator {
    const e = this.edge(u, v);
    yield* all(e.base.end(1, d, easeInOutCubic), tag ? delay(d * 0.7, this.showTag(u, v)) : waitFor(0));
  }
  *drawEdges(list?: [Id, Id][], stagger = 0.22, d = 0.6): ThreadGenerator {
    const l = list ?? [...this.edges.values()].map(e => [e.u, e.v] as [Id, Id]);
    yield* sequence(stagger, ...l.map(([u, v]) => this.drawEdge(u, v, d)));
  }
  *showTag(u: Id, v: Id, d = 0.4): ThreadGenerator {
    const t = this.edge(u, v).tag;
    if (t) yield* all(t.opacity(1, d * 0.5), t.scale(1, d, easeOutBack));
  }
  /** Everything at once (or staggered): for a cut into a chapter where the graph is already known. */
  showAll() {
    for (const n of this.nodes.values()) { n.disc.opacity(1); n.disc.scale(1); }
    for (const e of this.edges.values()) { e.base.end(1); e.tag?.opacity(1); e.tag?.scale(1); }
  }

  // ------------------------------------------------------------ emphasis
  /** Node state: idle | active (accent glow) | good (mint) | bad (rose) | dim. */
  *state(id: Id, s: 'idle' | 'active' | 'good' | 'bad' | 'dim', d = 0.35): ThreadGenerator {
    const n = this.node(id);
    const col = s === 'active' ? C.acc : s === 'good' ? C.mint : s === 'bad' ? C.rose : C.ink;
    const on = s === 'active' || s === 'good' || s === 'bad';
    if (on) n.halo.stroke(lineOf(col)).shadowColor(glow(col));
    yield* all(
      n.disc.stroke(s === 'dim' ? C.dim : lineOf(col), d),
      n.label.fill(s === 'dim' ? C.muted : on ? textOf(col) : C.ink, d),
      n.halo.opacity(on ? 1 : 0, d),
      n.group.opacity(s === 'dim' ? 0.45 : 1, d),
      on ? n.group.scale(1.1, d * 0.5, easeOutCubic).to(1, d * 0.8) : waitFor(0),
    );
  }
  /** Slowly rotating dashed ring around a node (e.g. "this is a stop"). */
  *ring(id: Id, color = C.acc, on = true, d = 0.4): ThreadGenerator {
    const n = this.node(id);
    if (on) { n.ring.stroke(lineOf(color)); n.ring.scale(1.25); }
    yield* all(n.ring.opacity(on ? 1 : 0, d), on ? n.ring.scale(1, d, easeOutCubic) : waitFor(0));
  }
  /** Expanding ring that fades: an arrival, a relaxation landing. */
  *ripple(id: Id, color = C.acc, d = 0.7): ThreadGenerator {
    const n = this.node(id);
    const r = new Circle({position: n.pos, size: this.R * 2, stroke: lineOf(color), lineWidth: 5, opacity: 0.9});
    this.fxLayer.add(r);
    yield* all(r.size(this.R * 2 + 90, d, easeOutCubic), r.opacity(0, d, easeInCubic), r.lineWidth(1, d));
    r.remove();
  }
  /** Draw an edge's highlight in `color` (re-colours it if it is already drawn). */
  *light(u: Id, v: Id, color = C.acc, d = 0.5): ThreadGenerator {
    const e = this.edge(u, v);
    e.fade(1);
    if (e.hi.end() > 0.99) {
      yield* all(e.hi.stroke(lineOf(color), d), e.hi.shadowColor(glow(color), d), e.tag ? e.tag.stroke(lineOf(color), d) : waitFor(0));
      return;
    }
    e.hi.stroke(lineOf(color)).shadowColor(glow(color));
    yield* all(e.hi.end(1, d, easeInOutCubic), e.tag ? e.tag.stroke(lineOf(color), d) : waitFor(0));
  }
  *unlight(u: Id, v: Id, d = 0.3): ThreadGenerator {
    const e = this.edge(u, v);
    yield* all(e.fade(0, d), e.tag ? e.tag.stroke(C.line, d) : waitFor(0));
    e.hi.end(0);
    e.fade(1);
  }
  /** A pulse runs along the edge (a relaxation fires); the target node ripples when it lands. */
  *fire(u: Id, v: Id, color = C.acc, d = 0.55): ThreadGenerator {
    const e = this.edge(u, v);
    e.pulse.stroke(hot(color)).shadowColor(glow(color));
    e.pulseAt(0);
    yield* all(
      e.pulseAt(1.22, d, easeInOutCubic),
      e.tag ? e.tag.stroke(lineOf(color), d * 0.4).wait(d * 0.4).to(C.line, d * 0.6) : waitFor(0),
      delay(d * 0.8, this.ripple(v, color, 0.6)),
    );
    e.pulseAt(-1);
  }
  /** A glowing token flies the route; edges light behind it. onHop(i) runs as it lands on path[i]. */
  *travel(path: Id[], color = C.acc, perEdge = 0.6, onHop?: (i: number) => ThreadGenerator): ThreadGenerator {
    const tk = this.token;
    tk.fill(lineOf(color)).shadowColor(glow(color));
    tk.position(this.posOf(path[0]));
    tk.scale(0.4);
    yield* all(tk.opacity(1, 0.15), tk.scale(1, 0.25, easeOutBack));
    for (let i = 0; i + 1 < path.length; i++) {
      const e = this.edge(path[i], path[i + 1]);
      e.fade(1);
      e.hi.stroke(lineOf(color)).shadowColor(glow(color));
      yield* all(
        e.hi.end(1, perEdge, easeInOutCubic),
        tween(perEdge, t => tk.position(e.base.getPointAtPercentage(easeInOutCubic(t)).position)),
        e.tag ? e.tag.stroke(lineOf(color), perEdge) : waitFor(0),
      );
      tk.position(this.posOf(path[i + 1]));
      const last = i + 2 === path.length;
      yield* all(
        this.node(path[i + 1]).group.scale(1.12, 0.1).to(1, 0.2),
        this.ripple(path[i + 1], color, 0.5),
        onHop ? onHop(i + 1) : waitFor(0),
        last ? all(tk.opacity(0, 0.2), tk.scale(0.3, 0.2)) : waitFor(0), // never park on the node's label
      );
    }
  }
  /**
   * An illegal route: drawn in rose, shaken, crossed out, faded; edges lit before it get their colour back.
   * The note (`why`) sits beside the crossed edge, or above node `noteAbove` (like a badge) when the space beside
   * the edge is taken by tags or nodes.
   */
  *reject(path: Id[], why = '', color = C.rose, hold = 0.6, noteAbove?: Id): ThreadGenerator {
    const es = path.slice(0, -1).map((u, i) => this.edge(u, path[i + 1]));
    const before = es.map(e => ({end: e.hi.end(), stroke: e.hi.stroke(), shadow: e.hi.shadowColor()}));
    for (const e of es) {
      e.fade(1);
      e.hi.end(0);
      e.hi.stroke(lineOf(color)).shadowColor(glow(color));
    }
    yield* sequence(0.18, ...path.slice(0, -1).map((u, i) => this.edge(u, path[i + 1]).hi.end(1, 0.35, easeInOutCubic)));
    // the cross sits a fifth of the way along the middle edge, clear of its weight tag (at the half)
    const mid = this.pointOn(path[Math.floor((path.length - 1) / 2)], path[Math.floor((path.length - 1) / 2) + 1], 0.22);
    const cross = new Node({position: mid, rotation: -6});
    const a = new Line({points: [[-38, -38], [38, 38]], stroke: lineOf(color), lineWidth: 12, lineCap: 'round', end: 0, shadowColor: glow(color), shadowBlur: 20});
    const b = new Line({points: [[38, -38], [-38, 38]], stroke: lineOf(color), lineWidth: 12, lineCap: 'round', end: 0, shadowColor: glow(color), shadowBlur: 20});
    cross.add(a);
    cross.add(b);
    let note: Rect | null = null, noteHold: Node | null = null;
    if (why) {
      // the note sits beside the edge (perpendicular, away from the graph's centre), clear of tags and nodes
      const ea = this.posOf(path[Math.floor((path.length - 1) / 2)]), eb = this.posOf(path[Math.floor((path.length - 1) / 2) + 1]);
      const d = eb.sub(ea).normalized, perp = new Vector2(-d.y, d.x);
      const ns = [...this.nodes.values()], cx = ns.reduce((a, n) => a + n.pos.x, 0) / ns.length, cy = ns.reduce((a, n) => a + n.pos.y, 0) / ns.length;
      const away = perp.dot(mid.sub([cx, cy])) < 0 ? -1 : 1;
      const [base, off] = noteAbove !== undefined
        ? [this.node(noteAbove).pos.add([0, -this.R]), new Vector2(0, -50)]
        : [mid, perp.scale(away * 130)];
      noteHold = new Node({position: base.add(off.scale(this.f)), scale: this.f});
      note = new Rect({fill: color, radius: 8, padding: [7, 14], layout: true, scale: 0});
      note.add(new Txt({text: why, fontFamily: F.mono, fontWeight: 800, fontSize: S.small, fill: onOf(color), letterSpacing: 1}));
      noteHold.add(note);
      this.fxLayer.add(noteHold);
    }
    this.fxLayer.add(cross);
    yield* all(
      shake(this.root, 16, 0.45),
      a.end(1, 0.2, easeOutCubic),
      delay(0.12, b.end(1, 0.2, easeOutCubic)),
      note ? delay(0.2, note.scale(1, 0.35, easeOutBack)) : waitFor(0),
    );
    yield* waitFor(hold);
    yield* all(cross.opacity(0, 0.4), note ? note.opacity(0, 0.4) : waitFor(0), ...es.map(e => e.fade(0, 0.5)));
    cross.remove();
    noteHold?.remove();
    es.forEach((e, i) => { e.hi.end(before[i].end).stroke(before[i].stroke).shadowColor(before[i].shadow); });
    es.forEach((e, i) => { if (before[i].end <= 0) e.fade(1); });
    yield* all(...es.filter((_, i) => before[i].end > 0).map(e => e.fade(1, 0.3)));
  }
  /** Clear every highlight, ring and node state instantly (while a chapter card covers the frame). */
  reset() {
    for (const e of this.edges.values()) { e.hi.end(0); e.fade(1); e.pulseAt(-1); e.tag?.stroke(C.line); }
    for (const n of this.nodes.values()) {
      n.halo.opacity(0); n.ring.opacity(0); n.disc.stroke(C.ink); n.label.fill(C.ink); n.group.opacity(1); n.group.scale(1);
    }
    this.token.opacity(0);
  }
  /** Clear every highlight, ring and node state. */
  *clear(d = 0.35): ThreadGenerator {
    yield* all(
      ...[...this.edges.values()].map(e => all(e.fade(0, d), e.tag ? e.tag.stroke(C.line, d) : waitFor(0))),
      ...[...this.nodes.values()].map(n => all(n.halo.opacity(0, d), n.ring.opacity(0, d), n.disc.stroke(C.ink, d),
        n.label.fill(C.ink, d), n.group.opacity(1, d))),
    );
    for (const e of this.edges.values()) { e.hi.end(0); e.fade(1); }
  }

  // ------------------------------------------------------------ attachments
  /** A pill above (or below) a node: SRC, DST, STOP... */
  badge(id: Id, text: string, color = C.acc, side: 'top' | 'bottom' | 'left' | 'right' = 'top') {
    const n = this.node(id), R = this.R;
    // anchored on the disc's rim; the gap and the pill's own half-size grow with the holder (see Holder)
    const [anchor, off] = {
      top: [[0, -R], [0, -50]], bottom: [[0, R], [0, 50]], left: [[-R, 0], [-80, 0]], right: [[R, 0], [80, 0]],
    }[side] as [[number, number], [number, number]];
    const hold = this.holder(this.fxLayer, n.pos.add(anchor), new Vector2(off), this.attachments);
    const r = new Rect({fill: color, radius: 8, padding: [6, 12], layout: true,
      scale: 0, opacity: 0, shadowColor: drop(0.5), shadowBlur: 12, shadowOffset: [0, 4]});
    const t = new Txt({text, fontFamily: F.mono, fontWeight: 800, fontSize: S.tiny, fill: onOf(color), letterSpacing: 1.5});
    r.add(t);
    hold.add(r);
    return {
      root: r, txt: t,
      *in(): ThreadGenerator { yield* all(r.opacity(1, 0.2), r.scale(1, 0.4, easeOutBack)); },
      *out(): ThreadGenerator { yield* all(r.opacity(0, 0.2), r.scale(0.6, 0.25)); },
    };
  }
  /**
   * A pill beside the middle of an edge ("FLIGHT 1", "ROUND 0"): `off` px towards the graph's centre (default 46),
   * or, negative, to the outer side beyond the weight tag (-134 leaves a clear gap above a weight tag): use that when the inner side is crowded.
   */
  edgeBadge(u: Id, v: Id, text: string, color = C.acc, along = 0.5, off = 0) {
    const e = this.edge(u, v);
    const p = this.pointOn(u, v, along);
    const dir = e.p2.sub(e.p0).normalized;
    let side = new Vector2(-dir.y, dir.x);
    if (side.dot(p.sub(this.center)) < 0) side = side.scale(-1);
    const hold = this.holder(this.fxLayer, p, side.scale(-(off || 46)), this.attachments);
    const r = new Rect({fill: color, radius: 8, padding: [5, 10], layout: true,
      scale: 0, opacity: 0, shadowColor: drop(0.5), shadowBlur: 12});
    r.add(new Txt({text, fontFamily: F.mono, fontWeight: 800, fontSize: S.tiny, fill: onOf(color), letterSpacing: 1}));
    hold.add(r);
    return {
      root: r,
      *in(): ThreadGenerator { yield* all(r.opacity(1, 0.2), r.scale(1, 0.4, easeOutBack)); },
      *out(): ThreadGenerator { yield* all(r.opacity(0, 0.2), r.scale(0.6, 0.25)); },
    };
  }
  /** Remove every badge, edge badge and chip (instantly): use while a chapter card covers the frame. */
  removeAttachments() {
    this.attachments.forEach(a => a.hold.remove());
    this.attachments = [];
  }
  /** A value chip under a node (dist values in a dry run). set() flips the value with a flash. */
  chip(id: Id, value = '∞', side: 'bottom' | 'top' = 'bottom') {
    const n = this.node(id), dir = side === 'bottom' ? 1 : -1;
    const hold = this.holder(this.fxLayer, n.pos.add([0, dir * this.R]), new Vector2(0, dir * 48), this.attachments);
    const r = new Rect({fill: C.tag, stroke: C.line,
      lineWidth: 2, radius: 10, layout: true, padding: [5, 14], minWidth: 92, justifyContent: 'center', scale: 0, opacity: 0});
    const t = new Txt({text: value, fontFamily: F.mono, fontWeight: 700, fontSize: S.small, fill: value === '∞' ? C.muted : C.ink, letterSpacing: 0.01});
    r.add(t);
    hold.add(r);
    return {
      root: r, txt: t,
      *in(): ThreadGenerator { yield* all(r.opacity(1, 0.2), r.scale(1, 0.4, easeOutBack)); },
      *out(): ThreadGenerator { yield* r.opacity(0, 0.25); },
      *set(v: string, color = C.mint): ThreadGenerator {
        yield* t.scale(0, 0.12, easeInCubic);
        t.text(v).fill(textOf(color));
        yield* all(t.scale(1, 0.3, easeOutBack), r.stroke(lineOf(color), 0.15).wait(0.5).to(C.line, 0.6));
      },
    };
  }
  /** Dim everything except the given nodes (and the edges between them). */
  *focusOn(ids: Id[], d = 0.4): ThreadGenerator {
    const keep = new Set(ids.map(String));
    yield* all(
      ...[...this.nodes.values()].map(n => n.group.opacity(keep.has(String(n.id)) ? 1 : 0.35, d)),
      ...[...this.edges.values()].map(e => e.base.opacity(keep.has(String(e.u)) && keep.has(String(e.v)) ? 1 : 0.3, d)),
    );
  }
  *unfocus(d = 0.4): ThreadGenerator {
    yield* all(
      ...[...this.nodes.values()].map(n => n.group.opacity(1, d)),
      ...[...this.edges.values()].map(e => e.base.opacity(1, d)),
    );
    for (const e of this.edges.values()) e.base.opacity(() => (e.base.end() > 0.002 ? 1 : 0));
  }
}

/** Shake a node horizontally (a rejection, an impact). */
export function* shake(n: Node, amp = 14, d = 0.4): ThreadGenerator {
  const x0 = n.x();
  yield* tween(d, t => n.x(x0 + Math.sin(t * Math.PI * 7) * amp * (1 - t)));
  n.x(x0);
}

export {linear};
