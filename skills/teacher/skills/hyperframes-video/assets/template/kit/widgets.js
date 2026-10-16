/* kit/widgets.js: small HUD pieces.

   KIT.meter({x, y, label: 'COST', value: '0', tone})        a running total; M.count(t, d, a, b) / M.to(t, '700', tone)
   KIT.pips({x, y, label: 'STOPS', max: 1})                  slots that fill: P.fill(i, t, tone) / P.empty(i, t)
   KIT.note(html, t, {x, y, tone, size, hold})               a chip with a short fact ("k + 1 = 2 flights")
   KIT.headline(html, t, {x, y, size, align, tone})          big display text (recaps); returns {el, out(t)}
   KIT.fanTree({x, y, w, h, branch: 3, depth: 2, labels})    a recursion tree for brute force: T.grow(t, perLevel) */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;

  K.meter = function (o) {
    const el = K.el('div', 'panel meter', o.parent || K.layer.hud, { left: o.x, top: o.y, minWidth: o.w || 220 });
    K.el('div', 'lbl', el, null, o.label || '');
    const vbox = K.el('div', 'v', el, { position: 'relative', height: 62, color: K.ink(o.tone || 'ink') });
    const v = K.stack(vbox, { left: 0, top: 0, width: (o.w || 220) - 52, height: 62 });
    v.to(null, o.value ?? '0', { align: 'flex-start' });
    K.hidden(el);
    const M = { el };
    M.show = (t) => K.show(el, t, 0.5, { x: 40 }, 'expo.out');
    M.out = (t) => K.hide(el, t, 0.3, { x: 40 });
    M.to = (t, val, tone) => v.to(t, val, { align: 'flex-start', color: K.ink(tone || o.tone || 'ink'), d: 0.35 });
    M.count = (t, d, a, b, tone) => {
      const s = v.to(t, String(a), { align: 'flex-start', color: K.ink(tone || o.tone || 'ink'), mode: 'fade', d: 0.01 });
      K.count(s, t, d, a, b);
      return t + d;
    };
    return M;
  };

  K.pips = function (o) {
    const el = K.el('div', 'panel meter', o.parent || K.layer.hud, { left: o.x, top: o.y });
    K.el('div', 'lbl', el, null, o.label || '');
    const row = K.el('div', 'pipsrow', el);
    const slots = Array.from({ length: o.max || 1 }, () => { const s = K.el('div', 'sp', row); return K.el('i', '', s); });
    const cap = o.caption ? K.el('div', 'lbl', el, { marginTop: 6, color: tok.color.mute }, o.caption) : null;
    K.hidden(el);
    const P = { el, slots, cap };
    P.show = (t) => K.show(el, t, 0.5, { x: 40 }, 'expo.out');
    P.out = (t) => K.hide(el, t, 0.3, { x: 40 });
    P.fill = (i, t, tone = 'accent') => {
      const s = slots[i];
      tl.to(s, { backgroundColor: K.tone(tone), duration: 0.01 }, t);
      tl.fromTo(s, { opacity: 0, scale: 0.2 }, { opacity: 1, scale: 1, duration: 0.4, ease: 'back.out(3)', immediateRender: false }, t);
    };
    P.empty = (i, t) => K.hide(slots[i], t, 0.25);
    return P;
  };

  K.note = function (html, t, o = {}) {
    const col = K.tone(o.tone || 'accent');
    const e = K.el('div', 'chip', o.parent || K.layer.hud, { left: o.x ?? 960, top: o.y ?? 400, fontSize: o.size || 30, borderColor: col, color: o.ink || tok.color.ink, fontWeight: 600 }, html);
    gsap.set(e, { xPercent: o.align === 'left' ? 0 : -50, yPercent: -50 });
    K.hidden(e);
    K.pop(e, t, 0.45, 0.5);
    if (o.hold) K.hide(e, t + o.hold, 0.3);
    return e;
  };

  K.headline = function (html, t, o = {}) {
    const e = K.el('div', 'headline', o.parent || K.layer.hud, { left: o.x ?? 0, top: o.y ?? 400, width: o.w ?? 1920, textAlign: o.align || 'center', fontSize: o.size || 84, color: K.ink(o.tone || 'ink') }, html);
    K.hidden(e);
    if (o.chars) { gsap.set(e, { opacity: 1 }); K.riseChars(e, t, 0.02, 0.6); }
    else K.show(e, t, 0.6, { y: 30, scale: 0.97 }, 'expo.out');
    return { el: e, out: (tt) => K.hide(e, tt, 0.35, { y: -20 }) };
  };

  K.fanTree = function (o) {
    const svg = o.svg || K.layer.hudsvg, g = K.svg('g', {}, svg);
    const r = o.r || 32, levels = [];
    let count = 1;
    for (let lv = 0; lv <= (o.depth ?? 2); lv++) {
      const y = o.y + (lv * o.h) / Math.max(1, o.depth ?? 2), row = [];
      for (let i = 0; i < count; i++) row.push({ x: o.x + (o.w * (i + 0.5)) / count, y, parent: lv ? Math.floor(i / (o.branch || 3)) : null, lv, i });
      levels.push(row);
      count *= o.branch || 3;
    }
    const lab = o.labels || ((lv, i) => String((i * 7 + lv * 3) % 4));
    levels.forEach((row, lv) => row.forEach((n) => {
      if (lv) {
        const p = levels[lv - 1][n.parent];
        n.edge = K.svg('path', { d: `M${p.x},${p.y + r} L${n.x},${n.y - r}`, stroke: tok.color.line2, 'stroke-width': 3, fill: 'none', 'stroke-linecap': 'round' }, g);
        K.drawable(n.edge);
      }
      n.g = K.svg('g', { transform: `translate(${n.x},${n.y})` }, g);
      n.c = K.svg('circle', { r, fill: tok.color.panel2, stroke: tok.color.line2, 'stroke-width': 3 }, n.g);
      K.text(n.g, 0, 1, lab(lv, n.i), { 'font-size': Math.max(tok.size.label, Math.round(r * 0.95)), 'font-weight': 700, fill: tok.color.ink, class: 'mono' });
      K.hidden(n.g);
    }));
    const T = { g, levels };
    T.grow = (t, per = 0.6, tone) => {
      levels.forEach((row, lv) => {
        const t0 = t + lv * per;
        row.forEach((n, i) => {
          const tt = t0 + (i / Math.max(1, row.length)) * per * 0.6;
          if (n.edge) K.draw(n.edge, tt, per * 0.5, 'power2.out');
          K.pop(n.g, tt + (n.edge ? per * 0.35 : 0), 0.4, 0.2);
          if (tone && lv === levels.length - 1) tl.to(n.c, { attr: { stroke: K.tone(tone) }, duration: 0.3 }, tt + per * 0.5);
        });
      });
      return t + levels.length * per;
    };
    T.out = (t) => K.hide(g, t, 0.4);
    return T;
  };
})();
