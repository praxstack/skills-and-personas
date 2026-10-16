// burst.js: comic callouts ("700!", "POP!", "TOO MANY STOPS!"): a jagged starburst with halftone dots, a black
// outline and a hard offset shadow, words in Bangers. Digits are set in Inter Black: Bangers' 7 reads as a 1, and a
// "700!" burst once read "100!". They live in screen space (the HUD) and punch in with an overshoot; pulse
// Camera.shake at the same moment for impact.
//
//   new Bursts({ slots: 2 })
// Theatre objects  Burst <i>:  in (0..1, use the 'back' ease to overshoot), text, color (gold|good|bad|accent|cool),
//                              x, y (centre, px), rot (degrees), size (1 = 120 px text)
import { C, FONT } from './tokens.js';
import { clamp, svg, setAttr, rng, SVGNS, contrast, hex, mix } from './util.js';

// star fill and its halftone dots (a darker shade of the same hue), per burst colour
const COLORS = Object.fromEntries(['gold', 'good', 'bad', 'accent', 'cool'].map((k) => [k, [C[k], C.burstDots[k]]]));

export class Bursts {
  constructor({ id = 'Burst', slots = 2 } = {}) { Object.assign(this, { id, slots }); }
  key(i) { return `${this.id} ${i}`; }
  objects() {
    const o = {};
    for (let i = 0; i < this.slots; i++) o[this.key(i)] = { in: 0, text: '', color: 'gold', x: 1420, y: 330, rot: -8, size: 1 };
    return o;
  }
  mount(stage) {
    const root = svg('svg', { class: 'bursts', width: 1920, height: 1080, viewBox: '0 0 1920 1080' }, stage.hud);
    const defs = svg('defs', {}, root);
    this.items = [];
    for (let i = 0; i < this.slots; i++) {
      const pat = svg('pattern', { id: `halftone-${i}`, width: 14, height: 14, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(30)' }, defs);
      const base = svg('rect', { width: 14, height: 14 }, pat);
      const dot = svg('circle', { cx: 7, cy: 7, r: 3.2 }, pat);
      const g = svg('g', { opacity: 0 }, root);
      const lines = svg('g', { opacity: 0.9 }, g);
      const R = rng(31 + i);
      for (let k = 0; k < 22; k++) {
        const a = (k / 22) * Math.PI * 2 + R() * 0.12, r0 = 1.05 + R() * 0.15, r1 = 1.3 + R() * 0.25;
        svg('line', { x1: Math.cos(a) * r0, y1: Math.sin(a) * r0, x2: Math.cos(a) * r1, y2: Math.sin(a) * r1, stroke: C.burstLines, 'stroke-width': 0.035, 'stroke-linecap': 'round' }, lines);
      }
      const shadow = svg('polygon', { fill: C.outline, opacity: 0.85 }, g);
      const star = svg('polygon', { stroke: C.outline, 'stroke-width': 9, 'stroke-linejoin': 'round' }, g);
      const tone = svg('polygon', { fill: `url(#halftone-${i})`, opacity: 0.35 }, g);
      const tx2 = svg('text', { 'text-anchor': 'middle', class: 'comic', fill: C.outline }, g);
      const tx = svg('text', { 'text-anchor': 'middle', class: 'comic', fill: C.burstText, stroke: C.outline, 'stroke-width': 10, 'paint-order': 'stroke', 'stroke-linejoin': 'round' }, g);
      this.items.push({ g, lines, shadow, star, tone, tx, tx2, base, dot, R: rng(57 + i), text: null });
    }
    return this;
  }
  shape(it, w, h) {
    const R = rng(97 + w | 0), n = 18, pts = [];
    for (let k = 0; k < n * 2; k++) {
      const a = (k / (n * 2)) * Math.PI * 2, out = k % 2 === 0;
      const j = out ? 1 + R() * 0.22 : 0.74 + R() * 0.06;
      pts.push(`${(Math.cos(a) * w * j).toFixed(1)},${(Math.sin(a) * h * j).toFixed(1)}`);
    }
    return pts.join(' ');
  }
  apply(V) {
    this.items.forEach((it, i) => {
      const v = V[this.key(i)], a = v.in;
      if (a <= 0.001 || !v.text) { setAttr(it.g, 'opacity', '0'); return; }
      const fs = 120 * v.size;
      if (it.text !== v.text + '|' + v.size + '|' + v.color) {
        it.text = v.text + '|' + v.size + '|' + v.color;
        const digits = (v.text.match(/[0-9]/g) || []).length;
        const w = Math.max(fs * 1.25, (v.text.length - digits) * fs * 0.36 + digits * fs * 0.6 + fs * 0.75), h = fs * 1.05;
        it.w = w; it.h = h;
        const pts = this.shape(it, w, h);
        setAttr(it.star, 'points', pts); setAttr(it.tone, 'points', pts);
        setAttr(it.shadow, 'points', pts); setAttr(it.shadow, 'transform', 'translate(14,16)');
        const [c1, c2] = COLORS[v.color] || COLORS.gold;
        setAttr(it.star, 'fill', c1); setAttr(it.base, 'fill', c1); setAttr(it.dot, 'fill', c2);
        if (C.burstInk) { // themed: the star's own on-colour; a light word keeps the dark outline, a dark one sits on the star
          const ink = C.burstInk[v.color] || C.burstInk.gold;
          const light = contrast(ink, C.outline) >= 3;
          setAttr(it.tx, 'fill', ink); setAttr(it.tx, 'stroke', light ? C.outline : c1);
          if (!light) setAttr(it.dot, 'fill', hex(mix(c1, C.lightest, 0.3))); // under a dark word the dots lighten the star, never darken it
        }
        for (const t of [it.tx, it.tx2]) { runs(t, v.text); setAttr(t, 'font-size', fs.toFixed(0)); setAttr(t, 'y', (fs * 0.36).toFixed(1)); }
        setAttr(it.tx2, 'transform', `translate(${(fs * 0.05).toFixed(1)},${(fs * 0.06).toFixed(1)})`);
        setAttr(it.lines, 'transform', `scale(${w.toFixed(1)},${h.toFixed(1)})`);
      }
      setAttr(it.g, 'opacity', clamp(a * 3).toFixed(3));
      const x = Math.min(1920 - 96 - it.w * 1.12, Math.max(96 + it.w * 1.12, v.x)), y = Math.min(880 - it.h * 1.12, Math.max(96 + it.h * 1.12, v.y));
      setAttr(it.g, 'transform', `translate(${x.toFixed(1)},${y.toFixed(1)}) rotate(${(v.rot - 18 * (1 - a)).toFixed(2)}) scale(${Math.max(0.01, a).toFixed(4)})`);
      setAttr(it.lines, 'opacity', (0.9 * clamp((1.02 - a) * 4)).toFixed(3)); // speed lines only while it punches in
    });
  }
}

/** words in Bangers (the text's class), digit runs in Inter Black so numbers read exactly */
function runs(t, text) {
  while (t.firstChild) t.removeChild(t.firstChild);
  for (const part of String(text).split(/([0-9][0-9,.]*)/)) {
    if (!part) continue;
    const sp = document.createElementNS(SVGNS, 'tspan');
    if (/^[0-9]/.test(part)) { sp.setAttribute('font-family', FONT.ui); sp.setAttribute('font-weight', '900'); sp.setAttribute('font-size', '0.9em'); }
    sp.textContent = part;
    t.appendChild(sp);
  }
}
