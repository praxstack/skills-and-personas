// graph3d.js: the persistent subject, a directed weighted graph built as toys on the board.
// Nodes are numbered toy blocks (pillars) on round pads with a glow ring; edges are arcs from block top to block
// top with an arrowhead, a weight tag and a travelling "fire" bead. Layout comes from data.
//
//   const g = new Graph(stage, ui, { nodes: [{ id: 0, pos: [-7, 1] }, ...], edges: [[0, 1, 100], [1, 2, 100, { labelAt: 0.6, bend: 0.5 }], ...] })
//   (pos is [x, z] on the board, about -12..12 by -7..7; leave pos out for a circle layout)
//   g.n(0)        node props:  rise 0..1 (grow out of the board), glow 0..1+, tone '#hex', dim 0..1, lift,
//                              value '' + valueOn 0..1 + valueTone (badge above), tag '' + tagOn (flag below)
//   g.e(0, 1)     edge props:  draw 0..1, glow, tone, dim 0..1, fire 0..1 (bead position; outside (0,1) hidden),
//                              labelOn 0..1, label (defaults to the weight), labelTone, labelPop (pulse it on a change)
//   g.top(i)      a node's top (Vector3), g.mid(a, b) an edge's apex, g.routePoint([0, 1, 3], u) for travel
//   g.bounds(ids, { flags })  points that outline the graph (islands, raised pillars + badges, arcs + weight tags,
//                 and the flags of the node ids in flags): feed to cam.fit()
//   Tween the props with the Timeline (tl.to(g.e(0, 1), { draw: 1 }, at('p1'), 0.6)); g.apply(t) runs each frame.
import * as THREE from 'three';
import { C, GLOW, FONT, FX, faceInkOf } from './style.js';
import { rbox, std, matte } from './stage.js';
import { clamp, E, mixHex } from './time.js';

const v3 = (x, y, z) => new THREE.Vector3(x, y, z);

function faceTexture(label, color, h) {
  const c = document.createElement('canvas'); c.width = 256; c.height = Math.round(256 * h); const x = c.getContext('2d');
  x.fillStyle = color; x.fillRect(0, 0, c.width, c.height);
  x.fillStyle = faceInkOf(color); x.font = `400 ${label.length > 2 ? 110 : 150}px ${FONT.comic}`; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(label, 128, c.height * 0.36);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t;
}

export class Graph {
  constructor(stage, ui, { nodes, edges, pillar = 2.6, width = 1.6, arc = 1.0 }) {
    this.stage = stage; this.ui = ui; this.nodes = []; this.edges = []; this.map = new Map();
    const R = Math.max(5, nodes.length * 1.6);
    nodes.forEach((d, i) => {
      const pos = d.pos || [Math.cos((i / nodes.length) * Math.PI * 2) * R, Math.sin((i / nodes.length) * Math.PI * 2) * R * 0.6];
      this.nodes.push(this._node(d, i, pos, d.h || pillar, width));
    });
    for (const e of edges) {
      const [a, b, w, o = {}] = Array.isArray(e) ? e : [e.from, e.to, e.w, e];
      this.edges.push(this._edge(a, b, w, o.bend || 0, arc, o.labelAt ?? 0.5));
    }
  }
  n(id) { const n = this.nodes.find((x) => x.id === id); if (!n) throw new Error(`no node ${id}`); return n.p; }
  e(a, b) { const e = this.map.get(`${a}>${b}`); if (!e) throw new Error(`no edge ${a} -> ${b}`); return e.p; }
  edgesOf(list) { return list.map(([a, b]) => this.e(a, b)); }
  top(id) { const n = this.nodes.find((x) => x.id === id); return v3(n.x, n.base + n.h * Math.max(0, n.p.rise) + n.p.lift + 0.02, n.z); }
  mid(a, b) { return this.map.get(`${a}>${b}`).curve.getPoint(0.5); }
  curve(a, b) { return this.map.get(`${a}>${b}`).curve; }
  bounds(ids, { flags = [] } = {}) {
    const pts = [];
    for (const n of this.nodes) {
      if (ids && !ids.includes(n.id)) continue;
      for (let k = 0; k < 8; k++) pts.push(v3(n.x + 2.75 * Math.cos(k * Math.PI / 4), 0.1, n.z + 2.75 * Math.sin(k * Math.PI / 4)));
      pts.push(v3(n.x, n.base + n.h + 1.6, n.z));   // pillar + value badge
      if (flags.includes(n.id)) pts.push(v3(n.x, -1.9, n.z + 1.7));   // the flag (tag) that hangs below the island
    }
    for (const e of this.edges) {
      if (ids && !(ids.includes(e.a) && ids.includes(e.b))) continue;
      pts.push(e.curve.getPoint(0.5).add(v3(0, 0.4, 0)));
      pts.push(e.curve.getPoint(e.labelAt).add(v3(0, 1.4, 0)));   // the weight tag stands above its point
    }
    return pts;
  }

  /** position + heading along a route of node ids; u runs 0..route.length-1 (one unit per flight) */
  routePoint(route, u) {
    const legs = route.length - 1;
    if (legs < 1) return { pos: this.top(route[0]), dir: v3(1, 0, 0), s: 0, leg: 0 };
    const i = Math.min(legs - 1, Math.floor(clamp(u, 0, legs - 1e-6))), s = clamp(u - i);
    const c = this.curve(route[i], route[i + 1]);
    return { pos: c.getPoint(s), dir: c.getTangent(Math.min(0.999, Math.max(0.001, s))), s, leg: i };
  }

  _node(d, i, [x, z], h, w) {
    const col = d.color || C.node[i % C.node.length];
    const g = new THREE.Group(); g.position.set(x, 0, z); this.stage.scene.add(g);
    // a little sand island with a few trees: the city's lot on the map
    const isl = new THREE.Mesh(new THREE.CylinderGeometry(2.55, 2.75, 0.22, 40), matte(C.island));
    isl.position.y = 0.11; isl.receiveShadow = true; g.add(isl);
    const treeM = matte(C.tree, { flatShading: true }), trunkM = matte(C.trunk);
    [[2.05, 2.4], [1.95, 2.95], [2.1, 3.6]].forEach(([r, a], k) => {
      const ang = a + i * 0.9, tr = new THREE.Group(); tr.position.set(Math.cos(ang) * r, 0.22, Math.sin(ang) * r);
      const s = 0.55 + 0.18 * ((i + k) % 3); tr.scale.setScalar(s);
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.12, 0.5, 6), trunkM); trunk.position.y = 0.25; tr.add(trunk);
      const top = new THREE.Mesh(new THREE.ConeGeometry(0.5, 1.2, 7), treeM); top.position.y = 1.0; tr.add(top);
      tr.traverse((o) => { if (o.isMesh) o.castShadow = true; }); g.add(tr);
    });
    const pad = new THREE.Mesh(new THREE.CylinderGeometry(1.5, 1.62, 0.28, 40), matte(mixHex(col, C.pad, 0.55)));
    pad.position.y = 0.36; pad.castShadow = pad.receiveShadow = true; g.add(pad);
    const ringM = new THREE.MeshBasicMaterial({ color: col, transparent: true });
    const ring = new THREE.Mesh(new THREE.TorusGeometry(1.62, 0.09, 8, 56), ringM); ring.rotation.x = Math.PI / 2; ring.position.y = 0.52; g.add(ring);
    const face = faceTexture(String(d.label ?? d.id), col, h / w);
    const side = std(C.white, { map: face, roughness: 0.42 });
    const plain = std(col, { roughness: 0.42 });
    const body = new THREE.Mesh(rbox(w, h, w, 0.3, 3), [side, side, plain, plain, side, side]);
    body.castShadow = body.receiveShadow = true; g.add(body);
    // a soft light disc under the block that glows with the node (reads as light spill on the board)
    const spillM = new THREE.MeshBasicMaterial({ color: col, transparent: true, opacity: 0, depthWrite: false, blending: FX.additive ? THREE.AdditiveBlending : THREE.NormalBlending });
    const spill = new THREE.Mesh(new THREE.CircleGeometry(3.2, 40), spillM); spill.rotation.x = -Math.PI / 2; spill.position.y = 0.24; g.add(spill);
    const n = { id: d.id, i, x, z, h, base: 0.5, g, pad, ring, ringM, body, side, plain, col, spill, spillM };
    n.p = { rise: 1, glow: 0, tone: col, dim: 0, lift: 0, value: '', valueOn: 0, valueTone: '', tag: '', tagOn: 0, tagTone: C.gold };
    n.badge = this.ui.anchor({ world: () => this.top(d.id).add(v3(0, 0.55, 0)), offset: [0, -6], cls: 'badge' });
    n.flag = this.ui.anchor({ world: () => v3(x, 0.2, z + 1.7), offset: [0, 18], cls: 'flag', pivot: [-50, 0] });
    return n;
  }

  _edge(a, b, w, bend, arc, labelAt) {
    const A = this.nodes.find((n) => n.id === a), B = this.nodes.find((n) => n.id === b);
    const P0 = v3(A.x, A.base + A.h + 0.05, A.z), P3 = v3(B.x, B.base + B.h + 0.05, B.z);
    const d = P0.distanceTo(P3), dir = P3.clone().sub(P0).setY(0).normalize();
    const side = v3(-dir.z, 0, dir.x).multiplyScalar(0.55 + bend); // keeps a->b and b->a apart
    const lift = (1.6 + d * 0.22) * arc + (A.h + B.h) * 0.0;
    const curve = new THREE.CubicBezierCurve3(P0,
      P0.clone().lerp(P3, 0.22).add(v3(0, lift, 0)).add(side),
      P0.clone().lerp(P3, 0.78).add(v3(0, lift, 0)).add(side), P3);
    const SEG = 72, RAD = 8;
    const tubeM = new THREE.MeshBasicMaterial({ color: C.edge, transparent: true, vertexColors: true });
    const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, SEG, 0.11, RAD, false), tubeM);
    { // darker near both ends: a glowing edge blooms along its length, not onto the blocks it joins
      const g = tube.geometry, n = g.attributes.position.count, col = new Float32Array(n * 3);
      for (let i = 0; i < n; i++) { const u = Math.floor(i / (RAD + 1)) / SEG, k = 0.4 + 0.6 * E.inOutSine(clamp(Math.min(u, 1 - u) / 0.14)); col.set([k, k, k], i * 3); }
      g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    }
    const haloM = new THREE.MeshBasicMaterial({ color: C.edge, transparent: true, opacity: 0, depthWrite: false, blending: FX.additive ? THREE.AdditiveBlending : THREE.NormalBlending });
    const halo = new THREE.Mesh(new THREE.TubeGeometry(curve, SEG, 0.3, RAD, false), haloM);
    const arrowM = new THREE.MeshBasicMaterial({ color: C.edge, transparent: true });
    const arrow = new THREE.Mesh(new THREE.ConeGeometry(0.27, 0.66, 16), arrowM);
    const AT = 0.88; arrow.position.copy(curve.getPoint(AT)); arrow.quaternion.setFromUnitVectors(v3(0, 1, 0), curve.getTangent(AT));
    const beadM = new THREE.MeshBasicMaterial({ color: C.white });
    const bead = new THREE.Mesh(new THREE.SphereGeometry(0.24, 14, 10), beadM);
    tube.castShadow = true;
    this.stage.scene.add(tube, halo, arrow, bead);
    const e = { a, b, w, curve, tube, tubeM, halo, haloM, arrow, arrowM, bead, beadM, SEG, per: RAD * 6, AT, labelAt };
    e.p = { draw: 0, glow: GLOW.idle, tone: C.edge, dim: 0, fire: -1, labelOn: 0, label: String(w ?? ''), labelTone: '', labelPop: 0 };
    e.tag = this.ui.anchor({ world: () => curve.getPoint(labelAt), offset: [0, -14], cls: 'wtag' });
    this.map.set(`${a}>${b}`, e);
    return e;
  }

  apply(t) {
    for (const n of this.nodes) {
      const p = n.p, r = Math.max(0, p.rise);
      n.body.visible = r > 0.001;
      n.body.scale.set(1, Math.max(0.001, r), 1); n.body.position.y = n.base + (n.h * r) / 2 + p.lift;
      const padS = 1;
      const glow = Math.max(0, p.glow);
      n.ringM.color.set(p.tone).multiplyScalar(FX.ring[0] + glow * FX.ring[1]); n.ringM.opacity = clamp(padS) * (1 - 0.6 * p.dim);
      n.spillM.opacity = FX.spill * clamp(glow); n.spillM.color.set(p.tone);
      const base = mixHex(n.col, C.dim, 0.75 * p.dim);
      n.plain.color.set(base); n.side.color.set(mixHex(C.white, C.dim, 0.75 * p.dim));
      n.plain.emissive.set(p.tone); n.plain.emissiveIntensity = FX.emissive[0] * glow;
      n.side.emissive.set(p.tone); n.side.emissiveIntensity = FX.emissive[1] * glow;
      n.badge.on = p.valueOn * clamp(r); n.badge.text = p.value; n.badge.tone = p.valueTone;
      n.flag.on = p.tagOn * clamp(r); n.flag.text = p.tag; n.flag.tone = p.tagTone;
    }
    for (const e of this.edges) {
      const p = e.p, on = p.draw > 0.002;
      e.tube.visible = e.halo.visible = on;
      const n = Math.floor(clamp(p.draw) * e.SEG) * e.per;
      e.tube.geometry.setDrawRange(0, n);
      // the halo skips both ends so several glowing edges meeting at one block do not stack into a white blob
      const h0 = Math.round(0.12 * e.SEG) * e.per, h1 = Math.min(n, Math.round(0.84 * e.SEG) * e.per);
      e.halo.geometry.setDrawRange(h0, Math.max(0, h1 - h0));
      const fade = 1 - 0.72 * clamp(p.dim);
      e.tubeM.color.set(p.dim > 0.5 ? mixHex(p.tone, C.dim, 0.6) : p.tone).multiplyScalar(FX.hdr ? p.glow : Math.min(1, p.glow));
      e.tubeM.opacity = fade;
      e.haloM.color.set(p.tone); e.haloM.opacity = FX.halo * clamp(p.glow - 1) * fade;
      e.arrowM.color.copy(e.tubeM.color); e.arrowM.opacity = fade;
      const ap = clamp((p.draw - (e.AT - 0.06)) / 0.08);
      e.arrow.visible = ap > 0.001; e.arrow.scale.setScalar(E.outBack(ap) || 0.001);
      const f = p.fire;
      e.bead.visible = f > 0 && f < 1;
      if (e.bead.visible) { e.bead.position.copy(e.curve.getPoint(f)); e.beadM.color.set(FX.beadMix ? mixHex(p.tone, C.ink, FX.beadMix) : p.tone).multiplyScalar(FX.bead); e.bead.scale.setScalar(0.7 + Math.sin(f * Math.PI) * 0.6); }
      e.tag.on = p.labelOn * clamp((p.draw - 0.4) / 0.3); e.tag.text = p.label; e.tag.tone = p.labelTone;
      e.tag.scale = 1 + 0.28 * p.labelPop;   // tl.pulse(g.e(a, b), { labelPop: 1 }, t) when the label changes
    }
  }
}
