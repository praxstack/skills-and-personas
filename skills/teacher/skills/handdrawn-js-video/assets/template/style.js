// style.js: every colour, font, size and texture setting in one place.
// Pick the look with STYLE_NAME. Scenes never hard-code colours: they use S.* (and S.node[i] for the subject).
//   'paper'     warm paper cut-outs with torn white edges and drop shadows, hand lettering   (default)
//   'chalk'     slate chalkboard, chalk strokes drawn on, no shadows
//   'blueprint' deep blue drafting paper with a grid, white line work
//   'whiteboard' marker on a whiteboard (a dark glass board on dark themes); the graph draws itself (kit/styles/whiteboard.js)
//   'papercraft-riso' cut-paper pieces printed in halftone spot inks, stop-motion drops (kit/styles/papercraft-riso.js)
//   'watercolor' layered washes that bloom in, a brush-pen ink line, cold-press paper (kit/styles/watercolor.js)
// A preview can override it with index.html?style=chalk (the render always uses STYLE_NAME).
'use strict';
const STYLE_NAME = 'paper';

// Pip the mascot (kit/mascot.js). Skin, hair and eyes stay natural in every theme; a registry theme recolours the clothes.
const PIP_COLOURS = { skin: '#F2C29B', hair: '#3B2A2A', coat: '#2FA58F', coat2: '#28917D', scarf: '#E2725B', hat: '#F2C14E', hat2: '#E0A63A', legs: '#2B2F5E', boots: '#4A2F2F', pack: '#E2725B', rim: '#FFF8EC', eye: '#1A1530', cheek: '#F29B9B', shine: '#fff' };

const FONT = { hand: 'Patrick Hand', brush: 'Caveat Brush', mono: 'JetBrains Mono' };

const THEMES = {
  paper: {
    kind: 'paper',
    // backdrop
    bg: '#F0E0C1', bgDeep: '#E2C99D', bgLight: '#FCF4E3', fiber: 'rgba(140,100,50,.045)', fiberLight: 'rgba(255,252,240,.16)',
    vignette: 'rgba(90,55,20,.28)', grain: 0.45, deepBlob: 0.6,   // deepBlob scales the dark mottling (text sits on it)
    // ink and cards (inkFaint is for lines and rings only, never text: it is under 3:1; inkSoft is the darkest secondary
    // ink that still reaches 4.5:1 measured on the darkest paper under a label, so it is nearly the ink itself)
    ink: '#24284A', inkSoft: '#292A3A', inkFaint: 'rgba(36,40,74,.32)',
    card: '#FCF8EE', cardEdge: '#FFFFFF', cardInk: '#24284A', rule: '#C3D3EC', margin: '#EBA8A4',
    sticky: '#F7D774', kraft: '#D6B98A', tape: 'rgba(240,205,120,.80)',
    shadow: 'rgba(70,45,20,.34)', shadowBlur: 16, shadowY: 9, shadowX: 4, tornEdge: 5,
    // meaning colours
    accent: '#E2603F', cool: '#1F9A86', gold: '#F0B23A', lilac: '#8A6BD0', sky: '#4F86D9',
    good: '#2F9A58', bad: '#D63D35', hl: 'rgba(255,208,70,.55)', glow: 'rgba(255,196,80,.55)',
    // text in a meaning colour is drawn in its deep shade (drawText swaps it in). Every shade reaches 4.5:1 measured by
    // legibility.py on the darkest paper a label sits on (the mottled tan under the vignette, about #C0B298); shapes
    // (trails, rings, fills) keep the bright colour
    txt: { accent: '#501A0C', cool: '#0A312B', gold: '#3A2805', lilac: '#331F5E', sky: '#122B53', good: '#0F321D', bad: '#541511' },
    node: ['#E2725B', '#2FA58F', '#F2B544', '#8E6FD1', '#4F86D9', '#E58FB0', '#7DBA5A', '#C9824A'],
    nodeInk: ['#24284A', '#24284A', '#24284A', '#24284A', '#24284A', '#24284A', '#24284A', '#24284A'],  // 3.6-7.8:1 on the discs
    burst: ['#E2503A', '#FFD34D'],
    // code colours: every one is at least 8:1 on the card (thin 32 px mono strokes measure well under their colour's
    // ratio); codeDim is the one colour of de-emphasised lines, the focused lines keep these colours and turn bold
    syntax: { kw: '#1C4592', type: '#7E2D1A', num: '#0B513C', str: '#633288', com: '#45475D', fn: '#723C0C', txt: '#24284A' },
    codeDim: '#45475D',
    // line work
    stroke: { w: 3.6, rough: 1.5, passes: 2, chalk: false },
    boilFps: 10, boilAmp: 1.0, jitter: 0.55,   // line boil changes 10x a second; cut-outs jitter like stop motion
    grainBoil: false,                          // true: grain flickers with the boil (livelier, ~1.5x bigger MP4)
    // every other colour the kit draws (kept here so nothing in kit/ or scenes.js hard-codes one)
    warm: '#E2725B', halo: 'rgba(251,243,226,.9)', goodSoft: '#E9F7D8', costTag: '#FFF3C4', spark: '#FFFBEA', sheen: 'rgba(255,255,255,.35)',
    tagHole: 'rgba(36,40,74,.45)', tapeShine: '#fff', curl: ['rgba(90,60,30,0)', 'rgba(90,60,30,.10)'], burstHalo: '#FFF8E6',
    crease: ['rgba(255,255,250,.22)', 'rgba(90,60,30,.07)'], keyLight: ['rgba(255,246,220,.30)', 'rgba(255,246,220,0)'],
    grainSpecks: ['rgba(255,250,235,.10)', 'rgba(20,12,4,.10)'], shade: '#3C2612', shadeK: 1, chipTo: '#FFFFFF', chipK: 0.38,
    hills: ['#CFC99A', '#E7BE8E'], cloud: '#FBF3E1', pipShadow: 'rgba(40,25,10,.25)',
    plane: { under: '#D9CBAE', mid: '#ECE3CC', top: '#FCF8EE', crease: 'rgba(90,80,60,.45)', wind: 'rgba(80,60,40,.45)' },
    capBand: 'rgba(0,0,0,.35)', lineFill: 'rgba(255,255,255,.06)', boardFill: '#000000', grid: '#EAF3FF', smudge: '#E6F0E6',
    mascot: true,
  },
  chalk: {
    kind: 'chalk',
    bg: '#25312D', bgDeep: '#1B2421', bgLight: '#33423C', fiber: 'rgba(230,240,230,.035)', fiberLight: 'rgba(230,240,230,.05)',
    vignette: 'rgba(5,10,8,.55)', grain: 0.45,
    ink: '#F3F1E7', inkSoft: '#BFC6BC', inkFaint: 'rgba(243,241,231,.30)',
    card: '#2E3B36', cardEdge: '#F3F1E7', cardInk: '#F3F1E7', rule: 'rgba(243,241,231,.10)', margin: 'rgba(240,140,130,.35)',
    sticky: '#3A4A44', kraft: '#2E3B36', tape: 'rgba(243,241,231,.0)',
    shadow: 'rgba(0,0,0,0)', shadowBlur: 0, shadowY: 0, shadowX: 0, tornEdge: 0,
    accent: '#FF9C7A', cool: '#7FE0C8', gold: '#FFE08A', lilac: '#C9B2FF', sky: '#9CC8FF',
    good: '#9BE39B', bad: '#FF8A80', hl: 'rgba(255,224,138,.22)', glow: 'rgba(255,240,180,.35)',
    node: ['#FF9C7A', '#7FE0C8', '#FFE08A', '#C9B2FF', '#9CC8FF', '#FFB3D1', '#B9E58C', '#E8B98A'],
    nodeInk: ['#25312D', '#25312D', '#25312D', '#25312D', '#25312D', '#25312D', '#25312D', '#25312D'],
    burst: ['#FF9C7A', '#FFE08A'],
    syntax: { kw: '#9CC8FF', type: '#FF9C7A', num: '#B9E58C', str: '#FFB3D1', com: '#A9B4AD', fn: '#FFE08A', txt: '#F3F1E7' },
    codeDim: '#AEB7AE',
    stroke: { w: 3.8, rough: 1.7, passes: 2, chalk: true },
    boilFps: 8, boilAmp: 1.1, jitter: 0,
    warm: '#E8B98A', halo: 'rgba(0,0,0,.35)', goodSoft: '#E9F7D8', costTag: undefined, spark: '#FFFBEA', sheen: 'rgba(255,255,255,.35)',
    tagHole: 'rgba(0,0,0,0)', tapeShine: '#fff', curl: ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], burstHalo: null,
    crease: ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], keyLight: ['rgba(255,255,255,.06)', 'rgba(255,246,220,0)'],
    grainSpecks: ['rgba(255,250,235,.10)', 'rgba(20,12,4,.10)'], shade: '#000000', shadeK: 1.6, chipTo: '#FFFFFF', chipK: 0.38,
    hills: ['#CFC99A', '#E7BE8E'], cloud: '#FBF3E1', pipShadow: 'rgba(40,25,10,.25)',
    plane: { under: '#D9CBAE', mid: '#ECE3CC', top: '#FCF8EE', crease: 'rgba(90,80,60,.45)', wind: 'rgba(80,60,40,.45)' },
    capBand: 'rgba(0,0,0,.35)', lineFill: 'rgba(255,255,255,.06)', boardFill: '#000000', grid: '#EAF3FF', smudge: '#E6F0E6',
    mascot: false,
  },
  blueprint: {
    kind: 'blueprint',
    bg: '#14457E', bgDeep: '#0E3463', bgLight: '#1D5596', fiber: 'rgba(255,255,255,.035)', fiberLight: 'rgba(255,255,255,.04)',
    vignette: 'rgba(3,15,40,.55)', grain: 0.4,
    ink: '#EAF3FF', inkSoft: '#A9C6EA', inkFaint: 'rgba(234,243,255,.32)',
    card: '#1A4F8E', cardEdge: '#EAF3FF', cardInk: '#EAF3FF', rule: 'rgba(234,243,255,.10)', margin: 'rgba(255,170,150,.35)',
    sticky: '#1F5A9C', kraft: '#1A4F8E', tape: 'rgba(0,0,0,0)',
    shadow: 'rgba(0,0,0,0)', shadowBlur: 0, shadowY: 0, shadowX: 0, tornEdge: 0,
    accent: '#FFB38A', cool: '#7FF0E0', gold: '#FFE27A', lilac: '#D2C0FF', sky: '#BFE0FF',
    good: '#A6F0A6', bad: '#FF9A8A', hl: 'rgba(255,226,122,.20)', glow: 'rgba(200,230,255,.35)',
    node: ['#FFB38A', '#7FF0E0', '#FFE27A', '#D2C0FF', '#BFE0FF', '#FFC2DA', '#C4F09A', '#F0C79A'],
    nodeInk: ['#14457E', '#14457E', '#14457E', '#14457E', '#14457E', '#14457E', '#14457E', '#14457E'],
    burst: ['#FFB38A', '#FFE27A'],
    syntax: { kw: '#BFE0FF', type: '#FFB38A', num: '#C4F09A', str: '#FFC2DA', com: '#A9C6EA', fn: '#FFE27A', txt: '#EAF3FF' },
    codeDim: '#A9C6EA',
    stroke: { w: 2.6, rough: 1.1, passes: 2, chalk: false },
    boilFps: 12, boilAmp: 0.8, jitter: 0,
    warm: '#E8B98A', halo: 'rgba(0,0,0,.35)', goodSoft: '#E9F7D8', costTag: undefined, spark: '#FFFBEA', sheen: 'rgba(255,255,255,.35)',
    tagHole: 'rgba(0,0,0,0)', tapeShine: '#fff', curl: ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], burstHalo: null,
    crease: ['rgba(0,0,0,0)', 'rgba(0,0,0,0)'], keyLight: ['rgba(255,255,255,.06)', 'rgba(255,246,220,0)'],
    grainSpecks: ['rgba(255,250,235,.10)', 'rgba(20,12,4,.10)'], shade: '#000000', shadeK: 1.6, chipTo: '#FFFFFF', chipK: 0.38,
    hills: ['#CFC99A', '#E7BE8E'], cloud: '#FBF3E1', pipShadow: 'rgba(40,25,10,.25)',
    plane: { under: '#D9CBAE', mid: '#ECE3CC', top: '#FCF8EE', crease: 'rgba(90,80,60,.45)', wind: 'rgba(80,60,40,.45)' },
    capBand: 'rgba(0,0,0,.35)', lineFill: 'rgba(255,255,255,.06)', boardFill: '#000000', grid: '#EAF3FF', smudge: '#E6F0E6',
    mascot: false,
  },
};

// Type sizes at 1080p (quality bar: headline 72-96, body 40-48, captions 38-44, code 30-36, nothing under 26).
// legibility.py measures the tallest glyph standing on the baseline, so a hand-lettered word made only of short
// letters ("new", "src") measures about 0.66 of its font size, and a Caveat Brush word about 0.6: keep text on the
// open paper at `label` or more, and small sizes (`small`, `tag`) for tags and cards with dark ink only.
// `tagMin`/`markMin` are the smallest scale a weight tag or a node mark may shrink to with the graph.
const SIZE = { title: 118, headline: 84, chapter: 88, chapterCorner: 0.56, body: 44, label: 40, small: 34, caption: 42, code: 32, table: 46,
  tag: 34, tagMin: 0.94, mark: 44, markMin: 1, chip: 34, head: 32, rowLabel: 36 };

// ------------------------------------------------------------------ registry themes (scripts/themes.json)
// source/theme.js sets window.THEME. The shipped file sets it to null: the style keeps its own palette above
// ('original', untouched). `python3 $S/theme.py emit <id> --format global --out source/theme.js` writes a registry
// theme there; themeStyle() then maps its tokens onto the style's roles (references/handdrawn-guide.md, "Themes").
// Fills stay fills; text gets the theme's solved inks; light themes keep the paper look (white cut-outs on a
// tinted paper, multiply grain, soft shadows instead of glows), dark ones become dark paper with light ink.
const THEME_ = (typeof window !== 'undefined' && window.THEME) || null;
const Colour = (() => {
  const rgb = (h) => { const n = parseInt(h.slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const hex = (c) => '#' + c.map((v) => Math.round(Math.max(0, Math.min(255, v))).toString(16).padStart(2, '0')).join('').toUpperCase();
  const mix = (a, b, u) => { const p = rgb(a), q = rgb(b); return hex(p.map((v, i) => v + (q[i] - v) * u)); };
  const alpha = (h, a) => { const [r, g, b] = rgb(h); return `rgba(${r},${g},${b},${a})`; };
  const lum = (h) => { const [r, g, b] = rgb(h).map((v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * r + 0.7152 * g + 0.0722 * b; };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const worst = (c, surfaces) => Math.min(...surfaces.map((s) => ratio(c, s)));
  // move c toward black or white (whichever side its surfaces leave room on) until it reaches `target` on all of them
  const ensure = (c, surfaces, target) => {
    if (worst(c, surfaces) >= target) return c;
    const end = lum(c) < surfaces.reduce((a, s) => a + lum(s), 0) / surfaces.length ? '#000000' : '#FFFFFF';
    for (let u = 0.04; u <= 1.0001; u += 0.04) { const m = mix(c, end, u); if (worst(m, surfaces) >= target) return m; }
    return end;
  };
  return { rgb, hex, mix, alpha, lum, ratio, worst, ensure };
})();

function themeStyle(base, T) {
  const { mix, alpha: A, lum, ratio } = Colour, dark = T.tone === 'dark';
  // the paper: dark themes use bg (mottled toward deep and bg2); light themes use deep as the paper and bg (a touch
  // whiter) for the cards, so cut-outs stand off the paper the way cream cards stand off the tan original. Every
  // surface text sits on stays between the theme's own surfaces, where its inks are solved.
  const ground = dark ? T.bg : T.deep;
  const card = dark ? mix(T.bg, lum(T.panel) >= lum(T.bg) ? T.panel : T.panel2, 0.55) : mix(T.bg, '#FFFFFF', 0.35);
  const hlA = dark ? 0.14 : 0.38, hlCard = mix(card, T.gold, hlA); // a highlighter swipe on a card (text sits on it)
  // every surface text sits on: the paper, the cards, a highlighted row. The hand fonts and thin mono strokes measure
  // well under their colour's nominal ratio, so text colours get headroom over the theme's 4.6:1 inks
  const surf = [ground, card, hlCard, T.bg2];
  // the overlay (buildOverlay) lays a white key light, then the vignette, over text and its surface alike, so both
  // drift toward one colour and the ratio drops (latte's 11:1 code measured 4.1:1 under the original's 0.28 key
  // light). So the key light is gentler here, and every ink must also reach SEEN on the colours as seen under the
  // overlay where text sits: off it, under the key light, and toward the left and right edges where the vignette
  // deepens (about 0.6 of its corner alpha at the code board and the side labels). legibility.py measures thin
  // strokes about 0.9 of the colour pair's ratio, so SEEN keeps 4.5:1 with a margin
  const vig = dark ? [T.deep, 0.6] : [mix(T.deep, T.shadow, 0.35), 0.26], key = dark ? 0 : 0.16, SEEN = 5.6;
  const fx = dark ? [[0, vig[1] * 0.3]] : [[key, 0], [key * 0.75, vig[1] * 0.6], [key * 0.4, vig[1] * 0.75]];
  const seen = (c, k, v) => mix(mix(c, '#FFFFFF', k), vig[0], v);
  const ok = (c, ss, target) => Colour.worst(c, ss) >= target
    && fx.every(([k, v]) => ss.every((s) => ratio(seen(c, k, v), seen(s, k, v)) >= Math.min(target, SEEN)));
  const ensure = (c, ss, target) => {
    if (ok(c, ss, target)) return c;
    const end = lum(c) < ss.reduce((a, s) => a + lum(s), 0) / ss.length ? '#000000' : '#FFFFFF';
    for (let u = 0.04; u <= 1.0001; u += 0.04) { const m = mix(c, end, u); if (ok(m, ss, target)) return m; }
    return end;
  };
  const lift = (c, target) => ensure(c, surf, target);
  const fills = { accent: T.accent, warm: T.warm, good: T.good, bad: T.bad, cool: T.cool, gold: T.gold, violet: T.violet };
  const onOf = Object.fromEntries(Object.entries(fills).map(([k, v]) => [v, T['on' + k[0].toUpperCase() + k.slice(1)]]));
  // ink for a label on a filled shape: the theme's on<Hue> for its own fills, else the best of text / bg / deep
  const inkOn = (fill) => {
    // (the theme solves on<Hue> to 4.6:1, but brush lettering on a textured fill measures under that: 700! on
    // latte's gold read 3.9:1, so it is lifted to 6.5:1 like the other inks)
    const c = onOf[fill] && ratio(onOf[fill], fill) >= 4.6 ? onOf[fill] : [T.text, T.bg].sort((a, b) => ratio(b, fill) - ratio(a, fill))[0];
    return ensure(c, [fill], 6.5);
  };
  const node = [T.warm, T.cool, T.gold, T.violet, T.accent, T.bad, T.good, mix(T.warm, T.gold, 0.5)];
  // the burst's inner star carries brush lettering in inkOn: where no ink reaches 6.5:1 on the theme's gold
  // (tokyonight-day's dark gold: white measured 4.22:1), the star's fill steps toward white or black, whichever
  // gets a readable ink soonest
  const burstIn = (() => {
    const reads = (f) => ok(inkOn(f), [f], 6.5);
    if (reads(T.gold)) return T.gold;
    for (let u = 0.04; u <= 0.6001; u += 0.04) for (const end of ['#FFFFFF', '#000000']) { const f = mix(T.gold, end, u); if (reads(f)) return f; }
    return T.gold;
  })();
  const edge = dark ? mix(card, T.text, 0.22) : '#FFFFFF';
  const deepInk = (c) => ensure(c, [card, hlCard], 6.5); // code is thin 32 px mono: it measures well under its colour's ratio
  const th = {
    ...base,
    bg: ground, bgDeep: dark ? T.deep : ground, bgLight: dark ? T.bg2 : T.bg,
    fiber: dark ? A('#000000', 0.10) : A(T.shadow, 0.045), fiberLight: dark ? A(T.text, 0.03) : A('#FFFFFF', 0.16),
    vignette: A(vig[0], vig[1]), grain: dark ? 0.32 : 0.4, deepBlob: dark ? 1 : 0.6,
    grainBlend: dark ? 'screen' : 'multiply', grainSpecks: [A('#FFFFFF', 0.10), A('#000000', 0.10)],
    ink: lift(T.text, 8.5), inkSoft: lift(T.muted, 6.5), inkFaint: A(T.text, 0.32),
    card, cardEdge: edge, cardInk: lift(T.text, 8.5), rule: mix(card, T.accent, dark ? 0.28 : 0.3), margin: mix(card, T.bad, 0.45),
    sticky: mix(card, T.gold, 0.45), kraft: mix(card, T.warm, 0.3), tape: dark ? A(T.gold, 0.42) : A(mix(T.gold, '#FFFFFF', 0.3), 0.75),
    shadow: dark ? A('#000000', 0.55) : A(T.shadow, 0.28),
    accent: T.accent, cool: T.cool, gold: T.gold, lilac: T.violet, sky: T.accent, warm: T.warm,
    good: T.good, bad: T.bad, hl: A(T.gold, hlA), glow: A(T.gold, dark ? 0.42 : 0.38),
    txt: { accent: lift(T.accentInk, 6), cool: lift(T.coolInk, 6), gold: lift(T.goldInk, 6), lilac: lift(T.violetInk, 6), sky: lift(T.accentInk, 6), good: lift(T.goodInk, 6), bad: lift(T.badInk, 6), warm: lift(T.warmInk, 6) },
    node, nodeInk: node.map(inkOn), burst: [T.warm, burstIn],
    syntax: { kw: deepInk(T.accentInk), type: deepInk(T.warmInk), num: deepInk(T.goodInk), str: deepInk(T.violetInk), com: ensure(T.dim, [card], 6), fn: deepInk(T.goldInk), txt: deepInk(T.text) },
    codeDim: ensure(T.dim, [card], 6),
    halo: dark ? A(T.deep, 0.85) : A(card, 0.9), goodSoft: mix(T.good, '#FFFFFF', dark ? 0.5 : 0.8),
    costTag: dark ? mix(card, T.gold, 0.22) : mix(T.gold, '#FFFFFF', 0.72), spark: dark ? mix(T.gold, '#FFFFFF', 0.6) : '#FFFFFF',
    tagHole: dark ? A(T.deep, 0.7) : A(T.text, 0.45), curl: [A(T.shadow, 0), A(T.shadow, dark ? 0.18 : 0.1)], burstHalo: null,
    crease: [dark ? A(T.text, 0.04) : A('#FFFFFF', 0.22), A(dark ? '#000000' : T.shadow, dark ? 0.18 : 0.07)],
    keyLight: dark ? null : [A('#FFFFFF', key), A('#FFFFFF', 0)], lights: T.lights, lightA: 0.07,
    shade: dark ? T.deep : T.shadow, shadeK: dark ? 2.4 : 0.8, chipTo: card, chipK: dark ? 0.7 : 0.45,
    hills: dark ? [mix(T.deep, T.good, 0.12), mix(T.deep, T.warm, 0.12)] : [mix(ground, T.good, 0.22), mix(ground, T.warm, 0.2)],
    cloud: dark ? mix(T.bg, T.text, 0.1) : mix(card, '#FFFFFF', 0.5), pipShadow: A(dark ? '#000000' : T.shadow, dark ? 0.35 : 0.25),
    plane: dark ? { under: mix(T.text, card, 0.5), mid: mix(T.text, card, 0.3), top: mix(T.text, card, 0.1), crease: A(T.deep, 0.45), wind: A(T.text, 0.45) }
      : { under: mix(card, T.deep, 0.75), mid: mix(card, T.deep, 0.35), top: card, crease: A(T.shadow, 0.35), wind: A(T.shadow, 0.4) },
    pip: { coat: T.cool, coat2: mix(T.cool, '#000000', 0.12), scarf: T.warm, pack: T.warm, hat: T.gold, hat2: mix(T.gold, '#000000', 0.1),
      legs: dark ? mix(T.accent, T.deep, 0.45) : mix(T.accent, T.text, 0.55), boots: mix(T.warm, '#000000', 0.6), rim: edge },
    glowShadow: dark ? null : A(T.shadow, 0.3),   // light grounds: a glow would read as a smudge, so it becomes a soft shadow
    inkOn, theme: T,
  };
  return th;
}

// A style from kit/styles/ (STYLE_DEFS) starts from a built-in palette (its `base`, recoloured by the theme) and its
// palette() returns the full token set; its hooks replace kit drawing (kit/styles/index.js). Built-ins have no hooks.
const STYLE_DEFS_ = typeof STYLE_DEFS !== 'undefined' ? STYLE_DEFS : {};
let STYLE = {};
const S = (() => {
  let name = STYLE_NAME;
  try { const q = new URLSearchParams(location.search).get('style'); if (q && (THEMES[q] || STYLE_DEFS_[q]) && !/render/.test(location.search)) name = q; } catch (e) { /* no location */ }
  STYLE = STYLE_DEFS_[name] || {};
  const base = THEMES[name] || THEMES[STYLE.base || 'paper'], txtOf = {};
  let th = THEME_ ? themeStyle(base, THEME_) : base;
  if (STYLE.palette) th = STYLE.palette(th, THEME_, Colour);
  for (const [k, v] of Object.entries(th.txt || {})) if (th[k]) txtOf[th[k]] = v; // bright colour -> its text shade
  const inkOn = th.inkOn || ((fill, orig) => orig ?? th.nodeInk[0]); // original: each call site keeps its own ink
  return Object.assign({ name, font: STYLE.font ? { ...FONT, ...STYLE.font } : FONT, size: STYLE.size ? { ...SIZE, ...STYLE.size } : SIZE, txtOf, codeDim: th.inkSoft }, th, { inkOn });
})();
