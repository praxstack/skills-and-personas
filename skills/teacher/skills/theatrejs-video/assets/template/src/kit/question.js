// question.js: the question card with a countdown ring for the think pause, which flips over (a CSS 3D flip) to
// show the answer. Its text comes from TIMING: set `q` to the question line id and `a` to the answer line id.
//
//   new QuestionCard({ T, x: 960, y: 120, w: 1200 })
// Theatre object  Question:  in, q (line id, hold), a (line id, hold), n (question number), timer (0..1 of the
//                            think pause elapsed), flip (0 question .. 1 answer)
import { C } from './tokens.js';
import { clamp, el, markup, setStyle, setText, svg, setAttr, css } from './util.js';

const strip = (s) => s.replace(/^\s*question\s*\d*\s*[:.]\s*/i, '');

export class QuestionCard {
  constructor({ T, id = 'Question', x = 960, y = 112, w = 1180, layer = 'panels' }) { Object.assign(this, { T, id, x, y, w, layerName: layer }); }
  rect() { return Object.assign([this.x - this.w / 2, this.y - 30, this.x + this.w / 2, this.y + 190], { layer: this.layerName }); }
  objects() { return { [this.id]: { in: 0, q: '', a: '', n: 1, timer: 0, flip: 0 } }; }
  mount(stage) {
    this.root = el('div', { class: 'qcard', style: { left: this.x - this.w / 2 + 'px', top: this.y + 'px', width: this.w + 'px' } }, stage.layer(this.layerName));
    this.front = el('div', { class: 'qface qfront' }, this.root);
    this.kick = el('div', { class: 'qkick' }, this.front);
    this.qtext = el('div', { class: 'qtext' }, this.front);
    const ring = svg('svg', { class: 'qring', width: 112, height: 112, viewBox: '-56 -56 112 112' }, this.front);
    svg('circle', { r: 44, fill: css(C.shade, 0.25), stroke: css(C.glass, 0.12), 'stroke-width': 8 }, ring);
    this.arc = svg('circle', { r: 44, fill: 'none', stroke: C.gold, 'stroke-width': 8, 'stroke-linecap': 'round', transform: 'rotate(-90)', 'stroke-dasharray': `${(2 * Math.PI * 44).toFixed(2)} 999` }, ring);
    this.secs = svg('text', { y: 14, 'text-anchor': 'middle', class: 'mono', 'font-size': 40, 'font-weight': 800, fill: C.ink }, ring);
    this.back = el('div', { class: 'qface qback' }, this.root);
    this.akick = el('div', { class: 'qkick', text: 'ANSWER' }, this.back);
    this.atext = el('div', { class: 'qtext' }, this.back);
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', a.toFixed(3));
    if (a <= 0.001) return;
    setStyle(this.root, 'transform', `translateY(${(-30 * (1 - a)).toFixed(1)}px) scale(${(0.94 + 0.06 * a).toFixed(4)})`);
    if (v.q && this.qid !== v.q) { this.qid = v.q; this.qtext.innerHTML = markup(strip(this.T.line(v.q).cap)); }
    if (v.a && this.aid !== v.a) { this.aid = v.a; this.atext.innerHTML = markup(this.T.line(v.a).cap); }
    setText(this.kick, `QUESTION ${Math.round(v.n)}`);
    const think = v.q ? this.T.line(v.q).think || 2 : 2, left = clamp(1 - v.timer);
    setAttr(this.arc, 'stroke-dashoffset', (2 * Math.PI * 44 * (1 - left)).toFixed(2));
    setAttr(this.arc, 'stroke', left < 0.34 ? C.accent : C.gold);
    setText(this.secs, v.timer <= 0.001 ? '?' : String(Math.ceil(think * left - 1e-6)));
    // the flip: 0..90 deg shows the question face, 90..180 the answer face (no backface-visibility needed)
    const ang = 180 * clamp(v.flip);
    const showBack = ang > 90;
    setStyle(this.front, 'display', showBack ? 'none' : 'flex');
    setStyle(this.back, 'display', showBack ? 'flex' : 'none');
    const face = showBack ? this.back : this.front, rot = showBack ? ang - 180 : ang;
    setStyle(face, 'transform', `perspective(1400px) rotateX(${rot.toFixed(2)}deg)`);
  }
}
