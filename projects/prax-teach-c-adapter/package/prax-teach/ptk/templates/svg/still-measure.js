// In-page measurement of one still SVG, run by verify/visual.py through shoot.mjs `script` jobs.
// It sizes the SVG the way the viewer page does (natural width, never wider than the viewport), then
// reports, all from computed styles of the rendered page:
//   problems   min-size (< opts.minPx CSS px), overflow (text outside its data-in box or the viewBox),
//              overlap (two text boxes), key-node-* (D20.3: each data-key node fully inside the viewport,
//              no taller than it, inside the figure; every required key present), numeric (not lining+tabular)
//   contrast   text vs the filled rect under it (4.5), rules / borders / path graphics vs both sides (3.0)
//   tones      rendered colours of data-tone="note" and data-tone="correction" text, for the L* check
(opts) => {
  const rgb = (c) => { const m = String(c).match(/[\d.]+/g); return m ? m.slice(0, 3).map(Number) : null; };
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => 0.2126 * lin(c[0]) + 0.7152 * lin(c[1]) + 0.0722 * lin(c[2]);
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const labL = (c) => { const y = lum(c); return y > 216 / 24389 ? 116 * Math.cbrt(y) - 16 : (24389 / 27) * y; };

  const svg = document.querySelector('svg');
  const vb = svg.viewBox.baseVal;
  const shown = Math.min(vb.width, window.innerWidth);
  svg.setAttribute('width', String(shown));
  svg.setAttribute('height', String(vb.height * shown / vb.width));
  svg.style.display = 'block';
  const scale = shown / vb.width;
  const all = [...svg.querySelectorAll('*')].filter((e) => !e.parentElement.closest('[data-math]'));
  const rects = all.filter((e) => e.tagName === 'rect');
  const texts = all.filter((e) => e.tagName === 'text');
  const box = (el) => { const b = el.getBBox(); return { x: b.x, y: b.y, r: b.x + b.width, b: b.y + b.height }; };
  const filled = (r) => { const f = getComputedStyle(r).fill; return f && f !== 'none' && !/rgba\(.*,\s*0\)/.test(f); };
  const before = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
  // the filled rect drawn last before `el` that contains the point
  const under = (el, x, y) => {
    let bg = null;
    for (const r of rects) {
      if (r === el || !before(r, el) || !filled(r)) continue;
      const rb = box(r);
      if (x >= rb.x && x <= rb.r && y >= rb.y && y <= rb.b) bg = r;
    }
    return bg;
  };
  const fillOf = (r) => rgb(getComputedStyle(r).fill);
  const problems = [], contrast = [], sizes = [], families = new Set(), tones = { note: [], correction: [] };

  for (const t of texts) {
    const a = box(t);
    const cs = getComputedStyle(t);
    families.add(cs.fontFamily);
    const px = parseFloat(cs.fontSize) * scale;
    sizes.push(px);
    if (px < opts.minPx - 0.01) problems.push({ kind: 'min-size', text: t.textContent.slice(0, 40), px: +px.toFixed(2) });
    const fvn = cs.fontVariantNumeric || '';
    if (!(fvn.includes('lining-nums') && fvn.includes('tabular-nums')))
      problems.push({ kind: 'numeric', text: t.textContent.slice(0, 40), fontVariantNumeric: fvn });
    if (t.dataset.in) {
      const c = document.getElementById(t.dataset.in);
      if (!c) problems.push({ kind: 'overflow', text: t.textContent.slice(0, 40), container: t.dataset.in, missing: true });
      else {
        const cb = box(c);
        if (a.x < cb.x - 0.5 || a.r > cb.r + 0.5 || a.y < cb.y - 0.5 || a.b > cb.b + 0.5)
          problems.push({ kind: 'overflow', text: t.textContent.slice(0, 40), container: t.dataset.in,
                          text_box: [a.x, a.r, a.y, a.b].map((v) => +v.toFixed(1)), box: [cb.x, cb.r, cb.y, cb.b] });
      }
    }
    if (a.r > vb.width + 0.5 || a.x < -0.5 || a.b > vb.height + 0.5 || a.y < -0.5)
      problems.push({ kind: 'overflow', text: t.textContent.slice(0, 40), container: 'svg' });
    const cx = (a.x + a.r) / 2, cy = (a.y + a.b) / 2;
    const bg = under(t, cx, cy);
    const bgc = bg ? fillOf(bg) : [255, 255, 255];
    const fgs = new Set([cs.fill, ...[...t.querySelectorAll('tspan')].map((s) => getComputedStyle(s).fill)]);
    for (const fg of fgs) {
      contrast.push({ kind: 'text', text: t.textContent.slice(0, 40), fg, bg: `rgb(${bgc.join(', ')})`,
                      ratio: +ratio(rgb(fg), bgc).toFixed(2), min: 4.5 });
    }
    if (t.dataset.tone && tones[t.dataset.tone]) tones[t.dataset.tone].push(+labL(rgb(cs.fill)).toFixed(2));
  }
  // math (MathJax glyphs in a [data-math] group): its colour against the background under it; its box
  // must stay inside the viewBox
  for (const m of svg.querySelectorAll('[data-math]')) {
    const [x, y, w, h] = m.dataset.box.split(' ').map(Number);
    const bg = under(m, x + w / 2, y + h / 2);
    const fg = rgb(getComputedStyle(m).color);
    const bgc = bg ? fillOf(bg) : [255, 255, 255];
    contrast.push({ kind: 'text', text: 'math', fg: `rgb(${fg.join(', ')})`, bg: `rgb(${bgc.join(', ')})`,
                    ratio: +ratio(fg, bgc).toFixed(2), min: 4.5 });
    if (x < -0.5 || x + w > vb.width + 0.5) problems.push({ kind: 'overflow', text: 'math', container: 'svg' });
  }
  for (let i = 0; i < texts.length; i++) {
    for (let j = i + 1; j < texts.length; j++) {
      const a = box(texts[i]), b = box(texts[j]);
      const ix = Math.min(a.r, b.r) - Math.max(a.x, b.x), iy = Math.min(a.b, b.b) - Math.max(a.y, b.y);
      if (ix > 1 && iy > 1) problems.push({ kind: 'overlap', a: texts[i].textContent.slice(0, 40), b: texts[j].textContent.slice(0, 40) });
    }
  }
  // graphics: rules, card borders, the path and its dots, against what is on each side of them
  const graphic = all.filter((e) => (e.tagName === 'rect' && e.getAttribute('stroke'))
    || ['rule', 'path', 'pill'].includes(e.dataset.role));
  for (const el of graphic) {
    const cs = getComputedStyle(el);
    const paint = el.tagName === 'circle' ? cs.fill : cs.stroke;
    if (!paint || paint === 'none') continue;
    const b = box(el);
    const sides = [];
    if (el.tagName === 'rect') {
      sides.push(filled(el) ? fillOf(el) : null);                  // inside the border
      const out = under(el, b.x - 2, (b.y + b.b) / 2);            // just outside it
      sides.push(out ? fillOf(out) : null);
    } else {
      const bg = under(el, (b.x + b.r) / 2, (b.y + b.b) / 2);
      sides.push(bg ? fillOf(bg) : null);
    }
    const fg = rgb(paint);
    const vals = sides.filter(Boolean).map((s) => ({ s, r: ratio(fg, s) }));
    if (!vals.length) continue;
    // WCAG 1.4.11: a border must stand out against at least one adjacent colour; a line against its ground
    const best = vals.reduce((p, q) => (q.r > p.r ? q : p));
    contrast.push({ kind: 'rule', el: el.id || el.dataset.role || el.tagName, fg: paint,
                    bg: `rgb(${best.s.join(', ')})`, ratio: +best.r.toFixed(2), min: 3 });
  }
  // key nodes (D20.3)
  const r0 = svg.getBoundingClientRect();
  const keys = {};
  for (const el of svg.querySelectorAll('[data-key]')) {
    const r = el.getBoundingClientRect();
    const k = el.dataset.key;
    keys[k] = { left: +r.left.toFixed(1), right: +r.right.toFixed(1), top: +(r.top - r0.top).toFixed(1),
                height: +r.height.toFixed(1), width: +r.width.toFixed(1) };
    if (r.left < -0.5 || r.right > window.innerWidth + 0.5)
      problems.push({ kind: 'key-node-offscreen', key: k, left: r.left, right: r.right, viewport: window.innerWidth });
    if (r.height > window.innerHeight + 0.5)
      problems.push({ kind: 'key-node-taller-than-viewport', key: k, height: r.height, viewport: window.innerHeight });
    if (r.top < r0.top - 0.5 || r.bottom > r0.bottom + 0.5 || r.left < r0.left - 0.5 || r.right > r0.right + 0.5)
      problems.push({ kind: 'key-node-clipped', key: k });
    if (!r.width || !r.height) problems.push({ kind: 'key-node-empty', key: k });
  }
  for (const k of opts.keys || []) if (!keys[k]) problems.push({ kind: 'key-node-missing', key: k });
  const sw = document.documentElement.scrollWidth;
  if (sw > window.innerWidth + 1) problems.push({ kind: 'page-overflow', scrollWidth: sw, innerWidth: window.innerWidth });
  return {
    scale, shown_width: shown, viewport: [window.innerWidth, window.innerHeight], problems, contrast, tones, keys,
    minPx: sizes.length ? Math.min(...sizes) : 0, fonts: [...families],
    title: document.querySelector('title')?.textContent || '', desc: document.querySelector('desc')?.textContent || '',
    source: !!document.querySelector('[data-role="source"]'),
    loadedFaces: [...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family),
  };
}
