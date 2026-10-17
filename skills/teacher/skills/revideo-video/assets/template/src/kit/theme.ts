// Style tokens: the one place for palette, type and sizes. Change the look here, not in the scenes.
// Recipe: "dark editorial" (references/quality-bar.md). Warm near-black with grain and a light pool,
// one warm accent for "the thing being looked at", mint for valid/answer, rose for illegal/wrong.
//
// Themes (references/themes.md): src/theme-active.ts holds the registry theme, emitted by
//   python3 $S/theme.py emit <id> --format ts --out source/src/theme-active.ts
// The template ships a stub there (THEME = null): the original palette below, unchanged. With a theme, every
// role below is mapped from the theme's tokens (see `themed()`), and the helpers (inkOf, textOf, onOf, lineOf,
// glow, drop) pick the right token for text, shapes, glows and shadows. Scenes and the kit take every colour
// from here.
import {THEME as ACTIVE} from '../theme-active';

/** A registry theme's tokens (the keys theme.py emits; every colour is #RRGGBB). */
export interface ThemeTokens {
  id: string; name: string; family: string; slot: string; tone: 'light' | 'dark';
  bg: string; bg2: string; deep: string; panel: string; panel2: string; line: string; line2: string;
  text: string; muted: string; dim: string;
  accent: string; accentInk: string; onAccent: string; warm: string; warmInk: string; onWarm: string;
  good: string; goodInk: string; onGood: string; bad: string; badInk: string; onBad: string;
  cool: string; coolInk: string; onCool: string; gold: string; goldInk: string; onGold: string;
  violet: string; violetInk: string; onViolet: string;
  lights: string[]; shadow: string;
}
/** The active registry theme, or null for the kit's original palette. */
export const THEME: ThemeTokens | null = (ACTIVE as unknown as ThemeTokens | null) ?? null;
export const THEMED = THEME !== null;
/** A light-ground theme: grain multiplies, glows become soft shadows, the vignette is a gentle `deep` edge. */
export const LIGHT = THEME?.tone === 'light';

// ---------------------------------------------------------------- colour maths (themes only)
const hx = (c: string) => [1, 3, 5].map(i => parseInt(c.slice(i, i + 2), 16));
/** 'r,g,b' of a #RRGGBB colour (for rgba() strings and the texture generators). */
export const rgbOf = (c: string) => hx(c).join(',');
export const alpha = (c: string, a: number) => `rgba(${rgbOf(c)},${a})`;
/** Mix two #RRGGBB colours (t = 0: a, t = 1: b). */
export const mix = (a: string, b: string, t: number) => {
  const x = hx(a), y = hx(b);
  return '#' + x.map((v, i) => Math.round(v + (y[i] - v) * t).toString(16).padStart(2, '0')).join('');
};
const lum = (c: string) => {
  const [r, g, b] = hx(c).map(v => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
};
/** WCAG contrast ratio of two #RRGGBB colours. */
export const contrast = (a: string, b: string) => {
  const x = lum(a), y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
};

// ---------------------------------------------------------------- the original palette (the verified starter look)
const ORIGINAL = {
  bg: '#0B0B0D',        // page
  bgWarm: '#1A1511',    // centre of the backdrop gradient (the light pool)
  bgMid: '#0F0E10',     // backdrop gradient, middle stop
  bgEdge: '#0B0B0D',    // backdrop gradient, edge
  panel: '#15141A',     // cards, nodes, cells
  panelHi: '#1E1C22',   // raised panel / gradient top
  ink: '#F2EDE4',       // primary text
  muted: '#B3ADA2',     // secondary text: 8.8:1 on bg, 7.3:1 in the light pool (thin 30 px strokes measure ~30% lower)
  dim: '#4A463F',       // idle strokes and tracks only: never text (2:1)
  line: '#2C2A27',      // hairlines, card borders
  edge: '#6B665E',      // idle graph edges
  acc: '#FF5B2E',       // signal orange: the thing being looked at (shapes, fills, big type)
  accText: '#FF8A5C',   // the accent for text under 40 px (6.4:1 on bg is not enough for thin small strokes)
  accSoft: 'rgba(255,91,46,0.16)',
  mint: '#7BE3B5',      // valid / answer
  mintSoft: 'rgba(123,227,181,0.14)',
  rose: '#FF4F6E',      // illegal / wrong
  gold: '#FFC94A',      // comic bursts, stars
  sky: '#7CC4FF',       // a cool second accent (sparingly: think timers, "old" values)
  shadow: 'rgba(0,0,0,0.55)',
  // surfaces (each holds text)
  card: 'rgba(22,21,27,0.94)',      // question cards
  cardSoft: 'rgba(22,21,27,0.9)',   // readouts in the scenes
  row: 'rgba(23,22,28,0.92)',       // complexity ladder rows
  strip: 'rgba(20,19,24,0.92)',     // lower third body
  pill: 'rgba(24,23,28,0.95)',      // flying copies
  cell: '#17161B',                  // table cells
  tag: '#18171C',                   // weight tags and value chips on the graph
  code: 'rgba(17,16,21,0.96)',      // code panel
  codeHead: 'rgba(255,255,255,0.03)',
  track: 'rgba(255,255,255,0.06)',  // empty bar tracks
  discTop: '#2A2730',               // graph node disc gradient
  discBottom: '#131217',
  // light and effects
  tokenCore: '#FFF6EE',             // hot core of the travelling token
  pulse: '#FFF4E8',                 // the pulse that runs along a firing edge
  halftone: 'rgba(0,0,0,0.22)',     // comic dots on chapter cards
  burstLine: '#140A05',             // comic burst outline
  captionShadow: 'rgba(0,0,0,0.8)', // behind caption text
  textShadow: 'rgba(0,0,0,0.5)',    // under headlines
};
export type Palette = typeof ORIGINAL;

/** Texture settings (kit/textures.ts, kit/stage.ts). */
const ORIGINAL_TEX = {
  poolRgb: ['255,91,46'],           // light pool colour(s): one per chapter when themed (the theme's `lights`)
  poolAlpha: [0.13, 0.05] as [number, number],
  vignetteRgb: '0,0,0', vignette: 0.62,
  scrimRgb: '7,7,9', scrimAlpha: [0.72, 0.9] as [number, number],
  dotRgb: '255,255,255', dotsOpacity: 0.07,
  grainLight: true,                 // light specks too (screen-like on dark); light themes use dark specks only
  grainRgb: '0,0,0', grainOpacity: 0.4,
};
export type TextureSettings = typeof ORIGINAL_TEX;

/** The code panel's syntax colours (inks, never fills) and its chrome. */
const ORIGINAL_CODE = {
  kw: '#FF8A5C',      // keywords
  type: '#7CC4FF',    // types
  num: '#7BE3B5',     // numbers
  str: '#FFC94A',     // strings
  com: '#A9A296',     // comments (7.5:1 on the panel; quieter than code, still readable)
  fn: '#FFD27A',      // function names
  punct: '#B3ACA0',   // operators and brackets
  id: ORIGINAL.ink,   // identifiers
  gutter: '#A39D92',  // line numbers
  dimToward: '#A39D92', // context lines move 60% toward this grey (every token stays >= 7:1)
  dots: ['#FF5F57', '#FEBC2E', '#28C840'],
};

// ---------------------------------------------------------------- theme mapping
const lighter = (a: string, b: string) => (lum(a) >= lum(b) ? a : b);

// The registry solves each hue ink to 4.6:1 on flat surfaces. Thin 30-32 px mono labels in a hue, drawn at the
// sub-pixel offsets of the drifting stage, measured 3.8:1 in the stills on a light ground (4.3:1 at 5.5:1 flat):
// anti-aliasing eats the stroke cores. So the kit sets hue text further from the ground: same hue and saturation,
// lightness moved until it clears the target on every surface (6.3:1 on light grounds, 5.5:1 on dark ones).
const INK_TARGET = {light: 6.3, dark: 5.5};
const toHsl = (c: string) => {
  const [r, g, b] = hx(c).map(v => v / 255), mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2;
  if (mx === mn) return [0, 0, l];
  const d = mx - mn, s = l > 0.5 ? d / (2 - mx - mn) : d / (mx + mn);
  const h = mx === r ? (g - b) / d + (g < b ? 6 : 0) : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [h / 6, s, l];
};
const fromHsl = (h: number, s: number, l: number) => {
  const f = (n: number) => {
    const k = (n + h * 12) % 12, a = s * Math.min(l, 1 - l);
    return Math.round(255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)))).toString(16).padStart(2, '0');
  };
  return '#' + f(0) + f(8) + f(4);
};
function deepen(T: ThemeTokens, c: string, target = INK_TARGET[T.tone]) {
  const grounds = [T.bg, T.bg2, T.deep, T.panel, T.panel2];
  const ok = (x: string) => Math.min(...grounds.map(g => contrast(x, g))) >= target;
  if (ok(c)) return c;
  const [h, s, l0] = toHsl(c), dir = T.tone === 'light' ? -1 : 1;
  for (let l = l0; l >= 0 && l <= 1; l += dir * 0.01) {
    const x = fromHsl(h, s, l);
    if (ok(x)) return x;
  }
  return T.text;
}
const darker = (a: string, b: string) => (lum(a) >= lum(b) ? b : a);

function themed(T: ThemeTokens): Palette {
  const L = T.tone === 'light';
  return {
    bg: T.bg,
    bgWarm: lighter(T.bg, T.bg2), bgMid: mix(T.bg, T.bg2, 0.5), bgEdge: darker(T.bg, T.bg2),
    panel: T.panel, panelHi: T.panel2,
    ink: T.text, muted: T.muted,
    dim: T.line2,                        // idle tracks and strokes (not text)
    line: L ? T.line2 : T.line,          // card borders: light grounds need the stronger line to show an edge
    edge: T.dim,                         // idle graph edges
    acc: T.accent, accText: deepen(T, T.accentInk), accSoft: alpha(T.accent, L ? 0.14 : 0.16),
    mint: T.good, mintSoft: alpha(T.good, 0.14),
    rose: T.bad, gold: T.gold, sky: T.cool,
    shadow: alpha(T.shadow, L ? 0.2 : 0.55),
    card: T.panel, cardSoft: T.panel, row: T.panel, strip: T.panel, pill: T.panel,
    cell: T.panel, tag: T.panel, code: T.panel,
    codeHead: alpha(T.text, 0.04), track: alpha(T.text, L ? 0.1 : 0.08),
    discTop: lighter(T.panel, T.panel2), discBottom: darker(T.panel, T.panel2),
    tokenCore: L ? T.bg : T.text,
    pulse: T.text,                       // dark themes: a hot streak; light themes use the firing hue (hot())
    halftone: alpha(T.shadow, 0.22),
    burstLine: T.shadow,
    captionShadow: L ? alpha(T.bg, 0.9) : alpha(T.shadow, 0.8),   // a light halo behind dark text on light grounds
    textShadow: L ? alpha(T.shadow, 0.14) : alpha(T.shadow, 0.5),
  };
}
function themedTex(T: ThemeTokens): TextureSettings {
  const L = T.tone === 'light';
  return {
    poolRgb: T.lights.map(rgbOf),
    poolAlpha: L ? [0.08, 0.03] : [0.13, 0.05],   // light grounds: a faint tint, not a glow
    vignetteRgb: rgbOf(T.deep), vignette: L ? 0.85 : 0.62,
    scrimRgb: rgbOf(T.deep), scrimAlpha: [0.72, 0.9],
    dotRgb: rgbOf(T.text), dotsOpacity: L ? 0.09 : 0.07,
    grainLight: !L, grainRgb: L ? rgbOf(T.shadow) : '0,0,0', grainOpacity: L ? 0.3 : 0.4,
  };
}
function themedCode(T: ThemeTokens) {
  return {
    kw: deepen(T, T.accentInk), type: deepen(T, T.coolInk), num: deepen(T, T.goodInk), str: deepen(T, T.goldInk),
    com: T.muted, fn: deepen(T, T.warmInk),
    punct: T.muted, id: T.text, gutter: T.dim, dimToward: T.muted, dots: [T.bad, T.gold, T.good],
  };
}

export const C: Palette = THEME ? themed(THEME) : ORIGINAL;
export const TEX: TextureSettings = THEME ? themedTex(THEME) : ORIGINAL_TEX;
export const CODE: typeof ORIGINAL_CODE = THEME ? themedCode(THEME) : ORIGINAL_CODE;

// hue fill -> its text ink and its on-fill label colour (themes only)
const HUES = ['accent', 'warm', 'good', 'bad', 'cool', 'gold', 'violet'] as const;
const INK = new Map<string, string>();
const ON = new Map<string, string>();
if (THEME) {
  for (const h of HUES) {
    const fill = THEME[h], k = h as string;
    if (!INK.has(fill)) INK.set(fill, deepen(THEME, (THEME as any)[`${k}Ink`]));
    if (!ON.has(fill)) ON.set(fill, (THEME as any)[`on${k[0].toUpperCase()}${k.slice(1)}`]);
  }
  INK.set(THEME.text, THEME.text);
  INK.set(THEME.muted, THEME.muted);
  INK.set(THEME.dim, THEME.dim);
}

/** The colour to set small text in when it is meant to read as `c` (the orange accent gets its lighter text tone). */
export const inkOf = (c: string) => (THEME ? INK.get(c) ?? c : c === C.acc ? C.accText : c);
/** Text in hue `c` at any size: the original palette uses the fill itself; a theme uses the hue's solved ink. */
export const textOf = (c: string) => (THEME ? INK.get(c) ?? c : c);
/** Label colour on a filled shape of hue `c` (badges, pills, the chapter wipe). */
export const onOf = (c: string) => {
  if (!THEME) return C.bg;
  const on = ON.get(c);
  if (on) return on;
  return contrast('#111111', c) >= contrast('#FFFFFF', c) ? '#111111' : '#FFFFFF';
};
/** A line or a small shape in hue `c`: the fill, or its ink when the fill is under 3:1 on the ground (themes). */
export const lineOf = (c: string) => {
  if (!THEME || !INK.has(c)) return c;
  return Math.min(contrast(c, C.bgWarm), contrast(c, C.bgEdge)) >= 3 ? c : INK.get(c)!;
};
/** shadowColor for a glow in hue `c`: the hue on dark grounds, a soft shadow on light ones (a glow there is a smudge). */
export const glow = (c: string) => (THEME && LIGHT ? alpha(THEME.shadow, 0.22) : c);
/** A drop shadow at strength `a` (black on dark grounds; a light theme's shadow tint, much softer). */
export const drop = (a: number) => (THEME ? alpha(THEME.shadow, LIGHT ? +(a * 0.35).toFixed(3) : a) : `rgba(0,0,0,${a})`);
/** The streak colour of a pulse firing in hue `c` (white-hot on dark grounds, the hue's line colour on light ones). */
export const hot = (c: string) => (THEME && LIGHT ? lineOf(c) : C.pulse);
/** The word colour of a comic burst filled with `c`. */
export const burstInkOf = (c: string) => (THEME ? onOf(c) : '#1A0E08');

/**
 * The chapter wipe for chapter n: its fill, a darker back strip and the label colour on it (dots: C.halftone).
 * Original: the orange wipe. A theme: the chapter's key light (`lights[(n - 1) % 6]`) with its on-fill colour.
 */
export function wipeOf(n: number) {
  if (!THEME) return {fill: C.acc, back: '#B83A16', ink: C.bg};
  const fill = THEME.lights[(Math.max(1, n) - 1) % THEME.lights.length];
  return {fill, back: mix(fill, THEME.shadow, 0.35), ink: onOf(fill)};
}
/** The light pool's colour index for chapter n (one key light per chapter, as the wipe). */
export const lightIndexOf = (n: number) => (THEME ? (Math.max(1, n) - 1) % TEX.poolRgb.length : 0);

// Fonts are loaded locally in project.ts (@fontsource) and awaited before the first frame.
// Display falls back to Inter where the system has no Inter Display (laptops).
export const F = {
  display: '"Inter Display", "Inter", sans-serif',
  text: '"Inter", sans-serif',
  mono: '"JetBrains Mono", monospace',
  comic: '"Bangers", "Inter Display", sans-serif',
};

// Sizes at 1080p (quality-bar.md): nothing under 26 px. The legibility check measures each text in the stills
// (within about 5%), so the smallest sizes sit a step above the floor: 30 px labels, 32 px tags.
export const S = {
  hero: 132,       // title card headline
  h1: 96,          // chapter card title
  h2: 64,          // big statements ("k = 1", "700.")
  h3: 52,          // question text
  body: 40,        // labels on the subject
  caption: 40,     // caption band
  code: 30,        // code panel (30-36)
  small: 32,       // tags, weights, chips, table labels
  tiny: 30,        // HUD, kickers, badges, column heads (the smallest size the kit uses)
};

// Layout: everything is designed in a 1920x1080 space centred on (0, 0).
export const W = 1920;
export const H = 1080;
export const SAFE = 96;                 // keep text this far from every edge
export const CAPTION_BAND = 180;        // bottom band reserved for captions
export const STAGE_BOTTOM = H / 2 - CAPTION_BAND - 16;  // lowest y the subject may use (= 344)
export const STAGE_TOP = -H / 2 + SAFE + 40;            // below the HUD (= -404)

// Motion defaults (seconds).
export const T = {
  enter: 0.5,
  exit: 0.3,
  stagger: 0.08,
  hold: 1.0,
};
