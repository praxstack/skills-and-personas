/* kit/burst.js: comic callouts ("700!", "POP!", "NOPE!"): a spiky starburst with halftone dots and speed lines,
   lettered in Bangers, popping with overshoot. Add an sfx to the line in script.json ("pop" or "thud") so the sound
   lands with it.

   KIT.burst('700!', t, {x: 1500, y: 300, tone: 'gold', size: 1, rot: -8, hold: 1.2})
     x, y are screen coordinates (HUD). For a point on the subject use KIT.cam.toScreen(wx, wy, t).
     hold = seconds on screen before it pops away (0 = stays). Returns the element. */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok, CL = K.col;
  let n = 0;
  K.burst = function (text, t, o = {}) {
    const size = o.size || 1, R = 150 * size * Math.max(1, text.length / 5.5) ** 0.5, r = K.rand(o.seed || 17 + n);
    const col = K.tone(o.tone || 'gold'), id = 'bu' + n++;
    let col2 = K.tone(o.tone2 || 'accent');
    // colours (kit/tokens.js color.burst). The original letters the word white with a dark outline over a cream
    // highlight; a theme letters and outlines it in the fill's on-colour, moves the highlight away from the word
    // (lighter under a dark word, darker under a light one), and keeps the rim tone only where the word reads on it.
    const B = Object.assign({}, tok.color.burst);
    if (tok.themed) {
      B.word = K.on(o.tone || 'gold');
      const dark = CL.lum(B.word) < 0.18;
      B.wordLine = CL.mix(B.word, col, 0.2); // same polarity as the word: outline and letters read as one ink on the fill
      B.hi = CL.mix(col, dark ? '#FFFFFF' : '#000000', dark ? 0.45 : 0.18);
      for (let k = 0; k < 10 && CL.ratio(B.word, col2) < 4.6; k++) col2 = CL.mix(col2, col, 0.25);
    }
    const wrap = K.decor(K.el('div', 'burst', o.parent || K.layer.hud, { left: o.x ?? 960, top: o.y ?? 400 }));
    const svg = K.svg('svg', { width: 2 * R * 1.6, height: 2 * R * 1.6, viewBox: `${-R * 1.6} ${-R * 1.6} ${R * 3.2} ${R * 3.2}`, style: `left:${-R * 1.6}px;top:${-R * 1.6}px` }, wrap);
    const defs = K.svg('defs', {}, svg);
    const lg = K.svg('radialGradient', { id: id + 'g', cx: '45%', cy: '40%', r: '65%' }, defs);
    K.svg('stop', { offset: '0%', 'stop-color': B.hi }, lg);
    K.svg('stop', { offset: '45%', 'stop-color': col }, lg);
    K.svg('stop', { offset: '100%', 'stop-color': col2 }, lg);
    const pat = K.svg('pattern', { id: id + 'p', width: 14, height: 14, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(30)' }, defs);
    K.svg('circle', { cx: 7, cy: 7, r: 2.6, fill: B.line, opacity: 0.22 }, pat);
    // speed lines
    const lines = K.svg('g', {}, svg);
    const ls = [];
    for (let i = 0; i < 12; i++) {
      const a = (i / 12) * Math.PI * 2 + r() * 0.3, r0 = R * 1.08, r1 = R * (1.3 + r() * 0.25);
      ls.push(K.svg('path', { d: `M${Math.cos(a) * r0},${Math.sin(a) * r0} L${Math.cos(a) * r1},${Math.sin(a) * r1}`, stroke: col, 'stroke-width': 7, 'stroke-linecap': 'round', fill: 'none' }, lines));
    }
    // starburst polygon
    const spikes = o.spikes || 14, pts = [];
    for (let i = 0; i < spikes * 2; i++) {
      const a = (i / (spikes * 2)) * Math.PI * 2 - Math.PI / 2, rr = i % 2 ? R * (0.66 + r() * 0.08) : R * (0.95 + r() * 0.12);
      pts.push(`${(Math.cos(a) * rr * 1.18).toFixed(1)},${(Math.sin(a) * rr * 0.92).toFixed(1)}`);
    }
    const g = K.svg('g', {}, svg);
    K.svg('polygon', { points: pts.join(' '), fill: B.drop, opacity: B.dropA, transform: 'translate(10,10)' }, g);
    K.svg('polygon', { points: pts.join(' '), fill: `url(#${id}g)`, stroke: B.line, 'stroke-width': 7, 'stroke-linejoin': 'round' }, g);
    K.svg('polygon', { points: pts.join(' '), fill: `url(#${id}p)` }, g);
    const word = K.el('div', 'word', wrap, { fontSize: Math.round(96 * size) }, text);
    if (tok.themed) { word.style.color = B.word; word.style.setProperty('--burst-line', B.wordLine); }
    gsap.set(wrap, { rotation: o.rot ?? -8 });
    gsap.set(word, { xPercent: -50, yPercent: -50 });
    K.hidden(wrap);
    K.drawable(ls);
    tl.set(wrap, { opacity: 1 }, t);
    tl.fromTo(g, { scale: 0, rotation: -30, transformOrigin: '50% 50%' }, { scale: 1, rotation: 0, duration: 0.42, ease: 'back.out(3.2)', immediateRender: false }, t);
    tl.fromTo(word, { scale: 0.8, rotation: 12 }, { scale: 1, rotation: 0, duration: 0.45, ease: 'back.out(3.6)', immediateRender: false }, t + 0.06); // starts at 0.8: legible from its first frames
    ls.forEach((l, i) => K.draw(l, t + 0.05 + (i % 3) * 0.03, 0.22, 'power2.out'));
    tl.to(ls, { drawSVG: '100% 100%', duration: 0.3, ease: 'power2.in' }, t + 0.35);
    tl.to(wrap, { scale: 1.06, duration: Math.max(0.2, (o.hold ?? 1.2) - 0.2), ease: 'sine.inOut' }, t + 0.45);
    if ((o.hold ?? 1.2) > 0) tl.to(wrap, { scale: 0, opacity: 0, rotation: (o.rot ?? -8) + 14, duration: 0.25, ease: 'back.in(2)' }, t + (o.hold ?? 1.2) + 0.25);
    return wrap;
  };
})();
