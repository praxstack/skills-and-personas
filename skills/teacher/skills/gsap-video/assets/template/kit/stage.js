// kit/stage.js: the layers, the camera, chapter lighting, captions, the lower-third tag and the ambient
// motion that runs every frame (drift, light, bokeh; the grain stays still). Ambient is a pure function of t (K.ambient).
//
// Layers, back to front:
//   canvas.bgc                        ONE half-resolution canvas redrawn every frame: base gradient, the two
//                                     coloured lights (K.mood), dot grid + bokeh with parallax, film grain,
//                                     vignette. (As separate full-screen DOM layers these cost 2.4x the
//                                     capture time; one small canvas costs almost nothing.)
//   svg#scene > g#cam > g#world       WORLD space: the persistent subject (graph, decoder panel, tokens)
//   #ui                               SCREEN space panels: code, table, ladder, tree, question cards
//   #fx                               SCREEN space comic callouts and stamps
//   #cards, #hud, #caps               chapter cards, lower-third tag, captions
(function () {
  const K = window.K;

  K.buildStage = function () {
    const stage = document.getElementById('stage');
    stage.innerHTML = '';
    K.stageEl = stage;
    BG.cv = K.html('canvas', 'bgc', null, stage);
    BG.cv.width = K.W / 2; BG.cv.height = K.H / 2;
    BG.ctx = BG.cv.getContext('2d');
    buildBg();
    const svg = (K.scene = K.svg('svg', { id: 'scene', width: K.W, height: K.H, viewBox: `0 0 ${K.W} ${K.H}` }, stage));
    K.defs = K.svg('defs', {}, svg);
    buildDefs();
    K.camEl = K.svg('g', { id: 'cam' }, svg);
    K.world = K.svg('g', { id: 'world' }, K.camEl);
    K.layer = {};
    for (const n of ['back', 'panels', 'edges', 'trails', 'nodes', 'labels', 'tokens', 'fx'])
      K.layer[n] = K.svg('g', { class: `layer-${n}` }, K.world);
    K.ui = K.html('div', '', '', stage); K.ui.id = 'ui';
    K.fx = K.html('div', '', '', stage); K.fx.id = 'fx';
    K.cards = K.html('div', '', '', stage); K.cards.id = 'cards';
    K.hudEl = K.html('div', '', '', stage); K.hudEl.id = 'hud';
    K.capsEl = K.html('div', '', '', stage); K.capsEl.id = 'caps';
    const m0 = TOKENS.moods[0];
    Object.assign(K.light, { key: m0.key, rim: m0.rim, glow: m0.glow });
    K.captions.build();
    K.hud.build();
  };

  function buildDefs() {
    const d = K.defs;
    // one soft glow gradient per palette colour: fill="url(#glow-accent)" etc. (cheap; no SVG blur filters)
    // (light themes use weaker stops: a strong glow on a light ground reads as a smudge)
    const [g0, g1] = K.FX.glowStops;
    for (const [name, c] of Object.entries(K.C)) {
      if (!c.startsWith('#')) continue;
      const g = K.svg('radialGradient', { id: `glow-${name}` }, d);
      K.svg('stop', { offset: '0%', 'stop-color': c, 'stop-opacity': g0 }, g);
      K.svg('stop', { offset: '45%', 'stop-color': c, 'stop-opacity': g1 }, g);
      K.svg('stop', { offset: '100%', 'stop-color': c, 'stop-opacity': 0 }, g);
    }
    const nf = K.svg('radialGradient', { id: 'node-fill', cx: '38%', cy: '32%', r: '75%' }, d);
    const U = K.U, [p0, p1] = K.FX.poolStops;
    K.svg('stop', { offset: '0%', 'stop-color': U.nodeA }, nf);
    K.svg('stop', { offset: '100%', 'stop-color': U.nodeB }, nf);
    const pool = K.svg('radialGradient', { id: 'pool' }, d);
    K.svg('stop', { offset: '0%', 'stop-color': U.pool, 'stop-opacity': p0 }, pool);
    K.svg('stop', { offset: '60%', 'stop-color': U.pool, 'stop-opacity': p1 }, pool);
    K.svg('stop', { offset: '100%', 'stop-color': U.pool, 'stop-opacity': 0 }, pool);
    const sh = K.svg('radialGradient', { id: 'shadow' }, d);
    K.svg('stop', { offset: '0%', 'stop-color': U.shadowCol, 'stop-opacity': K.FX.shadowA }, sh);
    K.svg('stop', { offset: '100%', 'stop-color': U.shadowCol, 'stop-opacity': 0 }, sh);
    const ht = K.svg('pattern', { id: 'halftone', width: 10, height: 10, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(20)' }, d);
    K.svg('circle', { cx: 5, cy: 5, r: 2.1, fill: U.dotShade }, ht);
  }

  // ------------------------------------------------------------------ background canvas
  const BG = {};
  const BOKEH = [];
  K.light = { key: TOKENS.moods[0].key, rim: TOKENS.moods[0].rim, glow: 0.4 };   // tweened by K.mood, drawn by drawBg
  function buildBg() {
    const c = BG.ctx, W = BG.cv.width, H = BG.cv.height;
    BG.base = c.createRadialGradient(W * 0.5, H * 0.4, 0, W * 0.5, H * 0.4, W * 0.75);
    const U = K.U;
    BG.base.addColorStop(0, U.bgA); BG.base.addColorStop(0.55, U.bgB); BG.base.addColorStop(1, U.bgC);
    BG.vig = c.createRadialGradient(W * 0.5, H * 0.45, H * 0.45, W * 0.5, H * 0.45, W * 0.68);
    BG.vig.addColorStop(0, U.vig0); BG.vig.addColorStop(1, U.vig);
    const dot = document.createElement('canvas'); dot.width = dot.height = 24;
    const dc = dot.getContext('2d'); dc.fillStyle = U.dot; dc.beginPath(); dc.arc(12, 12, 1.1, 0, 7); dc.fill();
    BG.dots = c.createPattern(dot, 'repeat');
    const n = 128, nz = document.createElement('canvas'); nz.width = nz.height = n;
    // grain: black and white specks on a dark ground; on a light ground only dark ones (they darken, like ink)
    const nc = nz.getContext('2d'), img = nc.createImageData(n, n), r = K.rng(5);
    const [ga, gb] = K.FX.grainA, darkOnly = K.FX.grain === 'dark';
    for (let i = 0; i < img.data.length; i += 4) {
      const v = r() < 0.5 || darkOnly ? 0 : 255;
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = ga + r() * gb;
    }
    nc.putImageData(img, 0, 0);
    BG.noise = c.createPattern(nz, 'repeat');
    const rb = K.rng(11);
    for (let i = 0; i < 16; i++) BOKEH.push({ r: 30 + rb() * 90, a: 0.05 + rb() * 0.1, x: rb() * K.W, y: rb() * K.H, ax: 20 + rb() * 50, ay: 10 + rb() * 30, w: 0.05 + rb() * 0.1, ph: rb() * 6.28 });
  }
  function rgba(col, a) {
    if (col[0] === '#') { const v = parseInt(col.slice(1), 16); return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`; }
    const m = col.match(/[\d.]+/g) || [255, 255, 255];
    return `rgba(${m[0]},${m[1]},${m[2]},${a})`;
  }
  function blob(c, x, y, r, col, a) {
    const g = c.createRadialGradient(x, y, 0, x, y, r);
    g.addColorStop(0, rgba(col, a)); g.addColorStop(0.5, rgba(col, a * 0.45)); g.addColorStop(1, rgba(col, 0));
    c.fillStyle = g; c.fillRect(x - r, y - r, 2 * r, 2 * r);
  }
  function drawBg(t, v, dx, dy) {
    const c = BG.ctx, W = BG.cv.width, H = BG.cv.height, h = 0.5;
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.globalCompositeOperation = 'source-over';
    c.fillStyle = BG.base; c.fillRect(0, 0, W, H);
    // the lights add on a dark ground ('lighter'); a light theme screens them (they lighten, never smudge)
    const FX = K.FX;
    c.globalCompositeOperation = FX.lightOp;
    const L = K.light;
    blob(c, (230 + Math.sin(t * 0.09) * 90) * h, (50 + Math.cos(t * 0.07) * 60) * h, 760 * h, L.key, L.glow * FX.lightK);
    blob(c, (1810 + Math.cos(t * 0.08) * 80) * h, (990 + Math.sin(t * 0.06) * 50) * h, 760 * h, L.rim, L.glow * 0.9 * FX.lightK);
    c.globalCompositeOperation = FX.bokehOp;
    for (const b of BOKEH) {
      const bx = b.x + Math.sin(t * b.w + b.ph) * b.ax + v.x * 0.3 + dx * 0.5, by = b.y + Math.cos(t * b.w * 0.8 + b.ph) * b.ay + v.y * 0.3 + dy * 0.5;
      blob(c, bx * h, by * h, b.r * h, K.U.bokeh, b.a * 0.6 * FX.bokehK);
    }
    c.globalCompositeOperation = 'source-over';
    const ps = 1 + (v.s - 1) * 0.25;   // the dot grid moves at 30% of the camera: depth by parallax
    const ox = (v.x * 0.3 + dx * 0.5) * h, oy = (v.y * 0.3 + dy * 0.5) * h;
    c.setTransform(ps, 0, 0, ps, ox, oy);
    c.fillStyle = BG.dots; c.fillRect(-ox / ps - 24, -oy / ps - 24, W / ps + 48, H / ps + 48);
    // Grain is fixed to the screen. Re-randomising it every frame (film-style) made the H.264 file 7x bigger
    // (37 vs 5 Mbit/s measured): the encoder spends every bit on noise. Keep it still.
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.fillStyle = BG.noise; c.fillRect(0, 0, W, H);
    c.setTransform(1, 0, 0, 1, 0, 0);
    c.fillStyle = BG.vig; c.fillRect(0, 0, W, H);
  }

  // ------------------------------------------------------------------ camera (world space -> screen)
  // K.cam.v = {x, y, s} is tweened by GSAP; K.ambient applies it (plus a slow drift) to g#cam every frame.
  // Views: {x, y, s} means world point p shows at screen (x + s*p.x, y + s*p.y).
  K.cam = {
    v: { x: 0, y: 0, s: 1 },
    moves: [],
    /** Initial view (before the film starts). */
    start(view) { Object.assign(this.v, view); this.v0 = { ...view }; },
    /** The view that fits world rect {x,y,w,h} into screen box (default: the safe area above the captions). */
    frame(rect, box = null, o = {}) {
      box = box || { x: K.SAFE.l, y: 170, w: K.SAFE.r - K.SAFE.l, h: K.SAFE.b - 170 };
      const pad = o.pad ?? 40;
      let s = Math.min((box.w - 2 * pad) / rect.w, (box.h - 2 * pad) / rect.h);
      s = K.clamp(s, o.minS ?? 0.25, o.maxS ?? 1.8);
      return { x: box.x + box.w / 2 - s * (rect.x + rect.w / 2), y: box.y + box.h / 2 - s * (rect.y + rect.h / 2), s };
    },
    /** Move the camera at time t to a view ({x,y,s}) or to frame a world rect ({x,y,w,h}). */
    to(t, view, o = {}) {
      if (view.w !== undefined) view = this.frame(view, o.box, o);
      const dur = o.dur ?? 1.4, ease = o.ease ?? 'power3.inOut';
      this.moves.push({ t, dur, ease, to: { x: view.x, y: view.y, s: view.s } });
      this.moves.sort((a, b) => a.t - b.t);
      K.to(this.v, { x: view.x, y: view.y, s: view.s, duration: dur, ease }, t);
      return t + dur;
    },
    /** Push in on a world point by a factor, keeping it at the same screen spot. */
    push(t, p, factor = 1.25, o = {}) {
      const v = this.at(t), sp = this.toScreen(p, t), s = v.s * factor;
      return this.to(t, { x: sp[0] - s * p[0], y: sp[1] - s * p[1], s }, { dur: 2.2, ease: 'sine.inOut', ...o });
    },
    /** The view at time t (from the recorded moves; build-time math, no DOM). */
    at(t) {
      let v = { ...(this.v0 || { x: 0, y: 0, s: 1 }) };
      for (const m of this.moves) {
        if (t <= m.t) break;
        const f = gsap.parseEase(m.ease)(K.clamp((t - m.t) / m.dur));
        v = { x: K.lerp(v.x, m.to.x, f), y: K.lerp(v.y, m.to.y, f), s: K.lerp(v.s, m.to.s, f) };
      }
      return v;
    },
    toScreen(p, t) { const v = this.at(t); return [v.x + v.s * p[0], v.y + v.s * p[1]]; },
    toWorld(q, t) { const v = this.at(t); return [(q[0] - v.x) / v.s, (q[1] - v.y) / v.s]; },
  };

  // ------------------------------------------------------------------ chapter lighting
  /** K.mood(t, n | {key, rim, glow}): shift the two background lights to chapter n's colours. */
  K.mood = (t, m, d = 1.6) => {
    const md = typeof m === 'number' ? TOKENS.moods[Math.min(m, TOKENS.moods.length - 1)] : m;
    K.to(K.light, { key: md.key, rim: md.rim, glow: md.glow, duration: d, ease: 'sine.inOut' }, t);
  };
  /** One mood change per chapter, starting in the pause before it. */
  K.autoMoods = () => K.T.chapters.forEach((c, i) => { if (i > 0) K.mood(Math.max(0, c.start - 0.8), c.n); });

  // ------------------------------------------------------------------ captions (bottom band, from TIMING)
  K.captions = {
    skip: new Set(),
    build() { this.el = K.html('div', 'cap', '', K.capsEl); this.cur = null; },
    /** Hide the caption for a line (question cards show their own text). */
    hideFor(id) { this.skip.add(id); },
    split(cap, limit = 84) { // same rule as captions.py: two lines at most, break near the middle
      if (cap.length <= limit) return [cap];
      const mid = cap.length / 2;
      let best = -1, bd = 1e9;
      for (const m of cap.matchAll(/[.:;,?!] |… | — /g)) { const i = m.index + 1; if (Math.abs(i - mid) < bd) { bd = Math.abs(i - mid); best = i; } }
      if (best < 0 || bd > cap.length * 0.28) {
        best = -1; bd = 1e9;
        for (let i = 0; i < cap.length; i++) if (cap[i] === ' ' && Math.abs(i - mid) < bd) { bd = Math.abs(i - mid); best = i; }
      }
      return [cap.slice(0, best).trim(), cap.slice(best).trim()];
    },
    update(t) {
      const l = K.lines.find((x) => t >= x.start && t < x.end);
      const show = l && !this.skip.has(l.id);
      const key = show ? l.id : null;
      if (key !== this.cur) {
        this.cur = key;
        if (show) this.el.innerHTML = this.split(l.cap).map((s) => `<span>${K.fmt(s)}</span>`).join('<br>');
      }
      if (!show) { this.el.style.opacity = 0; return; }
      // fade only at chapter gaps (adjacent lines cut, like real subtitles); a chapter's first caption waits
      // until the chapter card has left, so it is never drawn over the slab
      const t0 = K.afterCards ? K.afterCards(l.start) : l.start;
      const fin = l.prev && Math.abs(l.prev.end - l.start) < 0.01 && !this.skip.has(l.prev.id) ? 1 : K.clamp((t - t0) / 0.18);
      const fout = l.next && Math.abs(l.next.start - l.end) < 0.01 && !this.skip.has(l.next.id) ? 1 : K.clamp((l.end - t) / 0.18);
      this.el.style.opacity = Math.min(fin, fout).toFixed(3);
    },
  };

  // ------------------------------------------------------------------ lower-third tag + chapter progress
  K.hud = {
    build() {
      this.tags = {};
      this.segs = [];
      const chs = K.T.chapters.filter((c) => c.n > 0);
      this.bar = K.html('div', 'hud-bar', '', K.hudEl);
      chs.forEach((c) => { const s = K.html('i', '', '<b></b>', this.bar); this.segs.push({ c, fill: s.firstChild }); });
      K.init(this.bar, { autoAlpha: 0 });
      this.on = null;
    },
    /**
     * Swap the lower third to chapter n at time t ("02 · BRUTE FORCE"). hideAt: when the old tag leaves
     * (default t - 0.3); an earlier hideAt also hides the progress bar until t (chapter cards use this so
     * nothing of the HUD sits on top of the slab).
     */
    show(n, t, name = null, hideAt = t - 0.3) {
      const c = K.chapter(n);
      const tag = K.html('div', 'hud-tag', `<span class="num">${String(n).padStart(2, '0')}</span><span class="name">${K.esc((name || c.name).toUpperCase())}</span>`, K.hudEl);
      K.init(tag, { autoAlpha: 0, x: -30 });
      if (this.on) {
        K.to(this.on, { autoAlpha: 0, x: 20, duration: 0.25, ease: 'power2.in' }, hideAt);
        if (hideAt < t - 0.35) {
          K.to(this.bar, { autoAlpha: 0, duration: 0.25, ease: 'power2.in' }, hideAt);
          K.to(this.bar, { autoAlpha: 1, duration: 0.4 }, t);
        }
      } else K.fadeIn(this.bar, t, 0.5, { dy: 0 });
      K.to(tag, { autoAlpha: 1, x: 0, duration: 0.5, ease: 'expo.out' }, t);
      this.on = tag;
      return tag;
    },
    update(t) {
      for (const s of this.segs) {
        const f = K.clamp((t - s.c.start) / Math.max(0.1, s.c.end - s.c.start));
        s.fill.style.transform = `scaleX(${f.toFixed(4)})`;
      }
    },
  };

  // ------------------------------------------------------------------ ambient: runs every frame, pure f(t)
  // K.everyFrame(fn): register a pure function of t (idle spin, a shimmer). Never read state from the last frame.
  const EVERY = [];
  K.everyFrame = (fn) => EVERY.push(fn);
  const DRIFT = { cx: K.W / 2, cy: 470 };
  K.ambient = function (t) {
    for (const fn of EVERY) fn(t);
    const v = K.cam.v;
    const dx = Math.sin(t * 0.21) * 7 + Math.sin(t * 0.077) * 5, dy = Math.cos(t * 0.17) * 5;
    const ds = 1 + Math.sin(t * 0.11) * 0.007;
    K.camEl.setAttribute('transform',
      `translate(${(DRIFT.cx + dx).toFixed(2)} ${(DRIFT.cy + dy).toFixed(2)}) scale(${ds.toFixed(5)}) ` +
      `translate(${-DRIFT.cx} ${-DRIFT.cy}) translate(${v.x.toFixed(2)} ${v.y.toFixed(2)}) scale(${v.s.toFixed(5)})`);
    drawBg(t, v, dx, dy);
    K.captions.update(t);
    K.hud.update(t);
  };
})();
