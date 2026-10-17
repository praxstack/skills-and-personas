// code.js: the code panel. Monospace with ligatures off (JetBrains Mono NL plus font-feature-settings), syntax
// colours from the palette, lines revealed in chunks, and an active-line bar that glides from line to line.
//
//   new CodePanel({ code, file: 'solution.cpp', x: 1000, y: 120, fontSize: 30 })
// Theatre object  Code:  in, reveal (lines shown; 3.5 = three lines and half of the fourth), line (active line,
//                        0-based; glides when tweened; -1 hides the bar), x, y, dim, tilt (rotateY, degrees)
// Code is 30 to 36 px on screen (quality-bar.md): 30 px with 1.3 line height fits 17 lines of up to ~52 characters
// beside the graph; reflow long signatures (the code on screen must still be the code you compiled). `dim` keeps
// every token at 4.5:1 or better; focus a line with `line` (the bar), never by fading the others out.
import { C } from './tokens.js';
import { clamp, el, setStyle } from './util.js';

const KW = new Set('auto break case class const constexpr continue default delete do else enum explicit for if inline namespace new nullptr operator private protected public return sizeof static struct switch template this throw try typedef typename using virtual while true false'.split(' '));
const TY = new Set('int long short char bool double float void unsigned size_t vector map unordered_map set unordered_set pair queue priority_queue deque stack string array tuple greater less'.split(' '));

/** tiny C++/JS/Python-ish highlighter: returns HTML for one line */
export function highlight(line) {
  const esc = (x) => x.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const re = /(\/\/.*$|#.*$)|("(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(\b\d+(?:\.\d+)?(?:e\d+)?\b)|([A-Za-z_]\w*)(\s*\()?|([{}()[\];,.])|([-+*/%=<>!&|^~?:]+)/g;
  let out = '', i = 0, m;
  while ((m = re.exec(line))) {
    out += esc(line.slice(i, m.index));
    if (m[1]) out += `<span class="tk-c">${esc(m[1])}</span>`;
    else if (m[2]) out += `<span class="tk-s">${esc(m[2])}</span>`;
    else if (m[3]) out += `<span class="tk-n">${m[3]}</span>`;
    else if (m[4]) {
      const w = m[4];
      const cls = KW.has(w) ? 'tk-k' : TY.has(w) ? 'tk-t' : m[5] ? 'tk-f' : /^[A-Z][A-Z0-9_]+$/.test(w) ? 'tk-n' : 'tk-i';
      out += `<span class="${cls}">${w}</span>` + (m[5] ? esc(m[5]) : '');
    } else if (m[6]) out += `<span class="tk-p">${esc(m[6])}</span>`;
    else out += `<span class="tk-o">${esc(m[7])}</span>`;
    i = m.index + m[0].length;
  }
  return out + esc(line.slice(i));
}

export class CodePanel {
  constructor({ id = 'Code', code, file = 'solution.cpp', x = 990, y = 110, fontSize = 30, lineHeight = 1.3, layer = 'panels' }) {
    const lines = code.replace(/\s+$/, '').split('\n');
    Object.assign(this, { id, lines, file, x, y, fs: fontSize, lh: Math.round(fontSize * lineHeight), layerName: layer });
    this.w = Math.max(...lines.map((l) => l.length)) * fontSize * 0.6 + 78 + 24 + 40; // gutter + padding
  }
  rect() { return Object.assign([this.x, this.y, this.x + this.w, this.y + 62 + 16 + this.lines.length * this.lh + 22], { layer: this.layerName, tilt: -5, persp: 1600 }); }
  objects() { return { [this.id]: { in: 0, reveal: 0, line: -1, x: 0, y: 0, dim: 0, tilt: -5 } }; }
  /** line index (0-based) of the first line containing `text`; use it in shots so edits to the code stay in sync */
  find(text) { const i = this.lines.findIndex((l) => l.includes(text)); if (i < 0) throw new Error(`code: no line contains "${text}"`); return i; }
  mount(stage) {
    this.root = el('div', { class: 'panel code', style: { left: this.x + 'px', top: this.y + 'px', width: this.w + 'px' } }, stage.layer(this.layerName));
    const head = el('div', { class: 'code-head' }, this.root);
    for (const c of C.traffic) el('i', { style: { background: c } }, head);
    el('span', { class: 'code-file', text: this.file }, head);
    this.body = el('div', { class: 'code-body', style: { fontSize: this.fs + 'px', lineHeight: this.lh + 'px' } }, this.root);
    this.bar = el('div', { class: 'code-bar', style: { height: this.lh + 'px' } }, this.body);
    this.rows = this.lines.map((l, i) => {
      const r = el('div', { class: 'code-line', style: { height: this.lh + 'px' } }, this.body);
      el('span', { class: 'code-ln', text: String(i + 1) }, r);
      el('span', { class: 'code-src', html: highlight(l) || '&nbsp;' }, r);
      return r;
    });
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', (a * (1 - 0.2 * clamp(v.dim))).toFixed(3)); // dimmed syntax colours stay above 4.5:1
    if (a <= 0.001) return;
    setStyle(this.root, 'transform', `translate(${(v.x + 80 * (1 - a)).toFixed(1)}px,${v.y.toFixed(1)}px) perspective(1600px) rotateY(${(v.tilt - 18 * (1 - a)).toFixed(2)}deg)`);
    this.rows.forEach((r, i) => {
      const u = clamp(v.reveal - i);
      // no ghost of the lines still to come, and each line is fully opaque a third of the way into its reveal (it
      // keeps sliding in): faint half-revealed code is unreadable text on screen (qa.py moving-text)
      setStyle(r, 'opacity', clamp(3 * u).toFixed(3));
      setStyle(r, 'transform', `translateX(${(18 * (1 - u)).toFixed(1)}px)`);
      const act = v.line >= 0 && Math.abs(v.line - i) < 0.5;
      if (r.__act !== act) { r.__act = act; r.classList.toggle('active', act); }
    });
    setStyle(this.bar, 'opacity', v.line < -0.5 ? '0' : clamp(v.line + 1).toFixed(3));
    setStyle(this.bar, 'transform', `translateY(${(Math.max(0, v.line) * this.lh).toFixed(1)}px)`);
  }
}
