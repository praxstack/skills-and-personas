// cards.js: title card, chapter swipe and chapter tag (the "01 · THE PROBLEM" lower third).
//
//   new TitleCard({ title, subtitle, badge })      Theatre: Title    in (0..1 flips in), out (0..1 flies out)
//   new ChapterCard({ T })                         Theatre: Chapter  n (chapter number, hold), u (0 off right,
//                                                  0.5 centred, 1 off left): a diagonal band that covers the cut.
//                                                  It sits in stage.over, above the HUD; R.chapter fades all content
//                                                  out (Content.in) before it enters, so it never covers anything
//   new ChapterTag({ T })                          Theatre: ChapterTag n (hold), in (0..1 slides in at top left)
import { clamp, el, setStyle, setText } from './util.js';

const pad2 = (n) => String(n).padStart(2, '0');
const clock = (s) => `${Math.floor(s / 60)}:${pad2(Math.floor(s % 60))}`;

export class TitleCard {
  constructor({ id = 'Title', title, subtitle = '', badge = '', layer = 'panels' }) { Object.assign(this, { id, title, subtitle, badge, layerName: layer }); }
  objects() { return { [this.id]: { in: 0, out: 0 } }; }
  mount(stage) {
    this.root = el('div', { class: 'title-card' }, stage.layer(this.layerName));
    this.inner = el('div', { class: 'title-inner' }, this.root);
    if (this.badge) this.badgeEl = el('div', { class: 'title-badge', text: this.badge }, this.inner);
    this.h = el('div', { class: 'title-h', text: this.title }, this.inner);
    if (this.subtitle) el('div', { class: 'title-sub', text: this.subtitle }, this.inner);
    this.rule = el('div', { class: 'title-rule' }, this.inner);
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in), b = clamp(v.out);
    setStyle(this.root, 'opacity', (a <= 0.001 || b >= 0.999 ? 0 : clamp(a * 2) * (1 - b)).toFixed(3));
    if (a <= 0.001 || b >= 0.999) return;
    setStyle(this.inner, 'transform', `perspective(1200px) translateY(${(60 * (1 - v.in)).toFixed(1)}px) rotateX(${(70 * (1 - v.in)).toFixed(2)}deg) translateZ(${(260 * b).toFixed(1)}px)`);
    if (this.badgeEl) setStyle(this.badgeEl, 'transform', `rotate(-4deg) scale(${clamp((v.in - 0.4) / 0.6, 0, 1.2).toFixed(3)})`);
    setStyle(this.rule, 'transform', `scaleX(${clamp((v.in - 0.3) / 0.7).toFixed(3)})`);
  }
}

export class ChapterCard {
  constructor({ T, id = 'Chapter' }) { Object.assign(this, { T, id }); }
  objects() { return { [this.id]: { n: 1, u: 0 } }; }
  mount(stage) {
    this.root = el('div', { class: 'chapter-swipe' }, stage.over || stage.hud);
    this.band = el('div', { class: 'chapter-band' }, this.root);
    this.stripe = el('div', { class: 'chapter-stripe' }, this.root);
    // Bangers' 7 reads as a 1: if any chapter number has a 7, set all chapter numerals in Inter Black
    this.num = el('div', { class: 'chapter-num' + (hasSeven(this.T) ? ' num-safe' : '') }, this.band);
    const col = el('div', { class: 'chapter-col' }, this.band);
    this.kicker = el('div', { class: 'chapter-kicker' }, col);
    this.name = el('div', { class: 'chapter-name' }, col);
    return this;
  }
  apply(V) {
    const v = V[this.id], u = v.u;
    const on = u > 0.001 && u < 0.999;
    setStyle(this.root, 'display', on ? 'block' : 'none');
    if (!on) return;
    const n = Math.round(v.n), c = this.T.chapters.find((x) => x.n === n) || this.T.chapters[0];
    setText(this.num, pad2(n));
    setText(this.kicker, `CHAPTER ${pad2(n)} · ${clock(c.start)}`);
    setText(this.name, c.name.toUpperCase());
    // band and stripe travel at slightly different speeds (a cheap 2.5D parallax on the swipe itself)
    const x = (0.5 - u) * 2 * 2400;
    setStyle(this.band, 'transform', `translateX(${x.toFixed(1)}px) skewX(-12deg)`);
    setStyle(this.stripe, 'transform', `translateX(${(x * 1.25).toFixed(1)}px) skewX(-12deg)`);
  }
}

export class ChapterTag {
  constructor({ T, id = 'ChapterTag' }) { Object.assign(this, { T, id }); }
  objects() { return { [this.id]: { n: 1, in: 0 } }; }
  mount(stage) {
    this.root = el('div', { class: 'chapter-tag' }, stage.hud);
    this.num = el('span', { class: 'ct-num' + (hasSeven(this.T) ? ' num-safe' : '') }, this.root);
    this.name = el('span', { class: 'ct-name' }, this.root);
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', a.toFixed(3));
    if (a <= 0.001) return;
    const n = Math.round(v.n), c = this.T.chapters.find((x) => x.n === n) || this.T.chapters[0];
    setText(this.num, pad2(n));
    setText(this.name, c.name.toUpperCase());
    setStyle(this.root, 'transform', `translateX(${(-40 * (1 - a)).toFixed(1)}px) rotate(-2deg)`);
  }
}

function hasSeven(T) { return T.chapters.some((c) => /7/.test(pad2(c.n))); }
