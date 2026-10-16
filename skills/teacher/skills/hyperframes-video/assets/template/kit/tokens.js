/* kit/tokens.js: the ONE place for the film's look: palette, chapter lights, fonts, sizes, layout bands.
   Change the style here (from the brief's Style section); kit.css reads every colour as a CSS variable (--accent,
   --good, ...) and the JS kit reads KIT.tok, so nothing else needs editing to restyle a film.

   Themes (references/hyperframes-guide.md, "Themes"): index.html loads theme.js before this file. The shipped
   theme.js sets window.THEME = null, which keeps the kit's own palette below ("original", the verified look,
   unchanged). `theme.py emit <id> --format global --out source/theme.js` replaces it with a registry theme, and
   the mapping at the end of this file puts that theme's tokens onto the kit's roles:
     surfaces bg bg2 panel panel2 line line2 deep, text ink/mute/dim -> text/muted/dim,
     fills accent good bad cool gold violet warm (shapes, strokes, lights), inks <hue>Ink (text in a hue),
     on-fills on<Hue> (labels on a filled shape), chapter key lights = THEME.lights, rim lights = the same list
     turned by three, and the light-ground switches (grain blend, softer glows, shadows instead of black). */
window.KIT = window.KIT || {};
KIT.tok = {
  tone: 'dark',
  themed: false,
  theme: 'original',
  color: {
    bg: '#0B0B0D',      // near-black base
    bg2: '#17151F',     // gradient partner (a hint of blue-violet)
    deep: '#0D0C10',    // the deepest shade (themes: under the caption band and the vignette)
    slab: '#0d0c10',    // chapter sting slabs, lower thirds, stamps (themes: panel)
    panel: '#16151B',   // cards, code, tables
    panel2: '#201E27',
    line: '#2E2B36',    // hairlines
    chip: '#201E27',    // weight chips on edges (a text well: themes push it away from the inks)
    cell: '#16151B',    // table cells (a text well)
    line2: '#46424F',
    edge: '#46424F',    // idle graph edges and node rims (a shape: about 3:1 on the ground in themes)
    ink: '#F2EDE4',     // text
    mute: '#B8B2A7',    // secondary text: 8.2:1 on panels, so it stays above 4.5:1 inside a stepped-back (0.8) group
    dim: '#9C968B',     // the dimmest text colour (never stepped back further): 5.9:1 on panels, 6.7:1 on the background
    accent: '#FF5B2E',  // signal orange: the thing being looked at
    accentText: '#FF7F55', // the same orange for TEXT on the chapter light (accent is 4.25:1 on the outro green): 5.27:1 measured
    good: '#7BE3B5',    // mint: valid / the answer
    bad: '#FF4F6E',     // rose: illegal / wrong
    badDeep: '#B81C40', // a deeper rose for a burst lettered in white ("NOPE!": 5.2:1 under the word)
    cool: '#6FA8FF',    // cool rim light, secondary highlight
    gold: '#FFC857',    // comic bursts, emphasis in captions
    violet: '#A98BFF',
    warm: '#FF8A3D',
    // inks: text in a hue. The original palette letters such text in the fill itself (all pass on its dark ground).
    accentInk: '#FF5B2E', goodInk: '#7BE3B5', badInk: '#FF4F6E', coolInk: '#6FA8FF', goldInk: '#FFC857', violetInk: '#A98BFF', warmInk: '#FF8A3D',
    // on-fills: a label on a filled shape of that hue (tags, lit node numbers, badges)
    onAccent: '#140c08', onGood: '#140c08', onBad: '#140c08', onCool: '#140c08', onGold: '#140c08', onViolet: '#140c08', onWarm: '#140c08',
    onReject: '#160608', onCheck: '#0e1a14', onBadge: '#140b05', // the original's per-piece near-blacks (themes: on<Hue>)
    // pieces
    node: ['#3B3846', '#1E1C25', '#151419'],     // node disc: highlight, body, rim of the radial gradient
    mascot: { top: '#FF8A55', bot: '#E8461C', line: '#7a2108', eye: '#1a0d07', foot: '#a3300d' },
    gloss: '#ffffff',   // specular highlights (node gloss, mascot shine)
    spark: '#ffffff',   // the marching dashes on a held route
    cover: '#1a1920',   // decoder: the panel colour laid over a used token
    lineNo: '#9A94A3',  // code line numbers (full strength while code lines step back)
    syntax: { kw: '#FF8A5C', ty: '#7FB2FF', nu: '#FFC857', cm: '#B4AEA3', fn: '#7BE3B5', st: '#E3A6FF', op: '#c9c3b8' },
    rungCx: '#C4BEB3',  // the ladder's time / space line
    dots: ['#FF5F57', '#FEBC2E', '#28C840'], // the code window's traffic lights
    burst: { hi: '#FFF3C4', line: '#120d0a', word: '#ffffff', wordLine: '#120d0a', drop: '#120d0a', dropA: 1 },
  },
  // Key light per chapter index (0 intro, 1 problem, 2 brute, 3 intuition, 4 approaches, 5 code): warm to neon,
  // the way the reference film's light moves through a day. Extra chapters reuse the list cyclically.
  light: ['#FF6A2E', '#FF8A3D', '#FF3F7F', '#3F8CFF', '#8C6BFF', '#2FD39A'],
  rim: ['#3F8CFF', '#5A7DFF', '#7B5CFF', '#24C6C8', '#FF5BA8', '#FF8A3D'],
  // the light colour as TEXT (sting numbers, the chapter tag number): the original letters them in the light itself
  lightInk: ['#FF6A2E', '#FF8A3D', '#FF3F7F', '#3F8CFF', '#8C6BFF', '#2FD39A'],
  // light and shadow strengths (dark ground). A light theme turns glows down and shadows into soft tints.
  fx: {
    shadow: '0,0,0',    // rgb of every drop shadow
    shadowK: 1,         // multiplier on the drop-shadow alphas
    lightK: 1,          // multiplier on the chapter key / rim / horizon light alphas
    bokehK: 1,
    floorK: 1,
    glow: [0.13, 0.32], // the two halo strokes under a route (outer, inner)
    fireGlow: [0.18, 0.42],
    flyGlow: (c) => `0 0 12px ${c}`, // the text shadow of a decoder copy in flight
    grainBlend: 'overlay', grainOpacity: 0.07,
    vignette: 'rgba(0,0,0,0)', vignetteEdge: 'rgba(0,0,0,0.62)',
    sweep: 'rgba(255,255,255,0.10)',
    scrim: ['rgba(5,5,7,0)', 'rgba(5,5,7,0.72)', 'rgba(5,5,7,0.82)'], // the caption band
    capGlow: 'rgba(0,0,0,0.9)',
    panelTop: 'rgba(34,32,42,0.94)', panelBot: 'rgba(20,19,25,0.94)',
    tint: null,         // themes: (fill, alpha) -> an opaque highlight colour every ink reads on (null: fill at alpha)
  },
  font: {
    display: '"Inter Display", "InterLocal", "Inter", "DejaVu Sans", sans-serif',
    body: '"InterLocal", "Inter", "DejaVu Sans", sans-serif',
    mono: '"JBM", "DejaVu Sans Mono", monospace',
    comic: '"Bangers", "Inter Display", "InterLocal", sans-serif',
  },
  // px at 1080p. Nothing under 26 (quality-bar.md): labels and chips are 30, code 30 to 36.
  // world: the smallest on-screen size of text that lives in the world layer (weight chips, node tags, values).
  // Those labels counter-scale when the camera zooms out (camera.js writes --inv = 1/zoom on #world), so a wide
  // shot shrinks the graph but never its numbers.
  size: { title: 116, headline: 84, body: 44, caption: 40, code: 30, label: 30, chip: 30, world: 32, node: 30 },
  // Stepped-back state for context that is not the focus (ladder rungs, code lines): visibly dimmer, still 4.5:1.
  // Focus is shown with colour, a border or a highlight bar, never by fading text toward invisible.
  dimOpacity: 0.8,
  safe: 96,          // keep text this far from every edge
  captionBottom: 84, // caption baseline band (bottom 180 px is reserved for captions)
  mono: 0.6,         // JetBrains Mono advance width in em (layout math for code, decoder, chips)
};

/* ---------------------------------------------------------------- colour helpers (pure, deterministic) */
KIT.col = (function () {
  const rgb = (h) => { h = String(h).replace('#', ''); if (h.length === 3) h = h.replace(/./g, '$&$&'); return [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16)); };
  const hex = (c) => '#' + c.map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, '0')).join('').toUpperCase();
  const mix = (a, b, t) => { const x = rgb(a), y = rgb(b); return hex(x.map((v, i) => v + (y[i] - v) * t)); };
  const lum = (h) => { const c = rgb(h).map((v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; };
  const ratio = (a, b) => { const p = lum(a), q = lum(b); return (Math.max(p, q) + 0.05) / (Math.min(p, q) + 0.05); };
  const rgba = (h, a) => `rgba(${rgb(h).join(',')},${+a.toFixed(3)})`;
  /** move `c` toward `to` until it clears `need`:1 on every colour of `on` (or reaches `to`). */
  const ensure = (c, on, need, to) => { for (let t = 0; t <= 1.0001; t += 0.02) { const x = mix(c, to, t); if (on.every((s) => ratio(x, s) >= need)) return x; } return to; };
  return { rgb, hex, mix, lum, ratio, rgba, ensure };
})();

/* ---------------------------------------------------------------- a registry theme onto the kit's roles */
(function () {
  const TH = window.THEME;
  if (!TH) return; // original: the palette above, untouched
  const C = KIT.col, tok = KIT.tok, light = TH.tone === 'light';
  const HUES = ['accent', 'good', 'bad', 'cool', 'gold', 'violet', 'warm'];
  const cap = (s) => s[0].toUpperCase() + s.slice(1);
  const well = light ? C.mix(TH.panel, '#FFFFFF', 0.6) : C.mix(TH.panel, TH.deep, 0.6);
  const c = {
    bg: TH.bg, bg2: TH.bg2, deep: TH.deep, slab: TH.panel, panel: TH.panel, panel2: TH.panel2, line: TH.line, line2: TH.line2,
    edge: C.ensure(TH.line2, [TH.bg, TH.bg2], 3.0, TH.text),
    // text wells (weight chips, table cells): the panel pushed away from the inks (lighter on light grounds, darker
    // on dark ones), so hue inks keep a margin over 4.6:1 under the grain, vignette and chapter light
    chip: well, cell: well,
    ink: TH.text, mute: TH.muted, dim: TH.dim,
    accentText: TH.accentInk, badDeep: TH.bad,
    onReject: TH.onBad, onCheck: TH.onGood, onBadge: TH.onAccent,
    gloss: '#FFFFFF', spark: light ? TH.bg : '#FFFFFF',
    cover: C.mix(TH.panel2, TH.panel, 0.5),
    lineNo: TH.dim,
    syntax: { kw: TH.accentInk, ty: TH.coolInk, nu: TH.goldInk, cm: TH.dim, fn: TH.goodInk, st: TH.violetInk, op: TH.muted },
    rungCx: TH.muted,
    dots: [TH.bad, TH.warm, TH.good],
  };
  // fills stay as shipped, except a fill too close to the ground to read as a shape (under 3:1 on bg, which only
  // happens on light grounds): it moves toward its own ink (same hue) until it clears 3:1. Its on-colour is the
  // theme's when that still clears 4.6:1 on the moved fill, else whichever of text / bg reads best on it.
  HUES.forEach((h) => {
    const f = C.ratio(TH[h], TH.bg) >= 3 && C.ratio(TH[h], TH.bg2) >= 3 ? TH[h] : C.ensure(TH[h], [TH.bg, TH.bg2], 3.0, TH[h + 'Ink']);
    let on = TH['on' + cap(h)];
    if (f !== TH[h]) on = [on, TH.text, TH.bg, '#111111', '#FFFFFF'].sort((x, y) => C.ratio(y, f) - C.ratio(x, f))[0];
    c[h] = f; c[h + 'Ink'] = TH[h + 'Ink']; c['on' + cap(h)] = on;
    // a pill lettered in its on-colour (START / STOP tags): bold letter-spaced mono on a mid fill measured under the
    // pair's ratio (tokyonight-day's 5.0:1 STOP read 4.49:1), so the pill's fill steps away from its letters until
    // the pair has 6.3:1 (at 5.6:1 the vignette over a dark ground still took github-dimmed's STOP to 4.25:1); a
    // pill that already has it keeps the fill
    const away = C.lum(on) < C.lum(f) ? '#FFFFFF' : '#000000';
    let pill = f;
    // a dark-lettered pill on a dark ground can also sit under a card's drop shadow (q1's "1 STOP" under the question
    // card: github-dark's 7.5:1 gold read 4.30:1), so it also clears 5.0:1 with its fill 30% shaded toward black
    const shaded = (p) => (light || away === '#000000' ? 99 : C.ratio(on, C.mix(p, '#000000', 0.3)));
    for (let t = 0; t <= 0.5001 && (C.ratio(on, pill) < 6.3 || shaded(pill) < 5.0); t += 0.02) pill = C.mix(f, away, t);
    c[h + 'Pill'] = pill;
  });
  // text in a hue (kickers, accent words, code tokens): the theme solves these inks to 4.6:1, but glowing or
  // lit text measured under it (tokyonight-storm's accent kicker 4.45:1), so they get 5.4:1 on every text surface
  const textOn = [TH.bg, TH.bg2, TH.panel, TH.panel2, well];
  HUES.forEach((h) => { c[h + 'Ink'] = C.ensure(TH[h + 'Ink'], textOn, 5.4, light ? '#000000' : '#FFFFFF'); });
  c.accentText = c.accentInk;
  // labels (.lbl: table heads and row names, widget labels) stand on the backdrop, not a panel, so a light pool
  // behind them shows through (ayu-mirage's "round 0" read 3.96:1 in muted): they get 6.0:1 on every text surface
  c.label = C.ensure(TH.muted, textOn, 6.0, TH.text);
  // ... and on dark grounds a glow pool can lift the backdrop by about 15% toward the text (ayu-mirage's "new" and
  // "round 0" still read 4.27:1 at 6.0:1), so they also clear 5.2:1 on those lit grounds
  if (!light) c.label = C.ensure(c.label, textOn.map((g) => C.mix(g, TH.text, 0.15)), 5.2, TH.text);
  c.syntax = { kw: c.accentInk, ty: c.coolInk, nu: c.goldInk, cm: TH.dim, fn: c.goodInk, st: c.violetInk, op: TH.muted };
  // node discs: a lit top-left on dark grounds; on light grounds a paper-white top fading to the panel tone
  c.node = light ? [C.mix(TH.panel, '#FFFFFF', 0.7), TH.panel, TH.panel2] : [C.mix(TH.panel2, TH.line2, 0.45), TH.panel2, TH.panel];
  // the mascot is the accent, shaded from it (never a fixed orange)
  c.mascot = { top: C.mix(TH.accent, '#FFFFFF', 0.22), bot: C.mix(TH.accent, '#000000', 0.12), line: C.mix(TH.accent, '#000000', 0.6), eye: C.mix(TH.accent, '#000000', 0.86), foot: C.mix(TH.accent, '#000000', 0.38) };
  // comic burst: the word takes the burst fill's on-colour; its outline is the opposite end, the drop is the shadow
  c.burst = { hi: null, line: light ? TH.text : TH.shadow, word: null, wordLine: null, drop: TH.shadow, dropA: light ? 0.3 : 1 };
  Object.assign(tok.color, c);
  // chapter lights: the theme's six, rims are the same list turned by three; light-as-text uses that hue's ink
  const hueOf = (hx) => {
    let best = 'accent', bd = 1e9;
    HUES.forEach((h) => { const a = C.rgb(TH[h]), b = C.rgb(hx), d = a.reduce((s, v, i) => s + (v - b[i]) ** 2, 0); if (d < bd) { bd = d; best = h; } });
    return best;
  };
  tok.hueOf = hueOf;
  tok.light = TH.lights.slice();
  tok.rim = TH.lights.map((_, i) => TH.lights[(i + 3) % TH.lights.length]);
  tok.lightInk = TH.lights.map((l) => TH[hueOf(l) + 'Ink']);
  tok.tone = light ? 'light' : 'dark';
  tok.themed = true;
  tok.theme = TH.id;
  const sh = C.rgb(TH.shadow).join(',');
  Object.assign(tok.fx, light ? {
    // shadowK 0.2: a card's 60 px shadow falls on the world under it; at 0.4 it darkened a gold STOP chip 18%
    // (onGold 5.85:1 -> 4.11:1 on pastel-lavender). At 0.2 it darkens under 10%, which keeps 4.8:1.
    shadow: sh, shadowK: 0.2, lightK: 0.55, bokehK: 0.6, floorK: 0.8,
    glow: [0.07, 0.2], fireGlow: [0.1, 0.26],
    flyGlow: () => `0 2px 8px ${C.rgba(TH.shadow, 0.22)}`,
    grainBlend: 'multiply', grainOpacity: 0.03,
    vignette: C.rgba(TH.deep, 0), vignetteEdge: C.rgba(C.mix(TH.deep, TH.shadow, 0.08), 0.85),
    sweep: C.rgba('#FFFFFF', 0.35),
    scrim: [C.rgba(TH.deep, 0), C.rgba(TH.deep, 0.72), C.rgba(TH.deep, 0.82)],
    capGlow: C.rgba(TH.bg, 0.9),
  } : {
    shadow: sh, shadowK: 1, lightK: 0.7, bokehK: 0.8, floorK: 1, // theme muted/inks have less margin over the key light than the original's
    grainBlend: 'screen', grainOpacity: 0.03,
    vignette: C.rgba(TH.deep, 0), vignetteEdge: C.rgba(TH.deep, 0.75),
    scrim: [C.rgba(TH.deep, 0), C.rgba(TH.deep, 0.72), C.rgba(TH.deep, 0.82)],
    capGlow: C.rgba(TH.shadow, 0.9),
    // a decoder copy in flight: a tight dark halo under a softer glow in its tone (a full-strength glow lit the
    // ground behind its letters: [2,0,100] read 3.33:1 and 4.45:1 on tokyonight-storm and nord-frost)
    flyGlow: (g) => `0 0 3px ${C.rgba(TH.deep, 0.9)}, 0 0 14px ${C.rgba(g, 0.45)}`,
  });
  tok.fx.panelTop = C.rgba(light ? C.mix(TH.panel, '#FFFFFF', 0.35) : TH.panel2, 0.94);
  tok.fx.panelBot = C.rgba(TH.panel, 0.94);
  // inks clear 4.6:1 at full strength only; context steps back by opacity only as far as every ink still clears 4.6
  const inks = [TH.text, TH.muted, TH.dim, ...HUES.map((h) => TH[h + 'Ink'])];
  let op = 0.8;
  const passes = (a) => inks.every((i) => [TH.panel, TH.panel2].every((s) => C.ratio(C.mix(s, i, a), s) >= 4.6));
  while (op < 1 && !passes(op)) op = +(op + 0.01).toFixed(2);
  tok.dimOpacity = op;
  // a highlight under text (code cursor, decoder token, marked cell): the panel tinted with the fill at the asked
  // strength, with the panel first pushed away from the inks (lighter on light grounds, darker on dark ones) just
  // as far as every ink on it still clears 4.65:1. An opaque colour, so it reads the same on any panel.
  const away = light ? '#FFFFFF' : '#000000';
  tok.fx.tint = (fill, want) => {
    const ok = (x) => inks.every((i) => C.ratio(i, x) >= 4.9);
    for (let b = 0; b <= 1.0001; b += 0.05) { const x = C.mix(C.mix(well, away, b), fill, want); if (ok(x)) return x; }
    for (let a = want; a > 0; a -= 0.01) { const x = C.mix(away, fill, a); if (ok(x)) return x; }
    return away;
  };
})();

(function () {
  const r = document.documentElement.style, tok = KIT.tok, fx = tok.fx;
  for (const [k, v] of Object.entries(tok.color)) if (typeof v === 'string') r.setProperty('--' + k, v);
  for (const [k, v] of Object.entries(tok.color.syntax)) r.setProperty('--tk-' + k, v);
  for (const [k, v] of Object.entries(tok.font)) r.setProperty('--f-' + k, v);
  for (const [k, v] of Object.entries(tok.size)) r.setProperty('--s-' + k, v + 'px');
  const sh = (a) => `rgba(${fx.shadow},${+(a * fx.shadowK).toFixed(3)})`;
  r.setProperty('--sh45', sh(0.45)); r.setProperty('--sh55', sh(0.55)); r.setProperty('--sh60', sh(0.6));
  r.setProperty('--vig0', fx.vignette); r.setProperty('--vig1', fx.vignetteEdge);
  r.setProperty('--sweep', fx.sweep);
  fx.scrim.forEach((s, i) => r.setProperty('--scrim' + i, s));
  r.setProperty('--capglow', fx.capGlow);
  r.setProperty('--rim03', 'rgba(255,255,255,0.03)'); r.setProperty('--rim05', 'rgba(255,255,255,0.05)'); // panel bevel
  r.setProperty('--panel-top', fx.panelTop); r.setProperty('--panel-bot', fx.panelBot);
  r.setProperty('--burst-word', tok.color.burst.word || '#ffffff');
  r.setProperty('--burst-line', tok.color.burst.wordLine || tok.color.burst.line);
  r.setProperty('--grain-blend', fx.grainBlend); r.setProperty('--grain-op', String(fx.grainOpacity));
})();
