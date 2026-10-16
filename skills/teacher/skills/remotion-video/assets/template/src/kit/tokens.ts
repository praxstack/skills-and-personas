// Style tokens: the one place for palette, type and layout constants. Change the look here, not in scenes.
// Recipe: "dark editorial" (references/quality-bar.md) with a comic accent: near-black stage with grain and
// warm/cool light, one signal accent for the thing being looked at, mint = valid/answer, rose = illegal/wrong.
//
// Themes (references/themes.md): `./theme.ts` is either the shipped stub (THEME = null: the original palette below,
// unchanged) or a file emitted by `theme.py emit <id> --format ts --out source/src/kit/theme.ts`. With a theme, every
// role below is mapped onto the theme's tokens; kit code and scenes read only these names, never a hex value.
//   fills (areas, thick strokes):        C.accent C.amber C.mint C.rose C.cyan C.violet C.burst
//   text in a hue:                       ink(fill)    (theme <hue>Ink, firmed to 5.3:1; original: the fill itself)
//   text on a filled shape of that hue:  on(fill)     (theme on<Hue>; original: C.bg)
//   a line or shape that must show on the ground (3:1 against bg): mark(fill)
import {THEME} from './theme';
import {alpha, contrast, fit, mix} from './color';

type Theme = Record<string, string> & {id: string; tone: string; lights: readonly string[]};
const T = (THEME as unknown as Theme | null) ?? null;
/** the theme id the film is drawn in ('original' = the kit's own palette) */
export const THEME_ID = T ? T.id : 'original';
export const THEMED = T != null;
/** light ground: grain multiplies, glows become soft shadows, the vignette is a gentle `deep` edge */
export const LIGHT = T != null && T.tone === 'light';

const ORIGINAL = {
  bg: '#0B0B0D', // stage
  bgLift: '#15171D', // centre of the stage gradient
  ink: '#F2EDE4', // main text
  muted: '#A8A297', // secondary text (7:1 on bg, about 6.5:1 on panels)
  faint: '#9A958B', // tertiary: line numbers, used entries (still >= 5:1 on panels; dimmer than muted, never invisible)
  line: 'rgba(242,237,228,0.10)',
  line2: 'rgba(242,237,228,0.20)',
  panel: 'rgba(24,25,31,0.94)',
  panelTop: 'rgba(36,37,45,0.96)',

  accent: '#FF5B2E', // signal orange: the thing being looked at
  accentText: '#FF8F6B', // the accent for small text on an accent-tinted fill (6:1 there; plain accent is 4.5:1)
  amber: '#FFB547', // numbers, prices (luminance 0.55)
  amberHi: '#FFD27A', // highlight outline and tint behind active text (luminance 0.69): the decoder's active entry
  mint: '#7BE3B5', // valid, answer
  rose: '#FF4F6E', // illegal, wrong, rejected
  cyan: '#5CC8FF', // cool accent: start, "old" values
  violet: '#B79BFF', // code keywords
  burst: '#FFD23F', // comic callout fill
};
type Palette = {[K in keyof typeof ORIGINAL]: string};

// The kit asks a little more than theme.py's flat-surface targets (muted 5.5, dim and inks 4.6): thin glyphs, a
// spring scale or a tint behind the text measure 10-25% lower in the stills. Same hue, lightness moved (fit).
const SURF = T ? [T.bg, T.bg2, T.deep, T.panel, T.panel2] : [];
const MARGIN = {muted: 6.2, dim: 5.3, ink: 5.3};
const firm = (c: string, target: number) => fit(c, SURF, target);

export const C: Palette = T
  ? {
      bg: T.bg, bgLift: T.bg2, ink: T.text, muted: firm(T.muted, MARGIN.muted), faint: firm(T.dim, MARGIN.dim), line: T.line, line2: T.line2, panel: T.panel, panelTop: T.panel2,
      accent: T.accent, accentText: firm(T.accentInk, MARGIN.ink), amber: T.gold, amberHi: T.gold, mint: T.good, rose: T.bad, cyan: T.cool, violet: T.violet, burst: T.gold,
    }
  : ORIGINAL;

// fill -> ink / on-fill lookups (theme only; the original palette uses its fills as text and C.bg on fills)
const HUES = ['accent', 'warm', 'good', 'bad', 'cool', 'gold', 'violet'];
const key = (c: string) => c.trim().toUpperCase();
const INK = new Map<string, string>();
const ON = new Map<string, string>();
if (T) {
  for (const h of HUES) {
    const cap = h[0].toUpperCase() + h.slice(1);
    if (!INK.has(key(T[h]))) INK.set(key(T[h]), firm(T[h + 'Ink'], MARGIN.ink));
    if (!ON.has(key(T[h]))) ON.set(key(T[h]), T['on' + cap]);
  }
  for (const c of [T.text, C.muted, C.faint, C.accentText]) INK.set(key(c), c);
}
/** the colour for text (or a thin stroke) in this hue */
export const ink = (fill: string) => (T ? INK.get(key(fill)) ?? fill : fill);
/** the colour for text sitting on a filled shape of this hue */
export const on = (fill: string) => {
  if (!T) return ORIGINAL.bg;
  const o = ON.get(key(fill));
  if (o) return o;
  return contrast(T.text, fill) >= contrast(T.bg, fill) ? T.text : T.bg;
};
/** a line, ring or arrow in this hue that holds 3:1 against the ground (light themes darken pale fills) */
export const mark = (fill: string) => (T ? fit(fill, [T.bg, T.bg2], 3) : fill);
/** text colour `c` lifted until it clears 4.6:1 on a tinted surface (theme only: the solved inks have no margin for
 *  tints; the original palette was checked as it is) */
/** the outline of a highlight box drawn tight around text */
export const hlEdge = (c: string) => (S.edgeA >= 1 ? c : alpha(mark(c), S.edgeA));
export const inkOn = (c: string, surface: string | string[], target = MARGIN.ink) => (T ? fit(c, surface, target) : c);
/** a soft shadow colour at alpha a (light themes: a tint of the text colour, much lighter) */
export const sh = (a: number) => (T ? alpha(T.shadow, LIGHT ? a * 0.3 : a) : `rgba(0,0,0,${a})`);
/** glow strength multiplier for SVG blurs and coloured halos (a glow on a light ground reads as a smudge) */
export const GLOW_K = LIGHT ? 0.3 : 1;

// Surfaces and furniture that are not one of C's roles. Original values are the verified starter look.
const SO = {
  glass: 'rgba(14,14,17,0.82)', // chapter tag box
  card: 'rgba(16,17,21,0.93)', // fare card
  rung: 'rgba(24,25,31,0.93)', // ladder rung
  rungOn: 'rgba(24,25,31,0.96)', // ladder rung in focus (behind the tint)
  codeTop: 'rgba(30,31,38,0.97)', codeBot: 'rgba(17,18,22,0.97)', // code panel
  recapTop: 'rgba(36,37,45,0.96)', recapBot: 'rgba(20,21,26,0.96)', // recap card
  qTop: 'rgba(40,36,34,0.95)', qBot: 'rgba(22,22,26,0.95)', // question card
  pill: '#101116', // edge weight tag
  valuePill: '#0E0F13', // node value pill
  nodeHi: '#3A3D48', nodeMid: '#20222A', nodeLo: '#121318', // graph node body
  treeLo: '#15161B', // tree node body (from nodeHi)
  well: 'rgba(0,0,0,0.35)', // countdown ring's inside
  floor: '#000', // floor shadow under graph nodes
  floorO: 0.7,
  spec: '#FFFFFF', // specular highlight on nodes
  spark: '#FFFFFF', // the bright head of an edge pulse
  plane: '#FFFFFF', // the plane token
  dust: '#FFE2C8',
  dotGrid: 'rgba(242,237,228,0.11)',
  horizon: 'linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0))',
  vignette: 'radial-gradient(ellipse 75% 70% at 50% 46%, rgba(0,0,0,0) 55%, rgba(0,0,0,0.62) 100%)', // over everything
  groundVignette: 'none', // the same, drawn on the ground under the subject and the HUD
  grain: 0.09, grainBlend: 'overlay', grainFilter: 'none',
  capBand: 'linear-gradient(180deg, rgba(8,8,10,0) 0%, rgba(8,8,10,0.78) 38%, rgba(8,8,10,0.92) 100%)',
  capHalo: '0 2px 12px rgba(0,0,0,0.9)',
  stingDim: 'rgba(5,5,7,0.3)',
  stingMid: '#FF8A3D', // middle of the sting band's gradient (accent -> this -> burst)
  stingDots: 'rgba(11,11,13,0.22)', stingStreak: 'rgba(255,255,255,0.45)',
  stingText: ORIGINAL.bg, stingShadow: ORIGINAL.ink,
  burstLine: ORIGINAL.bg, burstText: ORIGINAL.ink, // comic burst outline and lettering
  hi: 'rgba(255,255,255,0.07)', // inset top highlight on cards
  hiSoft: 'rgba(255,255,255,0.03)', // the same on table cells
  dots: ['#FF5F57', '#FEBC2E', '#28C840'], // window dots
  tree: ORIGINAL.ink, // tree edges and rails: this colour at low alpha
  edgeA: 1, // alpha of the outline round a highlight that sits right around text (decoder entry, code pulse)
  pulseA: '44', // hex alpha of a code line's pulse flash
  hlGlow: 'AA', // hex alpha of the glow round a decoder highlight (they stack when several entries are lit)
  tagH: 1.45, // edge weight tag height in em: the pill's outline must clear the text's measuring box
  title: '0 10px 40px rgba(0,0,0,0.6)', // title word shadow
};

const themed = (t: Theme): typeof SO => {
  const dark = !LIGHT;
  // the sting band: accent -> warm -> gold when one text colour clears 4.6:1 on all of it, else accent only
  const stops = [t.accent, t.warm, mix(t.warm, t.gold, 0.3)];
  const cands = [t.onAccent, t.text, t.bg, '#111111', '#FFFFFF'];
  const best = cands.map((c) => [c, Math.min(...stops.map((s) => contrast(c, s)))] as [string, number]).sort((a, b) => b[1] - a[1])[0];
  const band = best[1] >= 4.6 ? {mid: t.warm, end: t.gold, text: best[0]} : {mid: t.accent, end: t.accent, text: t.onAccent};
  return {
    glass: t.panel, card: t.panel, rung: t.panel, rungOn: t.panel,
    codeTop: t.panel2, codeBot: t.panel, recapTop: t.panel2, recapBot: t.panel, qTop: t.panel2, qBot: t.panel,
    pill: t.panel, valuePill: t.panel,
    nodeHi: dark ? t.panel2 : t.bg, nodeMid: dark ? t.panel : t.panel, nodeLo: dark ? t.deep : t.panel2, treeLo: dark ? t.deep : t.panel2,
    well: dark ? alpha(t.deep, 0.6) : t.panel,
    floor: t.shadow, floorO: dark ? 0.7 : 0.22,
    spec: '#FFFFFF', spark: dark ? t.text : '#FFFFFF', plane: dark ? t.text : t.text,
    dust: dark ? t.text : t.line2,
    dotGrid: alpha(t.text, dark ? 0.11 : 0.09),
    horizon: dark ? SO.horizon : `linear-gradient(180deg, ${alpha(t.shadow, 0.025)}, ${alpha(t.shadow, 0)})`,
    // under a theme the vignette darkens the ground only: drawn over the text it washed the solved inks out by up to 25%
    vignette: 'none',
    groundVignette: `radial-gradient(ellipse 75% 70% at 50% 46%, ${alpha(t.deep, 0)} 55%, ${alpha(t.deep, dark ? 0.75 : 0.9)} 100%)`,
    grain: dark ? 0.09 : 0.07, grainBlend: dark ? 'overlay' : 'multiply', grainFilter: dark ? 'none' : 'brightness(1.75)',
    capBand: `linear-gradient(180deg, ${alpha(t.deep, 0)} 0%, ${alpha(t.deep, 0.78)} 38%, ${alpha(t.deep, 0.92)} 100%)`,
    capHalo: dark ? `0 2px 12px ${alpha(t.shadow, 0.9)}` : `0 1px 10px ${alpha(t.bg, 0.9)}`,
    stingDim: alpha(t.deep, 0.3),
    stingMid: band.mid,
    stingDots: alpha(band.text, 0.16), stingStreak: alpha(contrast('#FFFFFF', t.accent) > contrast('#000000', t.accent) ? '#FFFFFF' : t.shadow, 0.3),
    stingText: band.text, stingShadow: alpha(lumLight(band.text) ? t.shadow : '#FFFFFF', 0.5),
    burstLine: dark ? t.bg : t.text, burstText: dark ? t.text : t.bg,
    hi: dark ? 'rgba(255,255,255,0.07)' : 'rgba(255,255,255,0.5)',
    hiSoft: dark ? 'rgba(255,255,255,0.03)' : 'rgba(255,255,255,0.35)',
    dots: [t.bad, t.gold, t.good],
    tree: t.text,
    edgeA: 0, // tint only: an outline hugging the glyphs is read as the text's ground in the stills (fails 4.5:1)
    pulseA: '22', // a mid-tone flash leaves no text colour at 4.5:1 (neither light nor dark ink clears it)
    hlGlow: '00', // stacked glows lifted the ground between the decoder rows to under 4.5:1
    tagH: 1.75,
    title: dark ? `0 10px 40px ${alpha(t.shadow, 0.6)}` : `0 8px 30px ${alpha(t.shadow, 0.12)}`,
  };
};
const lumLight = (c: string) => contrast(c, '#000000') > contrast(c, '#FFFFFF');
export const S: typeof SO = T ? themed(T) : SO;
/** the sting band's end colour (the burst yellow in the original) */
export const STING_END = T ? (S.stingMid === T.accent ? T.accent : T.gold) : ORIGINAL.burst;

/** chapter key lights for the backdrop: [warm, cool] for chapter n (original: accent and cyan throughout) */
export const keyLights = (n: number): [string, string] => {
  if (!T) return [C.accent, C.cyan];
  const L = T.lights;
  const soft = (c: string) => (LIGHT ? mix(c, '#FFFFFF', 0.55) : c);
  return [soft(L[(Math.max(0, n) + L.length - 1) % L.length]), soft(L[(Math.max(0, n) + 2) % L.length])];
};

// Code syntax colours: inks, never fills (every one >= 4.5:1 on the code panel; the original's also on a dimmed line)
export const CODE_INK = T
  ? {kw: ink(T.violet), type: ink(T.cool), num: ink(T.gold), com: C.faint, fn: ink(T.good), txt: T.text, punct: C.muted, str: ink(T.warm)}
  : {kw: ORIGINAL.violet, type: ORIGINAL.cyan, num: ORIGINAL.amber, com: '#B0A99C', fn: ORIGINAL.mint, txt: '#E9E4DA', punct: '#B3AEA3', str: '#F4A99A'};
/** opacity of code lines outside the active range: the theme inks hold 4.6:1 only at full strength */
export const CODE_DIM_OPACITY = T ? 1 : 0.8;

export const FONT = {
  sans: '"Inter", "DejaVu Sans", sans-serif',
  serif: '"Instrument Serif", "DejaVu Serif", serif',
  mono: '"JetBrains Mono", "DejaVu Sans Mono", monospace',
  comic: '"Bangers", "Inter", sans-serif',
};

// Sizes at 1080p (quality bar: headline 72-96, body 40-48, captions 38-44, code 30-36, nothing under 26).
// `small` is the smallest size the kit draws (labels, chips, table headers, weight tags): 30 px on screen leaves
// room for a camera pull-back and the 4% tolerance of legibility.py above the 26 px floor. Lowercase-only words
// read smaller than their font size (x-height), so short labels are set in caps (Label) or at 32 px and up.
export const SIZE = {
  title: 128,
  headline: 84,
  body: 44,
  caption: 40,
  code: 30,
  label: 30,
  small: 30,
  min: 26,
};

// Layout: no text closer than 96 px to any edge. Top HUD row (chapter tag, progress): box from y 88, its text from
// y 100; caption band = the bottom 180 px, caption text bottom-anchored just above y 984 (96 px above the bottom edge).
// Keep subjects inside STAGE.
export const SAFE = {x: 96, top: 96, captionTop: 900, bottom: 984};
export const STAGE = {x0: 96, y0: 150, x1: 1824, y1: 880};

// Ligatures off for every glyph on screen ("!=" must never become a single glyph).
export const NO_LIGA = '"calt" 0, "liga" 0, "dlig" 0';

// Monospace metrics (JetBrains Mono advance = 0.6 em). Used to place tokens without measuring the DOM.
export const MONO_ADVANCE = 0.6;

export const SHADOW = T
  ? {
      card: `0 30px 80px -24px ${sh(0.85)}, 0 10px 24px -12px ${sh(0.6)}, inset 0 1px 0 ${S.hi}`,
      lift: `0 18px 40px -16px ${sh(0.8)}`,
    }
  : {
      card: '0 30px 80px -24px rgba(0,0,0,0.85), 0 10px 24px -12px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.07)',
      lift: '0 18px 40px -16px rgba(0,0,0,0.8)',
    };

/** a coloured glow as a CSS shadow (box-shadow, or text-shadow without `spread`). On a light theme it becomes a soft
 *  shadow tinted toward the colour, since a glow on a light ground reads as a smudge. `a` is a hex alpha suffix. */
export const halo = (color: string, blur: number, spread?: number, a = '') => {
  if (!LIGHT || !T) return `0 0 ${blur}px${spread != null ? ` ${spread}px` : ''} ${color}${a}`;
  const k = a ? parseInt(a, 16) / 255 : 1;
  return `0 ${Math.round(blur * 0.22)}px ${Math.round(blur * 0.8)}px${spread != null ? ` ${spread}px` : ''} ${alpha(mix(color, T.shadow, 0.45), 0.3 * k)}`;
};
export const glow = (color: string, r = 28, a = '66') => halo(color, r, undefined, a);
