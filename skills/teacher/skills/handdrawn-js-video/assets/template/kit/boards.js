// kit/boards.js: paper boards that hold information. The input note (raw input written by hand, with spans the
// scene can fly into the graph), the code card (monospace, syntax colours, typed reveal, active-line focus), the
// dry-run table (hand-written numbers filling cell by cell) and the complexity ladder.
// Each board has place(keys) with keys [[t, x, y, rot, alpha]] so it can slide in, move, and leave.
'use strict';
function placed(keys, x, y) { return keys || [[0, x, y, 0, 1]]; }
function placeAt(keys, t) {
  if (S.stepFps) t = Math.floor(t * S.stepFps + 1e-6) / S.stepFps; // a stop-motion style moves boards on its own steps
  const [x, y, r, a] = track(t, keys, Ease.inOut); return { x, y, r, a };
}
// slide a board in from `from` ([dx, dy]) at `at`, out to `to` at `out`
function slideKeys(x, y, at, out = Infinity, from = [-900, 0], to = [-900, 0], rot = -0.015) {
  const k = [[at, x + from[0], y + from[1], rot - 0.06, 0], [at + 0.01, x + from[0], y + from[1], rot - 0.06, 1], [at + 0.7, x, y, rot, 1]];
  if (out < Infinity) k.push([out, x, y, rot, 1], [out + 0.6, x + to[0], y + to[1], rot + 0.05, 1], [out + 0.61, x + to[0], y + to[1], rot, 0]);
  return k;
}

// ------------------------------------------------------------------ input note (decoder)
function note(o) {
  const w = o.w || 560, h = o.h || 700, rule = o.rule || 56, first = o.first || 104, pad = o.padX || 80;
  let keys = placed(o.keys, o.x ?? 100, o.y ?? 150);
  const rows = [], hls = [], rings = [];
  const N = {
    w, h, place(k) { keys = k; return N; },
    // write `text` on row r at time `at` (dur = writing time). o2: {color, font, size, x}
    line(r, text, at, o2 = {}) { rows.push({ r, text, at, dur: o2.dur ?? Math.min(1.3, 0.2 + text.length * 0.05), color: o2.color, font: o2.font || 'hand', size: o2.size || 44, x: o2.x ?? pad }); return N; },
    hl(r, o2 = {}) { hls.push({ r, at: o2.at, until: o2.until ?? Infinity, from: o2.from ?? 0, to: o2.to, color: o2.color || S.hl }); return N; },
    ring(r, o2 = {}) { rings.push({ r, at: o2.at, until: o2.until ?? Infinity, from: o2.from ?? 0, to: o2.to, color: o2.color || S.accent }); return N; },
    // world position of the middle of characters [from, to) on row r (for chips flying out of the text)
    spanXY(r, from, to, t) {
      const row = rows.filter((q) => q.r === r).pop(), P0 = placeAt(keys, t); if (!row) return [P0.x, P0.y];
      const x0 = row.x + measureText(row.text.slice(0, from), row.font, row.size), x1 = row.x + measureText(row.text.slice(0, to ?? row.text.length), row.font, row.size);
      const lx = (x0 + x1) / 2, ly = first + r * rule - row.size * 0.32, c = Math.cos(P0.r), s = Math.sin(P0.r);
      return [P0.x + lx * c - ly * s, P0.y + lx * s + ly * c];
    },
  };
  world(o.z ?? 35, (ctx, t) => {
    const p = placeAt(keys, t); if (p.a <= 0.003) return;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha *= p.a;
    drawCard(ctx, 0, 0, w, h, { kind: o.kind || 'note', tape: 2, seed: o.seed ?? 701, rule, first: first + 14, marginX: pad - 22, t, jit: 'note' });
    const ink = S.kind === 'paper' ? S.cardInk : S.ink;
    for (const q of hls) {
      const row = rows.filter((x) => x.r === q.r).pop(); if (!row) continue;
      const k = 1 - P(t, q.until, 0.25), pr = P(t, q.at, 0.35, Ease.out); if (pr <= 0 || k <= 0) continue;
      const x0 = row.x + measureText(row.text.slice(0, q.from), row.font, row.size) - 8, x1 = row.x + measureText(row.text.slice(0, q.to ?? row.text.length), row.font, row.size) + 8;
      const yb = first + q.r * rule;
      ctx.save(); ctx.globalAlpha *= k; ctx.fillStyle = q.color; const r = mulberry32(q.r + 7);
      ctx.beginPath(); ctx.moveTo(x0, yb - row.size * 0.82 + r() * 3); ctx.lineTo(x0 + (x1 - x0) * pr, yb - row.size * 0.82 + r() * 3); ctx.lineTo(x0 + (x1 - x0) * pr - 3, yb + 8 - r() * 3); ctx.lineTo(x0 + 2, yb + 8); ctx.closePath(); ctx.fill(); ctx.restore();
    }
    for (const q of rows) {
      const wr = P(t, q.at, q.dur, Ease.lin); if (wr <= 0) continue;
      drawText(ctx, q.text, q.x, first + q.r * rule, { font: q.font, size: q.size, color: q.color || ink, write: wr, t, boil: 0.35, seed: 'n' + q.r + q.text });
    }
    for (const q of rings) {
      const row = rows.filter((x) => x.r === q.r).pop(); if (!row) continue;
      const x0 = row.x + measureText(row.text.slice(0, q.from), row.font, row.size), x1 = row.x + measureText(row.text.slice(0, q.to ?? row.text.length), row.font, row.size);
      inkEllipse(ctx, (x0 + x1) / 2, first + q.r * rule - row.size * 0.3, (x1 - x0) / 2 + 14, row.size * 0.62, { color: q.color, w: 4.5, prog: P(t, q.at, 0.5), alpha: 1 - P(t, q.until, 0.25), seed: 'nr' + q.r + q.at, t, tip: true });
    }
    ctx.restore();
  });
  return N;
}

// ------------------------------------------------------------------ code card
const LANG = {
  kw: new Set('auto break case catch class const constexpr continue default delete do else enum explicit for friend if inline namespace new noexcept operator private protected public return sizeof static struct switch template this throw try typedef typename using virtual while def elif in is not and or lambda pass yield import from as with None True False function let var of null undefined true false fn mut impl pub match loop'.split(' ')),
  type: new Set('int long short char bool double float void unsigned signed size_t string vector map unordered_map set unordered_set pair queue deque stack priority_queue array tuple list dict str usize i32 i64 u32 u64 Vec HashMap'.split(' ')),
};
function tokenizeLine(s) { // -> per-character colour keys
  const out = Array(s.length).fill('txt'); let i = 0;
  const com = s.search(/\/\/|#(?!include|define)/); const end = com >= 0 ? com : s.length;
  for (let k = end; k < s.length; k++) out[k] = 'com';
  const re = /"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'|\b\d+(?:\.\d+)?(?:e\d+)?\b|[A-Za-z_][A-Za-z0-9_]*/g; let m;
  const body = s.slice(0, end);
  while ((m = re.exec(body))) {
    const w = m[0]; let k = 'txt';
    if (w[0] === '"' || w[0] === "'") k = 'str'; else if (/^\d/.test(w)) k = 'num'; else if (LANG.kw.has(w)) k = 'kw'; else if (LANG.type.has(w)) k = 'type'; else if (body[m.index + w.length] === '(') k = 'fn';
    for (let j = 0; j < w.length; j++) out[m.index + j] = k;
  }
  void i; return out;
}
// o: {code, x, y, w, size, lh, title ('C++'), keys, z, numbers (line numbers, default true), padT (top of the first
//     line, default 92), padB (below the last line, default 34)}
// Focus never fades code into the paper: the other lines turn the single S.codeDim colour (6:1 on the card) while
// the focused lines keep their syntax colours, the highlighter and the gutter pointer.
function codeCard(o) {
  const lines = o.code.replace(/\s+$/, '').split('\n'), size = o.size || S.size.code, lh = o.lh || Math.round(size * 1.36);
  const cw = monoW(size), gutter = o.numbers === false ? 30 : cw * 2 + 34, padT = o.padT ?? 92;
  const w = o.w || Math.ceil(gutter + cw * Math.max(...lines.map((l) => l.length)) + 36), h = o.h || Math.round(padT + (lines.length - 1) * lh + size * 0.3 + (o.padB ?? 34));
  let keys = placed(o.keys, o.x ?? 90, o.y ?? 120);
  const reveals = [], focuses = [];
  const colors = lines.map((l) => tokenizeLine(l).map((k) => S.syntax[k]));
  const C = {
    w, h, lines, place(k) { keys = k; return C; },
    // typed reveal of lines a..b (1-based, inclusive) over [at, at + dur]
    reveal(a, b, at, dur = 0.8) { reveals.push({ a, b, at, dur }); return C; },
    focus(a, b, o2 = {}) { focuses.push({ a, b, at: o2.at, until: o2.until ?? Infinity, color: o2.color || S.hl }); return C; },
    lineXY(n, t, right = false) { const p = placeAt(keys, t); return [p.x + (right ? w - 30 : gutter + 14), p.y + padT + (n - 1) * lh - size * 0.32]; },
  };
  world(o.z ?? 36, (ctx, t) => {
    const p = placeAt(keys, t); if (p.a <= 0.003) return;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha *= p.a;
    drawCard(ctx, 0, 0, w, h, { kind: 'plain', tape: 2, seed: o.seed ?? 702, t, jit: 'code' });
    if (o.title) drawText(ctx, o.title, w - 40, 62, { font: 'brush', size: 50, color: S.accent, align: 'right', write: P(t, keys[0][0] + 0.4, 0.5), t, boil: 0.7 });
    // which characters are revealed on each line
    const shown = lines.map(() => 0);
    for (const r of reveals) {
      const total = lines.slice(r.a - 1, r.b).reduce((s, l) => s + l.length + 6, 0); let budget = P(t, r.at, r.dur, Ease.lin) * total;
      for (let n = r.a; n <= r.b; n++) { const len = lines[n - 1].length; const k = clamp(budget / (len + 6)); shown[n - 1] = Math.max(shown[n - 1], k); budget -= len + 6; }
    }
    // focus: highlighter swipe behind the active lines (which turn bold), the others turn S.codeDim
    let dimOthers = 0; const active = new Set(), boldK = {};
    for (const f of focuses) {
      const k = env(t, f.at, f.until, 0.3, 0.25); if (k <= 0) continue;
      dimOthers = Math.max(dimOthers, k);
      for (let n = f.a; n <= f.b; n++) { active.add(n); boldK[n] = Math.max(boldK[n] || 0, k); }
      const sw = P(t, f.at, 0.35, Ease.out), y0 = padT + (f.a - 1) * lh - size * 0.95, y1 = padT + (f.b - 1) * lh + size * 0.38;
      ctx.save(); ctx.globalAlpha *= k; ctx.fillStyle = f.color; const r = mulberry32(f.a * 31 + f.b);
      ctx.beginPath(); ctx.moveTo(gutter - 6, y0 + r() * 4); ctx.lineTo(gutter - 6 + (w - gutter - 24) * sw, y0 + r() * 4); ctx.lineTo(gutter - 9 + (w - gutter - 24) * sw, y1 - r() * 4); ctx.lineTo(gutter - 4, y1); ctx.closePath(); ctx.fill(); ctx.restore();
      // pointer in the gutter
      const ay = (y0 + y1) / 2;
      inkArrow(ctx, [[-30, ay - 2], [gutter - 30, ay]], { color: S.accent, w: 4, prog: P(t, f.at, 0.3), alpha: k, seed: 'ptr' + f.a, t, head: 12 });
    }
    lines.forEach((ln, i) => {
      const k = shown[i]; if (k <= 0) return;
      const y = padT + i * lh, dim = active.size && !active.has(i + 1) ? dimOthers : 0;
      const cols = dim > 0 ? colors[i].map((c) => mixHex(c, S.codeDim, dim)) : colors[i];
      if (o.numbers !== false) drawMono(ctx, String(i + 1).padStart(2, ' '), 14, y, { size: Math.max(26, size * 0.88), color: S.codeDim });
      const b = boldK[i + 1] || 0, wr = k >= 1 ? undefined : k; // bold cross-fades in with the highlighter
      if (b < 1) drawMono(ctx, ln, gutter, y, { size, colors: cols, write: wr, caret: k < 1, alpha: 1 - b });
      if (b > 0) drawMono(ctx, ln, gutter, y, { size, colors: cols, weight: 700, write: wr, caret: false, alpha: b });
    });
    ctx.restore();
  });
  return C;
}

// ------------------------------------------------------------------ dry-run table
// o: {x, y, cols: ['city 0', ...], rows: ['start', 'round 0', ...], cw, rh, labelW, at (grid draws on), keys, z,
//     headSize (column chips, default S.size.head), labelSize (row labels, default S.size.rowLabel)}
// Column chips are the column's node colour lightened, lettered in dark ink (at least 6:1 on every node colour).
function table(o) {
  const cols = o.cols, rows = o.rows, cw = o.cw || 118, rh = o.rh || 78, lw = o.labelW || 150, hh = o.headH || 62;
  const headSize = o.headSize || S.size.head, labelSize = o.labelSize || S.size.rowLabel;
  const w = lw + cols.length * cw + 30, h = hh + rows.length * rh + 34, at = o.at ?? 0;
  let keys = placed(o.keys, o.x ?? 1200, o.y ?? 560);
  const cells = [], rowHls = [];
  const T = {
    w, h, place(k) { keys = k; return T; },
    cell(r, c, text, t0, o2 = {}) { cells.push({ r, c, text: String(text), at: t0, dur: o2.dur ?? 0.45, color: o2.color, ring: o2.ring, font: o2.font || 'hand', size: o2.size || S.size.table }); return T; },
    row(r, values, t0, stagger = 0.18, o2 = {}) { values.forEach((v, c) => v != null && T.cell(r, c, v, t0 + c * stagger, o2)); return T; },
    hlRow(r, o2 = {}) { rowHls.push({ r, at: o2.at, until: o2.until ?? Infinity }); return T; },
    cellXY(r, c, t) { const p = placeAt(keys, t), lx = lw + c * cw + cw / 2, ly = hh + r * rh + rh / 2 + 6, cs = Math.cos(p.r), sn = Math.sin(p.r); return [p.x + lx * cs - ly * sn, p.y + lx * sn + ly * cs]; },
  };
  world(o.z ?? 37, (ctx, t) => {
    const p = placeAt(keys, t); if (p.a <= 0.003 || t < at - 0.8) return;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha *= p.a;
    drawCard(ctx, 0, 0, w, h, { kind: 'plain', tape: 1, seed: o.seed ?? 703, t, jit: 'table' });
    const ink = S.kind === 'paper' ? S.cardInk : S.ink, g = P(t, at, 0.7, Ease.inOut);
    for (const q of rowHls) { const k = env(t, q.at, q.until, 0.25, 0.25); if (k > 0) { ctx.save(); ctx.globalAlpha *= k; ctx.fillStyle = S.hl; ctx.fillRect(14, hh + q.r * rh + 8, w - 28, rh - 8); ctx.restore(); } }
    // grid drawn on
    for (let r = 0; r <= rows.length; r++) inkLine(ctx, [[14, hh + r * rh + 4], [w - 14, hh + r * rh + 4]], { prog: clamp(g * 1.4 - r * 0.08), color: S.inkFaint, w: 2.2, seed: 'tr' + r, t, passes: 1 });
    for (let c = 0; c <= cols.length; c++) inkLine(ctx, [[lw + c * cw, 12], [lw + c * cw, h - 18]], { prog: clamp(g * 1.4 - c * 0.08), color: S.inkFaint, w: 2.2, seed: 'tc' + c, t, passes: 1 });
    cols.forEach((s, c) => {
      const k = pop(t, at + 0.2 + c * 0.08, 0.45); if (k.s <= 0) return;
      const col = (o.colColors || S.node)[c % S.node.length], cx = lw + c * cw + cw / 2;
      ctx.save(); ctx.translate(cx, hh / 2 + 4); if (k.rot) ctx.rotate(k.rot); ctx.scale(k.sx, k.sy);
      const chH = Math.round(headSize * 1.32);
      const chip = mixHex(col, S.chipTo, S.chipK); // the column's node colour, lightened toward the card
      if (S.kind === 'paper') { pathPts(ctx, rrPts(-cw / 2 + 6, -chH / 2, cw - 12, chH, 6)); ctx.fillStyle = chip; ctx.fill(); }
      drawText(ctx, s, 0, 0, { size: headSize, color: S.kind === 'paper' ? S.inkOn(chip, S.ink) : col, align: 'center', base: 'middle', maxW: cw - 18 });
      ctx.restore();
    });
    rows.forEach((s, r) => drawText(ctx, s, 22, hh + r * rh + rh / 2 + labelSize * 0.38, { size: labelSize, color: S.inkSoft, write: P(t, at + 0.3 + r * 0.1, 0.4, Ease.lin), t, maxW: lw - 30 }));
    // cells: the newest value written at or before t wins; the previous one fades as the new one is written
    const byCell = {};
    for (const q of cells) if (t >= q.at) { const key = q.r + ':' + q.c; (byCell[key] = byCell[key] || []).push(q); }
    for (const list of Object.values(byCell)) {
      list.sort((a, b) => a.at - b.at); const q = list[list.length - 1], prev = list[list.length - 2];
      const cx = lw + q.c * cw + cw / 2, cy = hh + q.r * rh + rh / 2 + 6;
      if (prev) drawText(ctx, prev.text, cx, cy, { font: prev.font, size: prev.size, color: prev.color || ink, align: 'center', base: 'middle', alpha: 1 - P(t, q.at, 0.15) });
      drawText(ctx, q.text, cx, cy, { font: q.font, size: q.size, color: q.color || ink, align: 'center', base: 'middle', write: P(t, q.at, q.dur, Ease.lin), t, boil: 0.5, seed: 'cell' + q.r + q.c + q.text });
      if (q.ring) inkEllipse(ctx, cx, cy, cw * 0.44, rh * 0.42, { color: q.ring === true ? S.accent : q.ring, w: 4, prog: P(t, q.at + q.dur * 0.6, 0.45), alpha: 1 - P(t, q.at + 1.6, 0.3), seed: 'cr' + q.r + q.c, t, tip: true });
    }
    ctx.restore();
  });
  return T;
}

// ------------------------------------------------------------------ complexity ladder
// rungs stack bottom (0) to top; each: {name, cx ('O(k·E) time'), cost 0..1 (bar length), at, color}
function ladder(o) {
  const w = o.w || 800, rh = o.rungH || 108, gap = o.gap || 22, n = o.n || 4;
  let keys = placed(o.keys, o.x ?? 110, o.y ?? 170);
  const rungs = [], picks = [];
  const K = {
    place(k) { keys = k; return K; },
    rung(i, r) { rungs.push({ i, ...r }); return K; },
    pick(i, at, text = 'INTERVIEW PICK') { picks.push({ i, at, text }); return K; },
    rungXY(i, t) { const p = placeAt(keys, t); return [p.x + w / 2, p.y + (n - 1 - i) * (rh + gap) + rh / 2]; },
  };
  world(o.z ?? 38, (ctx, t) => {
    const p = placeAt(keys, t); if (p.a <= 0.003 || !rungs.length) return;
    const t0 = Math.min(...rungs.map((r) => r.at)); if (t < t0 - 0.2) return;
    ctx.save(); ctx.translate(p.x, p.y); ctx.rotate(p.r); ctx.globalAlpha *= p.a;
    const H2 = n * (rh + gap) - gap;
    inkLine(ctx, [[-26, H2 + 30], [-26, -30]], { prog: P(t, t0 - 0.2, 0.7), w: 6, color: S.inkSoft, seed: 'railL', t });
    inkLine(ctx, [[w + 26, H2 + 30], [w + 26, -30]], { prog: P(t, t0 - 0.1, 0.7), w: 6, color: S.inkSoft, seed: 'railR', t });
    const ink = S.kind === 'paper' ? S.cardInk : S.ink;
    for (const r of rungs) {
      const k = pop(t, r.at, 0.55); if (k.s <= 0) continue;
      const y = (n - 1 - r.i) * (rh + gap);
      ctx.save(); ctx.translate(w / 2, y + rh / 2); if (k.rot) ctx.rotate(k.rot); ctx.scale(k.sx, k.sy); ctx.translate(-w / 2, -rh / 2);
      drawCard(ctx, 0, 0, w, rh, { kind: 'label', tape: 0, seed: 800 + r.i, t, jit: 'rung' + r.i });
      drawText(ctx, r.name, 30, 48, { size: 40, color: ink, write: P(t, r.at + 0.15, 0.6, Ease.lin), t });
      drawText(ctx, r.cx, w - 30, 48, { size: 38, color: r.color || S.accent, align: 'right', write: P(t, r.at + 0.5, 0.6, Ease.lin), t });
      // cost meter: hatched bar whose length is the cost
      const bw = (w - 60) * clamp(r.cost ?? 0.5) * P(t, r.at + 0.4, 0.6, Ease.out);
      if (bw > 2) { const poly = [[30, 70], [30 + bw, 70], [30 + bw, 88], [30, 88]]; hatch(ctx, poly, { color: r.color || S.accent, alpha: 0.85, gap: 7, angle: -0.9, seed: 'bar' + r.i, t, w: 2.4 }); inkRect(ctx, 30, 70, bw, 18, { color: r.color || S.accent, w: 2, seed: 'barr' + r.i, t, passes: 1 }); }
      ctx.restore();
    }
    for (const q of picks) {
      const k = pop(t, q.at, 0.6); if (k.s <= 0) continue;
      const y = (n - 1 - q.i) * (rh + gap) + rh / 2;
      ctx.save(); ctx.translate(w + 70, y); ctx.scale(k.sx, k.sy); ctx.rotate(Math.sin(t * 2) * 0.08 + (k.rot || 0));
      blit(ctx, cached('pickstar', () => sprite(140, 140, 70, 70, (g) => { const pts = []; for (let i = 0; i < 10; i++) { const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? 22 : 50; pts.push([Math.cos(a) * rr, Math.sin(a) * rr]); } cutout(g, pts, S.gold, { seed: 9, edge: 4, shadow: 10 }); }, 2)), 0, 0);
      ctx.restore();
      // the stamp sits on the open paper just above its rung (the board's top 86 px must be clear of other things)
      stampAt(ctx, t, q.text, w - 200, y - rh / 2 - 45, q.at + 0.3, { size: 36, color: S.good, rot: 0.04 });
    }
    ctx.restore();
  });
  return K;
}
