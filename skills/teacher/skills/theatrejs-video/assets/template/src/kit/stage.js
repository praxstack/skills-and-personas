// stage.js: the 2.5D world. A fixed 1920x1080 viewport holds depth layers (sky, far city, floor grid, subject,
// panels, foreground bokeh) and a screen-space HUD. A Theatre "Camera" object pans, dollies, orbits, tilts and
// rolls the stage: every layer moves by its depth, so near things slide faster than far ones (parallax), and an
// orbit swings the background one way and the foreground the other. Depth of field is a cross-fade between a sharp
// and a pre-blurred copy of the static background layers (a live CSS blur on a moving layer costs 3x the frame time).
//
// Theatre objects:
//   Camera  x, y (pan, px at the subject's depth), z (dolly toward the subject, px), orbit, tilt, roll (degrees),
//           dof (0..1 background blur), scrim (0..1 darkens the subject when a card sits in front),
//           drift (handheld float amplitude, 1 = subtle), shake (impact shake amplitude)
//   Sky     top, bottom, glow (rgba), glowY (0..1 height of the horizon glow), city (0..1 opacity of the sharp city)
//   Content in (0..1): the subject and panels layers and the HUD (captions, tag, bursts) fade together. R.chapter
//           takes it to 0 before the chapter card enters and back to 1 after the card has gone, so the card only
//           ever crosses the sky and the city. The card itself sits in `stage.over`, above the HUD, and never fades.
import { W, H, C, P } from './tokens.js';
import { el, rgb, css, rng, setStyle, rgba } from './util.js';

const LAYERS = [
  // name, depth (px behind the subject; negative = in front), overscan (px each side), static (pre-rendered)
  ['far', 1800, 260],
  ['floor', 520, 240],
  ['subject', 0, 0],
  ['panels', -140, 0],
  ['fore', -620, 300],
];

const DEPTH = Object.fromEntries(LAYERS.map(([name, depth]) => [name, depth]));

/** how many screen px one layer px of `layer` covers when the camera has dollied to z (the dolly part only) */
export function layerScale(layer, z = 0) {
  const d = DEPTH[layer] ?? 0;
  return (P + d) / Math.max(80, P + d - z);
}

/**
 * Where a point (x, y) of a layer lands on screen for a camera {x, y, z, orbit, tilt, roll}: the same transform
 * Stage.apply() gives the layer (pan, dolly, perspective, orbit, tilt, roll), without drift and shake.
 * R.focus() uses it to keep panels on nearer layers, tilted panels and orbiting shots inside the frame.
 */
export function projectPoint(layer, x, y, cam = {}) {
  const depth = DEPTH[layer] ?? 0;
  const { x: cx = 0, y: cy = 0, z = 0, orbit = 0, tilt = 0, roll = 0 } = cam;
  const dist = Math.max(80, P + depth - z), k = P / dist, S = (P + depth) / dist;
  const th = (orbit * Math.PI) / 180, ph = (tilt * Math.PI) / 180, rr = (roll * Math.PI) / 180;
  const tx = (-cx - depth * Math.sin(th)) * k, ty = (-cy + depth * Math.sin(ph)) * k;
  // CSS applies the transform list right to left: scale, rotateZ(roll), rotateY(orbit), rotateX(-tilt), perspective
  let X = (x - W / 2) * S, Y = (y - H / 2) * S, Z = 0;
  [X, Y] = [X * Math.cos(rr) - Y * Math.sin(rr), X * Math.sin(rr) + Y * Math.cos(rr)];
  [X, Z] = [X * Math.cos(th) + Z * Math.sin(th), -X * Math.sin(th) + Z * Math.cos(th)];
  [Y, Z] = [Y * Math.cos(-ph) - Z * Math.sin(-ph), Y * Math.sin(-ph) + Z * Math.cos(-ph)];
  const w = 1 - Z / dist;
  return [W / 2 + X / w + tx, H / 2 + Y / w + ty];
}

export class Stage {
  // grain: 'still' (default: a fixed texture that also dithers gradient banding), 'moving' (a new offset every
  // frame: filmic, but full-frame noise that changes every frame multiplies the H.264 bitrate about 6x and slows
  // the encode), or 'off'
  constructor({ backdrop = 'skyline', floor = true, seed = 7, sky = {}, grain = 'still' } = {}) {
    this.opts = { backdrop, floor, seed, grain };
    this.sky = { top: rgba(C.skyTop), bottom: rgba(C.skyBottom), glow: rgba(C.accent, 0.55), glowY: 0.6, city: 1, ...sky };
  }

  objects() {
    return {
      Camera: { x: 0, y: 0, z: 0, orbit: 0, tilt: 0, roll: 0, dof: 0.6, scrim: 0, drift: 1, shake: 0 },
      Sky: { ...this.sky },
      Content: { in: 1 },
    };
  }

  layer(name) { return this.L[name].inner; }

  mount(root) {
    this.vp = el('div', { id: 'viewport' }, root);
    this.skyEl = el('div', { class: 'sky' }, this.vp);
    this.L = {};
    for (const [name, depth, over] of LAYERS) {
      const outer = el('div', { class: `layer layer-${name}` }, this.vp);
      Object.assign(outer.style, { left: -over + 'px', top: -over + 'px', width: W + 2 * over + 'px', height: H + 2 * over + 'px',
        transformOrigin: `${W / 2 + over}px ${H / 2 + over}px` });
      const inner = el('div', { class: 'layer-inner' }, outer);
      Object.assign(inner.style, { left: over + 'px', top: over + 'px' });
      this.L[name] = { outer, inner, depth, over };
      if (name === 'subject') this.scrimEl = el('div', { class: 'scrim' }, this.vp);
    }
    this.hud = el('div', { class: 'hud' }, this.vp);
    this.over = el('div', { class: 'hud hud-over' }, this.vp); // the chapter card: above everything Content fades
    this.vignette = el('div', { class: 'vignette' }, this.vp);
    this.grain = el('div', { class: 'grain' }, this.vp);
    if (this.opts.grain !== 'off') this.grain.style.backgroundImage = `url(${noiseTile(256, this.opts.seed)})`;
    if (this.opts.backdrop !== 'none') this.paintFar();
    if (this.opts.floor) this.paintFloor();
    this.paintFore();
    return this;
  }

  // ----------------------------------------------------------------- static layers, painted once
  // Speed matters more than anything here (software compositing, no GPU): canvases cover only the band where
  // something is drawn, bokeh are small separate elements (Chrome skips empty tiles), and at rest only one of the
  // sharp/blurred copies is drawn (both only while Camera.dof is between 0.02 and 0.98).
  paintFar() {
    const { outer, over } = this.L.far;
    const w = W + 2 * over, R = rng(this.opts.seed);
    const horizon = over + H * 0.62, top = horizon - 300, h = 560; // the city band
    // distant glow orbs: small elements, not a full-layer canvas
    for (let i = 0; i < 8; i++) {
      const x = R() * w, y = over + R() * H * 0.5, r = 70 + R() * 150;
      const col = [C.accent, C.cool, C.violet, C.gold][i % 4];
      el('div', { class: 'orb', style: { left: x - r + 'px', top: y - r + 'px', width: 2 * r + 'px', height: 2 * r + 'px',
        background: `radial-gradient(circle, ${css(col, 0.2 * C.orbK)} 0%, ${css(col, 0.08 * C.orbK)} 45%, ${css(col, 0)} 70%)` } }, outer);
    }
    const sharp = canvas(w, h), g = sharp.getContext('2d');
    if (this.opts.backdrop === 'skyline') {
      const base0 = horizon - top;
      for (const [row, base, hmin, hmax, shade] of [[0, base0 - 6, 70, 230, C.city[0]], [1, base0 + 34, 40, 150, C.city[1]]]) {
        let x = -20;
        while (x < w) {
          const bw = 70 + R() * 120, bh = hmin + R() * (hmax - hmin);
          g.fillStyle = shade; g.fillRect(x, base - bh, bw, h);
          if (R() < 0.25) g.fillRect(x + bw * 0.4, base - bh - 40, 6, 40); // antenna
          for (let wy = base - bh + 14; wy < base - 8; wy += 22) for (let wx = x + 10; wx < x + bw - 12; wx += 18) {
            if (R() < 0.2) { g.fillStyle = css(R() < 0.7 ? C.gold : R() < 0.5 ? C.accent : C.cool, (0.22 + R() * 0.45) * (row ? 0.75 : 1)); g.fillRect(wx, wy, 9, 12); }
          }
          x += bw + 6 + R() * 20;
        }
      }
      // fade the band's bottom into the floor
      const fade = g.createLinearGradient(0, base0 + 40, 0, h);
      fade.addColorStop(0, css(C.cityFade, 0)); fade.addColorStop(1, css(C.cityFade, 1));
      g.fillStyle = fade; g.fillRect(0, base0 + 40, w, h);
    }
    const blurred = canvas(w, h), bg = blurred.getContext('2d');
    bg.filter = 'blur(6px)'; bg.drawImage(sharp, 0, 0);
    for (const c of [sharp, blurred]) Object.assign(c.style, { left: '0px', top: top + 'px' });
    this.farSharp = sharp; this.farBlur = blurred;
    outer.appendChild(sharp); outer.appendChild(blurred);
  }

  paintFloor() {
    const { outer, over } = this.L.floor;
    const w = W + 2 * over, hy = over + H * 0.66, h = H + 2 * over - hy;
    const cv = canvas(w, h), g = cv.getContext('2d'), vx = w / 2;
    const fill = g.createLinearGradient(0, 0, 0, h);
    fill.addColorStop(0, css(C.floorTop, 0)); fill.addColorStop(0.2, css(C.floorTop, 0.6)); fill.addColorStop(1, css(C.floorBottom, 0.97));
    g.fillStyle = fill; g.fillRect(0, 0, w, h);
    g.filter = 'blur(1.2px)';
    for (let i = -24; i <= 24; i++) { // lines toward the vanishing point
      const gr = g.createLinearGradient(0, 0, 0, h);
      gr.addColorStop(0, css(C.violet, 0)); gr.addColorStop(0.45, css(C.violet, 0.2)); gr.addColorStop(1, css(C.cool, 0.3));
      g.strokeStyle = gr; g.lineWidth = 2;
      g.beginPath(); g.moveTo(vx + i * 6, 0); g.lineTo(vx + i * 190, h); g.stroke();
    }
    for (let k = 1; k < 18; k++) { // cross lines, closer together toward the horizon
      const y = h * Math.pow(k / 18, 2.2);
      g.strokeStyle = css(C.violet, 0.05 + 0.28 * (k / 18)); g.lineWidth = 1 + 2 * (k / 18);
      g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
    }
    g.filter = 'none';
    const hg = g.createLinearGradient(0, 0, w, 0);
    hg.addColorStop(0, css(C.accent, 0)); hg.addColorStop(0.5, css(C.accent, 0.8)); hg.addColorStop(1, css(C.accent, 0));
    g.fillStyle = hg; g.fillRect(0, 0, w, 3);
    Object.assign(cv.style, { left: '0px', top: hy + 'px' });
    outer.appendChild(cv);
  }

  paintFore() {
    const { outer, over } = this.L.fore;
    const w = W + 2 * over, h = H + 2 * over, R = rng(this.opts.seed + 11);
    for (let i = 0; i < 14; i++) {
      // bokeh live near the edges; the middle of the frame stays clear
      let x = R() * w; const y = R() * h;
      if (Math.abs(x - w / 2) < W * 0.3 && Math.abs(y - h / 2) < H * 0.3) x = x < w / 2 ? x - W * 0.3 : x + W * 0.3;
      const r = 26 + R() * 70, col = [C.accent, C.cool, C.gold, C.violet][i % 4];
      el('div', { class: 'orb', style: { left: x - r + 'px', top: y - r + 'px', width: 2 * r + 'px', height: 2 * r + 'px',
        background: `radial-gradient(circle, ${css(col, 0.15 * C.foreK)} 0%, ${css(col, 0.11 * C.foreK)} 62%, ${css(col, 0)} 72%)` } }, outer);
    }
  }

  // ----------------------------------------------------------------- per frame
  apply(V, t) {
    const c = V.Camera, s = V.Sky;
    // handheld drift and impact shake: deterministic functions of t (no state between frames)
    const tau = Math.PI * 2;
    const dx = c.drift * (7 * Math.sin(tau * 0.05 * t) + 4 * Math.sin(tau * 0.13 * t + 1.3));
    const dy = c.drift * (5 * Math.sin(tau * 0.07 * t + 0.4) + 2 * Math.sin(tau * 0.17 * t + 2.1));
    const dr = c.drift * 0.18 * Math.sin(tau * 0.045 * t + 0.7);
    const n = (k) => Math.sin(t * 61.7 * k + k * 12.9) * Math.sin(t * 23.3 + k * 4.1);
    const sx = c.shake * 16 * n(1), sy = c.shake * 12 * n(2);
    const x = c.x + dx + sx, y = c.y + dy + sy, z = c.z, roll = c.roll + dr + c.shake * 0.8 * n(3);
    const th = (c.orbit * Math.PI) / 180, ph = (c.tilt * Math.PI) / 180;
    for (const name in this.L) {
      const { outer, depth } = this.L[name];
      const dist = Math.max(80, P + depth - z);
      const k = P / dist, S = (P + depth) / dist;
      const tx = (-x - depth * Math.sin(th)) * k, ty = (-y + depth * Math.sin(ph)) * k;
      setStyle(outer, 'transform',
        `translate(${tx.toFixed(2)}px,${ty.toFixed(2)}px) perspective(${dist.toFixed(0)}px) rotateX(${(-c.tilt).toFixed(3)}deg) rotateY(${c.orbit.toFixed(3)}deg) rotateZ(${roll.toFixed(3)}deg) scale(${S.toFixed(4)})`);
    }
    const dof = Math.min(1, Math.max(0, c.dof));
    if (this.farBlur) {
      // at rest draw one copy; cross-fade only while the focus is being pulled
      setStyle(this.farSharp, 'display', dof >= 0.98 ? 'none' : 'block');
      setStyle(this.farBlur, 'display', dof <= 0.02 ? 'none' : 'block');
      setStyle(this.farBlur, 'opacity', dof.toFixed(3));
      setStyle(this.farSharp, 'opacity', String(Math.max(0, Math.min(1, s.city))));
    }
    // Content fade (chapter changes): '' at full opacity, so the layers composite as usual between cards
    const a = Math.min(1, Math.max(0, V.Content.in)), op = a >= 0.999 ? '' : a.toFixed(3);
    for (const e of [this.L.subject.outer, this.L.panels.outer, this.hud]) setStyle(e, 'opacity', op);
    setStyle(this.scrimEl, 'opacity', Math.max(0, Math.min(1, c.scrim)).toFixed(3));
    setStyle(this.skyEl, 'background',
      `radial-gradient(120% 70% at 50% ${(s.glowY * 100).toFixed(1)}%, ${css(s.glow)} 0%, ${css(s.glow, 0)} 62%), linear-gradient(180deg, ${css(s.top)} 0%, ${css(s.bottom)} 100%)`);
    if (this.opts.grain === 'moving') { // a new deterministic offset every frame (see the constructor note)
      const f = Math.round(t * 30);
      setStyle(this.grain, 'backgroundPosition', `${(f * 73) % 256}px ${(f * 151) % 256}px`);
    }
  }
}

function canvas(w, h) { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function noiseTile(n, seed) {
  const c = canvas(n, n), g = c.getContext('2d'), img = g.createImageData(n, n), R = rng(seed + 99);
  for (let i = 0; i < n * n; i++) { const v = R() * 255; img.data.set([v, v, v, 255 * (0.35 + 0.65 * R())], i * 4); }
  g.putImageData(img, 0, 0);
  return c.toDataURL('image/png');
}
export { rgb };
