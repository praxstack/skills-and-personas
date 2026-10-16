// kit/panels.js: the input decoder (world space), and the screen-space code panel, state table, complexity
// ladder and value meter. Components that change state many times (code focus, table cells, ladder focus)
// collect their events and emit the tweens in time order at K.finalize(), so the order you call them in
// scenes.js does not matter and no two tweens fight over one property.
(function () {
  const K = window.K;
  const hooks = [];
  K.onFinalize = (fn) => hooks.push(fn);
  K.finalize = () => { hooks.splice(0).forEach((fn) => fn()); };
  const MONO = (s, w = 400) => `${w} ${s}px "JetBrains Mono"`;

  // ------------------------------------------------------------------ input decoder (WORLD space, SVG)
  /**
   * K.decoder({x, y, w, title, lines: ['n = 4', 'flights = [', '  [0, 1, 100],', ...], size: 30, lh: 50})
   *   .show(t)  .hide(t)  .mark(i, t, {color, until})  .chip(i, t, worldPoint, {text, col, dur, color})
   *   .pt(i, col) -> world point of line i (0-based), column col
   * Lines are monospace; numbers are amber, punctuation dim. Chips are copies of the text that fly to the subject.
   */
  K.decoder = function (o) {
    const size = o.size ?? 30, lh = o.lh ?? 50, pad = 34, top = 84;
    const cw = K.textW('0', MONO(size));
    // wide enough for the longest line and for the title (30 px caps, letter-spacing 0.14em, as .kicker-svg)
    const title = (o.title ?? 'INPUT').toUpperCase();
    const titleW = K.textW(title, '750 30px Inter') + title.length * 30 * 0.14;
    const w = o.w ?? Math.max(Math.max(...o.lines.map((l) => l.length)) * cw + pad * 2 + 20, titleW + pad * 2);
    const h = top + o.lines.length * lh + pad - 6;
    const D = { lines: [], bars: [], x: o.x, y: o.y, w, h };
    const g = (D.g = K.svg('g', { 'data-k': 'decoder' }, K.layer.panels));
    K.svg('rect', { x: o.x + 10, y: o.y + 14, width: w, height: h, rx: 22, fill: K.U.panelShadow }, g);
    K.svg('rect', { x: o.x, y: o.y, width: w, height: h, rx: 22, class: 'panel-rect' }, g);
    const tt = K.svg('text', { x: o.x + pad, y: o.y + 48, class: 'kicker-svg' }, g);
    tt.textContent = title;
    o.lines.forEach((line, i) => {
      const y = o.y + top + i * lh;
      const bar = K.svg('rect', { x: o.x + pad - 12, y: y - lh * 0.5, width: w - 2 * pad + 24, height: lh - 6, rx: 8, fill: K.C.accent, 'fill-opacity': K.FX.markA }, g);
      K.init(bar, { autoAlpha: 0 });
      D.bars.push(bar);
      const tx = K.svg('text', { x: o.x + pad, y: y + size * 0.36, class: 'mono decoder-line' }, g);
      for (const m of line.matchAll(/(\d+)|([A-Za-z_]\w*)|(\s+)|([^\w\s]+)/g)) {
        const sp = K.svg('tspan', { class: m[1] ? 'num' : m[2] ? 'id' : m[4] ? 'punct' : '' }, tx);
        sp.textContent = m[0];
      }
      tx.setAttribute('xml:space', 'preserve');
      K.init(tx, { autoAlpha: 0, x: -14 });
      D.lines.push(tx);
    });
    K.init(g, { autoAlpha: 0, x: -40 });
    D.pt = (i, col = 0) => [o.x + pad + col * cw, o.y + top + i * lh];
    D.show = (t, stagger = 0.07) => {
      K.to(g, { autoAlpha: 1, x: 0, duration: 0.6, ease: 'expo.out' }, t);
      K.to(D.lines, { autoAlpha: 1, x: 0, duration: 0.4, stagger, ease: 'power3.out' }, t + 0.15);
      return t + 0.15 + stagger * D.lines.length + 0.4;
    };
    D.hide = (t, d = 0.45) => K.to(g, { autoAlpha: 0, x: -60, duration: d, ease: 'power2.in' }, t);
    const marks = [];
    /** Highlight line i from t until `until` (default t + 1.6 s). */
    D.mark = (i, t, mo = {}) => {
      const bar = D.bars[i];
      marks.push({ bar, t, until: mo.until ?? t + 1.6, color: K.col(mo.color ?? 'accent') });
    };
    K.onFinalize(() => {
      const byBar = new Map();
      marks.forEach((m) => { if (!byBar.has(m.bar)) byBar.set(m.bar, []); byBar.get(m.bar).push(m); });
      byBar.forEach((ms, bar) => {
        ms.sort((a, b) => a.t - b.t);
        ms.forEach((m, k) => {
          const until = Math.min(m.until, ms[k + 1] ? ms[k + 1].t - 0.3 : 1e9);
          K.set(bar, { fill: m.color }, m.t);
          K.fromTo(bar, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.2 }, m.t);
          K.to(bar, { autoAlpha: 0, duration: 0.3 }, Math.max(m.t + 0.25, until));
        });
      });
    });
    /** A copy of (part of) line i flies to a world point and lands there at the returned time. */
    D.chip = (i, t, to, co = {}) => {
      const line = o.lines[i];
      const text = co.text ?? line.trim();
      const col = co.col ?? line.indexOf(text);
      const from = D.pt(i, Math.max(0, col));
      const tw = K.textW(text, MONO(size, 600)) + 36;   // roomy padding: the text never touches the chip's edge
      const c = K.svg('g', { 'data-k': `chip ${text}` }, K.layer.fx);
      K.svg('rect', { x: 0, y: -size * 0.85, width: tw, height: size * 1.7, rx: 12, fill: K.col(co.color ?? 'amber') }, c);
      const tx = K.svg('text', { x: 18, y: size * 0.36, class: 'mono chip-text' }, c);
      tx.style.fill = K.on(co.color ?? 'amber');
      tx.textContent = text;
      const dur = co.dur ?? 0.9;
      const sx = from[0] - 18, sy = from[1];
      const ex = to[0] - tw / 2, ey = to[1];
      const lift = Math.min(200, Math.abs(ex - sx) * 0.25 + 60);
      // leave along its own row first (straight out of the panel), then arc to the target: a chip that rises
      // straight up crosses the rows above it, and a still caught mid-flight shows two texts on top of each other
      const path = K.svg('path', { d: `M${sx},${sy} C${sx + (ex - sx) * 0.55},${sy} ${ex - (ex - sx) * 0.2},${ey - lift} ${ex},${ey}`, fill: 'none', stroke: 'none' }, K.layer.fx);
      K.init(c, { autoAlpha: 0, x: sx, y: sy, scale: 1 });
      K.to(c, { autoAlpha: 1, duration: 0.15 }, t);
      K.to(c, { motionPath: { path }, duration: dur, ease: 'power2.inOut' }, t);
      K.to(c, { autoAlpha: 0, duration: 0.25 }, t + dur - 0.05);
      return t + dur;
    };
    return D;
  };

  // ------------------------------------------------------------------ code panel (SCREEN space, HTML)
  const KW = new Set('int long short char bool void double float auto const constexpr static unsigned signed for while do if else return break continue struct class public private using namespace template typename new delete true false nullptr sizeof include define'.split(' '));
  const TY = new Set('vector map unordered_map set unordered_set pair queue priority_queue deque stack string array size_t INF'.split(' '));
  /** Tiny C++/Python/Java-ish highlighter: comments, strings, numbers, keywords, types, function calls. */
  K.highlight = (src) => {
    const out = [];
    const re = /(\/\/.*$|#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?(?:e\d+)?\b)|([A-Za-z_]\w*)(\s*\()?|(\s+)|(.)/g;
    for (const m of src.matchAll(re)) {
      if (m[1]) out.push(`<span class="cm">${K.esc(m[1])}</span>`);
      else if (m[2]) out.push(`<span class="st">${K.esc(m[2])}</span>`);
      else if (m[3]) out.push(`<span class="nu">${m[3]}</span>`);
      else if (m[4]) {
        const cls = KW.has(m[4]) ? 'kw' : TY.has(m[4]) ? 'ty' : m[5] ? 'fn' : 'id';
        out.push(`<span class="${cls}">${m[4]}</span>${m[5] ? K.esc(m[5]) : ''}`);
      } else out.push(K.esc(m[0]));
    }
    return out.join('');
  };
  /**
   * K.codePanel({x, y, w, title, code, size, lh, maxLines})
   *   .show(t) .hide(t) .reveal(t, a, b) (1-based, inclusive) .revealAll(t) .focus(t, a, b = a) .unfocus(t)
   *   .lineRect(n) -> screen rect of line n
   * The highlighted range is shown with a bar; other revealed lines dim (to opacity 0.75, still >= 4.5:1) while
   * something has focus.
   */
  const DIM = K.FX.codeDim;   // 0.75 in the original palette; 1 (no dimming) in a theme, whose inks have no headroom
  K.codePanel = function (o) {
    const size = o.size ?? K.Z.code, lh = Math.round(size * (o.lh ?? 1.45));
    const src = o.code.replace(/^\n+|\s+$/g, '').split('\n');
    const P = { n: src.length };
    const vis = Math.min(src.length, o.maxLines ?? src.length);   // longer code scrolls to keep the focus in view
    const el = (P.el = K.html('div', 'code-panel', '', K.ui, { left: `${o.x}px`, top: `${o.y}px`, width: `${o.w}px` }));
    K.html('div', 'code-head', `<i></i><i></i><i></i><span>${K.esc(o.title ?? 'solution.cpp')}</span>`, el);
    const body = K.html('div', 'code-body', '', el, { height: `${vis * lh}px`, fontSize: `${size}px` });
    const scroll = K.html('div', 'code-scroll', '', body);
    const bar = K.html('div', 'code-bar', '', scroll, { height: `${lh}px` });
    P.lines = src.map((s, i) => {
      const row = K.html('div', 'cl mono', `<span class="no">${i + 1}</span><span class="tx">${K.highlight(s) || ' '}</span>`, scroll,
        { top: `${i * lh}px`, height: `${lh}px`, lineHeight: `${lh}px` });
      K.init(row, { autoAlpha: 0, x: -18 });
      return { row, tx: row.lastChild };
    });
    P.height = 58 + vis * lh + 28;
    K.init(bar, { autoAlpha: 0, y: 0 });
    K.init(scroll, { y: 0 });
    K.init(el, { autoAlpha: 0, x: -60 });
    P.show = (t) => K.to(el, { autoAlpha: 1, x: 0, duration: 0.7, ease: 'expo.out' }, t);
    P.hide = (t, d = 0.45) => K.to(el, { autoAlpha: 0, x: -60, duration: d, ease: 'power2.in' }, t);
    P.reveal = (t, a, b = a, stagger = 0.06) => {
      const rows = P.lines.slice(a - 1, b).map((l) => l.row);
      K.to(rows, { autoAlpha: 1, x: 0, duration: 0.4, stagger, ease: 'power3.out' }, t);
      return t + 0.4 + stagger * rows.length;
    };
    P.revealAll = (t, stagger = 0.04) => P.reveal(t, 1, P.n, stagger);
    const ev = [];
    P.focus = (t, a, b = a) => { if (a < 1 || b > P.n) throw new Error(`code focus ${a}-${b} is outside 1-${P.n}`); ev.push({ t, a, b }); };
    P.unfocus = (t) => ev.push({ t, a: 0, b: 0 });
    /** Screen rect of line n (1-based) when the panel is not scrolled. */
    P.lineRect = (n) => ({ x: o.x + 20, y: o.y + 58 + 14 + (n - 1) * lh, w: o.w - 40, h: lh });
    K.onFinalize(() => {
      ev.sort((p, q) => p.t - q.t);
      let cur = { a: 0, b: 0 }, y = 0, hgt = lh, top = 0;
      const dim = new Array(P.n).fill(false);
      ev.forEach((e, k) => {
        const next = ev[k + 1];
        const d = Math.min(0.35, next ? Math.max(0.05, next.t - e.t - 0.02) : 0.35);
        if (e.a) {
          const ny = (e.a - 1) * lh, nh = (e.b - e.a + 1) * lh;
          if (!cur.a) K.fromTo(bar, { autoAlpha: 0, y: ny, height: hgt }, { autoAlpha: 1, y: ny, height: nh, duration: d, ease: 'power2.out' }, e.t);
          else K.fromTo(bar, { y, height: hgt }, { y: ny, height: nh, duration: d, ease: 'power3.inOut' }, e.t);
          y = ny; hgt = nh;
          if (vis < P.n) {   // scroll so the focus sits on the second visible line (or as low as the end allows)
            let nt = K.clamp(e.a - 2, 0, P.n - vis);
            if (e.b - nt > vis) nt = Math.min(P.n - vis, e.b - vis);
            if (nt !== top) { K.fromTo(scroll, { y: -top * lh }, { y: -nt * lh, duration: Math.max(d, 0.3), ease: 'power3.inOut' }, e.t); top = nt; }
          }
        } else if (cur.a) K.to(bar, { autoAlpha: 0, duration: d }, e.t);
        P.lines.forEach((l, i) => {
          const want = e.a ? i + 1 < e.a || i + 1 > e.b : false;
          // dimmed context stays readable (>= 4.5:1 for every token colour on the panel); the bar marks the focus
          if (want !== dim[i] && DIM < 1) { K.to(l.tx, { opacity: want ? DIM : 1, duration: d }, e.t); dim[i] = want; }
        });
        cur = e;
      });
    });
    return P;
  };

  // ------------------------------------------------------------------ state table (SCREEN space, HTML)
  /**
   * K.table({x, y, title, cols: ['0','1','2','3'], colHead: 'city', rows: [{id:'dist', label:'dist', values:[...], hidden}], cw, ch})
   *   .show(t) .hide(t) .showRow(id, t) .set(id, col, value, t, {color, flash}) .ring(id, col, t, {color, dur})
   *   .copyRow(from, to, t)  .cell(id, col) -> screen rect
   * Values are strings or numbers ('∞' is drawn dim). set() slides the new value in and flashes the cell.
   */
  K.table = function (o) {
    const cw = o.cw ?? 118, ch = o.ch ?? 80, gap = o.gap ?? 10, lw = o.labelW ?? 130;
    const Tb = { rows: {}, x: o.x, y: o.y };
    const el = (Tb.el = K.html('div', 'tbl', '', K.ui, { left: `${o.x}px`, top: `${o.y}px` }));
    const head0 = o.title ? 52 : 0;
    if (o.title) K.html('div', 'kicker', K.esc(o.title), el);
    const hdr = K.html('div', 'tbl-head', `<span style="width:${lw}px">${K.esc(o.colHead ?? '')}</span>`, el);
    o.cols.forEach((c) => K.html('span', 'mono', K.esc(c), hdr, { width: `${cw}px`, marginRight: `${gap}px` }));
    const events = [];
    o.rows.forEach((r, ri) => {
      const row = K.html('div', 'tbl-row', '', el, { height: `${ch}px`, marginTop: `${gap}px` });
      K.html('div', 'tbl-label mono', K.esc(r.label ?? r.id), row, { width: `${lw}px` });
      const cells = o.cols.map((c, ci) => {
        const cell = K.html('div', 'cell mono', '', row, { width: `${cw}px`, height: `${ch}px`, marginRight: `${gap}px`, fontSize: `${Math.round(ch * 0.46)}px` });
        return { cell, spans: [] };
      });
      Tb.rows[r.id] = { row, cells, ri, cur: r.values.slice() };
      r.values.forEach((v, ci) => events.push({ t: -1, id: r.id, ci, v, o: {} }));
      if (r.hidden) K.init(row, { autoAlpha: 0, y: -20 });
    });
    K.init(el, { autoAlpha: 0, y: 30 });
    Tb.show = (t) => K.to(el, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'expo.out' }, t);
    Tb.hide = (t, d = 0.4) => K.to(el, { autoAlpha: 0, y: 30, duration: d, ease: 'power2.in' }, t);
    Tb.showRow = (id, t) => K.to(Tb.rows[id].row, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'expo.out' }, t);
    Tb.set = (id, ci, v, t, so = {}) => { if (!Tb.rows[id]) throw new Error(`table has no row ${id}`); events.push({ t, id, ci, v, o: so }); };
    /** Copy every value of row `from` into row `to`, cell by cell (values as of build order). */
    Tb.copyRow = (from, to, t, stagger = 0.08) => {
      Tb.rows[from].cur.forEach((v, ci) => Tb.set(to, ci, v, t + ci * stagger, { flash: 'faint' }));
      return t + o.cols.length * stagger + 0.3;
    };
    const rings = [];
    Tb.ring = (id, ci, t, ro = {}) => rings.push({ id, ci, t, color: K.vis(ro.color ?? 'accent'), dur: ro.dur ?? 1.4 });
    Tb.cell = (id, ci) => {
      const r = Tb.rows[id];
      return { x: o.x + lw + ci * (cw + gap), y: o.y + head0 + 40 + gap + r.ri * (ch + gap), w: cw, h: ch };
    };
    // keep build-order values so copyRow() and later sets see what set() wrote
    const origSet = Tb.set;
    Tb.set = (id, ci, v, t, so = {}) => { origSet(id, ci, v, t, so); Tb.rows[id].cur[ci] = v; };
    K.onFinalize(() => {
      const byCell = new Map();
      events.forEach((e) => { const k = `${e.id}:${e.ci}`; if (!byCell.has(k)) byCell.set(k, []); byCell.get(k).push(e); });
      byCell.forEach((evs) => {
        evs.sort((a, b) => a.t - b.t);
        let prev = null;
        evs.forEach((e) => {
          const c = Tb.rows[e.id].cells[e.ci];
          const sp = K.html('span', String(e.v) === '∞' ? 'inf' : '', K.esc(e.v), c.cell);
          if (e.o.color) sp.style.color = K.cellInk(e.o.color);
          if (e.t < 0) { prev = sp; return; }
          K.init(sp, { autoAlpha: 0, y: 34 });
          K.to(sp, { autoAlpha: 1, y: 0, duration: 0.35, ease: 'back.out(1.6)' }, e.t);
          if (prev) K.to(prev, { autoAlpha: 0, y: -34, duration: 0.25, ease: 'power2.in' }, e.t);
          if (e.o.flash !== false) {
            const fc = K.flashCol(e.o.flash && e.o.flash !== true ? e.o.flash : e.o.color ?? 'accent');   // a tint in themes
            K.fromTo(c.cell, { backgroundColor: fc }, { backgroundColor: K.C.bg2, duration: 0.9, ease: 'power2.out' }, e.t);
          }
          prev = sp;
        });
      });
      rings.forEach((r) => {
        const rc = Tb.cell(r.id, r.ci);
        const ring = K.html('div', 'ring', '', K.fx, { left: `${rc.x - 7}px`, top: `${rc.y - 7}px`, width: `${rc.w + 14}px`, height: `${rc.h + 14}px`, borderColor: r.color });
        K.init(ring, { autoAlpha: 0, scale: 1.4 });
        K.to(ring, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(2)' }, r.t);
        K.to(ring, { autoAlpha: 0, duration: 0.3 }, r.t + r.dur);
      });
    });
    return Tb;
  };

  // ------------------------------------------------------------------ complexity ladder (SCREEN space)
  /**
   * K.ladder({x, y, w, title, rungs: [{name, time: 'O(n^(k+1))', space: 'O(k)', cost: 0..1, note}]})
   *   .show(t) .rung(i, t) .focus(i, t) .pick(i, t, label) .hide(t)
   * The bar under each rung is as long as its cost; the pick turns mint and gets a stamp.
   */
  K.ladder = function (o) {
    const Ld = { rows: [] };
    const el = (Ld.el = K.html('div', 'ladder', '', K.ui, { left: `${o.x}px`, top: `${o.y}px`, width: `${o.w}px` }));
    K.html('div', 'kicker', K.esc(o.title ?? 'Every approach'), el);
    K.html('div', 'ladder-head', '<span>approach</span><span>time</span><span>space</span>', el);
    o.rungs.forEach((r, i) => {
      const row = K.html('div', 'rung', `<span class="idx mono">${i + 1}</span><span class="nm">${K.esc(r.name)}</span>` +
        `<span class="cx mono">${K.fmt(r.time ?? '')}</span><span class="sp mono">${K.fmt(r.space ?? '')}</span>` +
        `<i class="cost"><b></b></i>` + (r.note ? `<span class="note">${K.esc(r.note)}</span>` : ''), el);
      const bar = row.querySelector('.cost b');
      bar.style.background = K.vis(r.cost > 0.75 ? 'rose' : r.cost > 0.4 ? 'amber' : 'mint');
      K.init(row, { autoAlpha: 0, x: -40 });
      K.init(bar, { scaleX: 0, transformOrigin: '0% 50%' });
      Ld.rows.push({ row, bar, cost: r.cost ?? 0.5 });
    });
    K.init(el, { autoAlpha: 0, y: 24 });
    Ld.show = (t) => K.to(el, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'expo.out' }, t);
    Ld.hide = (t, d = 0.4) => K.to(el, { autoAlpha: 0, y: 24, duration: d, ease: 'power2.in' }, t);
    Ld.rung = (i, t) => {
      const r = Ld.rows[i];
      K.to(r.row, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'expo.out' }, t);
      K.to(r.bar, { scaleX: Math.max(0.04, r.cost), duration: 0.9, ease: 'power3.out' }, t + 0.2);
      return t + 0.7;
    };
    const ev = [];
    Ld.focus = (i, t) => ev.push({ t, i, pick: false });
    Ld.pick = (i, t, label = 'INTERVIEW PICK') => {
      ev.push({ t, i, pick: true });
      const st = K.html('div', 'stamp mini', K.esc(label), Ld.rows[i].row);
      K.init(st, { autoAlpha: 0, scale: 2.2, rotation: -4 });   // hangs under the rung's right end (styles.css .stamp.mini)
      K.to(st, { autoAlpha: 1, scale: 1, duration: 0.4, ease: 'back.out(1.4)' }, t + 0.25);
    };
    K.onFinalize(() => {
      ev.sort((a, b) => a.t - b.t);
      let cur = -1, picked = -1;
      ev.forEach((e) => {
        if (cur >= 0 && cur !== e.i && cur !== picked) K.to(Ld.rows[cur].row, { backgroundColor: K.U.rungBg, borderColor: K.U.rungLine, duration: 0.3 }, e.t);
        const c = e.pick ? K.U.rungPick : K.U.rungFocus;
        K.to(Ld.rows[e.i].row, { backgroundColor: c, borderColor: K.vis(e.pick ? 'mint' : 'accent'), duration: 0.35 }, e.t);
        cur = e.i;
        if (e.pick) picked = e.i;
      });
    });
    return Ld;
  };

  // ------------------------------------------------------------------ meter: a labelled number that ticks
  /** K.meter({x | right, y, label, value, color}) .show(t) .to(t, value, d) .hide(t)   (numbers only) */
  K.meter = function (o) {
    const el = K.html('div', 'meter', `<span class="lab">${K.esc(o.label ?? '')}</span><span class="val mono">${o.value ?? 0}</span>`, K.ui,
      { top: `${o.y}px`, borderColor: K.vis(o.color ?? 'amber') });
    if (o.right !== undefined) el.style.right = `${o.right}px`; else el.style.left = `${o.x}px`;
    const val = el.lastChild;
    val.style.color = K.ink(o.color ?? 'amber');
    K.init(el, { autoAlpha: 0, y: 16 });
    let last = -1;
    return {
      el, val,
      show: (t) => K.to(el, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'back.out(1.8)' }, t),
      hide: (t) => K.to(el, { autoAlpha: 0, y: 16, duration: 0.3, ease: 'power2.in' }, t),
      // pulse: false for fast counters (a pulse lasts 0.4 s; closer updates overlap and gsap_check flags them)
      to: (t, v, d = 0.5, mo = {}) => {
        if (t < last) throw new Error('meter.to: call in time order');
        last = t + d;
        K.count(val, t, v, d);
        if (mo.pulse !== false) K.pulse(el, t + d * 0.6, 1.12, 0.4);
      },
    };
  };
})();
