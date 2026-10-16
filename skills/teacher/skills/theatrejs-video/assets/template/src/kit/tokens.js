// tokens.js: the style in one place. Every colour the kit draws with comes from here: the components read C and
// MOOD, and style.css reads CSS variables that cssVars() builds from C (main.js copies them onto :root).
//
// Themes (references/theatre-guide.md, Themes): src/kit/theme.js is either the shipped stub (THEME = null: the
// kit's own palette below, unchanged) or a registry theme emitted by
//   python3 $S/theme.py emit <id> --format js --out source/src/kit/theme.js
// in which case themed() maps the theme's tokens onto the kit's roles.
import { THEME } from './theme.js';
import { contrast, css, hex, mix } from './util.js';

export const W = 1920, H = 1080;
export const SAFE = 96;          // keep text this far from every edge
export const CAPTION_H = 180;    // bottom band reserved for captions
export const TAG_ZONE = [80, 82, 560, 180]; // the chapter tag (top left, cards.js): R.focus keeps content out of it
export const P = 1200;           // camera focal distance in px (bigger = flatter parallax)

// ------------------------------------------------------------------ the kit's own palette ('original')
const ORIGINAL = {
  // text
  ink: '#F2EDE4',       // main text
  inkDim: '#A9A2C4',    // secondary text
  muted: '#6C658E',     // idle lines, grid
  // fills: shapes, bars, glows (never text)
  accent: '#FF5B2E',    // signal orange: the thing being looked at
  good: '#7BE3B5',      // mint: valid, answer
  bad: '#FF4F6E',       // rose: illegal, wrong
  gold: '#FFD23F',      // comic yellow: labels, bursts
  cool: '#5CE1FF',      // cyan: secondary highlight, rim light
  violet: '#9B7BFF',
  // the same hues as text (the original palette uses the fills; a theme solves inks)
  accentInk: '#FF5B2E', goodInk: '#7BE3B5', badInk: '#FF4F6E', goldInk: '#FFD23F', coolInk: '#5CE1FF', violetInk: '#9B7BFF',
  onGold: '#111',       // labels on gold chips (tags, kicks, sums, the title badge)
  onGood: '#111',       // the ANSWER kick
  labelHot: '#14102a',  // a node label on a hot face (themed: graph.js picks the best of onAccent, onGood, ink)
  // surfaces
  page: '#000', viewport: '#05040f',
  panel: 'rgba(16,11,36,0.86)', panelEdge: 'rgba(255,255,255,0.13)',
  plate: '#0E0A20',     // weight chips and value badges (at 0.94 / 0.95)
  band: '#060412',      // caption band gradient
  chapterBand: '#0E0A24',
  stampBg: '#0A1E16',   // INTERVIEW PICK stamp (at 0.85)
  scrim: '#05040F', scrimK: 1, vignette: '#02010A', vignetteA: 0.62,
  orbK: 1, foreK: 1,    // far glow orbs and foreground bokeh (alpha multipliers)
  titleSub: '#A9A2C4',  // the title card's subtitle (over the sky)
  decBarEdge: '#FF5B2E', // the decoder's row highlight outline
  flashInk: '#7BE3B5',  // a table cell's text while it flashes (mixed from ink)
  flashK: 1,            // how far the flashing cell's tint and glow rise
  ladO: '#5CE1FF',      // the ladder's O(...) columns (rows fade in: themed, the 7:1 text colour)
  skyTop: '#07061A', skyBottom: '#1C1140',
  city: ['#140d30', '#0b0820'], cityFade: '#080616', floorTop: '#0A061C', floorBottom: '#060412',
  // graph
  node: '#2A2152',      // idle node face
  nodeSide: '#151033',
  nodeStroke: '#5b5390',
  edge: '#8D86B5',      // idle edge
  chipStroke: '#3a3260',
  tokenStroke: '#120c2a',
  fire: '#fff', shine: '#fff', glowK: 1,
  cellEdge: '#4a4470',  // table cell border while it flashes
  // comic
  outline: '#000',      // comic outlines and hard offset shadows
  ctNumBg: '#000', ctNumInk: '#FFD23F', chapterNum: '#FFD23F',
  burstDots: { gold: '#E0A800', good: '#3FB98A', bad: '#C92A4A', accent: '#C93A12', cool: '#1E9DC4' },
  burstLines: '#fff', burstText: '#fff', burstInk: null, // burstInk (themed): per-colour text on the star
  // soft light and shade
  shadow: '#000', shadowK: 1,          // soft drop shadows (alpha multiplier)
  glass: '#FFFFFF',                    // faint tints on panels (tracks, cell faces, rules)
  shade: '#000',                       // the countdown ring's well
  capShadow: '#000', titleGlowA: 0.35,
  grainBlend: 'normal', grainOpacity: 0.07,
  // code
  codeLn: '#8A84B8',
  tk: { k: '#FF7AB6', t: '#5CE1FF', n: '#FFD23F', c: '#A39DCB', s: '#7BE3B5', f: '#7BE3B5', i: '#F2EDE4', p: '#b9b3d6', o: '#FF9E7A' },
  traffic: ['#FF5F57', '#FEBC2E', '#28C840'],
  // the Three.js variant
  three: { fog: '#120c2c', hemiSky: '#9b7bff', hemiGround: '#1a1030', key: '#ffc89a', rim: '#5ce1ff', floor: '#150f30', grid: '#6b4fd8', grid2: '#2a2060' },
};

// sky moods for the Sky object (top, bottom, glow); key them per chapter for a warm-to-neon arc through the film
const ORIGINAL_MOOD = {
  dusk: { top: '#0B0820', bottom: '#3A1740', glow: '#FF7A3D' },
  night: { top: '#06061A', bottom: '#191243', glow: '#7B5CFF' },
  neon: { top: '#070A1F', bottom: '#122A4A', glow: '#2EC5FF' },
  ember: { top: '#0E0614', bottom: '#3B0F24', glow: '#FF4F6E' },
  dawn: { top: '#0B0A22', bottom: '#2E2350', glow: '#FFD23F' },
};

// ------------------------------------------------------------------ a registry theme mapped onto the kit's roles
// Fills stay fills (shapes, bars, glows); text uses text / muted / dim, <hue>Ink, or on<Hue> on a filled chip.
function themed(t) {
  const L = t.tone === 'light', m = (a, b, u) => hex(mix(a, b, u));
  // hue inks get a margin over the solved 4.6:1: the foreground bokeh drifts over the panels and veils the text
  const far = L ? '#000000' : '#FFFFFF', grounds = [t.panel, t.panel2, t.bg, t.bg2];
  const lift = (c) => { for (let u = 0; u < 0.6; u += 0.02) { const x = m(c, far, u); if (grounds.every((g) => contrast(x, g) >= 5.4)) return x; } return m(c, far, 0.6); };
  const ink = Object.fromEntries(['accent', 'good', 'bad', 'gold', 'cool', 'violet', 'warm'].map((h) => [h, lift(t[h + 'Ink'])]));
  return {
    ink: t.text, inkDim: t.muted, muted: t.dim,
    accent: t.accent, good: t.good, bad: t.bad, gold: t.gold, cool: t.cool, violet: t.violet,
    accentInk: ink.accent, goodInk: ink.good, badInk: ink.bad, goldInk: ink.gold, coolInk: ink.cool, violetInk: ink.violet,
    onGold: t.onGold, onGood: t.onGood, onAccent: t.onAccent, labelHot: null,
    page: t.deep, viewport: t.bg,
    panel: css(t.panel, 0.95), panelEdge: t.line2,
    plate: t.panel, band: L ? t.bg : t.deep, chapterBand: t.panel, stampBg: t.panel,
    // overlays sit above the text: keep them faint, the solved inks have little margin to give
    scrim: t.deep, scrimK: L ? 0 : 0.6, vignette: t.deep, vignetteA: L ? 0.3 : 0.5,
    orbK: L ? 0.6 : 1, foreK: L ? 0.4 : 0.75,
    titleSub: t.text, ladO: t.text, decBarEdge: L ? m(t.panel, t.accent, 0.5) : t.accent, flashInk: t.text, flashK: 0.35,
    // the far city: silhouettes a step darker than the sky (a paper cut-out on a light ground)
    city: L ? [m(t.bg2, t.line2, 0.55), m(t.bg2, t.line2, 0.9)] : [m(t.bg, t.shadow, 0.25), m(t.deep, t.shadow, 0.35)],
    cityFade: t.deep, floorTop: t.deep, floorBottom: L ? m(t.deep, t.line, 0.6) : m(t.deep, t.shadow, 0.4),
    // shapes keep about 3:1 on the ground: a panel-coloured face inside a `dim` rim, `dim` edges
    node: t.panel, nodeSide: L ? t.line2 : t.deep, nodeStroke: t.dim, edge: t.dim,
    chipStroke: t.line2, tokenStroke: t.shadow,
    fire: L ? t.accent : t.text, shine: L ? t.bg : t.text, glowK: L ? 0.5 : 1,
    cellEdge: t.line2,
    outline: t.shadow,
    ctNumBg: t.accent, ctNumInk: t.onAccent, chapterNum: ink.gold,
    burstDots: Object.fromEntries(['gold', 'good', 'bad', 'accent', 'cool'].map((k) => [k, m(t[k], t.shadow, 0.22)])),
    burstLines: L ? t.shadow : t.text, burstText: t.text, lightest: L ? t.bg : t.text,
    burstInk: { gold: t.onGold, good: t.onGood, bad: t.onBad, accent: t.onAccent, cool: t.onCool },
    shadow: t.shadow, shadowK: L ? 0.35 : 1,
    glass: t.text, shade: t.shadow,
    capShadow: L ? t.bg : t.shadow, titleGlowA: L ? 0 : 0.3,
    grainBlend: L ? 'multiply' : 'screen', grainOpacity: L ? 0.06 : 0.05,
    codeLn: t.dim,
    tk: { k: ink.violet, t: ink.cool, n: ink.gold, c: t.dim, s: ink.good, f: ink.good, i: t.text, p: t.muted, o: ink.warm },
    traffic: [t.bad, t.gold, t.good],
    three: { fog: t.bg, hemiSky: t.violet, hemiGround: t.deep, key: t.lights[1], rim: t.cool, floor: t.panel, grid: t.violet, grid2: t.line },
  };
}

// chapter key lights from the theme's six `lights` (warm, gold, bad, accent, violet, good). On a dark ground the
// light glows at the horizon; on a light ground a glow reads as a smudge, so it becomes a faint tint of the sky.
function themedMoods(t) {
  const L = t.tone === 'light', m = (a, b, u) => hex(mix(a, b, u));
  const mood = (light) => L
    ? { top: t.bg, bottom: m(t.bg2, light, 0.08), glow: m(t.bg, light, 0.2) }
    : { top: t.deep, bottom: m(t.bg2, light, 0.12), glow: m(t.bg2, light, 0.42) };
  const [warm, gold, bad, accent, violet] = t.lights;
  return { dusk: mood(warm), night: mood(violet), neon: mood(accent), ember: mood(bad), dawn: mood(gold) };
}

export const THEME_ID = THEME ? THEME.id : 'original';
export const TONE = THEME ? THEME.tone : 'dark';
export const MOOD = THEME ? themedMoods(THEME) : ORIGINAL_MOOD;
export const C = THEME ? { ...themed(THEME), skyTop: MOOD.night.top, skyBottom: MOOD.night.bottom } : ORIGINAL;

/** the CSS variables style.css reads (main.js sets them on :root); composite values are built here from C */
export function cssVars() {
  const sh = (a) => css(C.shadow, a * C.shadowK), gl = (a) => css(C.glass, a);
  return {
    page: C.page, viewport: C.viewport,
    ink: C.ink, 'ink-dim': C.inkDim, panel: C.panel, 'panel-edge': C.panelEdge,
    accent: C.accent, good: C.good, bad: C.bad, gold: C.gold, cool: C.cool, violet: C.violet,
    'accent-ink': C.accentInk, 'good-ink': C.goodInk, 'gold-ink': C.goldInk, 'cool-ink': C.coolInk,
    'on-gold': C.onGold, 'on-good': C.onGood, outline: C.outline,
    'scrim-bg': `radial-gradient(70% 70% at 50% 45%, ${css(C.scrim, 0.35 * C.scrimK)}, ${css(C.scrim, 0.8 * C.scrimK)})`,
    'vignette-bg': `radial-gradient(120% 95% at 50% 46%, ${css(C.vignette, 0)} 55%, ${css(C.vignette, C.vignetteA)} 100%)`,
    'grain-blend': C.grainBlend, 'grain-op': String(C.grainOpacity),
    'panel-shadow': `0 40px 80px ${sh(0.55)}, 0 0 0 1px ${sh(0.4)}, inset 0 1px 0 ${gl(0.08)}`,
    'accent-wash': css(C.accent, 0.16), 'dec-bar-edge': C.decBarEdge, 'title-sub': C.titleSub, 'lad-o': C.ladO,
    'cap-band': `linear-gradient(180deg, ${css(C.band, 0)} 0%, ${css(C.band, 0.78)} 34%, ${css(C.band, 0.92)} 100%)`,
    'cap-shadow': `0 2px 12px ${css(C.capShadow, 0.6)}`,
    'cap-track': gl(0.14),
    'title-shadow': C.titleGlowA ? `0 6px 0 ${sh(0.35)}, 0 0 60px ${css(C.accent, C.titleGlowA)}` : `0 6px 0 ${sh(0.35)}`,
    'chapter-band': C.chapterBand, 'chapter-shadow': `0 30px 80px ${sh(0.6)}`, 'chapter-num': C.chapterNum,
    'ct-num-bg': C.ctNumBg, 'ct-num-ink': C.ctNumInk,
    'q-shadow': `0 40px 90px ${sh(0.6)}, 0 0 50px ${css(C.gold, 0.18 * C.glowK)}`,
    'qback-shadow': `0 40px 90px ${sh(0.6)}, 0 0 50px ${css(C.good, 0.25 * C.glowK)}`,
    'code-rule': gl(0.08), 'code-bar-shadow': `0 0 30px ${css(C.accent, 0.18 * C.glowK)}`, 'code-ln': C.codeLn,
    ...Object.fromEntries(Object.entries(C.tk).map(([k, v]) => ['tk-' + k, v])),
    'cell-bg': gl(0.05), 'cell-edge': gl(0.12), 'colbar-shadow': `0 0 24px ${css(C.accent, 0.4 * C.glowK)}`,
    'lad-track': gl(0.08), 'lad-hl': gl(0.06),
    'picked-bg': css(C.good, 0.1), 'picked-shadow': `0 0 40px ${css(C.good, 0.2 * C.glowK)}`, 'stamp-bg': css(C.stampBg, 0.85),
  };
}

/** copy the variables and the fonts onto an element's style (document.documentElement.style) */
export function applyCssVars(style) {
  for (const [k, v] of Object.entries(cssVars())) style.setProperty('--' + k, v);
  style.setProperty('--font-ui', FONT.ui); style.setProperty('--font-mono', FONT.mono); style.setProperty('--font-comic', FONT.comic);
}

export const FONT = {
  ui: '"Inter Var", "Inter", "DejaVu Sans", sans-serif',
  mono: '"JB Mono", "DejaVu Sans Mono", monospace',
  comic: '"Bangers", "Inter Var", Impact, sans-serif',
};

// sizes at 1080p (quality-bar.md): nothing under 26 px on screen. The kit's smallest text is 28 px (panel titles,
// table headers) so the camera can pull back a little without crossing the floor.
export const SIZE = { headline: 104, title: 72, body: 44, caption: 40, code: 30, label: 32, small: 28 };

// Graph text lives in graph space, so it shrinks when the graph is scaled down (Graph.s) or the camera pulls back.
// Each kind keeps at least this many px ON SCREEN (the label grows inside the graph to hold it; when the graph is
// shown large, labels scale with it as usual). font = the size drawn at graph scale 1.
export const GRAPH_TEXT = {
  weight: { font: 32, min: 32 },   // edge weight chips
  badge: { font: 34, min: 34 },    // value badges above nodes (a dist value)
  tag: { font: 30, min: 30 },      // START / GOAL chips under nodes
  node: { font: 40, min: 34 },     // the node's own number
  sum: { font: 32, min: 32 },      // running total riding on a token
};
