// Style tokens: the only place colours, fonts and sizes live. A new film changes this file, not the kit.
// Colours come from src/theme-film.ts when it holds a registry theme (theme.py emit ... --format ts), else
// from ORIGINAL below, unchanged. Scenes and kit pieces use C, inkOf(), onFill(), glow(), shade() only.
// Recipe: "dark editorial" (references/quality-bar.md): near-black ground with warm light, one warm accent
// for the thing being looked at, mint for valid / the answer, rose for illegal / wrong, a cool blue for
// secondary information. Inter for words, JetBrains Mono (ligatures off) for code and numbers, Bangers for
// comic callouts only.
import {LezerHighlighter} from '@motion-canvas/2d';
import {HighlightStyle} from '@codemirror/language';
import {tags as t} from '@lezer/highlight';
import {parser as cppParser} from '@lezer/cpp';

import {THEME as FILM_THEME} from '../theme-film';

/** The registry tokens theme.py emits (references/themes.md). */
export interface ThemeTokens {
  id: string;
  name: string;
  tone: 'light' | 'dark';
  bg: string; bg2: string; deep: string; panel: string; panel2: string; line: string; line2: string;
  text: string; muted: string; dim: string;
  accent: string; warm: string; good: string; bad: string; cool: string; gold: string; violet: string;
  accentInk: string; warmInk: string; goodInk: string; badInk: string; coolInk: string; goldInk: string; violetInk: string;
  onAccent: string; onWarm: string; onGood: string; onBad: string; onCool: string; onGold: string; onViolet: string;
  lights: readonly string[];
  shadow: string;
}

/** The film's theme (src/theme-film.ts), or null for `original`: the palette below, exactly as shipped. */
export const THEME = FILM_THEME as unknown as ThemeTokens | null;
/** true on a light theme: glows turn into soft shadows, grain multiplies, the vignette is a gentle `deep` edge */
export const LIGHT = THEME?.tone === 'light';

/** Mix two #rrggbb colours: k = 0 gives a, 1 gives b. */
export function mix(a: string, b: string, k: number) {
  const ch = (s: string, i: number) => parseInt(s.slice(1 + i, 3 + i), 16);
  return '#' + [0, 2, 4].map(i => Math.round(ch(a, i) + (ch(b, i) - ch(a, i)) * k).toString(16).padStart(2, '0')).join('').toUpperCase();
}

// The shipped palette ("original"). Every colour the kit draws is one of these roles.
const ORIGINAL = {
  bg: '#0B0B0D', // ground
  bgGlow: '#241C16', // warm light behind the subject
  bgCool: '#111B2A', // cool light in the far corner
  bgCorner: '#151019', // a little colour in the bottom-left corner
  grid: '#2D2925', // backdrop dots
  panel: '#151519', // cards and panels
  panelHi: '#1F1E25', // top of a panel's gradient
  cell: '#1B1A20', // table cells
  line: '#2E2C34', // borders, idle edges
  border: '#34323C', // panel and cell outlines
  stroke: '#3A3843', // node rings, pill and chip outlines
  hair: '#2A2930', // receded outlines, the code panel's title rule
  edge: '#55525C', // idle graph edges
  nodeHi: '#2C2A33', // node disc, lit side
  nodeLo: '#121116', // node disc, far side
  pill: '#17161B', // edge weight pills
  shade: '#050507', // under the captions
  shadow: '#000000', // drop shadows
  ink: '#F2EDE4', // primary text
  muted: '#A39E96', // secondary text (6.5:1 on the panels; the darkest colour text may use)
  dim: '#6B6760', // idle strokes and decoration only: 3:1, too faint for text (quality bar: 4.5:1)
  accent: '#FF5B2E', // signal orange: the thing being looked at
  accent2: '#FF8A5C', // a lighter orange (the brute-force fan's middle level, C++ keywords)
  good: '#7BE3B5', // mint: valid, the answer
  bad: '#FF4F6E', // rose: illegal, wrong
  cool: '#6FB7FF', // secondary info (src, reads)
  gold: '#FFC94A', // comic burst fill, the interview pick
  black: '#000000',
  // chapter card: a deep burnt-orange band (white title text reads at 5.9:1 or more across it)
  cardA: '#B23A12',
  cardB: '#9A2F0E',
  cardC: '#7C230A',
  cardInk: '#FFF4EC',
  burstInk: '#1A1206', // lettering on the gold burst
  burstLine: '#14100A', // the burst's outline
  fanInk: '#1A0E08', // the label on the brute-force fan's root
  // code panel
  winRed: '#FF5F57',
  winAmber: '#FEBC2E',
  winGreen: '#28C840',
  recede: '#938E86', // the grey unfocused code recedes to (5.1:1 on the panel by itself)
  codeKeyword: '#FF8A5C',
  codeType: '#6FB7FF',
  codeNumber: '#FFC94A',
  codeComment: '#A8A196', // 6.9:1 on the code panel
  codeFunction: '#7BE3B5',
  codeOperator: '#BDB6AA',
  codeVariable: '#F2EDE4',
  codeString: '#E6C07B',
};
export type Palette = typeof ORIGINAL;

/** Map the registry tokens onto the kit's roles. Fills stay fills; text roles get the solved inks. */
function themed(t: ThemeTokens): Palette {
  const L = t.tone === 'light';
  // code inks: the solved 4.6:1 loses about a tenth under the active-line bar (accent at 13%), so they move
  // towards text until they keep 5.4:1 on the panel and on the bar
  const bar = mix(t.panel, t.accent, 0.13);
  const code = (c: string) => {
    let k = 0, x = c;
    while (k < 0.6 && (contrast(x, t.panel) < 5.4 || contrast(x, bar) < 5.4)) { k += 0.04; x = mix(c, t.text, k); }
    return x;
  };
  return {
    bg: t.bg,
    bgGlow: mix(t.bg, t.lights[0] ?? t.warm, L ? 0.07 : 0.13),
    bgCool: mix(t.bg2, t.cool, L ? 0.05 : 0.1),
    bgCorner: mix(t.bg2, t.violet, L ? 0.04 : 0.08),
    grid: L ? mix(t.line, t.line2, 0.6) : t.line,
    panel: t.panel,
    panelHi: L ? mix(t.panel, t.bg, 0.6) : t.panel2,
    cell: mix(t.panel, t.panel2, 0.5),
    line: t.line,
    border: L ? t.line2 : mix(t.line, t.line2, 0.35),
    stroke: L ? mix(t.line2, t.dim, 0.35) : mix(t.line, t.line2, 0.5),
    hair: t.line,
    edge: L ? mix(t.line2, t.dim, 0.6) : mix(t.line2, t.dim, 0.35),
    nodeHi: L ? mix(t.panel, '#FFFFFF', 0.45) : t.panel2,
    nodeLo: L ? t.panel2 : t.deep,
    pill: t.panel,
    shade: t.deep,
    shadow: t.shadow,
    ink: t.text,
    muted: t.muted,
    dim: t.dim,
    accent: t.accent,
    accent2: t.warm,
    good: t.good,
    bad: t.bad,
    cool: t.cool,
    gold: t.gold,
    black: t.shadow,
    cardA: t.panel2,
    cardB: mix(t.panel, t.panel2, 0.5),
    cardC: t.panel,
    cardInk: t.text,
    burstInk: t.onGold,
    burstLine: L ? t.text : t.shadow,
    fanInk: t.onAccent,
    winRed: t.bad,
    winAmber: t.gold,
    winGreen: t.good,
    recede: t.muted,
    codeKeyword: code(t.accentInk),
    codeType: code(t.coolInk),
    codeNumber: code(t.goldInk),
    codeComment: t.dim,
    codeFunction: code(t.goodInk),
    codeOperator: t.muted,
    codeVariable: t.text,
    codeString: code(t.warmInk),
  };
}

export const C: Palette = THEME ? themed(THEME) : ORIGINAL;

const key = (c: string) => (typeof c === 'string' ? c.slice(0, 7).toUpperCase() : '');
const INK = new Map<string, string>();
const ON = new Map<string, string>();
if (THEME) {
  for (const h of ['accent', 'warm', 'good', 'bad', 'cool', 'gold', 'violet'] as const) {
    const cap = h[0].toUpperCase() + h.slice(1);
    INK.set(key(THEME[h]), (THEME as any)[`${h}Ink`]);
    ON.set(key(THEME[h]), (THEME as any)[`on${cap}`]);
  }
}

/**
 * The colour for text (or a thin stroke) in the hue of fill `color`: the theme's solved ink (`accentInk`, ...).
 * With the original palette the fills are already text-safe on the dark ground, so it returns `color` itself.
 */
export function inkOf(color: string) {
  return INK.get(key(color)) ?? color;
}
/** Text on a filled shape of that hue (`onAccent`, ...); `fallback` is the original palette's choice. */
export function onFill(color: string, fallback: string) {
  return THEME ? (ON.get(key(color)) ?? C.ink) : fallback;
}
/**
 * A coloured glow (shadowColor). On a light theme a glow reads as a smudge, so it becomes a soft shadow.
 * `a` is the glow's alpha (1 = the colour itself).
 */
export function glow(color: string, a = 1) {
  if (LIGHT) return alpha(C.shadow, 0.3 * a);
  return a >= 1 ? color : alpha(color, a);
}
/** A drop shadow at alpha `a` (original: black; light themes: the theme's shadow tint, at about a third). */
export function shade(a: number) {
  return rgba(C.shadow, LIGHT ? Math.round(a * 35) / 100 : a);
}

/**
 * A colour for text drawn on a tint of itself (a chip, a highlighted pill): the colour moved `k` of the way
 * to ink. Orange and rose on their own 14% tint sit near 4.5:1; lifted 25% they read at 5.5:1 or more.
 * With a theme it starts from the hue's solved ink and moves towards `text` (more contrast, same hue).
 */
export function lift(hex: string, k = 0.25) {
  if (!/^#[0-9a-f]{6}/i.test(hex)) return hex; // not a #rrggbb colour: leave it as it is
  // themes: +0.25, since the solved inks sit at 4.6:1 and thin glyphs scaled by the camera lose about a fifth of that
  if (THEME) return mix(inkOf(hex), C.ink, Math.min(1, k + 0.25));
  const a = hex.slice(1, 7);
  const b = C.ink.replace('#', '');
  const ch = (s: string, i: number) => parseInt(s.slice(i, i + 2), 16);
  return '#' + [0, 2, 4].map(i => Math.round(ch(a, i) + (ch(b, i) - ch(a, i)) * k).toString(16).padStart(2, '0')).join('');
}

/** A CSS rgba() string with an exact alpha: rgba('#050507', 0.78) -> 'rgba(5,5,7,0.78)'. */
export function rgba(hex: string, a: number) {
  const ch = (i: number) => parseInt(hex.slice(1 + i, 3 + i), 16);
  return `rgba(${ch(0)},${ch(2)},${ch(4)},${a})`;
}

/**
 * A tint of `color` at strength `a` as a fill. Original: translucent. A theme: opaque (mixed into bg), so the
 * shape's own shadow never shows through and muddies the ground under its text.
 */
export function tint(color: string, a: number) {
  return THEME ? mix(C.bg, color.slice(0, 7), a) : alpha(color, a);
}

/** WCAG contrast ratio of two #rrggbb colours. */
export function contrast(a: string, b: string) {
  const lum = (h: string) => {
    const v = [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16) / 255).map(c => (c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2];
  };
  const x = lum(a), y = lum(b);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}

/**
 * A table cell's tint of `color` under text `ink`. Original: alpha(color, a), as shipped. A theme: opaque (mixed
 * into the cell colour, as tint() does), so the cell's own glow never shows through under its text, and thinned
 * until `ink` keeps 4.7:1 on it (the gate is 4.5:1, measured to about 4%). The answer cell on tokyonight-storm
 * read 4.29:1 with its green glow showing through a 20% tint.
 */
export function underText(color: string, a: number, ink: string = C.ink) {
  if (!THEME || !/^#[0-9a-f]{6}/i.test(color)) return alpha(color, a);
  const c = color.slice(0, 7);
  let k = a;
  while (k > 0.04 && contrast(ink, mix(C.cell, c, k)) < 4.7) k = Math.round((k - 0.02) * 100) / 100;
  return mix(C.cell, c, k);
}

/** Colour with alpha: alpha('#FF5B2E', 0.3) -> '#FF5B2E4D'. */
export function alpha(hex: string, a: number) {
  return hex.slice(0, 7) + Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16).padStart(2, '0');
}

export const F = {
  display: '"Inter Display", Inter, sans-serif', // system Inter Display when present, else Inter 800
  body: 'Inter, sans-serif',
  mono: '"JetBrains Mono", "DejaVu Sans Mono", monospace',
  comic: 'Bangers, Inter, sans-serif',
};

/**
 * Sizes at 1080p (quality-bar.md: headline 72-96, body 40-48, captions 38-44, code 30-36, nothing under 26 px).
 * These are the sizes on screen. Text in the world layer is scaled by the camera zoom, so a label there needs
 * fontSize >= 28 / zoom at the smallest zoom it is shown at (Graph's pills and tags are sized for zoom >= 0.8).
 */
export const S = {
  hero: 120,
  headline: 84,
  title: 56,
  body: 42,
  caption: 40,
  label: 30, // chips, row labels, kickers
  small: 28, // the smallest text anything uses (header, panel titles, notes)
  code: 30,
  mono: 32,
};

/** Frame geometry. The scene's origin (0, 0) is the centre of the frame. */
export const FRAME = {
  w: 1920,
  h: 1080,
  safe: 96, // keep text this far from every edge
  captionBand: 180, // bottom band reserved for captions
  /** centre line of the top chrome (chapter tag, show title): its text starts 96 px below the top edge */
  headerY: -540 + 116,
  /** bottom of the caption text: 96 px above the bottom edge */
  captionBottom: 540 - 96,
  /** usable content area between the top chrome and the caption band, in scene coordinates */
  top: -540 + 160,
  bottom: 540 - 180 - 20,
  left: -960 + 96,
  right: 960 - 96,
};

/** Default motion lengths (seconds). Enter 0.3 to 0.6, exit faster. */
export const M = {
  enter: 0.45,
  exit: 0.3,
  move: 0.9,
  stagger: 0.09,
};

const cppStyle = HighlightStyle.define([
  {tag: [t.keyword, t.controlKeyword, t.modifier, t.definitionKeyword], color: C.codeKeyword},
  {tag: [t.typeName, t.standard(t.typeName)], color: C.codeType},
  {tag: [t.number, t.bool], color: C.codeNumber},
  {tag: t.comment, color: C.codeComment, fontStyle: 'italic'},
  {tag: [t.function(t.variableName), t.function(t.definition(t.variableName))], color: C.codeFunction},
  {tag: [t.operator, t.punctuation, t.bracket, t.separator, t.derefOperator], color: C.codeOperator},
  {tag: [t.variableName, t.definition(t.variableName), t.propertyName], color: C.codeVariable},
  {tag: t.string, color: C.codeString},
]);

/** C++ syntax colours for the Code node (swap the parser for another language: @lezer/python, @lezer/java...). */
export const cpp = new LezerHighlighter(cppParser, cppStyle);
