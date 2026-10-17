// kit/ink.js: textures, the backdrop, rough (hand-drawn) strokes, paper cut-outs, sprites, cards, tags, stamps.
// Strokes are rebuilt from seeded noise every frame; the seed changes on boil frames only (8-12 fps), which is
// what makes lines "boil" like hand animation instead of shimmering. Cut-outs are baked once into sprites and
// jitter in position like stop motion.
'use strict';

// ------------------------------------------------------------------ canvases and sprites
function makeCanvas(w, h) { const c = document.createElement('canvas'); c.width = Math.max(1, Math.ceil(w)); c.height = Math.max(1, Math.ceil(h)); return c; }
const CACHE = new Map();
function cached(key, make) { let v = CACHE.get(key); if (v === undefined) { v = make(); CACHE.set(key, v); } return v; }
// draw once into an offscreen canvas at `res` x resolution (so camera push-ins stay sharp), blit every frame
function sprite(w, h, ox, oy, fn, res = 2) {
  const c = makeCanvas(w * res, h * res), g = c.getContext('2d');
  g.scale(res, res); g.translate(ox, oy); fn(g);
  return { c, w, h, ox, oy };
}
// o: {s, sx, sy, rot, alpha, jit: id for stop-motion jitter, t}
function blit(ctx, sp, x, y, o = {}) {
  const s = o.s ?? 1, sx = (o.sx ?? 1) * s, sy = (o.sy ?? 1) * s, a = o.alpha ?? 1;
  if (a <= 0.003 || Math.abs(sx) < 0.002 || Math.abs(sy) < 0.002) return;
  let rot = o.rot || 0;
  if (o.jit != null && o.t != null) { const j = jitter(o.jit, o.t); x += j[0]; y += j[1]; rot += j[2]; }
  ctx.save(); ctx.translate(x, y); if (rot) ctx.rotate(rot); ctx.scale(sx, sy); ctx.globalAlpha *= a;
  ctx.drawImage(sp.c, -sp.ox, -sp.oy, sp.w, sp.h); ctx.restore();
}

// ------------------------------------------------------------------ polylines
function polyCum(p) { const c = [0]; for (let i = 1; i < p.length; i++) c.push(c[i - 1] + Math.hypot(p[i][0] - p[i - 1][0], p[i][1] - p[i - 1][1])); return c; }
function resample(p, step = 6) {
  if (p.length < 2) return p.slice();
  const c = polyCum(p), L = c[c.length - 1], n = Math.max(2, Math.ceil(L / step)), out = [];
  let k = 0;
  for (let i = 0; i <= n; i++) {
    const d = (L * i) / n; while (k < c.length - 2 && c[k + 1] < d) k++;
    const seg = c[k + 1] - c[k] || 1, u = (d - c[k]) / seg;
    out.push([lerp(p[k][0], p[k + 1][0], u), lerp(p[k][1], p[k + 1][1], u)]);
  }
  return out;
}
// point and tangent angle at fraction u of the arc length
function polyAt(p, u) {
  const c = p._cum || (p._cum = polyCum(p)), L = c[c.length - 1], d = clamp(u) * L;
  let k = 0; while (k < c.length - 2 && c[k + 1] < d) k++;
  const a = p[k], b = p[k + 1] || a, seg = c[k + 1] - c[k] || 1, v = (d - c[k]) / seg;
  return [lerp(a[0], b[0], v), lerp(a[1], b[1], v), Math.atan2(b[1] - a[1], b[0] - a[0])];
}
// the part of a polyline between fractions u0 and u1 of its length
function polySlice(p, u0, u1) {
  if (u0 <= 0 && u1 >= 1) return p;
  const c = polyCum(p), L = c[c.length - 1], d0 = clamp(u0) * L, d1 = clamp(u1) * L, out = [];
  out.push(polyAt(p, u0).slice(0, 2));
  for (let i = 1; i < p.length - 1; i++) if (c[i] > d0 && c[i] < d1) out.push(p[i]);
  out.push(polyAt(p, u1).slice(0, 2));
  return out;
}
const polyLength = (p) => { const c = polyCum(p); return c[c.length - 1]; };
function quadPts(a, c, b, n = 32) {
  const p = [];
  for (let i = 0; i <= n; i++) { const u = i / n, v = 1 - u; p.push([v * v * a[0] + 2 * v * u * c[0] + u * u * b[0], v * v * a[1] + 2 * v * u * c[1] + u * u * b[1]]); }
  return p;
}
// smooth curve through points (Catmull-Rom)
function curvePts(pts, n = 12) {
  if (pts.length < 3) return pts.slice();
  const out = [];
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    for (let k = 0; k < n; k++) {
      const u = k / n, u2 = u * u, u3 = u2 * u;
      out.push([0, 1].map((j) => 0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u3)));
    }
  }
  out.push(pts[pts.length - 1]);
  return out;
}
function ellipsePts(cx, cy, rx, ry, n = 48, a0 = 0) { const p = []; for (let i = 0; i < n; i++) { const a = a0 + (i / n) * TAU; p.push([cx + Math.cos(a) * rx, cy + Math.sin(a) * ry]); } return p; }
function rrPts(x, y, w, h, r, seg = 5) {
  r = Math.min(r, w / 2, h / 2); const p = [];
  for (const [cx, cy, a0] of [[x + w - r, y + r, -Math.PI / 2], [x + w - r, y + h - r, 0], [x + r, y + h - r, Math.PI / 2], [x + r, y + r, Math.PI]])
    for (let i = 0; i <= seg; i++) { const a = a0 + (i / seg) * Math.PI / 2; p.push([cx + Math.cos(a) * r, cy + Math.sin(a) * r]); }
  return p;
}
function closedResample(p, step) { return resample([...p, p[0]], step).slice(0, -1); }
function signedArea(p) { let s = 0; for (let i = 0; i < p.length; i++) { const a = p[i], b = p[(i + 1) % p.length]; s += a[0] * b[1] - b[0] * a[1]; } return s; }
function normalsOf(p, closed = true) {
  const n = p.length, sg = closed && signedArea(p) < 0 ? -1 : 1;
  return p.map((_, i) => {
    const a = p[closed ? (i - 1 + n) % n : Math.max(0, i - 1)], b = p[closed ? (i + 1) % n : Math.min(n - 1, i + 1)];
    let tx = b[0] - a[0], ty = b[1] - a[1]; const l = Math.hypot(tx, ty) || 1; tx /= l; ty /= l;
    return [ty * sg, -tx * sg];
  });
}
function offsetPts(p, d) { const N = normalsOf(p); return p.map((q, i) => [q[0] + N[i][0] * d, q[1] + N[i][1] * d]); }
// torn-paper edge: resample, push each point out by a random amount (with an occasional bigger tear)
function tear(p, amp, seed, step = 5, bias = 0.5) {
  const r = mulberry32(seedOf(seed)), q = closedResample(p, step), N = normalsOf(q);
  return q.map((pt, i) => { let d = (r() - bias) * 2 * amp; if (r() < 0.06) d += amp * 1.4 * r(); return [pt[0] + N[i][0] * d, pt[1] + N[i][1] * d]; });
}
function pathPts(ctx, p, close = true) { ctx.beginPath(); ctx.moveTo(p[0][0], p[0][1]); for (let i = 1; i < p.length; i++) ctx.lineTo(p[i][0], p[i][1]); if (close) ctx.closePath(); }
function bbox(p) { let x0 = 1e9, y0 = 1e9, x1 = -1e9, y1 = -1e9; for (const [x, y] of p) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); } return [x0, y0, x1, y1]; }

// ------------------------------------------------------------------ textures (tiles drawn wrapped at +/- size, so no seams)
const TEX = {};
function wrapDraw(size, fn) { for (const dx of [-size, 0, size]) for (const dy of [-size, 0, size]) fn(dx, dy); }
function initTextures() {
  const N = 512;
  TEX.fiber = makeCanvas(N, N);
  let g = TEX.fiber.getContext('2d'), r = mulberry32(7);
  g.lineCap = 'round';
  for (let i = 0; i < 520; i++) {
    const light = r() < 0.5, x = r() * N, y = r() * N, L = 5 + r() * 22, a = r() * TAU, bend = (r() - 0.5) * 10, w = 0.6 + r() * 1.3;
    g.strokeStyle = light ? S.fiberLight : S.fiber; g.lineWidth = w;
    wrapDraw(N, (dx, dy) => { g.beginPath(); g.moveTo(x + dx, y + dy); g.quadraticCurveTo(x + dx + Math.cos(a) * L / 2 - Math.sin(a) * bend, y + dy + Math.sin(a) * L / 2 + Math.cos(a) * bend, x + dx + Math.cos(a) * L, y + dy + Math.sin(a) * L); g.stroke(); });
  }
  for (let i = 0; i < 5000; i++) { const x = r() * N, y = r() * N, s = 0.8 + r() * 1.6; g.fillStyle = r() < 0.5 ? S.fiber : S.fiberLight; wrapDraw(N, (dx, dy) => g.fillRect(x + dx, y + dy, s, s)); }
  // film grain tile (fixed on screen; S.grainBoil moves it on boil frames, which costs ~1.5x the file size)
  TEX.grain = makeCanvas(N, N); g = TEX.grain.getContext('2d'); r = mulberry32(11);
  for (let i = 0; i < 14000; i++) { const x = r() * N, y = r() * N; g.fillStyle = r() < 0.5 ? S.grainSpecks[0] : S.grainSpecks[1]; wrapDraw(N, (dx, dy) => g.fillRect(x + dx, y + dy, 1.4, 1.4)); }
  // chalk mask: colour with speckled holes (used as strokeStyle/fillStyle in the chalk style)
  TEX.chalkHoles = makeCanvas(256, 256); g = TEX.chalkHoles.getContext('2d'); r = mulberry32(13);
  g.fillStyle = '#000'; g.fillRect(0, 0, 256, 256); g.globalCompositeOperation = 'destination-out';
  for (let i = 0; i < 2600; i++) { const x = r() * 256, y = r() * 256, s = 0.8 + r() * 2.2; g.globalAlpha = 0.35 + r() * 0.65; wrapDraw(256, (dx, dy) => g.fillRect(x + dx, y + dy, s, s * (0.6 + r()))); }
  buildBackdrop(); buildOverlay();
}
function chalkStyle(ctx, color) {
  return cached('chalk' + color, () => {
    const c = makeCanvas(256, 256), g = c.getContext('2d');
    g.fillStyle = color; g.fillRect(0, 0, 256, 256); g.globalCompositeOperation = 'destination-in'; g.drawImage(TEX.chalkHoles, 0, 0);
    return ctx.createPattern(c, 'repeat');
  });
}
function fiberFill(ctx, b, strength = 1, seed = 1) {
  const pat = cached('fiberpat', () => ctx.createPattern(TEX.fiber, 'repeat'));
  pat.setTransform(new DOMMatrix().translate(rnd(seed, 1) * 512, rnd(seed, 2) * 512));
  ctx.save(); ctx.globalAlpha *= strength; ctx.fillStyle = pat; ctx.fillRect(b[0] - 2, b[1] - 2, b[2] - b[0] + 4, b[3] - b[1] + 4); ctx.restore();
}

// ------------------------------------------------------------------ backdrop, light, vignette, grain
const BACK = { pad: 520 };
function buildBackdrop() {
  const pw = W + BACK.pad * 2, ph = H + BACK.pad * 2;
  BACK.c = makeCanvas(pw, ph);
  const g = BACK.c.getContext('2d'), r = mulberry32(21);
  if (STYLE.backdrop) return STYLE.backdrop(g, pw, ph, r);
  g.fillStyle = S.bg; g.fillRect(0, 0, pw, ph);
  // mottling: big soft blobs of a deeper and a lighter tone
  for (let i = 0; i < 70; i++) {
    const x = r() * pw, y = r() * ph, R = 120 + r() * 420, deep = r() < 0.55;
    const gr = g.createRadialGradient(x, y, 0, x, y, R);
    gr.addColorStop(0, deep ? S.bgDeep : S.bgLight); gr.addColorStop(1, 'rgba(0,0,0,0)');
    g.globalAlpha = (0.10 + r() * 0.14) * (deep ? S.deepBlob ?? 1 : 1); g.fillStyle = gr; g.fillRect(x - R, y - R, 2 * R, 2 * R);
  }
  g.globalAlpha = 1;
  const pat = g.createPattern(TEX.fiber, 'repeat'); g.fillStyle = pat; g.fillRect(0, 0, pw, ph); g.fillRect(0, 0, pw, ph);
  if (S.kind === 'blueprint') {
    for (const [step, a] of [[40, 0.07], [200, 0.16]]) {
      g.strokeStyle = hexA(S.grid, a); g.lineWidth = step > 40 ? 1.6 : 1;
      for (let x = (BACK.pad % step); x < pw; x += step) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, ph); g.stroke(); }
      for (let y = (BACK.pad % step); y < ph; y += step) { g.beginPath(); g.moveTo(0, y); g.lineTo(pw, y); g.stroke(); }
    }
  }
  if (S.kind === 'chalk') { // old eraser smudges
    g.lineCap = 'round';
    for (let i = 0; i < 26; i++) {
      const x = r() * pw, y = r() * ph, L = 200 + r() * 500, a = (r() - 0.5) * 0.6;
      g.strokeStyle = hexA(S.smudge, 0.018 + r() * 0.03); g.lineWidth = 40 + r() * 90;
      g.beginPath(); g.moveTo(x, y); g.quadraticCurveTo(x + L / 2, y + (r() - 0.5) * 120, x + Math.cos(a) * L, y + Math.sin(a) * L); g.stroke();
    }
  }
  if (S.kind === 'paper') { // two faint fold creases
    for (const [x0, y0, x1, y1] of [[pw * 0.33, 0, pw * 0.36, ph], [0, ph * 0.58, pw, ph * 0.55]]) {
      g.strokeStyle = S.crease[0]; g.lineWidth = 3; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
      g.strokeStyle = S.crease[1]; g.lineWidth = 6; g.beginPath(); g.moveTo(x0 + 4, y0 + 3); g.lineTo(x1 + 4, y1 + 3); g.stroke();
    }
  }
}
function drawBackdrop(ctx, cam) {
  ctx.save(); applyCam(ctx, cam, S.backDepth ?? 0.35); ctx.drawImage(BACK.c, -BACK.pad, -BACK.pad); ctx.restore();
}
function buildOverlay() {
  BACK.light = makeCanvas(W, H);
  const g = BACK.light.getContext('2d');
  if (S.keyLight) { // the key light, top left (a registry dark theme draws it per chapter instead: drawKeyLight)
    const warm = g.createRadialGradient(W * 0.3, H * 0.18, 0, W * 0.3, H * 0.18, W * 0.75);
    warm.addColorStop(0, S.keyLight[0]); warm.addColorStop(1, S.keyLight[1]);
    g.fillStyle = warm; g.fillRect(0, 0, W, H);
  }
  const vg = g.createRadialGradient(W / 2, H / 2, H * 0.42, W / 2, H / 2, H * 1.08);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, S.vignette);
  g.fillStyle = vg; g.fillRect(0, 0, W, H);
}
// dark registry themes: a faint key light tinted by the chapter's colour from the theme's `lights`, eased across the
// chapter change (drawn per frame: one gradient fill)
function drawKeyLight(ctx, t) {
  const L6 = S.lights, chs = TIMING_.chapters; if (!L6 || !L6.length || S.keyLight) return;
  const c = chapterAt(t), i = c ? chs.indexOf(c) : 0, k = c ? P(t, c.start - 0.8, 1.0) : 1;
  const col = mixHex(L6[Math.max(0, i - 1) % L6.length], L6[i % L6.length], i > 0 ? k : 1);
  const gr = ctx.createRadialGradient(W * 0.3, H * 0.18, 0, W * 0.3, H * 0.18, W * 0.75);
  gr.addColorStop(0, hexA(col, S.lightA ?? 0.07)); gr.addColorStop(1, hexA(col, 0));
  ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
}
function drawOverlay(ctx, t) {
  drawKeyLight(ctx, t);
  ctx.drawImage(BACK.light, 0, 0);
  const pat = cached('grainpat', () => ctx.createPattern(TEX.grain, 'repeat')), k = S.grainBoil ? boilKey(t) : 0;
  pat.setTransform(new DOMMatrix().translate(rnd(5, k) * 512, rnd(6, k) * 512));
  ctx.save(); ctx.globalAlpha = S.grain; if (S.grainBlend) ctx.globalCompositeOperation = S.grainBlend; ctx.fillStyle = pat; ctx.fillRect(0, 0, W, H); ctx.restore();
  if (STYLE.overlay) STYLE.overlay(ctx, t);
}

// ------------------------------------------------------------------ rough strokes
// wobble a polyline along its normals with smooth noise (+ a little fine noise) and overshoot the ends
function roughen(p, seed, amp, ends = true) {
  if (amp <= 0) return p;
  const q = resample(p, 6), c = polyCum(q), N = normalsOf(q, false), L = c[c.length - 1] || 1;
  const wl = clamp(L / 3, 40, 140);
  const out = q.map((pt, i) => {
    const d = amp * (noise1(seed, c[i] / wl) + 0.3 * noise1(seed + 9, c[i] / 16)) * Math.min(1, 0.4 + (c[i] / L) * 8, 0.4 + ((L - c[i]) / L) * 8);
    return [pt[0] + N[i][0] * d, pt[1] + N[i][1] * d];
  });
  if (ends && q.length > 2) { // rough.js-style overshoot at both ends
    const ex = (k, j, s) => { const a = out[k], b = out[j], l = Math.hypot(a[0] - b[0], a[1] - b[1]) || 1; return [a[0] + (a[0] - b[0]) / l * s, a[1] + (a[1] - b[1]) / l * s]; };
    out.unshift(ex(0, 1, amp * (0.5 + rnd(seed, 3) * 1.5))); out.push(ex(out.length - 1, out.length - 2, amp * (0.5 + rnd(seed, 4) * 1.5)));
  }
  return out;
}
// The one stroke function. o: {color, w, prog (0..1 drawn), from (0..1), alpha, seed, t (boil), amp, passes,
// dash, dashOffset, glow (colour), tip (pen blob while drawing), cap, ends (overshoot)}
function inkLine(ctx, pts, o = {}) {
  if (STYLE.stroke) return STYLE.stroke(ctx, pts, o);
  const prog = o.prog ?? 1, from = o.from ?? 0;
  const base = ctx.globalAlpha; // inherit the group's fade (a board sliding out, a tree fading): multiply, never reset
  if (prog - from <= 0.001 || pts.length < 2 || base * (o.alpha ?? 1) <= 0.003) return;
  const seed0 = o.t != null ? boilSeed(o.seed ?? 1, o.t) : seedOf(o.seed ?? 1);
  const amp = (o.amp ?? S.stroke.rough) * (o.t != null ? S.boilAmp : 1), w = o.w ?? S.stroke.w, color = o.color || S.ink;
  const passes = o.passes ?? S.stroke.passes;
  ctx.save(); ctx.lineCap = o.cap || 'round'; ctx.lineJoin = 'round';
  for (let k = 0; k < passes; k++) {
    const rp = roughen(pts, seed0 + k * 101, amp * (k ? 1.3 : 1), o.ends ?? true);
    const part = polySlice(rp, from, prog);
    ctx.globalAlpha = base * (o.alpha ?? 1) * (k ? 0.55 : 1);
    ctx.lineWidth = k ? Math.max(1, w * 0.5) : w;
    ctx.strokeStyle = S.stroke.chalk ? chalkStyle(ctx, color) : color;
    if (o.dash) { ctx.setLineDash(o.dash); ctx.lineDashOffset = o.dashOffset || 0; }
    if (o.glow && k === 0) glowOrShadow(ctx, o.glow, o.glowBlur ?? 16);
    pathPts(ctx, part, false); ctx.stroke(); ctx.shadowBlur = 0; if (o.glow && S.glowShadow) { ctx.shadowOffsetX = 0; ctx.shadowOffsetY = 0; }
    if (k === 0 && o.tip && prog < 0.999) { const e = part[part.length - 1]; ctx.fillStyle = color; ctx.beginPath(); ctx.arc(e[0], e[1], w * 0.9, 0, TAU); ctx.fill(); }
  }
  ctx.restore();
}
// a glow on a dark ground; on a light registry theme it reads as a smudge, so it becomes a soft drop shadow
function glowOrShadow(ctx, color, blur) {
  if (S.glowShadow) { ctx.shadowColor = S.glowShadow; ctx.shadowBlur = Math.min(blur, 8); ctx.shadowOffsetX = 2; ctx.shadowOffsetY = 4; }
  else { ctx.shadowColor = color; ctx.shadowBlur = blur; }
}
const inkSeg = (ctx, x1, y1, x2, y2, o = {}) => inkLine(ctx, [[x1, y1], [x2, y2]], o);
// hand-drawn ellipse: one loop that overlaps itself a little, starting at a random angle
function inkEllipse(ctx, cx, cy, rx, ry, o = {}) {
  const s = seedOf(o.seed ?? 3), a0 = (o.a0 ?? -2.2) + (rnd(s, 1) - 0.5) * 0.6, turns = o.turns ?? 1.08, n = 64, pts = [];
  for (let i = 0; i <= n; i++) { const u = i / n, a = a0 + u * turns * TAU, k = 1 + (rnd(s, 2) - 0.5) * 0.04 + u * 0.05; pts.push([cx + Math.cos(a) * rx * k, cy + Math.sin(a) * ry * k]); }
  inkLine(ctx, pts, { ends: false, ...o });
}
// hand-drawn rectangle: four strokes that overshoot their corners; prog draws them in order
function inkRect(ctx, x, y, w, h, o = {}) {
  const sides = [[[x, y], [x + w, y]], [[x + w, y], [x + w, y + h]], [[x + w, y + h], [x, y + h]], [[x, y + h], [x, y]]];
  const prog = o.prog ?? 1;
  sides.forEach((sd, i) => { const p = clamp(prog * 4 - i); if (p > 0) inkLine(ctx, sd, { ...o, seed: seedOf(o.seed ?? 5) + i * 17, prog: p }); });
}
function arrowHead(ctx, x, y, ang, size, o = {}) {
  const a1 = ang + Math.PI - 0.5, a2 = ang + Math.PI + 0.5;
  inkLine(ctx, [[x + Math.cos(a1) * size, y + Math.sin(a1) * size], [x, y], [x + Math.cos(a2) * size, y + Math.sin(a2) * size]], { ends: false, amp: (o.amp ?? S.stroke.rough) * 0.5, ...o, prog: 1, tip: false });
}
// a stroke with an arrowhead that appears only once the line has fully drawn (undrawn things stay invisible)
function inkArrow(ctx, pts, o = {}) {
  const prog = o.prog ?? 1; if (prog <= 0) return;
  inkLine(ctx, pts, o);
  const k = smooth(0.9, 1, prog); if (k <= 0) return;
  const [x, y, a] = polyAt(pts, 1);
  arrowHead(ctx, x, y, a, (o.head ?? 16) * (0.4 + 0.6 * k), { ...o, alpha: (o.alpha ?? 1) * k });
}
// parallel rough hatch lines clipped to a polygon (shading, chalk fills, blueprint fills)
function hatch(ctx, poly, o = {}) {
  const [x0, y0, x1, y1] = bbox(poly), ang = o.angle ?? -0.8, gap = o.gap ?? 12, d = Math.hypot(x1 - x0, y1 - y0);
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, ca = Math.cos(ang), sa = Math.sin(ang);
  ctx.save(); pathPts(ctx, poly); ctx.clip();
  for (let k = -d / 2, i = 0; k < d / 2; k += gap, i++) {
    const px = cx - sa * k, py = cy + ca * k;
    inkLine(ctx, [[px - ca * d / 2, py - sa * d / 2], [px + ca * d / 2, py + sa * d / 2]], { w: o.w ?? 1.6, color: o.color, alpha: o.alpha ?? 0.5, seed: (o.seed ?? 1) + i, t: o.t, passes: 1, amp: 1.2 });
  }
  ctx.restore();
}

// ------------------------------------------------------------------ paper cut-outs
// A cut-out piece: drop shadow, torn white rim, coloured body with paper fibre. In chalk/blueprint styles the
// same call draws a chalk or line-work version, so scenes never branch on the style.
function cutout(g, pts, color, o = {}) {
  if (STYLE.cutout) return STYLE.cutout(g, pts, color, o);
  const seed = o.seed ?? 1;
  if (S.kind !== 'paper') {
    const body = o.smooth ? pts : tear(pts, 0.6, seed + 3, 6);
    pathPts(g, body); g.fillStyle = S.kind === 'chalk' ? hexA(color, 0.16) : S.lineFill; g.fill();
    if (S.kind === 'chalk' && o.hatch !== false) hatch(g, body, { color, alpha: 0.32, gap: 9, seed });
    inkLine(g, [...body, body[0]], { color: o.line || color, w: S.kind === 'chalk' ? 3.2 : 2.4, seed, ends: false, amp: 0.8 });
    return body;
  }
  const ew = o.edge ?? S.tornEdge;
  const rim = ew > 0 ? tear(offsetPts(pts, ew * 0.75), ew * 0.45, seed, 4.5, 0.35) : null;
  if (o.shadow !== 0) {
    g.save(); g.shadowColor = o.shadowColor || S.shadow; g.shadowBlur = o.shadow ?? S.shadowBlur; g.shadowOffsetY = (o.shadow ?? S.shadowBlur) * 0.55; g.shadowOffsetX = (o.shadow ?? S.shadowBlur) * 0.25;
    pathPts(g, rim || pts); g.fillStyle = o.edgeColor || S.cardEdge; g.fill(); g.restore();
  }
  if (rim) { pathPts(g, rim); g.fillStyle = o.edgeColor || S.cardEdge; g.fill(); }
  const body = o.smooth ? pts : tear(pts, 0.9, seed + 3, 6);
  pathPts(g, body); g.fillStyle = color; g.fill();
  if ((o.tex ?? 1) > 0) { g.save(); pathPts(g, body); g.clip(); fiberFill(g, bbox(body), 1.4 * (o.tex ?? 1), seed); g.restore(); }
  return body;
}
// mix two #rrggbb colours (u = 0 -> a, 1 -> b), cached in 1/20 steps
function mixHex(a, b, u) {
  if (!a.startsWith('#') || !b.startsWith('#')) return u < 0.5 ? a : b;
  const k = Math.round(clamp(u) * 20);
  return cached(`mix:${a}:${b}:${k}`, () => {
    const p = parseInt(a.slice(1, 7), 16), q = parseInt(b.slice(1, 7), 16), f = k / 20;
    const ch = (sh) => Math.round(((p >> sh) & 255) * (1 - f) + ((q >> sh) & 255) * f);
    return '#' + [16, 8, 0].map((sh) => ch(sh).toString(16).padStart(2, '0')).join('');
  });
}
function hexA(hex, a) {
  if (!hex.startsWith('#')) return hex;
  const n = parseInt(hex.slice(1, 7), 16); return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`;
}
function tapeStrip(g, x, y, w, rot, seed) {
  if (S.kind !== 'paper') return;
  g.save(); g.translate(x, y); g.rotate(rot);
  const p = tear(rrPts(-w / 2, -15, w, 30, 1), 1.6, seed, 4);
  pathPts(g, p); g.fillStyle = S.tape; g.fill();
  g.globalAlpha = 0.25; g.strokeStyle = S.tapeShine; g.lineWidth = 1; g.beginPath(); g.moveTo(-w / 2 + 6, -9); g.lineTo(w / 2 - 6, -9); g.stroke();
  g.restore();
}

// ------------------------------------------------------------------ cards
// kind: 'note' (ruled, red margin), 'plain', 'sticky', 'kraft', 'label' (torn all round)
// torn: 'top' | 'all' | 'none';  tape: 0, 1 or 2 strips
function cardSprite(w, h, o = {}) {
  const kind = o.kind || 'plain', seed = o.seed ?? (w * 7 + h * 13), torn = o.torn ?? (kind === 'label' ? 'all' : kind === 'note' ? 'top' : 'none');
  const key = `card:${S.name}:${w}x${h}:${kind}:${seed}:${torn}:${o.tape ?? 2}:${o.color || ''}:${o.rule || ''}`;
  return cached(key, () => sprite(w + 80, h + 80, 40, 40, (g) => {
    const color = o.color || (kind === 'sticky' ? S.sticky : kind === 'kraft' ? S.kraft : S.card);
    if (STYLE.card) return STYLE.card(g, w, h, kind, color, seed, o);
    let pts;
    if (torn === 'all') pts = tear(rrPts(0, 0, w, h, 2), 3.2, seed, 7);
    else if (torn === 'top') { const top = []; for (let x = 0; x <= w; x += 9) top.push([x, (rnd(seed, x) - 0.5) * 7]); pts = [...top, [w, h], [0, h]]; }
    else pts = rrPts(0, 0, w, h, 5);
    if (S.kind === 'paper') {
      const body = cutout(g, pts, color, { seed, edge: torn === 'all' ? 4 : 0, smooth: true, tex: 0.5 });
      g.save(); pathPts(g, body); g.clip();
      if (kind === 'note') {
        const sp = o.rule || 50; g.strokeStyle = S.rule; g.lineWidth = 1.6;
        for (let y = o.first || 90; y < h - 8; y += sp) { g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke(); }
        g.strokeStyle = S.margin; g.lineWidth = 2; g.beginPath(); g.moveTo(o.marginX || 60, 0); g.lineTo(o.marginX || 60, h); g.stroke();
      }
      // a soft curl shadow along the bottom edge
      const cg = g.createLinearGradient(0, h - 26, 0, h); cg.addColorStop(0, S.curl[0]); cg.addColorStop(1, S.curl[1]);
      g.fillStyle = cg; g.fillRect(0, h - 26, w, 26);
      g.restore();
      const nt = o.tape ?? 2;
      if (nt === 1) tapeStrip(g, w / 2, -2, Math.min(130, w * 0.4), (rnd(seed, 9) - 0.5) * 0.2, seed + 50);
      if (nt === 2) { tapeStrip(g, w * 0.12, -2, Math.min(110, w * 0.25), -0.32, seed + 51); tapeStrip(g, w * 0.88, -2, Math.min(110, w * 0.25), 0.28, seed + 52); }
    } else {
      pathPts(g, pts); g.fillStyle = hexA(S.boardFill, S.kind === 'chalk' ? 0.16 : 0.14); g.fill();
      inkRect(g, 2, 2, w - 4, h - 4, { color: S.cardEdge, w: S.kind === 'chalk' ? 3 : 2, seed, alpha: 0.85 });
      if (S.kind === 'blueprint') for (const [cx, cy] of [[0, 0], [w, 0], [0, h], [w, h]]) { g.strokeStyle = S.cardEdge; g.lineWidth = 2; g.beginPath(); g.arc(cx, cy, 7, 0, TAU); g.stroke(); }
      if (kind === 'note') { g.strokeStyle = S.rule; g.lineWidth = 1.4; for (let y = o.first || 90; y < h - 8; y += o.rule || 50) { g.beginPath(); g.moveTo(8, y); g.lineTo(w - 8, y); g.stroke(); } }
    }
  }, o.res ?? 1.5));
}
function drawCard(ctx, x, y, w, h, o = {}) { blit(ctx, cardSprite(w, h, o), x, y, o); }

// ------------------------------------------------------------------ tags, stamps
// luggage tag with a short label (edge weights, prices, small notes)
function tagSprite(label, o = {}) {
  const size = o.size || S.size.tag, f = o.font || 'hand';
  return cached(`tag:${S.name}:${label}:${size}:${o.color || ''}:${f}`, () => {
    const tw = measureText(label, f, size), w = tw + 30, h = size * 1.15;
    return sprite(w + 70, h + 50, w / 2 + 35, h / 2 + 25, (g) => {
      const pts = [[-w / 2, -h / 2], [w / 2, -h / 2], [w / 2, h / 2], [-w / 2, h / 2], [-w / 2 - 14, 0]];
      cutout(g, pts, o.color || S.card, { seed: hashStr(label), edge: 3, shadow: 7, tex: 0.5, hatch: false, line: o.ink || S.ink });
      if (S.kind === 'paper') { g.fillStyle = S.tagHole; g.beginPath(); g.arc(-w / 2 - 3, 0, 3.4, 0, TAU); g.fill(); }
      drawText(g, label, 7, size * 0.36, { font: f, size, color: o.ink || (S.kind === 'paper' ? S.cardInk : S.ink), align: 'center' });
    }, 2.5);
  });
}
// a torn paper slip (w x h, centred on 0,0) to letter a short note on, so it reads on any part of the paper
function slipSprite(w, h, seed = 1) {
  w = Math.round(w); h = Math.round(h);
  return cached(`slip:${S.name}:${w}x${h}:${seed}`, () => sprite(w + 50, h + 50, w / 2 + 25, h / 2 + 25, (g) => {
    cutout(g, tear(rrPts(-w / 2, -h / 2, w, h, 4), 1.6, seed, 6), S.card, { seed, edge: 3, shadow: 7, tex: 0.5, hatch: false, line: S.ink });
  }, 2.5));
}
function stampSprite(label, color, size) {
  color = textInk(color); // a stamp is text: its deep shade keeps it readable on the open paper
  return cached(`stamp:${label}:${color}:${size}`, () => {
    const tw = measureText(label, 'hand', size), w = tw + 64, h = size + 46; // clear room between the words and the frame
    return sprite(w + 30, h + 30, w / 2 + 15, h / 2 + 15, (g) => {
      g.fillStyle = S.card; g.globalAlpha = 0.9; g.fillRect(-w / 2, -h / 2, w, h); g.globalAlpha = 1; // stamped on a slip: readable on any backdrop
      g.strokeStyle = color; g.lineWidth = 5; g.strokeRect(-w / 2, -h / 2, w, h);
      g.lineWidth = 2; g.strokeRect(-w / 2 + 7, -h / 2 + 7, w - 14, h - 14);
      // stamp ink is heavy: a same-colour outline thickens the thin hand lettering so it stays readable
      drawText(g, label, 0, size * 0.36, { font: 'hand', size, color, align: 'center', halo: color, haloW: Math.max(2, size * 0.06) });
      g.globalCompositeOperation = 'destination-out'; const r = mulberry32(hashStr(label));
      for (let i = 0; i < 160; i++) { g.globalAlpha = 0.2 + r() * 0.35; g.fillRect(-w / 2 + r() * w, -h / 2 + r() * h, 1 + r() * 2, 1 + r() * 1.5); }
    }, 2);
  });
}
