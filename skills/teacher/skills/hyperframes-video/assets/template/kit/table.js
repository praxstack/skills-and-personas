/* kit/table.js: a table / array rows for DP state and dry runs, filling one cell per beat.

   const TB = KIT.table({x: 1180, y: 520, cols: ['0', '1', '2', '3'], colTitle: 'city', rows: ['start', 'round 0'], cw: 104, rh: 74})
   TB.show(t)                         frame, column headers and row labels (rows stay hidden until rowIn)
   TB.rowIn(r, t)                     row r's empty cells appear
   TB.set(r, c, '100', t, {tone, flash})   the value flips in; flash rings the cell
   rowGap: space between rows (default = gap); give arrows with labels between rows ~44 px
   TB.fill(r, ['0', '∞', '∞', '∞'], t, 0.12, {tone})   a whole row, staggered
   TB.mark(r, c, t, tone) / TB.strike(r, c, t)   outline a cell / cross it out
   TB.arrow([r1, c1], [r2, c2], t, tone, label, {bend})   curved arrow between two cells ("this value came from
                                      there"); two cells of one row get an arc under the row, bend = its depth
   TB.center(r, c) -> [x, y] on screen */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  K.table = function (o) {
    const cw = o.cw || 104, rh = o.rh || 74, gap = o.gap ?? 12, rg = o.rowGap ?? gap, lw = o.labelW ?? 170, hh = o.headH ?? 46, fs = o.fs || 34;
    const lfs = o.labelFs || tok.size.label; // column headers, the column title and row labels (30 px; 36 for short words without ascenders like "new", whose letters are only x-height tall)
    const x = o.x, y = o.y;
    const w = lw + o.cols.length * (cw + gap), h = hh + o.rows.length * (rh + rg);
    const box = K.el('div', 'tbl', o.parent || K.layer.hud, { left: x, top: y, width: w, height: h });
    const heads = o.cols.map((c, j) => K.el('div', 'ch lbl', box, { left: lw + j * (cw + gap), top: 0, width: cw, height: hh, lineHeight: hh + 'px', fontSize: lfs }, c));
    const title = o.colTitle ? K.el('div', 'lbl abs', box, { left: 0, top: 0, width: lw - 18, height: hh, lineHeight: hh + 'px', textAlign: 'right', fontSize: lfs, color: tok.color.mute }, o.colTitle) : null;
    const labels = [], cells = [];
    o.rows.forEach((r, i) => {
      labels.push(K.el('div', 'rl lbl', box, { left: 0, top: hh + i * (rh + rg), height: rh, lineHeight: rh + 'px', width: lw - 18, fontSize: lfs }, r));
      cells.push(o.cols.map((_, j) => {
        const e = K.el('div', 'cell', box, { left: lw + j * (cw + gap), top: hh + i * (rh + rg), width: cw, height: rh });
        const v = K.stack(e, { left: 0, top: 0, width: cw, height: rh }, 'v');
        v.el.style.fontSize = fs + 'px';
        return { e, v, i, j };
      }));
    });
    K.hidden([...heads, ...labels, ...cells.flat().map((c) => c.e)]);
    if (title) K.hidden(title);
    const TB = { el: box, cells, x, y, cw, rh, gap, lw, hh };
    TB.center = (r, c) => [x + lw + c * (cw + gap) + cw / 2, y + hh + r * (rh + rg) + rh / 2];
    TB.show = (t) => {
      tl.fromTo(title ? [title, ...heads] : heads, { opacity: 0, y: -10 }, { opacity: 1, y: 0, stagger: 0.05, duration: 0.35, ease: 'power2.out', immediateRender: false }, t);
    };
    TB.rowIn = (r, t, stagger = 0.05) => {
      K.show(labels[r], t, 0.4, { x: -20 });
      tl.fromTo(cells[r].map((c) => c.e), { opacity: 0, scale: 0.8 }, { opacity: 1, scale: 1, stagger, duration: 0.35, ease: 'back.out(2)', immediateRender: false }, t);
    };
    TB.set = (r, c, val, t, f = {}) => {
      const cell = cells[r][c];
      cell.v.to(t, val, { color: K.ink(f.tone || 'ink'), d: f.d ?? 0.4, mode: f.mode || 'flip' });
      if (f.flash !== false) {
        const col = K.tone(f.tone || 'accent');
        tl.fromTo(cell.e, { boxShadow: `0 0 0 0px ${col}00` }, { boxShadow: `0 0 0 6px ${col}88`, duration: 0.18, ease: 'power2.out', immediateRender: false }, t);
        tl.to(cell.e, { boxShadow: `0 0 0 0px ${col}00`, duration: 0.6, ease: 'power2.in' }, t + 0.2);
      }
    };
    TB.fill = (r, vals, t, stagger = 0.1, f = {}) => vals.forEach((v, c) => TB.set(r, c, v, t + c * stagger, Object.assign({ flash: false }, f)));
    TB.mark = (r, c, t, tone = 'good', d = 0.3) => {
      const col = K.tone(tone);
      tl.to(cells[r][c].e, { borderColor: col, backgroundColor: K.tint(col, 0x22 / 255), duration: d }, t);
    };
    TB.strike = (r, c, t, tone = 'bad') => {
      const cell = cells[r][c];
      const s = K.el('div', 'abs', cell.e, { left: 10, right: 10, top: rh / 2 - 2, height: 4, borderRadius: 2, background: K.tone(tone) });
      gsap.set(s, { scaleX: 0, transformOrigin: '0 50%', rotation: -18 });
      tl.to(s, { scaleX: 1, duration: 0.3, ease: 'power2.out' }, t);
      K.shake(cell.e, t, 6, 0.35);
    };
    TB.arrow = (a, b, t, tone = 'good', label, f = {}) => {
      let [x1, y1] = TB.center(...a), [x2, y2] = TB.center(...b);
      let sy1, sy2, cx, cy;
      if (Math.abs(y2 - y1) < 1) {
        // along one row: leave the bottom of one cell, dip under the row, come up into the other (a path between
        // the cells' centres would run behind the cells and not be seen). f.bend = how far the curve dips (60)
        const dx = Math.sign(x2 - x1) * Math.min(22, cw / 4);
        x1 += dx; x2 -= dx;
        sy1 = sy2 = y1 + rh / 2 + 4;
        cx = (x1 + x2) / 2; cy = sy1 + Math.abs(f.bend ?? 60) * 2;
      } else {
        sy1 = y1 + (y2 > y1 ? rh / 2 - 4 : -rh / 2 + 4); sy2 = y2 + (y2 > y1 ? -rh / 2 - 2 : rh / 2 + 2);
        const bend = f.bend ?? (Math.abs(x2 - x1) < 10 ? 60 : 0);
        cx = (x1 + x2) / 2 + bend; cy = (sy1 + sy2) / 2;
      }
      const col = K.tone(tone), svg = K.layer.hudsvg;
      const d = `M${x1},${sy1} Q${cx},${cy} ${x2},${sy2}`;
      const p = K.svg('path', { d, stroke: col, 'stroke-width': 4, fill: 'none', 'stroke-linecap': 'round' }, svg);
      const ang = (Math.atan2(sy2 - cy, x2 - cx) * 180) / Math.PI;
      const head = K.svg('path', { d: 'M2,0 L-14,-8 L-14,8 Z', fill: col, transform: `translate(${x2},${sy2}) rotate(${ang})` }, svg);
      K.drawable(p); K.hidden(head);
      K.draw(p, t, 0.45, 'power2.inOut');
      tl.to(head, { opacity: 1, duration: 0.15 }, t + 0.4);
      let lab = null;
      if (label) {
        lab = K.el('div', 'chip mono', K.layer.hud, { left: cx + (f.labelDx ?? 16), top: cy + (f.labelDy ?? 0), fontSize: tok.size.chip, color: K.ink(tone), borderColor: col, padding: '4px 14px' }, label);
        gsap.set(lab, { yPercent: -50 });
        K.hidden(lab); K.pop(lab, t + 0.25, 0.4, 0.5);
      }
      return { p, head, lab, out: (tt) => K.hide([p, head, ...(lab ? [lab] : [])], tt, 0.3) };
    };
    TB.out = (t) => K.hide(box, t, 0.4, { y: 30 });
    return TB;
  };
})();
