// kit/type.js: hand lettering. Patrick Hand and Caveat Brush are read with opentype.js so every letter is a
// real outline we can draw on stroke by stroke (write: 0..1) and shiver on boil frames. Symbols the fonts lack
// (→ ← ∞ ≤ ≥ ≠ ✓ ✗ ★) are drawn as hand strokes in the same weight. Code uses JetBrains Mono drawn one glyph at a
// time on a fixed grid, so ligatures can never turn != into ≠.
'use strict';
const FONTS = {};
const FONT_FILES = {
  hand: 'fonts/patrick-hand-latin-400-normal.woff',
  brush: 'fonts/caveat-brush-latin-400-normal.woff',
};
async function loadFonts() {
  if (S.fontFiles) Object.assign(FONT_FILES, S.fontFiles); // a style may letter in other fonts (kit/styles/)
  for (const [k, f] of Object.entries(FONT_FILES)) {
    const r = await fetch(f); if (!r.ok) throw new Error(`font ${f}: HTTP ${r.status} (serve the folder over http, not file://)`);
    FONTS[k] = opentype.parse(await r.arrayBuffer());
  }
  const faces = [
    [S.font.mono, 'fonts/jetbrains-mono-latin-400-normal.woff', { weight: '400' }],
    [S.font.mono, 'fonts/jetbrains-mono-latin-700-normal.woff', { weight: '700' }],
    [S.font.hand, FONT_FILES.hand, {}], [S.font.brush, FONT_FILES.brush, {}],
  ];
  for (const [name, file, desc] of faces) { const ff = new FontFace(name, `url(${file})`, desc); await ff.load(); document.fonts.add(ff); }
  await document.fonts.ready;
}

// ------------------------------------------------------------------ glyph outlines (em units, y down), cached
function flattenGlyph(fk, glyph) {
  return cached(`gl:${fk}:${glyph.index}`, () => {
    const upm = FONTS[fk].unitsPerEm, contours = []; let cur = null, px = 0, py = 0;
    const P2 = (x, y) => [x / upm, -y / upm];
    for (const c of glyph.path.commands) {
      if (c.type === 'M') { cur = [P2(c.x, c.y)]; contours.push(cur); px = c.x; py = c.y; }
      else if (c.type === 'L') { cur.push(P2(c.x, c.y)); px = c.x; py = c.y; }
      else if (c.type === 'Q') { const n = 6; for (let i = 1; i <= n; i++) { const u = i / n, v = 1 - u; cur.push(P2(v * v * px + 2 * v * u * c.x1 + u * u * c.x, v * v * py + 2 * v * u * c.y1 + u * u * c.y)); } px = c.x; py = c.y; }
      else if (c.type === 'C') { const n = 8; for (let i = 1; i <= n; i++) { const u = i / n, v = 1 - u; cur.push(P2(v * v * v * px + 3 * v * v * u * c.x1 + 3 * v * u * u * c.x2 + u * u * u * c.x, v * v * v * py + 3 * v * v * u * c.y1 + 3 * v * u * u * c.y2 + u * u * u * c.y)); } px = c.x; py = c.y; }
      else if (c.type === 'Z' && cur && cur.length) { cur.push(cur[0].slice()); }
    }
    const lens = contours.map((p) => polyLength(p)), path = new Path2D();
    for (const p of contours) { path.moveTo(p[0][0], p[0][1]); for (let i = 1; i < p.length; i++) path.lineTo(p[i][0], p[i][1]); path.closePath(); }
    return { contours, lens, len: lens.reduce((a, b) => a + b, 0), path, adv: glyph.advanceWidth / upm };
  });
}

// ------------------------------------------------------------------ hand-drawn symbols (em units, baseline y = 0)
const HAND_GLYPHS = {
  '→': { w: 0.95, s: [[[0.08, -0.3], [0.84, -0.3]], [[0.6, -0.48], [0.86, -0.3], [0.6, -0.12]]] },
  '←': { w: 0.95, s: [[[0.87, -0.3], [0.11, -0.3]], [[0.35, -0.48], [0.09, -0.3], [0.35, -0.12]]] },
  '∞': { w: 0.98, s: [Array.from({ length: 49 }, (_, i) => { const a = (i / 48) * TAU, d = 1 + Math.sin(a) ** 2; return [0.49 + 0.4 * Math.cos(a) / d, -0.3 + 0.4 * Math.sin(a) * Math.cos(a) / d]; })] },
  '≤': { w: 0.62, s: [[[0.5, -0.56], [0.1, -0.38], [0.5, -0.2]], [[0.1, -0.06], [0.52, -0.06]]] },
  '≥': { w: 0.62, s: [[[0.12, -0.56], [0.52, -0.38], [0.12, -0.2]], [[0.1, -0.06], [0.52, -0.06]]] },
  '≠': { w: 0.66, s: [[[0.1, -0.38], [0.56, -0.38]], [[0.1, -0.2], [0.56, -0.2]], [[0.45, -0.58], [0.21, -0.0]]] },
  '✓': { w: 0.72, s: [[[0.08, -0.33], [0.27, -0.08], [0.66, -0.66]]] },
  '✗': { w: 0.62, s: [[[0.1, -0.6], [0.52, -0.06]], [[0.52, -0.6], [0.1, -0.06]]] },
  '★': { w: 0.8, fill: true, s: [Array.from({ length: 11 }, (_, i) => { const a = -Math.PI / 2 + (i * Math.PI) / 5, r = i % 2 ? 0.15 : 0.36; return [0.4 + Math.cos(a) * r, -0.32 + Math.sin(a) * r]; })] },
};
HAND_GLYPHS['∞'].len = polyLength(HAND_GLYPHS['∞'].s[0]);
for (const g of Object.values(HAND_GLYPHS)) g.len = g.len || g.s.reduce((a, p) => a + polyLength(p), 0);

// ------------------------------------------------------------------ shaping: text -> positioned items (em units)
// Markup: ^{...} is a superscript (for O(n^{k+1})). Everything else is literal.
const SCRATCH = typeof document !== 'undefined' ? document.createElement('canvas').getContext('2d') : null;
function shape(text, fk = 'hand') {
  return cached(`sh:${fk}:${text}`, () => {
    const font = FONTS[fk], items = []; let x = 0, prev = null;
    const runs = []; const re = /\^\{([^}]*)\}/g; let m, last = 0;
    while ((m = re.exec(text))) { if (m.index > last) runs.push([text.slice(last, m.index), 1, 0]); runs.push([m[1], 0.62, -0.42]); last = re.lastIndex; }
    if (last < text.length) runs.push([text.slice(last), 1, 0]);
    for (const [s, sc, dy] of runs) for (const ch of s) {
      const hg = HAND_GLYPHS[ch];
      if (hg) { items.push({ kind: 'h', ch, x, sc, dy, w: hg.w * sc, len: hg.len * sc }); x += hg.w * sc; prev = null; continue; }
      const glyph = font.charToGlyph(ch);
      if (!glyph || glyph.index === 0) { // not in the font and not hand-drawn: system fallback
        SCRATCH.font = `100px "DejaVu Sans", sans-serif`; const w = SCRATCH.measureText(ch).width / 100;
        items.push({ kind: 'f', ch, x, sc, dy, w: w * sc, len: 0.6 * sc }); x += w * sc; prev = null; continue;
      }
      if (prev) x += (font.getKerningValue(prev, glyph) / font.unitsPerEm) * sc;
      const gd = flattenGlyph(fk, glyph);
      items.push({ kind: ch === ' ' ? 's' : 'g', ch, x, sc, dy, w: gd.adv * sc, len: ch === ' ' ? 0.12 : gd.len * sc, gd });
      x += gd.adv * sc; prev = glyph;
    }
    let c = 0; for (const it of items) { it.c0 = c; c += it.len; }
    return { items, width: x, ink: c };
  });
}
function measureText(text, fk = 'hand', size = 40) {
  if (fk === 'mono') { SCRATCH.font = `400 ${size}px "${S.font.mono}"`; return SCRATCH.measureText('M').width * text.length; }
  if (S.fontSize) size = S.fontSize(fk, size);
  return shape(text, fk).width * size;
}
function wrapText(text, fk, size, maxW) {
  const words = text.split(' '), lines = []; let cur = '';
  for (const w of words) { const tryS = cur ? cur + ' ' + w : w; if (cur && measureText(tryS, fk, size) > maxW) { lines.push(cur); cur = w; } else cur = tryS; }
  if (cur) lines.push(cur);
  return lines;
}

// ------------------------------------------------------------------ drawing
// Text in one of the theme's meaning colours (S.accent, S.good, ...) is drawn in that colour's deep shade (S.txt),
// so labels keep their contrast on the open paper; pass o.vivid to keep the bright colour on purpose.
function textInk(c) { return (S.txtOf && S.txtOf[c]) || c; }
// o: {font:'hand'|'brush'|'mono', size, color, align:'left'|'center'|'right', base:'alphabetic'|'middle'|'top',
//     write: 0..1 (stroke-on progress; omit = fully written), alpha, t + boil (px of letter shiver on boil
//     frames), seed, halo: colour (+ haloW) to lift text off busy backgrounds, maxW (shrink to fit), tip}
function drawText(ctx, text, x, y, o = {}) {
  text = String(text);
  let size = o.size || S.size.body; const fk = o.font || 'hand';
  if (fk === 'mono') return drawMono(ctx, text, x, y, o);
  if (S.fontSize) size = S.fontSize(fk, size); // a style's font may run small (Caveat's x-height is 0.37 em)
  const sh = shape(text, fk);
  if (o.maxW && sh.width * size > o.maxW) size = o.maxW / sh.width;
  const wpx = sh.width * size, alpha = o.alpha ?? 1;
  if (alpha <= 0.003) return wpx;
  const x0 = o.align === 'center' ? x - wpx / 2 : o.align === 'right' ? x - wpx : x;
  const y0 = o.base === 'middle' ? y + size * 0.3 : o.base === 'top' ? y + size * 0.78 : y;
  const color = o.vivid ? o.color || S.ink : textInk(o.color || S.ink), fill = S.stroke.chalk ? chalkStyle(ctx, color) : color;
  const write = o.write ?? 1, head = write * sh.ink;
  const boil = (o.boil || 0) * (S.textBoil ?? 1), seed = seedOf(o.seed ?? text), k = o.t != null ? boilKey(o.t) : 0;
  ctx.save(); ctx.globalAlpha *= alpha; ctx.translate(x0, y0); ctx.lineJoin = 'round'; ctx.lineCap = 'round';
  let tip = null;
  for (let i = 0; i < sh.items.length; i++) {
    const it = sh.items[i]; if (it.kind === 's') continue;
    const q = write >= 1 ? 1 : clamp((head - it.c0) / Math.max(1e-6, it.len));
    if (q <= 0) break;
    ctx.save(); ctx.translate(it.x * size, it.dy * size);
    if (boil) { ctx.translate((rnd(seed + i, k * 2) - 0.5) * 2 * boil, (rnd(seed + i, k * 2 + 1) - 0.5) * 2 * boil); ctx.rotate((rnd(seed + i, k * 3 + 7) - 0.5) * 0.03 * boil); }
    const sz = size * it.sc; ctx.scale(sz, sz);
    if (it.kind === 'g') {
      if (o.halo && q >= 1) { ctx.strokeStyle = o.halo; ctx.lineWidth = (o.haloW ?? 7) / sz; ctx.stroke(it.gd.path); }
      if (q >= 1) { ctx.fillStyle = fill; ctx.fill(it.gd.path); if (S.textStroke) { ctx.strokeStyle = fill; ctx.lineWidth = S.textStroke; ctx.stroke(it.gd.path); } }
      else {
        ctx.globalAlpha *= 1; ctx.fillStyle = fill; ctx.save(); ctx.globalAlpha *= smooth(0.45, 1, q); ctx.fill(it.gd.path); ctx.restore();
        ctx.strokeStyle = fill; ctx.lineWidth = Math.max(1.2, size * 0.035) / sz;
        let budget = q * it.gd.len;
        for (let c = 0; c < it.gd.contours.length && budget > 0; c++) {
          const p = it.gd.contours[c], l = it.gd.lens[c];
          const part = budget >= l ? p : polySlice(p, 0, budget / l); budget -= l;
          pathPts(ctx, part, false); ctx.stroke();
          if (budget <= 0) { const e = part[part.length - 1]; tip = [it.x * size + e[0] * sz, it.dy * size + e[1] * sz]; }
        }
      }
    } else if (it.kind === 'h') {
      const hg = HAND_GLYPHS[it.ch], lw = (fk === 'brush' ? 0.095 : 0.075);
      ctx.strokeStyle = fill; ctx.fillStyle = fill; ctx.lineWidth = lw; let budget = q * hg.len;
      for (const p of hg.s) {
        if (budget <= 0) break; const l = polyLength(p), part = budget >= l ? p : polySlice(p, 0, budget / l); budget -= l;
        if (hg.fill && q >= 1) { pathPts(ctx, p); ctx.fill(); } else { pathPts(ctx, part, false); ctx.stroke(); }
      }
    } else { // system fallback glyph
      ctx.globalAlpha *= smooth(0, 1, q); ctx.fillStyle = fill; ctx.font = `1px "DejaVu Sans", sans-serif`; ctx.fillText(it.ch, 0, 0);
    }
    ctx.restore();
  }
  if (tip && o.tip !== false) { if (STYLE.penTip) STYLE.penTip(ctx, tip[0], tip[1], color, write); else { ctx.fillStyle = color; ctx.beginPath(); ctx.arc(tip[0], tip[1], Math.max(1.8, size * 0.045), 0, TAU); ctx.fill(); } }
  ctx.restore();
  return wpx;
}
// several lines (already wrapped) with a line height; write progress runs across all lines in order
function drawLines(ctx, lines, x, y, o = {}) {
  const lh = o.lh || (o.size || S.size.body) * 1.25, fk = o.font || 'hand';
  const inks = lines.map((s) => (fk === 'mono' ? s.length : shape(s, fk).ink + 0.001)), tot = inks.reduce((a, b) => a + b, 0);
  let acc = 0;
  lines.forEach((s, i) => {
    const w = o.write == null ? undefined : clamp((o.write * tot - acc) / inks[i]);
    acc += inks[i];
    if (w === undefined || w > 0) drawText(ctx, s, x, y + i * lh, { ...o, write: w, seed: (o.seed ?? s) + ':' + i });
  });
  return lines.length * lh;
}

// ------------------------------------------------------------------ monospace (code, aligned numbers)
// One glyph at a time on a fixed grid. o: {size, weight, color, colors: [per char], align, write: 0..1 (typed)}
function monoW(size) { return cached(`monoW:${size}`, () => { SCRATCH.font = `400 ${size}px "${S.font.mono}"`; return SCRATCH.measureText('M').width; }); }
function drawMono(ctx, text, x, y, o = {}) {
  const size = o.size || S.size.code, cw = monoW(size), n = text.length, wpx = cw * n;
  const x0 = o.align === 'center' ? x - wpx / 2 : o.align === 'right' ? x - wpx : x;
  const shown = o.write == null ? n : Math.floor(clamp(o.write) * n + 1e-6);
  ctx.save(); ctx.globalAlpha *= o.alpha ?? 1; ctx.font = `${o.weight || 400} ${size}px "${S.font.mono}"`; ctx.textBaseline = 'alphabetic';
  for (let i = 0; i < shown; i++) {
    const ch = text[i]; if (ch === ' ') continue;
    const col = (o.colors && o.colors[i]) || o.color || S.ink;
    ctx.fillStyle = S.stroke.chalk ? chalkStyle(ctx, col) : col; ctx.fillText(ch, x0 + i * cw, y);
  }
  if (o.write != null && o.write < 1 && o.caret !== false) { ctx.fillStyle = o.color || S.ink; ctx.fillRect(x0 + shown * cw + 1, y - size * 0.78, Math.max(2, size * 0.08), size * 0.95); }
  ctx.restore();
  return wpx;
}
