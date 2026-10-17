// kit/graph.js: the persistent subject. A directed weighted graph in WORLD space (it moves with the camera).
//
//   const G = K.graph({ nodes: [{id:'0', x:760, y:520}, ...], edges: [{from:'0', to:'1', w:100}, ...] });
//   G.showNode('0', t)            pop a node in (with a ripple)
//   G.drawEdge('01', t, 0.7)      draw an edge (DrawSVG), then its arrowhead and weight pill
//   G.lightNode('1', t, 'accent') / G.unlightNode('1', t)
//   G.trail('01', t, 'mint', 0.8) a glowing stroke drawn along the edge (returns it; G.clearTrails(t) fades all)
//   G.fire('01', t, 'amber')      a comet runs along the edge and its weight flashes (dry runs: "this edge relaxed")
//   G.route(t, ['0','1','3'], {color, leg})  the plane token flies the route, trail drawn behind it
//   G.reject(t, ['0','1','2','3'])           a route drawn in rose, shaken, crossed out
//   G.flag('0', 'SRC', 'accent', t, 'left')  G.badge('1', 'stop 1', t)  G.badgeAt(G.edge('01').mid, 'flight 1', t)
//   G.fade(t, 0.3)  G.bbox(ids, pad)  G.pos(id)  G.makeToken(color)  G.placeToken(id, t)  G.hideToken(t)
// Edge ids default to from+to ('01'), or from+'-'+to when an id is longer than one character.
// bend: >0 bows the edge to the right of its direction of travel, <0 to the left; omit it and the edge bows
// outward from the graph's centre (and two-way pairs separate automatically).
(function () {
  const K = window.K;
  const qp = (P0, C, P1, t) => [(1 - t) * (1 - t) * P0[0] + 2 * (1 - t) * t * C[0] + t * t * P1[0], (1 - t) * (1 - t) * P0[1] + 2 * (1 - t) * t * C[1] + t * t * P1[1]];
  const qd = (P0, C, P1, t) => [2 * (1 - t) * (C[0] - P0[0]) + 2 * t * (P1[0] - C[0]), 2 * (1 - t) * (C[1] - P0[1]) + 2 * t * (P1[1] - C[1])];
  const dist = (a, b) => Math.hypot(a[0] - b[0], a[1] - b[1]);
  const f1 = (v) => v.toFixed(1);

  function trimmed(P0, C, P1, r0, r1) {
    let ta = 0, tb = 1;
    while (ta < 0.5 && dist(qp(P0, C, P1, ta), P0) < r0) ta += 0.002;
    while (tb > 0.5 && dist(qp(P0, C, P1, tb), P1) < r1) tb -= 0.002;
    const A = qp(P0, C, P1, ta), B = qp(P0, C, P1, tb);
    const Cc = [0, 1].map((i) => (1 - ta) * (1 - tb) * P0[i] + ((1 - ta) * tb + ta * (1 - tb)) * C[i] + ta * tb * P1[i]);
    return { d: `M${f1(A[0])},${f1(A[1])} Q${f1(Cc[0])},${f1(Cc[1])} ${f1(B[0])},${f1(B[1])}`, A, B, tan: qd(P0, C, P1, tb) };
  }

  K.graph = function (spec) {
    const R = spec.r ?? 56;
    const G = { nodes: {}, edges: {}, trails: [], r: R, groups: [], extents: [] };
    const grp = (layer) => { const g = K.svg('g', {}, K.layer[layer]); G.groups.push(g); return g; };
    const gEdges = grp('edges'), gTrails = grp('trails'), gNodes = grp('nodes'), gLabels = grp('labels'), gTok = grp('tokens'), gFx = grp('fx');
    G.fxLayer = gFx;
    const P = {};
    spec.nodes.forEach((n) => (P[n.id] = [n.x, n.y]));
    const cx = spec.nodes.reduce((s, n) => s + n.x, 0) / spec.nodes.length;
    const cy = spec.nodes.reduce((s, n) => s + n.y, 0) / spec.nodes.length;
    // a pool of light under the subject: reads as a lit stage, gives the flat graph depth
    const ext = Math.max(...spec.nodes.map((n) => Math.max(Math.abs(n.x - cx), Math.abs(n.y - cy) * 1.6)), 200);
    G.pool = K.svg('ellipse', { cx, cy: cy + 30, rx: ext * 1.55, ry: ext * 1.0, fill: 'url(#pool)' }, K.layer.back);
    K.init(G.pool, { autoAlpha: spec.pool ?? 1 });
    const eid = (a, b) => (String(a).length > 1 || String(b).length > 1 ? `${a}-${b}` : `${a}${b}`);

    // ---------------------------------------------------------------- nodes
    spec.nodes.forEach((n) => {
      const g = K.svg('g', { transform: `translate(${n.x},${n.y})`, 'data-k': `node ${n.id}` }, gNodes);
      const pop = K.svg('g', {}, g);
      const halos = K.svg('g', {}, pop);
      K.svg('ellipse', { cx: 0, cy: R * 0.62, rx: R * 1.05, ry: R * 0.55, fill: 'url(#shadow)' }, pop);
      const orbit = K.svg('circle', { r: R + 13, fill: 'none', stroke: K.C.faint, 'stroke-width': 1.5, 'stroke-dasharray': '3 7' }, pop);
      const disc = K.svg('circle', { r: R, fill: 'url(#node-fill)', stroke: K.C.ink, 'stroke-width': 3.5 }, pop);
      K.svg('circle', { r: R - 6, fill: 'none', stroke: K.U.nodeRim, 'stroke-width': 2 }, pop);
      K.svg('path', { d: `M${-R * 0.62},${-R * 0.5} A${R * 0.8},${R * 0.8} 0 0 1 ${R * 0.35},${-R * 0.72}`, fill: 'none', stroke: K.U.nodeSheen, 'stroke-width': 3, 'stroke-linecap': 'round' }, pop);
      const lbl = K.svg('text', { y: 16, 'text-anchor': 'middle', class: 'node-label' }, pop);
      lbl.textContent = n.label ?? n.id;
      K.init(pop, { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' });
      const spin = (n.x * 7 + n.y * 3) % 360;
      K.everyFrame((t) => orbit.setAttribute('transform', `rotate(${(spin + t * 9).toFixed(2)})`));
      G.nodes[n.id] = { id: n.id, p: [n.x, n.y], g, pop, halos, orbit, disc, lbl, halo: {}, lit: null };
    });
    G.node = (id) => { const n = G.nodes[id]; if (!n) throw new Error(`graph has no node "${id}"`); return n; };
    function haloFor(n, color) {
      const c = K.col(color);
      if (!n.halo[c]) {
        const name = Object.keys(K.C).find((k) => K.C[k] === c) || 'accent';
        n.halo[c] = K.svg('circle', { r: R * 2.4, fill: `url(#glow-${name})` }, n.halos);
        K.init(n.halo[c], { autoAlpha: 0 });
      }
      return n.halo[c];
    }

    // ---------------------------------------------------------------- edges
    const pairs = new Set(spec.edges.map((e) => `${e.from}>${e.to}`));
    const span = Math.max(...spec.nodes.map((n) => Math.hypot(n.x - cx, n.y - cy)), 1);
    spec.edges.forEach((e) => {
      const id = e.id ?? eid(e.from, e.to);
      const P0 = P[e.from], P1 = P[e.to];
      if (!P0 || !P1) throw new Error(`edge ${id}: unknown node ${!P0 ? e.from : e.to}`);
      const L = dist(P0, P1), nx = -(P1[1] - P0[1]) / L, ny = (P1[0] - P0[0]) / L;
      const mx = (P0[0] + P1[0]) / 2, my = (P0[1] + P1[1]) / 2;
      let bend = e.bend;
      if (bend === undefined) {
        if (pairs.has(`${e.to}>${e.from}`)) bend = 0.16;
        else {
          const off = Math.hypot(mx - cx, my - cy);
          bend = off < span * 0.2 ? 0 : 0.17 * Math.sign((mx - cx) * nx + (my - cy) * ny || 1);
        }
      }
      const C = [mx + nx * bend * L, my + ny * bend * L];
      const tq = trimmed(P0, C, P1, R + 8, R + 16);
      const base = K.svg('path', { d: tq.d, class: 'edge-base', 'data-k': `edge ${id}` }, gEdges);
      const ang = (Math.atan2(tq.tan[1], tq.tan[0]) * 180) / Math.PI;
      const headG = K.svg('g', { transform: `translate(${f1(tq.B[0])},${f1(tq.B[1])}) rotate(${ang.toFixed(1)})` }, gEdges);
      const head = K.svg('path', { d: 'M10,0 L-16,-12 L-10,0 L-16,12 Z', class: 'edge-head' }, headG);
      const full = K.svg('path', { d: `M${P0[0]},${P0[1]} Q${f1(C[0])},${f1(C[1])} ${P1[0]},${P1[1]}`, fill: 'none', stroke: 'none' }, gEdges);
      const mid = qp(P0, C, P1, 0.5);
      const pillG = K.svg('g', { transform: `translate(${f1(mid[0])},${f1(mid[1])})` }, gLabels);
      const pill = K.svg('g', { 'data-k': `weight ${id}` }, pillG);
      const label = e.label ?? (e.w !== undefined ? String(e.w) : '');
      // weights are 36 px in world space so they stay >= 28 px on screen at camera scale 0.8 (frame the graph no smaller)
      const pw = Math.max(72, K.textW(label, '700 36px "JetBrains Mono"') + 34);
      const prect = K.svg('rect', { x: -pw / 2, y: -29, width: pw, height: 58, rx: 29, class: 'pill-rect' }, pill);
      const ptxt = K.svg('text', { y: 13, 'text-anchor': 'middle', class: 'pill-text mono' }, pill);
      ptxt.textContent = label;
      K.init(base, { drawSVG: '0%', autoAlpha: 0 });
      K.init(head, { autoAlpha: 0, scale: 0.4, transformOrigin: '50% 50%' });
      K.init(pill, { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' });
      if (!label) pillG.style.display = 'none';
      const so = Math.sign((mid[0] - cx) * nx + (mid[1] - cy) * ny) || 1;
      G.edges[id] = { id, from: e.from, to: e.to, w: e.w, d: tq.d, base, head, headG, full, pill, prect, ptxt, mid, ang, end: tq.B, out: [nx * so, ny * so] };
    });
    G.edge = (id) => { const e = G.edges[id]; if (!e) throw new Error(`graph has no edge "${id}" (edges: ${Object.keys(G.edges).join(' ')})`); return e; };
    /** A world point beside edge id's weight pill, `d` px outward from the graph's centre (for edge labels). */
    G.beside = (id, d = 74) => { const e = G.edge(id); return [e.mid[0] + e.out[0] * d, e.mid[1] + e.out[1] * d]; };
    G.edgeBetween = (a, b) => G.edge(Object.keys(G.edges).find((k) => G.edges[k].from === String(a) && G.edges[k].to === String(b)) || eid(a, b));

    // ---------------------------------------------------------------- appearing
    G.showNode = (id, t) => {
      const n = G.node(id);
      K.pop(n.pop, t, 0.6, 0.2);
      G.ripple(n.p, t + 0.05, K.C.ink);
      return t + 0.6;
    };
    G.showNodes = (ids, t, stagger = 0.12) => { ids.forEach((id, i) => G.showNode(id, t + i * stagger)); return t + ids.length * stagger + 0.5; };
    G.drawEdge = (id, t, d = 0.7) => {
      const e = G.edge(id);
      K.set(e.base, { autoAlpha: 1 }, t);
      K.fromTo(e.base, { drawSVG: '0%' }, { drawSVG: '100%', duration: d, ease: 'power2.inOut' }, t);
      K.fromTo(e.head, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 1, scale: 1, duration: 0.3, ease: 'back.out(2)' }, t + d - 0.08);
      K.pop(e.pill, t + d * 0.45, 0.5);
      return t + d;
    };
    G.drawEdges = (ids, t, stagger = 0.25, d = 0.7) => { ids.forEach((id, i) => G.drawEdge(id, t + i * stagger, d)); return t + (ids.length - 1) * stagger + d; };
    /** Show everything at once (for a graph that should already be there). */
    G.showAll = (t, stagger = 0.06) => {
      const ns = Object.keys(G.nodes), es = Object.keys(G.edges);
      G.showNodes(ns, t, stagger);
      return G.drawEdges(es, t + 0.2, stagger, 0.6);
    };

    // ---------------------------------------------------------------- emphasis
    G.lightNode = (id, t, color = 'accent', d = 0.4) => {
      const n = G.node(id), c = K.col(color);
      if (n.lit === c) return;
      if (n.lit) K.to(haloFor(n, n.lit), { autoAlpha: 0, duration: d }, t);
      K.to(haloFor(n, c), { autoAlpha: 1, duration: d }, t);
      K.to(n.disc, { stroke: K.vis(c), duration: d }, t);
      n.lit = c;
    };
    G.unlightNode = (id, t, d = 0.4) => {
      const n = G.node(id);
      if (!n.lit) return;
      K.to(haloFor(n, n.lit), { autoAlpha: 0, duration: d }, t);
      K.to(n.disc, { stroke: K.C.ink, duration: d }, t);
      n.lit = null;
    };
    G.ripple = (p, t, color = K.C.accent) => {
      const c = K.svg('circle', { cx: p[0], cy: p[1], r: R, fill: 'none', stroke: K.vis(color), 'stroke-width': 3 }, gFx);
      K.init(c, { autoAlpha: 0, scale: 1, transformOrigin: '50% 50%' });
      K.fromTo(c, { autoAlpha: 0.8, scale: 1 }, { autoAlpha: 0, scale: 1.8, duration: 0.8, ease: 'power2.out' }, t);
    };
    G.trail = (id, t, color = 'accent', d = 0.8) => {
      const e = G.edge(id), c = K.vis(color);   // a fill too close to a light ground is lifted to 3:1 (themes only)
      const g = K.svg('g', {}, gTrails);
      const glow = K.svg('path', { d: e.d, class: 'trail-glow', stroke: c }, g);
      const core = K.svg('path', { d: e.d, class: 'trail-core', stroke: c }, g);
      const hg = K.svg('g', { transform: e.headG.getAttribute('transform') }, g);
      const head = K.svg('path', { d: 'M10,0 L-16,-12 L-10,0 L-16,12 Z', fill: c }, hg);
      K.init([glow, core], { drawSVG: '0%', autoAlpha: 0 });
      K.init(head, { autoAlpha: 0 });
      K.set([glow, core], { autoAlpha: 1 }, t);
      K.fromTo([glow, core], { drawSVG: '0%' }, { drawSVG: '100%', duration: d, ease: d > 0.6 ? 'power2.inOut' : 'power1.inOut' }, t);
      K.to(head, { autoAlpha: 1, duration: 0.15 }, t + d - 0.1);
      const tr = { id, g, glow, core, head, color: c, t, cleared: false };
      G.trails.push(tr);
      return tr;
    };
    /** Fade every trail drawn so far (or just `list`). */
    G.clearTrails = (t, d = 0.4, list = null) => {
      for (const tr of list || G.trails) if (!tr.cleared && tr.t < t) { K.to(tr.g, { autoAlpha: 0, duration: d }, t); tr.cleared = true; }
    };
    G.fire = (id, t, color = 'amber', d = 0.7) => {
      const e = G.edge(id), c = K.vis(color);
      const comet = K.svg('path', { d: e.d, class: 'comet', stroke: c }, gTrails);
      K.init(comet, { drawSVG: '0% 0%', autoAlpha: 0 });
      K.set(comet, { autoAlpha: 1 }, t);
      K.fromTo(comet, { drawSVG: '0% 0%' }, { drawSVG: '0% 38%', duration: d * 0.3, ease: 'power1.in' }, t);
      K.fromTo(comet, { drawSVG: '0% 38%' }, { drawSVG: '100% 100%', duration: d * 0.7, ease: 'power2.out' }, t + d * 0.3);
      K.set(comet, { autoAlpha: 0 }, t + d);
      G.flashWeight(id, t + d * 0.2, c);
      return t + d;
    };
    G.flashWeight = (id, t, color = 'amber') => {
      const e = G.edge(id);
      K.to(e.prect, { stroke: K.vis(color), duration: 0.12 }, t);
      K.pulse(e.pill, t, 1.3, 0.5);
      K.to(e.prect, { stroke: K.C.line, duration: 0.35 }, t + 0.35);
    };

    // ---------------------------------------------------------------- the token (paper plane) and routes
    G.makeToken = (color = 'accent', scale = 1.15) => {
      const g = K.svg('g', { 'data-k': 'token' }, gTok);
      const name = Object.keys(K.C).find((k) => K.C[k] === K.col(color)) || 'accent';
      K.svg('circle', { r: 64, fill: `url(#glow-${name})` }, g);
      const b = K.svg('g', { transform: `scale(${scale})` }, g);
      K.svg('path', { d: 'M34,0 L-30,-25 L-14,0 Z', fill: K.col(color), stroke: K.C.black, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, b);
      K.svg('path', { d: 'M34,0 L-14,0 L-30,25 Z', fill: shade(K.col(color), -0.28), stroke: K.C.black, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, b);
      K.svg('path', { d: 'M34,0 L-20,7 L-14,0 Z', fill: shade(K.col(color), 0.35), stroke: K.C.black, 'stroke-width': 1.5, 'stroke-linejoin': 'round' }, b);
      K.init(g, { autoAlpha: 0, x: 0, y: 0, rotation: 0 });
      return { g, visible: false, at: null };
    };
    G.token = G.makeToken();
    /** Place the token on a node at time t (pointing along `towards` if given). */
    G.placeToken = (id, t, towards = null, tok = G.token) => {
      const p = G.node(id).p;
      const rot = towards ? (Math.atan2(G.node(towards).p[1] - p[1], G.node(towards).p[0] - p[0]) * 180) / Math.PI : 0;
      K.set(tok.g, { x: p[0], y: p[1], rotation: rot }, t);
      if (!tok.visible) { K.to(tok.g, { autoAlpha: 1, duration: 0.3 }, t); tok.visible = true; }
      tok.at = id;
    };
    G.hideToken = (t, tok = G.token) => { if (tok.visible) { K.to(tok.g, { autoAlpha: 0, duration: 0.3 }, t); tok.visible = false; } };
    /**
     * Fly the token along a route of node ids. Returns {end, arrive: [time at each node after the first], trails}.
     * o: {color, leg (s per flight), hold (pause on each node), trail (true), token}
     */
    G.route = (t, path, o = {}) => {
      const tok = o.token || G.token, leg = o.leg ?? 0.9, hold = o.hold ?? 0.15, color = o.color ?? 'accent';
      const edges = path.slice(1).map((b, i) => G.edgeBetween(path[i], b));
      if (tok.at !== String(path[0]) || !tok.visible) G.placeToken(path[0], t, path[1], tok);
      const arrive = [], trails = [];
      let tt = t + 0.05;
      edges.forEach((e) => {
        K.to(tok.g, { motionPath: { path: e.full, autoRotate: true }, duration: leg, ease: 'power2.inOut' }, tt);
        if (o.trail !== false) trails.push(G.trail(e.id, tt, color, leg));
        arrive.push(tt + leg);
        G.ripple(G.node(e.to).p, tt + leg - 0.05, K.col(color));
        tt += leg + hold;
      });
      tok.at = String(path[path.length - 1]);
      return { end: tt - hold, arrive, trails };
    };
    /** Show a route as illegal: drawn in rose, shaken, crossed out. Returns the time the cross lands. */
    G.reject = (t, path, o = {}) => {
      const leg = o.leg ?? 0.45;
      const trs = path.slice(1).map((b, i) => G.trail(G.edgeBetween(path[i], b).id, t + i * leg, 'rose', leg));
      const t1 = t + trs.length * leg + 0.1;
      trs.forEach((tr) => {
        K.to(tr.g, { x: -9, duration: 0.06, ease: 'none' }, t1);
        K.to(tr.g, { x: 9, duration: 0.08, ease: 'none' }, t1 + 0.06);
        K.to(tr.g, { x: -6, duration: 0.08, ease: 'none' }, t1 + 0.14);
        K.to(tr.g, { x: 0, duration: 0.08, ease: 'none' }, t1 + 0.22);
        K.to(tr.g, { autoAlpha: 0.35, duration: 0.4 }, t1 + 0.35);
      });
      const mid = G.edgeBetween(path[Math.floor((path.length - 1) / 2)], path[Math.floor((path.length - 1) / 2) + 1]).mid;
      const x = K.svg('g', { transform: `translate(${f1(mid[0])},${f1(mid[1])})` }, gFx);
      const a = K.svg('path', { d: 'M-30,-30 L30,30', class: 'cross' }, x), b = K.svg('path', { d: 'M30,-30 L-30,30', class: 'cross' }, x);
      K.init([a, b], { drawSVG: '0%', autoAlpha: 0 });
      K.set([a, b], { autoAlpha: 1 }, t1 + 0.2);
      K.fromTo(a, { drawSVG: '0%' }, { drawSVG: '100%', duration: 0.18, ease: 'power2.in' }, t1 + 0.2);
      K.fromTo(b, { drawSVG: '0%' }, { drawSVG: '100%', duration: 0.18, ease: 'power2.in' }, t1 + 0.38);
      G.trails.push({ g: x, t: t1, cleared: false });
      return t1 + 0.56;
    };

    // ---------------------------------------------------------------- labels on the subject
    /** A coloured flag pill beside a node, joined to it (SRC / DST). side: left | right | top | bottom. */
    G.flag = (id, text, color, t, side = 'left') => {
      const n = G.node(id), c = K.col(color);
      const w = K.textW(text, '800 36px Inter') + 40, h = 58, gap = R + 16, len = 28;   // 36 px: >= 28 px on screen at scale 0.8
      const dir = { left: [-1, 0], right: [1, 0], top: [0, -1], bottom: [0, 1] }[side];
      const ax = n.p[0] + dir[0] * gap, ay = n.p[1] + dir[1] * gap;
      const bx = ax + dir[0] * len, by = ay + dir[1] * len;
      const px = side === 'left' ? bx - w : side === 'right' ? bx : bx - w / 2;
      const py = side === 'top' ? by - h : side === 'bottom' ? by : by - h / 2;
      const g = K.svg('g', { 'data-k': `flag ${text}` }, gLabels);
      K.svg('line', { x1: ax, y1: ay, x2: bx, y2: by, stroke: K.vis(c), 'stroke-width': 4, 'stroke-linecap': 'round' }, g);
      K.svg('rect', { x: px, y: py, width: w, height: h, rx: 14, fill: c }, g);
      const tx = K.svg('text', { x: px + w / 2, y: py + h / 2 + 13, 'text-anchor': 'middle', class: 'flag-text' }, g);
      tx.style.fill = K.on(c);   // the label on the flag's fill
      tx.textContent = text;
      K.init(g, { autoAlpha: 0, scale: 0.4, svgOrigin: `${ax} ${ay}` });
      K.to(g, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2)' }, t);
      G.extents.push({ x: Math.min(px, ax) - 12, y: py - 12, w: Math.abs(px - ax) + w + 24, h: h + 24 });
      return g;
    };
    /** A small pill near a node (default: above it). Returns the element; hide it with K.fadeOut(el, t). */
    G.badge = (id, text, t, o = {}) => {
      const n = G.node(id);
      return G.badgeAt([n.p[0] + (o.dx ?? 0), n.p[1] + (o.dy ?? -(R + 46))], text, t, o);
    };
    /** The same pill at a world point (e.g. G.edge('01').mid for "flight 1"). */
    G.badgeAt = (p, text, t, o = {}) => {
      const c = K.ink(o.color ?? 'amber');   // text and a thin outline: the hue's ink
      const w = K.textW(text, '700 32px "JetBrains Mono"') + 34;   // 32 px world: >= 26 px on screen at scale 0.8
      const g = K.svg('g', { transform: `translate(${f1(p[0])},${f1(p[1])})`, 'data-k': `badge ${text}` }, gLabels);
      const inner = K.svg('g', {}, g);
      K.svg('rect', { x: -w / 2, y: -26, width: w, height: 52, rx: 12, fill: K.C.panel, stroke: c, 'stroke-width': 2.5 }, inner);
      const tx = K.svg('text', { y: 11.5, 'text-anchor': 'middle', class: 'badge-text mono', fill: c }, inner);
      tx.textContent = text;
      K.init(inner, { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' });
      K.pop(inner, t, 0.5);
      if (o.until !== undefined) K.to(inner, { autoAlpha: 0, duration: 0.3 }, o.until);
      return inner;
    };

    // ---------------------------------------------------------------- whole-graph helpers
    G.fade = (t, opacity, d = 0.6) => K.to(G.groups, { opacity, duration: d, ease: 'sine.inOut' }, t);
    /**
     * World rect around the given nodes (default: all nodes plus the flags created so far), padded for labels.
     * Call it after G.flag(...) so camera framing keeps SRC/DST on screen.
     */
    G.bbox = (ids = null, pad = R + 40) => {
      const rs = (ids || Object.keys(G.nodes)).map((id) => { const p = G.node(id).p; return { x: p[0] - pad, y: p[1] - pad, w: 2 * pad, h: 2 * pad }; });
      if (!ids) rs.push(...G.extents);
      const x0 = Math.min(...rs.map((r) => r.x)), x1 = Math.max(...rs.map((r) => r.x + r.w));
      const y0 = Math.min(...rs.map((r) => r.y)), y1 = Math.max(...rs.map((r) => r.y + r.h));
      return { x: x0, y: y0, w: x1 - x0, h: y1 - y0 };
    };
    G.pos = (id) => G.node(id).p;
    return G;
  };

  function shade(hex, f) {
    const n = parseInt(hex.slice(1), 16), r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    const m = (c) => Math.round(f < 0 ? c * (1 + f) : c + (255 - c) * f);
    return `rgb(${m(r)},${m(g)},${m(b)})`;
  }
  K.shade = shade;
})();
