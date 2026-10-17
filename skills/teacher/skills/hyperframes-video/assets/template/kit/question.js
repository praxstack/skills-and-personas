/* kit/question.js: a question card with a countdown ring for the line's think pause (dsa-five-part-format.md:
   "the question card stays up during the think pause with a ring counting down; the subject stays visible").

   const Q = KIT.question({n: 1, line: KIT.L.q1, text: 'What is simpler to count than stops?', x, y, w})
   - slides in as the line starts, types the question while it is spoken
   - the ring counts down line.think seconds from the end of the voice, ticking whole seconds
   Q.answer(t, {tone: 'good'})   badge turns to a check, ring fades (call it at the answer line)
   Q.out(t)                      leaves */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  K.question = function (o) {
    const ln = o.line, w = o.w || 1360, x = o.x ?? Math.round((1920 - w) / 2), y = o.y ?? 196;
    const tone = K.tone(o.tone || 'accent');
    const card = K.el('div', 'panel qcard', o.parent || K.layer.hud, { left: x, top: y, width: w, minHeight: 124 });
    const badge = K.el('div', 'badge', card, { background: tone, color: K.on(o.tone || 'accent', 'onBadge') }, 'Q' + (o.n ?? ''));
    const q = K.el('div', 'q', card, { flex: 1 }, o.text ?? ln.cap.replace(/^question\s*\d*\s*:\s*/i, ''));
    const ringBox = K.el('div', 'ring', card);
    const svg = K.svg('svg', { width: 96, height: 96, viewBox: '0 0 96 96' }, ringBox);
    K.svg('circle', { cx: 48, cy: 48, r: 40, fill: 'none', stroke: tok.color.line2, 'stroke-width': 8 }, svg);
    const arc = K.svg('circle', { cx: 48, cy: 48, r: 40, fill: 'none', stroke: tone, 'stroke-width': 8, 'stroke-linecap': 'round', transform: 'rotate(-90 48 48)' }, svg);
    const num = K.stack(ringBox, { left: 0, top: 0, width: 96, height: 96 }, 'num');
    const check = K.el('div', 'abs', badge, { inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: tok.font.body, fontWeight: 900, fontSize: 46, color: K.on('good', 'onCheck'), background: K.tone('good'), borderRadius: 20 }, '✓');
    K.hidden([card, check, ringBox]);
    gsap.set(q, { clipPath: 'inset(-20% 100% -20% 0%)' }); // the card slides in empty and types as the line is spoken
    const t0 = ln.voiceAt - 0.2;
    tl.fromTo(card, { opacity: 0, y: -40, scale: 0.96 }, { opacity: 1, y: 0, scale: 1, duration: 0.55, ease: 'expo.out', immediateRender: false }, t0);
    tl.fromTo(badge, { rotation: -25, scale: 0.4 }, { rotation: 0, scale: 1, duration: 0.6, ease: 'back.out(2.6)', immediateRender: false }, t0 + 0.05);
    K.type(q, ln.voiceAt, q.textContent.length, Math.max(28, q.textContent.length / (ln.voiceDur * 0.75)));
    const think = ln.think || 0;
    if (think > 0) {
      const a = ln.voiceEnd;
      gsap.set(arc, { drawSVG: '100%' });
      K.pop(ringBox, a - 0.3, 0.4, 0.5);
      tl.fromTo(arc, { drawSVG: '100%' }, { drawSVG: '0%', duration: think, ease: 'none', immediateRender: false }, a);
      tl.to(arc, { attr: { stroke: K.tone('bad') }, duration: think, ease: 'power1.in' }, a);
      const n = Math.ceil(think - 1e-6);
      for (let k = 0; k < n; k++) num.to(k === 0 ? a - 0.3 : a + k, String(n - k), { d: 0.25, color: tok.color.ink });
      K.pulse(ringBox, a + think - 0.25, 1.12, 0.4);
    }
    const Q = { el: card };
    Q.answer = (t, f = {}) => {
      tl.fromTo(check, { opacity: 0, scale: 0.3 }, { opacity: 1, scale: 1, duration: 0.45, ease: 'back.out(3)', immediateRender: false }, t);
      tl.to(card, { borderColor: K.tone(f.tone || 'good'), duration: 0.3 }, t);
      if (think > 0) K.hide(ringBox, t, 0.3, { scale: 0.6 });
    };
    Q.out = (t) => K.hide(card, t, 0.35, { y: -30 });
    return Q;
  };
})();
