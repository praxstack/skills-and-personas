// style.js: every colour, font and size the film uses, in one place. Change the look here, not in scenes.
// Recipe: "toy diorama 3D" (references/quality-bar.md): rounded toy blocks on a desk at dusk, warm key light,
// cool rim light, soft shadows, glow (bloom) only on the active elements, comic bursts in screen space.
//
// Themes: src/theme.js is either the shipped stub (`THEME = null`: the original palette below, unchanged) or a
// file emitted by `python3 $S/theme.py emit <id> --format js --out source/src/theme.js`. With a theme, C, FX and
// the ink helpers are derived from its tokens (themed() below); nothing else in the kit holds a colour.
import { THEME } from '../theme.js';

// ------------------------------------------------------------------ the original palette (the verified starter look)
const ORIGINAL = {
  // world
  sky: ['#120c30', '#33226a', '#7a3a78', '#ff8a5c', '#1a1036'], // zenith, upper, near horizon, warm band, below
  fog: '#24194d',
  desk: '#b97c50',       // warm wooden desk
  deskEdge: '#7d4a2e',
  woodDark: '#46230f', woodLight: '#ffdcb4',   // grain strokes (drawn at low alpha)
  board: '#2d3366',      // the game board the subject sits on
  boardRim: '#f1dcc0',
  grid: '#3b4384',
  gridDot: 'rgba(255,255,255,0.06)',
  island: '#efd6a8',     // sand disc under each node
  tree: '#4cb87e', trunk: '#8a5a3c',
  pad: '#fff4e4',        // a node's pad is its colour mixed 55% toward this
  key: '#ffd9ae',        // warm key light
  keyLights: null,       // per-chapter key light colours (themes only; null = C.key all film)
  rim: '#7fb2ff',        // cool rim light
  fillLight: '#ffc9a0',
  skyFill: '#8f86ff', groundFill: '#ff9f7a',
  building: ['#1c1238', '#24174a'], windows: ['rgba(255,196,120,0.9)', 'rgba(255,140,160,0.8)'],
  bulb: '#ffd59a', bulbHalo: '#ffb36b', wire: '#2a1d4a',
  bokeh: ['#ff9a6b', '#ffcf7a', '#ff6fae', '#7fb2ff', '#b78cff'],
  mug: '#f4efe6', coffee: '#5a3524', pencilTip: '#f1d2a8', pot: '#e46f4f', leaf: '#3fae7a',
  white: '#ffffff',      // neutral: texture multipliers, alpha masks (not a colour anyone sees as such)
  // subject
  node: ['#2fd6b5', '#ffc94d', '#ff6f9f', '#8c8cff', '#5ad1ff', '#ff9a4d', '#b8e05a', '#e58cff'],
  faceInk: 'rgba(26,16,48,0.88)',   // the number printed on a block
  edge: '#fff1dc',       // idle edge (no glow)
  token: '#ff8a3d',      // the mascot
  eye: '#1a1030',
  // meaning (shared by 3D glows and the overlay)
  hot: '#ff5b2e',        // the thing being looked at right now
  good: '#7be3b5',       // valid / the answer
  bad: '#ff4f6e',        // illegal / wrong
  cool: '#7fd8ff',       // ghosts, exploration, "old" values
  gold: '#ffd23f',       // tags, highlights
  dim: '#5d5a86',
  // overlay
  // text on panels: ink about 15:1; soft (secondary) and faint (punctuation, line numbers, empty cells) stay at
  // least 6:1 on a panel even over the brightest toy behind it (quality bar: 4.5:1 minimum)
  ink: '#fff7ea',
  inkSoft: 'rgba(255,247,234,0.80)',
  inkFaint: 'rgba(255,247,234,0.64)',
  comment: '#b8aed6',    // code comments: dimmer than code, still about 7:1 on the code panel
  panel: 'rgba(18,12,40,0.86)',
  panelLine: 'rgba(255,255,255,0.14)',
  outline: '#1a1030',
  page: '#0f0b2a',
  vignette: ['rgba(8,4,24,0)', 'rgba(8,4,24,0.6)'], bottomFade: ['rgba(10,6,28,0)', 'rgba(10,6,28,0.62)'],
  badge: 'rgba(18,12,40,0.9)', badgeLine: 'rgba(255,255,255,0.28)',
  wtag: '#fff4e4', wtagInk: '#1a1030',
  cap: 'rgba(14,9,32,0.74)',
  shadow: ['rgba(0,0,0,0.35)', 'rgba(0,0,0,0.4)', 'rgba(0,0,0,0.45)', 'rgba(0,0,0,0.5)'], // soft drop shadows, small to large
  halftone: 'rgba(26,16,48,0.22)',
  halo: ['rgba(10,6,28,0.9)', 'rgba(10,6,28,0.85)'],     // the title's subtitle halo over the 3D
  titleShadow: '#1a1030',
  codeBg: 'rgba(13,9,30,0.93)', codeBar: 'rgba(255,255,255,0.05)', codeHl: 'rgba(255,91,46,0.17)',
  codeDots: ['#ff5f57', '#febc2e', '#28c840'],
  syntax: { k: '#ff8fc8', ty: '#8fc9ff', nu: '#ffd23f', op: '#ffb38a', fnc: '#7be3b5', key: '#8fc9ff' },
  cell: 'rgba(255,255,255,0.06)', cellLine: 'rgba(255,255,255,0.18)',
  rung: 'rgba(255,255,255,0.05)',
  track: 'rgba(255,255,255,0.06)', trackLine: 'rgba(255,255,255,0.14)',
  // text placed ON a fill of these colours (chapter band, tags, flags, stamp, flyers) and the comic stroke
  onHot: '#1a1030', onGold: '#1a1030', onGood: '#1a1030', bandInk: '#fff7ea', bandNum: '#ffd23f', stroke: '#1a1030',
  titleSub: 'rgba(255,247,234,0.80)', titleInk2: '#ff8a3d',
};

// how glow and light are drawn: values above 1 bloom (dark grounds); light themes turn glows into tinted fills
const ORIGINAL_FX = {
  hdr: true,              // glowing colours are multiplied above 1 (bloom); false = never above the fill itself
  additive: true,         // halos, spills, bokeh blend additively (false: normal blending, a tinted fill)
  ring: [0.9, 1.6],       // node ring colour x (a + glow * b)
  emissive: [0.35, 0.12], // node block emissive per unit of glow (plain side, numbered side)
  spill: 0.22, halo: 0.2, bead: 3.2, beadMix: 0, ghost: 1.6, ghostOpacity: 0.5,
  bulb: 3, bulbHalo: 0.6, bokeh: [0.12, 0.25],
  light: { key: 3.4, rim: 2.2, fill: 0.35, hemi: 0.5, exposure: 1.0 },
  bloom: [0.6, 0.45, 1.1],  // strength, radius, threshold
  skyGraded: false,         // themes: the sky shader is tone-mapped like every other material (draft = final)
  cellMix: [18, 30], rungMix: [5, 20],   // % of a tone in a flashing cell (peak 48%: white ink stays >= 4.5:1 on good) / a highlighted ladder rung
  stampPad: '6px 16px 3px',               // the INTERVIEW PICK stamp's padding
};

// ------------------------------------------------------------------ small colour maths (sRGB hex, WCAG 2.x)
const hex3 = (h) => { const n = parseInt(h.slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
const toHex = (c) => '#' + c.map((v) => Math.round(Math.min(255, Math.max(0, v))).toString(16).padStart(2, '0')).join('');
export const mix = (a, b, u) => { const A = hex3(a), B = hex3(b); return toHex(A.map((v, i) => v + (B[i] - v) * u)); };
/** '#rrggbb' + alpha -> 'rgba(r,g,b,a)' */
export const rgba = (h, a) => { const [r, g, b] = hex3(h); return `rgba(${r},${g},${b},${a})`; };
const lum = (h) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; const [r, g, b] = hex3(h).map(f); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
export const contrast = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
/** move a fill toward `to` until it reaches `target`:1 against every colour in `grounds` (unchanged if it passes) */
function reach(fill, grounds, to, target) {
  for (let u = 0; u <= 1.0001; u += 0.02) { const c = mix(fill, to, u); if (grounds.every((g) => contrast(c, g) >= target)) return c; }
  return to;
}

// ------------------------------------------------------------------ a registry theme -> the kit's roles
const HUES = ['accent', 'warm', 'good', 'bad', 'cool', 'gold', 'violet'];
function themed(T) {
  const L = T.tone === 'light', W = ORIGINAL.white;
  const panel = T.panel, text = T.text;
  // the board: the ground every shape of the subject stands on (fills must read about 3:1 on it)
  const board = L ? mix(T.panel, T.accent, 0.05) : mix(T.panel2, T.accent, 0.16);
  const solid = (f) => reach(f, [board], L ? text : W, 3);   // a fill the board would swallow, pushed until it reads
  const node = ['cool', 'gold', 'violet', 'accent', 'warm', 'good', 'bad', 'violet'].map((k) => solid(T[k]));
  const desk = L ? mix(T.deep, T.warm, 0.2) : mix(T.panel, T.warm, 0.42);
  const dark = L ? text : T.deep;        // comic strokes and eyes
  const line = L ? mix(T.line2, text, 0.3) : T.deep;   // outlines and offset shadows of tags, cards and bursts
  const sh = (a) => rgba(T.shadow, L ? +(a * 0.42).toFixed(3) : a);
  const C = {
    sky: L ? [mix(T.bg2, T.accent, 0.1), T.bg2, T.bg, mix(T.bg, T.warm, 0.22), T.deep]
      : [T.deep, mix(T.bg2, T.violet, 0.16), mix(T.bg2, T.violet, 0.36), mix(T.warm, T.bg, 0.2), T.deep],
    fog: L ? T.bg2 : mix(T.bg2, T.violet, 0.14),
    desk, deskEdge: L ? mix(desk, text, 0.3) : mix(desk, T.deep, 0.45),
    woodDark: L ? mix(desk, text, 0.55) : mix(desk, T.shadow, 0.6), woodLight: L ? T.bg : mix(desk, text, 0.6),
    board, boardRim: L ? T.line2 : mix(text, T.warm, 0.18),
    grid: mix(board, T.line2, L ? 0.45 : 0.35), gridDot: rgba(text, 0.06),
    island: L ? mix(T.deep, T.gold, 0.3) : mix(text, T.gold, 0.35),
    tree: T.good, trunk: mix(T.warm, T.shadow, 0.45),
    pad: L ? T.bg : text,
    key: mix(W, T.lights[0], L ? 0.12 : 0.3), keyLights: T.lights.map((c) => mix(W, c, L ? 0.12 : 0.3)),
    rim: mix(W, T.accent, 0.45), fillLight: mix(W, T.warm, 0.35),
    skyFill: mix(W, L ? T.accent : T.violet, L ? 0.12 : 0.45), groundFill: mix(W, T.warm, L ? 0.12 : 0.45),
    building: L ? [mix(T.bg2, T.line2, 0.55), mix(T.bg2, T.line2, 0.8)] : [mix(T.deep, T.violet, 0.1), mix(T.bg, T.violet, 0.14)],
    windows: L ? [rgba(T.bg, 0.9), rgba(mix(T.bg, T.accent, 0.35), 0.8)] : [rgba(T.gold, 0.9), rgba(T.bad, 0.8)],
    bulb: L ? T.gold : mix(T.gold, W, 0.4), bulbHalo: T.warm, wire: L ? T.line2 : T.deep,
    bokeh: [T.warm, T.gold, T.bad, T.accent, T.violet],
    mug: L ? T.bg : mix(text, T.panel, 0.08), coffee: mix(T.warm, T.shadow, 0.65), pencilTip: mix(T.gold, L ? T.bg : text, 0.55),
    pot: T.warm, leaf: T.good,
    white: W,
    node, faceInk: null, edge: L ? T.muted : text, token: solid(T.warm), eye: dark, wtagInk: text,
    hot: solid(T.accent), good: solid(T.good), bad: solid(T.bad), cool: solid(T.cool), gold: solid(T.gold),
    dim: L ? T.line2 : T.line,
    // dim text (line numbers, punctuation, comments) gets headroom over 4.6: measured on video frames, small
    // anti-aliased glyphs read about 7% under their flat-colour contrast
    ink: text, inkSoft: reach(T.muted, [T.bg, T.panel, T.panel2], text, 6.2), inkFaint: reach(T.dim, [T.bg, T.panel, T.panel2], text, 5.2), comment: reach(T.dim, [T.bg, T.panel, T.panel2], text, 5.2),
    panel: rgba(panel, 0.95), panelLine: L ? T.line2 : T.line, outline: line, page: T.bg,
    vignette: [rgba(T.deep, 0), rgba(T.deep, L ? 0.5 : 0.6)], bottomFade: [rgba(T.deep, 0), rgba(T.deep, L ? 0.3 : 0.62)],
    badge: rgba(panel, 0.96), badgeLine: L ? T.line2 : T.line,
    wtag: panel,
    cap: rgba(panel, 0.93),
    shadow: [sh(0.35), sh(0.4), sh(0.45), sh(0.5)],
    halftone: rgba(T.shadow, L ? 0.12 : 0.22),
    halo: [rgba(T.bg, 0.9), rgba(T.bg, 0.85)],
    titleShadow: L ? T.line2 : T.deep,
    codeBg: rgba(panel, 0.97), codeBar: T.panel2, codeHl: rgba(T.accent, L ? 0.1 : 0.16),
    codeDots: [T.bad, T.gold, T.good],
    cell: T.panel2, cellLine: T.line2, rung: mix(T.panel, T.panel2, 0.5), track: T.panel2, trackLine: T.line,
    titleSub: text, titleInk2: reach(T.warmInk, L ? [T.bg, T.bg2, T.deep, desk, board] : [T.bg, T.bg2, T.deep], L ? text : W, 6),
  };
  // inks (text in a hue) and on-colours (text on a fill of a hue), keyed by the fills the kit actually paints
  const INK = new Map(), ON = new Map();
  for (const k of HUES) for (const f of [T[k], solid(T[k])]) { INK.set(f.toLowerCase(), T[k + 'Ink']); ON.set(f.toLowerCase(), T['on' + k[0].toUpperCase() + k.slice(1)]); }
  // a plate: a fill that carries text, pushed away from its on-colour until the label clears 6.2:1 (the OCR
  // measures a small label below its flat-colour contrast: anti-aliasing, the outline, the bottom fade over it)
  function plateFor(fill) {
    if (!fill) return '';
    const on = onFill(fill);
    return reach(fill, [on], lum(on) > 0.3 ? T.shadow : W, 6.2);
  }
  C.syntax = { k: inkFor(T.violet), ty: inkFor(T.accent), nu: inkFor(T.gold), op: inkFor(T.warm), fnc: inkFor(T.good), key: inkFor(T.accent) };
  C.onHot = onFill(C.hot); C.onGold = onFill(C.gold); C.onGood = onFill(C.good);
  C.bandInk = C.onHot; C.bandNum = C.onHot; C.stroke = dark;
  function inkFor(tone) {
    if (!tone) return '';
    const k = tone.toLowerCase();
    return reach(INK.get(k) || tone, [T.bg, T.panel, T.panel2], text, 5.4);   // with headroom (see inkFaint); a blended tone is solved on the spot
  }
  function onFill(fill) {
    if (!fill) return '';
    const k = fill.toLowerCase();
    if (ON.has(k)) return ON.get(k);
    return contrast(text, fill) >= contrast(T.bg, fill) ? text : T.bg;
  }
  // the opposite of a text colour: a comic stroke that rings the letters instead of fattening them
  const strokeFor = (ink) => (lum(ink) > 0.3 ? dark : (L ? T.bg : text));
  const FX = L
    ? { ...ORIGINAL_FX, hdr: false, additive: false, ring: [1, 0], emissive: [0.12, 0.04], spill: 0.28, halo: 0.22, bead: 1, beadMix: 0.5,
      ghost: 1, ghostOpacity: 0.55, bulb: 1, bulbHalo: 0.3, bokeh: [0.05, 0.08],
      light: { key: 1.7, rim: 0.9, fill: 0.7, hemi: 2.6, exposure: 1.0 }, bloom: [0, 0.45, 1.1], skyGraded: true, cellMix: [14, 26], rungMix: [4, 8], stampPad: '10px 22px 8px' }
    : { ...ORIGINAL_FX, skyGraded: true, cellMix: [10, 26], rungMix: [4, 10], stampPad: '10px 22px 8px' };
  return { C, FX, inkFor, onFill, strokeFor, plateFor };
}

const TH = THEME ? themed(THEME) : null;
export const THEME_ID = THEME ? THEME.id : 'original';
export const TONE = THEME ? THEME.tone : 'dark';
export const C = TH ? TH.C : ORIGINAL;
export const FX = TH ? TH.FX : ORIGINAL_FX;
/** text in a hue (badge values, chip numbers, table heads, notes): the original paints the tone itself */
export const inkOf = (tone) => (TH ? TH.inkFor(tone) : tone);
/** text sitting on a fill of that tone (tags, flags, bursts, tree nodes): the original uses the outline colour */
export const onOf = (tone) => (TH ? TH.onFill(tone) : C.outline);
/** a leaf note under the recursion tree: the original lightens the tone toward white */
export const noteOf = (tone) => (TH ? TH.inkFor(tone) : mix(tone, C.white, 0.3));
/** the number printed on a block of that colour */
export const faceInkOf = (col) => (TH ? TH.onFill(col) : C.faceInk);
/** the comic stroke (and offset shadow) around Bangers text of that colour */
export const strokeOf = (ink) => (TH ? TH.strokeFor(ink) : C.stroke);
/** the fill behind a label of that tone (flags, toned weight tags, bursts, chapter tags): the original paints the tone */
export const plateOf = (tone) => (TH ? TH.plateFor(tone) : tone);
/** burst text on a burst of that tone */
export const burstInkOf = (tone) => (TH ? TH.onFill(tone) : C.ink);

// glow strength per meaning: values above ~1 bloom (final quality); 1 or less never bloom
export const GLOW = { idle: 0.85, hot: 2.6, good: 2.3, bad: 2.3, cool: 1.9, gold: 2.4, dim: 0.45 };

export const FONT = {
  ui: '"Inter Film", Inter, "DejaVu Sans", sans-serif',         // captions, body, labels
  mono: '"JetBrains Mono NL", "DejaVu Sans Mono", monospace',    // code and numbers (no ligatures: != stays !=)
  comic: '"Bangers", "Inter Film", sans-serif',                  // titles, bursts, chapter tags
};

// sizes in px on the 1920x1080 stage (the overlay is scaled to the real viewport); film.css holds the values
// each panel uses. Quality bar: body 40-48, captions 38-44, code 30-36, nothing under 26; in this kit the
// smallest text (weight tags, table headers, file name, tree notes) is 30-32 px.
export const SIZE = {
  W: 1920, H: 1080, safe: 96,
  title: 132, chapter: 120, headline: 64, body: 44, caption: 40, code: 30, label: 34, small: 30,
  captionBand: 180,
};
