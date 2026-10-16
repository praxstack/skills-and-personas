/* kit/code.js: a code panel: JetBrains Mono with ligatures off (so != <= ++ stay as typed), syntax colours from the
   palette, line numbers, chunked reveal and an active-line highlight that follows the narration.

   const P = KIT.code({x: 96, y: 170, code: CPP, title: 'solution.cpp', fs: 30, lh: 1.2, wrap: 58})
     fs: code size (quality bar: 30 to 36 px); wrap: soft-wrap lines longer than this many columns (display only)
   P.show(t)                         the window slides in (empty)
   P.reveal(t, 1, 5, 0.06)           lines 1..5 (1-based, inclusive) type in, staggered
   P.focus(t, 9) / P.focus(t, [9, 10])   the highlight bar moves there; the other lines step back to
                                         tok.dimOpacity (0.8: visibly quieter, still above 4.5:1)
   P.unfocus(t) / P.out(t)
   P.lineY(n) -> screen y of a line's centre (to draw arrows from code to the subject)
   The code on screen must be exactly the code that was compiled in the brief. */
(function () {
  'use strict';
  const K = window.KIT, tl = K.tl, tok = K.tok;
  const KW = new Set(['for', 'while', 'if', 'else', 'return', 'const', 'auto', 'break', 'continue', 'new', 'delete', 'class', 'struct', 'public', 'private', 'static', 'def', 'in', 'not', 'and', 'or', 'import', 'from', 'using', 'namespace', 'template', 'typename', 'true', 'false', 'nullptr', 'None', 'True', 'False', 'let', 'var', 'function', 'switch', 'case', 'do', 'lambda', 'yield']);
  const TY = new Set(['int', 'long', 'bool', 'void', 'char', 'double', 'float', 'string', 'vector', 'pair', 'map', 'set', 'unordered_map', 'unordered_set', 'queue', 'priority_queue', 'deque', 'array', 'size_t', 'list', 'dict', 'tuple', 'List', 'Map']);
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

  K.highlight = function (line) {
    const out = [];
    const re = /(\/\/.*$|#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?(?:e\d+)?\b)|([A-Za-z_][A-Za-z0-9_]*)(\s*\()?|(\s+)|(.)/g;
    let m;
    while ((m = re.exec(line))) {
      const [, cm, st, nu, id, call, sp, op] = m;
      if (cm) out.push(`<span class="tk-cm">${esc(cm)}</span>`);
      else if (st) out.push(`<span class="tk-st">${esc(st)}</span>`);
      else if (nu) out.push(`<span class="tk-nu">${nu}</span>`);
      else if (id) {
        const cls = KW.has(id) ? 'tk-kw' : TY.has(id) ? 'tk-ty' : call ? 'tk-fn' : '';
        out.push(cls ? `<span class="${cls}">${id}</span>` : id);
        if (call) out.push(esc(call));
      } else if (sp) out.push(sp);
      else out.push(`<span class="tk-op">${esc(op)}</span>`);
    }
    return out.join('');
  };

  K.code = function (o) {
    const fs = o.fs || tok.size.code, lh = Math.round(fs * (o.lh || 1.2)), cw = fs * tok.mono;
    const src = o.code.replace(/\s+$/, '').split('\n');
    const nw = String(src.length).length, gutter = Math.round((nw + 1.6) * cw), padR = Math.round(cw * 0.8);
    // Soft wrap (display only, like an editor's word wrap: the text and the line numbers stay exactly the source).
    // A line longer than `wrap` columns breaks before its trailing // comment (or at the last space that fits); the
    // continuation row has no line number and is indented 4 columns past the line's own indentation.
    const parts = src.map((s) => {
      if (!o.wrap || s.length <= o.wrap) return [s];
      const ind = s.match(/^\s*/)[0].length;
      let cut = s.indexOf('//') > 0 && s.indexOf('//') <= o.wrap ? s.indexOf('//') : s.lastIndexOf(' ', o.wrap);
      if (cut <= ind) cut = o.wrap;
      return [s.slice(0, cut).replace(/\s+$/, ''), ' '.repeat(ind + 4) + s.slice(cut).replace(/^\s+/, '')];
    });
    const rowsOf = parts.map((p) => p.length), start = rowsOf.map((_, i) => rowsOf.slice(0, i).reduce((a, b) => a + b, 0));
    const nRows = start[src.length - 1] + rowsOf[src.length - 1];
    const maxLen = Math.max(...parts.flat().map((s) => s.length));
    const top = 56 + 12, w = o.w || Math.round(gutter + maxLen * cw + 40), h = o.h || top + nRows * lh + 16;
    const x = o.x ?? 96, y = o.y ?? 170;
    const panel = K.el('div', 'panel code', o.parent || K.layer.hud, { left: x, top: y, width: w, height: h });
    K.el('div', 'bar', panel);
    tok.color.dots.forEach((c, i) => K.el('div', 'dot', panel, { left: 28 + i * 24, background: c }));
    K.el('div', 'fname mono', panel, null, o.title || 'solution.cpp');
    const cursor = K.el('div', 'cursor', panel, { width: w - 20, height: lh, top, background: K.tint(K.tone(o.tone || 'accent'), 0x2a / 255), borderLeft: `4px solid ${K.tone(o.tone || 'accent')}` });
    const no = (n) => `<span class="no" style="width:${gutter}px;padding-right:${padR}px">${n}</span>`;
    const rows = parts.map((p, i) => K.el('div', 'ln mono', panel, { top: top + start[i] * lh, height: p.length * lh, lineHeight: lh + 'px', fontSize: fs },
      p.map((s, k) => `${no(k ? '' : i + 1)}<span class="tx">${K.highlight(s)}</span>`).join('\n')));
    const texts = rows.map((r) => [...r.querySelectorAll('.tx')]);
    K.hidden([panel, ...rows]);
    const P = { el: panel, rows, x, y, w, h, lh, top };
    let focused = null;
    const dimOp = o.dim ?? tok.dimOpacity;
    P.show = (t, d = 0.6) => K.show(panel, t, d, { x: -60 }, 'expo.out');
    P.out = (t, d = 0.45) => K.hide(panel, t, d, { x: -80 });
    P.reveal = (t, a = 1, b = src.length, stagger = 0.06) => {
      const els = rows.slice(a - 1, b);
      tl.fromTo(els, { opacity: 0, x: -18 }, { opacity: 1, x: 0, duration: 0.35, stagger, ease: 'power2.out', immediateRender: false }, t);
      return t + 0.35 + stagger * (els.length - 1);
    };
    /** Move the highlight bar to source lines a..b; the other lines step back to tok.dimOpacity (still 4.5:1). */
    P.focus = (t, n, d = 0.35) => {
      const [a, b] = Array.isArray(n) ? n : [n, n];
      const ry = start[a - 1] * lh, rh = (start[b - 1] + rowsOf[b - 1] - start[a - 1]) * lh;
      const vars = { y: ry, height: rh, duration: d, ease: 'power3.inOut' };
      if (!focused) { tl.set(cursor, { y: ry, height: rh }, t); tl.to(cursor, { opacity: 1, duration: d }, t); }
      else tl.to(cursor, vars, t);
      texts.forEach((tx, i) => tl.to(tx, { opacity: i + 1 >= a && i + 1 <= b ? 1 : dimOp, duration: d }, t));
      focused = [a, b];
    };
    P.unfocus = (t, d = 0.35) => { tl.to(cursor, { opacity: 0, duration: d }, t); tl.to(texts.flat(), { opacity: 1, duration: d }, t); focused = null; };
    P.lineY = (n) => y + top + (start[n - 1] + 0.5) * lh;
    return P;
  };
})();
