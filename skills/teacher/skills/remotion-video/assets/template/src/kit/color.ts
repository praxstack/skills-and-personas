// Colour arithmetic for the theme mapping in tokens.ts: parse, mix, alpha, WCAG contrast, and `fit`, which moves a
// colour's lightness (same hue and saturation, like theme.py) until it clears a contrast target on a surface.
// Holds no palette: every colour on screen is named in tokens.ts.

type RGBA = [number, number, number, number];

export const parse = (c: string): RGBA => {
  const s = c.trim();
  if (s.startsWith('#')) {
    let h = s.slice(1);
    if (h.length === 3 || h.length === 4) h = h.split('').map((x) => x + x).join('');
    const n = (i: number) => parseInt(h.slice(i, i + 2), 16);
    return [n(0), n(2), n(4), h.length >= 8 ? n(6) / 255 : 1];
  }
  const m = s.match(/rgba?\(([^)]*)\)/);
  if (!m) throw new Error(`color: cannot parse ${c}`);
  const p = m[1].split(',').map((x) => parseFloat(x));
  return [p[0], p[1], p[2], p[3] ?? 1];
};

const h2 = (v: number) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0').toUpperCase();
export const hex = (r: number, g: number, b: number) => `#${h2(r)}${h2(g)}${h2(b)}`;

/** rgba() of a colour at alpha a (the colour's own alpha is replaced) */
export const alpha = (c: string, a: number) => {
  const [r, g, b] = parse(c);
  return `rgba(${r},${g},${b},${+a.toFixed(3)})`;
};

/** sRGB lerp from a to b (t = 0 is a), as CSS gradients blend; opaque hex out */
export const mix = (a: string, b: string, t: number) => {
  const x = parse(a);
  const y = parse(b);
  return hex(x[0] + (y[0] - x[0]) * t, x[1] + (y[1] - x[1]) * t, x[2] + (y[2] - x[2]) * t);
};

/** a translucent colour composited over an opaque surface */
export const over = (top: string, under: string) => {
  const [r, g, b, a] = parse(top);
  return mix(under, hex(r, g, b), a);
};

const lin = (v: number) => {
  const c = v / 255;
  return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
};
export const lum = (c: string) => {
  const [r, g, b] = parse(c);
  return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
};
export const contrast = (a: string, b: string) => {
  const x = lum(a);
  const y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

const toHsl = ([r, g, b]: RGBA): [number, number, number] => {
  const R = r / 255, G = g / 255, B = b / 255;
  const mx = Math.max(R, G, B), mn = Math.min(R, G, B);
  const l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn;
  const s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === R ? (G - B) / d + (G < B ? 6 : 0) : mx === G ? (B - R) / d + 2 : (R - G) / d + 4;
  return [h / 6, s, l];
};
const fromHsl = (h: number, s: number, l: number) => {
  if (s === 0) return hex(l * 255, l * 255, l * 255);
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  const f = (t: number) => {
    t = (t + 1) % 1;
    return t < 1 / 6 ? p + (q - p) * 6 * t : t < 1 / 2 ? q : t < 2 / 3 ? p + (q - p) * (2 / 3 - t) * 6 : p;
  };
  return hex(f(h + 1 / 3) * 255, f(h) * 255, f(h - 1 / 3) * 255);
};

/** `fg` with its lightness moved away from every surface in `on` until it clears `target` on all of them (fg
 *  unchanged when it already does). Same hue and saturation, as theme.py solves its inks. */
export const fit = (fg: string, on: string | string[], target = 4.6) => {
  const surfaces = Array.isArray(on) ? on : [on];
  const worst = (c: string) => Math.min(...surfaces.map((s) => contrast(c, s)));
  if (worst(fg) >= target) return fg;
  const [h, s, l] = toHsl(parse(fg));
  const dark = surfaces.reduce((k, x) => k + lum(x), 0) / surfaces.length > 0.18; // light surfaces: darken the ink
  for (let i = 1; i <= 100; i++) {
    const L = dark ? l * (1 - i / 100) : l + (1 - l) * (i / 100);
    const c = fromHsl(h, s, L);
    if (worst(c) >= target) return c;
  }
  return dark ? '#000000' : '#FFFFFF';
};
