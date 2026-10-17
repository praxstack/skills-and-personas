// graph.js: the persistent subject. A directed weighted graph drawn as glowing pucks and curved arrows, laid out
// from data, with travelling tokens (a plane by default) that fly routes, edge "fires", rings, tags and value badges.
//
//   new Graph({ nodes: [{ id: 0, x: 820, y: 520 }], edges: [{ from: 0, to: 1, w: 100, bend: 0.15 }], tokens: 2 })
//
// Theatre objects (all start hidden; shots.js brings them in):
//   Graph                    x, y, s (move/scale the whole graph around its centre), in (opacity)
//   Graph / node <id>        in (pop in), glow, hot, good, bad, dim, ring (0..1 expanding ring), tag (text chip
//                            under the node, e.g. "START"), tagIn, badge (text above, e.g. a dist value), badgeIn
//                            badgeAt (where the badge sits: 'tr' | 'tl' | 'br' | 'bl' | 'above' | 'below'; '' uses
//                            the node's data badgeAt, else 'tr'; s.set it per shot to keep badges clear of panels)
//   Graph / edge <a>-<b>     draw (0..1 stroke draws on), glow, hot, good, bad, dim, fire (0..1 pulse travelling
//                            along it), strike (0..1 rejection cross), label (weight chip visibility; the chip
//                            appears when the arrow has finished drawing)
//
// Legibility: every text here keeps a minimum size ON SCREEN (tokens.GRAPH_TEXT) however small the graph is placed
// or however far the camera pulls back, and `dim` fades lines and faces but keeps text at 4.5:1 or better.
//   Graph / token <i>        route ("0-1-3"), u (0..1 progress along the whole route), in, sum (running total chip)
import { C, GRAPH_TEXT as GT } from './tokens.js';
import { layerScale } from './stage.js';
import { clamp, lerp, mix, css, svg, setAttr, setText, bestInk } from './util.js';

const BADGE_AT = { tr: [1, -1], tl: [-1, -1], br: [1, 1], bl: [-1, 1], above: [0, -1], below: [0, 1] };

export class Graph {
  constructor({ id = 'Graph', nodes, edges, r = 54, tokens = 1, glyph = 'plane', layer = 'subject' }) {
    Object.assign(this, { id, nodes, edges, r, tokens, glyph, layerName: layer });
    this.N = new Map(nodes.map((n) => [String(n.id), n]));
    for (const e of edges) Object.assign(e, this.geometry(e));
    const xs = nodes.map((n) => n.x), ys = nodes.map((n) => n.y);
    this.cx = (Math.min(...xs) + Math.max(...xs)) / 2; this.cy = (Math.min(...ys) + Math.max(...ys)) / 2;
  }

  nodeKey(id) { return `${this.id} / node ${id}`; }
  edgeKey(a, b) { return `${this.id} / edge ${a}-${b}`; }
  tokenKey(i = 0) { return `${this.id} / token ${i}`; }
  edge(a, b) { return this.edges.find((e) => String(e.from) === String(a) && String(e.to) === String(b)); }

  objects() {
    const o = { [this.id]: { x: 0, y: 0, s: 1, in: 1 } };
    for (const n of this.nodes) o[this.nodeKey(n.id)] = { in: 0, glow: 0, hot: 0, good: 0, bad: 0, dim: 0, ring: 0, tag: '', tagIn: 0, badge: '', badgeIn: 0, badgeAt: '' };
    for (const e of this.edges) o[this.edgeKey(e.from, e.to)] = { draw: 0, glow: 0, hot: 0, good: 0, bad: 0, dim: 0, fire: 0, strike: 0, label: 1 };
    for (let i = 0; i < this.tokens; i++) o[this.tokenKey(i)] = { route: '', u: 0, in: 0, sum: 0 };
    return o;
  }

  /** bounding box [x0, y0, x1, y1] of some nodes (default all) for a Graph placement {x, y, s}: for R.focus() */
  rect(ids = null, place = {}, pad = null) {
    const { x = 0, y = 0, s = 1 } = place, p = pad ?? this.r + 30;
    const ns = ids ? ids.map((i) => this.N.get(String(i))) : this.nodes;
    const X = ns.map((n) => (n.x - this.cx) * s + this.cx + x), Y = ns.map((n) => (n.y - this.cy) * s + this.cy + y);
    return Object.assign([Math.min(...X) - p * s, Math.min(...Y) - p * s, Math.max(...X) + p * s, Math.max(...Y) + (p + 70) * s], { layer: this.layerName });
  }

  // ---------------------------------------------------------------- geometry (pure; the 3D variant reuses it)
  geometry(e) {
    const A = this.N.get(String(e.from)), B = this.N.get(String(e.to));
    if (!A || !B) throw new Error(`graph: edge ${e.from}-${e.to} names a missing node`);
    const dx = B.x - A.x, dy = B.y - A.y, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
    const bend = e.bend ?? 0.12;
    const cxy = [(A.x + B.x) / 2 + nx * bend * len, (A.y + B.y) / 2 + ny * bend * len];
    const q = (u) => [ // quadratic from centre to centre
      (1 - u) ** 2 * A.x + 2 * (1 - u) * u * cxy[0] + u * u * B.x,
      (1 - u) ** 2 * A.y + 2 * (1 - u) * u * cxy[1] + u * u * B.y];
    // trim the drawn stroke at the rims (and leave room for the arrowhead)
    const cut = (u0, from, gap) => { let u = u0; for (let i = 0; i < 60; i++) { const p = q(u); if (Math.hypot(p[0] - from.x, p[1] - from.y) >= this.r + gap) break; u += from === A ? 0.005 : -0.005; } return u; };
    const u0 = cut(0, A, 8), u1 = cut(1, B, 26);
    const t0 = cut(0, A, 40), t1 = cut(1, B, 30); // where a token leaves and docks: its body clears the node's number
    const pts = []; for (let i = 0; i <= 32; i++) pts.push(q(lerp(u0, u1, i / 32)));
    let L = 0; for (let i = 1; i < pts.length; i++) L += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
    const d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)} ` + pts.slice(1).map((p) => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
    const end = q(u1), pre = q(u1 - 0.02), ang = Math.atan2(end[1] - pre[1], end[0] - pre[0]);
    const mid = q(0.5), sgn = Math.sign(bend) || 1;
    return { q, d, L, end, ang, t0, t1, chip: [mid[0] + nx * 34 * sgn, mid[1] + ny * 34 * sgn], nrm: [nx * sgn, ny * sgn], mid };
  }

  /** point and heading of a token at progress u along a route like "0-1-3" (legs take equal time) */
  routePoint(route, u) {
    const ids = String(route).split('-').filter((x) => x !== '');
    if (ids.length < 2) { const n = this.N.get(ids[0] ?? String(this.nodes[0].id)); return { x: n.x, y: n.y, ang: 0, leg: 0, legs: 0, done: 0 }; }
    const legs = ids.length - 1, f = clamp(u) * legs, i = Math.min(legs - 1, Math.floor(f)), v = f - i;
    const e = this.edge(ids[i], ids[i + 1]);
    const A = this.N.get(ids[i]), B = this.N.get(ids[i + 1]);
    const q0 = e ? e.q : (w) => [lerp(A.x, B.x, w), lerp(A.y, B.y, w)];
    // a token leaves from the first node's rim and docks at the last arrowhead, so it never sits on a node's number
    // (in between it passes straight through the nodes it visits)
    const a0 = e && i === 0 ? e.t0 : 0, a1 = e && i === legs - 1 ? e.t1 : 1, q = (w) => q0(lerp(a0, a1, w));
    const p = q(v), p2 = q(Math.min(1, v + 0.02)), p1 = q(Math.max(0, v - 0.02));
    let done = 0; for (let k = 0; k < legs; k++) if (f >= k + 0.98) done += this.edge(ids[k], ids[k + 1])?.w ?? 0;
    return { x: p[0], y: p[1], ang: Math.atan2(p2[1] - p1[1], p2[0] - p1[0]), leg: i, legs, done, ids };
  }

  // ---------------------------------------------------------------- DOM
  mount(stage) {
    const root = svg('svg', { class: 'graph', width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, stage.layer(this.layerName));
    const defs = svg('defs', {}, root), U = (this.uid = this.id.replace(/\W/g, '_')); // gradient ids unique per graph
    defs.innerHTML = `
      <radialGradient id="g-halo-${U}"><stop offset="0" stop-color="${C.fire}" stop-opacity="0.9"/><stop offset="0.35" stop-color="${C.fire}" stop-opacity="0.35"/><stop offset="1" stop-color="${C.fire}" stop-opacity="0"/></radialGradient>
      <radialGradient id="g-shadow-${U}"><stop offset="0" stop-color="${C.shadow}" stop-opacity="${0.75 * C.shadowK}"/><stop offset="1" stop-color="${C.shadow}" stop-opacity="0"/></radialGradient>
      <linearGradient id="g-shine-${U}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${C.shine}" stop-opacity="0.28"/><stop offset="0.55" stop-color="${C.shine}" stop-opacity="0"/></linearGradient>`;
    this.g = svg('g', {}, root);
    const gEdges = svg('g', {}, this.g), gNodes = svg('g', {}, this.g), gTok = svg('g', {}, this.g);
    for (const e of this.edges) {
      const g = svg('g', { opacity: 0 }, gEdges);
      e.el = {
        g,
        glow: svg('path', { d: e.d, fill: 'none', 'stroke-width': 18, 'stroke-linecap': 'round', opacity: 0 }, g),
        line: svg('path', { d: e.d, fill: 'none', 'stroke-width': 5, 'stroke-linecap': 'round', 'stroke-dasharray': `${e.L.toFixed(1)} ${e.L.toFixed(1)}` }, g),
        head: svg('polygon', { points: '0,0 -24,-11 -18,0 -24,11', transform: `translate(${e.end[0].toFixed(1)},${e.end[1].toFixed(1)}) rotate(${(e.ang * 180 / Math.PI).toFixed(1)})` }, g),
        chip: svg('g', { transform: `translate(${e.chip[0].toFixed(1)},${e.chip[1].toFixed(1)})` }, g),
        fire: svg('g', { opacity: 0 }, g),
        strike: svg('g', { transform: `translate(${e.mid[0].toFixed(1)},${e.mid[1].toFixed(1)})`, opacity: 0 }, g),
      };
      const fs = GT.weight.font, w = String(e.w ?? '').length * fs * 0.6 + 40, h = Math.round(fs * 1.6); // the text sits well inside its outline, which glows when the edge is hot
      e.el.chipBg = svg('rect', { x: -w / 2, y: -h / 2, width: w, height: h, rx: 12, fill: css(C.plate, 0.94), 'stroke-width': 2 }, e.el.chip);
      e.el.chipTx = svg('text', { x: 0, y: Math.round(fs * 0.36), 'text-anchor': 'middle', class: 'mono', 'font-size': fs, 'font-weight': 700, fill: C.ink, text: e.w ?? '' }, e.el.chip);
      e.chipH = h;
      svg('circle', { r: 26, fill: `url(#g-halo-${this.uid})`, opacity: 0.55 }, e.el.fire);
      e.el.fireDot = svg('circle', { r: 9, fill: C.fire }, e.el.fire);
      for (const [a, b] of [[-1, -1], [1, -1]]) svg('line', { x1: 26 * a, y1: 26 * b, x2: -26 * a, y2: -26 * b, stroke: C.bad, 'stroke-width': 9, 'stroke-linecap': 'round' }, e.el.strike);
    }
    for (const n of this.nodes) {
      const g = svg('g', { opacity: 0 }, gNodes), r = this.r;
      const hg = svg('radialGradient', { id: `halo-${this.uid}-${String(n.id).replace(/\W/g, '_')}` }, defs);
      const stops = [[0, 0.85], [0.4, 0.3], [1, 0]].map(([o, a]) => svg('stop', { offset: o, 'stop-color': C.gold, 'stop-opacity': a }, hg));
      n.el = {
        g,
        shadow: svg('ellipse', { cx: 0, cy: r * 1.05, rx: r * 1.15, ry: r * 0.3, fill: `url(#g-shadow-${this.uid})` }, g),
        halo: svg('circle', { r: r * 2.3, fill: `url(#halo-${this.uid}-${String(n.id).replace(/\W/g, '_')})`, opacity: 0 }, g),
        ring: svg('circle', { r, fill: 'none', 'stroke-width': 5, opacity: 0 }, g),
        side: svg('circle', { cy: 10, r, fill: C.nodeSide }, g),
        face: svg('circle', { r, 'stroke-width': 4 }, g),
        shine: svg('ellipse', { cx: 0, cy: -r * 0.32, rx: r * 0.78, ry: r * 0.55, fill: `url(#g-shine-${this.uid})` }, g),
        label: svg('text', { y: Math.round(GT.node.font * 0.36), 'text-anchor': 'middle', class: 'mono', 'font-size': GT.node.font, 'font-weight': 800, fill: C.ink, text: n.label ?? n.id }, g),
        tag: svg('g', { transform: `translate(0,${r + 46})`, opacity: 0 }, g),
        badge: svg('g', { transform: `translate(${r * 0.95},${-r * 1.05})`, opacity: 0 }, g),
        stops,
      };
      // chips are padded generously: text sits well inside its plate (and away from the outline) at every size
      const tf = GT.tag.font, th = Math.round(tf * 1.7), bf = GT.badge.font, bh = Math.round(bf * 1.5);
      n.el.tagBg = svg('rect', { y: -th / 2, height: th, rx: 9, fill: C.gold, stroke: C.outline, 'stroke-width': 3 }, n.el.tag);
      n.el.tagTx = svg('text', { y: Math.round(tf * 0.36), 'text-anchor': 'middle', class: 'ui', 'font-size': tf, 'font-weight': 900, 'letter-spacing': 2, fill: C.onGold }, n.el.tag);
      n.el.badgeBg = svg('rect', { y: -bh / 2, height: bh, rx: 12, fill: css(C.plate, 0.95), 'stroke-width': 3 }, n.el.badge);
      n.el.badgeTx = svg('text', { y: Math.round(bf * 0.36), 'text-anchor': 'middle', class: 'mono', 'font-size': bf, 'font-weight': 800, fill: C.ink }, n.el.badge);
      Object.assign(n, { tagH: th, badgeH: bh, tagW: 0, badgeW: 0 });
    }
    this.tok = [];
    for (let i = 0; i < this.tokens; i++) {
      const g = svg('g', { opacity: 0 }, gTok), trail = [];
      for (let k = 0; k < 12; k++) trail.push(svg('circle', { r: 10 - k * 0.7, fill: i ? C.cool : C.gold, opacity: 0 }, g));
      const body = svg('g', {}, g);
      svg('circle', { r: 46, fill: `url(#g-halo-${this.uid})`, opacity: 0.5 }, body);
      const plane = svg('g', {}, body);
      if (this.glyph === 'plane') {
        svg('path', { d: 'M36,0 C36,-4 31,-6 25,-6 L8,-6 L-9,-36 L-19,-36 L-9,-6 L-25,-6 L-33,-18 L-40,-18 L-35,-3 L-35,3 L-40,18 L-33,18 L-25,6 L-9,6 L-19,36 L-9,36 L8,6 L25,6 C31,6 36,4 36,0 Z', fill: i ? C.cool : C.ink, stroke: C.tokenStroke, 'stroke-width': 3, 'stroke-linejoin': 'round' }, plane);
      } else svg('circle', { r: 16, fill: i ? C.cool : C.gold, stroke: C.tokenStroke, 'stroke-width': 4 }, plane);
      const sum = svg('g', { opacity: 0 }, g);
      const sf = GT.sum.font, sh = Math.round(sf * 1.5);
      const sumBg = svg('rect', { x: -60, y: -48 - sh, width: 120, height: sh, rx: 14, fill: C.gold, stroke: C.outline, 'stroke-width': 3 }, sum);
      const sumTx = svg('text', { y: Math.round(-48 - sh / 2 + sf * 0.36), 'text-anchor': 'middle', class: 'mono', 'font-size': sf, 'font-weight': 800, fill: C.onGold }, sum);
      this.tok.push({ g, trail, body, plane, sum, sumBg, sumTx });
    }
    return this;
  }

  stateColor(v, base) {
    let c = mix(base, C.accent, v.hot);
    c = mix(c, C.good, v.good);
    return mix(c, C.bad, v.bad);
  }

  apply(V) {
    const G = V[this.id];
    setAttr(this.g, 'transform', `translate(${(G.x + this.cx).toFixed(2)},${(G.y + this.cy).toFixed(2)}) scale(${G.s.toFixed(4)}) translate(${-this.cx},${-this.cy})`);
    setAttr(this.g, 'opacity', clamp(G.in).toFixed(3));
    // screen px per graph px (graph scale x camera dolly); a label grows inside the graph when that would put it
    // under its minimum on-screen size, and scales with the graph otherwise
    const eff = Math.max(0.05, G.s * (V.Camera ? layerScale(this.layerName, V.Camera.z) : 1));
    const grow = (kind) => Math.max(1, GT[kind].min / (GT[kind].font * eff));
    const gw = grow('weight'), gb = grow('badge'), gt = grow('tag'), gn = grow('node'), gs = grow('sum');
    for (const e of this.edges) {
      const v = V[this.edgeKey(e.from, e.to)], el = e.el;
      const draw = clamp(v.draw);
      setAttr(el.g, 'opacity', draw <= 0.001 ? '0' : '1');
      if (draw <= 0.001) continue;
      const dim = 1 - 0.72 * clamp(v.dim); // dims the stroke; the weight stays readable (inkDim on its plate)
      const col = this.stateColor(v, C.edge), hotness = clamp(Math.max(v.hot, v.good, v.bad));
      setAttr(el.line, 'stroke', css(col));
      setAttr(el.line, 'opacity', dim.toFixed(3));
      setAttr(el.line, 'stroke-dashoffset', (e.L * (1 - draw)).toFixed(1));
      setAttr(el.line, 'stroke-width', (5 + 2 * hotness).toFixed(2));
      setAttr(el.glow, 'stroke', css(col));
      setAttr(el.glow, 'stroke-dasharray', `${e.L.toFixed(1)} ${e.L.toFixed(1)}`);
      setAttr(el.glow, 'stroke-dashoffset', (e.L * (1 - draw)).toFixed(1));
      setAttr(el.glow, 'opacity', ((0.1 + 0.32 * clamp(v.glow + hotness)) * dim).toFixed(3));
      const hs = clamp((draw - 0.88) / 0.12);
      setAttr(el.head, 'fill', css(col));
      setAttr(el.head, 'opacity', (hs * dim).toFixed(3));
      // the weight appears as the arrow lands (no slow fade: half-transparent text is unreadable text)
      setAttr(el.chip, 'opacity', (clamp(v.label) * clamp((draw - 0.94) / 0.04)).toFixed(3));
      const off = Math.max(34, (e.chipH / 2 + 12) * gw);
      setAttr(el.chip, 'transform', `translate(${(e.mid[0] + e.nrm[0] * off).toFixed(1)},${(e.mid[1] + e.nrm[1] * off).toFixed(1)}) scale(${gw.toFixed(3)})`);
      setAttr(el.chipBg, 'stroke', css(mix(C.chipStroke, col, hotness)));
      setAttr(el.chipTx, 'fill', css(mix(C.ink, C.inkDim, clamp(v.dim))));
      const f = v.fire;
      if (f > 0.001 && f < 0.999) {
        const p = e.q(f);
        setAttr(el.fire, 'opacity', Math.min(1, Math.min(f, 1 - f) * 8).toFixed(3));
        setAttr(el.fire, 'transform', `translate(${p[0].toFixed(1)},${p[1].toFixed(1)})`);
      } else setAttr(el.fire, 'opacity', '0');
      setAttr(el.strike, 'opacity', clamp(v.strike * 1.5).toFixed(3));
      setAttr(el.strike, 'transform', `translate(${e.mid[0].toFixed(1)},${e.mid[1].toFixed(1)}) scale(${(0.4 + 0.6 * clamp(v.strike)).toFixed(3)}) rotate(${(-20 + 20 * clamp(v.strike)).toFixed(1)})`);
    }
    for (const n of this.nodes) {
      const v = V[this.nodeKey(n.id)], el = n.el;
      const s = Math.max(0, v.in);
      setAttr(el.g, 'opacity', s <= 0.001 ? '0' : (clamp(s * 2) * (1 - 0.35 * clamp(v.dim))).toFixed(3));
      if (s <= 0.001) continue;
      setAttr(el.g, 'transform', `translate(${n.x},${n.y}) scale(${s.toFixed(4)})`);
      const col = this.stateColor(v, C.edge), amt = clamp(Math.max(v.hot, v.good, v.bad));
      const face = mix(C.node, col, amt * 0.75);
      setAttr(el.face, 'fill', css(face));
      setAttr(el.face, 'stroke', css(mix(C.nodeStroke, col, Math.max(amt, 0.5 * clamp(v.glow)))));
      setAttr(el.side, 'fill', css(mix(C.nodeSide, col, amt * 0.45)));
      const haloCol = css(amt > 0.05 ? col : C.gold, 1);
      for (const st of el.stops) setAttr(st, 'stop-color', haloCol);
      setAttr(el.halo, 'opacity', (0.6 * C.glowK * clamp(v.glow + amt * 0.6)).toFixed(3));
      // on a hot face: the kit's dark label, or (themed) whichever on-colour or text colour reads best on that face
      setAttr(el.label, 'fill', amt > 0.5 ? C.labelHot || css(bestInk(face, [C.onAccent, C.onGood, C.ink])) : css(mix(C.ink, C.inkDim, clamp(v.dim))));
      setAttr(el.label, 'transform', `scale(${gn.toFixed(3)})`);
      const rg = v.ring;
      if (rg > 0.001 && rg < 0.999) {
        setAttr(el.ring, 'r', (this.r + 80 * rg).toFixed(1));
        setAttr(el.ring, 'opacity', (1 - rg).toFixed(3));
        setAttr(el.ring, 'stroke', css(amt > 0.1 ? col : C.gold));
      } else setAttr(el.ring, 'opacity', '0');
      if (v.tag && n.tagText !== v.tag) {
        n.tagText = v.tag; setText(el.tagTx, v.tag);
        n.tagW = Math.ceil(textWidth(el.tagTx, v.tag.length * GT.tag.font * 0.75)) + 36;
        setAttr(el.tagBg, 'x', -n.tagW / 2); setAttr(el.tagBg, 'width', n.tagW);
      }
      // entrances: opacity lands in the first fifth of the tween, the rest is a scale/slide pop
      const ti = v.tag ? clamp(v.tagIn) : 0;
      setAttr(el.tag, 'opacity', clamp(ti * 5).toFixed(3));
      setAttr(el.tag, 'transform', `translate(0,${(this.r + 18 + (n.tagH / 2) * gt + 14 * (1 - ti)).toFixed(1)}) rotate(-2) scale(${(gt * (0.85 + 0.15 * Math.min(1.2, v.tagIn))).toFixed(3)})`);
      if (v.badge && n.badgeText !== v.badge) {
        n.badgeText = v.badge; setText(el.badgeTx, v.badge);
        n.badgeW = Math.ceil(textWidth(el.badgeTx, [...v.badge].length * GT.badge.font * 0.6)) + 30;
        setAttr(el.badgeBg, 'x', -n.badgeW / 2); setAttr(el.badgeBg, 'width', n.badgeW);
      }
      if (v.badge) setAttr(el.badgeBg, 'stroke', css(amt > 0.1 ? col : C.cool));
      const bi = v.badge ? clamp(v.badgeIn) : 0;
      setAttr(el.badge, 'opacity', clamp(bi * 5).toFixed(3));
      const [ax, ay] = BADGE_AT[v.badgeAt || n.badgeAt || 'tr'] || BADGE_AT.tr, bs = gb * (0.85 + 0.15 * Math.min(1.2, v.badgeIn));
      // sit on the node's shoulder (corners) or clear of it (above / below), whatever size the badge has grown to
      const bx = ax ? ax * (this.r * 0.1 + (n.badgeW / 2) * gb) : 0;
      const by = ay * (ax ? this.r * 0.6 + (n.badgeH / 2) * gb : this.r + 14 + (n.badgeH / 2) * gb);
      setAttr(el.badge, 'transform', `translate(${bx.toFixed(1)},${by.toFixed(1)}) scale(${bs.toFixed(3)})`);
    }
    for (let i = 0; i < this.tokens; i++) {
      const v = V[this.tokenKey(i)], T = this.tok[i];
      const vis = clamp(v.in);
      setAttr(T.g, 'opacity', vis <= 0.001 || !v.route ? '0' : vis.toFixed(3));
      if (vis <= 0.001 || !v.route) continue;
      const p = this.routePoint(v.route, v.u);
      setAttr(T.body, 'transform', `translate(${p.x.toFixed(1)},${p.y.toFixed(1)})`);
      setAttr(T.plane, 'transform', `rotate(${(p.ang * 180 / Math.PI).toFixed(1)}) scale(${(0.7 + 0.3 * vis).toFixed(3)})`);
      T.trail.forEach((c, k) => {
        const uu = v.u - (k + 1) * 0.012;
        if (uu <= 0 || v.u >= 0.999 || v.u <= 0.001) { setAttr(c, 'opacity', '0'); return; }
        const q = this.routePoint(v.route, uu);
        setAttr(c, 'cx', q.x.toFixed(1)); setAttr(c, 'cy', q.y.toFixed(1));
        setAttr(c, 'opacity', (0.55 * (1 - k / 12)).toFixed(3));
      });
      setAttr(T.sum, 'opacity', clamp(v.sum * 5).toFixed(3));
      if (v.sum > 0.001) {
        // the running total rides above the token, and settles over the destination once the token docks at its rim
        const end = p.ids ? this.N.get(p.ids[p.ids.length - 1]) : null, dk = end ? clamp((v.u - 0.9) / 0.1) : 0;
        const sx = end ? lerp(p.x, end.x, dk) : p.x, sy = end ? lerp(p.y, end.y, dk) : p.y;
        setAttr(T.sum, 'transform', `translate(${sx.toFixed(1)},${sy.toFixed(1)}) scale(${gs.toFixed(3)})`);
        const txt = String(p.done);
        setText(T.sumTx, txt);
        const w = txt.length * GT.sum.font * 0.6 + 36; setAttr(T.sumBg, 'x', -w / 2); setAttr(T.sumBg, 'width', w);
      }
    }
  }
}

/** rendered width of an SVG text (fonts are loaded before mount); falls back to an estimate */
function textWidth(t, guess) {
  try { const w = t.getComputedTextLength(); return w > 0 ? w : guess; } catch { return guess; }
}
