// kit/parts.js: the film's furniture. Captions, chapter labels, title card, question card with a countdown,
// comic callouts, stamps, and hand annotations (written labels, arrows, pen circles, strikes, flying chips).
// Each call registers itself in a layer and draws itself at any t; nothing needs to be "updated".
// Positions may be [x, y] or a function t => [x, y] (to follow something that moves, like a graph node).
'use strict';
const at2 = (p, t) => (typeof p === 'function' ? p(t) : p);

// ------------------------------------------------------------------ caption band (bottom 180 px, automatic)
// Shows the current line's `cap`, wrapped to two lines. The band stays up across consecutive lines and only
// the text cross-fades; it leaves during chapter gaps.
function captionBand(o = {}) {
  const size = o.size || S.size.caption, maxW = o.maxW || 1560, lines = TIMING_.lines;
  const runs = []; // contiguous stretches of lines
  for (const l of lines) { const r = runs[runs.length - 1]; if (r && l.start - r.end < 0.1) r.end = l.end; else runs.push({ start: l.start, end: l.end }); }
  const layout = (cap) => cached(`cap:${size}:${cap}`, () => {
    let sz = size, ls = wrapText(cap, 'hand', sz, maxW);
    while (ls.length > 2 && sz > 32) { sz -= 2; ls = wrapText(cap, 'hand', sz, maxW); }
    return { ls, sz, w: Math.max(...ls.map((s) => measureText(s, 'hand', sz))) };
  });
  screen(o.z ?? 90, (ctx, t) => {
    const run = runs.find((r) => t >= r.start - 0.3 && t < r.end + 0.3); if (!run) return;
    const band = env(t, run.start - 0.05, run.end - 0.2, 0.3, 0.25); if (band <= 0) return;
    const l = lineAt(t) || lines.filter((x) => x.start <= t).pop() || lines[0];
    const i = lines.indexOf(l), nx = lines[i + 1];
    const A = layout(l.cap);
    let w = A.w; // ease the strip width towards the next line's width during the hand-over
    if (nx && nx.start - l.end < 0.1) w = lerp(A.w, layout(nx.cap).w, P(t, l.end - 0.12, 0.25));
    const nL = A.ls.length, bh = nL * A.sz * 1.18 + 30, bw = Math.ceil((w + 100) / 40) * 40, cy = H - 92 + (1 - band) * 40;
    ctx.save(); ctx.globalAlpha *= band;
    if (S.kind === 'paper') drawCard(ctx, W / 2 - bw / 2, cy - bh / 2, bw, Math.round(bh / 10) * 10, { kind: 'label', tape: 0, seed: 991 + bw, res: 1 });
    else { ctx.fillStyle = S.capBand; pathPts(ctx, rrPts(W / 2 - bw / 2, cy - bh / 2, bw, bh, 14)); ctx.fill(); }
    const ta = Math.min(P(t, l.start, 0.2, Ease.out), 1 - P(t, l.end - 0.12, 0.12, Ease.in) * (nx ? 1 : 0));
    const ink = S.kind === 'paper' ? S.cardInk : S.ink;
    A.ls.forEach((s, k) => drawText(ctx, s, W / 2, cy - (nL - 1) * A.sz * 0.59 + k * A.sz * 1.18 + A.sz * 0.3 + (1 - ta) * 8, { size: A.sz, color: ink, align: 'center', alpha: ta }));
    ctx.restore();
  });
}

// ------------------------------------------------------------------ chapter labels (automatic, screen)
// Each chapter: a torn-paper label ("01 · The problem") lives only in the top-left corner the layout keeps free
// for it (x 96..~640, y 100..184). In the chapter gap the previous label slides off to the left (0.8-0.5 s before
// the start), the new one pops into the same spot and is written on, finishing as the chapter starts: before
// its caption, its first word and its first content. It then stays as the lower third. It never covers the
// subject or a board. (An earlier version popped it big at the centre first, over content already on screen.)
function chapterLabels(o = {}) {
  if (STYLE.chapterLabels) return STYLE.chapterLabels(o);
  const skip = new Set(o.skip ?? [0]), chs = TIMING_.chapters.filter((c) => !skip.has(c.n));
  const lab = (c) => `${String(c.n).padStart(2, '0')}  ·  ${c.name}`;
  screen(o.z ?? 95, (ctx, t) => {
    chs.forEach((c, j) => {
      const tIn = c.start - 0.5;
      const nxt = chs[j + 1], tOut = nxt ? nxt.start - 0.8 : TIMING_.total + 1; // leaves as its chapter ends
      if (t < tIn || t > tOut + 0.3) return;
      const txt = lab(c), size = S.size.chapter, tw = measureText(txt, 'brush', size), w = Math.ceil((tw + 170) / 20) * 20, h = 150;
      const p = pop(t, tIn, 0.5);
      // corner size: Caveat Brush lower case is short, so the corner label keeps the words near 50 px (measured ~30)
      const cs = S.size.chapterCorner ?? 0.56, cx = 96 + (w * cs) / 2, cy = 100 + (h * cs) / 2;
      const off = P(t, tOut, 0.3, Ease.in); // slides off to the left, out of the frame, over nothing
      // a short dim of the world across the gap marks the chapter change
      const dim = env(t, c.start - 0.8, c.start + 0.2, 0.3, 0.4) * 0.18;
      if (dim > 0) { ctx.fillStyle = hexA(S.shade, dim * S.shadeK); ctx.fillRect(0, 0, W, H); } // shade toward the theme's deep
      ctx.save(); ctx.translate(cx - off * (w * cs + 140), cy); ctx.rotate(-0.006 - off * 0.08 + (p.rot || 0)); ctx.scale(cs * p.sx, cs * p.sy);
      drawCard(ctx, -w / 2, -h / 2, w, h, { kind: 'label', tape: 1, seed: 300 + c.n });
      const col = S.node[c.n % S.node.length], ink = S.kind === 'paper' ? S.cardInk : S.ink;
      blit(ctx, discSprite(String(c.n), col, S.nodeInk[c.n % S.node.length], 46), -w / 2 + 82, 0, { t, jit: 'chap' + c.n });
      drawText(ctx, c.name, -w / 2 + 150, 0, { font: 'brush', size, color: ink, base: 'middle', write: P(t, tIn + 0.05, 0.45, Ease.inOut), t, boil: 0.8 });
      ctx.restore();
    });
  });
}

// a paper disc with a hand-lettered label (node badges, chapter numbers, Q1 badges)
function discSprite(label, color, ink, r = 44, font = 'brush') {
  return cached(`disc:${S.name}:${label}:${color}:${r}:${font}`, () => sprite(r * 2 + 60, r * 2 + 60, r + 30, r + 30, (g) => {
    if (STYLE.disc) return STYLE.disc(g, label, color, ink, r, font);
    cutout(g, ellipsePts(0, 0, r, r, 44), color, { seed: hashStr(label + color), edge: 4.5, shadow: 9 });
    if (S.kind === 'paper') { g.strokeStyle = S.sheen; g.lineWidth = 2; g.beginPath(); g.arc(0, 0, r * 0.8, -2.6, -1.2); g.stroke(); }
    drawText(g, label, 0, 0, { font, size: r * (label.length > 2 ? 0.8 : 1.15), color: S.kind === 'paper' ? ink : color, align: 'center', base: 'middle' });
  }, 2.5));
}

// ------------------------------------------------------------------ title card (world)
function titleCard(o) {
  const at = o.at ?? 0, until = o.until, lines = o.lines || wrapText(o.title, 'brush', S.size.title, 1250);
  const size = S.size.title, w = 1400, h = 150 + lines.length * size * 1.0 + (o.kicker ? 40 : 0);
  const x = o.x ?? W / 2, y = o.y ?? H * 0.43;
  world(o.z ?? 40, (ctx, t) => {
    if (t < at || t > until + 0.6) return;
    const p = pop(t, at, 0.7), off = P(t, until, 0.5, Ease.in);
    ctx.save(); ctx.translate(x, y - off * 700); ctx.rotate(-0.02 - off * 0.25 + (p.rot || 0)); ctx.scale(p.sx, p.sy);
    drawCard(ctx, -w / 2, -h / 2, w, h, { kind: 'label', tape: 2, seed: 4242 });
    const ink = S.kind === 'paper' ? S.cardInk : S.ink;
    if (o.kicker) drawText(ctx, o.kicker, -w / 2 + 90, -h / 2 + 80, { size: S.size.label, color: S.accent, write: P(t, at + 0.1, 0.5) });
    const wr = (k) => P(t, at + 0.25 + k * 0.55, 0.9, Ease.inOut);
    lines.forEach((s, k) => drawText(ctx, s, 0, -h / 2 + (o.kicker ? 110 : 70) + (k + 0.78) * size * 0.98, { font: 'brush', size, color: k ? S.accent : ink, align: 'center', write: wr(k), t, boil: 1 }));
    ctx.restore();
    if (o.stamp) stampAt(ctx, t, o.stamp, x + w / 2 - 210, y + h / 2 - 10, o.stampAt ?? at + 1.3, { size: 40, color: S.accent, rot: -0.08, until: until });
  });
}

// ------------------------------------------------------------------ question card with a countdown ring (screen)
// q: line id of the question (its `think` drives the ring), a: line id of the answer (written under it).
function questionCard(q, a, o = {}) {
  const Lq = L[q], La = a ? L[a] : null;
  const qText = o.q ?? Lq.cap.replace(/^question\s*\d*\s*[:.]\s*/i, ''), aText = o.a ?? (La ? La.cap : '');
  const n = o.n ?? 1, cw = o.w ?? 1330, x = o.x ?? 470, y = o.y ?? 92, sz = 46; // x clears the chapter label (top-left)
  const qLines = wrapText(qText, 'hand', sz, cw - 400), aLines = aText ? wrapText(aText, 'hand', sz - 2, cw - 400) : [];
  const ch = 70 + qLines.length * sz * 1.22 + (aLines.length ? aLines.length * sz * 1.2 + 14 : 0) + 20;
  const tIn = o.at ?? Lq.start, tOut = o.until ?? (La ? La.end - 0.3 : Lq.end - 0.3);
  const thinkA = vEnd(q), thinkD = Lq.think || 0;
  screen(o.z ?? 80, (ctx, t) => {
    if (t < tIn || t > tOut + 0.4) return;
    const k = P(t, tIn, 0.5, Ease.back), off = P(t, tOut, 0.3, Ease.in);
    const yy = y - (1 - k) * (ch + 140) - off * (ch + 160);
    ctx.save(); ctx.translate(0, yy);
    drawCard(ctx, x, 0, cw, Math.round(ch / 10) * 10, { kind: 'note', tape: 2, seed: 500 + n, first: 64, rule: Math.round(sz * 1.22), marginX: 120 });
    const ink = S.kind === 'paper' ? S.cardInk : S.ink;
    blit(ctx, discSprite('Q' + n, S.accent, S.inkOn(S.accent), 38), x + 62, 58, { t, jit: 'q' + n });
    // written in the first half of the spoken words, so the text has landed while it is still being said
    drawLines(ctx, qLines, x + 150, 62 + sz * 0.3, { size: sz, color: ink, lh: sz * 1.22, write: P(t, vAt(q), Math.min(1.4, Lq.voiceDur * 0.55), Ease.lin), t, seed: 'q' + n });
    if (aLines.length) drawLines(ctx, aLines, x + 150, 62 + sz * 0.3 + qLines.length * sz * 1.22 + 10, { size: sz - 2, color: S.cool, lh: sz * 1.2, write: P(t, vAt(a), Math.min(1.1, La.voiceDur * 0.5), Ease.lin), t, seed: 'a' + n });
    // the countdown ring
    const rx = x + cw - 120, ry = Math.min(ch / 2, 110), r = 46;
    inkEllipse(ctx, rx, ry, r, r, { color: S.inkFaint, w: 3, seed: 'ring' + n, t, prog: P(t, tIn + 0.2, 0.5), turns: 1.02 });
    if (thinkD > 0 && t >= thinkA) {
      const u = clamp((t - thinkA) / thinkD), left = Math.max(0, thinkD - (t - thinkA));
      if (u < 1) {
        const pts = []; for (let i = 0; i <= 48; i++) { const ang = -Math.PI / 2 + (i / 48) * TAU * (1 - u); pts.push([rx + Math.cos(ang) * r, ry + Math.sin(ang) * r]); }
        inkLine(ctx, pts, { color: S.accent, w: 7, seed: 'cd' + n, t, ends: false, amp: 0.6 });
        const pp = pop(t, thinkA + Math.floor(t - thinkA), 0.35);
        ctx.save(); ctx.translate(rx, ry); ctx.scale(0.7 + 0.3 * pp.sx, 0.7 + 0.3 * pp.sy);
        drawText(ctx, String(Math.ceil(left - 1e-6)), 0, 0, { font: 'brush', size: 50, color: S.accent, align: 'center', base: 'middle' }); ctx.restore();
        drawText(ctx, 'think', rx, ry + r + 38, { size: S.size.small, color: S.inkSoft, align: 'center' });
      }
    }
    if (t < thinkA || thinkD === 0) drawText(ctx, '?', rx, ry, { font: 'brush', size: 56, color: S.inkSoft, align: 'center', base: 'middle', alpha: P(t, tIn + 0.4, 0.3), t, boil: 1 });
    else if (t >= thinkA + thinkD && La) { const pp = pop(t, Math.max(thinkA + thinkD, vAt(a)), 0.5); ctx.save(); ctx.translate(rx, ry); ctx.scale(pp.sx, pp.sy); drawText(ctx, '✓', 0, 0, { font: 'brush', size: 64, color: S.good, align: 'center', base: 'middle' }); ctx.restore(); }
    ctx.restore();
  });
}

// ------------------------------------------------------------------ comic callout burst ("700!", "POP!")
function burstSprite(text, size, colors) {
  return cached(`burst:${S.name}:${text}:${size}`, () => {
    const tw = measureText(text, 'brush', size), R = Math.max(tw * 0.62 + 40, size * 1.1), n = 14;
    return sprite(R * 2.6 + 60, R * 2.0 + 60, R * 1.3 + 30, R + 30, (g) => {
      const star = (rOut, rIn, seed) => { const r = mulberry32(seed), p = []; for (let i = 0; i < n * 2; i++) { const a = (i / (n * 2)) * TAU, rr = i % 2 ? rIn * (0.9 + r() * 0.2) : rOut * (0.85 + r() * 0.3); p.push([Math.cos(a) * rr * 1.25, Math.sin(a) * rr * 0.85]); } return p; };
      cutout(g, star(R, R * 0.7, hashStr(text)), colors[0], { seed: hashStr(text), edge: 5, shadow: 14 });
      cutout(g, star(R * 0.78, R * 0.58, hashStr(text) + 1), colors[1], { seed: hashStr(text) + 2, edge: 0, shadow: 0, hatch: false });
      drawText(g, text, 0, 0, { font: 'brush', size, color: S.kind === 'paper' ? S.inkOn(colors[1], S.ink) : colors[1], align: 'center', base: 'middle', halo: S.kind === 'paper' ? S.burstHalo : null, haloW: 9 });
    }, 2);
  });
}
function callout(text, pos, o = {}) {
  const at = o.at, until = o.until ?? at + 1.6, size = o.size || 74, rot = o.rot ?? -0.12;
  (o.space === 'screen' ? screen : world)(o.z ?? 70, (ctx, t) => {
    if (t < at || t > until + 0.3) return;
    const [x, y] = at2(pos, t), e = popEnv(t, at, until, 0.5, 0.2);
    // action lines on impact
    const u = (t - at) / 0.4;
    if (u > 0 && u < 1) for (let k = 0; k < 12; k++) {
      const a = (k / 12) * TAU + 0.2, r0 = size * (1.3 + Ease.out(u) * 0.9), r1 = r0 + size * 0.5 * (1 - u);
      inkSeg(ctx, x + Math.cos(a) * r0 * 1.2, y + Math.sin(a) * r0 * 0.8, x + Math.cos(a) * r1 * 1.2, y + Math.sin(a) * r1 * 0.8, { color: S.burst[0], w: 4, alpha: 1 - u, seed: k, passes: 1 });
    }
    blit(ctx, burstSprite(text, size, o.colors || S.burst), x, y, { sx: e.sx, sy: e.sy, rot: rot + Math.sin(t * 2.2) * 0.02 + (e.rot || 0), t, jit: 'b' + text });
  });
}

// ------------------------------------------------------------------ rubber stamp (slams in)
function stampAt(ctx, t, text, x, y, t0, o = {}) {
  if (t < t0 || (o.until != null && t > o.until + 0.3)) return;
  const u = clamp((t - t0) / 0.2), s = lerp(1.9, 1, Ease.out(u)) * (o.s || 1), a = u * (o.until != null ? 1 - P(t, o.until, 0.25) : 1);
  blit(ctx, stampSprite(text, o.color || S.bad, o.size || 44), x, y, { s, rot: o.rot ?? -0.12, alpha: a * 0.94 });
}
function stamp(text, pos, o = {}) {
  (o.space === 'screen' ? screen : world)(o.z ?? 72, (ctx, t) => { const [x, y] = at2(pos, t); stampAt(ctx, t, text, x, y, o.at, o); });
  if (o.shake) shake(o.at + 0.18, o.shake, 0.3);
}

// ------------------------------------------------------------------ hand annotations
// written label: o = {at, until, dur (write time), font, size, color, align, rot, halo, boil, space, z, base}
function label(text, pos, o = {}) {
  const at = o.at ?? 0, until = o.until ?? Infinity, dur = o.dur ?? Math.min(1.2, 0.25 + text.length * 0.045);
  (o.space === 'screen' ? screen : world)(o.z ?? 60, (ctx, t) => {
    if (t < at || t > until + 0.3) return;
    const [x, y] = at2(pos, t), a = 1 - P(t, until, 0.25, Ease.in);
    ctx.save(); ctx.translate(x, y); if (o.rot) ctx.rotate(o.rot);
    const tw = drawText(ctx, val(o.text ?? text, t), 0, 0, { font: o.font || 'hand', size: o.size || S.size.label, color: o.color || S.ink, align: o.align || 'center', base: o.base, write: P(t, at, dur, Ease.lin), alpha: a, t, boil: o.boil ?? 0.5, halo: o.halo, haloW: o.haloW, seed: text });
    if (o.strikeAt != null && t >= o.strikeAt) { // a pen line through the label (a rejected value)
      const sz = o.size || S.size.label, x0 = o.align === 'left' ? 0 : o.align === 'right' ? -tw : -tw / 2;
      inkLine(ctx, [[x0 - 10, -sz * 0.28 + 4], [x0 + tw + 10, -sz * 0.34]], { color: o.strikeColor || textInk(S.bad), w: 5, prog: P(t, o.strikeAt, 0.25, Ease.out), alpha: a, seed: 'lst' + text, t });
    }
    ctx.restore();
  });
}
// hand-drawn arrow: pts = [from, to] (bent by o.bend) or a longer polyline; o = {at, dur, until, color, w, head}
function arrow(pts, o = {}) {
  const at = o.at ?? 0, dur = o.dur ?? 0.5, until = o.until ?? Infinity;
  (o.space === 'screen' ? screen : world)(o.z ?? 62, (ctx, t) => {
    if (t < at || t > until + 0.3) return;
    let p = val(pts, t).map((q) => at2(q, t));
    if (p.length === 2) { const [a, b] = p, mx = (a[0] + b[0]) / 2, my = (a[1] + b[1]) / 2, dx = b[0] - a[0], dy = b[1] - a[1], k = o.bend ?? 0.2; p = quadPts(a, [mx - dy * k, my + dx * k], b, 24); }
    inkArrow(ctx, p, { color: o.color || S.ink, w: o.w ?? 4, prog: P(t, at, dur, Ease.inOut), alpha: 1 - P(t, until, 0.25), seed: o.seed ?? 'arr' + at, t, tip: true, head: o.head ?? 18 });
  });
}
function circle(pos, rx, ry, o = {}) {
  const at = o.at ?? 0, dur = o.dur ?? 0.5, until = o.until ?? Infinity;
  (o.space === 'screen' ? screen : world)(o.z ?? 62, (ctx, t) => {
    if (t < at || t > until + 0.3) return;
    const [x, y] = at2(pos, t);
    inkEllipse(ctx, x, y, rx, ry, { color: o.color || S.accent, w: o.w ?? 5, prog: P(t, at, dur, Ease.inOut), alpha: 1 - P(t, until, 0.25), seed: o.seed ?? 'c' + at, t, tip: true });
  });
}
function strike(p1, p2, o = {}) {
  const at = o.at ?? 0, dur = o.dur ?? 0.25, until = o.until ?? Infinity;
  (o.space === 'screen' ? screen : world)(o.z ?? 66, (ctx, t) => {
    if (t < at || t > until + 0.3) return;
    inkLine(ctx, [at2(p1, t), at2(p2, t)], { color: o.color || S.bad, w: o.w ?? 6, prog: P(t, at, dur, Ease.out), alpha: 1 - P(t, until, 0.25), seed: 'st' + at, t });
  });
}
// a small paper chip that flies from one place to another on an arc (values travelling from text to picture)
function chip(text, from, to, o = {}) {
  const at = o.at, dur = o.dur ?? 0.8, until = o.until ?? at + dur + 0.05, size = o.size || S.size.chip;
  (o.space === 'screen' ? screen : world)(o.z ?? 75, (ctx, t) => {
    if (t < at || t > until) return;
    const u = Ease.inOut(clamp((t - at) / dur)), a = at2(from, t), b = at2(to, t);
    const x = lerp(a[0], b[0], u), y = lerp(a[1], b[1], u) + (o.arc ?? -140) * Math.sin(Math.PI * u);
    const s = (o.s0 ?? 1) + ((o.s1 ?? 0.85) - (o.s0 ?? 1)) * u, rot = Math.sin(u * Math.PI) * (o.spin ?? -0.25);
    // the chip pops off its tag; a registry theme pops from 0.92, not 0.6, so its label never drops under 26 px
    const pop = S.theme ? 0.92 : 0.6;
    blit(ctx, tagSprite(text, { size, color: o.color }), x, y, { s: s * (pop + (1 - pop) * Math.min(1, u * 5)), rot, alpha: 1 - P(t, until - 0.08, 0.08) });
  });
}

// ------------------------------------------------------------------ scenery (paper style only): depth for free
// Two torn-paper hill layers along the bottom and a few paper clouds, each moving with the camera at its own
// depth (parallax). They sit behind everything; the caption band covers the middle of the hills.
function scenery(o = {}) {
  if (S.kind !== 'paper' || o.off) return;
  const hill = (seed, color, base, amp, wl) => cached(`hill:${seed}`, () => {
    const w = W + 900, pts = [];
    for (let x = 0; x <= w; x += 30) pts.push([x, base - amp * (0.55 + 0.45 * Math.sin(x / wl + seed)) * (0.6 + 0.4 * Math.sin(x / (wl * 2.7) + seed * 2)) - 40 * Math.exp(-(((x - 450 - W / 2) / 520) ** 2)) * -1]);
    pts.push([w, 330], [0, 330]);
    return sprite(w, 340, 0, 0, (g) => cutout(g, pts, color, { seed, edge: 4, shadow: 14, tex: 1 }), 1);
  });
  const layers = o.hills || [[0.42, 11, S.hills[0], 170, 110, 260], [0.68, 12, S.hills[1], 215, 80, 190]];
  for (const [depth, seed, color, base, amp, wl] of layers) back(depth, 1 + depth, (ctx) => blit(ctx, hill(seed, color, base, amp, wl), -450, H - 330 + (1 - depth) * 40));
  const cloud = (seed, w) => cached(`cloud:${seed}`, () => {
    const r = mulberry32(seed), pts = [];
    for (let i = 0; i <= 5; i++) { const cx = -w / 2 + (i / 5) * w, cr = w * (0.12 + r() * 0.08); for (let a = Math.PI; a <= Math.PI * 2.001; a += Math.PI / 10) pts.push([cx + Math.cos(a) * cr, -4 + Math.sin(a) * cr * (0.9 + r() * 0.4)]); }
    pts.push([w / 2 + 10, 8], [-w / 2 - 10, 8]);
    return sprite(w + 120, w * 0.6, w / 2 + 60, w * 0.42, (g) => cutout(g, pts, S.cloud, { seed, edge: 3, shadow: 12, tex: 0.8 }), 1);
  });
  const clouds = o.clouds || [[0.3, 61, 260, 1500, 70, 6], [0.5, 62, 200, 760, 40, 4], [0.38, 63, 230, 1850, 230, 5]];
  for (const [depth, seed, w, x0, y, v] of clouds) back(depth, 3 + depth, (ctx, t) => { const x = ((x0 + t * v + 300) % (W + 700)) - 300; blit(ctx, cloud(seed, w), x, y, { alpha: 0.95 }); });
}
