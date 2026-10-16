// kit/styles/papercraft-riso.js: cut-paper pieces printed on a risograph.
//   pieces    every node, tag, chip, card and burst is a cut piece of card stock: a light edge toward the light (top
//             left), a dark edge away from it, a soft blurred shadow and paper fibre; nodes carry a pasted stock window
//             for their label
//   print     coloured pieces are printed in halftone: each ink is its own dot screen at its own angle, multiplied
//             over the stock (screened on dark stock), and printed 1 to 3 px out of register with the cut, so a sliver
//             of bare stock shows on one side and two-ink overprints fringe; lines are solid ink with a little ink
//             starvation; glowing strokes (the route, the trails) get a halftone band printed under them
//   inks      three spot inks taken from the theme: the key (its text ink), ink A (its accent) and ink B (the theme
//             hue furthest from the accent). The subject (the city palette), the scenery, the rules and the tape are
//             all A, B and their overprint; meaning colours (good, bad, gold) print as their own drum where a scene
//             uses them, because no three inks reproduce red, green and the accent on every registry theme
//   register  live strokes and bands shift by a per-shot offset (a new shot at every chapter, never per frame);
//             each piece keeps the register of its own print; corner registration marks show the offsets
//   motion    pieces drop in from above with a small overshoot and rotation, stepped at 12 fps (stop motion), and
//             hold still otherwise: no jitter, no float, no line boil; boards slide on the same 12 fps steps
//   type      Fredoka (OFL, @fontsource/fredoka 600 and 700) printed as solid, registered ink: never halftoned
// Colours: every token is derived from the paper palette (original or themed) in palette(); nothing new is invented.
// This file loads before the kit: kit functions (roughen, drawText, ...) are only called inside hooks.
'use strict';
(() => {
  const FR = { t: 0, shot: 0 }; // the frame being drawn (set in beginFrame; never carried across frames)
  const TILE = 32;              // halftone tile size in px (one dot per cell), scaled to the screen cell when used

  // ---------------------------------------------------------------- colour helpers (palette time and draw time)
  const rgb01 = (h) => { const n = parseInt(h.slice(1, 7), 16); return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255]; };
  const hex01 = (c) => '#' + c.map((v) => Math.round(Math.max(0, Math.min(1, v)) * 255).toString(16).padStart(2, '0')).join('').toUpperCase();
  const hueOf = (h) => {
    const [r, g, b] = rgb01(h), mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn; if (d < 1e-6) return 0;
    const hh = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4; return (hh * 60 + 360) % 360;
  };
  const hueGap = (a, b) => { const d = Math.abs(hueOf(a) - hueOf(b)) % 360; return Math.min(d, 360 - d); };
  // the average colour a recipe [[ink, density], ...] prints on `stock`: multiplied (light stock) or screened (dark)
  const printed = (stock, recipe, dark) => hex01(rgb01(stock).map((v, ch) => {
    for (const [ink, d] of recipe) { const c = rgb01(ink)[ch]; v = dark ? 1 - (1 - v) * (1 - d * c) : v * (1 - d * (1 - c)); }
    return v;
  }));

  // ---------------------------------------------------------------- halftone screens and ink texture
  // one dot per cell; past 50% the cell is ink with a hole at its corners (a real AM screen does the same)
  function dotTile(color, d) {
    return cached(`riso:tile:${color}:${d}`, () => {
      const c = makeCanvas(TILE, TILE), g = c.getContext('2d'), A = TILE * TILE;
      g.fillStyle = color;
      if (d <= 0.5) { g.beginPath(); g.arc(TILE / 2, TILE / 2, Math.sqrt((d * A) / Math.PI), 0, TAU); g.fill(); }
      else {
        g.fillRect(0, 0, TILE, TILE); g.globalCompositeOperation = 'destination-out'; const r = Math.sqrt(((1 - d) * A) / Math.PI);
        for (const [x, y] of [[0, 0], [TILE, 0], [0, TILE], [TILE, TILE]]) { g.beginPath(); g.arc(x, y, r, 0, TAU); g.fill(); }
      }
      return c;
    });
  }
  // a dot-screen pattern: ink `color` at density d (0..1, in 1/20 steps), screen angle in degrees, cell in user units
  function screenPat(ctx, color, d, ang, cell, ox = 0, oy = 0) {
    const dq = Math.round(clamp(d) * 20) / 20, pat = cached(`riso:pat:${color}:${dq}`, () => ctx.createPattern(dotTile(color, dq), 'repeat'));
    pat.setTransform(new DOMMatrix().translateSelf(ox, oy).rotateSelf(ang).scaleSelf(cell / TILE));
    return pat;
  }
  // solid ink with a little starvation (sparse specks where the drum left no ink): lines and solid areas
  function inkPat(ctx, color) {
    if (typeof color !== 'string' || color[0] !== '#') return color;
    return cached(`riso:ink:${color}`, () => {
      const c = makeCanvas(160, 160), g = c.getContext('2d'), r = mulberry32(hashStr(color) + 5);
      g.fillStyle = color; g.fillRect(0, 0, 160, 160); g.globalCompositeOperation = 'destination-out';
      for (let i = 0; i < 230; i++) { const x = r() * 160, y = r() * 160, s = 0.7 + r() * 1.3; g.globalAlpha = 0.35 + r() * 0.5; wrapDraw(160, (dx, dy) => g.fillRect(x + dx, y + dy, s, s * (0.6 + r() * 0.8))); }
      return ctx.createPattern(c, 'repeat');
    });
  }
  const recipeOf = (color) => (S.recipes && S.recipes[color]) || [[color, S.inkDensity]];
  const angleOf = (ink) => (ink === S.inkA ? 15 : ink === S.inkB ? 75 : ink === S.ink ? 45 : 0);
  // per-shot misregistration of an ink, in px: the key ink is the register every other ink drifts from
  function regOf(ink, shot = FR.shot, salt = 0) {
    if (ink === S.ink || ink === S.inkSoft || typeof ink !== 'string' || ink[0] !== '#') return [0, 0];
    const s = hashStr('reg' + shot + ':' + (ink === S.inkA ? 'A' : ink === S.inkB ? 'B' : ink) + ':' + salt);
    const a = rnd(s, 1) * TAU, m = 1 + 2 * rnd(s, 2);
    return [Math.cos(a) * m, Math.sin(a) * m];
  }

  // ---------------------------------------------------------------- the cut-paper piece
  // a scissor cut: a low, slow wobble along the outline (never a torn edge)
  function cutPts(pts, seed, amp = 0.8) {
    const q = closedResample(pts, 6), N = normalsOf(q), c = polyCum([...q, q[0]]);
    return q.map((p, i) => { const d = amp * noise1(seed, c[i] / 46); return [p[0] + N[i][0] * d, p[1] + N[i][1] * d]; });
  }
  const shifted = (p, dx, dy) => p.map(([x, y]) => [x + dx, y + dy]);
  // a piece of stock `paper`, printed with `recipe` (null: blank stock). o: {seed, shadow (blur, 0 = none), edge (px)}
  function piece(g, pts, paper, recipe, o = {}) {
    const k = Math.hypot(g.getTransform().a, g.getTransform().b) || 1, seed = seedOf(o.seed ?? 1), e = o.edge ?? 1;
    const body = o.smooth ? pts : cutPts(pts, seed, o.cut ?? 0.8);
    const sb = o.shadow ?? S.shadowBlur;
    if (sb > 0) { // the soft shadow, cast down and right (the light is top left); canvas shadows are in device px
      g.save(); g.shadowColor = S.shadow; g.shadowBlur = sb * k; g.shadowOffsetX = sb * 0.3 * k; g.shadowOffsetY = sb * 0.6 * k;
      pathPts(g, shifted(body, 1.6 * e, 2.2 * e)); g.fillStyle = S.edgeDark; g.fill(); g.restore();
    }
    pathPts(g, shifted(body, 1.6 * e, 2.2 * e)); g.fillStyle = S.edgeDark; g.fill();     // the cut edge away from the light
    pathPts(g, shifted(body, -1.1 * e, -1.1 * e)); g.fillStyle = S.edgeLight; g.fill();  // the edge catching the light
    pathPts(g, body); g.fillStyle = paper; g.fill();
    if (recipe) printOn(g, body, recipe, seed, o.cell ?? S.cell);
    if ((o.tex ?? 1) > 0) { g.save(); pathPts(g, body); g.clip(); fiberFill(g, bbox(body), 1.2 * (o.tex ?? 1), seed); g.restore(); }
    return body;
  }
  // print a recipe inside a cut outline: one halftone screen per ink, each out of register with the cut by its own
  // 1 to 3 px (fixed for this piece: it was printed once, then cut)
  function printOn(g, body, recipe, seed, cell) {
    g.save(); pathPts(g, body); g.clip(); g.globalCompositeOperation = S.inkBlend;
    recipe.forEach(([ink, d], i) => {
      const a = rnd(seed, 40 + i) * TAU, m = 1 + 2 * rnd(seed, 50 + i), dx = Math.cos(a) * m, dy = Math.sin(a) * m;
      g.save(); g.translate(dx, dy); pathPts(g, body);
      g.fillStyle = d >= 0.94 ? inkPat(g, ink) : screenPat(g, ink, d, angleOf(ink), cell, rnd(seed, 60 + i) * cell, 0);
      g.fill(); g.restore();
    });
    g.restore();
  }

  // ---------------------------------------------------------------- printed lines and bands
  // a halftone band printed under a glowing stroke (the route, a trail): what a glow becomes in print
  function band(ctx, part, w, ink, m) {
    if (part.length < 2) return;
    const N = normalsOf(part, false), bw = Math.max(6, w * 1.35);
    const poly = [...part.map((q, i) => [q[0] + N[i][0] * bw, q[1] + N[i][1] * bw]), ...part.map((q, i) => [q[0] - N[i][0] * bw, q[1] - N[i][1] * bw]).reverse()];
    ctx.save(); ctx.translate(m[0] * 1.7, m[1] * 1.7); pathPts(ctx, poly);
    ctx.fillStyle = screenPat(ctx, ink, 0.42, angleOf(ink) + 30, Math.max(5, S.cell * 0.85)); ctx.fill(); ctx.restore();
  }

  // ---------------------------------------------------------------- registration marks (screen corners)
  function regMark(ctx, x, y, ink, m) {
    ctx.save(); ctx.translate(x + m[0], y + m[1]); ctx.strokeStyle = ink; ctx.lineWidth = 1.6;
    ctx.beginPath(); ctx.arc(0, 0, 9, 0, TAU); ctx.moveTo(-16, 0); ctx.lineTo(16, 0); ctx.moveTo(0, -16); ctx.lineTo(0, 16); ctx.stroke(); ctx.restore();
  }

  defineStyle('papercraft-riso', {
    base: 'paper',
    font: { hand: 'Fredoka SemiBold', brush: 'Fredoka Bold' },
    size: { chapterCorner: 0.56, chip: 40 }, // chips start their flight at 0.6 scale: Fredoka digits need 40 to stay clear of 26 px
    palette(P, T, C) {
      const { mix, alpha: A, ensure } = C, dark = !!T && T.tone === 'dark', white = '#FFFFFF', black = '#000000';
      // the stock: a bright paper (light themes), or the theme's own dark ground (dark themes, light inks screened on)
      const stock = dark ? P.bg : mix(P.bg, P.card, 0.7), card = dark ? P.card : mix(P.card, white, 0.3);
      const blend = dark ? 'screen' : 'multiply';
      // the three spot inks: the key (text ink), A (the accent) and B (the theme hue furthest from it)
      const inkA = P.accent, others = [P.cool, P.sky, P.lilac, P.good, P.gold, P.warm].filter((c) => c && c[0] === '#' && c !== inkA);
      const inkB = others.reduce((b, c) => (hueGap(c, inkA) > hueGap(b, inkA) + 8 ? c : b), others[0]);
      const pr = (recipe, on = card) => printed(on, recipe, dark);
      // the city palette: A, B, their overprint, then tints, so the subject reads as a two-ink print
      const nodeR = [[[inkA, 0.78]], [[inkB, 0.78]], [[inkA, 0.55], [inkB, 0.55]], [[inkA, 0.4]], [[inkB, 0.42]], [[inkA, 0.3], [inkB, 0.6]], [[inkA, 0.62], [inkB, 0.25]], [[inkB, 0.3]]];
      const node = nodeR.map((r) => pr(r)), recipes = {};
      node.forEach((c, i) => { recipes[c] = nodeR[i]; });
      const hillR = [[[inkB, 0.26]], [[inkA, 0.22]]], hills = hillR.map((r) => pr(r)), cloudR = [[inkB, 0.16]], cloud = pr(cloudR);
      hills.forEach((c, i) => { recipes[c] = hillR[i]; }); recipes[cloud] = cloudR;
      recipes[inkA] = [[inkA, 0.78]]; recipes[inkB] = [[inkB, 0.78]];
      const hlA = dark ? 0.2 : 0.38, hl = A(P.gold, hlA), hlCard = mix(card, P.gold, hlA);
      // every surface text sits on: the stock (and its halftone vignette near the edges), the cards, a highlighted row
      const surf = [stock, card, hlCard, pr([[P.ink, 0.1]], stock)];
      const lift = (c, k) => ensure(c, surf, k);
      const ink = lift(P.ink, 8.5), inkSoft = lift(P.inkSoft, 6.5);
      const keys = ['accent', 'cool', 'gold', 'lilac', 'sky', 'good', 'bad', 'warm'];
      const txt = Object.fromEntries(keys.map((k) => [k, lift((T && P.txt && P.txt[k]) || (P.txt && P.txt[k]) || P[k], 6)]));
      node.forEach((c, i) => { txt['node' + i] = lift(c, 6); });
      const syntax = Object.fromEntries(Object.entries(P.syntax).map(([k, v]) => [k, ensure(v, [card, hlCard], 6.5)]));
      const edgeLight = dark ? mix(card, P.ink, 0.22) : mix(card, white, 0.8), edgeDark = dark ? mix(card, black, 0.5) : mix(card, P.shade, 0.32);
      return {
        ...P, kind: 'paper', ...Object.fromEntries(node.map((c, i) => ['node' + i, c])), // node colours -> text shades (S.txtOf)
        bg: stock, bgDeep: stock, bgLight: stock, stock, card, cardEdge: edgeLight, cardInk: ink, ink, inkSoft, inkFaint: A(ink, 0.3),
        inkA, inkB, inkBlend: blend, recipes, inkDensity: 0.66, cell: 6.5, edgeLight, edgeDark,
        rule: mix(card, inkB, dark ? 0.4 : 0.45), margin: mix(card, inkA, 0.55), sticky: mix(card, P.gold, 0.32), kraft: mix(card, P.warm, 0.22),
        tape: A(inkB, dark ? 0.3 : 0.26), tapeDots: inkA,
        shadow: dark ? A(black, 0.6) : A(P.shade, 0.3), shadowBlur: 12, glowShadow: dark ? null : A(P.shade, 0.22),
        hl, glow: A(inkA, dark ? 0.3 : 0.24), txt, goodSoft: mix(card, P.good, 0.1), costTag: mix(card, P.gold, 0.3), spark: card,
        node, nodeInk: node.map(() => ink), burst: [inkA, card], syntax, codeDim: ensure(P.codeDim, [card, hlCard], 6),
        halo: A(card, 0.92), chipTo: card, chipK: dark ? 0.62 : 0.55, burstHalo: null, tagHole: A(ink, 0.45),
        hills, cloud, sheen: A(white, 0), curl: [A(P.shade, 0), A(P.shade, 0)],
        plane: { under: pr([[inkB, 0.45]]), mid: pr([[inkA, 0.22]]), top: card, crease: A(ink, 0.4), wind: A(ink, 0.4) },
        pip: { coat: inkB, coat2: mix(inkB, black, 0.12), scarf: inkA, pack: inkA, hat: P.gold, hat2: mix(P.gold, black, 0.1), legs: mix(inkB, ink, 0.55), boots: mix(inkA, black, 0.6), rim: edgeLight },
        vignette: A(ink, 0), keyLight: dark ? null : [A(white, 0.14), A(white, 0)], lights: null, deepBlob: 0,
        grain: dark ? 0.3 : 0.42, grainBlend: dark ? 'screen' : 'multiply', grainSpecks: [A(white, 0.1), A(black, 0.1)],
        stroke: { w: 3.4, rough: 0.7, passes: 1, chalk: false }, boilFps: 12, boilAmp: 0, jitter: 0, grainBoil: false,
        fontFiles: { hand: 'fonts/fredoka-latin-600-normal.woff', brush: 'fonts/fredoka-latin-700-normal.woff' },
        // Fredoka is wide (about 1.2x Patrick Hand per em), so it is set a little smaller: hand text keeps Patrick
        // Hand's x-height and brush text Caveat Brush's, and layouts written for paper still fit
        fontSize: (fk, size) => (fk === 'brush' ? size * 0.78 : size * 0.95),
        inkOn: (fill) => (typeof fill === 'string' && fill[0] === '#' ? ensure(ink, [fill], 6) : ink),
        textBoil: 0, float: 0, stepFps: 12,
      };
    },

    beginFrame(t) { FR.t = t; const c = chapterAt(t); FR.shot = c ? c.n : 0; },

    // a stop-motion drop: the piece appears lifted (bigger, a little turned), falls onto the board, overshoots by a
    // hair and settles, all on 12 fps steps
    pop(t, t0, d = 0.55) {
      if (!(t >= t0)) return { s: 0, sx: 0, sy: 0 };
      const step = 1 / S.stepFps, u = (Math.floor((t - t0) / step + 1e-6) * step) / d;
      if (u >= 1) return { s: 1, sx: 1, sy: 1, rot: 0 };
      const r0 = (rnd(Math.round(t0 * 1000), 7) < 0.5 ? -1 : 1) * (0.03 + 0.03 * rnd(Math.round(t0 * 1000), 8));
      let s, rot;
      if (u < 0.5) { const f = 1 - (u / 0.5) ** 2; s = 1 + 0.13 * f; rot = r0 * f; }
      else { const v = (u - 0.5) / 0.5, b = Math.sin(Math.PI * v) * (1 - v); s = 1 - 0.03 * b; rot = -r0 * 0.4 * b; }
      return { s, sx: s, sy: s, rot };
    },

    stroke(ctx, pts, o = {}) {
      const prog = o.prog ?? 1, from = o.from ?? 0, base = ctx.globalAlpha;
      if (prog - from <= 0.001 || pts.length < 2 || base * (o.alpha ?? 1) <= 0.003) return;
      const seed = seedOf(o.seed ?? 1), w = o.w ?? S.stroke.w, color = o.color || S.ink;
      const part = polySlice(roughen(pts, seed, o.amp ?? S.stroke.rough, o.ends ?? true), from, prog); // printed: no boil
      const m = regOf(color);
      ctx.save(); ctx.globalAlpha = base * (o.alpha ?? 1); ctx.globalCompositeOperation = S.inkBlend;
      if (o.glow && from <= 0) band(ctx, part, w, color, regOf(color, FR.shot, 1));
      ctx.translate(m[0], m[1]); ctx.lineCap = o.cap || 'round'; ctx.lineJoin = 'round'; ctx.lineWidth = w; ctx.strokeStyle = inkPat(ctx, color);
      if (o.dash) { ctx.setLineDash(o.dash); ctx.lineDashOffset = o.dashOffset || 0; }
      pathPts(ctx, part, false); ctx.stroke(); ctx.restore();
    },
    penTip() {}, // printed type has no pen

    // hatch: false marks a piece that carries text (tags, slips, a burst's middle): plain stock, never halftoned
    cutout(g, pts, color, o = {}) {
      const flat = o.hatch === false;
      return piece(g, pts, flat ? color : S.card, flat ? null : recipeOf(color), { seed: o.seed ?? 1, shadow: o.shadow, smooth: o.smooth, tex: o.tex, edge: o.edge === 0 ? 0.6 : 1 });
    },

    card(g, w, h, kind, color, seed, o) {
      const body = piece(g, rrPts(0, 0, w, h, kind === 'label' ? 6 : 4), color, null, { seed, cut: 0.6, tex: 0.6, shadow: S.shadowBlur });
      if (kind === 'note') { // rules and margin are printed: solid ink, out of register with the cut like any print
        const m = [(rnd(seed, 3) - 0.5) * 4, (rnd(seed, 4) - 0.5) * 4];
        g.save(); pathPts(g, body); g.clip(); g.translate(m[0], m[1]); g.globalCompositeOperation = S.inkBlend;
        g.strokeStyle = S.rule; g.lineWidth = 1.8;
        for (let y = o.first || 90; y < h - 8; y += o.rule || 50) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
        g.strokeStyle = S.margin; g.lineWidth = 2.2; g.beginPath(); g.moveTo(o.marginX || 60, 0); g.lineTo(o.marginX || 60, h); g.stroke();
        g.restore();
      }
      const nt = o.tape ?? 2, at = nt === 1 ? [[w / 2, (rnd(seed, 9) - 0.5) * 0.2]] : nt === 2 ? [[w * 0.12, -0.3], [w * 0.88, 0.27]] : [];
      at.forEach(([x, rot], i) => { // translucent tape, printed with a light dot screen
        const tw = Math.min(nt === 1 ? 130 : 110, w * (nt === 1 ? 0.4 : 0.25));
        g.save(); g.translate(x, -2); g.rotate(rot); const p = tear(rrPts(-tw / 2, -15, tw, 30, 1), 1.4, seed + 50 + i, 4);
        g.globalCompositeOperation = S.inkBlend; pathPts(g, p); g.fillStyle = S.tape; g.fill();
        g.save(); pathPts(g, p); g.clip(); pathPts(g, p); g.fillStyle = screenPat(g, S.tapeDots, 0.2, 15, 5); g.fill(); g.restore();
        g.restore();
      });
    },

    // a node or badge: a printed disc of stock with a pasted stock window for its label (the label is never halftoned)
    disc(g, label, color, ink, r, font) {
      const seed = hashStr(label + color);
      piece(g, ellipsePts(0, 0, r, r, 44), S.card, recipeOf(color), { seed, shadow: 9 });
      piece(g, ellipsePts(0, 0, r * 0.62, r * 0.62, 36), S.card, null, { seed: seed + 1, shadow: 3, edge: 0.6, tex: 0.5 });
      drawText(g, label, 0, 0, { font, size: r * (label.length > 2 ? 0.78 : 1.18), color: S.ink, align: 'center', base: 'middle', maxW: r * 1.1 });
    },

    backdrop(g, pw, ph, r) {
      g.fillStyle = S.stock; g.fillRect(0, 0, pw, ph);
      const pat = g.createPattern(TEX.fiber, 'repeat'); g.fillStyle = pat; g.fillRect(0, 0, pw, ph); g.fillRect(0, 0, pw, ph);
      // a halftone vignette in the key ink, densest outside the frame and gone 170 px inside it
      const pad = BACK.pad, cell = 9, ang = Math.PI / 4, ca = Math.cos(ang), sa = Math.sin(ang), R = Math.hypot(pw, ph);
      g.fillStyle = S.ink; g.globalCompositeOperation = S.inkBlend;
      for (let i = -R / cell; i < R / cell; i++) for (let j = -R / cell; j < R / cell; j++) {
        const x = pw / 2 + (i * ca - j * sa) * cell, y = ph / 2 + (i * sa + j * ca) * cell;
        if (x < -cell || y < -cell || x > pw + cell || y > ph + cell) continue;
        const e = Math.min(x - pad, pad + W - x, y - pad, pad + H - y), d = 0.17 * smooth(120, -80, e);
        if (d < 0.01) continue;
        g.beginPath(); g.arc(x, y, cell * Math.sqrt(d / Math.PI), 0, TAU); g.fill();
      }
      g.globalCompositeOperation = 'source-over'; void r;
    },

    // the frame's register: a mark per ink in each corner, each ink out by its offset for this shot
    overlay(ctx) {
      ctx.save(); ctx.globalCompositeOperation = S.inkBlend; ctx.globalAlpha = 0.75;
      for (const [x, y] of [[40, 40], [W - 40, 40], [40, H - 40], [W - 40, H - 40]]) for (const ink of [S.ink, S.inkA, S.inkB]) regMark(ctx, x, y, ink, regOf(ink));
      ctx.restore();
    },
  });
})();
