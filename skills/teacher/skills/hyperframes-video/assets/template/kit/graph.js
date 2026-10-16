/* kit/graph.js: the persistent subject: a directed, weighted graph with a mascot that travels it.

   const G = KIT.graph({nodes: [{id: 0, x: 560, y: 560}, ...], edges: [{from: 0, to: 1, w: 100, bend: 0}, ...], r: 52})
   Layout comes from data (world coordinates, 1920x1080 world). Everything starts hidden; scenes bring it in:
     G.nodeIn(id, t) / G.nodesIn(t, stagger)      nodes pop in (with floor shadow)
     G.edgeIn(i, t, d) / G.edgesIn(t, stagger)     the stroke draws from tail to head, arrowhead lands, weight chip pops
     G.light(id, t, tone|null) / G.lightAll(t)     tint a node (accent | good | bad | cool | gold | null = idle)
     G.ring(id, t, tone)                           a ripple from a node (an event happened here)
     G.edgeTone(i, t, tone|null)                   recolour an edge, its arrowhead and chip
     G.fire(i, t, tone, d)                         a comet runs along an edge ("this edge relaxes now"); returns arrival time
     G.route([0, 1, 3], t, d, tone, {lightNodes})  a glowing route drawn hop by hop; returns {clear, dim, reject, end}
     G.tag(id, text, t, tone, side)                a badge on a node (START / GOAL / STOP); returns the element
     G.edgeTag(i, text, t, tone)                   a badge beside an edge ("FLIGHT 1"), clear of its weight chip
     G.value(id, t, html, {tone})                  a changing value beside a node (dist labels)
     G.dim(t, opacity, keepIds) / G.undim(t)       push everything back except what matters
     G.mascotAt(id, t) / G.hop([0, 1, 3], t, dHop, {trail}) / G.blink(t)   the traveller
   Geometry: G.pos(id), G.mid(i) (chip centre), G.idx(u, v) (edge index).
   Text sizes: node numbers, weight chips, tags and values are drawn at world size but never drop below
   tok.size.node / tok.size.world px on screen: they counter-scale as the camera pulls back (KIT.wfs / KIT.wscale read
   the --inv variable the camera keeps on #world), so a wide shot or a corner thumbnail keeps every number readable. */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  const C = tok.color;
  const TONES = ['accent', 'good', 'bad', 'cool', 'gold', 'violet'];
  let uid = 0;

  function ensureDefs(svg) {
    if (svg.__graphDefs) return;
    svg.__graphDefs = true;
    const d = K.defs(svg);
    const rad = (id, stops, attrs = {}) => {
      const g = K.svg('radialGradient', Object.assign({ id, cx: '38%', cy: '32%', r: '75%' }, attrs), d);
      stops.forEach(([o, c, a]) => K.svg('stop', { offset: o, 'stop-color': c, 'stop-opacity': a ?? 1 }, g));
    };
    rad('gNode', [['0%', C.node[0]], ['70%', C.node[1]], ['100%', C.node[2]]]);
    TONES.forEach((tn) => rad('gTint-' + tn, [['0%', K.tone(tn)], ['55%', K.tone(tn), 0.82], ['100%', K.tone(tn), 0.55]]));
    rad('gShadow', [['0%', `rgb(${tok.fx.shadow})`, 0.6 * tok.fx.shadowK], ['100%', `rgb(${tok.fx.shadow})`, 0]], { cx: '50%', cy: '50%', r: '50%' });
    const m = K.svg('linearGradient', { id: 'gMascot', x1: '0', y1: '0', x2: '0', y2: '1' }, d);
    K.svg('stop', { offset: '0%', 'stop-color': C.mascot.top }, m);
    K.svg('stop', { offset: '100%', 'stop-color': C.mascot.bot }, m);
  }

  K.graph = function (spec) {
    const svg = spec.svg || K.layer.wsvg, html = spec.html || K.layer.whtml;
    ensureDefs(svg);
    const R = spec.r || 52, id = 'g' + uid++;
    const root = K.svg('g', { class: 'graph', id }, svg);
    const L = {};
    ['shadow', 'edge', 'route', 'chip', 'node', 'tok'].forEach((k) => { L[k] = K.svg('g', {}, root); });
    const G = { root, R, nodes: {}, edges: [], html };

    // ---------------------------------------------------------------- nodes
    spec.nodes.forEach((n) => {
      const g = K.svg('g', { transform: `translate(${n.x},${n.y})` }, L.node);
      const body = K.svg('g', {}, g);
      const halo = K.svg('circle', { r: R + 15, fill: 'none', stroke: C.accent, 'stroke-width': 4, opacity: 0 }, body);
      const base = K.svg('circle', { r: R, fill: 'url(#gNode)', stroke: C.edge, 'stroke-width': 3.5 }, body);
      const tints = {};
      const gloss = K.svg('ellipse', { cx: -R * 0.22, cy: -R * 0.42, rx: R * 0.5, ry: R * 0.22, fill: C.gloss, opacity: 0.12 }, body);
      const nfs = Math.round(R * 0.82);
      const label = K.text(body, 0, 2, n.label ?? String(n.id), { 'font-size': nfs, 'font-weight': 700, fill: C.ink, style: `font-size:${K.wfs(nfs, tok.size.node)}` });
      const shadow = K.svg('ellipse', { cx: n.x, cy: n.y + R * 1.05, rx: R * 1.1, ry: R * 0.3, fill: 'url(#gShadow)' }, L.shadow);
      K.hidden([g, shadow]);
      G.nodes[n.id] = { ...n, g, body, halo, base, tints, gloss, label, shadow, tone: null };
    });
    const N = (nid) => { const n = G.nodes[nid]; if (!n) throw new Error(`graph: no node ${nid}`); return n; };
    G.pos = (nid) => ({ x: N(nid).x, y: N(nid).y });

    // ---------------------------------------------------------------- edges
    spec.edges.forEach((e, i) => {
      const a = N(e.from), b = N(e.to);
      const dx = b.x - a.x, dy = b.y - a.y, len = Math.hypot(dx, dy), nx = -dy / len, ny = dx / len;
      const bend = e.bend || 0;
      const cx = (a.x + b.x) / 2 + nx * bend * 2, cy = (a.y + b.y) / 2 + ny * bend * 2;
      const u1 = [cx - a.x, cy - a.y], u2 = [b.x - cx, b.y - cy];
      const l1 = Math.hypot(...u1), l2 = Math.hypot(...u2);
      const sx = a.x + (u1[0] / l1) * (R + 7), sy = a.y + (u1[1] / l1) * (R + 7);
      const ex = b.x - (u2[0] / l2) * (R + 16), ey = b.y - (u2[1] / l2) * (R + 16);
      const d = bend ? `M${sx},${sy} Q${cx},${cy} ${ex},${ey}` : `M${sx},${sy} L${ex},${ey}`;
      const ang = (Math.atan2(u2[1], u2[0]) * 180) / Math.PI;
      const tipx = ex + (u2[0] / l2) * 11, tipy = ey + (u2[1] / l2) * 11;
      const path = K.svg('path', { d, stroke: C.edge, 'stroke-width': 4.5, fill: 'none', 'stroke-linecap': 'round' }, L.edge);
      const arrow = K.svg('path', { d: 'M2,0 L-20,-11 L-14,0 L-20,11 Z', fill: C.edge, transform: `translate(${tipx},${tipy}) rotate(${ang})` }, L.edge);
      const mx = bend ? 0.25 * sx + 0.5 * cx + 0.25 * ex : (sx + ex) / 2, my = bend ? 0.25 * sy + 0.5 * cy + 0.25 * ey : (sy + ey) / 2;
      const cg = K.svg('g', { transform: `translate(${mx},${my})` }, L.chip);
      const fs = spec.chipSize || tok.size.world;
      // the pill and its number grow together when the camera pulls back (scale about the chip centre)
      const cz = K.svg('g', { style: `transform:${K.wscale(fs)};transform-box:view-box;transform-origin:0px 0px` }, cg);
      const chip = K.svg('g', {}, cz);
      const txt = e.label ?? (e.w != null ? String(e.w) : '');
      const w = txt.length * fs * tok.mono + 30, h = fs * 1.6;
      const rect = K.svg('rect', { x: -w / 2, y: -h / 2, width: w, height: h, rx: h / 2, fill: C.chip, stroke: C.line2, 'stroke-width': 2.5 }, chip);
      const text = K.text(chip, 0, 1.5, txt, { 'font-size': fs, 'font-weight': 700, fill: C.ink, class: 'mono' });
      if (!txt) chip.setAttribute('display', 'none');
      K.drawable(path);
      K.hidden([arrow, chip]);
      G.edges.push({ ...e, i, d, path, arrow, chip, rect, text, mx, my, len: len - 2 * R, a, b });
    });
    G.idx = (u, v) => {
      const i = G.edges.findIndex((e) => e.from === u && e.to === v);
      if (i < 0) throw new Error(`graph: no edge ${u} -> ${v}`);
      return i;
    };
    G.mid = (i) => ({ x: G.edges[i].mx, y: G.edges[i].my });

    // ---------------------------------------------------------------- entrances
    G.nodeIn = (nid, t, d = 0.55) => {
      const n = N(nid);
      tl.set(n.g, { opacity: 1 }, t);
      tl.fromTo(n.body, { scale: 0, transformOrigin: '50% 50%' }, { scale: 1, duration: d, ease: 'back.out(2.6)', immediateRender: false }, t);
      tl.fromTo(n.shadow, { opacity: 0 }, { opacity: 1, duration: d, immediateRender: false }, t);
      return t + d;
    };
    G.nodesIn = (t, stagger = 0.12, ids) => (ids || Object.keys(G.nodes)).forEach((nid, k) => G.nodeIn(isNaN(nid) ? nid : +nid, t + k * stagger));
    G.edgeIn = (i, t, d = 0.6) => {
      const e = G.edges[i];
      K.draw(e.path, t, d, 'power2.inOut');
      tl.fromTo(e.arrow, { opacity: 0, scale: 0.2, transformOrigin: '80% 50%' }, { opacity: 1, scale: 1, duration: 0.25, ease: 'back.out(3)', immediateRender: false }, t + d - 0.06);
      tl.fromTo(e.chip, { opacity: 0, scale: 0.3, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(2.4)', immediateRender: false }, t + d * 0.55);
      return t + d;
    };
    G.edgesIn = (t, stagger = 0.15, d = 0.6) => G.edges.forEach((e, k) => G.edgeIn(k, t + k * stagger, d));

    // ---------------------------------------------------------------- state changes
    function tint(n, tone) {
      if (!tone) return null;
      if (!n.tints[tone]) {
        n.tints[tone] = K.svg('circle', { r: R, fill: `url(#gTint-${tone})`, opacity: 0 }, n.body);
        n.body.insertBefore(n.tints[tone], n.gloss);
      }
      return n.tints[tone];
    }
    G.light = (nid, t, tone, d = 0.35) => {
      const n = N(nid);
      if (n.tone === tone) return;
      const prev = tint(n, n.tone), next = tint(n, tone);
      if (prev) tl.to(prev, { opacity: 0, duration: d }, t);
      if (next) tl.to(next, { opacity: 1, duration: d }, t);
      tl.to(n.label, { attr: { fill: tone ? K.on(tone, 'onAccent') : C.ink }, duration: d }, t);
      tl.to(n.base, { attr: { stroke: tone ? K.tone(tone) : C.edge }, duration: d }, t);
      tl.to(n.halo, { attr: { stroke: K.tone(tone || 'accent') }, opacity: tone ? 0.55 : 0, duration: d }, t);
      n.tone = tone;
    };
    G.ring = (nid, t, tone = 'accent', d = 0.7) => {
      const n = N(nid);
      const c = K.svg('circle', { cx: n.x, cy: n.y, r: R, fill: 'none', stroke: K.tone(tone), 'stroke-width': 5, opacity: 0 }, L.route);
      tl.fromTo(c, { attr: { r: R }, opacity: 0.9 }, { attr: { r: R + 46 }, opacity: 0, duration: d, ease: 'power2.out', immediateRender: false }, t);
    };
    G.lightAll = (t, tone = null, d = 0.35) => Object.keys(G.nodes).forEach((k) => G.light(G.nodes[k].id, t, tone, d));
    G.pulse = (nid, t, s = 1.18) => K.pulse(N(nid).body, t, s);
    G.edgeTone = (i, t, tone, d = 0.35) => {
      const e = G.edges[i], c = tone ? K.tone(tone) : C.edge;
      tl.to(e.path, { attr: { stroke: c }, duration: d }, t);
      tl.to(e.arrow, { attr: { fill: c }, duration: d }, t);
      tl.to(e.rect, { attr: { stroke: tone ? c : C.line2 }, duration: d }, t);
      tl.to(e.text, { attr: { fill: tone ? K.ink(tone) : C.ink }, duration: d }, t);
    };
    const GLOW = tok.fx.glow, FIRE = tok.fx.fireGlow; // halo strengths (softer on light grounds, where a glow reads as a smudge)
    function glowPaths(parent, d, color, width = 5) {
      return [
        K.svg('path', { d, stroke: color, 'stroke-width': width * 4.2, fill: 'none', 'stroke-linecap': 'round', opacity: GLOW[0] }, parent),
        K.svg('path', { d, stroke: color, 'stroke-width': width * 2.2, fill: 'none', 'stroke-linecap': 'round', opacity: GLOW[1] }, parent),
        K.svg('path', { d, stroke: color, 'stroke-width': width, fill: 'none', 'stroke-linecap': 'round' }, parent),
      ];
    }
    G.fire = (i, t, tone = 'accent', d = 0.7) => {
      const e = G.edges[i];
      const g = K.svg('g', {}, L.route);
      const ps = glowPaths(g, e.d, K.tone(tone), 6);
      K.drawable(ps);
      tl.set(ps, { opacity: (k) => [FIRE[0], FIRE[1], 1][k] }, t);
      tl.fromTo(ps, { drawSVG: '0% 0%' }, { drawSVG: '0% 45%', duration: d * 0.4, ease: 'power1.in', immediateRender: false }, t);
      tl.to(ps, { drawSVG: '100% 100%', duration: d * 0.6, ease: 'power2.out' }, t + d * 0.4);
      tl.set(ps, { opacity: 0 }, t + d + 0.02);
      G.ring(e.to, t + d * 0.85, tone);
      return t + d;
    };

    /** A glowing route along node ids, drawn hop by hop in `d` seconds. */
    G.route = (ids, t, d = 1.6, tone = 'accent', o = {}) => {
      const g = K.svg('g', {}, L.route);
      const color = K.tone(tone);
      const segs = [];
      for (let k = 0; k + 1 < ids.length; k++) segs.push(G.edges[G.idx(ids[k], ids[k + 1])]);
      const tot = segs.reduce((s, e) => s + e.len, 0);
      let at = t;
      const all = [];
      const flows = [];
      segs.forEach((e, k) => {
        const dd = (d * e.len) / tot;
        const ps = glowPaths(g, e.d, color, o.width || 6);
        K.drawable(ps);
        tl.set(ps, { opacity: (j) => [GLOW[0], GLOW[1], 1][j] }, at);
        tl.fromTo(ps, { drawSVG: '0%' }, { drawSVG: '100%', duration: dd, ease: k === 0 ? 'power2.in' : k === segs.length - 1 ? 'power2.out' : 'none', immediateRender: false }, at);
        if (o.tint !== false) G.edgeTone(e.i, at, tone);
        if (o.lightNodes) { G.light(ids[k], at, tone); G.light(ids[k + 1], at + dd, tone); G.ring(ids[k + 1], at + dd * 0.9, tone); }
        const fl = K.svg('path', { d: e.d, stroke: C.spark, 'stroke-width': 3, fill: 'none', 'stroke-linecap': 'round', 'stroke-dasharray': '2 22', opacity: 0 }, g);
        flows.push(fl);
        all.push(...ps);
        at += dd;
      });
      // marching dashes keep a held route alive
      tl.to(flows, { opacity: 0.55, duration: 0.4 }, at);
      tl.fromTo(flows, { strokeDashoffset: 0 }, { strokeDashoffset: -240 * Math.max(1, (K.T.total - at) / 4), duration: Math.max(1, K.T.total - at), ease: 'none', immediateRender: false }, at);
      const h = {
        g, end: at, paths: all,
        clear(tc, dc = 0.4) { tl.to(g, { opacity: 0, duration: dc }, tc); if (o.tint !== false) segs.forEach((e) => G.edgeTone(e.i, tc, null, dc)); return h; },
        dim(tc, op = 0.3, dc = 0.4) { tl.to(g, { opacity: op, duration: dc }, tc); return h; },
        reject(tc, label) {
          const bad = K.tone('bad');
          tl.to(all, { attr: { stroke: bad }, duration: 0.25 }, tc);
          segs.forEach((e) => G.edgeTone(e.i, tc, 'bad', 0.25));
          K.shake(g, tc + 0.1, 10, 0.45);
          if (label) {
            const m = segs[Math.floor(segs.length / 2)];
            const x = K.el('div', 'chip mono', html, { left: m.mx, top: m.my - 64, background: bad, color: K.on('bad', 'onReject'), borderColor: bad, fontWeight: 700, fontSize: K.wfs(tok.size.chip), padding: '0.25em 0.65em' }, label);
            gsap.set(x, { xPercent: -50, yPercent: -50 });
            K.hidden(x); K.pop(x, tc + 0.15);
            h.label = x;
          }
          tl.to(g, { opacity: 0.35, duration: 0.5 }, tc + 0.8);
          return h;
        },
      };
      return h;
    };

    G.tag = (nid, text, t, tone = 'accent', side = 'top', o = {}) => {
      const n = N(nid), col = K.pill(tone);
      // anchored by the edge that faces the node, so a tag that grows with a pulled-back camera grows away from it
      const off = { top: [0, -(R + 22)], bottom: [0, R + 22], left: [-(R + 26), 0], right: [R + 26, 0] }[side];
      const e = K.el('div', 'chip mono', html, { left: n.x + off[0] + (o.dx || 0), top: n.y + off[1] + (o.dy || 0), background: col, borderColor: col, color: K.on(tone, 'onAccent'), fontWeight: 700, fontSize: K.wfs(o.size || tok.size.chip), letterSpacing: '0.08em', padding: '0.2em 0.55em' }, text);
      gsap.set(e, { xPercent: side === 'left' ? -100 : side === 'right' ? 0 : -50, yPercent: side === 'top' ? -100 : side === 'bottom' ? 0 : -50 });
      K.hidden(e);
      K.pop(e, t, 0.45, 0.4);
      return e;
    };
    /** A badge beside an edge, pushed away from the graph's centre so it never sits on the weight chip. */
    G.edgeTag = (i, text, t, tone = 'accent', o = {}) => {
      const e = G.edges[i], col = K.pill(tone);
      const ns = Object.values(G.nodes), gx = ns.reduce((s, n) => s + n.x, 0) / ns.length, gy = ns.reduce((s, n) => s + n.y, 0) / ns.length;
      let vx = e.mx - gx, vy = e.my - gy;
      const vl = Math.hypot(vx, vy) || 1;
      // far enough along (vx, vy) that the badge's box clears the weight chip's box (both sizes estimated from text);
      // both grow by the same factor when the camera pulls back, and so does the offset (KIT.wgrow)
      const fs = o.size || tok.size.chip, cfs = spec.chipSize || tok.size.world, ux = Math.abs(vx / vl), uy = Math.abs(vy / vl);
      const W = (text.length * fs * tok.mono * 1.06 + 1.1 * fs + String(e.w ?? '').length * cfs * tok.mono + 30) / 2, H = (fs * 1.2 + 0.4 * fs + 4 + cfs * 1.6) / 2;
      const off = o.offset ?? Math.min(ux > 0.05 ? W / ux : 1e9, uy > 0.05 ? H / uy : 1e9) + 20;
      const grow = K.wgrow(Math.min(fs, cfs));
      const el = K.el('div', 'chip mono', html, { left: `calc(${e.mx}px + ${((vx / vl) * off).toFixed(1)}px * ${grow})`, top: `calc(${e.my}px + ${((vy / vl) * off).toFixed(1)}px * ${grow})`, background: col, borderColor: col, color: K.on(tone, 'onAccent'), fontWeight: 700, fontSize: K.wfs(fs), letterSpacing: '0.06em', padding: '0.2em 0.55em' }, text);
      gsap.set(el, { xPercent: -50, yPercent: -50 });
      K.hidden(el);
      K.pop(el, t, 0.45, 0.4);
      return el;
    };
    G.value = (nid, t, htmlText, o = {}) => {
      const n = N(nid);
      if (!n.val) {
        const side = o.side || 'right', vfs = o.size || 34, g = K.wgrow(vfs);
        // a 150 x 48 box at world size; box and text grow together (g) when the camera pulls back, away from the node
        const at = (px, k) => `calc(${px}px + ${k}px * ${g})`;
        const pos = { right: [at(n.x + R + 18, 0), at(n.y, -24)], left: [at(n.x - R - 18, -150), at(n.y, -24)],
          bottom: [at(n.x, -75), at(n.y + R + 14, 0)], top: [at(n.x, -75), at(n.y - R - 14, -48)] }[side];
        n.val = K.stack(html, { left: pos[0], top: pos[1], width: `calc(150px * ${g})`, height: `calc(48px * ${g})` }, 'mono');
        n.val.el.style.fontSize = K.wfs(vfs);
        n.val.el.style.fontWeight = 700;
        n.val.el.style.justifyContent = side === 'left' ? 'flex-end' : 'flex-start';
      }
      return n.val.to(t, htmlText, { color: K.ink(o.tone || 'ink'), align: (o.side || 'right') === 'left' ? 'flex-end' : 'flex-start', mode: o.mode || 'flip' });
    };
    G.dim = (t, op = 0.28, keep = [], d = 0.4) => {
      const ks = new Set(keep.map(String));
      const els = [];
      Object.values(G.nodes).forEach((n) => { if (!ks.has(String(n.id))) els.push(n.body); });
      G.edges.forEach((e) => { if (!ks.has(`${e.from}-${e.to}`)) els.push(e.path, e.arrow, e.chip); });
      tl.to(els, { opacity: op, duration: d }, t);
    };
    G.undim = (t, d = 0.4) => {
      const els = [];
      Object.values(G.nodes).forEach((n) => els.push(n.body));
      G.edges.forEach((e) => els.push(e.path, e.arrow, e.chip));
      tl.to(els, { opacity: 1, duration: d }, t);
    };

    // ---------------------------------------------------------------- the mascot (a small orange block with eyes)
    let M = null;
    const perch = (nid) => { const n = N(nid); return { x: n.x, y: n.y - R + 4 }; };
    function mascot() {
      if (M) return M;
      const g = K.svg('g', { class: 'mascot' }, L.tok);
      const sh = K.svg('ellipse', { cx: 0, cy: 6, rx: 30, ry: 8, fill: `rgb(${tok.fx.shadow})`, opacity: 0.35 * tok.fx.shadowK }, g);
      const body = K.svg('g', {}, g);
      K.svg('rect', { x: -34, y: -60, width: 68, height: 60, rx: 15, fill: 'url(#gMascot)', stroke: C.mascot.line, 'stroke-width': 2.5 }, body);
      K.svg('rect', { x: -25, y: -54, width: 34, height: 9, rx: 4.5, fill: C.gloss, opacity: 0.28 }, body);
      const eyes = K.svg('g', {}, body);
      K.svg('rect', { x: -18, y: -42, width: 11, height: 19, rx: 4, fill: C.mascot.eye }, eyes);
      K.svg('rect', { x: 7, y: -42, width: 11, height: 19, rx: 4, fill: C.mascot.eye }, eyes);
      K.svg('rect', { x: -30, y: -4, width: 16, height: 8, rx: 3, fill: C.mascot.foot }, body);
      K.svg('rect', { x: 14, y: -4, width: 16, height: 8, rx: 3, fill: C.mascot.foot }, body);
      K.hidden(g);
      M = { g, body, eyes, sh, at: null };
      return M;
    }
    G.mascotAt = (nid, t, d = 0.5) => {
      const m = mascot(), p = perch(nid);
      tl.set(m.g, { x: p.x, y: p.y }, t);
      tl.fromTo(m.g, { opacity: 0 }, { opacity: 1, duration: 0.15, immediateRender: false }, t);
      tl.fromTo(m.body, { scale: 0, transformOrigin: '50% 100%' }, { scale: 1, duration: d, ease: 'back.out(3)', immediateRender: false }, t);
      m.at = nid;
      return t + d;
    };
    G.mascotOut = (t) => { const m = mascot(); tl.to(m.body, { scale: 0, duration: 0.3, ease: 'back.in(2)', transformOrigin: '50% 100%' }, t); tl.set(m.g, { opacity: 0 }, t + 0.3); };
    G.blink = (t) => { const m = mascot(); tl.to(m.eyes, { scaleY: 0.1, transformOrigin: '50% 60%', duration: 0.07, yoyo: true, repeat: 1, ease: 'power1.inOut' }, t); };
    G.look = (t, dx) => { const m = mascot(); tl.to(m.eyes, { x: dx, duration: 0.2, ease: 'power2.out' }, t); };
    /** Hop along node ids; o.trail = tone draws the route under it; o.onLand(nodeId, time) for counters. */
    G.hop = (ids, t, dHop = 0.9, o = {}) => {
      const m = mascot();
      let at = t;
      const lands = [];
      const legs = [];
      for (let k = 0; k + 1 < ids.length; k++) {
        const a = perch(ids[k]), b = perch(ids[k + 1]);
        const mid = { x: (a.x + b.x) / 2, y: Math.min(a.y, b.y) - (o.height || 120) };
        G.look(at, Math.sign(b.x - a.x) * 4);
        tl.to(m.body, { scaleY: 0.78, scaleX: 1.16, transformOrigin: '50% 100%', duration: 0.1, ease: 'power2.out' }, at);
        tl.to(m.body, { scaleY: 1.12, scaleX: 0.92, duration: 0.18, ease: 'power2.out' }, at + 0.1);
        tl.to(m.g, { motionPath: { path: [a, mid, b], curviness: 1.25 }, duration: dHop - 0.12, ease: 'power1.inOut' }, at + 0.12);
        tl.to(m.sh, { scale: 0.45, opacity: 0.12, duration: (dHop - 0.12) / 2, yoyo: true, repeat: 1, ease: 'sine.inOut', transformOrigin: '50% 50%' }, at + 0.12);
        if (o.trail) legs.push(G.route([ids[k], ids[k + 1]], at + 0.12, dHop - 0.12, o.trail, { lightNodes: o.lightNodes !== false }));
        const land = at + dHop;
        tl.to(m.body, { scaleY: 0.74, scaleX: 1.2, duration: 0.09, ease: 'power2.in' }, land - 0.02);
        tl.to(m.body, { scaleY: 1, scaleX: 1, duration: 0.42, ease: 'elastic.out(1, 0.45)' }, land + 0.07);
        lands.push(land);
        if (o.onLand) o.onLand(ids[k + 1], land);
        at = land + (o.pause ?? 0.15);
      }
      G.look(at, 0);
      m.at = ids[ids.length - 1];
      const trail = o.trail ? { legs, clear: (tc, dc) => legs.forEach((h) => h.clear(tc, dc)), dim: (tc, op, dc) => legs.forEach((h) => h.dim(tc, op, dc)) } : null;
      return { lands, end: at, trail };
    };
    return G;
  };
})();
