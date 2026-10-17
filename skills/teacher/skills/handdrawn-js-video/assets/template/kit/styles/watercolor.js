// kit/styles/watercolor.js: watercolor washes with an ink line, on cold-press paper.
//   washes    every node, burst, star, hill and cloud is a wash painted with Tyler Hobbs' method: the shape is
//             deformed by recursive midpoint displacement (each vertex with its own variance), then about 30
//             layers, each deformed again, are laid at about 4% opacity through a random circle mask, the colour
//             deepening in groups of five layers; every layer leaves a little more pigment along its own edge, so
//             the edge pools darker while the outside stays soft; pigment then granulates into the paper's valleys
//             and lifts off its peaks. Each wash is painted once into a cached canvas and only drawn after that
//   bloom     graph nodes bloom in: the cached wash is revealed through a growing, irregular wet front, then the
//             ink ring is drawn and the label written. The highlighted route and the plane's trail get a wash
//             along their length (painted once per edge in a canonical frame, revealed as the line draws)
//   state     shown by wash colour: the target (a glowing node) gets a halo wash, the route and trails a wash in
//             their colour (accent for the route, red for a rejected one, green for the recap), relaxations a wet
//             gold stroke
//   ink       every line is a brush-pen stroke with a pressure taper (perfect-freehand's idea, no library): it
//             lands thin, swells and lifts off thin; it is laid once and never boils
//   paper     cold-press: a tileable height field shaded from the top left (the tooth), a few pale background
//             washes; text pieces (tags, slips, cards, the caption band) are deckle-edged scraps of the same paper
//   motion    pieces land a touch large and settle, without squash or bounce; nothing jitters, floats or boils. Text stays crisp ink
// Colours: every token is derived from the paper palette (original or themed) in palette(); nothing new is invented.
// This file loads before the kit: kit functions (roughen, drawText, ...) are only called inside hooks.
'use strict';
(() => {
  // ---------------------------------------------------------------- paper and mask tiles (built once, deterministic)
  // a tileable height field: value noise in octaves whose cells divide the tile, so it wraps without a seam
  function heightField(N, seed) {
    const h = new Float32Array(N * N), oct = [[2, 0.12], [4, 0.32], [8, 0.3], [16, 0.16], [32, 0.1]];
    for (const [cell, wgt] of oct) {
      const G = N / cell, r = mulberry32(seed + cell), v = new Float32Array(G * G).map(() => r());
      for (let y = 0; y < N; y++) {
        const gy = y / cell, iy = Math.floor(gy), fy = gy - iy, sy = fy * fy * (3 - 2 * fy), y0 = (iy % G) * G, y1 = ((iy + 1) % G) * G;
        for (let x = 0; x < N; x++) {
          const gx = x / cell, ix = Math.floor(gx), fx = gx - ix, sx = fx * fx * (3 - 2 * fx), x0 = ix % G, x1 = (ix + 1) % G;
          h[y * N + x] += wgt * lerp(lerp(v[y0 + x0], v[y0 + x1], sx), lerp(v[y1 + x0], v[y1 + x1], sx), sy);
        }
      }
    }
    let lo = 1e9, hi = -1e9; for (const q of h) { lo = Math.min(lo, q); hi = Math.max(hi, q); }
    return h.map((q) => (q - lo) / (hi - lo));
  }
  // tiles from the height field: the tooth lit from the top left (light and dark), its peaks and its valleys
  const TILES = () => cached('wc:tiles', () => {
    const N = 512, h = heightField(N, 501), at = (x, y) => h[((y + N) % N) * N + ((x + N) % N)];
    const mk = (fn) => { const c = makeCanvas(N, N), g = c.getContext('2d'), d = g.createImageData(N, N);
      for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) { const [v, a] = fn(x, y), i = (y * N + x) * 4; d.data[i] = d.data[i + 1] = d.data[i + 2] = v; d.data[i + 3] = a; }
      g.putImageData(d, 0, 0); return c; };
    const sh = (x, y) => (at(x - 1, y - 1) + at(x - 2, y - 1) - at(x + 1, y + 1) - at(x + 2, y + 1)) * 2.6;
    return {
      light: mk((x, y) => [255, Math.round(255 * clamp(sh(x, y)))]),
      dark: mk((x, y) => [0, Math.round(255 * clamp(-sh(x, y)))]),
      peak: mk((x, y) => [0, Math.round(255 * smooth(0.56, 0.82, at(x, y)))]),
      valley: mk((x, y) => [0, Math.round(255 * smooth(0.46, 0.18, at(x, y)))]),
    };
  });
  // Hobbs' texture masks: a few hundred small circles; each layer goes through one, at a random offset
  const MASKS = () => cached('wc:masks', () => [0, 1, 2, 3].map((m) => {
    const N = 256, c = makeCanvas(N, N), g = c.getContext('2d'), r = mulberry32(900 + m);
    for (let i = 0; i < 170; i++) {
      const x = r() * N, y = r() * N, rr = 5 + r() * r() * 26;
      wrapDraw(N, (dx, dy) => { const gr = g.createRadialGradient(x + dx, y + dy, 0, x + dx, y + dy, rr); gr.addColorStop(0, 'rgba(0,0,0,1)'); gr.addColorStop(0.65, 'rgba(0,0,0,0.85)'); gr.addColorStop(1, 'rgba(0,0,0,0)'); g.fillStyle = gr; g.beginPath(); g.arc(x + dx, y + dy, rr, 0, TAU); g.fill(); });
    }
    return c;
  }));
  const PAT = (c, key) => cached('wc:pat:' + key, () => SCRATCH.createPattern(c, 'repeat'));
  // a pattern laid in device pixels at k device px per world unit, offset by (ox, oy) world units
  function devPat(c, key, k, ox, oy, rot = 0) {
    const p = PAT(c, key); p.setTransform(new DOMMatrix().scaleSelf(k).translateSelf(ox, oy).rotateSelf(rot)); return p;
  }
  // the colour's valley tile (pigment that settles), cached per colour
  const valleyOf = (col) => cached('wc:val:' + col, () => { const t = TILES().valley, c = makeCanvas(t.width, t.height), g = c.getContext('2d');
    g.fillStyle = col; g.fillRect(0, 0, c.width, c.height); g.globalCompositeOperation = 'destination-in'; g.drawImage(t, 0, 0); return c; });
  // the cold-press tooth over a region (sprites and the backdrop): lit edges and shaded hollows, in world units
  function tooth(g, x0, y0, w, h, strength = 1, seed = 1) {
    const T = TILES(), r = mulberry32(seedOf(seed) + 3), ox = r() * 512, oy = r() * 512;
    g.save(); const a0 = g.globalAlpha * strength * S.toothK;
    g.globalAlpha = a0 * 0.55; g.fillStyle = devPat(T.light, 'light', 1, ox, oy); g.fillRect(x0, y0, w, h);
    g.globalAlpha = a0 * 0.42; g.fillStyle = devPat(T.dark, 'dark', 1, ox, oy); g.fillRect(x0, y0, w, h); g.restore();
  }

  // ---------------------------------------------------------------- Hobbs' wash
  const gauss = (r) => (r() + r() + r() + r() - 2) * 1.73;
  // recursive midpoint displacement: points [x, y, variance]; each pass inserts a displaced midpoint on every
  // edge, and every variance shrinks, so the outline gets detail at every scale
  function deform(pts, r, passes, decay = 0.58) {
    for (let p = 0; p < passes; p++) {
      const out = [];
      for (let i = 0; i < pts.length; i++) {
        const a = pts[i], b = pts[(i + 1) % pts.length], v = (a[2] + b[2]) / 2;
        out.push([a[0], a[1], a[2] * decay]);
        out.push([(a[0] + b[0]) / 2 + gauss(r) * v, (a[1] + b[1]) / 2 + gauss(r) * v, v * decay * (0.6 + 0.8 * r())]);
      }
      pts = out;
    }
    return pts;
  }
  // one round of Chaikin corner cutting on a closed outline (keeps the variances)
  function chaikin(p) {
    const out = [];
    for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; out.push([0.75 * a[0] + 0.25 * b[0], 0.75 * a[1] + 0.25 * b[1], a[2]], [0.25 * a[0] + 0.75 * b[0], 0.25 * a[1] + 0.75 * b[1], b[2]]); }
    return out;
  }
  // paint a wash of `color` filling `poly` (local units of g) into g. o: {seed, layers, alpha, spread (world px of
  // edge wander), rim (world px of the pooled edge), gran (granulation 0..1), deep (the colour it deepens toward)}
  function wash(g, poly, color, o = {}) {
    const M = g.getTransform(), k = Math.hypot(M.a, M.b) || 1, r = mulberry32(seedOf(o.seed ?? 1) * 7 + 77);
    const layers = o.layers ?? S.washLayers, a = o.alpha ?? S.washA, spread = (o.spread ?? 8) * k, rimW = (o.rim ?? 2.4) * k, gran = o.gran ?? 1;
    const dev = poly.map(([x, y]) => [M.a * x + M.c * y + M.e, M.b * x + M.d * y + M.f]);
    const per = polyLength([...dev, dev[0]]) / k, n = Math.round(clamp(per / (o.step ?? 22), 10, 300));
    const base = chaikin(deform(closedResample(dev, (per * k) / n).map(([x, y]) => [x, y, spread * (0.35 + 1.3 * r())]), r, 2, 0.5));
    let [x0, y0, x1, y1] = bbox(base); const m = spread * 2.2 + rimW + 4;
    x0 = Math.max(0, Math.floor(x0 - m)); y0 = Math.max(0, Math.floor(y0 - m)); x1 = Math.min(g.canvas.width, Math.ceil(x1 + m)); y1 = Math.min(g.canvas.height, Math.ceil(y1 + m));
    const bw = x1 - x0, bh = y1 - y0; if (bw < 2 || bh < 2) return;
    const acc = makeCanvas(bw, bh), ag = acc.getContext('2d'), scr = makeCanvas(bw, bh), sg = scr.getContext('2d'), masks = MASKS();
    const deep = mixHex(color, o.deep || S.washDeep, 0.28);
    for (let i = 0; i < layers; i++) {
      const lp = chaikin(deform(base.map(([x, y, v]) => [x - x0, y - y0, v * 1.5]), r, 2, 0.5));
      sg.globalCompositeOperation = 'source-over'; sg.clearRect(0, 0, bw, bh);
      pathPts(sg, lp); sg.fillStyle = Math.floor(i / 5) % 2 ? deep : color;
      sg.globalAlpha = 0.36; sg.fill(); sg.globalAlpha = 1; sg.lineWidth = rimW * (0.6 + 0.8 * r()); sg.strokeStyle = sg.fillStyle; sg.lineJoin = 'round'; sg.stroke();
      sg.globalCompositeOperation = 'destination-in'; const mi = Math.floor(r() * masks.length);
      sg.fillStyle = devPat(masks[mi], 'm' + mi, k, r() * 256 - x0 / k, r() * 256 - y0 / k, r() * 360); sg.fillRect(0, 0, bw, bh);
      ag.globalAlpha = Math.min(1, a / 0.36); ag.drawImage(scr, 0, 0);
    }
    if ((o.tide ?? 1) > 0) {
      sg.globalCompositeOperation = 'source-over'; sg.globalAlpha = 1; sg.clearRect(0, 0, bw, bh); sg.filter = `blur(${0.8 * k}px)`;
      pathPts(sg, base.map(([x, y]) => [x - x0, y - y0])); sg.strokeStyle = deep; sg.lineWidth = 1.5 * k; sg.lineJoin = 'round'; sg.stroke(); sg.filter = 'none';
      ag.globalAlpha = Math.min(1, a * 5 * (o.tide ?? 1)); ag.drawImage(scr, 0, 0);
    }
    if (o.soft !== 0) { // the wet edge softens a little into the paper
      sg.globalCompositeOperation = 'source-over'; sg.globalAlpha = 1; sg.clearRect(0, 0, bw, bh); sg.drawImage(acc, 0, 0);
      ag.globalAlpha = 1; ag.globalCompositeOperation = 'copy'; ag.filter = `blur(${(o.soft ?? 1.1) * k}px)`; ag.drawImage(scr, 0, 0); ag.filter = 'none'; ag.globalCompositeOperation = 'source-over';
    }
    if (gran > 0) { // granulation: pigment lifts off the tooth's peaks and settles in its valleys
      const T = TILES(), ox = r() * 512 - x0 / k, oy = r() * 512 - y0 / k;
      ag.globalAlpha = 0.42 * gran; ag.globalCompositeOperation = 'destination-out'; ag.fillStyle = devPat(T.peak, 'peak', k, ox, oy); ag.fillRect(0, 0, bw, bh);
      sg.globalCompositeOperation = 'source-over'; sg.globalAlpha = 1; sg.clearRect(0, 0, bw, bh);
      sg.fillStyle = devPat(valleyOf(deep), 'val' + deep, k, ox, oy); sg.fillRect(0, 0, bw, bh);
      sg.globalCompositeOperation = 'destination-in'; sg.drawImage(acc, 0, 0);
      ag.globalCompositeOperation = 'source-over'; ag.globalAlpha = 0.6 * gran; ag.drawImage(scr, 0, 0);
    }
    g.save(); g.setTransform(1, 0, 0, 1, 0, 0); g.globalAlpha *= o.opacity ?? 1; g.drawImage(acc, x0, y0); g.restore();
  }

  // ---------------------------------------------------------------- the brush pen
  // the outline of a pressure-tapered stroke, added to `path`: it lands thin, swells with the (simulated) pressure
  // and lifts off thin; endK 0 keeps a round wet head while the stroke is still being drawn
  function brushPath(path, p, w, seed, endK = 1) {
    if (p.length < 2) return;
    const c = polyCum(p), L = c[c.length - 1] || 1, N = normalsOf(p, false), n = p.length;
    const t0 = Math.min(L * 0.3, w * 5), t1 = Math.min(L * 0.4, w * 8);
    const hw = c.map((d) => {
      const press = 0.74 + 0.36 * noise1(seed + 5, d / 64);
      const land = 0.2 + 0.8 * smooth(0, t0, d), lift = lerp(1, 0.12 + 0.88 * smooth(0, t1, L - d), endK);
      return Math.max(0.35, w * 0.5 * press * land * lift);
    });
    path.moveTo(p[0][0] + N[0][0] * hw[0], p[0][1] + N[0][1] * hw[0]);
    for (let i = 1; i < n; i++) path.lineTo(p[i][0] + N[i][0] * hw[i], p[i][1] + N[i][1] * hw[i]);
    const ae = Math.atan2(N[n - 1][1], N[n - 1][0]); path.arc(p[n - 1][0], p[n - 1][1], hw[n - 1], ae, ae + Math.PI);
    for (let i = n - 1; i >= 0; i--) path.lineTo(p[i][0] - N[i][0] * hw[i], p[i][1] - N[i][1] * hw[i]);
    const as = Math.atan2(N[0][1], N[0][0]); path.arc(p[0][0], p[0][1], hw[0], as + Math.PI, as + 2 * Math.PI);
    path.closePath();
  }
  // dashes as separate dabs of the brush
  function dashPath(path, p, w, seed, dash, off = 0) {
    const L = polyLength(p), per = dash[0] + dash[1]; if (L < 1) return;
    for (let d = -((off % per) + per) % per, i = 0; d < L; d += per, i++) {
      const a = Math.max(0, d), b = Math.min(L, d + dash[0]); if (b - a < 1) continue;
      brushPath(path, polySlice(p, a / L, b / L), w, seed + i * 13, 1);
    }
  }

  // ---------------------------------------------------------------- a wash along a route (painted once per edge)
  // The route's points at any t are the same curve moved and scaled (the graph is placed by x, y, scale), so the
  // wash is painted in a canonical frame (first point at 0,0, last at C,0) and drawn back into the curve's frame.
  const C = 600;
  function routeWash(ctx, pts, w, color, prog, seed) {
    const a = pts[0], b = pts[pts.length - 1], dx = b[0] - a[0], dy = b[1] - a[1], c = Math.hypot(dx, dy); if (c < 2) return;
    const ang = Math.atan2(dy, dx), k = C / c, ca = Math.cos(-ang), sa = Math.sin(-ang), q4 = (v) => Math.round(v * 4) / 4;
    const q = pts.map(([x, y]) => { const u = (x - a[0]) * k, v = (y - a[1]) * k; return [q4(u * ca - v * sa), q4(u * sa + v * ca)]; });
    const wq = Math.round(w * k * 2) / 2, bw = wq * 2.3, key = `wc:route:${seed}:${color}:${wq}:${hashStr(q.map((p) => p.join(',')).join(';'))}`;
    const sp = cached(key, () => {
      const [x0, y0, x1, y1] = bbox(q), m = bw * 3 + 30;
      return sprite(x1 - x0 + 2 * m, y1 - y0 + 2 * m, m - x0, m - y0, (g) => {
        const sm = resample(q, 24), N = normalsOf(sm, false);
        const band = [...sm.map((p, i) => [p[0] + N[i][0] * bw, p[1] + N[i][1] * bw]), ...sm.map((p, i) => [p[0] - N[i][0] * bw, p[1] - N[i][1] * bw]).reverse()];
        wash(g, band, color, { seed, layers: 26, spread: bw * 0.17, rim: 3, step: 30, soft: 1.5 });
      }, 1);
    });
    ctx.save(); ctx.translate(a[0], a[1]); ctx.rotate(ang); ctx.scale(1 / k, 1 / k);
    if (prog < 0.999) { // reveal along the drawn part, with a round wet head
      const part = polySlice(resample(q, 12), 0, prog), N = normalsOf(part, false), R2 = bw * 3, e = part[part.length - 1];
      ctx.beginPath(); ctx.moveTo(part[0][0] + N[0][0] * R2, part[0][1] + N[0][1] * R2);
      for (let i = 1; i < part.length; i++) ctx.lineTo(part[i][0] + N[i][0] * R2, part[i][1] + N[i][1] * R2);
      const an = Math.atan2(N[N.length - 1][1], N[N.length - 1][0]); ctx.arc(e[0], e[1], R2, an, an + Math.PI);
      for (let i = part.length - 1; i >= 0; i--) ctx.lineTo(part[i][0] - N[i][0] * R2, part[i][1] - N[i][1] * R2);
      ctx.closePath(); ctx.clip();
    }
    ctx.drawImage(sp.c, -sp.ox, -sp.oy, sp.w, sp.h); ctx.restore();
  }

  // ---------------------------------------------------------------- pieces
  const RB = 46; // node and halo washes are painted at this radius and scaled to the node
  const nodeWash = (color) => cached('wc:node:' + color, () => sprite(RB * 2 + 90, RB * 2 + 90, RB + 45, RB + 45, (g) => {
    const sd = hashStr('n' + color), r = mulberry32(sd), ox = (r() - 0.5) * 7, oy = (r() - 0.5) * 7;
    wash(g, ellipsePts(ox, oy, RB * 1.04, RB * 0.98, 11), color, { seed: sd, spread: 8.5, rim: 4.2 });
  }, 2.5));
  const haloWash = (color) => cached('wc:halo:' + color, () => sprite(RB * 4.4 + 90, RB * 4.4 + 90, RB * 2.2 + 45, RB * 2.2 + 45, (g) => {
    wash(g, ellipsePts(0, 0, RB * 1.75, RB * 1.75, 14), color, { seed: hashStr('h' + color), spread: 10, rim: 3.4, layers: 24 });
  }, 1.5));
  // an irregular wet front of radius rho around (x, y) as a clip path
  function wetFront(ctx, x, y, rho, seed) {
    ctx.beginPath();
    for (let i = 0; i <= 40; i++) { const an = (i / 40) * TAU, rr = rho * (1 + 0.16 * noise1(seed, (i % 40) / 4) + 0.06 * noise1(seed + 3, i / 1.5)); i ? ctx.lineTo(x + Math.cos(an) * rr, y + Math.sin(an) * rr) : ctx.moveTo(x + Math.cos(an) * rr, y + Math.sin(an) * rr); }
    ctx.closePath();
  }
  // a deckle-edged scrap of the paper (tags, slips, cards): soft shadow, the tooth, a pale wash of its colour
  function scrap(g, pts, sheet, tint, o = {}) {
    const k = Math.hypot(g.getTransform().a, g.getTransform().b) || 1, seed = seedOf(o.seed ?? 1);
    const body = o.smooth ? pts : tear(pts, o.deckle ?? 1.3, seed + 3, 5);
    if ((o.shadow ?? 8) > 0) { g.save(); g.shadowColor = S.shadow; g.shadowBlur = (o.shadow ?? 8) * k; g.shadowOffsetX = 1.5 * k; g.shadowOffsetY = (o.shadow ?? 8) * 0.45 * k; pathPts(g, body); g.fillStyle = sheet; g.fill(); g.restore(); }
    pathPts(g, body); g.fillStyle = sheet; g.fill();
    g.save(); pathPts(g, body); g.clip();
    if (tint) { const [x0, y0, x1, y1] = bbox(body), ins = Math.min(16, (x1 - x0) * 0.12, (y1 - y0) * 0.16);
      wash(g, o.washPoly || offsetPts(closedResample(body, 8), -ins), tint, { seed, layers: o.layers ?? 16, alpha: S.washA * (o.washK ?? 0.6), spread: o.spread ?? 4, rim: 1.8, gran: 0.6 }); }
    const [x0, y0, x1, y1] = bbox(body); tooth(g, x0, y0, x1 - x0, y1 - y0, o.tooth ?? 0.35, seed);
    g.restore();
    return body;
  }
  const inkOutline = (g, body, o = {}) => inkLine(g, [...body, body[0], body[1]], { color: o.color || S.ink, w: o.w ?? 2.2, seed: o.seed ?? 1, ends: false, amp: 0.6, alpha: o.alpha ?? 0.85 });
  const isScenery = (c) => c === S.cloud || (S.hills && S.hills.includes(c));

  defineStyle('watercolor', {
    base: 'paper',
    size: { chip: 40 }, // the kit pops chips from 0.6 scale on 'original': 40 keeps a flying chip's digits over 26 px
    palette(P, T, C) {
      const { mix, alpha: A, ensure } = C, dark = !!T && T.tone === 'dark', white = '#FFFFFF', black = '#000000';
      // the paper: a warm cold-press white (light themes: the theme's card toward its paper), or the theme's own dark
      // ground (dark themes: light pigment on dark paper, like gouache on black). Text pieces are lighter scraps of it.
      const paper = dark ? P.bg : mix(P.card, P.bg, 0.16), card = dark ? P.card : mix(P.card, white, 0.55);
      const washA = dark ? 0.072 : 0.042, washDeep = dark ? white : P.ink;
      const tints = dark ? [P.sky, P.lilac] : [P.sky, P.gold], hlA = dark ? 0.2 : 0.36, hlCard = mix(card, P.gold, hlA);
      const hills = [mix(P.cool, P.sky, 0.45), mix(P.good, P.gold, 0.4)], cloud = mix(P.sky, paper, 0.45);
      const bgWash = [P.sky, P.warm];
      // every surface text sits on: the paper and its pale background washes, the hills and clouds (washes of about
      // half strength), the scraps and their tint washes, a highlighted row
      const washOf = (c, k, on = paper) => mix(on, c, k);
      const surf = [paper, card, hlCard, ...tints.map((c) => washOf(c, 0.32, card)), ...bgWash.map((c) => washOf(c, 0.16)), ...hills.map((c) => washOf(c, 0.36)), washOf(cloud, 0.4)];
      const lift = (c, k) => ensure(c, surf, k);
      const ink = lift(P.ink, 8.5), inkSoft = lift(P.inkSoft, 6.5);
      const keys = ['accent', 'cool', 'gold', 'lilac', 'sky', 'good', 'bad', 'warm'];
      const txt = Object.fromEntries(keys.map((k) => [k, lift((T && P.txt && P.txt[k]) || (P.txt && P.txt[k]) || P[k], 6)]));
      const hues = keys.map((k) => P[k]);
      P.node.forEach((c, i) => { if (!hues.includes(c)) txt['node' + i] = lift(c, 6); });
      // ink on a wash of `fill`: on a full wash (a node, a burst; the centre is light, the pooled edge dense) and on a
      // scrap tinted with it; dark themes may need the paper's dark instead of the light ink
      const washed = new Set([...P.node, ...keys.map((k) => P[k])].filter((c) => typeof c === 'string').map((c) => c.toUpperCase()));
      const inkOn = (fill) => {
        if (typeof fill !== 'string' || fill[0] !== '#') return ink;
        // a palette colour is painted as a wash (light centre, dense edge, or a pale tint on a scrap); any other
        // colour is a flat fill (a table's header chip)
        fill = fill.toUpperCase();
        const ss = washed.has(fill) ? [washOf(fill, dark ? 0.62 : 0.3), washOf(fill, dark ? 0.95 : 0.78), washOf(fill, 0.35, card), fill] : [fill];
        // (a flat chip carries thin 32 px lettering, which measures well under its pair's ratio: it gets more headroom)
        const k = washed.has(fill) ? 6 : 7.5;
        if (C.worst(ink, ss) >= k) return ink;
        const best = [ink, P.bg, black, white].sort((a, b) => C.worst(b, ss) - C.worst(a, ss))[0]; // the best reader of all of them
        return ensure(best, ss, k);
      };
      const syntax = Object.fromEntries(Object.entries(P.syntax).map(([k, v]) => [k, ensure(v, [card, hlCard, ...tints.map((c) => washOf(c, 0.32, card))], 6.5)]));
      return {
        ...P, kind: 'paper', ...Object.fromEntries(P.node.map((c, i) => ['node' + i, c])), // node colours -> text shades (S.txtOf)
        bg: paper, bgDeep: paper, bgLight: paper, paper, card, cardEdge: card, cardInk: ink, ink, inkSoft, inkFaint: A(ink, 0.3),
        washA, washLayers: 30, washDeep, tints, bgWash, cardWashK: dark ? 0.2 : 0.32, reserve: dark ? [30, 1.3] : [14, 0.55], toothK: dark ? 0.2 : 0.22,
        rule: mix(card, P.sky, dark ? 0.35 : 0.4), margin: mix(card, P.bad, 0.45), sticky: mix(card, P.gold, 0.22), kraft: mix(card, P.warm, 0.18),
        shadow: dark ? A(black, 0.55) : A(P.shade, 0.2), glowShadow: dark ? null : A(P.shade, 0.2),
        hl: A(P.gold, hlA), glow: P.gold, txt, goodSoft: P.good, costTag: P.gold, spark: card,
        node: P.node, nodeInk: P.node.map(inkOn), burst: [P.warm, P.gold], syntax, codeDim: ensure(P.codeDim, [card, hlCard, ...tints.map((c) => washOf(c, 0.32, card))], 6),
        halo: A(paper, 0.9), chipTo: card, chipK: dark ? 0.75 : 0.55, burstHalo: null, tagHole: A(ink, 0.4), sheen: A(white, 0),
        hills, cloud, inkOn,
        vignette: dark ? P.vignette : A(P.shade, 0.12), keyLight: dark ? null : [A(white, 0.16), A(white, 0)], deepBlob: 0,
        grain: dark ? 0.22 : 0.2, grainBlend: dark ? 'screen' : 'multiply', grainSpecks: [A(white, 0.1), A(black, 0.1)],
        stroke: { w: 3.4, rough: 0.8, passes: 1, chalk: false }, boilFps: 10, boilAmp: 0, jitter: 0, grainBoil: false, mascot: false,
        textBoil: 0, float: 0,
      };
    },

    // a piece lands like a drop: it appears a touch large and settles, with no squash and no bounce (never drawn
    // smaller than its size, so a tag's label is never caught under 26 px while it arrives)
    pop(t, t0, d = 0.55) {
      if (!(t >= t0)) return { s: 0, sx: 0, sy: 0 };
      const u = (t - t0) / (d * 0.8); if (u >= 1) return { s: 1, sx: 1, sy: 1 };
      const s = 1 + 0.07 * (1 - Ease.out(u)); return { s, sx: s, sy: s };
    },

    stroke(ctx, pts, o = {}) {
      const prog = o.prog ?? 1, from = o.from ?? 0, base = ctx.globalAlpha;
      if (prog - from <= 0.001 || pts.length < 2 || base * (o.alpha ?? 1) <= 0.003) return;
      const seed = seedOf(o.seed ?? 1), w = o.w ?? S.stroke.w, color = o.color || S.ink;
      const part = polySlice(roughen(pts, seed, o.amp ?? S.stroke.rough, o.ends ?? true), from, prog); // laid once: no boil
      ctx.save(); ctx.globalAlpha = base * (o.alpha ?? 1);
      const route = o.glow && o.t != null && from <= 0 && !o.dash && pts.length > 6; // the route, a trail (not their arrowheads): a wash along it
      if (route) routeWash(ctx, pts, w, color, prog, seed);
      const path = new Path2D(), endK = smooth(0.85, 1, prog);
      if (o.dash) dashPath(path, part, w, seed, o.dash, o.dashOffset || 0);
      else brushPath(path, part, route ? w * 0.5 : w, seed, endK);
      ctx.fillStyle = route ? textInk(color) : color; ctx.globalAlpha *= o.glow && !route ? 0.85 : 0.94; ctx.fill(path);
      ctx.restore();
    },
    penTip() {}, // the brush leaves no dot

    // hatch: false marks a piece that carries text (tags, slips, a burst's middle). With no shadow it is paper left
    // bare inside a wash (a burst's middle); otherwise a scrap of paper with a pale wash of its colour
    cutout(g, pts, color, o = {}) {
      const seed = o.seed ?? 1;
      if (o.hatch === false) {
        if (o.shadow === 0) { // reserved paper: no edge, no shadow, a breath of its colour
          const body = tear(pts, 1.6, seedOf(seed) + 3, 6); pathPts(g, body); g.fillStyle = S.paper; g.fill();
          wash(g, offsetPts(closedResample(body, 8), -6), color, { seed, layers: S.reserve[0], alpha: S.washA * S.reserve[1], spread: 5, gran: 0.5 });
          return body;
        }
        const body = scrap(g, pts, S.card, color === S.card ? null : color, { seed, shadow: Math.min(o.shadow ?? 7, 7), deckle: 1.1 });
        inkOutline(g, body, { color: o.line || S.ink, w: 1.8, seed, alpha: 0.7 });
        return body;
      }
      const scenery = isScenery(color);
      wash(g, pts, color, { seed, spread: scenery ? 12 : Math.max(5, Math.min(10, polyLength(pts) / 50)), rim: scenery ? 3.6 : 3.4, layers: scenery ? 24 : 30, alpha: S.washA * (scenery ? (color === S.cloud ? 0.38 : 0.5) : 1), step: scenery ? 20 : 22, soft: scenery ? 1.6 : 1.1 });
      if (!scenery) inkOutline(g, closedResample(pts, 6), { seed, w: 2.2, alpha: 0.8 });
      return pts;
    },

    card(g, w, h, kind, color, seed, o) {
      const tint = kind === 'sticky' ? S.gold : kind === 'kraft' ? S.warm : S.tints[Math.abs(Math.floor(seed)) % S.tints.length];
      const body = scrap(g, rrPts(0, 0, w, h, 4), color, tint, { seed, shadow: 12, deckle: kind === 'label' ? 1.6 : 1.2, layers: 14, washK: S.cardWashK, spread: Math.min(10, h * 0.05),
        washPoly: rrPts(w * 0.06, h * 0.1, w * 0.88, h * 0.8, 20) });
      if (kind === 'note') { // pale ruled lines and a margin, painted with a fine brush
        for (let y = o.first || 90; y < h - 8; y += o.rule || 50) inkLine(g, [[6, y], [w - 6, y]], { color: S.rule, w: 1.7, seed: seed + y, amp: 0.4, ends: false, alpha: 0.9 });
        inkLine(g, [[o.marginX || 60, 4], [o.marginX || 60, h - 4]], { color: S.margin, w: 2, seed: seed + 3, amp: 0.4, ends: false });
      }
      inkRect(g, 5, 5, w - 10, h - 10, { color: S.ink, w: kind === 'label' ? 2.6 : 2.2, seed, amp: 1.2, alpha: 0.78 });
      void body;
    },

    disc(g, label, color, ink, r, font) {
      const sp = nodeWash(color); blit(g, sp, 0, 0, { s: r / RB });
      inkEllipse(g, 0, 0, r, r, { color: S.ink, w: Math.max(2.4, r * 0.065), seed: hashStr(label + color), turns: 1.04 });
      drawText(g, label, 0, 0, { font, size: r * (label.length > 2 ? 0.8 : 1.15), color: S.inkOn(color), align: 'center', base: 'middle' });
    },

    // graph nodes bloom: the wash spreads through a growing wet front, then the ink ring is drawn and the label written
    node(ctx, x, y, r, label, color, t, t0, alpha) {
      if (t < t0 || alpha <= 0.003) return;
      const u = clamp((t - t0) / 0.7), seed = hashStr('wn' + color);
      ctx.save(); ctx.globalAlpha *= alpha;
      ctx.save(); if (u < 1) { wetFront(ctx, x, y, r * (0.12 + 1.4 * Ease.out(u)), seed); ctx.clip(); }
      blit(ctx, nodeWash(color), x, y, { s: r / RB }); ctx.restore();
      inkEllipse(ctx, x, y, r, r, { color: S.ink, w: Math.max(2.4, r * 0.065), prog: P(t, t0 + 0.12, 0.45, Ease.inOut), seed, turns: 1.04 });
      const wr = P(t, t0 + 0.3, 0.25, Ease.lin);
      if (wr > 0) drawText(ctx, label, x, y, { font: 'brush', size: r * (label.length > 2 ? 0.8 : 1.15), color: S.inkOn(color), align: 'center', base: 'middle', write: wr, t });
      ctx.restore();
    },

    // the target's state: a halo wash blooms behind the node in the glow colour
    glow(ctx, x, y, r, color, k, t, t0) {
      const u = clamp((t - t0) / 0.8), rr = r / 2.4, seed = hashStr('wh' + color);
      ctx.save(); ctx.globalAlpha *= k;
      if (u < 1) { wetFront(ctx, x, y, rr * (0.6 + 2.0 * Ease.out(u)), seed); ctx.clip(); }
      blit(ctx, haloWash(color), x, y, { s: rr / RB }); ctx.restore();
    },

    backdrop(g, pw, ph, r) {
      g.fillStyle = S.paper; g.fillRect(0, 0, pw, ph);
      const pad = BACK.pad;
      // a few pale washes laid on the paper before anything else (most of their area is outside the frame)
      [[S.bgWash[0], pad + W * 0.94, pad + H * 0.02, 430, 11], [S.bgWash[1], pad + W * 0.02, pad + H * 1.0, 380, 12], [S.bgWash[0], pad - 260, pad + H * 0.3, 300, 13]].forEach(([c, x, y, rad, s]) => {
        wash(g, ellipsePts(x, y, rad * 1.3, rad, 12), c, { seed: s, layers: 22, alpha: S.washA * 0.3, spread: rad * 0.12, rim: 5, step: 60, soft: 2 });
      });
      tooth(g, 0, 0, pw, ph, 1, 7);
      void r;
    },

    plane(ctx, o) {
      const sp = cached('wc:plane', () => sprite(200, 120, 80, 50, (g) => {
        const top = [[66, 0], [-50, -26], [-30, -1]], under = [[66, 0], [-34, -2], [-46, 20]], mid = [[66, 0], [-34, -2], [-22, 9]];
        for (const p of [under, mid, top]) { pathPts(g, p); g.fillStyle = S.card; g.fill(); }
        wash(g, under, S.accent, { seed: 31, layers: 18, spread: 2, rim: 1.4, step: 12 });
        wash(g, mid, S.sky, { seed: 32, layers: 14, alpha: S.washA * 0.7, spread: 2, rim: 1.2, step: 12 });
        for (const [p, s] of [[under, 1], [mid, 2], [top, 3]]) inkLine(g, [...p, p[0], p[1]], { color: S.ink, w: 2.6, seed: 'plane' + s, ends: false, amp: 0.4 });
      }, 2.5));
      blit(ctx, sp, 0, 0);
      for (let i = 0; i < 2; i++) { const ph = ((o.t || 0) * 2.2 + i * 0.5) % 1; inkLine(ctx, [[-62 - ph * 40, -12 + i * 16], [-96 - ph * 40, -12 + i * 16]], { color: S.inkFaint, w: 2.4, seed: 'wind' + i, alpha: 1 - ph, amp: 0.3 }); }
    },
  });
})();
