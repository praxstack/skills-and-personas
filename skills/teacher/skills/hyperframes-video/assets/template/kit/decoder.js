/* kit/decoder.js: the raw input as text (`flights = [[0,1,100],...]`), whose entries fly into the subject, so the
   viewer sees the mapping from text to picture (dsa-five-part-format.md: "Decoding inputs").

   const D = KIT.decoder({x: 360, y: 150, rows: ['n = 4   src = 0', 'flights = [[0,1,100],[1,2,100]]'], fs: 30})
   D.show(t) / D.hide(t)
   D.tok('e0', 1, '[0,1,100]')            register a token by its text in a row (nth occurrence optional)
   D.hl('e0', t, 'accent') / D.unhl('e0', t)
   D.fly('e0', t, d, KIT.cam.toScreen(wx, wy, t + d), {tone})   a copy travels from the text to the picture
   D.dimTok('e0', t, 0.35)                fade a used token back */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  const colorize = (s) => s.replace(/([A-Za-z_][A-Za-z0-9_]*)|(-?\d+)|([[\](),=])/g, (m, id, nu, pn) =>
    id ? `<span class="id">${id}</span>` : nu ? `<span class="nu">${nu}</span>` : `<span class="pn">${pn}</span>`);

  K.decoder = function (o) {
    const fs = o.fs || 30, cw = fs * tok.mono, lh = Math.round(fs * 1.75), px = o.pad ?? 30, py = o.padY ?? 22;
    const maxLen = Math.max(...o.rows.map((r) => r.length));
    const w = o.w || Math.round(maxLen * cw + 2 * px), h = o.rows.length * lh + 2 * py;
    const x = o.x ?? Math.round((1920 - w) / 2), y = o.y ?? 150;
    const panel = K.el('div', 'panel decoder', o.parent || K.layer.hud, { left: x, top: y, width: w, height: h });
    const inner = K.el('div', 'abs mono', panel, { left: 0, top: 0, width: w, height: h, fontSize: fs });
    if (tok.themed) inner.style.zIndex = 1; // a theme's token highlight is opaque (K.tint): the text sits on top of it
    o.rows.forEach((r, i) => K.el('div', 'row', inner, { left: px, top: py + i * lh, lineHeight: lh + 'px', height: lh }, colorize(r)));
    K.hidden(panel);
    const toks = {};
    const D = { el: panel, x, y, w, h, fs, cw, lh };
    D.show = (t, d = 0.6) => K.show(panel, t, d, { y: -30 }, 'expo.out');
    D.hide = (t, d = 0.4) => K.hide(panel, t, d, { y: -30 });
    D.tok = (id, row, text, nth = 0) => {
      let i = -1;
      for (let k = 0; k <= nth; k++) i = o.rows[row].indexOf(text, i + 1);
      if (i < 0) throw new Error(`decoder: "${text}" not found in row ${row}`);
      toks[id] = { row, col: i, len: text.length, text, sx: x + px + i * cw, sy: y + py + row * lh };
      return toks[id];
    };
    D.pos = (id) => { const k = toks[id]; return [k.sx + (k.len * cw) / 2, k.sy + lh / 2]; };
    D.hl = (id, t, tone = 'accent', d = 0.3) => {
      const k = toks[id], c = K.tone(tone);
      if (!k.box) {
        k.box = K.el('div', 'hlbox', panel, { left: k.sx - x - 7, top: k.sy - y + 4, width: k.len * cw + 14, height: lh - 8, background: K.tint(c, 0x2e / 255), border: `2px solid ${c}` });
      }
      tl.fromTo(k.box, { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1, duration: d, ease: 'power2.out', immediateRender: false }, t);
      return k.box;
    };
    D.unhl = (id, t, d = 0.3) => { const k = toks[id]; if (k.box) K.hide(k.box, t, d); };
    D.fly = (id, t, d, target, f = {}) => {
      const k = toks[id], c = K.tone(f.tone || 'accent');
      // lettered in a light tint of the tone (about 9:1 over any chapter light), glowing in the tone itself;
      // a theme letters it in the tone's ink, with a soft shadow on light grounds instead of a glow
      const ink = tok.themed ? K.ink(f.tone || 'accent') : gsap.utils.interpolate(c, tok.color.ink, 0.5);
      const clone = K.el('div', 'abs mono', o.flyParent || K.layer.hud, { left: k.sx, top: k.sy, height: lh, lineHeight: lh + 'px', fontSize: fs, fontWeight: 700, color: ink, whiteSpace: 'pre', textShadow: tok.fx.flyGlow(c) }, k.text);
      K.hidden(clone); K.decor(clone);
      const [cx, cy] = D.pos(id);
      tl.set(clone, { opacity: 1 }, t);
      // the copy stays full size and full strength while it travels (readable in any frame), leaves its source fast
      // (an in-out ease would sit on top of the original text for the first frames, a double image) and hands over to
      // the picture in the last 0.12 s
      tl.fromTo(clone, { x: 0, y: 0, scale: 1 }, { x: target[0] - cx, y: target[1] - cy, scale: f.scale ?? 1, duration: d, ease: f.ease || 'power2.out', immediateRender: false }, t);
      tl.to(clone, { opacity: 0, duration: 0.12 }, t + d - 0.06);
      return t + d;
    };
    D.dimTok = (id, t, op = 0.35) => {
      const k = toks[id];
      const cover = K.el('div', 'abs', panel, { left: k.sx - x - 4, top: k.sy - y + 6, width: k.len * cw + 8, height: lh - 12, background: tok.color.cover });
      if (tok.themed) cover.style.zIndex = 2; // over the text it fades back
      K.hidden(cover);
      tl.to(cover, { opacity: 1 - op, duration: 0.3 }, t);
    };
    return D;
  };
})();
