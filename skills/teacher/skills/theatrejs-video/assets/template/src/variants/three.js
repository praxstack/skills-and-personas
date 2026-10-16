// variants/three.js: the SAME Theatre sheet bound to Three.js objects instead of the DOM/SVG stage. A small working
// example of the 3D route: the graph becomes pucks on a floor with arcing flight tubes, the Theatre Camera object
// becomes an orbiting perspective camera, and the 2D kit (captions, chapter cards, bursts, panels) stays on top as a
// screen-space overlay. Same world.js, same shots.js, same theatre-state.json: re-voicing re-times both variants.
//
// Build: npm i --save-exact three@0.186.1 && node tools/build.mjs --3d     Page: index-3d.html
// Render: capture.mjs --page source/index-3d.html --webgl ...   (SwiftShader: expect ~1 to 3 fps on 4 CPUs)
// For a full 3D film (lights, shadows, bloom, models, the 3D kit) use the threejs-video skill; keep Theatre as the
// animation system by binding its objects the way this file does.
import * as THREE from 'three';
import '../kit/style.css';
import interVar from 'inter-ui/variable/InterVariable.woff2';
import jbBold from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-Bold.woff2';
import bangers from '@fontsource/bangers/files/bangers-latin-400-normal.woff2';
import { C, P, applyCssVars } from '../kit/tokens.js';
import { clamp, mix, el, hex, css, setStyle, setText } from '../kit/util.js';
import { timeline } from '../theatre/timing.js';
import { compileFilm, schemaOf } from '../theatre/keys.js';
import { createRig } from '../theatre/rig.js';
import world, { PROJECT_ID } from '../film/world.js';
import shots from '../film/shots.js';

const W3 = (x, y, h = 0) => new THREE.Vector3((x - 960) / 100, h, (y - 540) / 100); // layer px -> world units
const col = (c) => { const [r, g, b] = mix(c, c, 0); return new THREE.Color(r / 255, g / 255, b / 255); };
const srgb = (c) => new THREE.Color(hex(c)); // a CSS colour, as THREE.Color(0xrrggbb) reads it (sRGB)

async function boot() {
  for (const [fam, url, weight] of [['Inter Var', interVar, '100 900'], ['JB Mono', jbBold, '400 900'], ['Bangers', bangers, '400']]) {
    const f = new FontFace(fam, `url(${url})`, { weight }); await f.load(); document.fonts.add(f);
  }
  applyCssVars(document.documentElement.style);

  const T = timeline(window.TIMING), Wd = world(T), G = Wd.graph;
  let state;
  try { const res = await fetch('theatre-state.json'); state = res.ok ? await res.json() : null; } catch { state = null; }
  if (!state || (!state.pinned && state.generated?.timingHash !== T.hash)) state = compileFilm({ T, W: Wd, shots }).state;
  const rig = await createRig({ projectId: PROJECT_ID, state, schema: schemaOf(Wd.components) });

  // ---- three.js scene
  const vp = el('div', { id: 'viewport' }, document.getElementById('root'));
  const renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1); renderer.setSize(1920, 1080); vp.appendChild(renderer.domElement);
  Object.assign(renderer.domElement.style, { position: 'absolute', left: '0px', top: '0px' });
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.outputColorSpace = THREE.SRGBColorSpace;
  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(srgb(C.three.fog), 18, 42);
  const camera = new THREE.PerspectiveCamera(36, 1920 / 1080, 0.1, 200);
  scene.add(new THREE.HemisphereLight(srgb(C.three.hemiSky), srgb(C.three.hemiGround), 1.4));
  const key = new THREE.DirectionalLight(srgb(C.three.key), 2.2); key.position.set(-6, 12, 8); scene.add(key);
  const rim = new THREE.DirectionalLight(srgb(C.three.rim), 1.2); rim.position.set(8, 6, -10); scene.add(rim);
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(80, 80), new THREE.MeshStandardMaterial({ color: srgb(C.three.floor), roughness: 0.9 }));
  floor.rotation.x = -Math.PI / 2; scene.add(floor);
  const grid = new THREE.GridHelper(80, 80, srgb(C.three.grid), srgb(C.three.grid2)); grid.position.y = 0.01; scene.add(grid);

  const label = (text) => { // number sprite
    const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
    g.font = '800 72px "JB Mono"'; g.fillStyle = C.ink; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(text, 64, 70);
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: new THREE.CanvasTexture(c), depthTest: false, depthWrite: false }));
    s.scale.set(0.7, 0.7, 1); s.renderOrder = 10; return s; // drawn last: the edge tubes end at the puck centres and would cover it
  };
  const nodes = G.nodes.map((n) => {
    const g = new THREE.Group(); g.position.copy(W3(n.x, n.y));
    const mat = new THREE.MeshStandardMaterial({ color: col(C.node), roughness: 0.35, metalness: 0.1, emissive: new THREE.Color(0, 0, 0) });
    const puck = new THREE.Mesh(new THREE.CylinderGeometry(0.55, 0.6, 0.35, 48), mat); puck.position.y = 0.18; g.add(puck);
    const l = label(String(n.label ?? n.id)); l.position.y = 0.75; g.add(l);
    scene.add(g); return { n, g, mat };
  });
  const edges = G.edges.map((e) => {
    const A = G.N.get(String(e.from)), B = G.N.get(String(e.to));
    const pts = []; for (let i = 0; i <= 48; i++) { const u = i / 48, p = e.q(u); pts.push(W3(p[0], p[1], 0.35 + 1.1 * Math.sin(Math.PI * u))); }
    const curve = new THREE.CatmullRomCurve3(pts);
    const geo = new THREE.TubeGeometry(curve, 96, 0.05, 8, false);
    const mat = new THREE.MeshBasicMaterial({ color: col(C.edge), transparent: true, toneMapped: false });
    const mesh = new THREE.Mesh(geo, mat); scene.add(mesh);
    return { e, curve, mesh, mat, count: geo.index.count, A, B };
  });
  const tokens = Array.from({ length: G.tokens }, (_, i) => {
    const m = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.5, 16), new THREE.MeshStandardMaterial({ color: i ? col(C.cool) : col(C.gold), emissive: i ? col(C.cool) : col(C.gold), emissiveIntensity: 0.6 }));
    m.rotation.z = -Math.PI / 2; const g = new THREE.Group(); g.add(m); scene.add(g); return g;
  });

  // ---- the 2D kit on top: HUD pieces + panels in screen space (no 2D graph: it is 3D now)
  // the graph's text chips (edge weights, START/GOAL tags, value badges) as DOM at the projected 3D positions,
  // under the panels and faded with the content, like the 2D graph's chips (the decoder's chips land on the weights)
  const chips = el('div', { style: { position: 'absolute', left: '0px', top: '0px', width: '1920px', height: '1080px', pointerEvents: 'none' } }, vp);
  const chip = (cls, st) => el('div', { class: cls, style: { position: 'absolute', left: '0px', top: '0px', whiteSpace: 'nowrap', opacity: '0', borderRadius: '12px', ...st } }, chips);
  const GT = { weight: 32, tag: 30, badge: 34 };
  const BADGE_AT = { tr: [1, -1], tl: [-1, -1], br: [1, 1], bl: [-1, 1], above: [0, -1], below: [0, 1] };
  const overlay = el('div', { class: 'layer-inner', style: { left: '0px', top: '0px' } }, vp);
  const hud = el('div', { class: 'hud' }, vp);
  const over = el('div', { class: 'hud hud-over' }, vp); // the chapter card, above everything Content fades
  const fake = { hud, over, layer: () => overlay, vp };
  const flat = Wd.components.filter((c) => c !== Wd.stage && c !== G);
  for (const c of flat) c.mount(fake);
  // the decoder's chips fly to where the 3D edge's midpoint is on screen
  const project = (v) => { const p = v.clone().project(camera); return [(p.x + 1) * 960, (1 - p.y) * 540]; };
  Wd.decoder.target = (to) => {
    if (to.edge) { const [a, b] = to.edge.split('-'); const E = edges.find((x) => String(x.e.from) === a && String(x.e.to) === b); return project(E.curve.getPoint(0.5).applyMatrix4(E.mesh.matrixWorld)); }
    const N = nodes.find((x) => String(x.n.id) === String(to.node)); return project(N.g.position.clone().setY(0.6));
  };

  for (const E of edges) E.chip = chip('mono', { padding: '2px 18px', background: css(C.plate, 0.94), color: C.ink, border: `2px solid ${css(C.chipStroke)}`, fontSize: `${GT.weight}px`, fontWeight: '700' });
  for (const N of nodes) {
    N.tag = chip('ui', { padding: '4px 16px', background: C.gold, color: C.onGold, border: `3px solid ${css(C.outline)}`, borderRadius: '9px', fontSize: `${GT.tag}px`, fontWeight: '900', letterSpacing: '2px' });
    N.badge = chip('mono', { padding: '3px 15px', background: css(C.plate, 0.95), color: C.ink, border: `3px solid ${css(C.cool)}`, fontSize: `${GT.badge}px`, fontWeight: '800' });
  }
  const at = (e, [x, y], dx, dy, o, sc = 1) => { setStyle(e, 'opacity', o.toFixed(3)); if (o > 0.001) setStyle(e, 'transform', `translate(${(x + dx).toFixed(1)}px,${(y + dy).toFixed(1)}px) translate(-50%,-50%) scale(${sc.toFixed(3)})`); };

  const tgt = new THREE.Vector3();
  window.TOTAL = T.total;
  window.renderFrame = (t) => {
    const V = rig.values(t), cam = V.Camera, gp = V[G.id];
    // Content fade (chapter changes, see R.chapter): the 3D graph, the 2D panels and the HUD; the card stays
    const fadeA = clamp(V.Content ? V.Content.in : 1);
    for (const e of [chips, overlay, hud]) e.style.opacity = fadeA >= 0.999 ? '' : fadeA.toFixed(3);
    for (const N of nodes) N.g.traverse((o) => { if (o.material) { o.material.transparent = o.isSprite || fadeA < 0.999; o.material.opacity = fadeA; } });
    for (const g of tokens) g.traverse((o) => { if (o.material) { o.material.transparent = o.isSprite || fadeA < 0.999; o.material.opacity = fadeA; } });
    // Theatre Camera -> orbiting perspective camera (pan x/y, dolly z, orbit, tilt)
    const k = P / Math.max(200, P - cam.z);
    const dist = 17 / k, az = THREE.MathUtils.degToRad(cam.orbit * 4), el_ = THREE.MathUtils.degToRad(52 + cam.tilt * 3);
    tgt.set(cam.x / 100, 0, cam.y / 100 + 0.6);
    camera.position.set(tgt.x + dist * Math.cos(el_) * Math.sin(az), dist * Math.sin(el_), tgt.z + dist * Math.cos(el_) * Math.cos(az));
    camera.lookAt(tgt);
    const sky = V.Sky; scene.background = new THREE.Color(sky.bottom.r, sky.bottom.g, sky.bottom.b); scene.fog.color.copy(scene.background);
    // graph placement (Graph x, y, s) as a group transform around the graph centre
    const place = (x, y) => [(x - G.cx) * gp.s + G.cx + gp.x, (y - G.cy) * gp.s + G.cy + gp.y];
    for (const N of nodes) {
      const v = V[G.nodeKey(N.n.id)], [x, y] = place(N.n.x, N.n.y);
      N.g.position.copy(W3(x, y)); N.g.scale.setScalar(Math.max(0.001, v.in * gp.s)); N.g.visible = v.in > 0.01;
      const c = mix(mix(mix(C.node, C.accent, v.hot), C.good, v.good), C.bad, v.bad);
      N.mat.color.setRGB(c[0] / 255, c[1] / 255, c[2] / 255); N.mat.emissive.setRGB(c[0] / 255 * 0.4 * clamp(v.glow + v.hot + v.good), c[1] / 255 * 0.4 * clamp(v.glow + v.hot + v.good), c[2] / 255 * 0.4 * clamp(v.glow + v.hot + v.good));
    }
    for (const E of edges) {
      const v = V[G.edgeKey(E.e.from, E.e.to)];
      E.mesh.visible = v.draw > 0.01;
      E.mesh.geometry.setDrawRange(0, Math.floor(E.count * clamp(v.draw) / 3) * 3);
      const c = mix(mix(mix(C.edge, C.accent, v.hot), C.good, v.good), C.bad, v.bad);
      E.mat.color.setRGB(c[0] / 255, c[1] / 255, c[2] / 255); E.mat.opacity = (1 - 0.7 * clamp(v.dim)) * fadeA;
      E.mesh.scale.set(gp.s, gp.s, gp.s); // the graph's placement: p' = (p - centre) * s + centre + offset
      E.mesh.position.set((1 - gp.s) * (G.cx - 960) / 100 + gp.x / 100, 0, (1 - gp.s) * (G.cy - 540) / 100 + gp.y / 100);
    }
    tokens.forEach((g, i) => {
      const v = V[G.tokenKey(i)]; g.visible = v.in > 0.02 && !!v.route; if (!g.visible) return;
      const p = G.routePoint(v.route, v.u), q = G.routePoint(v.route, Math.min(1, v.u + 0.01));
      const [x, y] = place(p.x, p.y), [x2, y2] = place(q.x, q.y);
      const legU = (clamp(v.u) * p.legs) % 1, h = 0.4 + 1.1 * Math.sin(Math.PI * legU) * gp.s;
      g.position.copy(W3(x, y, h)); g.lookAt(W3(x2, y2, h)); g.rotateY(-Math.PI / 2);
    });
    renderer.render(scene, camera);
    // text chips at the projected positions (after the camera has moved, so they never swim)
    for (const E of edges) {
      const v = V[G.edgeKey(E.e.from, E.e.to)], o = clamp(v.label) * clamp((v.draw - 0.94) / 0.04);
      if (o > 0.001) { setText(E.chip, E.e.w ?? ''); setStyle(E.chip, 'color', css(mix(C.ink, C.inkDim, clamp(v.dim)))); }
      at(E.chip, project(E.curve.getPoint(0.5).applyMatrix4(E.mesh.matrixWorld)), 0, -30, o);
    }
    for (const N of nodes) {
      const v = V[G.nodeKey(N.n.id)], p = project(N.g.position.clone().setY(0.2)), sc = Math.max(0.6, gp.s);
      if (v.tag) setText(N.tag, v.tag);
      at(N.tag, p, 0, 62 * sc + 14 * (1 - clamp(v.tagIn)), v.tag && N.g.visible ? clamp(v.tagIn * 5) : 0);
      if (v.badge) setText(N.badge, v.badge);
      const [ax, ay] = BADGE_AT[v.badgeAt || N.n.badgeAt || 'tr'] || BADGE_AT.tr;
      at(N.badge, p, ax * 78 * sc, ay * (ax ? 56 : 84) * sc, v.badge && N.g.visible ? clamp(v.badgeIn * 5) : 0, 0.85 + 0.15 * Math.min(1.2, v.badgeIn));
    }
    for (const c of flat) c.apply(V, t);
  };
  window.renderFrame(0);
  return true;
}
window.READY = boot().catch((e) => { console.error(e); const m = String(e.stack || e); window.renderFrame = () => { throw new Error(m); }; throw e; });
