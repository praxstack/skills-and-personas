// token.js: the mascot, a little orange toy block with eyes that hops along routes on the graph.
// It looks at the viewer when standing and faces its direction of travel while flying.
//
//   const tok = new Token(stage, graph)            (ghost: true makes a translucent explorer copy)
//   props: route [ids] (set it), u 0..route.length-1 (tween it: one unit per flight), on 0..1, jump (tween 0->1 =
//          one happy hop), hop (arc height while flying), shake 0..1 (a "no" wobble), x/y/z (extra offset)
import * as THREE from 'three';
import { C, FX } from './style.js';
import { rbox, std } from './stage.js';
import { clamp } from './time.js';

export class Token {
  constructor(stage, graph, { color = C.token, ghost = false, size = 1 } = {}) {
    this.stage = stage; this.graph = graph; this.ghost = ghost;
    const g = new THREE.Group(); stage.scene.add(g); this.g = g;
    const body = new THREE.Group(); g.add(body); this.body = body;
    const mat = ghost
      ? new THREE.MeshBasicMaterial({ color: new THREE.Color(color).multiplyScalar(FX.ghost), transparent: true, opacity: FX.ghostOpacity, depthWrite: false })
      : std(color, { roughness: 0.4 });
    const eyeM = ghost ? new THREE.MeshBasicMaterial({ color: C.eye, transparent: true, opacity: 0.6 }) : std(C.eye, { roughness: 0.3 });
    const torso = new THREE.Mesh(rbox(1.15, 0.92, 0.98, 0.24), mat); torso.position.y = 0.62; body.add(torso);
    this.eyes = [-0.24, 0.24].map((x) => { const e = new THREE.Mesh(rbox(0.14, 0.3, 0.06, 0.05, 2), eyeM); e.position.set(x, 0.7, 0.5); body.add(e); return e; });
    this.feet = [-0.3, 0.3].map((x) => { const f = new THREE.Mesh(rbox(0.26, 0.2, 0.34, 0.08, 2), mat); f.position.set(x, 0.1, 0.05); body.add(f); return f; });
    const nub = new THREE.Mesh(rbox(0.22, 0.22, 0.3, 0.08, 2), mat); nub.position.set(0.66, 0.6, -0.05); body.add(nub);
    const nub2 = nub.clone(); nub2.position.x = -0.66; body.add(nub2);
    if (!ghost) body.traverse((o) => { if (o.isMesh) o.castShadow = true; });
    g.scale.setScalar(size);
    this.p = { route: [0], u: 0, on: 1, jump: 0, hop: 1, shake: 0, x: 0, y: 0, z: 0 };
    this.seed = ghost ? 1.7 : 0;
  }
  /** world position the token stands at right now (for labels and bursts) */
  where() { return this.g.position.clone().add(new THREE.Vector3(0, 1.3, 0)); }
  apply(t) {
    const p = this.p, on = clamp(p.on);
    this.g.visible = on > 0.01;
    if (!this.g.visible) return;
    const legs = p.route.length - 1;
    const r = this.graph.routePoint(p.route, Math.min(p.u, Math.max(0, legs)));
    const flying = legs > 0 && r.s > 0.001 && r.s < 0.999;
    const pos = legs > 0 && r.s >= 0.999 ? this.graph.top(p.route[r.leg + 1]) : legs > 0 && r.s <= 0.001 ? this.graph.top(p.route[r.leg]) : r.pos;
    const hop = flying ? Math.sin(Math.PI * r.s) * 0.5 * p.hop : 0;
    const jump = Math.sin(Math.PI * clamp(p.jump)) * 1.5;
    this.g.position.set(pos.x + p.x, pos.y + p.y + hop + jump, pos.z + p.z);
    // facing: travel direction while flying, the camera while standing
    const cam = this.stage.camera.position;
    const toCam = Math.atan2(cam.x - this.g.position.x, cam.z - this.g.position.z);
    const dirYaw = Math.atan2(r.dir.x, r.dir.z);
    const w = flying ? clamp(Math.sin(Math.PI * r.s) * 3) : 0;
    let d = dirYaw - toCam; d = Math.atan2(Math.sin(d), Math.cos(d));
    this.g.rotation.y = toCam + d * w + Math.sin(t * 9) * 0.35 * clamp(p.shake);
    // squash and stretch: stretch mid-flight, squash on take-off/landing and at the bottom of a jump
    const land = legs > 0 ? Math.max(0, 1 - Math.min(r.s, 1 - r.s) * 12) * (flying ? 1 : 0) : 0;
    const j = clamp(p.jump), jl = j > 0 && j < 1 ? Math.max(0, 1 - Math.min(j, 1 - j) * 8) : 0;
    const breathe = Math.sin(t * 2.6 + this.seed) * 0.025;
    const sq = 1 - 0.2 * Math.max(land, jl) + (flying ? 0.08 * Math.sin(Math.PI * r.s) : 0) + breathe;
    this.body.scale.set((1 / Math.sqrt(sq)) * on, sq * on, (1 / Math.sqrt(sq)) * on);
    // blink every few seconds (deterministic)
    const ph = (t + this.seed * 3) % 3.7, blink = ph < 0.12 ? 0.15 : 1;
    for (const e of this.eyes) e.scale.y = blink;
  }
}
