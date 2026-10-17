// decoder.js: the raw input as text (`flights = [[0,1,100], ...]`), whose entries fly into place on the graph.
// It lives in the same layer as the graph so a flying entry travels in one coordinate space.
//
//   new Decoder({ graph, x: 96, y: 150, rows: [
//       { text: 'n = 4' },
//       { text: '  [0, 1, 100],', chip: '100', to: { edge: '0-1' } },   // the weight lifts off the row and lands on
//                                                                        // that edge as its weight chip
//       { text: 'src = 0', to: { node: 0 } } ] })                        // flies to a node
// A chip lifts off from where its text is written in the row (when the row contains it), flies at full opacity
// above the graph and is gone the frame it lands: time the target's own text (the edge's weight appears when its
// arrow finishes drawing, a node tag) to appear as it lands, so the hand-off never shows two half-faded texts.
// Theatre objects:  Decoder         in, rows (how many rows are typed in; fractional fades the next one),
//                                   hl (row highlight, glides between rows; -1 hides it), dim, x, y
//                   Decoder / fly <i>  u (0..1 flight of row i's chip to its target; landed at 1)
import { C } from './tokens.js';
import { clamp, lerp, el, setStyle } from './util.js';

const LH = 48, FS = 32, CW = FS * 0.6, PAD = 30, HEAD = 70;
const TILT = 6; // a gentle turn: a steeper one slants each row enough to make the text read smaller

export class Decoder {
  constructor({ id = 'Decoder', graph, x = 96, y = 150, title = 'INPUT', rows, layer = 'subject' }) {
    Object.assign(this, { id, graph, x, y, title, rows, layerName: layer });
    this.w = Math.max(...rows.map((r) => r.text.length)) * CW + 2 * PAD + 10;
    this.h = HEAD + rows.length * LH + PAD;
  }
  rect() { return Object.assign([this.x, this.y, this.x + this.w, this.y + this.h], { layer: this.layerName, tilt: TILT, persp: 1400 }); }
  flyKey(i) { return `${this.id} / fly ${i}`; }
  objects() {
    const o = { [this.id]: { in: 0, rows: 0, hl: -1, dim: 0, x: 0, y: 0 } };
    this.rows.forEach((r, i) => { if (r.to) o[this.flyKey(i)] = { u: 0 }; });
    return o;
  }
  /** where row i's text sits (layer coordinates) */
  rowPos(i, V) {
    const v = V[this.id], r = this.rows[i], chip = this.chipText(r), at = r.text.indexOf(chip);
    const lead = r.text.length - r.text.trimStart().length;
    const cx = at >= 0 ? PAD + (at + chip.length / 2) * CW : PAD + lead * CW; // the chip's own text in the row
    return [this.x + v.x + cx, this.y + v.y + HEAD + i * LH + LH / 2];
  }
  chipText(r) { return r.chip || r.text.trim().replace(/,$/, ''); }
  mount(stage) {
    const L = stage.layer(this.layerName);
    this.root = el('div', { class: 'panel decoder', style: { left: this.x + 'px', top: this.y + 'px', width: this.w + 'px', height: this.h + 'px' } }, L);
    el('div', { class: 'panel-kick', text: this.title }, this.root);
    this.bar = el('div', { class: 'dec-bar', style: { height: LH + 'px', top: HEAD + 'px' } }, this.root);
    this.rowEls = this.rows.map((r, i) => el('div', { class: 'dec-row mono', text: r.text, style: { top: HEAD + i * LH + 'px', left: PAD + 'px', fontSize: FS + 'px', lineHeight: LH + 'px' } }, this.root));
    this.flyEls = this.rows.map((r) => r.to ? el('div', { class: 'dec-fly mono', text: this.chipText(r) }, L) : null);
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', (a * (1 - 0.3 * clamp(v.dim))).toFixed(3)); // dimmed rows stay above 4.5:1
    setStyle(this.root, 'transform', `translate(${(v.x - 40 * (1 - a)).toFixed(1)}px,${v.y.toFixed(1)}px) perspective(1400px) rotateY(${(TILT + 14 * (1 - a)).toFixed(2)}deg)`);
    this.rowEls.forEach((e, i) => {
      const u = clamp(v.rows - i);
      setStyle(e, 'opacity', u.toFixed(3));
      setStyle(e, 'transform', `translateX(${(14 * (1 - u)).toFixed(1)}px)`);
      const landed = this.rows[i].to && V[this.flyKey(i)].u >= 0.999;
      setStyle(e, 'color', landed ? C.goodInk : '');
    });
    setStyle(this.bar, 'opacity', v.hl < -0.5 ? '0' : clamp(v.hl + 1).toFixed(3));
    setStyle(this.bar, 'transform', `translateY(${(Math.max(0, v.hl) * LH).toFixed(1)}px)`);
    this.rows.forEach((r, i) => {
      const f = this.flyEls[i]; if (!f) return;
      const u = V[this.flyKey(i)].u;
      if (u <= 0.001 || u >= 0.999 || a <= 0.001) { setStyle(f, 'opacity', '0'); return; }
      const [x0, y0] = this.rowPos(i, V);
      const [x1, y1] = this.target(r.to, V);
      const h = Math.min(260, Math.hypot(x1 - x0, y1 - y0) * 0.35);
      // sideways first (x eases out), so the chip leaves the panel instead of sliding up over the rows above it
      const x = lerp(x0, x1, 1 - (1 - u) * (1 - u)), y = lerp(y0, y1, u) - h * 4 * u * (1 - u);
      // full opacity for the whole flight (a fading chip is unreadable): it pops off the row and lands
      setStyle(f, 'opacity', '1');
      setStyle(f, 'transform', `translate(${x.toFixed(1)}px,${y.toFixed(1)}px) translate(-50%,-50%) scale(${(1 + 0.3 * Math.sin(Math.PI * u)).toFixed(3)}) rotate(${(-6 * Math.sin(Math.PI * u)).toFixed(2)}deg)`);
    });
  }
  target(to, V) {
    const G = V[this.graph.id], g = this.graph;
    let p;
    if (to.edge) { const [a, b] = to.edge.split('-'); p = g.edge(a, b).chip; } else if (to.node !== undefined) { const n = g.N.get(String(to.node)); p = [n.x, n.y]; } else p = to.xy;
    return [(p[0] - g.cx) * G.s + g.cx + G.x, (p[1] - g.cy) * G.s + g.cy + G.y];
  }
}
