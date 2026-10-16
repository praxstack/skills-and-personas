// kit/array.js: an ARRAY + STACK subject for array problems (next greater element, monotonic stack, two
// pointers, prefix sums...), in the kit's style (WORLD space, moves with the camera). First built for LC 739
// (Daily Temperatures) by a test run of this skill, then generalised. Same rules as the kit: every change is a
// tween on K.tl at a line time; components that change one property many times collect events and emit them
// in time order at K.finalize() with durations clamped, so no two tweens fight (gsap_check stays clean).
//
//   const R = K.barRow({ x0, stride, base, values, lo, hi, titles: {index: 'index', answer: 'answer'}, unit: '' })
//             value bars (height and heat colour follow the value) + index row + answer row.
//   const R = K.tempRow({...})  the same row drawn as thermometers (look 'thermo', titles day/answer, unit °).
//   R.showTubes(t) R.fill(i, t, v, {lo, hi}) R.setAll(t, values, {lo, hi}) R.showIdx(t) R.showCells(t)
//   R.answer(i, v, t, {color}) R.clearAnswers(t, ids, v) R.flash(i, t, color) R.idxColor(i, t, color)
//   R.arc(j, i, t, {color, label}) R.clearArcs(t) R.tag(i, text, t, {color, until}) R.marker(color, text)
//   R.labelPt(i) R.cellPt(i) R.rect(i0, i1, {top, bottom})
//   const S = K.stackCol({ x, w, bottom, top, R, title, colorOf, chipText: (i, v) => [`i ${i}`, `${v}`] })
//             a glass tube; each chip is one index (left text) and its value (right text).
//   S.show(t) S.push(i, v, t) S.pop(t, i, {value, write}) -> {j, land} S.flashTop(t, color) S.clear(t) S.rect()
//             pop flies the chip to answer cell j and writes value there (default i - j, the distance;
//             value: v for "next greater value"; write: false to write nothing).
//   const ch = K.channel(el); ch.to(t, vars, d); ch.set(t, vars)   many updates of one property set (fast
//             counters, colours) emitted in time order and trimmed so they never overlap.
(function () {
  const K = window.K;
  const f1 = (v) => (+v).toFixed(1);
  const rgb = (c) => { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const mix = (a, b, f) => '#' + rgb(a).map((x, i) => Math.round(x + (rgb(b)[i] - x) * f).toString(16).padStart(2, '0')).join('');
  /** cold (cyan) -> mild (cream) -> warm (amber) -> hot (accent); a cream midpoint avoids the muddy cyan/amber mix */
  const HEAT = () => [[0, K.C.cyan], [0.4, K.U.heatMid], [0.65, K.C.amber], [1, K.C.accent]];
  K.heat = (f) => { f = K.clamp(f); const S = HEAT(); let k = 1; while (k < S.length - 1 && f > S[k][0]) k++; return mix(S[k - 1][1], S[k][1], (f - S[k - 1][0]) / (S[k][0] - S[k - 1][0])); };

  // ------------------------------------------------------------------ channel: many changes, one property set
  /** K.channel(el): .to(t, vars, d, ease) / .set(t, vars). Emitted sorted at finalize; a tween is cut short
   *  where the next one starts (and dropped if the next starts at the same moment), so they never overlap. */
  K.channel = function (el) {
    const ev = [];
    K.onFinalize(() => {
      ev.sort((a, b) => a.t - b.t);
      ev.forEach((e, k) => {
        const nx = ev[k + 1];
        if (e.d === 0) { if (!(nx && nx.t <= e.t + 1e-6 && nx.d === 0)) K.set(el, e.vars, e.t); return; }
        let d = e.d;
        if (nx) d = Math.min(d, nx.t - e.t - 0.004);
        if (d < 0.03) { if (nx && nx.t - e.t < 0.01) return; d = Math.max(d, 0.004); }
        K.to(el, { ...e.vars, duration: d, ease: e.ease || 'power2.out' }, e.t);
      });
    });
    return { to: (t, vars, d = 0.3, ease) => { ev.push({ t, vars, d, ease }); return t + d; }, set: (t, vars) => ev.push({ t, vars, d: 0 }) };
  };

  // ------------------------------------------------------------------ the row of thermometers
  K.tempRow = (o) => K.barRow({ look: 'thermo', titles: { index: 'day', answer: 'answer' }, unit: '°', ...o });
  K.barRow = function (o) {
    const look = o.look ?? 'bars', thermo = look === 'thermo';
    const titles = { index: 'index', answer: 'answer', ...(o.titles || {}) };   // row titles render uppercase
    const x0 = o.x0 ?? 330, st = o.stride ?? 130, base = o.base ?? 680;
    const hMin = o.hMin ?? 60, hMax = o.hMax ?? 300;
    const tubeTop = base - hMax - 18, labY = tubeTop - 18, idxY = base + 96, cellY = base + 114;
    const cw = o.cw ?? 96, ch = o.ch ?? 66, arcY = o.arcY ?? 250;
    const N = o.values.length;
    const R = { N, look, unit: o.unit ?? '', base, labY, idxY, cellY, cw, ch, arcY, tubeTop, x: (i) => x0 + i * st, bars: [], arcs: [], tags: [] };
    const gBack = K.svg('g', { 'data-k': 'row back' }, K.layer.panels);
    const gBars = K.svg('g', { 'data-k': 'row bars' }, K.layer.nodes);
    const gLab = K.svg('g', { 'data-k': 'row labels' }, K.layer.labels);
    const gArc = K.svg('g', { 'data-k': 'row arcs' }, K.layer.trails);
    R.fxLayer = K.svg('g', {}, K.layer.fx);
    let scale = { lo: o.lo ?? 66, hi: o.hi ?? 76 };
    const hOf = (v, s = scale) => hMin + K.clamp((v - s.lo) / (s.hi - s.lo)) * (hMax - hMin);
    const cOf = (v, s = scale) => K.heat((v - s.lo) / (s.hi - s.lo));

    // row titles
    const tDay = K.svg('text', { x: x0 - 68, y: idxY, 'text-anchor': 'end', class: 'row-title' }, gLab); tDay.textContent = titles.index;
    const tAns = K.svg('text', { x: x0 - 68, y: cellY + ch / 2 + 10, 'text-anchor': 'end', class: 'row-title' }, gLab); tAns.textContent = titles.answer;
    K.init([tDay, tAns], { autoAlpha: 0 });
    R.titles = { day: tDay, index: tDay, answer: tAns };

    for (let i = 0; i < N; i++) {
      const x = R.x(i);
      const g = K.svg('g', { 'data-k': `bar ${i}` }, gBars);
      K.svg('ellipse', { cx: x, cy: base + 52, rx: 56, ry: 14, fill: 'url(#shadow)' }, g);
      let merc, bulb;
      if (thermo) {
        K.svg('rect', { x: x - 23, y: tubeTop, width: 46, height: base - tubeTop + 4, rx: 23, class: 'tube' }, g);
        for (let k = 1; k <= 4; k++) K.svg('line', { x1: x + 12, x2: x + 20, y1: base - k * (hMax / 5), y2: base - k * (hMax / 5), class: 'tick' }, g);
        merc = K.svg('rect', { x: x - 11, y: base, width: 22, height: 12, rx: 11, fill: K.C.cyan }, g);
        K.svg('circle', { cx: x, cy: base + 24, r: 31, class: 'bulb-glass' }, g);
        bulb = K.svg('circle', { cx: x, cy: base + 24, r: 22, fill: K.C.cyan }, g);
        K.svg('path', { d: `M${x - 13},${base + 14} A14,14 0 0 1 ${x - 2},${base + 9}`, class: 'shine' }, g);
        K.svg('rect', { x: x - 6, y: tubeTop + 10, width: 5, height: 70, rx: 2.5, class: 'shine-bar' }, g);
      } else {
        // a plain value bar in a faint track on a base plate; the plate takes the heat colour with the bar
        const bw = o.barW ?? Math.min(64, st * 0.5);
        K.svg('rect', { x: x - bw / 2 - 6, y: tubeTop, width: bw + 12, height: base - tubeTop + 6, rx: 14, class: 'tube' }, g);
        merc = K.svg('rect', { x: x - bw / 2, y: base, width: bw, height: 12, rx: 10, fill: K.C.cyan }, g);
        bulb = K.svg('rect', { x: x - bw / 2 - 6, y: base + 12, width: bw + 12, height: 8, rx: 4, fill: K.C.cyan }, g);
        K.svg('rect', { x: x - bw / 2 + 6, y: tubeTop + 12, width: 6, height: 70, rx: 3, class: 'shine-bar' }, g);
      }
      const lab = K.svg('text', { x, y: labY, 'text-anchor': 'middle', class: 'bar-label mono' }, gLab);
      lab.textContent = String(o.values[i]);
      const idx = K.svg('text', { x, y: idxY, 'text-anchor': 'middle', class: 'bar-idx mono' }, gLab);
      idx.textContent = String(i);
      const cell = K.svg('g', { 'data-k': `cell ${i}` }, gLab);
      const crect = K.svg('rect', { x: x - cw / 2, y: cellY, width: cw, height: ch, rx: 14, class: 'acell' }, cell);
      K.init(g, { autoAlpha: 0 });
      K.init([lab, idx], { autoAlpha: 0 });
      K.init(cell, { autoAlpha: 0, y: 14 });
      const b = { i, x, g, merc, bulb, lab, idx, cell, crect, v: o.values[i], shown: false, labShown: false, idxShown: false, cellShown: false, values: [] };
      b.vis = K.channel(g); b.geo = K.channel(merc); b.col = K.channel([merc, bulb]); b.txt = K.channel(lab);
      b.lcol = K.channel(lab); b.lvis = K.channel(lab); b.icol = K.channel(idx); b.ivis = K.channel(idx);
      b.cvis = K.channel(cell); b.cstroke = K.channel(crect);
      R.bars.push(b);
    }
    // channels on the same element but different properties: K.channel(el) per property group (tracked separately)
    const B = (i) => { const b = R.bars[i]; if (!b) throw new Error(`barRow has no bar ${i}`); return b; };
    R.bar = B;
    R.labelPt = (i) => [R.x(i), labY - 13];
    R.cellPt = (i) => [R.x(i), cellY + ch / 2];
    R.bulbPt = (i) => [R.x(i), thermo ? base + 24 : base + 16];
    /** World rect around bars i0..i1. top: 'arcs' | 'tags' | 'labels' | number; bottom: 'cells' | 'idx' */
    R.rect = (i0 = 0, i1 = N - 1, ro = {}) => {
      const top = ro.top === 'arcs' ? arcY - 36 - 22 * (ro.span ?? 4) - 26 : ro.top === 'tags' ? labY - 82 : ro.top === 'labels' ? labY - 44 : ro.top ?? labY - 82;
      const bottom = ro.bottom === 'idx' ? idxY + 16 : ro.bottom ?? cellY + ch + 8;
      const left = R.x(i0) - 66 - (i0 === 0 && ro.titles !== false ? 120 : 0), right = R.x(i1) + 66;
      return { x: left, y: top, w: right - left, h: bottom - top };
    };

    // tubes appear (empty)
    R.showTubes = (t, stagger = 0.06, ids = null) => {
      (ids || R.bars.map((b) => b.i)).forEach((i, k) => { const b = B(i); if (!b.shown) { b.vis.to(t + k * stagger, { autoAlpha: 1 }, 0.45); b.shown = true; } });
      return t + 0.45 + stagger * N;
    };
    R.hideBars = (t, ids) => ids.forEach((i) => { const b = B(i); if (b.shown) { b.vis.to(t, { autoAlpha: 0 }, 0.35); b.shown = false; } });
    /** Set bar i to value v: mercury rises/falls, colour follows, the label counts to v (and appears if hidden). */
    R.fill = (i, t, v, fo = {}) => {
      const b = B(i), s = fo.scale || scale, h = hOf(v, s), d = fo.d ?? 0.7;
      b.geo.to(t, { attr: { y: base - h, height: h + 12 } }, d, 'power3.out');
      b.col.to(t, { fill: cOf(v, s) }, d);
      if (!b.labShown) { b.lvis.to(t, { autoAlpha: 1 }, 0.3); b.labShown = true; b.txt.set(t, { textContent: String(v) }); }
      else if (b.v !== v) b.txt.to(t, { textContent: v, snap: { textContent: 1 } }, d * 0.9, 'power1.inOut');
      b.v = v;
      return t + d;
    };
    /** Morph the whole row to new values (bars past values.length fade out; returning bars fade in). */
    R.setAll = (t, values, so = {}) => {
      if (so.lo !== undefined) scale = { lo: so.lo, hi: so.hi };
      const stg = so.stagger ?? 0.05;
      R.bars.forEach((b, i) => {
        if (i < values.length) {
          if (!b.shown) { b.vis.to(t + i * stg, { autoAlpha: 1 }, 0.4); b.shown = true; }
          if (b.cellShown === false && so.cells) R.showCells(t, 0, [i]);
          R.fill(i, t + i * stg, values[i], { d: so.d ?? 0.8 });
          if (!b.idxShown && so.idx !== false) R.showIdx(t + i * stg, 0, [i]);
        } else {
          if (b.shown) { b.vis.to(t, { autoAlpha: 0 }, 0.35); b.shown = false; }
          if (b.labShown) { b.lvis.to(t, { autoAlpha: 0 }, 0.3); b.labShown = false; }
          if (b.idxShown) { b.ivis.to(t, { autoAlpha: 0 }, 0.3); b.idxShown = false; }
          if (b.cellShown) { b.cvis.to(t, { autoAlpha: 0, y: 14 }, 0.3); b.cellShown = false; }
        }
      });
      return t + stg * values.length + (so.d ?? 0.8);
    };
    R.showIdx = (t, stagger = 0.06, ids = null) => {
      (ids || R.bars.map((b) => b.i)).forEach((i, k) => { const b = B(i); if (!b.idxShown) { b.ivis.to(t + k * stagger, { autoAlpha: 1 }, 0.35); b.idxShown = true; } });
    };
    R.showCells = (t, stagger = 0.06, ids = null) => {
      (ids || R.bars.map((b) => b.i)).forEach((i, k) => { const b = B(i); if (!b.cellShown) { b.cvis.to(t + k * stagger, { autoAlpha: 1, y: 0 }, 0.4, 'back.out(1.6)'); b.cellShown = true; } });
    };
    /** Fade whole columns (bar, label, index, answer cell) to alpha a: hide what a panel would cover. */
    R.cols = (t, ids, a, d = 0.4) => ids.forEach((i) => {
      const b = B(i);
      b.vis.to(t, { autoAlpha: a }, d); b.cvis.to(t, { autoAlpha: a }, d);
      if (b.labShown) b.lvis.to(t, { autoAlpha: a }, d);
      if (b.idxShown) b.ivis.to(t, { autoAlpha: a }, d);
    });
    R.showTitle = (name, t) => K.to(R.titles[name], { autoAlpha: 1, duration: 0.4 }, t);
    R.hideTitle = (name, t) => K.to(R.titles[name], { autoAlpha: 0, duration: 0.3 }, t);
    /** Flash bar i's label in a colour, then back to ink. */
    R.flash = (i, t, color = 'accent', hold = 0.35) => {
      const b = B(i);
      b.lcol.to(t, { fill: K.ink(color) }, 0.12);
      b.lcol.to(t + hold, { fill: K.C.ink }, 0.35);
    };
    /** Tint the label (and keep it) until `until`. */
    R.tint = (i, t, color, until) => { const b = B(i); b.lcol.to(t, { fill: K.ink(color) }, 0.25); if (until !== undefined) b.lcol.to(until, { fill: K.C.ink }, 0.3); };
    R.idxColor = (i, t, color, until) => { const b = B(i); b.icol.to(t, { fill: K.ink(color) }, 0.25); if (until !== undefined) b.icol.to(until, { fill: K.C.dim }, 0.3); };
    R.cellFlash = (i, t, color = 'mint') => { const b = B(i); b.cstroke.to(t, { stroke: K.vis(color), strokeWidth: 4 }, 0.15); b.cstroke.to(t + 0.6, { stroke: K.U.acellLine, strokeWidth: 2 }, 0.5); };

    // answer cell values (events per cell, emitted in time order)
    R.answer = (i, v, t, ao = {}) => { B(i).values.push({ t, v: String(v), color: ao.color, flash: ao.flash ?? true }); return t + 0.35; };
    R.clearAnswers = (t, ids = null, v = '', stagger = 0.03) => (ids || R.bars.map((b) => b.i)).forEach((i, k) => R.answer(i, v, t + k * stagger, { flash: false }));
    K.onFinalize(() => {
      R.bars.forEach((b) => {
        b.values.sort((p, q) => p.t - q.t);
        let prev = null;
        b.values.forEach((e, k) => {
          const nx = b.values[k + 1];
          if (nx && nx.t - e.t < 0.02) return;   // superseded at once
          const tx = K.svg('text', { x: b.x, y: cellY + ch / 2 + 13, 'text-anchor': 'middle', class: 'acell-text mono' }, b.cell);
          tx.textContent = e.v;
          tx.style.fill = e.color ? K.ink(e.color) : e.v === '0' ? K.C.dim : e.v === '?' ? K.C.faint : K.C.ink;
          K.init(tx, { autoAlpha: 0, y: 24 });
          K.to(tx, { autoAlpha: 1, y: 0, duration: 0.32, ease: 'back.out(1.7)' }, e.t);
          if (prev) K.to(prev, { autoAlpha: 0, y: -24, duration: Math.min(0.25, nx ? nx.t - e.t - 0.01 : 0.25), ease: 'power2.in' }, e.t);
          if (e.flash && e.v !== '') R.cellFlash(b.i, e.t, e.color || 'mint');
          prev = tx;
        });
      });
    });

    // wait arcs: from waiting day j to the warmer day i, labelled with i - j
    R.arc = (j, i, t, ao = {}) => {
      const c = K.vis(ao.color ?? 'mint'), ci = K.ink(ao.color ?? 'mint'), d = Math.abs(i - j), H = 36 + 22 * d;
      const A = [R.x(j) + 8, arcY], Bp = [R.x(i) - 8, arcY], C = [(A[0] + Bp[0]) / 2, arcY - 2 * H];
      const g = K.svg('g', { 'data-k': `arc ${j}-${i}` }, gArc);
      const path = `M${f1(A[0])},${A[1]} Q${f1(C[0])},${f1(C[1])} ${f1(Bp[0])},${Bp[1]}`;
      const glow = K.svg('path', { d: path, class: 'arc-glow', stroke: c }, g);
      const core = K.svg('path', { d: path, class: 'arc-core', stroke: c, 'stroke-dasharray': ao.dash ? '10 10' : null }, g);
      const ang = Math.atan2(Bp[1] - C[1], Bp[0] - C[0]) * 180 / Math.PI;
      const head = K.svg('path', { d: 'M8,0 L-12,-9 L-7,0 L-12,9 Z', fill: c, transform: `translate(${f1(Bp[0])},${Bp[1]}) rotate(${ang.toFixed(1)})` }, g);
      K.init([glow, core], { drawSVG: '0%' });
      K.init(head, { autoAlpha: 0 });
      K.init(g, { autoAlpha: 0 });
      const dd = ao.d ?? 0.4 + 0.08 * d;
      K.set(g, { autoAlpha: 1 }, t);
      K.fromTo([glow, core], { drawSVG: '0%' }, { drawSVG: '100%', duration: dd, ease: 'power2.inOut' }, t);
      K.to(head, { autoAlpha: 1, duration: 0.12 }, t + dd - 0.08);
      let pill = null;
      if (ao.label !== undefined && ao.label !== null) {
        pill = K.svg('g', { transform: `translate(${f1(C[0])},${f1(arcY - H)})` }, gArc);
        const inner = K.svg('g', {}, pill);
        const w = Math.max(44, K.textW(String(ao.label), '700 28px "JetBrains Mono"') + 24);
        K.svg('rect', { x: -w / 2, y: -21, width: w, height: 42, rx: 21, fill: K.C.panel, stroke: c, 'stroke-width': 3 }, inner);
        const tx = K.svg('text', { y: 10, 'text-anchor': 'middle', class: 'arc-label mono', fill: ci }, inner);
        tx.textContent = String(ao.label);
        K.init(inner, { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' });
        K.pop(inner, t + dd * 0.7, 0.45);
        pill = inner;
      }
      const a = { g, pill, t, cleared: false, end: t + dd };
      R.arcs.push(a);
      if (ao.until !== undefined) R.clearArcs(ao.until, 0.3, [a]);
      return a;
    };
    R.clearArcs = (t, d = 0.35, list = null) => {
      for (const a of list || R.arcs) if (!a.cleared && a.t < t) {
        K.to(a.g, { autoAlpha: 0, duration: d }, t);
        if (a.pill) K.to(a.pill, { autoAlpha: 0, duration: d }, t);
        a.cleared = true;
      }
    };
    /** A small pill above bar i's label. */
    R.tag = (i, text, t, to = {}) => {
      const c = K.col(to.color ?? 'cyan');
      const w = K.textW(text, '700 26px "JetBrains Mono"') + 26;
      const g = K.svg('g', { transform: `translate(${R.x(i)},${labY - 62 + (to.dy ?? 0)})`, 'data-k': `tag ${text} ${i}` }, gLab);
      const inner = K.svg('g', {}, g);
      K.svg('rect', { x: -w / 2, y: -19, width: w, height: 38, rx: 10, fill: to.solid ? c : K.C.panel, stroke: to.solid ? c : K.ink(c), 'stroke-width': 2.5 }, inner);
      const tx = K.svg('text', { y: 9, 'text-anchor': 'middle', class: 'tag-text mono', fill: to.solid ? K.on(c) : K.ink(c) }, inner);
      tx.textContent = text;
      K.init(inner, { autoAlpha: 0, scale: 0.3, transformOrigin: '50% 50%' });
      K.pop(inner, t, 0.45);
      if (to.until !== undefined) K.to(inner, { autoAlpha: 0, duration: 0.25 }, to.until);
      R.tags.push(inner);
      return inner;
    };
    /** A highlight column behind a bar with a tag on top ("today", "i", "j"); moves between bars. */
    R.marker = (color = 'accent', text = 'today') => {
      const c = K.col(color);
      const g = K.svg('g', { 'data-k': `marker ${text}` }, gBack);
      const name = Object.keys(K.C).find((k) => K.C[k] === c) || 'accent';
      const top = labY - 44, bot = idxY + 14;
      K.svg('rect', { x: -62, y: top, width: 124, height: bot - top, rx: 22, fill: c, 'fill-opacity': 0.085, stroke: K.vis(c), 'stroke-width': 3, 'stroke-opacity': 0.85 }, g);
      K.svg('ellipse', { cx: 0, cy: thermo ? base + 24 : base - 40, rx: 90, ry: 90, fill: `url(#glow-${name})`, opacity: 0.7 }, g);
      if (text) {
        const w = K.textW(text, '800 26px Inter') + 28;
        K.svg('rect', { x: -w / 2, y: top - 40, width: w, height: 36, rx: 9, fill: c }, g);
        const tx = K.svg('text', { x: 0, y: top - 13, 'text-anchor': 'middle', class: 'marker-text' }, g);
        tx.style.fill = K.on(c);
        tx.textContent = text;
      }
      K.init(g, { autoAlpha: 0, x: R.x(0) });
      const vis = K.channel(g), pos = K.channel(g);
      // vis and pos touch different properties (opacity vs x) of the same element: the fight detector keys on property
      const M = { g, at: null, on: false };
      M.show = (t, i) => { if (i !== undefined) { pos.set(t - 0.001, { x: R.x(i) }); M.at = i; } if (!M.on) { vis.to(t, { autoAlpha: 1 }, 0.3); M.on = true; } };
      M.hide = (t) => { if (M.on) { vis.to(t, { autoAlpha: 0 }, 0.25); M.on = false; } };
      M.to = (i, t, d = 0.35, ease = 'power3.inOut') => { if (!M.on) M.show(t, i); else pos.to(t, { x: R.x(i) }, d, ease); M.at = i; return t + d; };
      return M;
    };
    return R;
  };

  // ------------------------------------------------------------------ the stack column
  K.stackCol = function (o) {
    const R = o.R, x = o.x ?? 1350, w = o.w ?? 250, bottom = o.bottom ?? 700, top = o.top ?? 400;
    const cw = o.chipW ?? 210, chh = o.chipH ?? 58, gap = 10;
    const cx = x + w / 2;
    const S = { x, w, bottom, top, chips: [], stack: [], pushes: 0, pops: 0 };
    const g = K.svg('g', { 'data-k': 'stack' }, K.layer.panels);
    K.svg('rect', { x: x + 12, y: top + 18, width: w, height: bottom - top, rx: 26, fill: K.U.stackShadow }, g);
    K.svg('rect', { x, y: top, width: w, height: bottom - top, rx: 26, class: 'stack-fill' }, g);
    const r = 26;
    const u = K.svg('path', { d: `M${x},${top} L${x},${bottom - r} Q${x},${bottom} ${x + r},${bottom} L${x + w - r},${bottom} Q${x + w},${bottom} ${x + w},${bottom - r} L${x + w},${top}`, class: 'stack-tube' }, g);
    const lips = [K.svg('line', { x1: x - 14, x2: x + 10, y1: top, y2: top, class: 'stack-tube' }, g), K.svg('line', { x1: x + w - 10, x2: x + w + 14, y1: top, y2: top, class: 'stack-tube' }, g)];
    const title = K.svg('text', { x: cx, y: top - 28, 'text-anchor': 'middle', class: 'kicker-svg' }, g);
    title.textContent = (o.title ?? 'STACK').toUpperCase();
    const topLab = K.svg('text', { x: x + w + 22, y: top + 40, class: 'stack-side' }, g); topLab.textContent = o.topText ?? '';
    K.init(u, { drawSVG: '0%' });
    K.init(lips, { autoAlpha: 0 });
    K.init(g, { autoAlpha: 0 });
    K.init([title, topLab], { autoAlpha: 0, y: 10 });
    const gChips = K.svg('g', { 'data-k': 'chips' }, K.layer.tokens);
    S.slotY = (k) => bottom - 14 - chh / 2 - k * (chh + gap);
    S.rect = (pad = 30) => ({ x: x - pad, y: top - 64 - pad, w: w + 2 * pad, h: bottom - top + 64 + 2 * pad });
    S.show = (t) => {
      K.set(g, { autoAlpha: 1 }, t);
      K.fromTo(u, { drawSVG: '0%' }, { drawSVG: '100%', duration: 0.8, ease: 'power2.inOut' }, t);
      K.to(lips, { autoAlpha: 1, duration: 0.3 }, t + 0.6);
      K.to([title, topLab], { autoAlpha: 1, y: 0, duration: 0.45, stagger: 0.1 }, t + 0.4);
      return t + 0.8;
    };
    S.hide = (t) => K.to(g, { autoAlpha: 0, duration: 0.4 }, t);
    /** Fade the tube and every chip in it (the chips keep their own state). */
    S.fade = (t, a, d = 0.4) => K.to([g, gChips], { opacity: a, duration: d, ease: 'sine.inOut' }, t);
    function chip(i, v) {
      const c = K.svg('g', { 'data-k': `chip ${i}` }, gChips);
      const fill = o.colorOf ? o.colorOf(v) : K.C.cyan;
      const rect = K.svg('rect', { x: -cw / 2, y: -chh / 2, width: cw, height: chh, rx: 14, fill, stroke: K.C.black, 'stroke-width': 2.5 }, c);
      K.svg('rect', { x: -cw / 2 + 4, y: -chh / 2 + 4, width: cw - 8, height: 10, rx: 5, fill: K.U.chipHi }, c);
      const tx = K.svg('text', { x: 0, y: 11, 'text-anchor': 'middle', class: 'chip-big mono' }, c);
      tx.style.fill = K.on(fill);   // the label on the chip's fill (heat colours: text or bg, whichever reads better)
      const [ta, tb] = o.chipText ? o.chipText(i, v) : R.look === 'thermo' ? [`day ${i}`, `${v}${R.unit}`] : [`i ${i}`, `${v}${R.unit}`];
      tx.innerHTML = `<tspan class="chip-day">${K.esc(ta)}</tspan><tspan dx="14">${K.esc(tb)}</tspan>`;
      K.init(c, { autoAlpha: 0, x: R.labelPt(i)[0], y: R.labelPt(i)[1], scale: 1, transformOrigin: '50% 50%' });
      return { g: c, rect, tx, i, v, fill };
    }
    /** Push day i (value v) at t: a chip lifts off bar i's label and drops into the next slot. */
    S.push = (i, v, t, po = {}) => {
      const k = S.stack.length, ch = chip(i, v);
      const [sx, sy] = R.labelPt(i), ex = cx, ey = S.slotY(k);
      const lift = Math.min(220, 80 + Math.abs(ex - sx) * 0.18);
      const path = K.svg('path', { d: `M${f1(sx)},${f1(sy)} C${f1(sx)},${f1(sy - lift)} ${f1(ex)},${f1(Math.min(sy, ey) - lift)} ${f1(ex)},${f1(ey)}`, fill: 'none', stroke: 'none' }, gChips);
      const d = po.d ?? 0.75;
      K.to(ch.g, { autoAlpha: 1, duration: 0.15 }, t);
      K.to(ch.g, { motionPath: { path }, duration: d, ease: 'power2.inOut' }, t);
      ch.inAt = t + d;
      S.stack.push(ch); S.chips.push(ch); S.pushes++;
      return t + d;
    };
    /** Flash the top chip (being compared). */
    S.flashTop = (t, color = 'accent', hold = 0.4) => {
      const ch = S.stack[S.stack.length - 1];
      if (!ch) return;
      K.to(ch.rect, { stroke: K.col(color), strokeWidth: 6, duration: 0.12 }, t);
      K.to(ch.rect, { stroke: K.C.black, strokeWidth: 2.5, duration: 0.3 }, t + hold);
    };
    /** Pop the top chip (index j) at t because element i resolves it: it flies to answer cell j and writes
     *  po.value there (default i - j, the distance; value: v for "next greater value"; write: false for none). */
    S.pop = (t, i, po = {}) => {
      const ch = S.stack.pop();
      if (!ch) throw new Error('stackCol.pop on an empty stack');
      const j = ch.i, k = S.stack.length;
      const sx = cx, sy = S.slotY(k), [ex, ey] = R.cellPt(j);
      K.to(ch.rect, { fill: K.C.mint, duration: 0.15 }, t);
      K.to(ch.tx, { fill: K.on('mint'), duration: 0.15 }, t);
      K.to(ch.g, { y: sy - 70, duration: 0.3, ease: 'power2.out' }, t + 0.05);
      const path = K.svg('path', { d: `M${f1(sx)},${f1(sy - 70)} C${f1(sx - 120)},${f1(sy - 200)} ${f1(ex + 60)},${f1(ey - 260)} ${f1(ex)},${f1(ey)}`, fill: 'none', stroke: 'none' }, gChips);
      const d = po.d ?? 0.8;
      K.to(ch.g, { motionPath: { path }, duration: d, ease: 'power2.inOut' }, t + 0.36);
      K.to(ch.g, { scale: 0.45, duration: d, ease: 'power2.in' }, t + 0.36);
      K.to(ch.g, { autoAlpha: 0, duration: 0.18 }, t + 0.36 + d - 0.12);
      const land = t + 0.36 + d - 0.05;
      if (po.write !== false) R.answer(j, po.value ?? i - j, land, { color: po.color ?? 'mint' });
      S.pops++;
      return { j, land };
    };
    /** Empty the stack at t (chips fade where they are; the model resets). */
    S.clear = (t) => { S.stack.splice(0).forEach((ch) => K.to(ch.g, { autoAlpha: 0, duration: 0.35 }, t)); };
    S.topChip = () => S.stack[S.stack.length - 1];
    S.depth = () => S.stack.length;
    return S;
  };
})();
