// camera.js: an orbit rig driven by tweens. A shot is { target: [x, y, z], dist, az, el, fov }:
// az = degrees around the board (0 = from the front), el = degrees above the board, dist = distance to target,
// frame = where the target lands on screen ([0.5, 0.5] = centre, [0.3, 0.5] = left third). Moving `frame` shifts the
// lens instead of turning the camera, so "graph on the left, panel on the right" keeps the same straight-on view.
// Tweening between shots interpolates target, distance and angles separately, so a change of az orbits around
// the subject and a change of dist dollies in; `drift` adds a slow deterministic float so holds never freeze.
//
//   const cam = new CameraRig(stage, SHOT.wide)
//   cam.shot(tl, at('p2'), SHOT.closeOn0, 1.4)            ease 'inOut' by default; dur 0 = a hard cut
//   cam.shake(tl, at('p4', 1), 0.5)                         a short impact shake
//   cam.fit(g.bounds(), [80, 140, 1000, 860], { az: -10, el: 46 })
//        returns a shot that frames those points inside that box of the 1920x1080 frame (left, top, right, bottom),
//        solving target, dist and frame for you. Use it whenever a panel shares the screen with the graph.
import { clamp } from './time.js';

export class CameraRig {
  constructor(stage, shot) {
    this.stage = stage;
    this.p = { target: [0, 0, 0], dist: 30, az: 0, el: 40, fov: 32, frame: [0.5, 0.5], drift: 1, shake: 0, ...shot };
    this.p.target = [...this.p.target];
    this.p.frame = [...this.p.frame];
    this.view = '';
  }
  shot(tl, time, s, d = 1.4, ease = 'inOut') {
    const props = {};
    for (const k of ['target', 'dist', 'az', 'el', 'fov', 'frame', 'drift']) if (k in s) props[k] = Array.isArray(s[k]) ? [...s[k]] : s[k];
    if (!('frame' in s)) props.frame = [0.5, 0.5];   // a shot without `frame` is centred
    if (d <= 0) tl.set(this.p, props, time); else tl.to(this.p, props, time, d, ease);
    return this;
  }
  fit(points, box, o = {}) {
    const THREE = this.stage.THREE, cam = this.stage.camera.clone(), v = new THREE.Vector3();
    const c = new THREE.Box3().setFromPoints(points).getCenter(new THREE.Vector3());
    const shot = { az: 0, el: 40, fov: this.p.fov, ...o, target: [c.x, c.y, c.z] };
    const rig = new CameraRig({ camera: cam }, { ...shot, drift: 0 });
    const [l, t, r, b] = box, bw = r - l, bh = b - t;
    let dist = 40, frame = [(l + r) / 3840, (t + b) / 2160];
    for (let i = 0; i < 16; i++) {
      rig.p.dist = dist; rig.p.frame = frame; rig.apply(0);
      let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
      for (const p of points) {
        v.copy(p).project(cam);
        const x = (v.x + 1) * 960, y = (1 - v.y) * 540;
        x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y);
      }
      dist *= Math.max((x1 - x0) / bw, (y1 - y0) / bh);
      frame = [frame[0] + ((l + r) - (x0 + x1)) / 3840, frame[1] + ((t + b) - (y0 + y1)) / 2160];
    }
    return { ...shot, dist: +dist.toFixed(2), frame: frame.map((f) => +f.toFixed(4)) };
  }
  shake(tl, time, d = 0.5, amount = 1) { tl.set(this.p, { shake: 0 }, time - 1e-3); tl.to(this.p, { shake: amount }, time, 0.05, 'linear'); tl.to(this.p, { shake: 0 }, time + 0.05, d, 'out'); return this; }
  apply(t) {
    const p = this.p, cam = this.stage.camera;
    const dr = p.drift;
    const az = (p.az + dr * 2.2 * Math.sin(t * 0.19) + dr * 0.8 * Math.sin(t * 0.43 + 1.3)) * Math.PI / 180;
    const el = clamp(p.el + dr * 1.2 * Math.sin(t * 0.23 + 0.7), -5, 89) * Math.PI / 180;
    const dist = p.dist * (1 + dr * 0.012 * Math.sin(t * 0.17 + 2.1));
    const [tx, ty, tz] = p.target;
    const sh = p.shake * 0.18;
    cam.position.set(tx + dist * Math.cos(el) * Math.sin(az) + sh * Math.sin(t * 61), ty + dist * Math.sin(el) + sh * Math.sin(t * 53 + 1), tz + dist * Math.cos(el) * Math.cos(az));
    cam.lookAt(tx + sh * 0.5 * Math.sin(t * 47), ty, tz);
    const [fx, fy] = p.frame, key = `${p.fov}|${fx.toFixed(5)}|${fy.toFixed(5)}`;
    if (key !== this.view) {
      this.view = key;
      cam.fov = p.fov;
      if (Math.abs(fx - 0.5) < 1e-5 && Math.abs(fy - 0.5) < 1e-5) cam.clearViewOffset();
      else cam.setViewOffset(1920, 1080, (0.5 - fx) * 1920, (0.5 - fy) * 1080, 1920, 1080);
      cam.updateProjectionMatrix();
    }
    cam.updateMatrixWorld();
  }
}
