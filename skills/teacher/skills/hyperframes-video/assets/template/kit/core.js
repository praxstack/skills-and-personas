/* kit/core.js: the film timeline, timing lookups, layers, DOM/SVG builders and the small tween helpers that every
   other kit file and every scene uses.

   Rules this file enforces (each one fixed a real defect in an earlier render):
   - Every tween goes on ONE paused timeline, KIT.tl, at an ABSOLUTE time taken from timing.js (KIT.L.<id>.voiceAt
     and friends). Never hard-code seconds: re-voicing a line moves its picture with it.
   - Entrances use fromTo(..., {immediateRender: false}); the hidden start state is set once at build time
     (KIT.hidden). That prevents the one-frame A-B-A flicker qa.py looks for.
   - Undrawn strokes stay at opacity 0 until they start drawing (round caps would show a dot). */
(function () {
  'use strict';
  const K = window.KIT;
  const T = window.TIMING;
  if (!T || !T.lines) throw new Error('timing.js is missing or empty: run voice.py --emit source/timing.js');
  gsap.registerPlugin(DrawSVGPlugin, MotionPathPlugin, SplitText, TextPlugin, CustomEase);

  // ------------------------------------------------------------------ timing
  K.T = T;
  const lines = {};
  T.lines.forEach((l, i) => {
    l.index = i;
    l.voiceEnd = +(l.voiceAt + l.voiceDur).toFixed(3);   // the voice stops here
    l.thinkEnd = +(l.voiceEnd + (l.think || 0)).toFixed(3); // the think pause ends here
    lines[l.id] = l;
  });
  const strict = (obj, what) => new Proxy(obj, {
    get(o, k) {
      if (typeof k !== 'string' || k in o || k === 'then' || k === 'toJSON') return o[k];
      throw new Error(`KIT.${what}.${k}: no ${what === 'L' ? 'line' : 'scene'} "${k}" in timing.js (have: ${Object.keys(o).join(', ')})`);
    },
  });
  K.L = strict(lines, 'L');           // KIT.L.p3.voiceAt, .voiceEnd, .thinkEnd, .start, .end, .cap, .say
  K.has = (id) => id in lines;
  const scenes = {};
  T.scenes.forEach((s) => { scenes[s.id] = s; });
  K.SC = strict(scenes, 'SC');        // KIT.SC.ex1.start / .end
  K.chapters = T.chapters;            // [{n, name, start, end}]
  K.chapter = (n) => T.chapters.find((c) => c.n === n);
  K.lineAt = (t) => T.lines.find((l) => t >= l.start && t < l.end) || T.lines[T.lines.length - 1];

  /** Time at which `phrase` is spoken inside a line, estimated from its position in `say` (within ~0.3 s). */
  K.cue = (line, phrase, offset = 0) => {
    const say = line.say.toLowerCase(), i = say.indexOf(String(phrase).toLowerCase());
    if (i < 0) throw new Error(`KIT.cue: "${phrase}" is not in the say of ${line.id}: "${line.say}"`);
    return +(line.voiceAt + (line.voiceDur * i) / say.length + offset).toFixed(3);
  };
  /** Time at fraction f (0..1) of a line's spoken part. */
  K.frac = (line, f) => +(line.voiceAt + line.voiceDur * f).toFixed(3);

  // ------------------------------------------------------------------ layers
  const $ = (id) => document.getElementById(id);
  K.layer = {
    root: $('root'), bg: $('bg'), scene: $('scene'), cam: $('cam'), drift: $('drift'), world: $('world'), wsvg: $('wsvg'),
    whtml: $('whtml'), hud: $('hud'), hudsvg: $('hudsvg'), chrome: $('chrome'), cards: $('cards'), caps: $('caps'), fx: $('fx'),
  };

  // ------------------------------------------------------------------ builders
  const UNITLESS = /opacity|zIndex|fontWeight|lineHeight|flex|order|scale/;
  /** K.esc(s): text from the script (titles, chapter names, captions) is data; escape it before any html argument. */
  K.esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  /** HTML element: K.el('div', 'chip mono', parent, {left: 100, top: 40}, 'text'). Numbers become px. */
  K.el = (tag, cls, parent, style, html) => {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (style) for (const k in style) e.style[k] = typeof style[k] === 'number' && !UNITLESS.test(k) ? style[k] + 'px' : style[k];
    if (html != null) e.innerHTML = html;
    (parent || K.layer.hud).appendChild(e);
    return e;
  };
  const NS = 'http://www.w3.org/2000/svg';
  /** SVG element: K.svg('circle', {r: 10}, parent). */
  K.svg = (tag, attrs, parent) => {
    const e = document.createElementNS(NS, tag);
    if (attrs) for (const k in attrs) e.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(e);
    return e;
  };
  K.text = (parent, x, y, str, attrs) => {
    const t = K.svg('text', Object.assign({ x, y, 'text-anchor': 'middle', 'dominant-baseline': 'central' }, attrs || {}), parent);
    t.textContent = str;
    return t;
  };
  /** World-layer text sizes. The camera keeps --inv = 1 / zoom on #world, so these hold a floor of `min` px on screen:
   *  K.wfs(base)     a CSS font-size: `base` world px, grown when the camera pulls back (HTML labels in #whtml, SVG text)
   *  K.wscale(base)  a CSS transform for an SVG group drawn at `base` px (chip pills: the pill grows with its text)
   *  K.wgrow(base)   the same factor as a CSS number, for offsets that must grow with the label */
  K.wgrow = (base, min = K.tok.size.world) => `max(1, calc(${+(min / base).toFixed(4)} * var(--inv, 1)))`;
  K.wfs = (base, min = K.tok.size.world) => `max(${base}px, calc(${min}px * var(--inv, 1)))`;
  K.wscale = (base, min = K.tok.size.world) => `scale(${K.wgrow(base, min)})`;
  /** Mark decorative full-frame pieces (lights, grain, vignette, scrims) so `hyperframes check` audits only content. */
  K.decor = (el) => { el.setAttribute('data-layout-ignore', ''); return el; };
  /** A drop-shadow colour at alpha a (black on dark grounds; a soft deep tint, weaker, on light ones). */
  K.shade = (a) => `rgba(${K.tok.fx.shadow},${+(a * K.tok.fx.shadowK).toFixed(3)})`;
  K.defs = (svg) => svg.querySelector('defs') || K.svg('defs', {}, svg);
  /** Colour by role (every value comes from kit/tokens.js):
   *  K.tone(name)   a FILL: shapes, thick strokes, borders, glows ('accent', 'good', ... or a hex)
   *  K.ink(name)    TEXT in that hue (<hue>Ink; 'ink' / 'mute' / 'dim' are text already)
   *  K.on(name, r)  text ON a filled shape of that hue (on<Hue>; the original palette keeps its own role r)
   *  K.tint(c, a)   a highlight under text: colour c at alpha a (a theme makes it an opaque colour every ink clears 4.65:1 on) */
  K.tone = (name) => (!name ? K.tok.color.ink : name[0] === '#' ? name : K.tok.color[name] || name);
  // a hex tone maps to the nearest theme hue; 'badDeep' (a role shade of a hue) to its hue
  const hueOf = (name) => (name && name[0] === '#' ? (K.tok.hueOf ? K.tok.hueOf(name) : null) : String(name).replace(/Deep$/, ''));
  K.ink = (name) => {
    if (!name) return K.tok.color.ink;
    const h = hueOf(name), c = K.tok.color;
    if (name[0] === '#' && !K.tok.themed) return name;
    return c[h + 'Ink'] || c[name] || name;
  };
  K.on = (name, role = 'onAccent') => {
    const c = K.tok.color, h = (hueOf(name) || 'accent').replace(/Text$/, '');
    if (!K.tok.themed) return c[role] || c.onAccent;
    return c['on' + h[0].toUpperCase() + h.slice(1)] || c.onAccent;
  };
  /** the fill of a pill lettered with K.on (a theme steps it away from its letters to 5.6:1; else K.tone) */
  K.pill = (name) => (K.tok.themed && K.tok.color[(hueOf(name) || 'accent') + 'Pill']) || K.tone(name);
  K.alpha = (c, a) => c + Math.round(Math.max(0, Math.min(1, a)) * 255).toString(16).padStart(2, '0');
  K.tint = (c, a) => (K.tok.fx.tint ? K.tok.fx.tint(c, a) : K.alpha(c, a));
  /** Deterministic random numbers (never Math.random: every render of a frame must be identical). */
  K.rand = (seed = 1) => () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  /** Wrap O(...) notation: "O(n^(k+1))" -> O(n<sup>k+1</sup>). */
  K.fmtO = (s) => String(s).replace(/\^\(([^)]+)\)/g, '<sup>$1</sup>').replace(/\^(\w+)/g, '<sup>$1</sup>');

  // ------------------------------------------------------------------ the timeline
  const tl = (K.tl = gsap.timeline({ paused: true }));
  const REST = { x: 0, y: 0, xPercent: 0, yPercent: 0, rotation: 0, rotationX: 0, rotationY: 0, scale: 1, scaleX: 1, scaleY: 1, skewX: 0, filter: 'blur(0px)' };
  const restOf = (from) => { const o = {}; for (const k in from) if (k in REST) o[k] = REST[k]; return o; };

  /** Hide at build time (the state before the element's entrance). */
  K.hidden = (els) => { gsap.set(els, { opacity: 0 }); return els; };
  /** Fade + move in: K.show(el, t, 0.5, {y: 24}). `from` holds the offset it arrives from. */
  K.show = (el, t, d = 0.5, from = { y: 24 }, ease = 'power3.out') => {
    tl.fromTo(el, Object.assign({ opacity: 0 }, from), Object.assign({ opacity: 1, duration: d, ease, immediateRender: false }, restOf(from)), t);
    return el;
  };
  /** Fade out (faster than entrances): K.hide(el, t, 0.3, {y: -20}). */
  K.hide = (el, t, d = 0.3, to = {}, ease = 'power2.in') => { tl.to(el, Object.assign({ opacity: 0, duration: d, ease }, to), t); return el; };
  /** Scale-overshoot entrance (pair it with a "pop" sfx in script.json). */
  K.pop = (el, t, d = 0.5, s0 = 0.3, ease = 'back.out(2.4)') => {
    tl.fromTo(el, { opacity: 0, scale: s0, transformOrigin: '50% 50%' }, { opacity: 1, scale: 1, duration: d, ease, immediateRender: false }, t);
    return el;
  };
  K.pulse = (el, t, s = 1.15, d = 0.5) => {
    tl.to(el, { scale: s, transformOrigin: '50% 50%', duration: d * 0.35, ease: 'power2.out' }, t);
    tl.to(el, { scale: 1, duration: d * 0.65, ease: 'power2.inOut' }, t + d * 0.35);
  };
  K.shake = (el, t, amp = 12, d = 0.45) => {
    tl.to(el, { keyframes: { x: [0, -amp, amp, -amp * 0.7, amp * 0.45, -amp * 0.2, 0] }, duration: d, ease: 'none' }, t);
  };
  /** Make a stroke drawable (invisible until K.draw starts it). */
  K.drawable = (paths) => { gsap.set(paths, { drawSVG: '0%', opacity: 0 }); return paths; };
  K.draw = (path, t, d = 0.6, ease = 'power2.inOut', from = '0%', to = '100%') => {
    tl.set(path, { opacity: 1 }, t);
    tl.fromTo(path, { drawSVG: from }, { drawSVG: to, duration: d, ease, immediateRender: false }, t);
  };
  /** Count a number up/down in an element's text. */
  K.count = (el, t, d, a, b, fmt = (v) => String(Math.round(v)), ease = 'power1.inOut') => {
    const o = { v: a };
    tl.fromTo(o, { v: a }, { v: b, duration: d, ease, immediateRender: false, onUpdate: () => { el.textContent = fmt(o.v); } }, t);
  };
  /** Typewriter reveal by clip-path (keeps layout; no reflow). Returns the duration used. */
  K.type = (el, t, chars, cps = 40) => {
    const d = Math.max(0.3, chars / cps);
    tl.fromTo(el, { clipPath: 'inset(-20% 100% -20% 0%)', opacity: 1 }, { clipPath: 'inset(-20% 0% -20% 0%)', duration: d, ease: `steps(${Math.max(4, Math.round(chars))})`, immediateRender: false }, t);
    return d;
  };
  /** Split text into characters and rise them in (titles). */
  K.riseChars = (el, t, stagger = 0.025, d = 0.7) => {
    const chars = new SplitText(el, { type: 'chars', charsClass: 'ch' }).chars;
    gsap.set(chars, { opacity: 0, display: 'inline-block' });
    tl.fromTo(chars, { opacity: 0, yPercent: 70, rotation: 5 }, { opacity: 1, yPercent: 0, rotation: 0, stagger, duration: d, ease: 'power3.out', immediateRender: false }, t);
    return chars;
  };

  /**
   * A value that changes over time, shown in one spot: each `to()` stacks a new span and flips/fades between them
   * (fully reversible, so seeking anywhere in the film shows the right value).
   *   const v = K.stack(parent, {left: 0, top: 0}, 'class'); v.to(t, '100', {color: K.tone('good')});
   */
  K.stack = (parent, style, cls) => {
    const box = K.el('div', 'abs ' + (cls || ''), parent, Object.assign({}, style));
    let cur = null;
    return {
      el: box,
      get current() { return cur; },
      to(t, html, opts = {}) {
        const s = K.el('div', 'abs', box, { left: 0, top: 0, right: 0, bottom: 0, display: 'flex', alignItems: 'center', justifyContent: opts.align || 'center', color: opts.color || '' }, html);
        if (opts.style) Object.assign(s.style, opts.style);
        K.hidden(s);
        const mode = opts.mode || 'flip', d = opts.d ?? 0.4;
        if (t == null) { gsap.set(s, { opacity: 1 }); cur = s; return s; }
        if (cur) {
          if (mode === 'flip') tl.to(cur, { opacity: 0, yPercent: -60, duration: d * 0.55, ease: 'power2.in' }, t);
          else K.hide(cur, t, d * 0.45); // 'fade' is sequential: the old text is gone before the new one comes (no ghost)
        }
        if (mode === 'flip') tl.fromTo(s, { opacity: 0, yPercent: 60 }, { opacity: 1, yPercent: 0, duration: d, ease: 'back.out(1.8)', immediateRender: false }, t + (cur ? d * 0.35 : 0));
        else K.show(s, t + (cur ? d * 0.45 : 0), d * 0.55, { scale: 0.9 });
        cur = s;
        return s;
      },
    };
  };

  /** Close the film: the timeline lasts at least TIMING.total (the render wrapper cuts it exactly). */
  K.finish = () => { tl.set({}, {}, T.total); return tl; };
})();
