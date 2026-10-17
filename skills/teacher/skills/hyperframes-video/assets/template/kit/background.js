/* kit/background.js: depth and light behind everything.
   KIT.background({floor: true, bokeh: 22, grain: true})
   - a key light and a rim light per chapter (colours from tok.light / tok.rim), cross-fading at chapter changes
   - a perspective floor grid that slowly scrolls (constant, quiet motion), lit in the chapter colour
   - out-of-focus bokeh drifting upward, film grain, and a vignette over the whole frame
   KIT.sweep(t) draws a light sweep across the frame (chapter stings call it). */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  const hexA = (hex, a) => hex + Math.round(a * 255).toString(16).padStart(2, '0');
  const fx = tok.fx, lk = fx.lightK, bk = fx.bokehK; // light strengths: 1 on dark grounds, softer on light ones

  function grainURL(seed = 3) {
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const g = c.getContext('2d'), img = g.createImageData(256, 256), r = K.rand(seed);
    for (let i = 0; i < img.data.length; i += 4) {
      const v = Math.floor(r() * 255);
      img.data[i] = img.data[i + 1] = img.data[i + 2] = v;
      img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
    return c.toDataURL('image/png');
  }

  /* The floor is a perspective grid drawn on a canvas as a pure function of film time (a CSS 3D plane with a
     moving background repaints ~6 MP per frame and roughly halves render speed in the software renderer).
     Lines scroll toward the viewer, converge on the horizon and take the chapter's light colour. */
  function floor(bg, chs, total) {
    const W = 1920, TOP = 600, H = 1080 - TOP, HY = 36, NEAR = H - HY; // horizon at y = TOP + HY
    const cv = K.decor(K.el('canvas', 'floorcv', bg, { left: 0, top: TOP, width: W, height: H }));
    cv.width = W; cv.height = H;
    const g = cv.getContext('2d');
    const rgb = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
    const cols = chs.map((c) => rgb(tok.light[c.n % tok.light.length]));
    const colorAt = (t) => {
      let c = cols[0];
      chs.forEach((ch, i) => {
        if (!i) return;
        const p = Math.min(1, Math.max(0, (t - (ch.start - 0.5)) / 1.4));
        if (p > 0) { const e = 0.5 - Math.cos(Math.PI * p) / 2; c = c.map((v, k) => v + (cols[i][k] - v) * e); }
      });
      return c.map(Math.round).join(',');
    };
    const CELL = 0.32, SPEED = 0.14, PITCH = 190; // depth step, cells per second, lateral spacing at the near edge (px)
    const draw = (t) => {
      g.clearRect(0, 0, W, H);
      const c = colorAt(t), fade = g.createLinearGradient(0, HY, 0, H);
      fade.addColorStop(0, `rgba(${c},0)`); fade.addColorStop(0.3, `rgba(${c},${+(0.10 * fx.floorK).toFixed(3)})`); fade.addColorStop(1, `rgba(${c},${+(0.30 * fx.floorK).toFixed(3)})`);
      g.strokeStyle = fade;
      const off = ((t * SPEED) % 1) * CELL;
      g.beginPath();
      for (let k = 0; k < 400; k++) { // horizontal lines: depth z = 1 + k*CELL - off, screen y = HY + NEAR / z
        const z = 1 + k * CELL - off;
        if (z < 0.98) continue;
        const y = HY + NEAR / z;
        if (y - HY < 3) break;
        g.moveTo(0, y); g.lineTo(W, y);
      }
      for (let j = -14; j <= 14; j++) { const x = W / 2 + j * PITCH; g.moveTo(x, H); g.lineTo(W / 2 + ((x - W / 2) * 4) / NEAR, HY + 4); }
      g.lineWidth = 2;
      g.stroke();
    };
    let cur = -1;
    const clock = { get t() { return cur; }, set t(v) { if (v !== cur) { cur = v; draw(v); } } };
    tl.fromTo(clock, { t: 0 }, { t: total, duration: total, ease: 'none', immediateRender: false }, 0);
    clock.t = 0;
  }

  K.background = function (opts = {}) {
    const o = Object.assign({ floor: true, bokeh: 22, grain: true, vignette: true }, opts);
    const bg = K.layer.bg, total = K.T.total, chs = K.chapters;
    // chapter lights
    chs.forEach((c, i) => {
      const col = tok.light[c.n % tok.light.length], rim = tok.rim[c.n % tok.rim.length];
      const key = K.decor(K.el('div', 'light', bg, { left: -520, top: -760, width: 1900, height: 1900, background: `radial-gradient(circle, ${hexA(col, 0.30 * lk)} 0%, ${hexA(col, 0.10 * lk)} 34%, ${hexA(col, 0)} 64%)` }));
      const rl = K.decor(K.el('div', 'light', bg, { left: 1000, top: 260, width: 1500, height: 1500, background: `radial-gradient(circle, ${hexA(rim, 0.20 * lk)} 0%, ${hexA(rim, 0.06 * lk)} 38%, ${hexA(rim, 0)} 64%)` }));
      const hz = K.decor(K.el('div', 'horizon', bg, { background: `radial-gradient(60% 50% at 50% 50%, ${hexA(col, 0.22 * lk)} 0%, ${hexA(col, 0)} 100%)` }));
      const ls = [key, rl, hz];
      const a = i === 0 ? 0 : c.start - 0.5, b = i + 1 < chs.length ? chs[i + 1].start - 0.5 : total + 1;
      if (i === 0) gsap.set(ls, { opacity: 1 });
      else tl.fromTo(ls, { opacity: 0 }, { opacity: 1, duration: 1.4, ease: 'sine.inOut', immediateRender: false }, a);
      if (b < total) tl.to(ls, { opacity: 0, duration: 1.4, ease: 'sine.inOut' }, b);
      // the key light wanders a little while it is on
      tl.fromTo(key, { x: 0, y: 0 }, { x: 260, y: 120, duration: Math.max(1, b - a + 1.4), ease: 'sine.inOut', immediateRender: false }, Math.max(0, a));
    });
    if (o.floor) floor(bg, chs, total);
    // bokeh (deterministic)
    const r = K.rand(11);
    for (let i = 0; i < o.bokeh; i++) {
      const s = 18 + r() * 110, x = r() * 1920, y = 80 + r() * 900, warm = r() < 0.5;
      const col = warm ? tok.light[0] : tok.rim[0];
      const b = K.decor(K.el('div', 'bokeh', bg, { left: x, top: y, width: s, height: s, opacity: 0.25 + r() * 0.5,
        background: `radial-gradient(circle, ${hexA(col, 0.20 * bk)} 0%, ${hexA(col, 0.08 * bk)} 55%, ${hexA(col, 0)} 72%)` }));
      tl.fromTo(b, { x: 0, y: 0 }, { x: (r() - 0.5) * 160, y: -(60 + r() * 160), duration: total, ease: 'sine.inOut', immediateRender: false }, 0);
    }
    if (o.grain) K.decor(K.el('div', 'grain', K.layer.fx, { backgroundImage: `url(${grainURL()})` }));
    // the original darkens the whole frame at the edges; a theme shades only the ground (behind the subject), so the
    // edge never washes text toward deep: theme inks hold 4.6:1 on the surfaces, with little margin to spare
    if (o.vignette) (tok.themed ? K.layer.bg : K.layer.fx).classList.add('vig');
  };

  /** A soft light sweep across the whole frame (chapter changes). */
  K.sweep = function (t, d = 0.9) {
    const s = K.decor(K.el('div', 'sweep', K.layer.fx));
    tl.fromTo(s, { x: -900, opacity: 1 }, { x: 2300, opacity: 1, duration: d, ease: 'power2.inOut', immediateRender: false }, t);
    tl.set(s, { opacity: 0 }, t + d);
  };
})();
