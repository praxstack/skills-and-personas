// kit/core.js: the master timeline, line lookup, tween helpers that catch fighting tweens, small utilities.
// Everything in the film is placed on ONE paused GSAP timeline (K.tl) at times taken from TIMING lines.
// Never hard-code seconds: use L.<id>.voiceAt, L.<id>.at('phrase'), L.<id>.vEnd, L.<id>.end.
(function () {
  const K = (window.K = window.K || {});
  const T = window.TIMING;
  if (!window.gsap) { window.BOOT_ERROR = 'vendor/gsap.min.js did not load: in source/ run  npm ci && npm run vendor'; return; }
  if (!T || !Array.isArray(T.lines)) { window.BOOT_ERROR = 'timing.js is missing: run  python3 $S/voice.py --project . --emit source/timing.js'; return; }
  gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin, MorphSVGPlugin, TextPlugin, CustomEase);

  K.T = T;
  K.W = T.width || 1920;
  K.H = T.height || 1080;
  K.TOTAL = T.total;
  K.C = TOKENS.color;      // fills (areas, thick strokes, glows)
  K.I = TOKENS.inks;       // text and thin strokes in a hue
  K.O = TOKENS.ons;        // text on a fill of that hue
  K.U = TOKENS.look;       // every other kit colour, by role
  K.FX = TOKENS.fx;        // atmosphere numbers and blend modes
  K.tone = TOKENS.tone || 'dark';
  K.F = TOKENS.font;
  K.Z = TOKENS.size;
  K.SAFE = { l: TOKENS.safe, t: TOKENS.safe, r: K.W - TOKENS.safe, b: K.H - TOKENS.captionBand };
  // lazy:false makes first renders happen inside seek() instead of on the next tick (frames are seeked, not played)
  K.tl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out', duration: 0.5, lazy: false } });

  // ------------------------------------------------------------------ lines: L.<id>
  // Each line: start, voiceAt, voiceDur, vEnd (voice ends), think, end, dur, cap, say, chapter, scene, i,
  // next/prev, at('phrase', frac) = when the voice says that phrase (estimated from its character position),
  // p(f) = voiceAt + f * voiceDur.
  const lines = T.lines.map((l, i) => ({ ...l, i }));
  lines.forEach((l, i) => {
    l.next = lines[i + 1] || null;
    l.prev = lines[i - 1] || null;
    l.vEnd = l.voiceAt + l.voiceDur;
    l.p = (f) => l.voiceAt + l.voiceDur * f;
    l.at = (phrase, frac = 0) => {
      const s = l.say.toLowerCase();
      const j = s.indexOf(String(phrase).toLowerCase());
      if (j < 0) throw new Error(`line ${l.id}: phrase "${phrase}" is not in its say text: "${l.say}"`);
      return l.voiceAt + (l.voiceDur * (j + frac * phrase.length)) / s.length;
    };
  });
  K.lines = lines;
  const byId = Object.fromEntries(lines.map((l) => [l.id, l]));
  K.L = new Proxy(byId, {
    get(o, k) {
      if (typeof k === 'string' && !(k in o) && !['then', 'toJSON', 'constructor'].includes(k))
        throw new Error(`scenes.js uses line "${k}", but timing.js has no such line. Lines: ${Object.keys(o).join(' ')}`);
      return o[k];
    },
  });
  K.has = (id) => id in byId;
  K.chapter = (n) => T.chapters.find((c) => c.n === n);

  // ------------------------------------------------------------------ tween helpers (with a fight detector)
  // Two tweens on the same element+property whose time ranges overlap make the frame depend on seek order
  // (that is where single-frame A-B-A flicker comes from). K.to/K.fromTo/K.set record every target+property
  // and K.warnings lists the overlaps; gsap_check.mjs prints them. Pass {overlapOk: true} to silence one.
  const SPECIAL = new Set(['duration', 'ease', 'delay', 'stagger', 'immediateRender', 'overwrite', 'onComplete', 'onStart',
    'onUpdate', 'repeat', 'yoyo', 'repeatDelay', 'transformOrigin', 'svgOrigin', 'smoothOrigin', 'lazy', 'id', 'paused',
    'callbackScope', 'runBackwards', 'startAt', 'data', 'inherit', 'keyframes', 'snap', 'modifiers', 'overlapOk', 'force3D']);
  const ALIAS = { autoAlpha: ['opacity', 'visibility'], alpha: ['opacity'], scale: ['scaleX', 'scaleY'],
    motionPath: ['x', 'y', 'rotation'], text: ['textContent'] };
  const seen = new WeakMap();
  K.warnings = [];
  K.moments = [];   // short-lived events (bursts, stamps) gsap_check.mjs also audits: {id, t}
  const label = (el) => (el && el.id ? '#' + el.id : el && el.getAttribute && el.getAttribute('data-k') ? el.getAttribute('data-k')
    : el && el.tagName ? el.tagName.toLowerCase() + (el.className && el.className.baseVal === undefined && el.className ? '.' + String(el.className).split(' ')[0] : '') : 'object');
  function track(targets, vars, pos, dur) {
    if (vars.overlapOk) return;
    const els = gsap.utils.toArray(targets);
    const st = vars.stagger ? (typeof vars.stagger === 'number' ? vars.stagger : vars.stagger.each || 0) : 0;
    els.forEach((el, i) => {
      if (!el || typeof el !== 'object') return;
      const a = pos + st * i, b = a + dur;
      let list = seen.get(el);
      if (!list) seen.set(el, (list = []));
      for (const key of Object.keys(vars)) {
        if (SPECIAL.has(key)) continue;
        for (const p of ALIAS[key] || [key]) {
          for (const e of list) {
            if (e.p !== p) continue;
            const clash = (dur > 1e-4 && e.b - e.a > 1e-4 && a < e.b - 1e-3 && e.a < b - 1e-3) ||
              (dur <= 1e-4 && a > e.a + 1e-3 && a < e.b - 1e-3) || (e.b - e.a <= 1e-4 && e.a > a + 1e-3 && e.a < b - 1e-3);
            if (clash) K.warnings.push(`overlapping tweens on ${label(el)} "${p}": ${e.a.toFixed(2)}-${e.b.toFixed(2)}s and ${a.toFixed(2)}-${b.toFixed(2)}s`);
          }
          list.push({ p, a, b });
        }
      }
    });
  }
  const clean = (v) => { const o = { ...v }; delete o.overlapOk; return o; };
  const num = (t, what) => {
    if (typeof t !== 'number' || !isFinite(t)) throw new Error(`${what}: time must be a number from TIMING (got ${t})`);
    return t;
  };
  /** K.to(el, vars, t): tween from the current state to vars, starting at absolute time t. */
  K.to = (el, vars, t) => {
    num(t, 'K.to');
    track(el, vars, t, vars.duration ?? 0.5);
    return K.tl.to(el, clean(vars), t);
  };
  /** K.fromTo(el, from, to, t): explicit start values; immediateRender is off so earlier frames are untouched. */
  K.fromTo = (el, from, to, t) => {
    num(t, 'K.fromTo');
    track(el, { ...from, ...to }, t, to.duration ?? 0.5);
    return K.tl.fromTo(el, clean(from), { immediateRender: false, ...clean(to) }, t);
  };
  /** K.set(el, vars, t): instant change at time t (reverts when seeking back before t). */
  K.set = (el, vars, t) => {
    num(t, 'K.set');
    track(el, vars, t, 0);
    return K.tl.set(el, clean(vars), t);
  };
  /** K.init(el, vars): the state before the film starts (build time, not on the timeline). */
  K.init = (el, vars) => gsap.set(el, vars);

  // common moves
  K.fadeIn = (el, t, d = 0.45, extra = {}) => K.fromTo(el, { autoAlpha: 0, y: extra.dy ?? 18 }, { autoAlpha: 1, y: 0, duration: d, ease: 'power3.out' }, t);
  K.fadeOut = (el, t, d = 0.3) => K.to(el, { autoAlpha: 0, duration: d, ease: 'power2.in' }, t);
  K.pop = (el, t, d = 0.55, s0 = 0.3) => K.fromTo(el, { autoAlpha: 0, scale: s0 }, { autoAlpha: 1, scale: 1, duration: d, ease: 'back.out(2.2)' }, t);
  /** K.pulse(el, t): a quick scale bump that returns to 1 (needs nothing else tweening el's scale then). */
  K.pulse = (el, t, s = 1.18, d = 0.5) => {
    K.to(el, { scale: s, duration: d * 0.4, ease: 'power2.out' }, t);
    return K.to(el, { scale: 1, duration: d * 0.6, ease: 'power2.inOut' }, t + d * 0.4);
  };
  /** K.count(el, t, to, d): tick a number in el's text from its current value to `to`. */
  K.count = (el, t, to, d = 0.6) => K.to(el, { textContent: to, snap: { textContent: 1 }, duration: d, ease: 'power1.inOut' }, t);

  // ------------------------------------------------------------------ DOM / SVG / text utilities
  const NS = 'http://www.w3.org/2000/svg';
  K.svg = (tag, attrs = {}, parent = null) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  K.html = (tag, cls = '', inner = null, parent = null, style = null) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (inner !== null && inner !== undefined) e.innerHTML = inner;
    if (style) Object.assign(e.style, style);
    if (parent) parent.appendChild(e);
    return e;
  };
  K.esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  /** K.fmt('O(n^(k+1))') -> HTML with real superscripts; also n^2, 2^k. Escapes everything else. */
  K.fmt = (s) => K.esc(s)
    .replace(/\^\(([^()]*(?:\([^()]*\))?[^()]*)\)/g, '<sup>$1</sup>')
    .replace(/\^([A-Za-z0-9]+)/g, '<sup>$1</sup>');
  const cv = document.createElement('canvas').getContext('2d');
  /** K.textW('flights', '600 30px "JetBrains Mono"'): width in px (call after fonts load: inside Film.build). */
  K.textW = (text, font) => { cv.font = font; return cv.measureText(text).width; };
  /** Largest font size <= max whose text fits maxW. */
  K.fit = (text, fontTpl, maxW, max, min = 20) => {
    for (let s = max; s > min; s -= 2) if (K.textW(text, fontTpl.replace('{s}', s)) <= maxW) return s;
    return min;
  };
  K.rng = (seed) => () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  K.clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  K.lerp = (a, b, f) => a + (b - a) * f;
  /** Colour by name ('accent', 'mint'...) or pass any CSS colour through. This is the FILL: areas, thick strokes. */
  K.col = (c) => (c && K.C[c]) || c || K.C.accent;
  const nameOf = (c) => (c && K.C[c] ? c : Object.keys(K.C).find((k) => K.C[k] === c));
  /** The palette name of a colour (name or fill value), or undefined. */
  K.nameOf = nameOf;
  /** Text (and thin strokes) in a hue: the theme's solved ink. In the original palette it is the fill itself. */
  K.ink = (c) => { const n = nameOf(c ?? 'accent'); return n ? K.I[n] : c; };
  const hex3 = (c) => { const n = parseInt(String(c).slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const lum = (c) => { const v = hex3(c).map((x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  /** WCAG contrast of two #rrggbb colours. */
  K.contrast = (p, q) => { const a = lum(p), b = lum(q); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
  /** Text on a filled shape: the theme's on<Hue> for a palette fill, else text or bg, whichever reads better. */
  K.on = (c) => {
    const n = nameOf(c ?? 'accent');
    if (n) return K.O[n];
    if (!TOKENS.theme || !/^#[0-9a-f]{6}$/i.test(String(c))) return K.C.black;
    const T = TOKENS.theme;
    return K.contrast(c, T.text) >= K.contrast(c, T.bg) ? T.text : T.bg;
  };
  /** rgba() of a #rrggbb colour. */
  K.rgba = (c, a) => { const [r, g, b] = hex3(c); return `rgba(${r},${g},${b},${a})`; };
  /** A hue as a visible STROKE: in a theme, a fill too close to the ground (under 3:1 against bg) is moved
   *  towards its ink until it reaches 3:1, keeping the hue. In the original palette: the fill, unchanged. */
  const visCache = {};
  K.vis = (c) => {
    const f = K.col(c);
    if (!K.FX.visStroke || !/^#[0-9a-f]{6}$/i.test(f)) return f;
    if (visCache[f]) return visCache[f];
    const bg = TOKENS.theme.bg, ink = K.ink(f);
    if (K.contrast(f, bg) >= 3 || !/^#[0-9a-f]{6}$/i.test(ink)) return (visCache[f] = f);
    const mix = (k) => '#' + hex3(f).map((x, i) => Math.round(x + (hex3(ink)[i] - x) * k).toString(16).padStart(2, '0')).join('');
    let k = 0;
    while (k < 1 && K.contrast(mix(k), bg) < 3) k += 0.05;
    return (visCache[f] = mix(Math.min(1, k)));
  };
  /** Text in a hue on a table cell. Original: the hue's ink. A theme: the solved ink sits near 4.6:1, so on a cell
   *  it is moved towards the body text until it reads 6.3:1 on the cell, leaving room for the flash tint under it. */
  const cellCache = {};
  K.cellInk = (c) => {
    const i = K.ink(c);
    if (!TOKENS.theme || !/^#[0-9a-f]{6}$/i.test(i) || !/^#[0-9a-f]{6}$/i.test(K.C.ink)) return i;
    if (cellCache[i]) return cellCache[i];
    const mix = (k) => '#' + hex3(i).map((x, j) => Math.round(x + (hex3(K.C.ink)[j] - x) * k).toString(16).padStart(2, '0')).join('');
    let k = 0;
    while (k < 1 && [K.C.bg2, K.C.panel].some((b) => K.contrast(mix(k), b) < 6.3)) k = Math.round((k + 0.05) * 100) / 100;
    return (cellCache[i] = mix(Math.min(1, k)));
  };
  /** A tint of a fill for a flash under text (themes), or the solid fill (original palette). In a theme the tint
   *  is thinned until the hue's cell ink and the body text both keep 4.7:1 on it (the gate is 4.5, measured to 4%) over the cell, panel and ground (a
   *  cell caught mid-flash read 4.27:1 at 0.3 on tokyonight-storm); where they already do, it is FX.flashA. */
  const flashCache = {};
  K.flashCol = (c) => {
    const f = K.col(c);
    if (!K.FX.flashA || !/^#[0-9a-f]{6}$/i.test(f)) return f;
    if (flashCache[f]) return flashCache[f];
    const mix = (b, a) => '#' + hex3(b).map((x, i) => Math.round(x + (hex3(f)[i] - x) * a).toString(16).padStart(2, '0')).join('');
    const inks = [K.cellInk(f), K.C.ink].filter((x) => /^#[0-9a-f]{6}$/i.test(x));
    const under = [K.C.bg2, K.C.panel, K.C.bg].filter((x) => /^#[0-9a-f]{6}$/i.test(x));
    let a = K.FX.flashA;
    while (a > 0.04 && under.some((b) => inks.some((i) => K.contrast(i, mix(b, a)) < 4.7))) a = Math.round((a - 0.02) * 100) / 100;
    return (flashCache[f] = K.rgba(f, a));
  };
  let uid = 0;
  K.uid = (p = 'k') => `${p}${++uid}`;
})();
