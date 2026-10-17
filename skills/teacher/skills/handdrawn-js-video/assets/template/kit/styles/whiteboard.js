// kit/styles/whiteboard.js: the graph draws itself on a whiteboard (a dark glass board on dark registry themes).
//   strokes   marker lines with a pressure taper (a filled outline, perfect-freehand's idea), revealed along their
//             length as the scenes key them; settled strokes boil very lightly (10 fps, under a pixel)
//   pen       a marker follows the tip of whatever is being drawn or written, hidden between strokes
//   fills     hachure on the highlighted route (every glowing stroke), nodes, bursts and stars
//   labels    Caveat Bold (OFL, @fontsource/caveat 700), scaled up for its small x-height, with a thin marker outline
//   board     faint ghosting of old marker, locked to the world so drawings never slide on it; boards are sheets
//             held by magnets; chapter changes are an eraser wipe and a corner label drawn in marker
// Colours: every token is derived from the paper palette (original or themed) in palette(); nothing new is invented.
// This file loads before the kit: kit functions (inkLine, roughen, drawText, ...) are only called inside hooks.
'use strict';
(() => {
  const WB = { tips: [] }; // pen tips seen while the current frame draws (reset each frame: never carried across frames)

  // ---------------------------------------------------------------- geometry
  // sub-pixel re-trace of a settled stroke (the boil): smooth noise along the normals
  function wobble(p, seed, amp) {
    const N = normalsOf(p, false);
    return p.map((q, i) => { const d = amp * noise1(seed, i / 7); return [q[0] + N[i][0] * d, q[1] + N[i][1] * d]; });
  }
  // marker body: the outline of a pressure-tapered stroke with round ends, added to `path` (filled once: no overlaps)
  function taperPath(path, p, w, seed, endK) {
    if (p.length < 2) return;
    const c = polyCum(p), L = c[c.length - 1] || 1, tl = Math.min(L * 0.32, w * 6), N = normalsOf(p, false), n = p.length;
    const hw = c.map((d) => {
      const a = 0.42 + 0.58 * smooth(0, tl, d), b = 0.42 + 0.58 * smooth(0, tl, L - d);
      return w * 0.5 * Math.min(a, 1 - (1 - b) * endK) * (1 + 0.1 * noise1(seed + 5, d / 55));
    });
    path.moveTo(p[0][0] + N[0][0] * hw[0], p[0][1] + N[0][1] * hw[0]);
    for (let i = 1; i < n; i++) path.lineTo(p[i][0] + N[i][0] * hw[i], p[i][1] + N[i][1] * hw[i]);
    const ae = Math.atan2(N[n - 1][1], N[n - 1][0]); path.arc(p[n - 1][0], p[n - 1][1], hw[n - 1], ae, ae + Math.PI);
    for (let i = n - 1; i >= 0; i--) path.lineTo(p[i][0] - N[i][0] * hw[i], p[i][1] - N[i][1] * hw[i]);
    const as = Math.atan2(N[0][1], N[0][0]); path.arc(p[0][0], p[0][1], hw[0], as + Math.PI, as + 2 * Math.PI);
    path.closePath();
  }
  // hachure: parallel marker lines clipped to a polygon, spaced from an anchor so they travel with the shape.
  // o: {gap, angle, w, alpha, seed, anchor, prog (0..1 of the lines, swept along the normal)}
  function hachure(ctx, poly, color, o = {}) {
    const [x0, y0, x1, y1] = bbox(poly), ang = o.angle ?? -0.72, gap = o.gap ?? 8, ca = Math.cos(ang), sa = Math.sin(ang);
    const [ax, ay] = o.anchor || [x0, y0], seed = seedOf(o.seed ?? 1), corners = [[x0, y0], [x1, y0], [x0, y1], [x1, y1]];
    const ks = corners.map(([x, y]) => (x - ax) * -sa + (y - ay) * ca), ts = corners.map(([x, y]) => (x - ax) * ca + (y - ay) * sa);
    const k0 = Math.floor(Math.min(...ks) / gap), k1 = Math.ceil(Math.max(...ks) / gap), t0 = Math.min(...ts) - 12, t1 = Math.max(...ts) + 12;
    const kEnd = k0 + (k1 - k0) * clamp(o.prog ?? 1); if (kEnd <= k0) return;
    ctx.save(); pathPts(ctx, poly); ctx.clip(); ctx.beginPath();
    for (let k = k0; k <= kEnd; k++) {
      const off = k * gap + (rnd(seed, k) - 0.5) * gap * 0.3, px = ax - sa * off, py = ay + ca * off, j = (rnd(seed, k + 977) - 0.5) * gap * 0.5;
      ctx.moveTo(px + ca * t0 - sa * j, py + sa * t0 + ca * j); ctx.lineTo(px + ca * t1 + sa * j, py + sa * t1 - ca * j);
    }
    ctx.strokeStyle = color; ctx.lineWidth = o.w ?? 2; ctx.lineCap = 'round'; ctx.globalAlpha *= o.alpha ?? 0.5; ctx.stroke(); ctx.restore();
  }
  // a hachured band along a drawn route (what a glow becomes on a whiteboard)
  function band(ctx, part, w, color, seed) {
    if (part.length < 2) return;
    const N = normalsOf(part, false), bw = w * 1.9;
    const poly = [...part.map((q, i) => [q[0] + N[i][0] * bw, q[1] + N[i][1] * bw]), ...part.map((q, i) => [q[0] - N[i][0] * bw, q[1] - N[i][1] * bw]).reverse()];
    ctx.save(); pathPts(ctx, poly); ctx.fillStyle = hexA(color, 0.1); ctx.fill(); ctx.restore();
    hachure(ctx, poly, color, { gap: Math.max(6, w * 0.85), w: Math.max(1.6, w * 0.24), alpha: 0.55, seed, anchor: part[0] });
  }
  const tint = (c) => mixHex(c, S.board, S.tintK);
  // the pen: remember where the tip is, in canvas pixels (only on the film canvas, never inside a sprite)
  function tipAt(ctx, pt, color, prog) {
    if (typeof CANVAS === 'undefined' || ctx.canvas !== CANVAS) return;
    const m = ctx.getTransform();
    WB.tips.push({ x: m.a * pt[0] + m.c * pt[1] + m.e, y: m.b * pt[0] + m.d * pt[1] + m.f, s: Math.hypot(m.a, m.b), color, prog });
  }

  // a node or badge: hachured tint, marker ring drawn on, label written. o: {ring, fill, write (0..1), t, tip, font, seed}
  function drawDisc(ctx, x, y, r, label, color, o = {}) {
    const seed = o.seed ?? hashStr(label + color), fillP = o.fill ?? 1;
    if (fillP > 0) {
      const poly = ellipsePts(x, y, r * 0.93, r * 0.93, 40);
      ctx.save(); ctx.globalAlpha *= fillP; pathPts(ctx, poly); ctx.fillStyle = tint(color); ctx.fill(); ctx.restore();
      hachure(ctx, poly, color, { gap: Math.max(6, r * 0.17), w: Math.max(1.6, r * 0.05), alpha: 0.6, seed, anchor: [x - r, y - r], prog: fillP });
    }
    inkEllipse(ctx, x, y, r, r, { color: S.ink, w: Math.max(2.6, r * 0.08), prog: o.ring ?? 1, seed, t: o.t, tip: o.tip, turns: 1.1 });
    if ((o.write ?? 1) > 0) drawText(ctx, label, x, y, { font: o.font || 'brush', size: r * (label.length > 2 ? 0.8 : 1.15), color: S.ink, align: 'center', base: 'middle', halo: S.halo, haloW: 6, write: o.write, t: o.t, tip: o.tip ? undefined : false });
  }

  // ---------------------------------------------------------------- the pen and the eraser (drawn, not sprites)
  function drawMarker(ctx, color) {
    const M = S.marker;
    ctx.save(); ctx.shadowColor = S.shadow; ctx.shadowBlur = 14; ctx.shadowOffsetX = 9; ctx.shadowOffsetY = 15;
    pathPts(ctx, rrPts(30, -13, 142, 26, 9)); ctx.fillStyle = M.body; ctx.fill(); ctx.restore();
    pathPts(ctx, [[0, -2.4], [15, -5], [15, 5], [0, 2.4]]); ctx.fillStyle = color; ctx.fill();                 // felt tip
    pathPts(ctx, [[14, -6], [32, -12.5], [32, 12.5], [14, 6]]); ctx.fillStyle = M.collar; ctx.fill();         // collar
    pathPts(ctx, rrPts(30, -13, 142, 26, 9)); ctx.fillStyle = M.body; ctx.fill(); ctx.strokeStyle = M.edge; ctx.lineWidth = 1.4; ctx.stroke();
    ctx.fillStyle = color; ctx.fillRect(74, -13, 44, 26);                                                       // colour band
    pathPts(ctx, rrPts(166, -14.5, 20, 29, 7)); ctx.fill();                                                      // cap end
    ctx.strokeStyle = M.shine; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(40, -7); ctx.lineTo(160, -7); ctx.stroke();
    ctx.restore();
  }
  function drawEraser(ctx) {
    const E = S.eraser;
    ctx.save(); ctx.shadowColor = S.shadow; ctx.shadowBlur = 18; ctx.shadowOffsetX = 10; ctx.shadowOffsetY = 16;
    pathPts(ctx, rrPts(-80, -34, 160, 68, 14)); ctx.fillStyle = E.top; ctx.fill(); ctx.restore();
    pathPts(ctx, rrPts(-80, 12, 160, 24, 7)); ctx.fillStyle = E.felt; ctx.fill();
    pathPts(ctx, rrPts(-80, -34, 160, 68, 14)); ctx.strokeStyle = E.edge; ctx.lineWidth = 2; ctx.stroke();
    ctx.strokeStyle = S.marker.shine; ctx.lineWidth = 3; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(-62, -22); ctx.lineTo(60, -22); ctx.stroke();
    ctx.restore();
  }
  // one eraser pass: keys [[t, x, y], ...] in screen units. Behind it a soft wiped streak that fades in half a second.
  function drawWipe(ctx, t, keys) {
    const a = keys[0][0], b = keys[keys.length - 1][0]; if (t < a) return;
    ctx.save(); ctx.lineCap = 'butt'; ctx.lineJoin = 'round'; ctx.strokeStyle = S.board; ctx.lineWidth = 128;
    const step = 1 / 60; let prev = track(a, keys);
    for (let ts = a + step; ts <= Math.min(t, b) + 1e-6; ts += step) {
      const cur = track(ts, keys), k = 0.62 * (1 - clamp((t - ts) / 0.5)); if (k > 0.004) { ctx.globalAlpha = k; ctx.beginPath(); ctx.moveTo(prev[0], prev[1]); ctx.lineTo(cur[0], cur[1]); ctx.stroke(); }
      prev = cur;
    }
    ctx.lineWidth = 3; ctx.strokeStyle = S.ghost; prev = track(a, keys); // the faint smear the felt leaves
    for (let ts = a + step; ts <= Math.min(t, b) + 1e-6; ts += step) {
      const cur = track(ts, keys), k = 1 - clamp((t - ts) / 0.9); if (k > 0.004) { ctx.globalAlpha = k; ctx.beginPath(); for (const o of [-38, -12, 22, 44]) { ctx.moveTo(prev[0], prev[1] + o); ctx.lineTo(cur[0], cur[1] + o); } ctx.stroke(); }
      prev = cur;
    }
    ctx.restore();
    if (t > b) return;
    const [x, y] = track(t, keys), [x2, y2] = track(t + 0.02, keys);
    ctx.save(); ctx.translate(x, y); ctx.rotate(clamp(Math.atan2(y2 - y, x2 - x) * 0.12, -0.3, 0.3) - 0.08); ctx.scale(1.35, 1.35); drawEraser(ctx); ctx.restore();
  }

  defineStyle('whiteboard', {
    base: 'paper',
    font: { hand: 'Caveat Bold', brush: 'Caveat Bold' },
    size: { chapterCorner: 0.62 }, // the corner label keeps its lower-case words over 26 px measured
    palette(P, T, C) {
      const { mix, alpha: A, ensure } = C, dark = !!T && T.tone === 'dark', white = '#FFFFFF';
      // the board: near white (a light theme's paper lifted toward white), or the theme's own dark ground as glass.
      // Boards (notes, code, tables) are sheets a shade off the board, held on it by magnets.
      const board = dark ? P.bg : mix(P.card, white, 0.72), card = dark ? P.card : mix(P.card, P.bg, 0.25);
      const tintK = dark ? 0.7 : 0.8, hlA = dark ? 0.16 : 0.42, hlCard = mix(card, P.gold, hlA);
      const surf = [board, card, hlCard, mix(P.gold, board, tintK)]; // every surface text sits on (the last: a burst's middle)
      const lift = (c, k) => ensure(c, surf, k);
      const ink = lift(P.ink, 8.5), inkSoft = lift(T ? P.inkSoft : mix(P.ink, board, 0.3), 6.5);
      // text in a meaning colour: the theme's solved ink, or the paper marker colour darkened just enough
      const txt = Object.fromEntries(['accent', 'cool', 'gold', 'lilac', 'sky', 'good', 'bad', 'warm'].map((k) => [k, lift((T && P.txt && P.txt[k]) || P[k], 6)]));
      const hues = ['accent', 'cool', 'gold', 'lilac', 'sky', 'good', 'bad', 'warm'].map((k) => P[k]);
      P.node.forEach((c, i) => { if (!hues.includes(c)) txt['node' + i] = lift(c, 6); }); // a node colour that is no meaning colour
      const syntax = Object.fromEntries(Object.entries(P.syntax).map(([k, v]) => [k, ensure(v, [card, hlCard], 6.5)]));
      return {
        ...P, kind: 'whiteboard', ...Object.fromEntries(P.node.map((c, i) => ['node' + i, c])), // node colours -> text shades (S.txtOf)
        bg: board, bgDeep: board, bgLight: board, board, card, cardEdge: ink, cardInk: ink, ink, inkSoft, inkFaint: A(ink, 0.3),
        rule: mix(card, P.sky, dark ? 0.3 : 0.22), margin: mix(card, P.bad, 0.35), sticky: mix(card, P.gold, 0.35), kraft: mix(card, P.warm, 0.25),
        sheetEdge: A(ink, 0.14), tintK,
        shadow: dark ? A('#000000', 0.55) : A(ink, 0.18), glowShadow: dark ? null : A(ink, 0.16),
        hl: A(P.gold, hlA), glow: A(P.gold, dark ? 0.34 : 0.4), txt, goodSoft: txt.good,
        node: P.node, nodeInk: P.node.map(() => ink), burst: [P.warm, P.gold], syntax, codeDim: ensure(P.codeDim, [card, hlCard], 6),
        halo: A(board, 0.92), capBand: A(card, 0.95), lineFill: A(board, 0.9), boardFill: board, costTag: mix(card, P.gold, 0.3), chipTo: card,
        vignette: dark ? P.vignette : A(ink, 0.06), keyLight: dark ? null : [A(white, 0.2), A(white, 0)], deepBlob: 0,
        grain: dark ? 0.16 : 0.1, grainBlend: dark ? 'screen' : 'multiply',
        sheenHi: A(dark ? P.ink : white, dark ? 0.035 : 0.55), sheenLo: A(dark ? '#000000' : ink, dark ? 0.12 : 0.025),
        ghost: A(ink, dark ? 0.05 : 0.042), ghostWipe: A(ink, dark ? 0.018 : 0.014), glass: dark,
        marker: { body: dark ? mix(card, ink, 0.55) : mix(board, ink, 0.05), collar: mix(board, ink, dark ? 0.35 : 0.22), edge: A(dark ? board : ink, 0.4), shine: A(white, dark ? 0.25 : 0.6) },
        eraser: { top: mix(P.sky, ink, 0.3), felt: mix(board, ink, dark ? 0.45 : 0.24), edge: A(ink, 0.25) },
        stroke: { w: 4.4, rough: 1.0, passes: 1, chalk: false }, boilFps: 10, boilAmp: 0.45, jitter: 0, grainBoil: false, mascot: false,
        fontFiles: { hand: 'fonts/caveat-latin-700-normal.woff', brush: 'fonts/caveat-latin-700-normal.woff' },
        // Caveat's x-height is 0.37 em (Patrick Hand 0.48), and legibility.py measures a lower-case word by it, so body
        // sizes grow to about 53 px at the 40 px label size; big sizes only by 10%. A thin outline gives marker weight.
        fontSize: (fk, size) => (fk === 'hand' ? Math.max(size * 1.12, size * 0.6 + 29) : size * 1.1), textStroke: 0.028,
        textBoil: 0.3, backDepth: 1, float: 0,
      };
    },

    beginFrame() { WB.tips.length = 0; },

    stroke(ctx, pts, o = {}) {
      const prog = o.prog ?? 1, from = o.from ?? 0, base = ctx.globalAlpha;
      if (prog - from <= 0.001 || pts.length < 2 || base * (o.alpha ?? 1) <= 0.003) return;
      const seed = seedOf(o.seed ?? 1), w = o.w ?? S.stroke.w, color = o.color || S.ink;
      let rp = roughen(pts, seed, o.amp ?? S.stroke.rough, o.ends ?? true); // one fixed shape while it is drawn
      const settled = o.t != null && from <= 0 ? smooth(0.96, 1, prog) : 0;
      if (settled > 0 && S.boilAmp > 0) rp = wobble(rp, boilSeed(seed, o.t), S.boilAmp * settled);
      const part = polySlice(rp, from, prog);
      ctx.save(); ctx.globalAlpha = base * (o.alpha ?? 1);
      if (o.glow && from <= 0) band(ctx, part, w, color, seed);
      if (o.dash) {
        ctx.setLineDash(o.dash); ctx.lineDashOffset = o.dashOffset || 0; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
        ctx.lineWidth = w * 0.9; ctx.strokeStyle = color; pathPts(ctx, part, false); ctx.stroke();
      } else { const path = new Path2D(); taperPath(path, part, w, seed, smooth(0.8, 1, prog)); ctx.fillStyle = color; ctx.fill(path); }
      ctx.restore();
      if (o.tip && prog < 0.999 && from <= 0) tipAt(ctx, part[part.length - 1], color, prog);
    },
    penTip(ctx, x, y, color, write) { tipAt(ctx, [x, y], color, write); },

    cutout(g, pts, color, o = {}) {
      const plain = color === S.card, tag = plain || color === S.costTag;
      if (tag) pts = offsetPts(pts, 7); // a tag or slip: room between its words and the marker outline
      pathPts(g, pts); g.fillStyle = plain ? S.card : tint(color); g.fill();
      if (!plain && o.hatch !== false) hachure(g, pts, color, { gap: 7, w: 1.8, alpha: 0.6, seed: o.seed ?? 1 });
      inkLine(g, [...pts, pts[0]], { color: o.line || (plain ? S.ink : color), w: plain ? 2.4 : 2.8, seed: o.seed ?? 1, ends: false, amp: 0.7 });
      return pts;
    },

    card(g, w, h, kind, color, seed, o) {
      if (kind === 'label') { // a box drawn straight on the board; filled with the board so it reads over anything
        pathPts(g, rrPts(0, 0, w, h, 10)); g.fillStyle = S.board; g.fill();
        inkRect(g, 4, 4, w - 8, h - 8, { color: S.ink, w: 3.6, seed, amp: 1.4 });
        inkRect(g, 9, 8, w - 17, h - 15, { color: S.ink, w: 1.8, seed: seed + 7, amp: 1.8, alpha: 0.45 });
        return;
      }
      // a sheet held on the board by magnets (the tape count of the paper card)
      g.save(); g.shadowColor = S.shadow; g.shadowBlur = 12; g.shadowOffsetY = 5; g.shadowOffsetX = 2;
      pathPts(g, rrPts(0, 0, w, h, 3)); g.fillStyle = color; g.fill(); g.restore();
      pathPts(g, rrPts(0, 0, w, h, 3)); g.strokeStyle = S.sheetEdge; g.lineWidth = 1.2; g.stroke();
      if (kind === 'note') {
        g.strokeStyle = S.rule; g.lineWidth = 1.6;
        for (let y = o.first || 90; y < h - 8; y += o.rule || 50) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
        g.strokeStyle = S.margin; g.lineWidth = 2; g.beginPath(); g.moveTo(o.marginX || 60, 0); g.lineTo(o.marginX || 60, h); g.stroke();
      }
      const nt = o.tape ?? 2, at = nt === 1 ? [w / 2] : nt === 2 ? [w * 0.1, w * 0.9] : [];
      at.forEach((x, i) => {
        const col = S.node[(seed + i * 3) % S.node.length];
        g.save(); g.shadowColor = S.shadow; g.shadowBlur = 6; g.shadowOffsetY = 4; g.shadowOffsetX = 2;
        g.beginPath(); g.arc(x, 8, 15, 0, TAU); g.fillStyle = col; g.fill(); g.restore();
        g.beginPath(); g.arc(x, 8, 15, 0, TAU); g.strokeStyle = S.sheetEdge; g.lineWidth = 1.2; g.stroke();
        g.strokeStyle = S.marker.shine; g.lineWidth = 3; g.lineCap = 'round'; g.beginPath(); g.arc(x, 8, 9, -2.6, -1.4); g.stroke();
      });
    },

    disc(g, label, color, ink, r, font) { drawDisc(g, 0, 0, r, label, color, { font }); },

    // graph nodes draw themselves: the ring is drawn on with the pen, the hachure sweeps in, the label is written
    node(ctx, x, y, r, label, color, t, t0, alpha) {
      if (t < t0 || alpha <= 0.003) return;
      ctx.save(); ctx.globalAlpha *= alpha;
      drawDisc(ctx, x, y, r, label, color, { ring: P(t, t0, 0.42, Ease.inOut), fill: P(t, t0 + 0.28, 0.3, Ease.out), write: P(t, t0 + 0.36, 0.24, Ease.lin), t, tip: true, seed: hashStr('node' + color) });
      ctx.restore();
    },

    backdrop(g, pw, ph, r) {
      g.fillStyle = S.board; g.fillRect(0, 0, pw, ph);
      // a broad soft sheen across the board (room light on a glossy surface)
      const sh = g.createLinearGradient(0, 0, pw * 0.8, ph);
      sh.addColorStop(0, S.sheenHi); sh.addColorStop(0.42, hexA(S.board, 0)); sh.addColorStop(1, S.sheenLo);
      g.fillStyle = sh; g.fillRect(0, 0, pw, ph);
      if (S.glass) for (const [x, wd] of [[0.28, 0.11], [0.45, 0.04], [0.74, 0.07]]) { // reflections on dark glass
        g.fillStyle = S.sheenHi; g.beginPath(); g.moveTo(pw * x, 0); g.lineTo(pw * (x + wd), 0); g.lineTo(pw * (x + wd - 0.3), ph); g.lineTo(pw * (x - 0.3), ph); g.closePath(); g.fill();
      }
      // ghosting: old marker that was never quite erased, and the swirls of the eraser
      g.lineCap = 'round'; g.lineJoin = 'round';
      for (let i = 0; i < 14; i++) {
        const x = r() * pw, y = r() * ph, L = 260 + r() * 520, a = (r() - 0.5) * 0.8;
        g.strokeStyle = S.ghostWipe; g.lineWidth = 60 + r() * 90;
        g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + L / 2, y + (r() - 0.5) * 160, x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
      }
      for (let i = 0; i < 34; i++) {
        const x = r() * pw, y = r() * ph, kind = Math.floor(r() * 4), s = 40 + r() * 120, a0 = r() * TAU, ry = 0.5 + r() * 0.5;
        let p;
        if (kind === 0) p = Array.from({ length: 40 }, (_, k) => { const a = a0 + (k / 39) * TAU * 0.9; return [x + Math.cos(a) * s, y + Math.sin(a) * s * ry]; });
        else if (kind === 1) p = [[x, y], [x + s * 1.6, y + (r() - 0.5) * 30]];
        else if (kind === 2) p = [[x, y], [x + s * 1.4, y + 4], [x + s * 1.4 - 3, y + s * 0.8], [x + 2, y + s * 0.8 - 3], [x, y + 6]];
        else p = Array.from({ length: 16 }, (_, k) => [x + k * s * 0.1, y + Math.sin(k * 1.9 + a0) * s * 0.1]); // a scribbled word
        g.strokeStyle = S.ghost; g.lineWidth = 3 + r() * 4; g.globalAlpha = 0.45 + r() * 0.5;
        pathPts(g, roughen(kind === 3 ? p : resample(p, 12), 400 + i, 2.2), false); g.stroke();
      }
      g.globalAlpha = 1;
    },

    overlay(ctx) {
      if (!WB.tips.length) return;
      const tip = WB.tips.reduce((a, b) => (b.prog < a.prog ? b : a)); // the newest stroke has the pen
      const k = CANVAS.width / W, sc = clamp(tip.s / k, 0.8, 1.25) * k;
      ctx.save(); ctx.setTransform(1, 0, 0, 1, 0, 0); ctx.translate(tip.x, tip.y); ctx.scale(sc, sc); ctx.rotate(-0.95);
      drawMarker(ctx, tip.color); ctx.restore();
    },

    plane(ctx, o) {
      const top = [[66, 0], [-50, -26], [-30, -1]], under = [[66, 0], [-34, -2], [-46, 20]], mid = [[66, 0], [-34, -2], [-22, 9]];
      for (const p of [under, mid, top]) { pathPts(ctx, p); ctx.fillStyle = S.board; ctx.fill(); }
      hachure(ctx, under, S.accent, { gap: 6, w: 1.8, alpha: 0.7, seed: 31, anchor: [0, 0] });
      hachure(ctx, mid, S.accent, { gap: 6, w: 1.8, alpha: 0.35, seed: 32, anchor: [0, 0] });
      for (const [p, s] of [[under, 1], [mid, 2], [top, 3]]) inkLine(ctx, [...p, p[0]], { color: S.ink, w: 3, seed: 'plane' + s, t: o.t, ends: false, amp: 0.5 });
    },

    // chapter changes: an eraser wipes the old corner label off and sweeps the board, then the new label is drawn
    // in the corner with the pen (box, number ring, name), written by the chapter start like the paper label
    chapterLabels(o = {}) {
      const skip = new Set(o.skip ?? [0]), chs = TIMING_.chapters.filter((c) => !skip.has(c.n));
      const size = S.size.chapter, cs = S.size.chapterCorner ?? 0.56, h = 150;
      const ws = chs.map((c) => Math.ceil((measureText(c.name, 'brush', size) + 200) / 20) * 20);
      const pass = (t0) => [[t0 - 0.05, -170, 142], [t0 + 0.3, 780, 150], [t0 + 0.62, 1640, 380], [t0 + 0.95, 300, 640], [t0 + 1.25, 2120, 790]];
      screen(o.z ?? 95, (ctx, t) => {
        chs.forEach((c, j) => {
          const w = ws[j], tIn = c.start - 0.5, nxt = chs[j + 1], tOut = nxt ? nxt.start - 0.8 : TIMING_.total + 1;
          if (t < tIn || t > tOut + 0.35) return;
          ctx.save();
          if (t > tOut) { const ex = track(t, pass(tOut))[0]; ctx.beginPath(); ctx.rect(ex + 50, 0, W, H); ctx.clip(); } // wiped where the eraser has passed
          ctx.translate(96, 100); ctx.scale(cs, cs);
          ctx.save(); ctx.globalAlpha *= P(t, tIn, 0.18); pathPts(ctx, rrPts(0, 0, w, h, 12)); ctx.fillStyle = S.board; ctx.fill(); ctx.restore();
          inkRect(ctx, 4, 4, w - 8, h - 8, { color: S.ink, w: 5.5, prog: P(t, tIn, 0.3, Ease.inOut), seed: 'chb' + c.n, t, tip: true, amp: 1.4 });
          drawDisc(ctx, 82, h / 2, 46, String(c.n), S.node[c.n % S.node.length], { ring: P(t, tIn + 0.08, 0.25), fill: P(t, tIn + 0.2, 0.2), write: P(t, tIn + 0.24, 0.16), t, seed: 'chd' + c.n });
          drawText(ctx, c.name, 150, h / 2, { font: 'brush', size, color: S.ink, base: 'middle', write: P(t, tIn + 0.05, 0.45, Ease.inOut), t, boil: 0.8 });
          ctx.restore();
        });
        chs.forEach((c) => { const t0 = c.start - 0.8; if (t >= t0 - 0.1 && t <= t0 + 1.9) drawWipe(ctx, t, pass(t0)); });
      });
    },
  });
})();
