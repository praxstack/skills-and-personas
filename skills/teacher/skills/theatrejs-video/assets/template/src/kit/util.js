// Small pure helpers shared by the kit (no DOM access at import time, so tools/build.mjs can import the kit in node).

export const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
export const lerp = (a, b, u) => a + (b - a) * u;
export const smooth = (u) => { u = clamp(u); return u * u * (3 - 2 * u); };
export const fmt = (x, d = 2) => Number(x).toFixed(d);

// colours: '#rrggbb', '#rgb' or {r,g,b,a} (Theatre rgba, 0..1) -> mixable [r,g,b,a] in 0..255 / 0..1
export function rgb(c) {
  if (Array.isArray(c)) return c;
  if (typeof c === 'object') return [c.r * 255, c.g * 255, c.b * 255, c.a ?? 1];
  let h = c.replace('#', '');
  if (h.length === 3) h = [...h].map((x) => x + x).join(''); // '#fff'
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16), 1];
}
export const mix = (a, b, u) => { const A = rgb(a), B = rgb(b); return A.map((x, i) => lerp(x, B[i], clamp(u))); };
export const css = (c, alpha) => { const [r, g, b, a] = rgb(c); return `rgba(${r | 0},${g | 0},${b | 0},${fmt(alpha ?? a, 3)})`; };
/** '#ff5b2e' -> Theatre rgba {r,g,b,a} */
export const rgba = (hex, a = 1) => { const [r, g, b] = rgb(hex); return { r: r / 255, g: g / 255, b: b / 255, a }; };
/** any colour -> '#rrggbb' (for mixes that must stay hex, e.g. Theatre string defaults) */
export const hex = (c) => '#' + rgb(c).slice(0, 3).map((x) => Math.round(clamp(x, 0, 255)).toString(16).padStart(2, '0')).join('');
/** WCAG contrast ratio of two colours */
export function contrast(a, b) {
  const L = (c) => { const v = rgb(c).slice(0, 3).map((x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  const x = L(a), y = L(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}
/** the candidate with the highest contrast on `ground` (a label on a shape whose fill is a mix of several hues) */
export const bestInk = (ground, candidates) => candidates.reduce((best, c) => (contrast(c, ground) > contrast(best, ground) ? c : best));

// deterministic pseudo-random numbers (same seed, same film)
export function rng(seed = 1) {
  let s = seed >>> 0 || 1;
  return () => { s ^= s << 13; s ^= s >>> 17; s ^= s << 5; return ((s >>> 0) % 100000) / 100000; };
}

// DOM helpers (only called from mount(), never at import time)
export function el(tag, attrs = {}, parent = null, ns = null) {
  const e = ns ? document.createElementNS(ns, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === 'text') e.textContent = v;
    else if (k === 'html') e.innerHTML = v;
    else if (k === 'style' && typeof v === 'object') Object.assign(e.style, v);
    else e.setAttribute(k, v);
  }
  if (parent) parent.appendChild(e);
  return e;
}
export const SVGNS = 'http://www.w3.org/2000/svg';
export const svg = (tag, attrs, parent) => el(tag, attrs, parent, SVGNS);

// only touch the DOM when a value really changed (keeps the per-frame cost low)
export function setStyle(e, k, v) { if (e.__s?.[k] !== v) { (e.__s ||= {})[k] = v; e.style[k] = v; } }
export function setAttr(e, k, v) { if (e.__a?.[k] !== v) { (e.__a ||= {})[k] = v; e.setAttribute(k, v); } }
export function setText(e, v) { v = String(v); if (e.__t !== v) { e.__t = v; e.textContent = v; } }

// highlight numbers, O(...) and arrows inside a caption-like string (returns HTML)
export function markup(s) {
  const esc = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const re = /(O\((?:[^()]|\([^()]*\))*\))|(\[[^\]]*\])|(-?\d+(?:\.\d+)?)|([→∞≤≥≠·])/g;
  let out = '', i = 0, m;
  while ((m = re.exec(s))) {
    out += esc(s.slice(i, m.index));
    out += `<span class="${m[1] ? 'hl-o' : m[2] ? 'hl-arr' : m[3] ? 'hl-num' : 'hl-sym'}">${esc(m[0])}</span>`;
    i = m.index + m[0].length;
  }
  return (out + esc(s.slice(i))).replace(/\^\(([^()]*)\)/g, '<sup>$1</sup>').replace(/\^(\w)/g, '<sup>$1</sup>');
}
