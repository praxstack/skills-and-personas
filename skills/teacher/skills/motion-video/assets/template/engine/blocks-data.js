// engine/blocks-data.js: number and chart blocks. stat (a big number that counts), bars, line, ring.
// Values come from film.json directly or from a dataset ("=set.col:max", {"from": "set", "x": .., "y": ..}),
// so a new CSV re-renders the film with the new numbers and nothing else edited.
(function () {
  const M = window.M;
  if (!M || !M.tl) return;
  const TY = LOOK.TYPE;
  const fmtOf = (p, v) => p.format || (Number.isInteger(v) ? 'int' : '0.0');
  const given = (v) => v !== undefined && v !== null && v !== '';   // written down by the author: 0 counts
  /** Grow 0 -> 1 over d seconds, calling fn(f) on every frame (one proxy per element, tracked for overlaps). */
  const grow = (key, t, d, fn, ease = 'settle') => {
    const o = { f: 0, key };
    fn(0);
    return M.fromTo(o, { f: 0 }, { f: 1, duration: d, ease, onUpdate: () => fn(o.f) }, t);
  };
  const nice = (x) => {
    if (x <= 0) return 1;
    const e = Math.pow(10, Math.floor(Math.log10(x))), f = x / e;
    return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10) * e;
  };
  const title = (c, el) => {
    const { props: p, u } = c;
    if (!p.title) return 0;
    const t = M.el('div', 'ttl', el);
    M.rich(p.title, t);
    if (p.unit) { t.appendChild(document.createTextNode(' ')); M.el('span', 'unit', t, null, p.unit); }
    M.fit(t, c.box.w, 60 * u, 36 * u, TY.min * u, `${c.where} title`);
    return { el: t, h: 76 * u };
  };

  // ------------------------------------------------------------------ stat
  M.block('stat', {
    fields: {
      value: { type: 'value', required: true, help: 'a number, or "=set.column:max" from a dataset' },
      from: { type: 'number', help: 'count up from this, a number (default 0)' },
      format: { type: 'text', help: 'int, 0.0, pct, compact, x, money, money:₹, time' },
      prefix: { type: 'text' }, suffix: { type: 'text', help: 'e.g. " fps"' },
      label: { type: 'text', help: 'what the number is' },
      kicker: { type: 'text' },
      delta: { type: 'json', help: '{"text": "+12% vs last week", "tone": "good"}' },
      spark: { type: 'json', help: 'a small trend line, 2 or more numbers: [3, 5, 4, 8] or {"from": "set", "x": "day", "y": "n"}' },
      align: { type: 'enum', options: ['left', 'center'] },
    },
    cues: ['count', 'delta'],
    weight: { row: 1, column: 1 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const v = M.data.num(c.value(p.value));
      if (!isFinite(v)) throw new Error(`value ${JSON.stringify(p.value)} is not a number`);
      const from = p.from === undefined || p.from === null || p.from === '' ? 0 : M.data.num(p.from);
      if (!isFinite(from)) throw new Error(`"from" ${JSON.stringify(p.from)} is not a number`);
      const fmt = fmtOf(p, v);
      const inn = M.el('div', 'in', el);
      if (p.align === 'center') { inn.style.alignItems = 'center'; inn.style.textAlign = 'center'; }
      const kick = p.kicker ? M.el('div', 'kicker', inn, null, p.kicker) : null;
      const vEl = M.el('div', 'v num', inn);
      if (p.prefix) M.el('span', 'affix', vEl, null, p.prefix);
      const nEl = M.el('span', 'n', vEl, null, M.fmtNum(v, fmt));
      if (p.suffix) M.el('span', 'affix', vEl, null, p.suffix);
      const lab = p.label ? M.el('div', 'lab', inn) : null;
      if (lab) M.rich(p.label, lab);
      let delta = null;
      if (p.delta !== undefined && p.delta !== null && p.delta !== '') {
        // a text, or {"text": ..., "tone": ...}; a chip with nothing in it would animate and say nothing
        const d = typeof p.delta === 'string' || typeof p.delta === 'number' ? { text: p.delta } : p.delta;
        const shown = d && typeof d === 'object' && !Array.isArray(d) && ((typeof d.text === 'string' && d.text.trim() !== '') || (typeof d.text === 'number' && isFinite(d.text)));
        if (!shown) throw new Error(`delta is ${JSON.stringify(p.delta)}; give a text, or {"text": "+12% vs last week", "tone": "good"}`);
        if (d.tone !== undefined && d.tone !== null && d.tone !== '' && !LOOK.HUES.includes(d.tone)) throw new Error(`delta tone ${JSON.stringify(d.tone)} is not one of ${LOOK.HUES.join(', ')}`);
        const hue = M.hue(d.tone || (/^[-−▼]/.test(String(d.text)) ? 'bad' : 'good'));
        delta = M.el('div', 'delta chip num', inn, { color: P[hue + 'Ink'] }, String(d.text));
      }
      let spark = null;
      if (p.spark) {
        const inline = Array.isArray(p.spark) && p.spark.every((y) => y === null || typeof y !== 'object');   // [3, 5, 4, 8]
        const pts = inline ? p.spark.map((y, i) => {
          const v = M.data.num(y);
          if (!isFinite(v)) throw new Error(`spark point ${i + 1} (${JSON.stringify(y)}) is not a number`);
          return { label: String(i), value: v };
        }) : c.rows(p.spark);
        if (pts.length < 2) throw new Error(`spark needs at least 2 points (got ${pts.length})`);
        const sw = Math.min(box.w, 520 * u), sh = 96 * u;
        const svg = M.svg('svg', { width: sw, height: sh + 20 * u, viewBox: `0 -${10 * u} ${sw} ${sh + 20 * u}` }, inn);
        const lo = Math.min(...pts.map((d) => d.value)), hi = Math.max(...pts.map((d) => d.value));
        const xy = pts.map((d, i) => [(i / Math.max(1, pts.length - 1)) * (sw - 16 * u) + 8 * u, sh - ((d.value - lo) / ((hi - lo) || 1)) * sh]);
        const path = M.svg('path', { d: 'M' + xy.map((q) => q.map((x) => x.toFixed(1)).join(',')).join('L'), fill: 'none', stroke: P.accent, 'stroke-width': 6 * u, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg);
        const dot = M.svg('circle', { cx: xy[xy.length - 1][0], cy: xy[xy.length - 1][1], r: 10 * u, fill: P.accent }, svg);
        spark = { path, dot };
      }
      // sizes: the number takes what is left after the other rows
      const rest = (kick ? 60 : 0) + (lab ? 110 : 0) + (delta ? 80 : 0) + (spark ? 140 : 0);
      const size = M.fit(vEl, box.w, Math.max(90 * u, box.h - rest * u), (M.shape === 'tall' ? TY.statTall : TY.stat) * u, 64 * u, `${c.where} value`);
      vEl.querySelectorAll('.affix').forEach((a) => { a.style.fontSize = size * 0.42 + 'px'; });
      if (lab) M.fit(lab, box.w, 110 * u, TY.label * 1.18 * u, TY.min * u, `${c.where} label`);
      const cueOf = (n) => c.cues.find((x) => x.do === n);
      if (delta) M.init(delta, { autoAlpha: 0 });
      let counted = 0, landed = 0;
      const showDelta = (t1) => M.fromTo(delta, { autoAlpha: 0, scale: 0.7 }, { autoAlpha: 1, scale: 1, duration: 0.5, ease: 'back.out(2.2)' }, t1);
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (kick) M.fromTo(kick, { autoAlpha: 0, x: -24 * u }, { autoAlpha: 1, x: 0, duration: 0.5 }, t0);
          M.fromTo(vEl, { autoAlpha: 0, y: 30 * u }, { autoAlpha: 1, y: 0, duration: 0.6, ease: 'lift' }, t0 + 0.05);
          landed = t0 + 0.65;
          if (!cueOf('count')) { M.count(nEl, t0 + 0.15, from, v, fmt, 1.3); counted = t0 + 1.45; } else nEl.textContent = M.fmtNum(from, fmt);
          if (lab) M.fromTo(lab, { autoAlpha: 0, y: 16 * u }, { autoAlpha: 1, y: 0, duration: 0.5 }, t0 + 0.35);
          if (spark) {
            M.fromTo(spark.path, { drawSVG: '0%' }, { drawSVG: '100%', duration: 1.2, ease: 'power2.inOut' }, t0 + 0.4);
            M.fromTo(spark.dot, { scale: 0, transformOrigin: '50% 50%' }, { scale: 1, duration: 0.4, ease: 'back.out(3)' }, t0 + 1.55);
          }
          const deltaIn = delta && !cueOf('delta') ? Math.max(t0 + 1.2, counted) + 0.5 : 0;
          if (deltaIn) showDelta(deltaIn - 0.5);
          return Math.max(landed, counted, deltaIn, lab ? t0 + 0.85 : 0, spark ? t0 + 1.95 : 0);   // value, count, delta, label and sparkline in
        },
        cues: {
          count: (cue, t1) => {
            const t = Math.max(t1, landed), d = cue.d === undefined || cue.d === null || cue.d === '' ? 1.3 : M.data.num(cue.d);
            if (!(d >= 0.2 && d <= 10)) throw new Error(`"d" ${JSON.stringify(cue.d)} is the seconds the count runs, a number from 0.2 to 10`);
            M.count(nEl, t, from, v, fmt, d);
            counted = t + d;
            return { at: t, end: counted };   // the final number must land before the block leaves
          },
          delta: (cue, t1) => {
            if (!delta) throw new Error('there is no delta to show; add "delta": {"text": "+12% vs last week"} or drop the cue');
            const t = Math.max(t1, counted - 0.2); showDelta(t);
            return { at: t, end: t + 0.5 };
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ bars
  M.block('bars', {
    fields: {
      rows: { type: 'rows', required: true, help: '[{"label": "GSAP", "value": 7}] or {"from": "set", "x": "kit", "y": "fps", "sort": "desc"}' },
      title: { type: 'text' }, unit: { type: 'text', help: 'shown after the title, e.g. "frames/s"' },
      format: { type: 'text' },
      highlight: { type: 'text', help: 'a label (or "max"/"min") drawn in the accent; the rest go neutral' },
      orient: { type: 'enum', options: ['auto', 'h', 'v'] },
      max: { type: 'number', help: 'the scale end, at least the largest value and target (default: the largest value)' },
      target: { type: 'json', help: '{"value": 30, "label": "real time"}: a dashed line' },
    },
    cues: ['highlight', 'target'],
    weight: { row: 1.3, column: 1.4 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      el.classList.add('chart');
      const data = c.rows(p.rows);
      if (!data.length) throw new Error('rows is empty');
      const neg = data.filter((d) => d.value < 0);
      if (neg.length) throw new Error(`bars are sizes from zero, so values must be 0 or more (below 0: ${neg.map((d) => d.label).join(', ')}); show a change that can go negative with a line chart`);
      const ttl = title(c, el);
      const top = ttl ? ttl.h : 0;
      const W = box.w, H = box.h - top;
      const tv = p.target ? M.data.num(c.value(p.target.value)) : null;
      if (p.target && !(isFinite(tv) && tv >= 0)) throw new Error(`target needs {"value": a number of 0 or more} (got ${JSON.stringify(p.target.value)})`);
      const tlab = p.target && p.target.label;
      if (tlab !== undefined && tlab !== null && tlab !== '' && !(typeof tlab === 'string' && tlab.trim() !== '') && !(typeof tlab === 'number' && isFinite(tlab))) throw new Error(`target label ${JSON.stringify(tlab)} is not a text`);
      if (!p.target && c.cues.some((x) => x.do === 'target')) throw new Error('a "target" cue needs the block\'s target ({"value": 30, "label": "real time"})');
      const big = Math.max(...data.map((d) => d.value), tv || 0);
      const maxV = p.max === undefined || p.max === null || p.max === '' ? big || 1 : M.data.num(p.max);  // all zeros: empty bars, not NaN
      if (!(isFinite(maxV) && maxV > 0)) throw new Error(`max ${JSON.stringify(p.max)} must be a number above 0`);
      if (maxV < big) throw new Error(`max ${maxV} is below the largest value or target (${big}); raise it or leave it out`);
      const fmt = p.format || (data.every((d) => Number.isInteger(d.value)) ? 'int' : '0.0');
      const longest = Math.max(...data.map((d) => d.label.length));
      const orient = p.orient && p.orient !== 'auto' ? p.orient : (M.shape === 'wide' && data.length <= 8 && longest <= 9 ? 'v' : 'h');
      const svg = M.svg('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, el);
      svg.style.marginTop = top + 'px';
      const n = data.length;
      const bars = [];
      const valFont = (s) => `700 ${s}px Inter`, labFont = (s) => `560 ${s}px Inter`;
      if (orient === 'h') {
        const band = p.target ? 46 * u : 0;   // the target's label sits in a band above the rows, inside the chart
        const rowH = (H - band) / n, bh = Math.min(rowH * 0.6, 70 * u);
        const fs = M.clamp(rowH * 0.34, TY.min * u, 36 * u);
        const lw = Math.max(...data.map((d) => M.textW(d.label, labFont(fs)))) + 26 * u;
        const vw = Math.max(...data.map((d) => M.textW(M.fmtNum(d.value, fmt), valFont(fs)))) + 22 * u;
        const pw = W - lw - vw;
        M.svg('line', { class: 'axis', x1: lw, x2: lw, y1: band, y2: H, 'stroke-width': 3 * u }, svg);
        data.forEach((d, i) => {
          const cy = band + rowH * (i + 0.5);
          const lab = M.svg('text', { x: lw - 20 * u, y: cy, 'text-anchor': 'end', 'dominant-baseline': 'central', 'font-size': fs }, svg);
          lab.textContent = d.label;
          const r = M.svg('rect', { x: lw, y: cy - bh / 2, width: 0, height: bh, rx: Math.min(bh * 0.24, 14 * u), fill: P.accent }, svg);
          const val = M.svg('text', { class: 'val', x: lw + 14 * u, y: cy, 'dominant-baseline': 'central', 'font-size': fs }, svg);
          const len = (pw * d.value) / maxV;
          bars.push({ d, r, val, lab, set: (f) => { r.setAttribute('width', Math.max(0, len * f)); val.setAttribute('x', lw + len * f + 14 * u); val.textContent = M.fmtNum(d.value * f, fmt); } });
        });
        if (p.target) {
          const x = lw + (pw * tv) / maxV;
          const g = M.svg('g', {}, svg);
          M.svg('line', { x1: x, x2: x, y1: 4 * u, y2: H, stroke: P.text, 'stroke-width': 3 * u, 'stroke-dasharray': `${10 * u} ${8 * u}` }, g);
          const txt = given(tlab) ? String(tlab) : M.fmtNum(tv, fmt);
          const right = x + 10 * u + M.textW(txt, valFont(30 * u)) <= W;
          const tl = M.svg('text', { class: 'val', x: right ? x + 10 * u : x - 10 * u, y: band - 14 * u, 'text-anchor': right ? 'start' : 'end', 'font-size': 30 * u }, g);
          tl.textContent = txt;
          bars.target = g;
        }
      } else {
        const colW = W / n, bw = Math.min(colW * 0.58, 130 * u);
        const fs = M.clamp(Math.min(colW * 0.2, 34 * u), TY.min * u, 34 * u);
        const labH = 58 * u, valH = 56 * u, ph = H - labH - valH;
        const base = valH + ph;
        M.svg('line', { class: 'axis', x1: 0, x2: W, y1: base, y2: base, 'stroke-width': 3 * u }, svg);
        data.forEach((d, i) => {
          const cx = colW * (i + 0.5);
          const lab = M.svg('text', { x: cx, y: base + 42 * u, 'text-anchor': 'middle', 'font-size': fs }, svg);
          lab.textContent = d.label;
          const r = M.svg('rect', { x: cx - bw / 2, y: base, width: bw, height: 0, rx: Math.min(bw * 0.16, 14 * u), fill: P.accent }, svg);
          const val = M.svg('text', { class: 'val', x: cx, y: base - 14 * u, 'text-anchor': 'middle', 'font-size': fs * 1.08 }, svg);
          const len = (ph * d.value) / maxV;
          bars.push({ d, r, val, lab, set: (f) => { r.setAttribute('y', base - len * f); r.setAttribute('height', Math.max(0, len * f)); val.setAttribute('y', base - len * f - 14 * u); val.textContent = M.fmtNum(d.value * f, fmt); } });
        });
        if (p.target) {
          const y = base - (ph * tv) / maxV;
          const g = M.svg('g', {}, svg);
          M.svg('line', { x1: -6 * u, x2: W + 6 * u, y1: y, y2: y, stroke: P.text, 'stroke-width': 3 * u, 'stroke-dasharray': `${10 * u} ${8 * u}` }, g);
          const tl = M.svg('text', { class: 'val', x: W, y: y - 12 * u, 'text-anchor': 'end', 'font-size': 30 * u }, g);
          tl.textContent = given(tlab) ? String(tlab) : M.fmtNum(tv, fmt);
          bars.target = g;
        }
      }
      if (bars.target) M.init(bars.target, { autoAlpha: 0 });
      const pick = (lbl) => {
        if (lbl === 'max') return bars.reduce((a, b) => (b.d.value > a.d.value ? b : a));
        if (lbl === 'min') return bars.reduce((a, b) => (b.d.value < a.d.value ? b : a));
        const hits = bars.filter((x) => x.d.label.toLowerCase() === String(lbl).toLowerCase());
        if (!hits.length) throw new Error(`highlight "${lbl}" is not one of the labels (${bars.map((x) => x.d.label).join(', ')})`);
        if (hits.length > 1) throw new Error(`highlight "${lbl}" names ${hits.length} bars (the label repeats in rows); give each row its own label`);
        return hits[0];
      };
      const highlight = (lbl, t1) => {
        const hb = pick(lbl);
        bars.forEach((b) => M.to(b.r, { attr: { fill: b === hb ? P.accent : P.line2 }, duration: 0.45 }, t1));
        bars.forEach((b) => M.to(b.val, { fill: b === hb ? P.accentInk : P.text, duration: 0.3 }, t1));
        M.fromTo(hb.r, { scale: 1, transformOrigin: orient === 'h' ? '0% 50%' : '50% 100%' }, { scale: 1.06, duration: 0.25, ease: 'power2.out', yoyo: true, repeat: 1 }, t1);
      };
      const cueOf = (k) => c.cues.find((x) => x.do === k);
      let landed = 0;
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (ttl) M.fromTo(ttl.el, { autoAlpha: 0, y: 14 * u }, { autoAlpha: 1, y: 0, duration: 0.5 }, t0);
          M.fromTo(svg, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, t0 + 0.05);
          const st = Math.min(0.12, 0.8 / n);
          bars.forEach((b, i) => grow(`bar${i}`, t0 + 0.2 + i * st, 1.1, b.set));
          landed = t0 + 0.2 + (n - 1) * st + 1.1;
          if (p.highlight && !cueOf('highlight')) highlight(p.highlight, landed + 0.2);
          if (bars.target && !cueOf('target')) M.fromTo(bars.target, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, landed);
          // every bar grown, and the highlight and target line in when they come without a cue
          return Math.max(landed, p.highlight && !cueOf('highlight') ? landed + 0.7 : 0, bars.target && !cueOf('target') ? landed + 0.4 : 0);
        },
        cues: {
          highlight: (cue, t1) => { const t = Math.max(t1, landed); highlight(given(cue.label) ? cue.label : given(p.highlight) ? p.highlight : 'max', t); return { at: t, end: t + 0.5 }; },
          target: (cue, t1) => {
            const t = Math.max(t1, landed - 0.3);   // the build refuses this cue without a target
            M.fromTo(bars.target, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, t);
            return { at: t, end: t + 0.4 };
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ line chart
  M.block('line', {
    fields: {
      rows: { type: 'rows', required: true, help: '[{"label": "Mon", "value": 3}] or {"from": "set", "x": "day", "y": "n"}' },
      title: { type: 'text' }, unit: { type: 'text' }, format: { type: 'text' },
      area: { type: 'bool', help: 'shade under the line (default true)' },
      min: { type: 'number', help: 'the scale\'s bottom, at or below every value (default: 0, or the lowest value if below 0)' },
      max: { type: 'number', help: 'the scale\'s top, above min and at or above every value (default: a round number over the highest value)' },
    },
    cues: ['annotate'],
    weight: { row: 1.4, column: 1.3 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      el.classList.add('chart');
      const data = c.rows(p.rows);
      if (data.length < 2) throw new Error('a line needs at least 2 rows');
      const ttl = title(c, el);
      const top = ttl ? ttl.h : 0;
      const W = box.w, H = box.h - top;
      const vals = data.map((d) => d.value);
      const set = (v) => v !== undefined && v !== null && v !== '';
      const lo = set(p.min) ? M.data.num(p.min) : Math.min(0, ...vals);
      const hi = set(p.max) ? M.data.num(p.max) : nice(Math.max(...vals) * 1.08);
      if (!(isFinite(lo) && isFinite(hi) && hi > lo)) throw new Error(`the scale needs max above min (min ${lo}, max ${hi})`);
      const vlo = Math.min(...vals), vhi = Math.max(...vals);   // every point stays on the chart
      if (vlo < lo || vhi > hi) throw new Error(`the scale ${lo} to ${hi} leaves out values (they run ${vlo} to ${vhi}); widen min and max, or leave them out`);
      const fmt = p.format || (vals.every(Number.isInteger) ? 'int' : '0.0');
      const fs = 30 * u;
      // ticks on a round step (1, 2, 2.5 or 5 x 10^n; no 2.5 for whole numbers), three to five of them
      const raw = (hi - lo) / 4, mag = 10 ** Math.floor(Math.log10(raw || 1));
      const step = (fmt === 'int' && mag >= 1 ? [1, 2, 5, 10] : [1, 2, 2.5, 5, 10]).map((m) => m * mag).find((x) => x >= raw) || raw;
      const ticks = [];
      for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-9; v += step) ticks.push(+v.toFixed(6));
      const lw = Math.max(...ticks.map((t) => M.textW(M.fmtNum(t, fmt), `560 ${fs}px Inter`))) + 22 * u;
      const bh = 54 * u, rpad = 90 * u, tpad = 40 * u;
      const pw = W - lw - rpad, ph = H - bh - tpad;
      const X = (i) => lw + (i / (data.length - 1)) * pw, Y = (v) => tpad + ph - ((v - lo) / (hi - lo)) * ph;
      const svg = M.svg('svg', { width: W, height: H, viewBox: `0 0 ${W} ${H}` }, el);
      svg.style.marginTop = top + 'px';
      ticks.forEach((t) => {
        M.svg('line', { class: 'grid', x1: lw, x2: lw + pw, y1: Y(t), y2: Y(t), 'stroke-width': 2 * u }, svg);
        const tx = M.svg('text', { x: lw - 14 * u, y: Y(t), 'text-anchor': 'end', 'dominant-baseline': 'central', 'font-size': fs }, svg);
        tx.textContent = M.fmtNum(t, fmt);
      });
      const every = Math.ceil(data.length / (M.shape === 'wide' ? 8 : 5));
      data.forEach((d, i) => {
        if (i % every && i !== data.length - 1) return;
        const tx = M.svg('text', { x: X(i), y: tpad + ph + 40 * u, 'text-anchor': 'middle', 'font-size': fs }, svg);
        tx.textContent = d.label;
      });
      const pts = data.map((d, i) => [X(i), Y(d.value)]);
      const dStr = 'M' + pts.map((q) => q.map((x) => x.toFixed(1)).join(',')).join('L');
      const area = p.area === false ? null : M.svg('path', { d: `${dStr}L${X(data.length - 1)},${Y(lo)}L${X(0)},${Y(lo)}Z`, fill: M.rgba(P.accent, 0.14) }, svg);
      const line = M.svg('path', { d: dStr, fill: 'none', stroke: P.accent, 'stroke-width': 7 * u, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, svg);
      const last = pts[pts.length - 1];
      const dot = M.svg('circle', { cx: last[0], cy: last[1], r: 13 * u, fill: P.accent, stroke: P.bg, 'stroke-width': 5 * u }, svg);
      const endLab = M.svg('text', { class: 'val', x: last[0] + 22 * u, y: last[1], 'dominant-baseline': 'central', 'font-size': 36 * u, fill: P.accentInk }, svg);
      endLab.textContent = M.fmtNum(data[data.length - 1].value, fmt);
      [area, dot, endLab].forEach((x) => x && M.init(x, { autoAlpha: 0 }));
      let landed = 0;
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          if (ttl) M.fromTo(ttl.el, { autoAlpha: 0, y: 14 * u }, { autoAlpha: 1, y: 0, duration: 0.5 }, t0);
          M.fromTo(svg, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.4 }, t0 + 0.05);
          M.fromTo(line, { drawSVG: '0%' }, { drawSVG: '100%', duration: 1.6, ease: 'power2.inOut' }, t0 + 0.25);
          if (area) M.fromTo(area, { autoAlpha: 0 }, { autoAlpha: 1, duration: 1.0 }, t0 + 0.9);
          M.fromTo(dot, { autoAlpha: 0, scale: 0, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: 0.45, ease: 'back.out(3)' }, t0 + 1.8);
          M.fromTo(endLab, { autoAlpha: 0, x: -10 * u }, { autoAlpha: 1, x: 0, duration: 0.4 }, t0 + 1.9);
          landed = t0 + 2.1;
          return t0 + 2.3;   // the line drawn and its end value in
        },
        cues: {
          annotate: (cue, t1) => {
            const i = data.findIndex((d) => d.label === String(cue.x));
            if (i < 0) throw new Error(`annotate x "${cue.x}" is not a label (${data.map((d) => d.label).join(', ')})`);
            if (data.findIndex((d, k) => k > i && d.label === String(cue.x)) >= 0) throw new Error(`annotate x "${cue.x}" names more than one point (the label repeats in rows); give each row its own label`);
            const [x, y] = pts[i];
            const hue = M.hue(cue.tone || 'accent');
            const g = M.svg('g', {}, svg);
            M.svg('circle', { cx: x, cy: y, r: 12 * u, fill: P[hue], stroke: P.bg, 'stroke-width': 5 * u }, g);
            M.svg('line', { x1: x, x2: x, y1: y - 18 * u, y2: Math.max(8 * u, y - 90 * u), stroke: P[hue + 'Ink'], 'stroke-width': 3 * u }, g);
            const tx = M.svg('text', { class: 'val', x, y: Math.max(8 * u, y - 90 * u) - 12 * u, 'text-anchor': x > W * 0.7 ? 'end' : x < W * 0.3 ? 'start' : 'middle', 'font-size': 32 * u, fill: P[hue + 'Ink'] }, g);
            const own = cue.text !== undefined && cue.text !== null && cue.text !== '';
            if (own && !(typeof cue.text === 'string' && cue.text.trim() !== '') && !(typeof cue.text === 'number' && isFinite(cue.text))) throw new Error(`annotate "text" is ${JSON.stringify(cue.text)}; give a short text (or leave it out to show the value)`);
            tx.textContent = own ? String(cue.text) : M.fmtNum(data[i].value, fmt);
            M.init(g, { autoAlpha: 0 });
            const t = Math.max(t1, landed - 0.4);
            M.fromTo(g, { autoAlpha: 0, y: 14 * u }, { autoAlpha: 1, y: 0, duration: 0.45, ease: 'back.out(2)' }, t);
            return { at: t, end: t + 0.45 };
          },
        },
      };
    },
  });

  // ------------------------------------------------------------------ ring: a share of a whole
  M.block('ring', {
    fields: {
      value: { type: 'value', required: true, help: 'a number or "=set.col:agg", from 0 to the total' },
      total: { type: 'value', help: 'the whole, above 0 (default 100)' },
      label: { type: 'text' }, format: { type: 'text', help: 'default pct of total' },
      tone: { type: 'enum', options: LOOK.HUES },
    },
    weight: { row: 1, column: 1 },
    build(c) {
      const { el, box, props: p, u, P } = c;
      const v = M.data.num(c.value(p.value)), tot = p.total !== undefined ? M.data.num(c.value(p.total)) : 100;
      if (!isFinite(v)) throw new Error(`value ${JSON.stringify(p.value)} is not a number`);
      if (!(isFinite(tot) && tot > 0)) throw new Error(`total ${JSON.stringify(p.total)} is not a number above 0`);
      if (v < 0 || v > tot) throw new Error(`value ${v} is outside 0 to ${tot} (the total); a ring shows a share of its total`);
      const share = v / tot;
      const labH = p.label ? 120 * u : 0;
      const R = Math.max(80 * u, Math.min(box.w, box.h - labH) / 2 - 24 * u), sw = Math.max(26 * u, R * 0.16);
      const svg = M.svg('svg', { width: box.w, height: R * 2 + 20 * u, viewBox: `${-box.w / 2} ${-R - 10 * u} ${box.w} ${R * 2 + 20 * u}` }, el);
      Object.assign(svg.style, { position: 'absolute', left: 0, top: Math.max(0, (box.h - labH - R * 2 - 20 * u) / 2) + 'px' });
      M.svg('circle', { r: R - sw / 2, fill: 'none', stroke: P.line, 'stroke-width': sw }, svg);
      const hue = M.hue(p.tone || 'accent');
      const arc = M.svg('circle', { r: R - sw / 2, fill: 'none', stroke: P[hue], 'stroke-width': sw, 'stroke-linecap': 'round', transform: 'rotate(-90)' }, svg);
      const num = M.svg('text', { 'text-anchor': 'middle', 'dominant-baseline': 'central', 'font-size': R * 0.5, 'font-weight': 760, fill: P.text, 'font-family': 'Inter' }, svg);
      const pct = !p.format || /^pct/.test(p.format) ? share * 100 : null;
      const fmt = p.format || 'pct';
      num.textContent = M.fmtNum(pct ?? v, fmt);
      const lab = p.label ? M.el('div', 'lab', el, { position: 'absolute', left: 0, right: 0, bottom: 0, textAlign: 'center', fontSize: 38 * u + 'px', color: P.muted, fontWeight: 560 }) : null;
      if (lab) { M.rich(p.label, lab); M.fit(lab, box.w, labH, 38 * u, TY.min * u, `${c.where} label`); }
      return {
        enter(t0) {
          M.set(el, { autoAlpha: 1 }, t0);
          M.fromTo(svg, { autoAlpha: 0, scale: 0.9, transformOrigin: '50% 50%' }, { autoAlpha: 1, scale: 1, duration: 0.6, ease: 'lift' }, t0);
          M.fromTo(arc, { drawSVG: '0% 0%' }, { drawSVG: `0% ${(share * 100).toFixed(2)}%`, duration: 1.4, ease: 'settle' }, t0 + 0.2);
          M.count(num, t0 + 0.2, 0, pct ?? v, fmt, 1.4);
          if (lab) M.fromTo(lab, { autoAlpha: 0, y: 14 * u }, { autoAlpha: 1, y: 0, duration: 0.5 }, t0 + 0.5);
          return t0 + 1.6;   // the arc and its count done
        },
      };
    },
  });
})();
