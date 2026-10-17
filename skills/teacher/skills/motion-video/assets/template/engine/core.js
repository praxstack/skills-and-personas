// engine/core.js: the frame geometry, the master timeline, line timing, time references and small utilities.
// Everything in a clip sits on ONE paused GSAP timeline (M.tl) at times taken from TIMING lines; film.json names
// those times with references like "q2", "q2:seven hundred", "q2@0.5", "q2.end" (see M.time).
(function () {
  const M = (window.M = window.M || {});
  const T = window.TIMING;
  if (!window.gsap) { window.BOOT_ERROR = 'vendor/gsap.min.js did not load: in source/ run  npm ci && npm run vendor'; return; }
  if (!T || !Array.isArray(T.lines)) { window.BOOT_ERROR = 'timing.js is missing: run  python3 $S/voice.py --project . --emit source/timing.js'; return; }
  gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin, CustomEase);
  CustomEase.create('settle', 'M0,0 C0.18,0.72 0.25,1 1,1');           // fast start, long soft landing
  CustomEase.create('lift', 'M0,0 C0.5,0 0.2,1 1,1');                  // entrances
  const params = new URLSearchParams(location.search);

  M.T = T;
  M.TOTAL = T.total;
  M.params = params;

  // ------------------------------------------------------------------ frame geometry
  // The render size always comes from the timing (script meta width/height). ?aspect=9:16 changes it for a
  // preview only (the editor's aspect buttons), so you can see a layout before re-voicing at another size.
  const ASPECTS = { '16:9': [1920, 1080], '9:16': [1080, 1920], '1:1': [1080, 1080], '4:5': [1080, 1350] };
  let W = T.width || 1920, H = T.height || 1080;
  if (params.get('aspect') && ASPECTS[params.get('aspect')] && !params.has('render')) [W, H] = ASPECTS[params.get('aspect')];
  M.ASPECTS = ASPECTS;
  M.W = W; M.H = H;
  M.u = Math.min(W, H) / 1080;
  M.shape = W >= H * 1.3 ? 'wide' : H >= W * 1.6 ? 'tall' : 'square';   // 4:5 and 1:1 lay out as 'square'
  M.aspect = Object.keys(ASPECTS).find((k) => ASPECTS[k][0] === W && ASPECTS[k][1] === H) || `${W}x${H}`;

  /** Safe areas, in px at 1080 on the short side (scaled by u like everything else, since a platform's overlay
   *  scales with the frame). Wide: 96 px from every edge, captions in the bottom band (quality-bar.md). Tall
   *  (Shorts, Reels, TikTok): the platform draws its title, channel and buttons over the bottom ~430 px and the
   *  right ~120 px, so content and captions stay above and left of them. Square / 4:5: 72 px. */
  M.geometry = (captions) => {
    const u = M.u;
    const m0 = M.shape === 'wide' ? { l: 96, r: 96, t: 80, b: 72 }
      : M.shape === 'tall' ? { l: 72, r: 120, t: 150, b: 430 } : { l: 72, r: 72, t: 64, b: 60 };
    const m = Object.fromEntries(Object.entries(m0).map(([k, v]) => [k, v * u]));
    const chromeH = (M.shape === 'tall' ? 80 : 64) * u;
    const capH = captions ? (M.shape === 'tall' ? 190 : M.shape === 'wide' ? 150 : 140) * u : 0;
    const gap = captions ? 24 * u : 0;
    const safe = { x: m.l, y: m.t, w: W - m.l - m.r, h: H - m.t - m.b };
    const chrome = { x: safe.x, y: safe.y, w: safe.w, h: chromeH };
    const content = { x: safe.x, y: safe.y + chromeH + 24 * u, w: safe.w, h: safe.h - chromeH - 24 * u - capH - gap };
    const cap = captions ? { x: safe.x, y: safe.y + safe.h - capH, w: safe.w, h: capH } : null;
    return { safe, chrome, content, cap, margins: m };
  };

  // ------------------------------------------------------------------ lines: M.L.<id>
  // Each line: start, voiceAt, voiceDur, vEnd (voice ends), think, end, dur, cap, say, chapter, i, next/prev,
  // at('phrase', f) = when the voice says that phrase (from its character position), p(f) = voiceAt + f * voiceDur.
  const lines = T.lines.map((l, i) => ({ ...l, i }));
  lines.forEach((l, i) => {
    l.next = lines[i + 1] || null;
    l.prev = lines[i - 1] || null;
    l.vEnd = l.voiceAt + l.voiceDur;
    l.p = (f) => l.voiceAt + l.voiceDur * f;
    l.at = (phrase, frac = 0) => {
      const s = l.say.toLowerCase();
      const j = s.indexOf(String(phrase).toLowerCase());
      if (j < 0) throw new Error(`line ${l.id}: the phrase "${phrase}" is not in its say text: "${l.say}"`);
      return l.voiceAt + (l.voiceDur * (j + frac * phrase.length)) / s.length;
    };
  });
  M.lines = lines;
  const byId = Object.assign(Object.create(null), Object.fromEntries(lines.map((l) => [l.id, l])));   // no inherited ids ("constructor")
  M.has = (id) => id in byId;
  M.line = (id, where = 'film.json') => {
    if (!(id in byId)) throw new Error(`${where} names line "${id}", but timing.js has no such line. Lines: ${Object.keys(byId).join(' ')}`);
    return byId[id];
  };
  M.lineAt = (t) => lines.find((l) => t >= l.start && t < l.end) || (t >= M.TOTAL - 1e-6 ? lines[lines.length - 1] : null);

  /** A time reference from film.json, resolved to seconds:
   *    "q2"           the moment the voice starts line q2
   *    "q2:phrase"    when the voice says that phrase inside q2 (estimated from its position in the say text)
   *    "q2@0.6"       60% of the way through q2's voice
   *    "q2.start"     the line's slot start (before its lead-in); also .vEnd (voice ends), .end (slot ends),
   *                   .think (the think pause starts = .vEnd)
   *    any of them + " +0.3" or " -0.2"   an offset in seconds (a space before the sign)
   *  A number is taken as seconds (avoid: it will not follow a re-voice). */
  M.time = (ref, where = 'film.json') => {
    if (typeof ref === 'number') return ref;
    if (typeof ref !== 'string' || !ref.trim()) throw new Error(`${where}: a time must name a line, like "q2" or "q2:phrase" (got ${JSON.stringify(ref)})`);
    let s = ref.trim(), off = 0;
    const om = /\s([+-])\s*(\d+(?:\.\d+)?)$/.exec(s);
    if (om) { off = (om[1] === '-' ? -1 : 1) * parseFloat(om[2]); s = s.slice(0, om.index).trim(); }
    let m;
    if ((m = /^([A-Za-z0-9_-]+):(.+)$/.exec(s))) return M.line(m[1], where).at(m[2].trim()) + off;
    if ((m = /^([A-Za-z0-9_-]+)@(\d*\.?\d+)$/.exec(s))) {
      const f = parseFloat(m[2]);   // a share of the line's voice; later than its end is ".end" or an offset
      if (f > 1) throw new Error(`${where}: "${ref}": the share after @ is from 0 to 1; for later use "${m[1]}.vEnd +0.5" or "${m[1]}.end"`);
      return M.line(m[1], where).p(f) + off;
    }
    if ((m = /^([A-Za-z0-9_-]+)\.(start|voice|vEnd|think|end)$/.exec(s))) {
      const l = M.line(m[1], where);
      return { start: l.start, voice: l.voiceAt, vEnd: l.vEnd, think: l.vEnd, end: l.end }[m[2]] + off;
    }
    if (/^[A-Za-z0-9_-]+$/.test(s)) return M.line(s, where).voiceAt + off;
    throw new Error(`${where}: cannot read the time "${ref}" (use "id", "id:phrase", "id@0.5", "id.end", with an optional " +0.3")`);
  };

  // ------------------------------------------------------------------ timeline + tween helpers
  // Two tweens on the same element and property whose time ranges overlap make the frame depend on seek order
  // (single-frame flicker). M.to / M.fromTo / M.set record each target+property; M.warnings lists overlaps and
  // motion_check.mjs prints them. Pass {overlapOk: true} for a deliberate overlap.
  const SPECIAL = new Set(['duration', 'ease', 'delay', 'stagger', 'immediateRender', 'overwrite', 'onComplete', 'onStart',
    'onUpdate', 'repeat', 'yoyo', 'repeatDelay', 'transformOrigin', 'svgOrigin', 'lazy', 'id', 'paused', 'runBackwards',
    'startAt', 'data', 'inherit', 'keyframes', 'snap', 'modifiers', 'overlapOk', 'force3D']);
  const ALIAS = { autoAlpha: ['opacity', 'visibility'], alpha: ['opacity'], scale: ['scaleX', 'scaleY'],
    motionPath: ['x', 'y', 'rotation'], text: ['textContent'] };
  let seen = new WeakMap();
  const label = (el) => (el && el.dataset && el.dataset.k) || (el && el.id ? '#' + el.id : el && el.tagName ? el.tagName.toLowerCase() : 'object');
  function track(targets, vars, pos, dur) {
    if (vars.overlapOk) return;
    // a repeated (or yoyo) tween runs its duration repeat + 1 times, with repeatDelay between the runs
    const reps = typeof vars.repeat === 'number' && vars.repeat > 0 ? vars.repeat : 0;
    dur = dur * (reps + 1) + reps * (+vars.repeatDelay || 0);
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
            if (clash) M.warnings.push(`overlapping tweens on ${label(el)} "${p}": ${e.a.toFixed(2)}-${e.b.toFixed(2)}s and ${a.toFixed(2)}-${b.toFixed(2)}s`);
          }
          list.push({ p, a, b });
        }
      }
    });
  }
  const clean = (v) => { const o = { ...v }; delete o.overlapOk; return o; };
  const num = (t, what) => {
    if (typeof t !== 'number' || !isFinite(t)) throw new Error(`${what}: time must be a number from TIMING (got ${t})`);
    return Math.max(0, t);
  };
  M.reset = () => {
    if (M.tl) M.tl.kill();
    M.tl = gsap.timeline({ paused: true, defaults: { ease: 'power3.out', duration: 0.5, lazy: false } });
    seen = new WeakMap();
    M.warnings = [];
    M.errors = [];
    M.events = [];      // {t, what, end}: visible changes, so motion_check can find lines where nothing happens
    M.notes = [];       // what the engine adjusted on its own (inks darkened for the lit backdrop)
    M.shots = [];       // filled when a build succeeds; empty after one that failed (the editor still lists the shots)
  };
  M.reset();
  M.to = (el, vars, t) => { t = num(t, 'M.to'); track(el, vars, t, vars.duration ?? 0.5); return M.tl.to(el, clean(vars), t); };
  M.fromTo = (el, from, to, t) => {
    t = num(t, 'M.fromTo');
    track(el, { ...from, ...to }, t, to.duration ?? 0.5);
    return M.tl.fromTo(el, clean(from), { immediateRender: false, ...clean(to) }, t);
  };
  M.set = (el, vars, t) => { t = num(t, 'M.set'); track(el, vars, t, 0); return M.tl.set(el, clean(vars), t); };
  M.init = (el, vars) => gsap.set(el, vars);
  M.event = (t, what, end = t) => M.events.push({ t, what, end });   // end: when what it shows has landed
  /** Count a number in el's text from `from` to `to`, formatted (M.fmtNum) on every frame. */
  M.count = (el, t, from, to, fmt, d = 1.1, ease = 'settle') => {
    const o = { v: from };
    el.textContent = M.fmtNum(from, fmt);
    t = num(t, 'M.count');
    track(o, { v: 1 }, t, d);
    M.event(t, 'count');
    return M.tl.fromTo(o, { v: from }, { v: to, duration: d, ease, immediateRender: false, onUpdate: () => { el.textContent = M.fmtNum(o.v, fmt); } }, t);
  };

  // ------------------------------------------------------------------ DOM, text and colour utilities
  const NS = 'http://www.w3.org/2000/svg';
  M.svg = (tag, attrs = {}, parent = null) => {
    const e = document.createElementNS(NS, tag);
    for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  M.el = (tag, cls = '', parent = null, style = null, text = null) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (style) Object.assign(e.style, style);
    if (text !== null && text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  };
  M.esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const sup = (s) => s.replace(/\^\(([^()]*)\)/g, '<sup>$1</sup>').replace(/\^([A-Za-z0-9+]+)/g, '<sup>$1</sup>');

  /** Rich text: *marked words* (highlighted), `code`, x^2 / x^(k+1). Builds one span per word into `parent`
   *  (so words can be revealed one by one) and returns {words, marks}: marks are the highlighted word spans. */
  M.rich = (text, parent, opts = {}) => {
    const words = [], marks = [];
    // *a mark* has no space just inside its stars, so the two in "data/*.csv and 3 * 4" stay characters
    const re = /(\*[^*\s](?:[^*]*[^*\s])?\*|`[^`]+`|\s+|[^\s*`]+|[*`])/g;   // a lone * or ` is just a character
    let m;
    const add = (w, cls) => {
      const s = M.el('span', 'w' + (cls ? ' ' + cls : ''), parent);
      s.innerHTML = sup(M.esc(w));
      words.push(s);
      if (cls && cls.includes('mk')) marks.push(s);
      return s;
    };
    let lone = false;
    while ((m = re.exec(String(text))) !== null) {
      const tok = m[1];
      if (/^\s+$/.test(tok)) { parent.appendChild(document.createTextNode(' ')); continue; }
      if (tok.length > 1 && tok.startsWith('*') && tok.endsWith('*')) {
        tok.slice(1, -1).split(/\s+/).forEach((w, i, a) => {
          add(w, 'mk');
          if (i < a.length - 1) parent.appendChild(document.createTextNode(' '));
        });
      } else if (tok.length > 1 && tok.startsWith('`')) add(tok.slice(1, -1), 'code');
      else if (words.length && (tok === '*' || tok === '`' || lone) && parent.lastChild === words[words.length - 1] && !/\b(mk|code)\b/.test(parent.lastChild.className)) {
        // a lone * or ` and what follows it stay in the word they touch (data/*.csv is one word)
        parent.lastChild.innerHTML += sup(M.esc(tok));
      } else add(tok, opts.cls || '');
      lone = tok === '*' || tok === '`';
    }
    return { words, marks };
  };
  /** Shrink el's font size from `size` until it fits w x h (it must be in the DOM), stopping at `min`.
   *  Returns the size used; warns when it hit the floor and still overflows. */
  M.fit = (el, w, h, size, min = LOOK.TYPE.min * M.u, what = 'text') => {
    let s = size;
    el.style.fontSize = s + 'px';
    while (s > min && (el.scrollWidth > w + 1 || el.scrollHeight > h + 1)) { s = Math.max(min, s - 2 * M.u); el.style.fontSize = s + 'px'; }
    if (el.scrollWidth > w + 1 || el.scrollHeight > h + 1) M.warnings.push(`${what} does not fit its box even at ${Math.round(s)} px: shorten it or give the block more room`);
    return s;
  };
  const cv = document.createElement('canvas').getContext('2d');
  M.textW = (text, font) => { cv.font = font; return cv.measureText(text).width; };

  M.rng = (seed) => () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  M.clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  M.lerp = (a, b, f) => a + (b - a) * f;
  M.smooth = (x) => { x = M.clamp(x); return x * x * (3 - 2 * x); };
  const hex3 = (c) => { const n = parseInt(String(c).slice(1, 7), 16); return [(n >> 16) & 255, (n >> 8) & 255, n & 255]; };
  const lum = (c) => { const v = hex3(c).map((x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4; }); return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]; };
  M.contrast = (p, q) => { const a = lum(p), b = lum(q); return (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05); };
  M.rgba = (c, a) => { const [r, g, b] = hex3(c); return `rgba(${r},${g},${b},${a})`; };
  /** Straight sRGB blend (what alpha compositing does): f = 0 gives a, f = 1 gives b. */
  M.mix = (a, b, f) => '#' + hex3(a).map((x, i) => Math.round(x + (hex3(b)[i] - x) * f).toString(16).padStart(2, '0')).join('');
  /** The strongest tint of `fill` over `ground` (up to `max`) that still keeps `ink` at 4.7:1 on it. */
  M.tint = (fill, ground, ink, max = 0.3) => {
    let a = max;
    while (a > 0.03 && M.contrast(ink, M.mix(ground, fill, a)) < 4.7) a = Math.round((a - 0.01) * 100) / 100;
    return M.mix(ground, fill, a);
  };
  // a tone is one of the hues; a misspelt one is an error (it would quietly turn into accent and mean the wrong thing)
  M.hue = (name) => {
    if (name === undefined || name === null || name === '') return 'accent';
    if (!LOOK.HUES.includes(name)) throw new Error(`tone ${JSON.stringify(name)} is not one of ${LOOK.HUES.join(', ')} (leave it out for the default)`);
    return name;
  };
  let uid = 0;
  M.uid = (p = 'm') => `${p}${++uid}`;

  // ------------------------------------------------------------------ numbers
  /** Format a number: fmt "int" (1,234), "0.0" (one decimal), "pct" (42%), "pct0.0", "compact" (12.3k),
   *  "x" (3.4x), "money" ($1,234), "money:₹" (₹1,234), "time" (m:ss); anything else: as is with 0-2 decimals. */
  M.fmtNum = (v, fmt = 'auto') => {
    if (typeof v !== 'number' || !isFinite(v)) return String(v ?? '');
    const grp = (n, d) => n.toLocaleString('en-US', { minimumFractionDigits: d, maximumFractionDigits: d });
    const dec = /^(?:pct)?0\.(0+)$/.exec(fmt);
    if (fmt === 'int') return grp(Math.round(v), 0);
    if (dec && !fmt.startsWith('pct')) return grp(v, dec[1].length);
    if (fmt === 'pct') return grp(Math.round(v), 0) + '%';
    if (dec && fmt.startsWith('pct')) return grp(v, dec[1].length) + '%';
    if (fmt === 'x') return grp(v, v < 10 ? 1 : 0) + 'x';
    if (fmt === 'compact') {
      const a = Math.abs(v);
      return a >= 1e9 ? grp(v / 1e9, 1) + 'B' : a >= 1e6 ? grp(v / 1e6, 1) + 'M' : a >= 1e4 ? grp(v / 1e3, 1) + 'k' : grp(Math.round(v), 0);
    }
    // a negative amount or duration takes one sign in front: -$1,200 and -0:30 (not $-1,200 or -1:-30)
    if (fmt && fmt.startsWith('money')) { const r = Math.round(v); return (r < 0 ? '-' : '') + (fmt.split(':')[1] || '$') + grp(Math.abs(r), 0); }
    if (fmt === 'time') { const r = Math.round(v), s = Math.abs(r); return `${r < 0 ? '-' : ''}${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`; }
    return Number.isInteger(v) ? grp(v, 0) : grp(v, Math.abs(v) < 10 ? 1 : 0);
  };
})();
