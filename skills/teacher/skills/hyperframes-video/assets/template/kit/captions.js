/* kit/captions.js: the caption band. One caption per narration line, taken from timing.js `cap`, shown while the
   line is spoken (and through its think pause), bottom 180 px, wrapping to two lines at most. Numbers, ∞ and
   O(...) are tinted so the eye finds them. KIT.captions({emphasis: /regex/}) builds them all. */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl;
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  K.capHTML = function (cap, emphasis) {
    const keep = [];
    // O(...) spans are set aside under private-use placeholders so the emphasis pass cannot touch them
    let s = esc(cap).replace(/O\((?:[^()]|\([^()]*\))*\)/g, (m) => { keep.push(`<span class="o">${K.fmtO(m)}</span>`); return String.fromCharCode(0xe000 + keep.length - 1); });
    s = s.replace(emphasis, '<em>$1</em>');
    return s.replace(/[\ue000-\ue0ff]/g, (c) => keep[c.charCodeAt(0) - 0xe000]);
  };

  K.captions = function (o = {}) {
    const emphasis = o.emphasis || /(\b\d+\b|∞|\bk\s?\+\s?1\b|→)/g;
    const layer = K.layer.caps;
    layer.classList.add('scrim'); // the dark band behind captions (style/kit.css)
    const ls = K.T.lines;
    const ins = ls.map((l) => Math.max(0, l.voiceAt - 0.12));
    ls.forEach((l, i) => {
      const e = K.el('div', 'cap', layer, null, K.capHTML(l.cap, emphasis));
      e.setAttribute('data-layout-allow-caption-zone', '');
      const tin = ins[i], next = ins[i + 1];
      const tout = next != null && next - l.end < 1.2 ? next - 0.1 : l.end - 0.05;
      tl.fromTo(e, { opacity: 0, y: 14 }, { opacity: 1, y: 0, duration: 0.22, ease: 'power2.out', immediateRender: false }, tin);
      tl.to(e, { opacity: 0, duration: 0.12, ease: 'power1.in' }, Math.max(tin + 0.3, tout));
    });
  };
})();
