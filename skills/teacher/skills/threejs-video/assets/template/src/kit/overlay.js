// overlay.js: the DOM layer above the WebGL canvas. All text lives here (captions, code, numbers, labels), so it
// is crisp at any resolution, uses real fonts with ligatures off, and wraps like CSS. capture.mjs grabs page
// screenshots (no CAPTURE_SELECTOR), which composite the canvas and this layer in the same frame.
//
//   const ui = createOverlay(stage)     ui.root (a 1920x1080 stage scaled to the viewport), ui.project(v3)
//   ui.anchor({ world, offset, cls })   an element pinned to a 3D point (labels, badges, bursts)
//   el(tag, cls, parent, html)          tiny DOM helper;  fmt('O(n^(k+1))') -> HTML with a real superscript
import * as THREE from 'three';
import { SIZE, inkOf, onOf, plateOf } from './style.js';

export function el(tag, cls, parent, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html != null) e.innerHTML = html;
  if (parent) parent.appendChild(e);
  return e;
}
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
// escape, then: x^(k+1) or x^k -> superscript, **bold** -> <b> (styled with the element's --tone)
export function fmt(s) {
  return esc(s).replace(/\^\(([^)]*)\)/g, '<sup>$1</sup>').replace(/\^([A-Za-z0-9+]+)/g, '<sup>$1</sup>')
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>');
}
// set only when changed (DOM writes are the expensive part of a frame)
export function setText(e, s, html = false) {
  const v = String(s);
  if (e._v === v) return;
  e._v = v; if (html) e.innerHTML = v; else e.textContent = v;
}
export function setStyle(e, k, v) { if (e['_s' + k] !== v) { e['_s' + k] = v; e.style[k] = v; } }
export function show(e, a, transform) {
  const o = a <= 0.001 ? 0 : Math.min(1, a);
  setStyle(e, 'opacity', o.toFixed(3));
  setStyle(e, 'visibility', o > 0 ? 'visible' : 'hidden');
  if (transform !== undefined) setStyle(e, 'transform', transform);
  return o > 0;
}

export function createOverlay(stage, css) {
  const style = el('style', null, document.head); style.textContent = css;
  const root = el('div', 'ui', document.getElementById('film'));
  root.id = 'ui';
  const scale = stage.W / SIZE.W;
  root.style.transform = `scale(${scale})`;
  const layers = { world: el('div', 'layer', root), hud: el('div', 'layer', root), top: el('div', 'layer', root) };
  const v = new THREE.Vector3();
  const items = [];
  const ui = {
    root, layers, scale, items,
    /** 3D point -> stage pixels {x, y, z (0..1 depth), ok (in front of the camera)} */
    project(p) {
      v.copy(p).project(stage.camera);
      return { x: (v.x + 1) / 2 * SIZE.W, y: (1 - v.y) / 2 * SIZE.H, z: v.z, ok: v.z < 1 };
    },
    /** register anything with apply(t); called every frame after the timeline seek */
    add(item) { items.push(item); return item; },
    anchor(o) { return ui.add(new Anchor(ui, o)); },
    apply(t) { for (const it of items) it.apply(t); },
  };
  return ui;
}

// An element pinned to a 3D point (world: Vector3 or () => Vector3) or to a stage pixel (pos: [x, y]).
// Props (tween them): on 0..1 (fade + grow; outBack overshoot welcome), scale, dx, dy, tone '#hex',
// text (escaped; **bold** and x^(k+1) supported via fmt). With format: (n) => 'cost **' + n + '**', tween n instead
// of text (a counter that ticks up).
export class Anchor {
  constructor(ui, { world = null, pos = null, offset = [0, 0], cls = 'chip', text = '', tone = '', layer = 'world', pivot = [-50, -100], format = null, n = 0 }) {
    this.ui = ui; this.world = world; this.screen = pos; this.e = el('div', 'anchor ' + cls, ui.layers[layer]);
    this.pivot = pivot; this.format = format;
    this.on = 0; this.scale = 1; this.dx = offset[0]; this.dy = offset[1]; this.text = text; this.tone = tone; this.n = n;
  }
  get p() { return this; } // props live on the object itself; .p is an alias so every kit object reads the same
  pos() { return typeof this.world === 'function' ? this.world() : this.world; }
  apply() {
    if (this.on <= 0.001) { show(this.e, 0); return; }
    const p = this.screen ? { x: this.screen[0], y: this.screen[1], ok: true } : this.ui.project(this.pos());
    if (!p.ok) { show(this.e, 0); return; }
    setText(this.e, fmt(this.format ? this.format(this.n) : this.text), true);
    if (this.tone !== this._tone) {
      this._tone = this.tone; const st = this.e.style;
      st.setProperty('--tone', this.tone || ''); st.setProperty('--tone-ink', inkOf(this.tone || '')); st.setProperty('--tone-on', this.tone ? onOf(this.tone) : ''); st.setProperty('--tone-plate', plateOf(this.tone || ''));
      this.e.classList.toggle('toned', !!this.tone);
    }
    const s = this.scale * (0.6 + 0.4 * this.on);
    show(this.e, this.on, `translate(${(p.x + this.dx).toFixed(1)}px, ${(p.y + this.dy).toFixed(1)}px) translate(${this.pivot[0]}%, ${this.pivot[1]}%) scale(${s.toFixed(3)})`);
  }
}
