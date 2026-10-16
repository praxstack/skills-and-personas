/* kit/cards.js: header chrome, title card, chapter stings, lower thirds.

   KIT.chrome({tag: 'LC 787', title})            header (top-left), chapter pips (top-right), persistent chapter tag
   KIT.titleCard({kicker, lines: [...], sub, at, out})   big title; returns {el, out(t)}
   KIT.chapterCards({skip: [0], hold: 0.1})       a sting for every chapter in timing.js ("02 · BRUTE FORCE"),
                                                  a light sweep, the header tag and pips updated; skip the intro.
                                                  The card never covers content: at the previous chapter's last
                                                  spoken word the subject layers (#cam: the world, #hud: panels)
                                                  fade out (0.3 s), the card enters 0.3 s later over empty ground,
                                                  leaves at start + hold (+ 0.3 s), and only then do the subject
                                                  layers fade back in (0.25 s). Content that film.js brings in
                                                  under the card appears with the layers, after the card has gone
   KIT.cardIn(n) / KIT.cardClear(n)               when chapter n's card enters / has gone (the subject is back):
                                                  start each chapter's first entrances at cardClear(n), so the
                                                  subject is on screen before the chapter's voice starts
   KIT.lowerThird(text, t, d, {tone, left, top}) comic lower third ("7:00 AM RISE AND SHINE" style) */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  const pad = (n) => String(n).padStart(2, '0');
  let chapTag = null, pips = [];

  K.chrome = function (o = {}) {
    const c = K.layer.chrome;
    const brand = K.el('div', 'brand', c, null,
      `<span class="tag">${K.esc(o.tag || '')}</span>${o.tag ? '<span class="sep"></span>' : ''}<span class="name">${K.esc(o.title || K.T.title || '')}</span>`);
    K.hidden(brand);
    K.show(brand, o.at ?? 0.3, 0.6, { y: -12 });
    chapTag = K.stack(c, { left: 96, top: 136, width: 900, height: 48 }, 'chtag-holder');
    const row = K.el('div', 'pips', c);
    K.hidden(row);
    K.show(row, o.at ?? 0.3, 0.6, { y: -12 });
    pips = K.chapters.filter((ch) => ch.n > 0).map((ch) => {
      const p = K.el('div', 'pip', row);
      const i = K.el('i', '', p, { background: tok.light[ch.n % tok.light.length] });
      tl.fromTo(i, { scaleX: 0 }, { scaleX: 1, duration: Math.max(0.5, ch.end - ch.start), ease: 'none', immediateRender: false }, ch.start);
      return p;
    });
    return { brand, row };
  };

  K.titleCard = function (o) {
    const el = K.el('div', 'titlecard', K.layer.cards);
    const at = o.at ?? 0.2;
    if (o.kicker) {
      const k = K.el('div', 'kick', el, null, o.kicker);
      K.hidden(k);
      K.show(k, at, 0.6, { y: 16 });
      tl.fromTo(k, { letterSpacing: '0.42em' }, { letterSpacing: '0.16em', duration: 1.2, ease: 'expo.out', immediateRender: false }, at);
    }
    (o.lines || []).forEach((txt, i) => {
      const t = K.el('div', i ? 't2' : 't1', el, null, txt);
      K.riseChars(t, at + 0.15 + i * 0.3);
    });
    if (o.sub) { const s = K.el('div', 'sub', el, null, o.sub); K.hidden(s); K.show(s, at + 0.8, 0.6, { y: 14 }); }
    if (o.flourish !== false) {
      // a flight arc under the title: two airports, a dashed route drawing on, a small block hopping along it
      const svg = K.svg('svg', { width: 1920, height: 1080, viewBox: '0 0 1920 1080', style: 'position:absolute;left:0;top:0;overflow:visible' }, el);
      const y0 = o.arcY ?? 700, d = `M560,${y0} Q960,${y0 - 150} 1360,${y0}`;
      const arc = K.svg('path', { d, stroke: tok.color.accent, 'stroke-width': 4, fill: 'none', 'stroke-linecap': 'round', 'stroke-dasharray': '2 16' }, svg);
      const ends = [560, 1360].map((x) => K.svg('circle', { cx: x, cy: y0, r: 11, fill: tok.color.bg, stroke: tok.color.accent, 'stroke-width': 4 }, svg));
      const blk = K.svg('rect', { x: -15, y: -13, width: 30, height: 26, rx: 7, fill: tok.color.accent }, svg);
      K.hidden([arc, ...ends, blk]);
      ends.forEach((c, i) => K.pop(c, at + 0.5 + i * 0.2, 0.4, 0.2));
      tl.fromTo(arc, { opacity: 1, clipPath: 'inset(0% 100% 0% 0%)' }, { clipPath: 'inset(0% 0% 0% 0%)', duration: 1.2, ease: 'power2.inOut', immediateRender: false }, at + 0.6);
      tl.set(blk, { opacity: 1 }, at + 0.6);
      tl.fromTo(blk, { motionPath: { path: arc, align: arc, alignOrigin: [0.5, 0.5], autoRotate: true, start: 0, end: 0 } },
        { motionPath: { path: arc, align: arc, alignOrigin: [0.5, 0.5], autoRotate: true, start: 0, end: 1 }, duration: 1.2, ease: 'power2.inOut', immediateRender: false }, at + 0.6);
      tl.fromTo(arc, { strokeDashoffset: 0 }, { strokeDashoffset: -180, duration: 3, ease: 'none', immediateRender: false }, at + 0.6);
    }
    const out = (t) => tl.to(el, { opacity: 0, scale: 1.18, y: -40, filter: 'blur(10px)', duration: 0.55, ease: 'power2.in' }, t);
    if (o.out != null) out(o.out);
    return { el, out };
  };

  /** The sting's times for chapter n: word (subject starts fading out), t0 (card in), tOut (card starts leaving),
      back (card gone: the subject layers fade back in). */
  let HOLD = 0.1;
  function cardTimes(n, hold = HOLD) {
    const c = K.chapter(n);
    const prev = K.T.lines.filter((l) => l.chapter < n).pop();
    const word = prev ? prev.voiceAt + (prev.voiceDur || 0) : c.start - 0.8;
    const t0 = word + 0.3, tOut = Math.max(c.start + hold, t0 + 0.8);
    return { word, t0, tOut, back: tOut + 0.3 };
  }
  /** When chapter n's card comes in, and when it has gone and the subject returns. Bring the chapter's first
      content in at K.cardClear(n) (as the card leaves), not at the first line's voiceAt: the voice starts about
      0.6 s later (voice.py's chapter lead), and the subject must already be on screen when it does. */
  K.cardIn = (n) => cardTimes(n).t0;
  K.cardClear = (n) => cardTimes(n).back;

  /** One sting per chapter, built from timing.js. */
  K.chapterCards = function (o = {}) {
    if (o.hold != null) HOLD = o.hold;
    const skip = new Set(o.skip ?? [0]);
    const count = K.chapters.filter((c) => !skip.has(c.n)).length;
    const subj = [K.layer.cam, K.layer.hud]; // the persistent world and the screen-space panels
    K.chapters.forEach((c) => {
      const col = tok.light[c.n % tok.light.length], ink = tok.lightInk[c.n % tok.lightInk.length]; // the light as fill / as text
      const label = K.esc((o.names && o.names[c.n]) || c.name); // chapter names come from script.json: text, not markup
      if (skip.has(c.n)) return;
      // the card never sits over content: the subject fades out at the previous chapter's last word, the card
      // enters 0.3 s later over empty ground (lights, floor, header and captions stay), and the subject comes back
      // only after the card has left. Then it hands over to the chapter tag at top left.
      const { word, t0, tOut, back } = cardTimes(c.n, o.hold);
      tl.fromTo(subj, { opacity: 1 }, { opacity: 0, duration: 0.3, ease: 'power2.in', immediateRender: false }, word);
      tl.fromTo(subj, { opacity: 0 }, { opacity: 1, duration: 0.25, ease: 'power2.out', immediateRender: false }, back);
      if (chapTag) chapTag.to(tOut + 0.05,
        `<div class="chtag"><span class="n" data-layout-allow-overlap style="color:${ink}">${pad(c.n)}</span><span class="t" data-layout-allow-overlap>${label}</span></div>`, { align: 'flex-start', mode: 'fade' });
      const s = K.decor(K.el('div', 'sting', K.layer.cards)); // a deliberate overlay: not layout-audited
      s.style.setProperty('--c', col);
      s.style.setProperty('--ci', ink);
      const slab = K.el('div', 'slab', s);
      const num = K.el('div', 'num', s, null, pad(c.n));
      const ttl = K.el('div', 'ttl', s, null, `<b>${label}</b><span>part ${c.n} of ${count}</span>`);
      K.hidden(s);
      tl.set(s, { opacity: 1 }, t0);
      tl.fromTo(slab, { x: -900, skewX: -30 }, { x: 0, skewX: 0, duration: 0.5, ease: 'expo.out', immediateRender: false }, t0);
      tl.fromTo(num, { opacity: 0, scale: 2.2, rotation: -12 }, { opacity: 1, scale: 1, rotation: 0, duration: 0.45, ease: 'back.out(2.2)', immediateRender: false }, t0 + 0.12);
      tl.fromTo(ttl, { opacity: 0, x: -60 }, { opacity: 1, x: 0, duration: 0.5, ease: 'expo.out', immediateRender: false }, t0 + 0.2);
      tl.to(s, { x: 30, duration: tOut - t0, ease: 'none' }, t0);
      tl.to(s, { opacity: 0, x: 260, skewX: -8, duration: 0.3, ease: 'power2.in' }, tOut);
      K.sweep(t0 - 0.05);
    });
  };

  K.lowerThird = function (text, t, d = 3, o = {}) {
    const col = K.tone(o.tone || 'gold');
    const e = K.el('div', 'chip', o.parent || K.layer.chrome, { left: o.left ?? 96, top: o.top ?? 196, background: tok.color.slab, borderColor: col, borderRadius: 8,
      fontFamily: tok.font.display, fontStyle: 'italic', fontWeight: 900, fontSize: 30, letterSpacing: '0.04em', textTransform: 'uppercase', color: K.ink(o.tone || 'gold'), boxShadow: `6px 6px 0 ${col}` }, text);
    K.hidden(e);
    K.show(e, t, 0.45, { x: -40, skewX: -12 }, 'expo.out');
    if (d) K.hide(e, t + d, 0.3, { x: 30 });
    return e;
  };
})();
