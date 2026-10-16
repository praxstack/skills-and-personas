// The persistent subject for graph problems: a directed weighted graph laid out from data, drawn with depth
// (shaded nodes, floor shadows, glow on what is active; on a light theme the glows soften and lines use mark()).
// Its look at any frame is a GraphState that the scene director builds from cues keyed to line ids, so the same
// graph lives through the whole film.
//
//   const g = new GraphState(MAP);
//   g.nodes(['0','1','2','3'], (id, i) => ({show: pop(fr, f('p1', 0.2 + i * 0.1))}));
//   g.routeAt(fr, ['e01', 'e13'], f('p4'), sec(2), C.accent, {token: 'plane'});
//   g.fire('e12', fr, f('c1', 1.2), sec(0.6), C.mint);
//   <Graph data={MAP} st={g} place={{x: 1240, y: 520, s: 0.95, o: 1}} />
//
// Text keeps its size on screen when the graph is placed small: weight tags, node labels, badges and value pills
// never draw under `minPx` (SIZE.small, 30 px at camera zoom 1) whatever `place.s` is. So a small placement
// (a thumbnail next to code or a table) needs room for 30 px tags: about s >= 0.5 for a 1000-unit-wide graph.
import React from 'react';
import {clamp01, ease, EASE, bump} from '../lib/motion';
import {alpha} from './color';
import {C, FONT, GLOW_K, ink, mark, on, S, SIZE} from './tokens';

export type GNode = {id: string; x: number; y: number; label?: string; valueSide?: 'top' | 'bottom'; badgeSide?: 'top' | 'bottom'};
export type GEdge = {id: string; from: string; to: string; w?: number | string; bend?: number; tagAt?: number; tagShift?: number};
export type GraphData = {W: number; H: number; R: number; nodes: GNode[]; edges: GEdge[]};
/** where the graph sits in the world: centre x/y, scale, opacity */
export type Place = {x: number; y: number; s: number; o: number};

type HL = {c: string; d: number; o: number};
type Fire = {c: string; p: number; o: number};
export type EdgeS = {draw: number; dim: number; hl: HL[]; fire: Fire[]; tag: number; tagC?: string; strike: number};
export type NodeS = {
  show: number; dim: number; ring?: string; ringO: number; badge?: string; badgeC?: string; badgeO: number;
  value?: string; valueC?: string; valuePop: number; valueO: number; pulse: number; pulseC?: string;
};
export type Token = {route: string[]; p: number; c: string; o: number; icon: 'plane' | 'dot'};

/** mutable per-frame state of the graph; defaults: everything shown and drawn */
export class GraphState {
  n: Record<string, NodeS> = {};
  e: Record<string, EdgeS> = {};
  tokens: Token[] = [];
  constructor(public data: GraphData) {
    for (const nd of data.nodes) this.n[nd.id] = {show: 1, dim: 0, ringO: 0, badgeO: 0, valuePop: 1, valueO: 0, pulse: 0};
    for (const ed of data.edges) this.e[ed.id] = {draw: 1, dim: 0, hl: [], fire: [], tag: 1, strike: 0};
  }
  node(id: string) {
    const s = this.n[id];
    if (!s) throw new Error(`graph: no node ${id}`);
    return s;
  }
  edge(id: string) {
    const s = this.e[id];
    if (!s) throw new Error(`graph: no edge ${id}`);
    return s;
  }
  /** set fields on several nodes: g.nodes(ids, (id, i) => ({show: ...})) */
  nodes(ids: string[], fn: (id: string, i: number) => Partial<NodeS>) {
    ids.forEach((id, i) => Object.assign(this.node(id), fn(id, i)));
    return this;
  }
  edges(ids: string[], fn: (id: string, i: number) => Partial<EdgeS>) {
    ids.forEach((id, i) => Object.assign(this.edge(id), fn(id, i)));
    return this;
  }
  all() {
    return {nodes: this.data.nodes.map((x) => x.id), edges: this.data.edges.map((x) => x.id)};
  }
  /** dim everything except the given ids (v: 0..1) */
  dimExcept(v: number, keepNodes: string[] = [], keepEdges: string[] = []) {
    for (const id of Object.keys(this.n)) if (!keepNodes.includes(id)) this.n[id].dim = Math.max(this.n[id].dim, v);
    for (const id of Object.keys(this.e)) if (!keepEdges.includes(id)) this.e[id].dim = Math.max(this.e[id].dim, v);
    return this;
  }
  ring(id: string, color: string, o: number) {
    if (o <= 0) return this;
    Object.assign(this.node(id), {ring: color, ringO: o});
    return this;
  }
  badge(id: string, text: string, color: string, o: number) {
    if (o <= 0) return this;
    Object.assign(this.node(id), {badge: text, badgeC: color, badgeO: o});
    return this;
  }
  value(id: string, text: string, color: string, popV: number, o = 1) {
    if (o <= 0) return this;
    Object.assign(this.node(id), {value: text, valueC: color, valuePop: popV, valueO: o});
    return this;
  }
  /** expanding ring on a node (an event landed here) */
  pulse(id: string, fr: number, at: number, color = C.accent) {
    const k = (fr - at) / 18;
    if (k >= 0 && k <= 1) Object.assign(this.node(id), {pulse: k, pulseC: color});
    return this;
  }
  /** highlight a route: p runs 0 -> ids.length; a token rides the front when opts.token is set */
  route(ids: string[], p: number, color: string, opts: {o?: number; token?: 'plane' | 'dot' | false} = {}) {
    const o = opts.o ?? 1;
    if (p <= 0 || o <= 0) return this;
    ids.forEach((id, i) => this.edge(id).hl.push({c: color, d: clamp01(p - i), o}));
    const len = ids.length;
    if (opts.token && p < len + 0.35) {
      this.tokens.push({route: ids, p: Math.min(p, len), c: color, o: o * clamp01(p / 0.1) * clamp01((len + 0.35 - p) / 0.35), icon: opts.token});
    }
    return this;
  }
  /** eased route from frame `start` lasting `dur` frames */
  routeAt(fr: number, ids: string[], start: number, dur: number, color: string, opts: {o?: number; token?: 'plane' | 'dot' | false} = {}) {
    return this.route(ids, ease(fr, start, dur, EASE.inOut) * (ids.length + 0.35), color, opts);
  }
  /** an edge "fires": a bright pulse runs along it and it flashes */
  fire(id: string, fr: number, start: number, dur: number, color: string) {
    const p = (fr - start) / dur;
    const e = this.edge(id);
    if (p >= 0 && p <= 1.15) e.fire.push({c: color, p: Math.min(1, p), o: 1 - clamp01((p - 1) / 0.15)});
    const fl = bump(fr, start, dur + 10, 4, 14);
    if (fl > 0) e.hl.push({c: color, d: 1, o: fl * 0.9});
    return this;
  }
  /** strike an edge (an illegal or skipped move): rose X at its tag */
  strike(id: string, v: number) {
    this.edge(id).strike = Math.max(this.edge(id).strike, v);
    return this;
  }
}

type Pt = {x: number; y: number};
const towards = (a: Pt, b: Pt, r: number) => {
  const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy) || 1;
  return {x: a.x + (dx / L) * r, y: a.y + (dy / L) * r};
};

export const edgeGeom = (a: Pt, b: Pt, bend: number, R: number) => {
  const dx = b.x - a.x, dy = b.y - a.y, L = Math.hypot(dx, dy) || 1;
  const c = {x: (a.x + b.x) / 2 + (-dy / L) * bend, y: (a.y + b.y) / 2 + (dx / L) * bend};
  const s = towards(a, c, R + 6);
  const e = towards(b, c, R + 16);
  const pt = (t: number) => ({
    x: (1 - t) ** 2 * s.x + 2 * (1 - t) * t * c.x + t * t * e.x,
    y: (1 - t) ** 2 * s.y + 2 * (1 - t) * t * c.y + t * t * e.y,
  });
  const tan = (t: number) => ({x: 2 * (1 - t) * (c.x - s.x) + 2 * t * (e.x - c.x), y: 2 * (1 - t) * (c.y - s.y) + 2 * t * (e.y - c.y)});
  let len = 0;
  let prev = pt(0);
  for (let i = 1; i <= 48; i++) {
    const p = pt(i / 48);
    len += Math.hypot(p.x - prev.x, p.y - prev.y);
    prev = p;
  }
  return {d: `M ${s.x} ${s.y} Q ${c.x} ${c.y} ${e.x} ${e.y}`, pt, tan, len, s, e};
};

const geomCache = new WeakMap<GraphData, Record<string, ReturnType<typeof edgeGeom>>>();
export const geoms = (data: GraphData) => {
  let g = geomCache.get(data);
  if (!g) {
    const pos = Object.fromEntries(data.nodes.map((n) => [n.id, n]));
    g = Object.fromEntries(data.edges.map((e) => [e.id, edgeGeom(pos[e.from], pos[e.to], e.bend ?? 0, data.R)]));
    geomCache.set(data, g);
  }
  return g;
};

const tagPoint = (data: GraphData, ed: GEdge) => {
  const g = geoms(data)[ed.id];
  const p = g.pt(ed.tagAt ?? 0.5);
  if (!ed.tagShift) return p;
  const tn = g.tan(ed.tagAt ?? 0.5);
  const L = Math.hypot(tn.x, tn.y) || 1;
  return {x: p.x + (-tn.y / L) * ed.tagShift, y: p.y + (tn.x / L) * ed.tagShift};
};

/** graph coordinates -> world coordinates under a placement */
export const graphToWorld = (data: GraphData, place: Place, p: Pt) => ({
  x: place.x + (p.x - data.W / 2) * place.s,
  y: place.y + (p.y - data.H / 2) * place.s,
});
export const nodeWorld = (data: GraphData, place: Place, id: string) => {
  const n = data.nodes.find((x) => x.id === id);
  if (!n) throw new Error(`graph: no node ${id}`);
  return graphToWorld(data, place, n);
};
/** world position of an edge's weight tag (where a decoded entry lands) */
export const edgeTagWorld = (data: GraphData, place: Place, id: string) => {
  const ed = data.edges.find((x) => x.id === id);
  if (!ed) throw new Error(`graph: no edge ${id}`);
  return graphToWorld(data, place, tagPoint(data, ed));
};

const PLANE = 'M 18 0 L 6 -3.4 L -1 -16 L -7 -16 L -2.4 -3.4 L -11 -2.8 L -14.5 -9 L -18 -9 L -15.5 0 L -18 9 L -14.5 9 L -11 2.8 L -2.4 3.4 L -7 16 L -1 16 L 6 3.4 Z';

const Arrowhead: React.FC<{g: ReturnType<typeof edgeGeom>; fill: string; o: number; k?: number}> = ({g, fill, o, k = 1}) => {
  if (o <= 0) return null;
  const tn = g.tan(1);
  const ang = (Math.atan2(tn.y, tn.x) * 180) / Math.PI;
  return <path d="M 8 0 L -13 -10 L -8 0 L -13 10 Z" fill={fill} opacity={o} transform={`translate(${g.e.x} ${g.e.y}) rotate(${ang}) scale(${k})`} />;
};

/** text sizes in graph units for a placement: the design sizes, raised so nothing lands under minPx on screen */
export const graphText = (place: Place, tagSize = 36, labelSize = 48, minPx = SIZE.small) => {
  const lo = minPx / Math.max(0.05, place.s);
  const tag = Math.max(tagSize, lo);
  return {tag, tagH: tag * S.tagH, label: Math.max(labelSize, lo), badge: Math.max(28, lo), value: Math.max(38, lo)};
};

export const Graph: React.FC<{data: GraphData; st: GraphState; place: Place; uid?: string; tagSize?: number; labelSize?: number; minPx?: number}> = ({data, st, place, uid = 'g', tagSize = 36, labelSize = 48, minPx = SIZE.small}) => {
  if (place.o <= 0.002) return null;
  const {W, H, R} = data;
  const geo = geoms(data);
  const ts = graphText(place, tagSize, labelSize, minPx);
  return (
    <div style={{position: 'absolute', left: place.x - W / 2, top: place.y - H / 2, width: W, height: H, transform: `scale(${place.s})`, opacity: Math.min(1, place.o)}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{overflow: 'visible'}}>
        <defs>
          <radialGradient id={`${uid}-body`} cx="38%" cy="30%" r="80%">
            <stop offset="0%" stopColor={S.nodeHi} />
            <stop offset="55%" stopColor={S.nodeMid} />
            <stop offset="100%" stopColor={S.nodeLo} />
          </radialGradient>
          <radialGradient id={`${uid}-shadow`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={S.floor} stopOpacity={S.floorO} />
            <stop offset="100%" stopColor={S.floor} stopOpacity="0" />
          </radialGradient>
          <filter id={`${uid}-glow`} x="-60%" y="-60%" width="220%" height="220%">
            <feGaussianBlur stdDeviation="7" />
          </filter>
        </defs>

        {/* floor shadows under nodes (depth) */}
        {data.nodes.map((nd) => {
          const s = st.n[nd.id];
          if (s.show <= 0.01) return null;
          return <ellipse key={'sh' + nd.id} cx={nd.x + 8} cy={nd.y + R * 0.95} rx={R * 1.25 * s.show} ry={R * 0.38 * s.show} fill={`url(#${uid}-shadow)`} opacity={1 - s.dim * 0.7} />;
        })}

        {/* base edges: invisible until they start drawing; arrowhead only once fully drawn */}
        {data.edges.map((ed) => {
          const s = st.e[ed.id];
          if (s.draw <= 0.001) return null;
          const g = geo[ed.id];
          return (
            <g key={ed.id} opacity={1 - s.dim * 0.8}>
              <path d={g.d} fill="none" stroke={alpha(C.ink, 0.34)} strokeWidth={4} strokeLinecap="round"
                strokeDasharray={`${g.len} ${g.len + 2}`} strokeDashoffset={g.len * (1 - s.draw)} />
              <Arrowhead g={g} fill={alpha(C.ink, 0.55)} o={clamp01((s.draw - 0.94) / 0.06)} />
            </g>
          );
        })}

        {/* highlight layers: glow + core + arrowhead */}
        {data.edges.map((ed) => {
          const s = st.e[ed.id];
          const g = geo[ed.id];
          return s.hl.map((l, i) =>
            l.d > 0 && l.o > 0.01 ? (
              <g key={ed.id + 'h' + i} opacity={l.o}>
                <path d={g.d} fill="none" stroke={l.c} strokeWidth={16} opacity={0.55 * GLOW_K} filter={`url(#${uid}-glow)`}
                  strokeDasharray={`${g.len} ${g.len + 2}`} strokeDashoffset={g.len * (1 - l.d)} strokeLinecap="round" />
                <path d={g.d} fill="none" stroke={mark(l.c)} strokeWidth={6.5} strokeLinecap="round"
                  strokeDasharray={`${g.len} ${g.len + 2}`} strokeDashoffset={g.len * (1 - l.d)} />
                <Arrowhead g={g} fill={mark(l.c)} o={clamp01((l.d - 0.9) / 0.1)} k={1.15} />
              </g>
            ) : null,
          );
        })}

        {/* fire pulses */}
        {data.edges.map((ed) => {
          const s = st.e[ed.id];
          const g = geo[ed.id];
          return s.fire.map((fi, i) => {
            const seg = Math.min(110, g.len * 0.4);
            const head = g.pt(fi.p);
            return (
              <g key={ed.id + 'f' + i} opacity={fi.o}>
                <path d={g.d} fill="none" stroke={S.spark} strokeWidth={7} strokeLinecap="round"
                  strokeDasharray={`${seg} ${g.len + seg}`} strokeDashoffset={-(fi.p * g.len - seg)} />
                <circle cx={head.x} cy={head.y} r={22} fill={fi.c} opacity={0.45 * GLOW_K} filter={`url(#${uid}-glow)`} />
                <circle cx={head.x} cy={head.y} r={8} fill={S.spark} />
              </g>
            );
          });
        })}

        {/* weight tags */}
        {data.edges.map((ed) => {
          if (ed.w === undefined) return null;
          const s = st.e[ed.id];
          const o = Math.min(clamp01((s.draw - 0.3) / 0.3), clamp01(s.tag)) * (1 - s.dim * 0.75);
          if (o <= 0.01) return null;
          const p = tagPoint(data, ed);
          const top = s.hl.filter((l) => l.d > 0.45 && l.o > 0.4).pop();
          const col = s.tagC ?? (top ? top.c : C.amber);
          const txt = String(ed.w);
          const w = txt.length * ts.tag * 0.6 + ts.tag * 0.95;
          const h = ts.tagH;
          const sc = 0.7 + 0.3 * Math.min(1.08, s.tag);
          return (
            <g key={ed.id + 't'} opacity={o} transform={`translate(${p.x} ${p.y}) scale(${sc})`}>
              <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={h / 2} fill={S.pill} stroke={top ? mark(col) : alpha(C.ink, 0.22)} strokeWidth={2.5} />
              <text y={ts.tag * 0.36} textAnchor="middle" fontFamily={FONT.mono} fontWeight={800} fontSize={ts.tag} fill={ink(col)}>{txt}</text>
            </g>
          );
        })}

        {/* strikes */}
        {data.edges.map((ed) => {
          const s = st.e[ed.id];
          if (s.strike <= 0.01) return null;
          const p = tagPoint(data, ed);
          const k = s.strike;
          return (
            <g key={ed.id + 'x'} transform={`translate(${p.x} ${p.y - ts.tagH / 2 - 26}) scale(${0.6 + 0.4 * Math.min(1.1, k)})`} opacity={clamp01(k)}>
              <circle r={30} fill={C.rose} opacity={0.22} />
              <path d="M -15 -15 L 15 15 M 15 -15 L -15 15" stroke={mark(C.rose)} strokeWidth={8} strokeLinecap="round" />
            </g>
          );
        })}

        {/* nodes */}
        {data.nodes.map((nd) => {
          const s = st.n[nd.id];
          if (s.show <= 0.002) return null;
          const vSide = nd.valueSide === 'top' ? -1 : 1;
          const bSide = nd.badgeSide === 'bottom' ? 1 : -1;
          const op = 1 - s.dim * 0.65;
          return (
            <g key={nd.id} transform={`translate(${nd.x} ${nd.y})`} opacity={op}>
              <g transform={`scale(${s.show})`} opacity={clamp01(s.show * 1.5)}>
                {s.ringO > 0 && s.ring && (
                  <>
                    <circle r={R + 18} fill={s.ring} opacity={0.35 * s.ringO * GLOW_K} filter={`url(#${uid}-glow)`} />
                    <circle r={R + 9} fill="none" stroke={mark(s.ring)} strokeWidth={5} opacity={s.ringO} />
                  </>
                )}
                <circle r={R} fill={`url(#${uid}-body)`} stroke={alpha(C.ink, 0.28)} strokeWidth={2.5} />
                <ellipse cx={-R * 0.3} cy={-R * 0.42} rx={R * 0.42} ry={R * 0.22} fill={S.spec} opacity={0.09} />
                <text y={ts.label * 0.35} textAnchor="middle" fontFamily={FONT.mono} fontWeight={800} fontSize={ts.label} fill={C.ink}>{nd.label ?? nd.id}</text>
                {s.pulse > 0 && s.pulse < 1 && (
                  <circle r={R + 6 + s.pulse * 46} fill="none" stroke={mark(s.pulseC ?? C.accent)} strokeWidth={6 * (1 - s.pulse)} opacity={1 - s.pulse} />
                )}
              </g>
              {s.badgeO > 0 && s.badge && (() => {
                const bf = ts.badge;
                const bw = s.badge.length * bf * 0.68 + bf * 1.43;
                const bh = bf * 1.57;
                return (
                  <g opacity={clamp01(s.badgeO)} transform={`translate(0 ${bSide * (R + bh / 2 + 18) + (1 - clamp01(s.badgeO)) * 12})`}>
                    <rect x={-bw / 2} y={-bh / 2} width={bw} height={bh} rx={bh / 2} fill={s.badgeC} />
                    <text y={bf * 0.36} textAnchor="middle" fontFamily={FONT.sans} fontWeight={900} fontSize={bf} letterSpacing="0.08em" fill={on(s.badgeC ?? C.accent)}>{s.badge}</text>
                  </g>
                );
              })()}
              {s.valueO > 0 && s.value != null && (() => {
                const fs = ts.value;
                const w = s.value.length * fs * 0.6 + fs * 1.05;
                const h = fs * 1.58;
                return (
                  <g opacity={clamp01(s.valueO)} transform={`translate(0 ${vSide * (R + h / 2 + 14)}) scale(${0.55 + 0.45 * s.valuePop})`}>
                    <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={14} fill={S.valuePill} stroke={mark(s.valueC ?? C.ink)} strokeWidth={3} />
                    <text y={fs * 0.36} textAnchor="middle" fontFamily={FONT.mono} fontWeight={800} fontSize={fs} fill={ink(s.valueC ?? C.ink)}>{s.value}</text>
                  </g>
                );
              })()}
            </g>
          );
        })}

        {/* tokens riding routes */}
        {st.tokens.map((tk, i) => {
          const L = tk.route.length;
          const k = Math.min(Math.floor(tk.p), L - 1);
          const g = geo[tk.route[k]];
          const u = clamp01(tk.p - k);
          const q = g.pt(u);
          const tn = g.tan(u);
          const ang = (Math.atan2(tn.y, tn.x) * 180) / Math.PI;
          return (
            <g key={'tk' + i} opacity={tk.o} transform={`translate(${q.x} ${q.y}) rotate(${ang})`}>
              <circle r={34} fill={tk.c} opacity={0.5 * GLOW_K} filter={`url(#${uid}-glow)`} />
              {tk.icon === 'plane' ? (
                <path d={PLANE} fill={S.plane} stroke={tk.c} strokeWidth={1.5} transform="scale(1.7)" />
              ) : (
                <circle r={13} fill={S.plane} />
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
