/* kit/ladder.js: the complexity ladder: every approach as a rung with time and space, a bar whose length is its
   cost, the interview pick stamped.

   const LD = KIT.ladder({x: 820, y: 230, w: 1000, rungs: [
     {name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1.0},
     {name: 'Bellman-Ford, k + 1 rounds', time: 'O(k·E)', space: 'O(n)', cost: 0.3}]})
   LD.show(t, 0.12)  /  LD.rung(i, t)       rungs slide in (all, or one)
   LD.focus(i, t, tone)                     that rung lights (border, glow, scale); the others step back to
                                            tok.dimOpacity, still readable
   LD.strike(i, t)                          too slow: struck through in rose
   LD.pick(i, t, 'INTERVIEW PICK')          stamped in mint */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  K.ladder = function (o) {
    const w = o.w || 1000, rh = o.rungH || 116, gap = o.gap ?? 20, bw = o.barW || 230;
    const box = K.el('div', 'ladder', o.parent || K.layer.hud, { left: o.x, top: o.y, width: w, height: o.rungs.length * (rh + gap) });
    const rungs = o.rungs.map((r, i) => {
      const e = K.el('div', 'rung panel', box, { top: i * (rh + gap), width: w, height: rh });
      K.el('div', 'idx', e, null, String(i + 1).padStart(2, '0')).setAttribute('data-layout-allow-overflow', '');
      K.el('div', 'nm', e, null, r.name);
      K.el('div', 'cx', e, null, `time <b style="color:${tok.color.ink}">${K.fmtO(r.time)}</b>${r.space ? `&nbsp;&nbsp;·&nbsp;&nbsp;space <b style="color:${tok.color.ink}">${K.fmtO(r.space)}</b>` : ''}`);
      const bar = K.el('div', 'bar', e, { width: bw });
      const fill = K.el('i', '', bar, { width: Math.max(0.06, Math.min(1, r.cost ?? 0.5)) * bw, background: K.tone(r.tone || ((r.cost ?? 0.5) > 0.7 ? 'bad' : (r.cost ?? 0.5) > 0.4 ? 'gold' : 'good')) });
      gsap.set(fill, { scaleX: 0 });
      K.hidden(e);
      return { e, fill, r };
    });
    const LD = { el: box, rungs };
    LD.rung = (i, t) => {
      K.show(rungs[i].e, t, 0.5, { x: 80 }, 'expo.out');
      tl.to(rungs[i].fill, { scaleX: 1, duration: 0.8, ease: 'power2.out' }, t + 0.25);
    };
    LD.show = (t, stagger = 0.12, ids) => (ids || rungs.map((_, i) => i)).forEach((i, k) => LD.rung(i, t + k * stagger));
    LD.focus = (i, t, tone = 'accent', d = 0.35) => {
      const col = K.tone(tone);
      rungs.forEach((r, k) => {
        if (k === i) tl.to(r.e, { opacity: 1, scale: 1.03, borderColor: col, boxShadow: `0 0 0 3px ${col}55, 0 24px 60px ${K.shade(0.55)}`, duration: d, ease: 'power2.out' }, t);
        // the others step back (tok.dimOpacity keeps their text above 4.5:1); the focus is the border, glow and scale
        else tl.to(r.e, { opacity: tok.dimOpacity, scale: 1, borderColor: tok.color.line, boxShadow: `0 24px 60px ${K.shade(0.55)}`, duration: d }, t);
      });
    };
    LD.unfocus = (t, d = 0.35) => tl.to(rungs.map((r) => r.e), { opacity: 1, scale: 1, duration: d }, t);
    LD.strike = (i, t) => {
      const s = K.el('div', 'abs', rungs[i].e, { left: 20, top: rh / 2 - 3, width: w - 40, height: 6, borderRadius: 3, background: K.tone('bad') });
      gsap.set(s, { scaleX: 0, transformOrigin: '0 50%' });
      tl.to(s, { scaleX: 1, duration: 0.4, ease: 'power2.inOut' }, t);
    };
    LD.pick = (i, t, label = 'INTERVIEW PICK', tone = 'good') => {
      const col = K.tone(tone);
      // straddles the rung's bottom edge at the right, clear of its cost bar and of the rung above
      const s = K.el('div', 'stamp', rungs[i].e, { right: 28, top: rh - 30, zIndex: 2, color: K.ink(tone), borderColor: col, background: tok.color.slab }, label);
      tl.fromTo(s, { opacity: 0, scale: 2.4, rotation: -16 }, { opacity: 1, scale: 1, rotation: -6, duration: 0.32, ease: 'power3.in', immediateRender: false }, t);
      K.shake(rungs[i].e, t + 0.3, 5, 0.3);
      return s;
    };
    LD.out = (t) => K.hide(box, t, 0.4, { x: 80 });
    return LD;
  };
})();
