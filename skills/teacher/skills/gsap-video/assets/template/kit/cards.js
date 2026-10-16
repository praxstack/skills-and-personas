// kit/cards.js: title card, chapter cards, question card with countdown, comic callouts, stamps, notes,
// result card, and the recursion/fan-out tree. All SCREEN space (they do not move with the camera).
(function () {
  const K = window.K;

  // ------------------------------------------------------------------ title card
  /** K.titleCard({kicker, title: 'Line one\nLine two', sub}, tIn, tOut): big headline, letters rise in. */
  K.titleCard = function (o, tIn, tOut) {
    const el = K.html('div', 'title-card', '', K.cards);
    const kick = K.html('div', 'kicker', K.esc(o.kicker ?? ''), el);
    const h = K.html('div', 'title-h', '', el);
    const chars = [];
    o.title.split('\n').forEach((line) => {
      const ln = K.html('div', 'tl', '', h);
      line.split(' ').forEach((word, wi) => {
        const w = K.html('span', 'w', '', ln);
        for (const ch of word) chars.push(K.html('span', 'c', K.esc(ch), w));
        if (wi < line.split(' ').length - 1) K.html('span', 'sp', ' ', ln);
      });
    });
    const rule = K.html('div', 'title-rule', '', el);
    const sub = K.html('div', 'title-sub', K.esc(o.sub ?? ''), el);
    K.init(chars, { autoAlpha: 0, y: 90, rotation: 8 });
    K.init([kick, sub], { autoAlpha: 0, y: 20 });
    K.init(rule, { scaleX: 0, transformOrigin: '0% 50%' });
    K.to(kick, { autoAlpha: 1, y: 0, duration: 0.5 }, tIn);
    K.to(chars, { autoAlpha: 1, y: 0, rotation: 0, duration: 0.7, stagger: 0.022, ease: 'expo.out' }, tIn + 0.05);
    K.to(rule, { scaleX: 1, duration: 0.8, ease: 'expo.inOut' }, tIn + 0.35);
    K.to(sub, { autoAlpha: 1, y: 0, duration: 0.5 }, tIn + 0.6);
    if (tOut !== undefined) K.to(el, { autoAlpha: 0, y: -50, duration: 0.5, ease: 'power2.in' }, tOut);
    return el;
  };

  // ------------------------------------------------------------------ chapter cards + lower thirds
  /**
   * K.chapterCard(n, t, {name, color}): a coloured slab sweeps in from the left during the pause before
   * chapter n (t = the chapter's start), shows "02" and the name, sweeps out as the voice starts, and the
   * lower-third tag switches to this chapter. K.chapterCards() does this for every chapter after the intro.
   *
   * The slab covers the left 900 px of the frame from K.cardIn(n) until K.cardClear(n) (about t - 0.78 to
   * t + 0.56). Nothing in screen space may be under it: hide the last chapter's left-side panels so they are
   * gone by K.cardIn(n), and bring this chapter's in at K.cardClear(n) or later (K.question and the captions
   * wait for the card by themselves). gsap_check.mjs warns about anything visible under a slab. The LC 739
   * test film showed its chapter 4 ladder and first caption appearing under the leaving card.
   */
  const CARD = { in: -0.78, out: 0.2, outDur: 0.36 };
  K.cardWindows = [];
  /** When chapter n's card starts to come in (old screen-space content on the left must be gone by then). */
  K.cardIn = (n) => K.chapter(n).start + CARD.in;
  /** When chapter n's card has gone (new screen-space content on the left may appear from then on). */
  K.cardClear = (n) => K.chapter(n).start + CARD.out + CARD.outDur;
  /** t, or the end of the chapter card that is on screen at t (for things that must not appear under a card). */
  K.afterCards = (t) => { for (const w of K.cardWindows) if (t >= w.in - 1e-3 && t < w.clear) return w.clear; return t; };
  K.chapterCard = function (n, t, o = {}) {
    const c = K.chapter(n);
    const name = (o.name ?? c.name).toUpperCase();
    const color = K.col(o.color ?? TOKENS.moods[Math.min(n, TOKENS.moods.length - 1)].key);
    const el = K.html('div', 'chap', '', K.cards);
    // the label is the fill's on-colour; in a theme the slab's gradient runs AWAY from the label's lightness,
    // so the solved on-colour only gains contrast across the slab (original: a fixed shade, near-black text)
    const label = K.on(color);
    let shadeF = K.FX.slabShade ?? (K.contrast(label, '#000000') > K.contrast(label, '#FFFFFF') ? -0.18 : 0.22);
    // a dark label must still read at 5:1 where the name sits on the darkened gradient (the original -0.35
    // left black text at 4.2:1 on the violet slab): ease the shade back toward the slab colour until it does
    const hexOf = (c) => '#' + c.match(/\d+/g).map((v) => (+v).toString(16).padStart(2, '0')).join('');
    if (shadeF < 0 && K.contrast(label, '#000000') < K.contrast(label, '#FFFFFF')) {
      while (shadeF < 0 && K.contrast(label, hexOf(K.shade(color, shadeF))) < 5) shadeF = Math.min(0, shadeF + 0.01);
    }
    const slab = K.html('div', 'chap-slab', '', el, { background: `linear-gradient(135deg, ${color}, ${K.shade(color, shadeF)})` });
    K.html('div', 'chap-dots', '', slab);
    const num = K.html('div', 'chap-num', String(n).padStart(2, '0'), slab, { webkitTextStroke: `5px ${label}` });
    const size = K.fit(name, '900 {s}px Inter', 640, 92, 44);
    const nm = K.html('div', 'chap-name', K.esc(name), slab, { fontSize: `${size}px`, color: label });
    const streak = K.html('div', 'chap-streak', '', el, { background: `linear-gradient(90deg, transparent, ${color}, transparent)` });
    K.init(slab, { xPercent: -105 });
    K.init([num, nm], { autoAlpha: 0, x: -50 });
    K.init(streak, { autoAlpha: 0, x: -400 });
    const tIn = t + CARD.in, tOut = t + CARD.out, clear = tOut + CARD.outDur;
    K.to(slab, { xPercent: 0, duration: 0.5, ease: 'expo.out' }, tIn);
    K.to(num, { autoAlpha: 1, x: 0, duration: 0.45, ease: 'expo.out' }, tIn + 0.1);
    K.to(nm, { autoAlpha: 1, x: 0, duration: 0.45, ease: 'expo.out' }, tIn + 0.16);
    K.to(streak, { autoAlpha: 1, x: 2400, duration: 0.7, ease: 'power2.inOut' }, tIn + 0.05);
    K.to(slab, { xPercent: -105, duration: CARD.outDur, ease: 'power3.in' }, tOut);
    // the lower third (drawn above the cards) leaves before the slab arrives and returns once it has gone
    K.hud.show(n, clear - 0.05, o.name, tIn - 0.3);
    K.cardWindows.push({ n, start: t, in: tIn, out: tOut, clear, el });
    return { el, in: tIn, end: clear };
  };
  K.chapterCards = (o = {}) => K.T.chapters.forEach((c) => { if (c.n > 0 && !(o.skip || []).includes(c.n)) K.chapterCard(c.n, c.start, (o.opts || {})[c.n]); });

  // ------------------------------------------------------------------ question card with countdown ring
  /**
   * K.question(L.q1, {n: 1, text, x, cy, w, size}): the card comes in as the question is read, its words light
   * up as they are spoken, a ring counts down the line's think seconds, and it leaves when the line ends.
   * The caption for that line is suppressed (the card shows the text). Leave the subject visible beside it.
   */
  K.question = function (line, o = {}) {
    let text = o.text ?? line.cap.replace(/^question\s*\d*\s*[:.]\s*/i, '');
    text = text.charAt(0).toUpperCase() + text.slice(1);
    const x = o.x ?? K.SAFE.l, cy = o.cy ?? 498, w = o.w ?? 800;   // cy: vertical centre of the card
    const el = K.html('div', 'qcard', '', K.ui, { left: `${x}px`, top: `${cy}px`, width: `${w}px` });
    if (o.banner) el.classList.add('banner');   // wide top banner, think ring on the right: keeps a wide subject visible
    K.html('div', 'kicker', `Question${o.n ? ' ' + o.n : ''}`, el);
    const q = K.html('div', 'qtext', '', el, { fontSize: `${o.size ?? 64}px` });
    const words = [];
    let pos = 0;
    text.split(' ').forEach((wd) => {
      const sp = K.html('span', 'qw', `${K.fmt(wd)} `, q);
      words.push({ sp, f: pos / text.length });
      pos += wd.length + 1;
    });
    const think = line.think || 0;
    const timer = K.html('div', 'qtimer', `<svg width="92" height="92" viewBox="-46 -46 92 92"><circle r="38" class="qring-bg"/><circle r="38" class="qring" transform="rotate(-90)"/></svg><div class="qnum mono"></div><div class="qlab">think</div>`, el);
    const ring = timer.querySelector('.qring'), qnum = timer.querySelector('.qnum');
    const secs = Math.max(1, Math.round(think));
    const nums = [];
    for (let s = secs; s >= 1; s--) nums.push(K.html('span', '', String(s), qnum));
    const ringSvg = timer.querySelector('svg'), lab = timer.querySelector('.qlab');
    K.init(el, { autoAlpha: 0, y: 30, yPercent: -50 });
    // words not spoken yet are dimmer but still readable (opacity 0.5 is about 4.5:1 on the card; 0.22 was 2:1).
    // A theme's solved inks have no headroom for opacity, so there the unspoken words are the dim ink instead.
    const UC = K.FX.unspokenColor;
    K.init(words.map((x) => x.sp), UC ? { color: UC } : { opacity: K.FX.unspoken });
    K.init(timer.querySelector('.qring'), { stroke: K.vis('amber') });
    K.init(ring, { drawSVG: '100%' });
    K.init(nums, { autoAlpha: 0 });
    K.init(ringSvg, { autoAlpha: 0.35 });   // the ring waits dimmed; the "think" label stays readable (dim ink)
    K.captions.hideFor(line.id);
    // the card waits for a chapter card on the left to leave (it is placed at finalize, after every card exists)
    const tIn0 = Math.max(line.start, line.voiceAt - 0.3);
    K.onFinalize(() => K.to(el, { autoAlpha: 1, y: 0, duration: 0.5, ease: 'expo.out' }, K.afterCards(tIn0)));
    words.forEach((wd) => K.to(wd.sp, UC ? { color: K.C.ink, duration: 0.25, ease: 'power1.out' } : { opacity: 1, duration: 0.25, ease: 'power1.out' }, line.voiceAt + line.voiceDur * wd.f));
    const t0 = line.vEnd + 0.05;
    if (think > 0) {
      K.to(ringSvg, { autoAlpha: 1, duration: 0.25 }, t0 - 0.2);
      K.to(lab, { color: K.ink('amber'), duration: 0.25 }, t0 - 0.2);
      K.to(ring, { drawSVG: '0%', duration: think, ease: 'none' }, t0);
      nums.forEach((nEl, i) => {
        K.set(nEl, { autoAlpha: 1 }, t0 + i * (think / secs));
        if (i < nums.length - 1) K.set(nEl, { autoAlpha: 0 }, t0 + (i + 1) * (think / secs));
      });
    }
    K.to(el, { autoAlpha: 0, y: -20, duration: 0.35, ease: 'power2.in' }, line.end - 0.3);
    return { el, end: line.end };
  };

  // ------------------------------------------------------------------ comic callout burst
  let seed = 7;
  /**
   * K.callout('700!', t, {x, y} | {at: worldPoint}, color, rot, size, hold): a comic starburst that pops with
   * an overshoot, holds, and blows away. Screen space; with `at` the world point is converted using the
   * camera at time t. Pair it with an sfx "pop" on that line.
   */
  K.callout = function (text, t, o = {}) {
    const size = o.size ?? 104;
    let x = o.x, y = o.y;
    if (o.at) [x, y] = K.cam.toScreen(o.at, t);
    x += o.dx ?? 0; y += o.dy ?? 0;
    // Bangers' 7 reads as a 1 ("700!" looked like "100!") and it has capitals only ("k + 1" read "K + 1"), so
    // digits and lowercase letters are set in Inter Black inside the burst: write comic words in CAPITALS
    const runs = String(text).match(/[0-9a-z]+|[^0-9a-z]+/g) || [''];
    const inter = (r) => /[0-9a-z]/.test(r);
    const tw = runs.reduce((w, r) => w + K.textW(r, inter(r) ? `900 ${size * 0.92}px Inter` : `${size}px Bangers`), 0) + 40;
    const spans = runs.map((r) => (inter(r) ? `<tspan class="callout-num" font-size="${Math.round(size * 0.92)}">${r}</tspan>` : `<tspan>${K.esc(r)}</tspan>`)).join('');
    const rx = Math.max(tw * 0.68, size * 1.2), ry = Math.max(size * 1.05, rx * 0.55);
    const r = K.rng(seed++ * 101 + text.length);
    const n = 16, pts = [];
    for (let i = 0; i < n * 2; i++) {
      const a = (i / (n * 2)) * Math.PI * 2 + r() * 0.08, k = i % 2 ? 0.72 + r() * 0.08 : 1 + r() * 0.16;
      pts.push(`${(Math.cos(a) * rx * k).toFixed(1)},${(Math.sin(a) * ry * k).toFixed(1)}`);
    }
    const W = rx * 2.6, H = ry * 2.6, color = K.col(o.color ?? 'amber');
    // themes: the words are the fill's solved on-colour, outlined in the opposite lightness (a light word on a
    // mid-tone fill measured 3.8:1); the original keeps its cream words with the near-black outline
    let tstyle = '';
    if (K.FX.calloutOn) {
      const on = K.on(color), T = TOKENS.theme;
      const away = K.contrast(on, T.text) > K.contrast(on, T.bg) ? T.text : T.bg;
      tstyle = ` style="fill:${on};stroke:${away}"`;
    }
    const el = K.html('div', 'callout', '', K.fx, { left: `${x - W / 2}px`, top: `${y - H / 2}px`, width: `${W}px`, height: `${H}px` });
    el.innerHTML = `<svg width="${W}" height="${H}" viewBox="${-W / 2} ${-H / 2} ${W} ${H}">` +
      `<polygon points="${pts.join(' ')}" transform="translate(10,14)" fill="${K.U.calloutShadow}" opacity="${K.FX.calloutShadowA}"/>` +
      `<polygon points="${pts.join(' ')}" fill="${color}" stroke="${K.C.black}" stroke-width="7" stroke-linejoin="round"/>` +
      `<polygon points="${pts.join(' ')}" fill="url(#halftone)" opacity="0.9"/>` +
      `<text class="callout-text" y="${(size * 0.36).toFixed(0)}" font-size="${size}" transform="rotate(-4) skewX(-6)"${tstyle}>${spans}</text></svg>`;
    // the halftone pattern lives in the scene SVG's defs; inline SVGs in the same document can use it
    const rot = o.rot ?? -8;
    K.init(el, { autoAlpha: 0, scale: 0.1, rotation: rot - 30 });
    K.to(el, { autoAlpha: 1, scale: 1, rotation: rot, duration: 0.5, ease: 'back.out(3)' }, t);
    const hold = o.hold ?? 1.4;
    K.to(el, { autoAlpha: 0, scale: 1.25, duration: 0.25, ease: 'power2.in' }, t + 0.5 + hold);
    K.moments.push({ id: `callout "${text}"`, t: t + 0.5 + Math.min(0.3, hold / 2) });
    return el;
  };

  /** K.stamp('TOO MANY STOPS', t, {x, y} | {at}, color, rot, size, hold): a rubber stamp slams down. */
  K.stamp = function (text, t, o = {}) {
    let x = o.x, y = o.y;
    if (o.at) [x, y] = K.cam.toScreen(o.at, t);
    const el = K.html('div', 'stamp', K.esc(text), K.fx, { left: `${x}px`, top: `${y}px`, fontSize: `${o.size ?? 40}px`, color: K.ink(o.color ?? 'rose'), borderColor: K.ink(o.color ?? 'rose') });
    K.init(el, { autoAlpha: 0, scale: 2.4, rotation: o.rot ?? -9, xPercent: -50, yPercent: -50 });
    K.to(el, { autoAlpha: 1, scale: 1, duration: 0.32, ease: 'power4.in' }, t);
    K.to(el, { x: 4, duration: 0.05, ease: 'none' }, t + 0.32);
    K.to(el, { x: 0, duration: 0.08, ease: 'none' }, t + 0.37);
    if (o.hold) K.to(el, { autoAlpha: 0, duration: 0.3 }, t + 0.45 + o.hold);
    K.moments.push({ id: `stamp "${text}"`, t: t + 0.5 });
    return el;
  };

  /** K.note(text, t, {x, y, w, size, color, until}): a short label in screen space ("k = 1 → at most 1 stop"). */
  K.note = function (text, t, o = {}) {
    const el = K.html('div', 'note', K.fmt(text), K.ui, { left: `${o.x}px`, top: `${o.y}px`, fontSize: `${o.size ?? 38}px`, borderColor: K.vis(o.color ?? 'accent'), maxWidth: `${o.w ?? 760}px` });
    K.init(el, { autoAlpha: 0, x: -24 });
    K.to(el, { autoAlpha: 1, x: 0, duration: 0.45, ease: 'expo.out' }, t);
    if (o.until !== undefined) K.to(el, { autoAlpha: 0, duration: 0.3 }, o.until);
    return el;
  };

  /** K.resultCard({x, y, w, kicker, big, lines: ['O(k·E) time', ...]}, t, tOut): the answer card. */
  K.resultCard = function (o, t, tOut) {
    const el = K.html('div', 'result', '', K.ui, { left: `${o.x}px`, top: `${o.y}px`, width: `${o.w ?? 560}px` });
    const parts = [K.html('div', 'kicker', K.esc(o.kicker ?? ''), el), K.html('div', 'big', K.fmt(o.big ?? ''), el, { color: K.ink(o.color ?? 'accent') })];
    K.html('div', 'rule', '', el);
    (o.lines || []).forEach((l) => parts.push(K.html('div', 'ln', K.fmt(l), el)));
    K.init(el, { autoAlpha: 0, x: 60 });
    K.init(parts, { autoAlpha: 0, y: 18 });
    K.to(el, { autoAlpha: 1, x: 0, duration: 0.7, ease: 'expo.out' }, t);
    K.to(parts, { autoAlpha: 1, y: 0, duration: 0.45, stagger: 0.12, ease: 'expo.out' }, t + 0.15);
    if (tOut !== undefined) K.to(el, { autoAlpha: 0, duration: 0.4 }, tOut);
    return el;
  };

  // ------------------------------------------------------------------ trees (brute force, recursion)
  /**
   * K.tree({x, y, w, h, root: {label, kids: [...], edge}, r, color}) in screen space.
   *   .grow(t, perLevel) -> [time each level is complete]   .mark(path, t, color) path = child indexes from root
   *   .hide(t)   .count(level) -> nodes on that level
   * K.fanTree({branching: 3, depth: 4, ...}) builds a full fan-out tree (the exponential picture).
   * K.dfsTree(G, src, depth) builds the real "every route" tree of a K.graph, labels = city ids, edge = price.
   */
  K.tree = function (o) {
    const levels = [];
    (function walk(n, d) { n.d = d; (levels[d] = levels[d] || []).push(n); (n.kids || []).forEach((k) => walk(k, d + 1)); })(o.root, 0);
    const leaves = []; (function lv(n) { if (!n.kids || !n.kids.length) leaves.push(n); else n.kids.forEach(lv); })(o.root);
    leaves.forEach((n, i) => (n.x = o.x + (leaves.length === 1 ? o.w / 2 : (i / (leaves.length - 1)) * o.w)));
    (function px(n) { if (n.kids && n.kids.length) { n.kids.forEach(px); n.x = n.kids.reduce((s, k) => s + k.x, 0) / n.kids.length; } })(o.root);
    const dy = levels.length > 1 ? o.h / (levels.length - 1) : 0;
    levels.forEach((lv, d) => lv.forEach((n) => (n.y = o.y + d * dy)));
    const svg = K.svg('svg', { width: K.W, height: K.H, viewBox: `0 0 ${K.W} ${K.H}`, class: 'tree' }, null);
    K.ui.appendChild(svg);
    const gE = K.svg('g', {}, svg), gN = K.svg('g', {}, svg), gL = K.svg('g', {}, svg);
    const color = K.vis(o.color ?? 'ink');
    // heat: ['amber', 'accent', 'rose'] colours each level from the first entry (root) to the last (leaves)
    const heat = (d) => o.heat ? K.vis(o.heat[Math.round((d / Math.max(1, levels.length - 1)) * (o.heat.length - 1))]) : color;
    levels.forEach((lv, d) => lv.forEach((n) => {
      const r = n.r = o.r ? o.r(d, levels.length) : Math.max(4, 30 - d * 6);
      (n.kids || []).forEach((k) => {
        k.edgeEl = K.svg('path', { d: `M${n.x},${n.y + r} C${n.x},${(n.y + k.y) / 2} ${k.x},${(n.y + k.y) / 2} ${k.x},${k.y - (o.r ? o.r(d + 1, levels.length) : Math.max(4, 30 - (d + 1) * 6))}`, class: 'tree-edge' }, gE);
        if (o.heat) Object.assign(k.edgeEl.style, { stroke: heat(d + 1), strokeOpacity: 0.7 });
        K.init(k.edgeEl, { drawSVG: '0%', autoAlpha: 0 });
        if (k.edge !== undefined && r >= 14) {
          const lt = K.svg('text', { x: (n.x + k.x) / 2 + (k.x >= n.x ? 12 : -12), y: (n.y + k.y) / 2, 'text-anchor': k.x >= n.x ? 'start' : 'end', class: 'tree-elabel mono' }, gL);
          lt.textContent = k.edge; k.elabel = lt; K.init(lt, { autoAlpha: 0 });
        }
      });
      n.el = K.svg('g', { transform: `translate(${n.x.toFixed(1)},${n.y.toFixed(1)})` }, gN);
      n.inner = K.svg('g', {}, n.el);
      n.disc = K.svg('circle', { r, class: 'tree-node', stroke: heat(d) }, n.inner);
      if (n.label !== undefined && r >= 14) { const t = K.svg('text', { y: r * 0.36, 'text-anchor': 'middle', class: 'tree-label', 'font-size': Math.round(r * 1.05) }, n.inner); t.textContent = n.label; }
      K.init(n.inner, { autoAlpha: 0, scale: 0.2, transformOrigin: '50% 50%' });
    }));
    const Tr = { levels, svg, root: o.root };
    Tr.count = (d) => levels[d].length;
    Tr.grow = (t, per = 0.45) => {
      const times = [];
      levels.forEach((lv, d) => {
        const td = t + d * per;
        lv.forEach((n, i) => {
          const j = td + (i / Math.max(1, lv.length)) * per * 0.5;
          if (d > 0) {
            K.set(n.edgeEl, { autoAlpha: 1 }, j);
            K.fromTo(n.edgeEl, { drawSVG: '0%' }, { drawSVG: '100%', duration: per * 0.6, ease: 'power2.out' }, j);
            if (n.elabel) K.to(n.elabel, { autoAlpha: 1, duration: 0.3 }, j + per * 0.4);
          }
          K.to(n.inner, { autoAlpha: 1, scale: 1, duration: 0.35, ease: 'back.out(2.4)' }, j + (d > 0 ? per * 0.45 : 0));
        });
        times.push(td + per);
      });
      return times;
    };
    Tr.mark = (path, t, c = 'accent') => {
      let n = o.root; const col = K.vis(c);
      K.to(n.disc, { stroke: col, fill: col, fillOpacity: 0.25, duration: 0.3 }, t);
      path.forEach((i, k) => {
        n = n.kids[i];
        const tk = t + (k + 1) * 0.18;
        K.to(n.edgeEl, { stroke: col, strokeWidth: 6, duration: 0.3 }, tk);
        K.to(n.disc, { stroke: col, fill: col, fillOpacity: 0.25, duration: 0.3 }, tk);
      });
      return n;
    };
    Tr.hide = (t, d = 0.4) => K.to(svg, { autoAlpha: 0, duration: d }, t);
    return Tr;
  };
  K.fanTree = (o) => {
    const mk = (d) => ({ kids: d < o.depth ? Array.from({ length: o.branching }, () => mk(d + 1)) : [] });
    const root = mk(0);
    root.label = o.rootLabel ?? '';
    return K.tree({ ...o, root });
  };
  K.dfsTree = (G, src, depth) => {
    const mk = (id, d) => ({ label: id, kids: d < depth ? Object.values(G.edges).filter((e) => e.from === id).map((e) => ({ ...mk(e.to, d + 1), edge: e.w })) : [] });
    return mk(String(src), 0);
  };
})();
