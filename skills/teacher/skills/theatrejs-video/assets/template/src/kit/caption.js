// caption.js: the caption band (bottom 180 px, screen space). Shows the `cap` of the line being spoken, wraps to
// two lines, highlights numbers, O(...) and arrows, and carries a chapter progress strip. It reads TIMING directly
// (captions belong to lines, not to shots); the Theatre object only hides or shows the band.
//
// Theatre object:  Caption  in (0..1; hide during the title card or a full-frame moment)
import { clamp, el, markup, setStyle } from './util.js';

export class Caption {
  constructor({ T, id = 'Caption' }) { Object.assign(this, { T, id }); }
  objects() { return { [this.id]: { in: 1 } }; }

  mount(stage) {
    this.band = el('div', { class: 'caption' }, stage.hud);
    this.text = el('div', { class: 'caption-text' }, this.band);
    this.prog = el('div', { class: 'caption-chapters' }, this.band);
    const { chapters, total } = this.T;
    this.segs = chapters.map((c) => {
      const s = el('div', { class: 'cap-seg' }, this.prog);
      s.style.flex = String(Math.max(0.5, c.end - c.start));
      return { c, fill: el('div', { class: 'cap-seg-fill' }, s), seg: s };
    });
    this.total = total;
    return this;
  }

  apply(V, t) {
    const vis = clamp(V[this.id].in);
    setStyle(this.band, 'opacity', vis.toFixed(3));
    const ln = this.T.lineAt(t);
    if (ln && this.cur !== ln.id) { this.cur = ln.id; this.text.innerHTML = `<span>${markup(ln.cap)}</span>`; }
    if (!ln) { this.cur = null; this.text.innerHTML = ''; }
    // each new line rises in over 0.3 s (the old one is replaced at the slot boundary, inside the breath pause); it
    // is at full opacity from its first frame, so no frame shows a half-faded caption (the band's own fade is Caption.in)
    const a = ln ? clamp((t - ln.start) / 0.3) : 0;
    setStyle(this.text, 'opacity', ln ? '1' : '0');
    setStyle(this.text, 'transform', `translateY(${(10 * (1 - a)).toFixed(1)}px)`);
    for (const { c, fill, seg } of this.segs) {
      const u = clamp((t - c.start) / Math.max(0.01, c.end - c.start));
      setStyle(fill, 'transform', `scaleX(${u.toFixed(4)})`);
      setStyle(seg, 'opacity', t >= c.start - 0.01 && t < c.end + 0.8 ? '1' : '0.45');
    }
  }
}
