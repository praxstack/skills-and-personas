// tokens.js: the ONE place for palette, type, sizes and chapter lighting. Change the look here, not in the kit.
// Every colour is also published as a CSS variable (--bg, --ink, --accent, ...) for styles.css.
// Default recipe: "Dark editorial" from references/quality-bar.md (near-black, warm accent, mint/rose for
// right/wrong, Inter Display headlines, JetBrains Mono for code and numbers, comic bursts in Bangers).
//
// Themes: theme.js (loaded just before this file) sets window.THEME. The template ships a stub (THEME = null),
// which keeps the original palette below exactly. `python3 $S/theme.py emit <id> --format global --out
// source/theme.js` replaces it with one of the 30 registry themes, and themed() maps its tokens onto the
// kit's roles (references/gsap-guide.md, "Themes"). Kit colours come in three kinds:
//   K.C  (color)  fills: areas, thick strokes, glows          K.col(c)
//   K.I  (inks)   text and thin strokes in a hue               K.ink(c)
//   K.O  (ons)    text sitting on a filled shape of that hue   K.on(c)
//   K.U  (look)   every other surface, line, shadow and sheen of the kit, by role
// In the original palette inks equal fills and every on-colour is the near-black, as the starter was built.
window.TOKENS = {
  color: {
    bg: '#0B0B0D',        // background base
    bg2: '#15151B',       // raised surfaces (nodes, cells)
    panel: '#111116',     // cards and panels
    line: 'rgba(242,237,228,0.16)',
    ink: '#F2EDE4',       // text
    dim: 'rgba(242,237,228,0.62)',
    faint: 'rgba(242,237,228,0.30)',
    accent: '#FF5B2E',    // the thing being looked at
    mint: '#7BE3B5',      // valid / answer
    rose: '#FF4F6E',      // illegal / wrong
    amber: '#FFC24B',     // numbers, comic bursts
    cyan: '#5CC8FF',      // secondary, cool rim light
    violet: '#A88BFF',
    black: '#0B0B0D',
  },
  // every other colour the kit draws, by role (CSS: var(--<role>), JS: K.U.<role>)
  look: {
    raised: '#17171D',                         // weight pills, tree nodes, thermometer glass
    glass: 'rgba(17,17,22,0.94)',             // decoder panel, meters
    noteBg: 'rgba(17,17,22,0.92)',
    capBg: 'rgba(8,8,11,0.80)', capLine: 'rgba(242,237,228,0.09)', capShadow: 'rgba(0,0,0,0.45)',
    hardShadow: 'rgba(0,0,0,0.55)', hardShadow2: 'rgba(0,0,0,0.5)',   // offset comic shadows (HUD tag, meter)
    track: 'rgba(242,237,228,0.16)',          // chapter progress track
    dotShade: 'rgba(0,0,0,0.22)',             // halftone on chapter slabs and bursts
    qcardA: 'rgba(30,30,38,0.96)', qcardB: 'rgba(16,16,21,0.96)',
    resultA: 'rgba(30,30,38,0.97)', resultB: 'rgba(14,14,19,0.97)',
    cardLine: 'rgba(242,237,228,0.14)', cardShadow: 'rgba(0,0,0,0.55)', cardHi: 'rgba(255,255,255,0.06)',
    qringBg: 'rgba(242,237,228,0.12)',
    calloutText: '#FFF6E2', calloutShadow: '#000',
    stampBg: 'rgba(11,11,13,0.82)', noteShadow: 'rgba(0,0,0,0.4)', panelShadow: 'rgba(0,0,0,0.45)',
    codeBg: 'rgba(14,14,19,0.97)', codeLine: 'rgba(242,237,228,0.13)', codeHead: 'rgba(255,255,255,0.035)',
    codeHeadLine: 'rgba(242,237,228,0.08)', codeDot: '#3A3A44', codeBar: 'rgba(255,91,46,0.20)',
    codeText: '#E9E3D8', codeNo: '#8A8A99',
    synKw: '#FF8A65', synTy: '#5CC8FF', synNu: '#FFC24B', synCm: '#A8A8B8', synSt: '#7BE3B5', synFn: '#FFD9A0', synId: '#ECE6DB',
    logBg: 'rgba(14,14,19,0.94)', logShadow: 'rgba(0,0,0,0.5)',
    cellLine: 'rgba(242,237,228,0.12)', cellShadow: 'rgba(0,0,0,0.4)', cellHi: 'rgba(255,255,255,0.05)',
    rungBg: 'rgba(255,255,255,0.035)', rungLine: 'rgba(242,237,228,0.10)', costTrack: 'rgba(242,237,228,0.07)',
    rungFocus: 'rgba(255,91,46,0.14)', rungPick: 'rgba(123,227,181,0.16)',
    treeEdge: 'rgba(242,237,228,0.45)',
    tubeFill: 'rgba(255,255,255,0.035)', tubeLine: 'rgba(242,237,228,0.34)', tick: 'rgba(242,237,228,0.30)',
    bulbLine: 'rgba(242,237,228,0.40)', shine: 'rgba(255,255,255,0.55)', shineBar: 'rgba(255,255,255,0.10)',
    acellLine: 'rgba(242,237,228,0.16)', stackFill: 'rgba(92,200,255,0.05)', stackTube: 'rgba(242,237,228,0.55)',
    stackShadow: 'rgba(0,0,0,0.35)', chipHi: 'rgba(255,255,255,0.22)', heatMid: '#EDE6D6',
    nodeA: '#2A2A33', nodeB: '#121217', nodeRim: 'rgba(255,255,255,0.07)', nodeSheen: 'rgba(255,255,255,0.22)',
    pool: '#FFF3E0', shadowCol: '#000',      // light pool under the subject; contact shadow under nodes
    bgA: '#17171D', bgB: '#0D0D11', bgC: '#060608',   // background canvas: centre, middle, edge
    vig0: 'rgba(0,0,0,0)', vig: 'rgba(0,0,0,0.6)', dot: 'rgba(242,237,228,0.16)', bokeh: '#FFFFFF',
  },
  // how the atmosphere is drawn (numbers and blend modes; the light theme values differ, see themed())
  fx: {
    lightOp: 'lighter', lightK: 1,          // chapter key/rim lights: canvas blend mode, strength
    bokehOp: 'lighter', bokehK: 1,
    grain: 'both', grainA: [8, 22],         // grain specks: 'both' (black and white) or 'dark'; alpha range /255
    glowStops: [0.55, 0.18],                // SVG halo gradients (centre, 45%)
    poolStops: [0.085, 0.03], shadowA: 0.6, calloutShadowA: 0.55,
    slabShade: -0.35,                       // chapter slab gradient: the slab colour to this shade
    markA: 0.2,                             // decoder line highlight (fill-opacity)
    codeDim: 0.75,                          // code lines outside the focus (opacity)
    unspoken: 0.5, unspokenColor: null,     // question words not spoken yet: opacity, or a colour (themes)
    flashA: null,                           // table cell flash: null = the solid colour, else a tint alpha
    visStroke: false,                       // themes: lift strokes in a hue to 3:1 against bg
    calloutOn: false,                       // themes: burst words in the fill's on-colour
  },
  // preview controls (never in a render)
  chrome: { previewBg: '#18181D', previewInk: '#ddd', btnBg: '#2A2A33', btnInk: '#eee', errBg: '#3A0D14', errInk: '#FFD7DD', letterbox: '#000' },
  font: {
    display: "'Inter', system-ui, sans-serif",     // Inter 4 variable: opsz 32 = Inter Display at headline sizes
    ui: "'Inter', system-ui, sans-serif",
    mono: "'JetBrains Mono', 'Inter', monospace",  // ligatures are switched off in styles.css (.mono)
    comic: "'Bangers', 'Inter', sans-serif",
  },
  size: { headline: 112, title: 72, body: 44, caption: 40, code: 30, label: 30, small: 28 },   // 1080p px; nothing on screen under 26 (aim for 28+: world text shrinks with the camera)
  safe: 96,           // keep text this far from every edge
  captionBand: 180,   // bottom band reserved for captions; the subject stays above it
  // Light per chapter (index = chapter number): a warm key light top-left and a rim light bottom-right.
  // Changing hue per chapter gives the film the day-to-night variety of the reference films.
  moods: [
    { key: '#FF8A3D', rim: '#FF4F6E', glow: 0.46 },   // 0 intro: sunrise
    { key: '#FF7A3D', rim: '#3FA9FF', glow: 0.40 },   // 1 problem: warm + cool
    { key: '#FF4F6E', rim: '#7A5CFF', glow: 0.42 },   // 2 brute force: hot
    { key: '#8F6BFF', rim: '#33D1FF', glow: 0.42 },   // 3 intuition: neon dusk
    { key: '#FFB547', rim: '#2EC4A6', glow: 0.40 },   // 4 approaches: gold
    { key: '#3FD9A0', rim: '#3F7BFF', glow: 0.40 },   // 5 code + dry run: terminal
    { key: '#FF8A3D', rim: '#A88BFF', glow: 0.42 },   // 6+ (extra chapters wrap around)
  ],
};
(function theme() {
  const TK = window.TOKENS, C = TK.color;
  // original palette: inks are the fills, every label on a fill is the near-black
  TK.inks = Object.fromEntries(Object.keys(C).map((k) => [k, C[k]]));
  TK.ons = Object.fromEntries(Object.keys(C).map((k) => [k, C.black]));
  TK.themeId = 'original';
  const T = window.THEME;
  if (T && T.bg) themed(TK, T);
})();
/**
 * themed(TK, T): map a registry theme (theme.py emit --format global) onto the kit's roles.
 * Fills stay fills; text gets text / muted / dim / <hue>Ink / on<Hue>. Panels are mixes of the theme's own
 * surfaces (bg, bg2, deep, panel, panel2), so the solved inks keep their contrast on them.
 */
function themed(TK, T) {
  const dark = T.tone === 'dark';
  const hex = (c) => { const n = parseInt(c.slice(1), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const a = (c, al) => { const [r, g, b] = hex(c); return `rgba(${r},${g},${b},${al})`; };
  const mix = (p, q, f) => '#' + hex(p).map((x, i) => Math.round(x + (hex(q)[i] - x) * f).toString(16).padStart(2, '0')).join('');
  const sk = dark ? 1 : 0.4;              // shadows: full on dark grounds, soft on light ones
  const sh = (al) => a(T.shadow, +(al * sk).toFixed(3));
  const tx = (al) => a(T.text, al);       // hairlines in the text colour
  const lk = dark ? 1 : 1.25;             // hairlines read a little weaker on light grounds
  const hi = (al) => `rgba(255,255,255,${dark ? al : Math.min(0.7, al * 6)})`;   // sheens: brighter on light grounds
  // the darkest outline the theme has (comic strokes, chip borders, HUD tag frame)
  const outline = dark ? T.deep : T.text;
  // hue inks get a margin over the solved 4.6:1: the light pools and glows lift the ground under the text (a gold
  // kicker read 4.18:1 on github-dimmed's warm glow). Same hue, moved towards the body text.
  const lin = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  const lum = (c) => { const [r, g, b] = hex(c).map(lin); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const cr = (p, q) => { const x = lum(p), y = lum(q); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const lift = (c, target, under) => { let k = 0, x = c; while (k < 0.7 && under.some((g) => cr(x, g) < target)) { k += 0.04; x = mix(c, T.text, k); } return x; };
  const grounds = [T.bg, T.bg2, T.panel, T.deep];
  const hueInk = (c) => lift(c, 5.4, grounds);
  // a ladder rung's ground: the panel at 35% (30% light), or the focus / pick tint, over the ground
  const rungUnder = [T.bg, T.bg2, T.deep].flatMap((g) => [mix(g, T.panel, dark ? 0.35 : 0.3), mix(g, T.good, 0.14), mix(g, T.accent, 0.12)]);
  TK.color = {
    bg: T.bg, bg2: T.bg2, panel: T.panel, line: tx(0.16 * lk), ink: T.text, dim: T.muted, faint: T.dim,
    accent: T.accent, mint: T.good, rose: T.bad, amber: T.gold, cyan: T.cool, violet: T.violet, black: outline,
    warm: T.warm,
  };
  TK.inks = {
    bg: T.text, bg2: T.text, panel: T.text, line: T.dim, ink: T.text, dim: T.muted, faint: T.dim, black: T.text,
    accent: hueInk(T.accentInk), mint: hueInk(T.goodInk), rose: hueInk(T.badInk), amber: hueInk(T.goldInk), cyan: hueInk(T.coolInk),
    violet: hueInk(T.violetInk), warm: hueInk(T.warmInk),
  };
  TK.ons = {
    bg: T.text, bg2: T.text, panel: T.text, line: T.text, ink: T.bg, dim: T.bg, faint: T.text, black: T.bg,
    accent: T.onAccent, mint: T.onGood, rose: T.onBad, amber: T.onGold, cyan: T.onCool, violet: T.onViolet, warm: T.onWarm,
  };
  // card surfaces: on dark grounds the lighter panels; on light grounds between bg and panel
  const cardA = dark ? T.panel2 : mix(T.bg, T.panel, 0.3), cardB = dark ? T.panel : mix(T.bg, T.panel, 0.6);
  const glassC = dark ? T.panel : mix(T.bg, T.panel, 0.55);
  const codeC = dark ? T.panel : mix(T.bg, T.panel, 0.5);
  TK.look = {
    raised: dark ? T.panel : mix(T.bg, T.panel, 0.6),
    glass: a(glassC, 0.97), noteBg: a(glassC, 0.97),
    capBg: a(dark ? T.deep : T.bg2, 0.92), capLine: tx(0.12 * lk), capShadow: sh(0.45),
    hardShadow: sh(0.55), hardShadow2: sh(0.5), track: tx(0.16 * lk), dotShade: a(T.shadow, dark ? 0.22 : 0.12),
    qcardA: a(cardA, 0.98), qcardB: a(cardB, 0.98), resultA: a(cardA, 0.98), resultB: a(cardB, 0.98),
    cardLine: tx(0.14 * lk), cardShadow: sh(0.55), cardHi: hi(0.06), qringBg: tx(0.14 * lk),
    calloutText: dark ? T.text : T.bg, calloutShadow: T.shadow,
    stampBg: a(dark ? T.bg : mix(T.bg, T.panel, 0.2), 0.96), noteShadow: sh(0.4), panelShadow: sh(0.45),
    codeBg: a(codeC, 0.98), codeLine: tx(0.13 * lk), codeHead: tx(0.04), codeHeadLine: tx(0.1), codeDot: T.line2,
    codeBar: a(T.accent, dark ? 0.16 : 0.12), codeText: T.text, codeNo: T.dim,
    synKw: T.violetInk, synTy: T.coolInk, synNu: T.warmInk, synCm: T.muted, synSt: T.goodInk, synFn: T.accentInk, synId: T.text,
    logBg: a(codeC, 0.98), logShadow: sh(0.5),
    cellLine: tx(0.14 * lk), cellShadow: sh(0.4), cellHi: hi(0.05),
    rungBg: a(T.panel, dark ? 0.35 : 0.3), rungLine: tx(0.12 * lk), costTrack: tx(0.08 * lk),
    rungFocus: a(T.accent, 0.12), rungPick: a(T.good, 0.14),
    rungTime: lift(T.goldInk, 5.6, rungUnder), rungSpace: lift(T.muted, 5.6, rungUnder),   // the rung's O(...) columns
    kickerInk: lift(T.goldInk, 6.3, grounds),   // kickers sit in the chapter light pools (4.42:1 on github-dimmed's title at 5.4)
    treeEdge: tx(0.45),
    tubeFill: a(T.panel, 0.4), tubeLine: tx(0.34), tick: tx(0.3), bulbLine: tx(0.4), shine: hi(0.55), shineBar: hi(0.1),
    acellLine: tx(0.16 * lk), stackFill: a(T.cool, 0.06), stackTube: tx(0.55), stackShadow: sh(0.35), chipHi: hi(0.22),
    heatMid: T.line2,
    nodeA: dark ? T.panel2 : T.bg, nodeB: dark ? T.panel : mix(T.bg, T.panel, 0.7),
    nodeRim: hi(0.07), nodeSheen: hi(0.22),
    pool: dark ? T.text : '#FFFFFF', shadowCol: T.shadow,
    bgA: dark ? T.bg2 : T.bg, bgB: dark ? T.bg : mix(T.bg, T.bg2, 0.5), bgC: dark ? T.deep : T.bg2,
    vig0: a(T.deep, 0), vig: a(T.deep, dark ? 0.6 : 0.55), dot: tx(dark ? 0.12 : 0.14), bokeh: '#FFFFFF',
  };
  TK.fx = {
    ...TK.fx,
    // on a dark ground the lights add; on a light ground they screen (they lighten, never smudge the paper)
    lightOp: dark ? 'lighter' : 'screen', lightK: dark ? 0.55 : 0.9,
    bokehOp: dark ? 'lighter' : 'source-over', bokehK: dark ? 0.6 : 0.8,
    grain: dark ? 'both' : 'dark', grainA: dark ? [6, 16] : [5, 14],
    glowStops: dark ? [0.45, 0.14] : [0.32, 0.1],
    poolStops: dark ? [0.06, 0.02] : [0.45, 0.18], shadowA: dark ? 0.6 : 0.22, calloutShadowA: dark ? 0.55 : 0.25,
    slabShade: null,                     // computed per slab: towards more contrast with its label (cards.js)
    markA: dark ? 0.16 : 0.13,
    codeDim: 1,                          // solved inks have no headroom for opacity: focus shows by the bar
    unspoken: 1, unspokenColor: T.dim,   // words not yet spoken in the dim ink, spoken ones in text
    flashA: 0.3,
    visStroke: true,
    calloutOn: true,
  };
  // chapter lights: the theme's six key lights; the rim is the light three chapters on
  const L = T.lights;
  TK.moods = L.concat([L[0]]).map((k, i) => ({ key: k, rim: L[(i + 3) % L.length], glow: TK.moods[Math.min(i, TK.moods.length - 1)].glow }));
  TK.tone = T.tone;
  TK.themeId = T.id;
  TK.theme = T;
}
(function publish() {
  const TK = window.TOKENS, s = document.documentElement.style;
  for (const [k, v] of Object.entries(TK.color)) s.setProperty(`--${k}`, v);
  for (const [k, v] of Object.entries(TK.inks)) s.setProperty(`--i-${k}`, v);
  for (const [k, v] of Object.entries(TK.ons)) s.setProperty(`--on-${k}`, v);
  for (const [k, v] of Object.entries(TK.look)) s.setProperty(`--${k}`, v);
  for (const [k, v] of Object.entries(TK.chrome)) s.setProperty(`--${k}`, v);
  for (const [k, v] of Object.entries(TK.font)) s.setProperty(`--font-${k}`, v);
})();
