// stage.js: renderer, quality presets, lights, and the diorama set: a wooden desk under a warm lamp (a spot
// light pool, soft shadows), the game board the subject stands on, a few toys for scale, and behind the desk a dusk
// skyline with string lights and out-of-focus bokeh. Scenes never touch the renderer directly.
//
//   const stage = createStage();      stage.scene, stage.camera, stage.render(), stage.quality, stage.set.*
//   quality: window.QUALITY ('final' in index.html, 'draft' in draft.html) or ?q=draft|final in a browser
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { EffectComposer } from 'three/examples/jsm/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/examples/jsm/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/examples/jsm/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/examples/jsm/postprocessing/OutputPass.js';
import { FXAAPass } from 'three/examples/jsm/postprocessing/FXAAPass.js';
import { C, FX, rgba } from './style.js';
import { rand, clamp, mixHex, CHAPTERS } from './time.js';

// Speeds measured with SwiftShader on 4 CPUs are in references/threejs-guide.md ("Rendering").
// scale = the 3D renders at that fraction of the page size and is upscaled (the DOM text stays sharp).
export const PRESETS = {
  draft: { scale: 0.75, bloom: false, msaa: 0, shadowMap: 1024, shadowRadius: 3 }, // timing checks, quick reviews
  fast: { scale: 0.75, bloom: true, msaa: 4, shadowMap: 1536, shadowRadius: 4 },   // long films without a GPU
  final: { scale: 1, bloom: true, msaa: 4, shadowMap: 2048, shadowRadius: 5 },     // the best look
};
export function qualityName() {
  const q = new URLSearchParams(location.search).get('q') || window.QUALITY || 'final';
  if (!PRESETS[q]) throw new Error(`unknown quality "${q}" (use ${Object.keys(PRESETS).join(' | ')})`);
  return q;
}
// the preset, with optional URL overrides for experiments: ?q=final&bloom=0&msaa=0&aa=fxaa&shadow=1024
function quality() {
  const name = qualityName(), Q = { ...PRESETS[name] }, u = new URLSearchParams(location.search);
  if (u.has('bloom')) Q.bloom = u.get('bloom') !== '0';
  if (u.has('msaa')) Q.msaa = +u.get('msaa');
  if (u.has('aa')) Q.aa = u.get('aa');
  if (u.has('shadow')) Q.shadowMap = +u.get('shadow');
  if (u.has('scale')) Q.scale = +u.get('scale');
  return [name, Q];
}

export const rbox = (w, h, d, r = 0.2, seg = 3) => new RoundedBoxGeometry(w, h, d, seg, Math.min(r, w / 2, h / 2, d / 2) * 0.999);
export const std = (color, o = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.62, metalness: 0, ...o });
// matte surfaces: Lambert looks the same at this roughness and costs far less per pixel under SwiftShader
export const matte = (color, o = {}) => { const { roughness, metalness, ...rest } = o; return new THREE.MeshLambertMaterial({ color, ...rest }); };
export function shade(obj, cast = true, receive = true) { obj.traverse((o) => { if (o.isMesh) { o.castShadow = cast; o.receiveShadow = receive; } }); return obj; }
const canvasTex = (w, h, draw) => { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };

let DOT = null; // a soft round sprite for bokeh and halos
export function softDot() {
  DOT = DOT || canvasTex(128, 128, (x) => {
    const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
    g.addColorStop(0, rgba(C.white, 1)); g.addColorStop(0.5, rgba(C.white, 0.8)); g.addColorStop(0.78, rgba(C.white, 0.2)); g.addColorStop(1, rgba(C.white, 0)); // an alpha mask, tinted by each sprite
    x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  });
  return DOT;
}

function woodTexture() {
  const R = rand(5);
  const t = canvasTex(1024, 512, (x, w, h) => {
    x.fillStyle = C.desk; x.fillRect(0, 0, w, h);
    for (let i = 0; i < 140; i++) { // grain: long wavy strokes, a little darker or lighter than the base
      const y0 = R() * h, a = 0.04 + R() * 0.08, amp = 2 + R() * 6, f = 0.004 + R() * 0.01, ph = R() * 6;
      x.strokeStyle = R() > 0.5 ? rgba(C.woodDark, a) : rgba(C.woodLight, a * 0.8); x.lineWidth = 1 + R() * 3;
      x.beginPath(); for (let px = 0; px <= w; px += 16) x.lineTo(px, y0 + Math.sin(px * f + ph) * amp); x.stroke();
    }
    for (let i = 0; i < 4; i++) { const cx = R() * w, cy = R() * h; x.strokeStyle = rgba(C.woodDark, 0.12); for (let r = 4; r < 22; r += 5) { x.beginPath(); x.ellipse(cx, cy, r * 2.2, r, 0, 0, Math.PI * 2); x.stroke(); } }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2, 2); return t;
}
function boardTexture() {
  return canvasTex(1024, 1024, (x) => {
    x.fillStyle = C.board; x.fillRect(0, 0, 1024, 1024);
    x.strokeStyle = C.grid; x.lineWidth = 2;
    for (let i = 0; i <= 16; i++) { const v = i * 64; x.beginPath(); x.moveTo(v, 0); x.lineTo(v, 1024); x.stroke(); x.beginPath(); x.moveTo(0, v); x.lineTo(1024, v); x.stroke(); }
    x.fillStyle = C.gridDot;
    for (let i = 0; i <= 16; i++) for (let j = 0; j <= 16; j++) { x.beginPath(); x.arc(i * 64, j * 64, 4, 0, Math.PI * 2); x.fill(); }
  });
}
function skylineTexture() { // a ring of building silhouettes with lit windows, transparent above the roofs
  const R = rand(21);
  const t = canvasTex(2048, 512, (x, w, h) => {
    let px = 0;
    while (px < w) {
      const bw = 40 + R() * 90, bh = 90 + R() * 260, top = h - bh;
      x.fillStyle = R() > 0.5 ? C.building[0] : C.building[1]; x.fillRect(px, top, bw, bh);
      for (let wy = top + 12; wy < h - 10; wy += 16) for (let wx = px + 8; wx < px + bw - 10; wx += 14) {
        if (R() < 0.32) { x.fillStyle = R() > 0.35 ? C.windows[0] : C.windows[1]; x.fillRect(wx, wy, 6, 8); }
      }
      px += bw + R() * 6;
    }
  });
  t.wrapS = THREE.RepeatWrapping; t.repeat.set(3, 1); return t;
}

function buildSet(scene) {
  const R = rand(11);
  // sky dome: dark zenith, violet, a warm band at the horizon, deep plum below
  const sky = new THREE.Mesh(new THREE.SphereGeometry(320, 32, 16), new THREE.ShaderMaterial({
    side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: { c0: { value: new THREE.Color(C.sky[0]) }, c1: { value: new THREE.Color(C.sky[1]) }, c2: { value: new THREE.Color(C.sky[2]) }, c3: { value: new THREE.Color(C.sky[3]) }, lo: { value: new THREE.Color(C.sky[4]) } },
    vertexShader: 'varying vec3 vP; void main(){ vP = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }',
    fragmentShader: `uniform vec3 c0, c1, c2, c3, lo; varying vec3 vP;
      void main(){ float h = vP.y;
        vec3 c = mix(c2, c1, smoothstep(0.0, 0.22, h)); c = mix(c, c0, smoothstep(0.22, 0.75, h));
        c = mix(lo, c, smoothstep(-0.3, 0.0, h));
        c = mix(c, c3, exp(-abs(h - 0.01) * 14.0) * 0.85);
        gl_FragColor = vec4(c, 1.0);${FX.skyGraded ? '\n        #include <tonemapping_fragment>\n        #include <colorspace_fragment>' : ''} }`,
  }));
  scene.add(sky);
  scene.fog = new THREE.Fog(C.fog, 80, 260);

  // skyline ring far behind the desk
  const city = new THREE.Mesh(new THREE.CylinderGeometry(170, 170, 70, 48, 1, true),
    new THREE.MeshBasicMaterial({ map: skylineTexture(), transparent: true, side: THREE.BackSide, fog: false, depthWrite: false }));
  city.position.y = -38; scene.add(city);

  // desk + board
  const desk = new THREE.Mesh(rbox(66, 3, 42, 1.3), matte(C.white, { map: woodTexture() }));
  desk.position.y = -2.1; shade(desk, false, true); scene.add(desk);
  const legM = matte(C.deskEdge);
  for (const [x, z] of [[-29, -17], [29, -17], [-29, 17], [29, 17]]) { const l = new THREE.Mesh(new THREE.CylinderGeometry(1.2, 1.0, 40, 12), legM); l.position.set(x, -23.6, z); scene.add(l); }
  const board = new THREE.Group(); scene.add(board);
  const rimM = matte(C.boardRim);
  const top = new THREE.Mesh(rbox(27, 0.6, 17.5, 0.28), [rimM, rimM, matte(C.white, { map: boardTexture() }), rimM, rimM, rimM]);
  top.position.y = -0.3; shade(top, false, true); board.add(top);
  const lip = new THREE.Mesh(rbox(28.2, 0.36, 18.7, 0.18), rimM);
  lip.position.y = -0.5; shade(lip, true, true); board.add(lip);

  // toys on the desk (scale and story); kept outside the board so they never cover the subject
  const toys = new THREE.Group(); scene.add(toys);
  const blockCols = [C.node[0], C.node[1], C.node[2]];
  [[-20, 0.3, -10.5, 0.3, 0], [-19.6, 2.1, -10.7, -0.25, 1], [-17.6, 0.3, -12, 0.9, 2]].forEach(([x, y, z, r, i]) => {
    const b = new THREE.Mesh(rbox(1.8, 1.8, 1.8, 0.34), std(blockCols[i], { roughness: 0.45 })); b.position.set(x, y, z); b.rotation.y = r; toys.add(b);
  });
  const mug = new THREE.Group(); mug.position.set(19.5, -0.6, -10.5); toys.add(mug);
  const mugM = std(C.mug, { roughness: 0.35 });
  const mugBody = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.18, 2.7, 28), mugM); mugBody.position.y = 1.35; mug.add(mugBody);
  const coffee = new THREE.Mesh(new THREE.CircleGeometry(1.14, 28), std(C.coffee, { roughness: 0.2 })); coffee.rotation.x = -Math.PI / 2; coffee.position.y = 2.5; mug.add(coffee);
  const handle = new THREE.Mesh(new THREE.TorusGeometry(0.62, 0.17, 10, 20), mugM); handle.position.set(1.35, 1.4, 0); mug.add(handle);
  const pencil = new THREE.Group(); pencil.position.set(17, -0.6 + 0.28, 11.5); pencil.rotation.y = 0.5; toys.add(pencil);
  const pb = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.28, 7, 6), std(C.gold, { roughness: 0.5 })); pb.rotation.z = Math.PI / 2; pencil.add(pb);
  const tip = new THREE.Mesh(new THREE.ConeGeometry(0.28, 0.9, 6), std(C.pencilTip)); tip.rotation.z = -Math.PI / 2; tip.position.x = 3.95; pencil.add(tip);
  const eraser = new THREE.Mesh(new THREE.CylinderGeometry(0.29, 0.29, 0.6, 12), std(C.node[2])); eraser.rotation.z = Math.PI / 2; eraser.position.x = -3.8; pencil.add(eraser);
  const plant = new THREE.Group(); plant.position.set(-20.5, -0.6, 9); toys.add(plant);
  const pot = new THREE.Mesh(new THREE.CylinderGeometry(1.3, 1.0, 1.9, 20), matte(C.pot)); pot.position.y = 0.95; plant.add(pot);
  const leafM = matte(C.leaf, { flatShading: true });
  for (let i = 0; i < 7; i++) { const l = new THREE.Mesh(new THREE.IcosahedronGeometry(0.7 + R() * 0.35, 0), leafM); const a = i * 0.95; l.position.set(Math.cos(a) * 0.65, 2.3 + (i % 3) * 0.55, Math.sin(a) * 0.65); plant.add(l); }
  shade(toys, true, true);

  // string lights hanging behind the desk (they bloom in final quality; halos keep them glowing in draft)
  const dot = softDot();
  const lights = new THREE.Group(); scene.add(lights);
  const bulbM = new THREE.MeshBasicMaterial({ color: new THREE.Color(C.bulb).multiplyScalar(FX.bulb), fog: false });
  const wire = [];
  for (let i = 0; i <= 26; i++) {
    const u = i / 26, x = -70 + 140 * u, y = 13 - 7 * Math.sin(Math.PI * u) + 1.2 * Math.sin(u * 17), z = -40 - 8 * Math.sin(u * 2.7);
    wire.push(new THREE.Vector3(x, y + 0.5, z));
    const b = new THREE.Mesh(new THREE.SphereGeometry(0.45, 10, 8), bulbM); b.position.set(x, y, z); lights.add(b);
    const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: C.bulbHalo, transparent: true, opacity: FX.bulbHalo, depthWrite: false, fog: false, blending: FX.additive ? THREE.AdditiveBlending : THREE.NormalBlending }));
    halo.position.copy(b.position); halo.scale.setScalar(3.6); lights.add(halo);
  }
  lights.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(wire), new THREE.LineBasicMaterial({ color: C.wire })));

  // out-of-focus bokeh all around (cheap depth-of-field feel)
  const cols = C.bokeh;
  for (let i = 0; i < 60; i++) {
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: dot, color: cols[i % cols.length], transparent: true, opacity: FX.bokeh[0] + R() * FX.bokeh[1], depthWrite: false, fog: false, blending: FX.additive ? THREE.AdditiveBlending : THREE.NormalBlending }));
    const a = -Math.PI * 0.98 + R() * Math.PI * 0.96, r = 70 + R() * 70;
    s.position.set(Math.cos(a) * r, -26 + R() * 56, Math.sin(a) * r * 0.9 - 10);
    s.scale.setScalar(3 + R() * 10); scene.add(s);
  }
  return { sky, city, desk, board, toys, lights };
}

export function createStage() {
  const [qname, Q] = quality();
  const W = window.innerWidth, H = window.innerHeight;
  // the 3D can render below the page resolution (scale < 1) and be upscaled; the text overlay stays crisp
  const s = Q.scale || 1, GW = Math.round(W * s), GH = Math.round(H * s);
  const renderer = new THREE.WebGLRenderer({ antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
  renderer.setPixelRatio(1); renderer.setSize(GW, GH, false);
  Object.assign(renderer.domElement.style, { width: '100%', height: '100%' });
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.NeutralToneMapping; renderer.toneMappingExposure = FX.light.exposure;
  renderer.shadowMap.enabled = Q.shadowMap > 0; renderer.shadowMap.type = THREE.PCFShadowMap;
  renderer.domElement.id = 'gl';
  document.getElementById('film').prepend(renderer.domElement);

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(30, W / H, 0.5, 800);

  // lights: a warm desk lamp (spot, soft shadows, a pool of light on the board), cool rim from behind, dim fill
  const key = new THREE.SpotLight(C.key, FX.light.key, 0, 0.5, 0.75, 0);
  key.position.set(-15, 36, 19); key.target.position.set(0, 0, 0);
  key.castShadow = Q.shadowMap > 0;
  key.shadow.mapSize.set(Q.shadowMap || 512, Q.shadowMap || 512);
  key.shadow.camera.near = 15; key.shadow.camera.far = 90;
  key.shadow.radius = Q.shadowRadius; key.shadow.bias = -0.0004; key.shadow.normalBias = 0.03;
  scene.add(key, key.target);
  const rim = new THREE.DirectionalLight(C.rim, FX.light.rim); rim.position.set(18, 14, -22); scene.add(rim);
  const fill = new THREE.DirectionalLight(C.fillLight, FX.light.fill); fill.position.set(10, 12, 25); scene.add(fill);
  scene.add(new THREE.HemisphereLight(C.skyFill, C.groundFill, FX.light.hemi));

  const set = buildSet(scene);

  let composer = null;
  if (Q.bloom || Q.msaa || Q.aa) {
    const rt = new THREE.WebGLRenderTarget(GW, GH, { type: THREE.HalfFloatType, samples: Q.msaa || 0 });
    composer = new EffectComposer(renderer, rt);
    composer.setPixelRatio(1); composer.setSize(GW, GH);
    composer.addPass(new RenderPass(scene, camera));
    if (Q.bloom && FX.bloom[0] > 0) composer.addPass(new UnrealBloomPass(   // light themes: no bloom (nothing glows above its fill)
      new THREE.Vector2(GW, GH), ...FX.bloom));
    composer.addPass(new OutputPass());
    if (Q.aa === 'fxaa') composer.addPass(new FXAAPass());
  }
  return {
    THREE, scene, camera, renderer, key, rim, set, quality: qname, Q, W, H,
    /** per-frame stage state (a pure function of t): with a theme, the key light takes each chapter's colour
     *  from the theme's six chapter lights, cross-fading behind the chapter banner */
    apply(t) {
      if (!C.keyLights) return;
      const ks = C.keyLights, col = (i) => ks[((i % ks.length) + ks.length) % ks.length];
      let i = 0; CHAPTERS.forEach((c, k) => { if (c.start - 0.8 <= t) i = k; });
      const c = CHAPTERS[i], u = clamp((t - (c.start - 0.8)) / 1.2);
      key.color.set(i === 0 ? col(0) : mixHex(col(i - 1), col(i), u));
    },
    render() { if (composer) composer.render(); else renderer.render(scene, camera); },
    warmup() { renderer.compile(scene, camera); this.render(); },
  };
}
