// ladder.js: the complexity ladder. One rung per approach with its time and space, a bar whose length shows the
// cost, and the interview pick stamped.
//
//   new Ladder({ x: 980, y: 140, rungs: [{ name: 'Brute-force DFS', time: 'O(n^(k+1))', space: 'O(k)', cost: 1 }, ...], pick: 2 })
// Theatre object  Ladder:  in, shown (rungs revealed; fractional fades the next), hl (row highlight, glides;
//                          -1 off), pick (0..1 stamps the pick rung), x, y
import { C } from './tokens.js';
import { clamp, el, markup, mix, css, setStyle } from './util.js';

export class Ladder {
  constructor({ id = 'Ladder', x = 980, y = 140, w = 960, title = 'COMPLEXITY', rungs, pick = rungs.length - 1, layer = 'panels' }) {
    Object.assign(this, { id, x, y, w, title, rungs, pick, layerName: layer });
  }
  // (+46: the INTERVIEW PICK stamp hangs over the panel's bottom edge, under the picked rung, never over its text)
  rect() { return Object.assign([this.x, this.y, this.x + this.w, this.y + 76 + 44 + this.rungs.length * 92 + 26 + 46], { layer: this.layerName, tilt: -6, persp: 1600 }); }
  objects() { return { [this.id]: { in: 0, shown: 0, hl: -1, pick: 0, x: 0, y: 0 } }; }
  mount(stage) {
    this.root = el('div', { class: 'panel ladder', style: { left: this.x + 'px', top: this.y + 'px', width: this.w + 'px' } }, stage.layer(this.layerName));
    el('div', { class: 'panel-kick', text: this.title }, this.root);
    const head = el('div', { class: 'lad-row lad-head' }, this.root);
    el('div', { class: 'lad-name', text: 'approach' }, head); el('div', { class: 'lad-o', text: 'time' }, head); el('div', { class: 'lad-o', text: 'space' }, head);
    this.box = el('div', { class: 'lad-box' }, this.root);
    this.bar = el('div', { class: 'lad-hl' }, this.box);
    this.rows = this.rungs.map((r) => {
      const row = el('div', { class: 'lad-row' }, this.box);
      const name = el('div', { class: 'lad-name' }, row);
      el('div', { text: r.name }, name);
      const track = el('div', { class: 'lad-track' }, name);
      const fill = el('div', { class: 'lad-fill' }, track);
      fill.style.background = `linear-gradient(90deg, ${css(mix(C.good, C.bad, r.cost * 0.6))}, ${css(mix(C.good, C.bad, r.cost))})`;
      el('div', { class: 'lad-o mono', html: markup(r.time) }, row);
      el('div', { class: 'lad-o mono', html: markup(r.space) }, row);
      return { row, fill, r };
    });
    this.stamp = el('div', { class: 'lad-stamp', text: 'INTERVIEW PICK' }, this.box);
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', a.toFixed(3));
    if (a <= 0.001) return;
    setStyle(this.root, 'transform', `translate(${(v.x + 60 * (1 - a)).toFixed(1)}px,${v.y.toFixed(1)}px) perspective(1600px) rotateY(${(-6 - 14 * (1 - a)).toFixed(2)}deg)`);
    const RH = 92;
    this.rows.forEach(({ row, fill, r }, i) => {
      const u = clamp(v.shown - i);
      setStyle(row, 'opacity', u.toFixed(3));
      setStyle(row, 'transform', `translateY(${(16 * (1 - u)).toFixed(1)}px)`);
      setStyle(fill, 'transform', `scaleX(${(Math.max(0.04, r.cost) * clamp((v.shown - i) * 1.4 - 0.2)).toFixed(4)})`);
      const picked = i === this.pick && v.pick > 0.5;
      if (row.__p !== picked) { row.__p = picked; row.classList.toggle('picked', picked); }
    });
    setStyle(this.bar, 'opacity', v.hl < -0.5 ? '0' : clamp(v.hl + 1).toFixed(3));
    setStyle(this.bar, 'transform', `translateY(${(Math.max(0, v.hl) * RH).toFixed(1)}px)`);
    const p = v.pick;
    setStyle(this.stamp, 'opacity', clamp(p * 3).toFixed(3));
    // under the last rung it hangs over the panel's bottom edge, clear of the rung's text; a middle pick stamps the rung
    const last = this.pick === this.rungs.length - 1;
    setStyle(this.stamp, 'top', `${last ? (this.pick + 1) * RH + 24 : this.pick * RH + 46}px`);
    setStyle(this.stamp, 'left', last ? '70%' : '62%');
    setStyle(this.stamp, 'transform', `translate(-50%,-50%) rotate(${(-9 + 14 * (1 - clamp(p))).toFixed(2)}deg) scale(${(2.2 - 1.2 * p).toFixed(3)})`);
  }
}
