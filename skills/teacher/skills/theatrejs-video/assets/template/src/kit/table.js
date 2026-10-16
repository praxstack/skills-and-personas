// table.js: rows of cells for DP state and dry runs (dist / next rows, a memo table, an array). Each row holds a list
// of snapshots; the Theatre `step` picks the snapshot, and cells that changed since the previous step flash.
//
//   new Table({ x: 200, y: 760, cols: ['0', '1', '2', '3'], rows: [
//       { label: 'dist', steps: [[0, '∞', '∞', '∞'], [0, 100, '∞', '∞'], [0, 100, 200, 700]] } ] })
// Theatre object  Table:  in, step (snapshot index; set it with s.set so it holds), flash (0..1 highlight of the
//                         cells that just changed; pulse it on every step), col (column highlight, glides; -1 off),
//                         x, y
import { C } from './tokens.js';
import { clamp, el, setStyle, setText, mix, css } from './util.js';

export class Table {
  constructor({ id = 'Table', x, y, cols, rows, title = '', cell = 96, layer = 'subject' }) {
    Object.assign(this, { id, x, y, cols, rows, title, cell, layerName: layer });
    this.labelW = Math.max(...rows.map((r) => r.label.length)) * 34 * 0.6 + 40; // .tbl-label is 34 px mono
  }
  rect() { return Object.assign([this.x, this.y, this.x + this.labelW + this.cols.length * this.cell + 52, this.y + (this.title ? 70 : 22) + 48 + this.rows.length * 84 + 22], { layer: this.layerName }); }
  objects() { return { [this.id]: { in: 0, step: 0, flash: 0, col: -1, x: 0, y: 0 } }; }
  mount(stage) {
    const c = this.cell;
    this.root = el('div', { class: 'panel table', style: { left: this.x + 'px', top: this.y + 'px' } }, stage.layer(this.layerName));
    if (this.title) el('div', { class: 'panel-kick', text: this.title }, this.root);
    const grid = el('div', { class: 'tbl-grid' }, this.root);
    this.colBar = el('div', { class: 'tbl-colbar', style: { width: c + 'px', left: this.labelW + 'px' } }, grid);
    const head = el('div', { class: 'tbl-row' }, grid);
    el('div', { class: 'tbl-label', style: { width: this.labelW + 'px' } }, head);
    for (const h of this.cols) el('div', { class: 'tbl-head mono', text: h, style: { width: c + 'px' } }, head);
    this.cells = this.rows.map((r) => {
      const row = el('div', { class: 'tbl-row' }, grid);
      el('div', { class: 'tbl-label mono', text: r.label, style: { width: this.labelW + 'px' } }, row);
      return this.cols.map(() => el('div', { class: 'tbl-cell mono', style: { width: c - 10 + 'px', height: c - 26 + 'px' } }, row));
    });
    return this;
  }
  apply(V) {
    const v = V[this.id], a = clamp(v.in);
    setStyle(this.root, 'opacity', a.toFixed(3));
    if (a <= 0.001) return;
    setStyle(this.root, 'transform', `translate(${v.x.toFixed(1)}px,${(v.y + 30 * (1 - a)).toFixed(1)}px)`);
    const step = Math.max(0, Math.floor(v.step + 1e-6)), f = clamp(v.flash);
    this.rows.forEach((r, ri) => {
      const cur = r.steps[Math.min(step, r.steps.length - 1)] || [];
      const prev = step > 0 ? r.steps[Math.min(step - 1, r.steps.length - 1)] || [] : cur;
      this.cells[ri].forEach((e, ci) => {
        const val = cur[ci] ?? '';
        setText(e, val);
        const changed = String(prev[ci]) !== String(val);
        const k = changed ? f : 0;
        // a changed cell flashes with a mint tint, border, glow and text; the tint stays dark enough that the
        // text keeps 4.5:1 at every moment of the flash (a bright fill with a text colour switch dips to 3.7:1)
        setStyle(e, 'transform', `scale(${(1 + 0.16 * k).toFixed(4)})`);
        setStyle(e, 'background', k > 0.001 ? css(C.good, +(0.08 + 0.22 * k * C.flashK).toFixed(3)) : '');
        setStyle(e, 'borderColor', k > 0.001 ? css(mix(C.cellEdge, C.good, Math.min(1, k * 2))) : '');
        setStyle(e, 'boxShadow', k > 0.001 ? `0 0 ${(26 * k).toFixed(1)}px ${css(C.good, +(0.45 * k * C.glowK * C.flashK).toFixed(3))}` : '');
        setStyle(e, 'color', String(val) === '∞' ? C.inkDim : css(mix(C.ink, C.flashInk, k)));
      });
    });
    setStyle(this.colBar, 'opacity', v.col < -0.5 ? '0' : clamp(v.col + 1).toFixed(3));
    setStyle(this.colBar, 'transform', `translateX(${(Math.max(0, v.col) * this.cell).toFixed(1)}px)`);
  }
}
