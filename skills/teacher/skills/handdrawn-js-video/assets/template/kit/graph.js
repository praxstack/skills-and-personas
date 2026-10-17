// kit/graph.js: the persistent subject (a directed weighted graph) and the travelling token (a paper plane).
// The graph is declared once and given events keyed to line ids; it draws itself at any t from those events.
//
//   const g = graph({ nodes: [{x:-400,y:0}, ...], edges: [[0,1,100], ...] });   // or layout: 'circle' | 'layers'
//   g.place([[0, 1180, 470, 1], [L.b1.start, 1500, 420, 0.7]]);                // where it sits in the world, over time
//   g.showNodes(vAt('p1', 0.1), 0.15);  g.showEdges(vAt('p1', 0.5), 0.5);      // pop nodes, stroke on edges
//   g.hl(g.route([0, 1, 3]), { at, dur, color: S.accent });  g.fire(e, { at });  g.mark(0, 'src', { at });
'use strict';
function layoutGraph(n, edges, kind = 'circle', o = {}) {
  if (kind === 'circle') { const R = o.radius ?? 320; return Array.from({ length: n }, (_, i) => { const a = -Math.PI / 2 + (i / n) * TAU; return { x: Math.cos(a) * R * 1.25, y: Math.sin(a) * R }; }); }
  if (kind === 'layers') { // BFS levels from o.src along edge direction: src on the left, levels to the right
    const lvl = Array(n).fill(-1), q = [o.src ?? 0]; lvl[o.src ?? 0] = 0;
    while (q.length) { const u = q.shift(); for (const [a, b] of edges) if (a === u && lvl[b] < 0) { lvl[b] = lvl[u] + 1; q.push(b); } }
    const maxL = Math.max(0, ...lvl); lvl.forEach((l, i) => { if (l < 0) lvl[i] = maxL + 1; });
    const cols = {}; lvl.forEach((l, i) => (cols[l] = cols[l] || []).push(i));
    const nL = Math.max(...lvl) + 1, gx = o.gapX ?? 300, gy = o.gapY ?? 220, pos = [];
    for (const [l, ids] of Object.entries(cols)) ids.forEach((i, k) => { pos[i] = { x: (l - (nL - 1) / 2) * gx, y: (k - (ids.length - 1) / 2) * gy }; });
    return pos;
  }
  throw new Error('layout: circle | layers (or give nodes with x, y)');
}

function graph(spec) {
  const edges = spec.edges.map((e) => ({ u: e[0], v: e[1], w: e[2] }));
  const n = spec.nodes ? spec.nodes.length : spec.n;
  const pos = spec.nodes && spec.nodes[0].x != null ? spec.nodes.map((q) => ({ x: q.x, y: q.y })) : layoutGraph(n, spec.edges, spec.layout, spec);
  const nodes = pos.map((p, i) => ({ ...p, label: (spec.nodes && spec.nodes[i].label) ?? String(i), color: (spec.nodes && spec.nodes[i].color) || S.node[i % S.node.length], ink: S.nodeInk[i % S.node.length] }));
  const R = spec.r ?? 46, directed = spec.directed !== false;
  const cx0 = pos.reduce((a, p) => a + p.x, 0) / n, cy0 = pos.reduce((a, p) => a + p.y, 0) / n;
  edges.forEach((e, k) => {
    const back = edges.some((f) => f.u === e.v && f.v === e.u);
    if (spec.edges[k][3] != null) { e.bend = spec.edges[k][3]; return; }        // [u, v, w, bend] overrides
    if (back) { e.bend = 0.2; return; }                                          // antiparallel pairs split apart
    const a = pos[e.u], b = pos[e.v], l = Math.hypot(b.x - a.x, b.y - a.y) || 1, nx = -(b.y - a.y) / l, ny = (b.x - a.x) / l;
    const side = ((a.x + b.x) / 2 - cx0) * nx + ((a.y + b.y) / 2 - cy0) * ny;    // > 0: the normal points away from the centre
    const mag = spec.bend ?? 0.1;
    e.bend = Math.abs(side) < 0.12 * l ? mag * 0.5 : side > 0 ? mag : -mag;
  });
  const ev = { nodeIn: Array(n).fill(Infinity), edgeIn: edges.map(() => ({ t: Infinity, d: 0.6 })), tagIn: edges.map(() => Infinity), marks: [], rings: [], glows: [], hls: [], fires: [], dims: [], swaps: [] };
  let place = [[0, spec.x ?? W / 2, spec.y ?? H / 2, spec.s ?? 1]];

  const G = { nodes, edges, R, ev, center: [cx0, cy0] };
  G.place = (keys) => { place = keys.slice().sort((a, b) => a[0] - b[0]); return G; };
  G.xf = (t) => { const [x, y, s] = track(t, place, Ease.inOut); return { x, y, s }; };
  // node centre in the world (paper nodes float a little)
  G.nodeXY = (i, t, xf = G.xf(t)) => { const b = (spec.float ?? S.float ?? 3) * Math.sin(t * 0.9 + i * 1.7); return [xf.x + nodes[i].x * xf.s, xf.y + (nodes[i].y + b) * xf.s]; };
  G.edgePts = (e, t, xf = G.xf(t)) => {
    const E = edges[e], a = G.nodeXY(E.u, t, xf), b = G.nodeXY(E.v, t, xf), s = xf.s;
    let dx = b[0] - a[0], dy = b[1] - a[1]; const l = Math.hypot(dx, dy) || 1; dx /= l; dy /= l;
    const mx = (a[0] + b[0]) / 2 - dy * l * E.bend, my = (a[1] + b[1]) / 2 + dx * l * E.bend;
    // trim to the node rims along the curve's own end directions
    const t0 = norm([mx - a[0], my - a[1]]), t1 = norm([b[0] - mx, b[1] - my]);
    const p0 = [a[0] + t0[0] * (R + 8) * s, a[1] + t0[1] * (R + 8) * s], p1 = [b[0] - t1[0] * (R + (directed ? 10 : 8)) * s, b[1] - t1[1] * (R + (directed ? 10 : 8)) * s];
    return quadPts(p0, [mx, my], p1, 28);
  };
  const norm = (v) => { const l = Math.hypot(v[0], v[1]) || 1; return [v[0] / l, v[1] / l]; };
  // weight tags shrink with the map only down to S.size.tagMin, so their numbers stay at least 30 px on screen
  const tagK = (s) => Math.max(s, S.size.tagMin ?? 0.9), tagSize = spec.tagSize ?? S.size.tag;
  G.tagXY = (e, t, xf = G.xf(t)) => {
    const p = G.edgePts(e, t, xf), [x, y, a] = polyAt(p, 0.5), side = edges[e].bend >= 0 ? -1 : 1, k = tagK(xf.s);
    const hw = (measureText(String(edges[e].w ?? ''), 'hand', tagSize) + 44) / 2, d = (14 + hw * Math.abs(Math.sin(a)) + tagSize * 0.62 * Math.abs(Math.cos(a))) * k;
    return [x + Math.sin(a) * d * side, y - Math.cos(a) * d * side];
  };
  G.edgeIndex = (u, v) => edges.findIndex((e) => e.u === u && e.v === v);
  G.route = (ns) => ns.slice(1).map((v, i) => { const e = G.edgeIndex(ns[i], v); if (e < 0) throw new Error(`no edge ${ns[i]}->${v}`); return e; });

  // ---- events (all times in seconds; key them to line ids)
  G.showNodes = (t0, stagger = 0.15, ids = nodes.map((_, i) => i)) => { ids.forEach((i, k) => (ev.nodeIn[i] = t0 + k * stagger)); return G; };
  G.showEdges = (t0, stagger = 0.4, ids = edges.map((_, i) => i), d = 0.6) => { ids.forEach((e, k) => { ev.edgeIn[e] = { t: t0 + k * stagger, d }; ev.tagIn[e] = t0 + k * stagger + d * 0.8; }); return G; };
  G.showEdge = (e, t0, d = 0.6, tagAt = t0 + d * 0.8) => { ev.edgeIn[e] = { t: t0, d }; ev.tagIn[e] = tagAt; return G; };
  G.mark = (i, text, o = {}) => { ev.marks.push({ i, text, at: o.at ?? 0, until: o.until ?? Infinity, color: o.color || S.ink, side: o.side || 'down', size: o.size || S.size.mark, font: o.font || 'hand', dx: o.dx || 0, dy: o.dy || 0 }); return G; };
  G.ring = (i, o = {}) => { ev.rings.push({ i, at: o.at ?? 0, until: o.until ?? Infinity, color: o.color || S.accent, dash: o.dash, w: o.w ?? 5 }); return G; };
  G.glow = (i, o = {}) => { ev.glows.push({ i, at: o.at ?? 0, until: o.until ?? Infinity, color: o.color || S.glow }); return G; };
  // highlight edges: drawn on in order (dur per edge), coloured, glowing; dash for ghost/illegal routes
  G.hl = (es, o = {}) => { [].concat(es).forEach((e, k) => ev.hls.push({ e, at: (o.at ?? 0) + k * (o.dur ?? 0.6) * (o.seq === false ? 0 : 1), dur: o.dur ?? 0.6, until: o.until ?? Infinity, color: o.color || S.accent, dash: o.dash, w: o.w ?? 9, glow: o.glow ?? true })); return G; };
  G.fire = (es, o = {}) => { [].concat(es).forEach((e, k) => ev.fires.push({ e, at: (o.at ?? 0) + k * (o.gap ?? 0), dur: o.dur ?? 0.55, color: o.color || S.gold })); return G; };
  G.dim = (o = {}) => { ev.dims.push({ at: o.at ?? 0, until: o.until ?? Infinity, alpha: o.alpha ?? 0.3, edges: o.edges ? new Set(o.edges) : null, nodes: o.nodes ? new Set(o.nodes) : null }); return G; };
  G.relabel = (i, text, at) => { ev.swaps.push({ i, text, at }); return G; };

  const dimOf = (t, kind, id) => { let a = 1; for (const d of ev.dims) { const set = kind === 'e' ? d.edges : d.nodes; if (set && set.has(id)) continue; const k = env(t, d.at, d.until, 0.4, 0.4); a = Math.min(a, 1 - (1 - d.alpha) * k); } return a; };

  world(spec.z ?? 30, (ctx, t) => {
    const xf = G.xf(t), s = xf.s, alpha = spec.alpha ? val(spec.alpha, t) : 1;
    if (alpha <= 0.003) return;
    ctx.save(); ctx.globalAlpha *= alpha;
    // glows behind nodes
    for (const gl of ev.glows) { const k = env(t, gl.at, gl.until, 0.3, 0.4); if (k <= 0) continue; const [x, y] = G.nodeXY(gl.i, t, xf), r = R * s * 2.4; if (STYLE.glow) { STYLE.glow(ctx, x, y, r, gl.color, k, t, gl.at); continue; } const gr = ctx.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, gl.color); gr.addColorStop(1, 'rgba(0,0,0,0)'); ctx.save(); ctx.globalAlpha *= k * (0.8 + 0.2 * Math.sin(t * 6)); ctx.fillStyle = gr; ctx.fillRect(x - r, y - r, 2 * r, 2 * r); ctx.restore(); }
    // edges: ink line drawn on, arrowhead only once fully drawn
    edges.forEach((E, e) => {
      const { t: t0, d } = ev.edgeIn[e], pr = P(t, t0, d, Ease.inOut); if (pr <= 0) return;
      const p = G.edgePts(e, t, xf), a = dimOf(t, 'e', e);
      if (directed) inkArrow(ctx, p, { prog: pr, w: S.stroke.w * Math.max(s, 0.7), alpha: a, seed: 'e' + e, t, tip: true, head: 17 * Math.max(s, 0.7) });
      else inkLine(ctx, p, { prog: pr, w: S.stroke.w * Math.max(s, 0.7), alpha: a, seed: 'e' + e, t, tip: true });
    });
    // highlights
    for (const h of ev.hls) {
      const pr = P(t, h.at, h.dur, Ease.inOut), a = 1 - P(t, h.until, 0.35, Ease.in); if (pr <= 0 || a <= 0) continue;
      const p = G.edgePts(h.e, t, xf), ww = h.w * Math.max(s, 0.7);
      inkArrow(ctx, p, { prog: pr, color: h.color, w: ww, alpha: a * dimOf(t, 'e', h.e), seed: 'h' + h.e + h.at, t, glow: h.glow ? hexA(h.color, 0.55) : null, dash: h.dash ? [ww * 1.8, ww * 1.5] : null, head: 22 * Math.max(s, 0.7), tip: true });
    }
    // fires: a bright pulse runs along the edge
    for (const f of ev.fires) {
      const u = (t - f.at) / f.dur; if (u < 0 || u > 1.25) continue;
      const p = G.edgePts(f.e, t, xf), head = clamp(u), tail = clamp(u - 0.35);
      inkLine(ctx, p, { from: tail, prog: head, color: f.color, w: 10 * Math.max(s, 0.7), glow: f.color, seed: 'f' + f.e, passes: 1, alpha: 1 - clamp((u - 1) / 0.25) });
      if (u <= 1) { const [x, y] = polyAt(p, head); ctx.save(); ctx.fillStyle = S.spark; glowOrShadow(ctx, f.color, 18); ctx.beginPath(); ctx.arc(x, y, 7 * Math.max(s, 0.7), 0, TAU); ctx.fill(); ctx.restore(); }
    }
    // weight tags
    edges.forEach((E, e) => {
      if (E.w == null || spec.weights === false) return;
      const k = popEnv(t, ev.tagIn[e], Infinity, 0.45); if (k.s <= 0) return;
      const [x, y] = G.tagXY(e, t, xf), ts = tagK(s);
      blit(ctx, tagSprite(String(E.w), { size: tagSize }), x, y, { sx: k.sx * ts, sy: k.sy * ts, rot: k.rot, alpha: dimOf(t, 'e', e), t, jit: 'tag' + e });
    });
    // nodes
    nodes.forEach((N, i) => {
      const k = pop(t, ev.nodeIn[i], 0.55); if (k.s <= 0) return;
      let lab = N.label; for (const sw of ev.swaps) if (sw.i === i && t >= sw.at) lab = sw.text;
      const [x, y] = G.nodeXY(i, t, xf);
      if (STYLE.node) { STYLE.node(ctx, x, y, R * s, lab, N.color, t, ev.nodeIn[i], dimOf(t, 'n', i)); return; } // drawn on live
      blit(ctx, discSprite(lab, N.color, N.ink, R), x, y, { sx: k.sx * s, sy: k.sy * s, rot: k.rot, alpha: dimOf(t, 'n', i), t, jit: 'n' + i });
    });
    for (const r of ev.rings) {
      const pr = P(t, r.at, 0.5, Ease.inOut), a = 1 - P(t, r.until, 0.3); if (pr <= 0 || a <= 0) continue;
      const [x, y] = G.nodeXY(r.i, t, xf), rr = (R + 16) * s;
      inkEllipse(ctx, x, y, rr, rr, { color: r.color, w: r.w, prog: pr, alpha: a, seed: 'r' + r.i + r.at, t, dash: r.dash ? [10, 9] : null, tip: true });
    }
    for (const m of ev.marks) {
      const a = env(t, m.at, m.until, 0.3, 0.25); if (a <= 0) continue;
      const [x, y] = G.nodeXY(m.i, t, xf), off = (R + 26) * s, sz = m.size * Math.max(s, S.size.markMin ?? 0.9);
      const [px, py, al] = m.side === 'up' ? [x, y - off - sz * 0.3, 'center'] : m.side === 'left' ? [x - off, y + sz * 0.3, 'right'] : m.side === 'right' ? [x + off, y + sz * 0.3, 'left'] : [x, y + off + sz * 0.85, 'center'];
      // paper style: the mark is lettered on a torn paper slip, so a short word like "src" keeps 4.5:1 on any paper
      const slip = S.kind === 'paper' && m.slip !== false;
      if (slip) {
        const tw = measureText(m.text, m.font, m.size), k = sz / m.size, cxs = al === 'center' ? 0 : al === 'right' ? -tw * k / 2 : tw * k / 2, pp = pop(t, m.at, 0.45);
        blit(ctx, slipSprite(tw + m.size * 0.55, m.size * 1.12, hashStr(m.text)), px + m.dx + cxs, py + m.dy - sz * 0.3, { sx: k * pp.sx, sy: k * pp.sy, rot: pp.rot, alpha: a, t, jit: 'mk' + m.i + m.text });
      }
      drawText(ctx, m.text, px + m.dx, py + m.dy, { font: m.font, size: sz, color: m.color, align: al, write: P(t, m.at + 0.1, 0.45, Ease.lin), alpha: a, halo: slip ? null : S.halo, haloW: 8, t, boil: 0.5 });
    }
    ctx.restore();
  });
  return G;
}

// ------------------------------------------------------------------ the travelling token
// const plane = token(g);  plane.fly([0, 1, 3], { at, legDur: 1.2, pause: 0.35, trail: S.accent, cost: true });
// plane.park(0, { at, until, side: 'left' });   ghost routes: { ghost: 0.5, trail: S.bad, dash: true }
// fly() options: legDur, pause (at each stop), trail (colour), until (trail stays), hold (plane stays landed until),
//   cost (running total tag), costPrefix, stopLabel ('stop' -> 'stop 1' at each intermediate node), mascot, expr
function token(G, o = {}) {
  const flights = [], parks = [];
  const T = {
    fly(route, f = {}) {
      const es = G.route(route), legDur = f.legDur ?? 1.1, pause = f.pause ?? 0.3, legs = [];
      let t0 = f.at;
      es.forEach((e) => { legs.push({ e, t0, t1: t0 + legDur }); t0 += legDur + pause; });
      flights.push({ route, legs, at: f.at, end: t0 - pause, hold: f.hold ?? (t0 - pause + 0.25), until: f.until ?? Infinity, trail: f.trail, dash: f.dash, ghost: f.ghost ?? 1, cost: f.cost, costPrefix: f.costPrefix ?? '', mascot: f.mascot ?? (o.mascot ?? S.mascot), stopLabel: f.stopLabel, expr: f.expr });
      return legs[legs.length - 1].t1; // when it lands
    },
    park(i, p = {}) { parks.push({ i, at: p.at ?? 0, until: p.until ?? Infinity, side: p.side || 'left', mascot: p.mascot ?? (o.mascot ?? S.mascot) }); return T; },
    // where the token is at t (null if hidden), for following it with labels
    poseAt(t) { return pose(t); },
  };
  function legPose(t, leg, xf) { const p = G.edgePts(leg.e, t, xf), u = Ease.inOut(clamp((t - leg.t0) / (leg.t1 - leg.t0))); const [x, y, a] = polyAt(p, u); return { x, y, a, u }; }
  function pose(t) {
    const xf = G.xf(t);
    for (const f of flights) {
      if (t < f.at - 0.3 || t > Math.max(f.end, f.hold) + 0.35) continue;
      for (let j = 0; j < f.legs.length; j++) {
        const lg = f.legs[j], nx = f.legs[j + 1];
        if (t <= lg.t1 || (nx && t < nx.t0)) { const q = legPose(Math.min(t, lg.t1), lg, xf); return { ...q, f, j, landed: t > lg.t1, s: xf.s }; }
      }
      const lg = f.legs[f.legs.length - 1], q = legPose(lg.t1, lg, xf);
      return { ...q, f, j: f.legs.length - 1, landed: true, s: xf.s, done: true };
    }
    for (const p of parks) if (t >= p.at && t < p.until) {
      const [x, y] = G.nodeXY(p.i, t, xf), d = (G.R + 52) * xf.s, up = p.side === 'up';
      return { x: up ? x - 6 * xf.s : x + (p.side === 'left' ? -d : d), y: up ? y - (G.R + 58) * xf.s : y - 18 * xf.s, a: up ? -0.12 : p.side === 'left' ? -0.25 : Math.PI + 0.25, s: xf.s, park: p, parkA: env(t, p.at, p.until, 0.35, 0.25) };
    }
    return null;
  }
  world(o.z ?? 50, (ctx, t) => {
    const xf = G.xf(t);
    // trails (persist until `until`)
    for (const f of flights) {
      if (!f.trail || t < f.at || t > f.until + 0.4) continue;
      const a = 1 - P(t, f.until, 0.4);
      for (const lg of f.legs) {
        const u = Ease.inOut(clamp((t - lg.t0) / (lg.t1 - lg.t0))); if (u <= 0) continue;
        const p = G.edgePts(lg.e, t, xf), w = 8 * Math.max(xf.s, 0.7);
        inkLine(ctx, p, { prog: u, color: f.trail, w, alpha: a * f.ghost, seed: 'tr' + lg.e + f.at, t, glow: f.dash ? null : hexA(f.trail, 0.5), dash: f.dash ? [w * 1.8, w * 1.5] : null });
        if (u >= 1) { const [x, y, an] = polyAt(p, 1); arrowHead(ctx, x, y, an, 20 * Math.max(xf.s, 0.7), { color: f.trail, w, alpha: a * f.ghost, t, seed: 'trh' + lg.e }); }
      }
      // stop labels at the intermediate nodes
      if (f.stopLabel) f.legs.slice(0, -1).forEach((lg, j) => {
        const k = env(t, lg.t1 + 0.05, f.until, 0.3, 0.3); if (k <= 0) return;
        const v = G.edges[lg.e].v, [x, y] = G.nodeXY(v, t, xf);
        drawText(ctx, `${f.stopLabel} ${j + 1}`, x, y - (G.R + 22) * xf.s, { size: S.size.label * Math.max(xf.s, 0.9), color: f.trail || S.ink, align: 'center', alpha: k * f.ghost, write: P(t, lg.t1 + 0.05, 0.4, Ease.lin), halo: S.kind === 'paper' ? S.halo : null, haloW: 8 });
      });
    }
    const q = pose(t); if (!q) return;
    const s = 1.0 * Math.max(q.s, 0.55);
    if (q.park) { drawPlane(ctx, q.x, q.y + Math.sin(t * 2.4) * 3, q.a + Math.sin(t * 1.7) * 0.04, s * q.parkA, { t, pip: q.park.mascot, expr: 'happy' }); return; }
    const f = q.f, fade = env(t, f.at - 0.3, Math.max(f.end, f.hold), 0.3, 0.3);
    const bob = q.landed ? Math.sin(t * 5) * 2 : 0;
    drawPlane(ctx, q.x, q.y - 10 * s + bob, q.landed ? q.a * 0.3 : q.a, s, { t, pip: f.mascot, alpha: fade * f.ghost, expr: f.expr || (q.done ? 'cheer' : 'happy'), noseAt: true });
    // running cost counter riding with the plane
    if (f.cost) {
      let sum = 0, prev = 0, tick = -1;
      f.legs.forEach((lg) => { if (t >= lg.t1) { prev = sum; sum += G.edges[lg.e].w; tick = lg.t1; } });
      const shown = tick < 0 ? 0 : Math.round(lerp(prev, sum, P(t, tick, 0.35, Ease.out)));
      const pp = tick < 0 ? { sx: 1, sy: 1 } : pop(t, tick, 0.45);
      // rides on the inner side of the route (weight tags sit on the outer side); after the last landing it moves
      // to the outside of the destination
      const lgq = f.legs[q.j], E = G.edges[lgq.e], mp = polyAt(G.edgePts(lgq.e, t, xf), 0.5);
      const wc = [xf.x + G.center[0] * xf.s, xf.y + G.center[1] * xf.s], an = q.landed ? polyAt(G.edgePts(lgq.e, t, xf), 1)[2] : q.a;
      const sg = Math.sign((-Math.sin(mp[2])) * (wc[0] - mp[0]) + Math.cos(mp[2]) * (wc[1] - mp[1])) || 1;
      const off = 80 * Math.max(xf.s, 0.7);
      let cx = q.x - Math.sin(an) * sg * off - Math.cos(an) * 30 * s, cy = q.y + Math.cos(an) * sg * off + 8 * s;
      if (q.done) {
        const lg = f.legs[f.legs.length - 1], v = G.edges[lg.e].v, [nx, ny] = G.nodeXY(v, t, xf), k = P(t, lg.t1 + 0.1, 0.45);
        let ox = G.nodes[v].x - G.center[0], oy = G.nodes[v].y - G.center[1]; const ol = Math.hypot(ox, oy) || 1; ox /= ol; oy = oy / ol - 0.7;
        const l2 = Math.hypot(ox, oy) || 1, d = (G.R + 95) * Math.max(xf.s, 0.7);
        // swing around the node (polar interpolation) so the tag never slides across it
        const a0 = Math.atan2(cy - ny, cx - nx), r0 = Math.hypot(cx - nx, cy - ny), a1 = Math.atan2(oy, ox);
        let da = a1 - a0; while (da > Math.PI) da -= TAU; while (da < -Math.PI) da += TAU;
        const aa = a0 + da * k, rr = lerp(r0, d, k) + Math.sin(Math.PI * k) * 20;
        cx = nx + Math.cos(aa) * rr; cy = ny + Math.sin(aa) * rr;
      }
      blit(ctx, tagSprite(f.costPrefix + shown, { size: 34, color: S.kind === 'paper' ? S.costTag : undefined }), cx, cy, { sx: pp.sx, sy: pp.sy, alpha: fade * f.ghost, rot: -0.06 + (pp.rot || 0), t, jit: 'cost' });
    }
  });
  return T;
}
