// The stage every film is built on: layered depth, a camera, and a film clock.
//
//   const w = createWorld(view);   // inside makeScene2D
//   yield w.run();                 // starts the clock, camera drift and grain (background thread)
//   w.world.add(graph.root);       // things the camera moves (the persistent subject)
//   w.hud.add(panel);              // screen-fixed panels (code, tables, question cards)
//   w.top.add(...)                 // bursts and things flying between layers
//   yield* w.camera.frame(graph.center(), [-420, -40], 1.1);   // put a world point at a screen point
//
// Layers, back to front: backdrop (parallax dots and warm light) / world (camera space) / vignette /
// hud / top / grain / chrome (captions, chapter cards, progress).
import {Node, Rect, Gradient, type NodeProps, type View2D} from '@motion-canvas/2d';
import {
  Vector2,
  createSignal,
  easeInOutCubic,
  easeOutCubic,
  linear,
  type PossibleVector2,
  type SimpleSignal,
  type ThreadGenerator,
  type TimingFunction,
  all,
  useThread,
} from '@motion-canvas/core';
import {C, FRAME, LIGHT, THEME, alpha, mix, rgba} from './theme';
import {CHAPTERS, TOTAL, setFilmThread} from './clock';

/** A node that paints itself with a plain canvas callback (used for cached backgrounds and grain). */
export class Painter extends Node {
  public constructor(
    private readonly paint: (ctx: CanvasRenderingContext2D) => void,
    props: NodeProps = {},
  ) {
    super(props);
  }
  protected override draw(context: CanvasRenderingContext2D) {
    this.paint(context);
    super.draw(context);
  }
}

// small deterministic PRNG (same frames on every render)
export function rng(seed: number) {
  let s = seed >>> 0;
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let t = s;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const MARGIN = 260; // backdrop overscan for parallax
const KEY_FADE = 1.2; // seconds a chapter's key light takes to fade in (themes only)

/**
 * The far layer: ground, soft light and a dot grid. `key` is the warm key light behind the subject (C.bgGlow);
 * with a theme, each chapter gets its own key light from the theme's `lights` (one canvas per chapter).
 */
function makeBackdropCanvas(key: string = C.bgGlow) {
  const w = FRAME.w + 2 * MARGIN;
  const h = FRAME.h + 2 * MARGIN;
  const cv = document.createElement('canvas');
  cv.width = w;
  cv.height = h;
  const g = cv.getContext('2d')!;
  g.fillStyle = C.bg;
  g.fillRect(0, 0, w, h);
  if (THEME) {
    // the theme's gradient partner, towards the bottom right
    const lin = g.createLinearGradient(0, 0, w, h);
    lin.addColorStop(0, alpha(THEME.bg2, 0));
    lin.addColorStop(1, alpha(THEME.bg2, 1));
    g.fillStyle = lin;
    g.fillRect(0, 0, w, h);
  }
  const glow = (x: number, y: number, r: number, color: string, a: number) => {
    const grd = g.createRadialGradient(x, y, 0, x, y, r);
    grd.addColorStop(0, color);
    // a theme fades to its own colour (a fade to transparent black greys a light ground)
    grd.addColorStop(1, rgba(THEME ? color : C.black, 0));
    g.globalAlpha = a;
    g.fillStyle = grd;
    g.fillRect(0, 0, w, h);
    g.globalAlpha = 1;
  };
  glow(w * 0.45, h * 0.42, 1100, key, 1); // warm key light behind the subject
  glow(w * 0.45, h * 0.42, 520, key, 0.8); // its hot centre
  glow(w * 0.92, h * 0.08, 900, C.bgCool, 1); // cool rim light, top right
  glow(w * 0.08, h * 0.95, 700, C.bgCorner, 0.9); // a little colour in the far corner
  // dot grid that fades towards the edges
  const step = 44;
  for (let y = step / 2; y < h; y += step) {
    for (let x = step / 2; x < w; x += step) {
      const dx = (x - w / 2) / (w / 2);
      const dy = (y - h / 2) / (h / 2);
      const fade = Math.max(0, 1 - 0.75 * Math.sqrt(dx * dx + dy * dy));
      g.globalAlpha = 0.3 + 0.9 * fade;
      g.fillStyle = C.grid;
      g.beginPath();
      g.arc(x, y, 1.7, 0, Math.PI * 2);
      g.fill();
    }
  }
  g.globalAlpha = 1;
  return cv;
}

/** The key light for chapter n: the theme's chapter lights, mixed gently into the ground. */
function chapterKey(n: number) {
  const L = THEME!.lights;
  return mix(THEME!.bg, L[((n % L.length) + L.length) % L.length], LIGHT ? 0.07 : 0.13);
}

function makeGrainCanvas() {
  const n = 256;
  const cv = document.createElement('canvas');
  cv.width = n;
  cv.height = n;
  const g = cv.getContext('2d')!;
  const img = g.createImageData(n, n);
  const r = rng(7);
  for (let i = 0; i < n * n; i++) {
    const v = r() < 0.5 ? 0 : 255;
    img.data[i * 4] = img.data[i * 4 + 1] = img.data[i * 4 + 2] = v;
    img.data[i * 4 + 3] = Math.floor(r() * 26);
  }
  g.putImageData(img, 0, 0);
  return cv;
}

export interface CameraTarget {
  /** world point to look at */
  focus?: PossibleVector2;
  /** where on screen (scene coordinates, origin at the centre) that world point appears */
  anchor?: PossibleVector2;
  zoom?: number;
}

/**
 * A 2D camera: moves and scales the world layer. `focus` (a world point) appears at `anchor` (a screen point)
 * at `zoom`. A slow drift and breathing zoom keep holds alive; `shake()` punctuates rejections.
 */
export class Camera {
  public readonly focus = Vector2.createSignal(Vector2.zero);
  public readonly anchor = Vector2.createSignal(Vector2.zero);
  public readonly zoom = createSignal(1);
  /** drift amplitude in pixels (0 turns it off) */
  public readonly drift = createSignal(7);
  private readonly shakeAmp = createSignal(0);

  public constructor(
    private readonly layer: Node,
    private readonly time: SimpleSignal<number>,
  ) {
    layer.scale(() => {
      const t = this.time();
      return this.zoom() * (1 + 0.006 * Math.sin((2 * Math.PI * t) / 17));
    });
    layer.position(() => this.offset());
  }

  /** the world layer's current translation (used by the backdrop for parallax) */
  public offset(): Vector2 {
    const t = this.time();
    const z = this.layer.scale().x;
    const d = this.drift();
    const s = this.shakeAmp();
    const drift = new Vector2(Math.sin((2 * Math.PI * t) / 13) * d, Math.cos((2 * Math.PI * t) / 11) * d * 0.6);
    const shake = new Vector2(Math.sin(t * 71) * 14 * s, Math.cos(t * 53) * 10 * s);
    return this.anchor().sub(this.focus().scale(z)).add(drift).add(shake);
  }

  /** Move the camera. Any field left out keeps its value. */
  public *to(target: CameraTarget, duration = 1.0, ease: TimingFunction = easeInOutCubic): ThreadGenerator {
    const anims: ThreadGenerator[] = [];
    if (target.focus !== undefined) anims.push(this.focus(new Vector2(target.focus), duration, ease));
    if (target.anchor !== undefined) anims.push(this.anchor(new Vector2(target.anchor), duration, ease));
    if (target.zoom !== undefined) anims.push(this.zoom(target.zoom, duration, ease));
    yield* all(...anims);
  }

  /** Put world point `focus` at screen point `anchor` with `zoom` (the usual move between compositions). */
  public *frame(focus: PossibleVector2, anchor: PossibleVector2, zoom: number, duration = 1.0, ease = easeInOutCubic) {
    yield* this.to({focus, anchor, zoom}, duration, ease);
  }

  /** Push in on a world point, keeping the current anchor. */
  public *pushIn(focus: PossibleVector2, zoom = 1.3, duration = 0.8) {
    yield* this.to({focus, zoom}, duration, easeInOutCubic);
  }

  /** A short shake (a rejection, a thud). */
  public *shake(strength = 1, duration = 0.45): ThreadGenerator {
    this.shakeAmp(strength);
    yield* this.shakeAmp(0, duration, easeOutCubic);
  }

  /** Set without animation. */
  public set(target: CameraTarget) {
    if (target.focus !== undefined) this.focus(new Vector2(target.focus));
    if (target.anchor !== undefined) this.anchor(new Vector2(target.anchor));
    if (target.zoom !== undefined) this.zoom(target.zoom);
  }
}

export interface World {
  view: View2D;
  backdrop: Node;
  world: Node;
  hud: Node;
  top: Node;
  chrome: Node;
  camera: Camera;
  /** film time in seconds as a signal (for computed props that depend on time) */
  time: SimpleSignal<number>;
  /** background thread: run with `yield w.run()` */
  run: () => ThreadGenerator;
}

export function createWorld(view: View2D): World {
  setFilmThread(useThread()); // background() tasks live on the film's own thread
  const time = createSignal(0);
  // with a theme: one backdrop per chapter key light, cross-faded under each chapter card
  const keyCanvases = THEME ? CHAPTERS.map(c => makeBackdropCanvas(chapterKey(c.n))) : [];
  const bgCanvas = keyCanvases[0] ?? makeBackdropCanvas();
  const grainCanvas = makeGrainCanvas();

  const world = new Node({});
  const camera = new Camera(world, time);

  const backdrop = new Painter(ctx => {
    // parallax: the far layer moves at 18% of the camera's translation
    const o = camera.offset().scale(0.18);
    const x = Math.max(-MARGIN, Math.min(MARGIN, o.x));
    const y = Math.max(-MARGIN, Math.min(MARGIN, o.y));
    if (!keyCanvases.length) {
      ctx.drawImage(bgCanvas, -FRAME.w / 2 - MARGIN + x, -FRAME.h / 2 - MARGIN + y);
      return;
    }
    // chapter key lights: chapter n's light fades in over KEY_FADE s from chapter(n).start - 0.6 (under its card)
    const t = time();
    let i = 0;
    while (i + 1 < CHAPTERS.length && t >= CHAPTERS[i + 1].start - 0.6) i++;
    const k = i === 0 ? 1 : Math.min(1, (t - (CHAPTERS[i].start - 0.6)) / KEY_FADE);
    if (k < 1) ctx.drawImage(keyCanvases[i - 1], -FRAME.w / 2 - MARGIN + x, -FRAME.h / 2 - MARGIN + y);
    ctx.save();
    ctx.globalAlpha = k;
    ctx.drawImage(keyCanvases[i], -FRAME.w / 2 - MARGIN + x, -FRAME.h / 2 - MARGIN + y);
    ctx.restore();
  });

  // dark: darken towards black (original) or the theme's shadow; light: a gentle `deep` edge, never black
  const vig = LIGHT ? C.shade : C.shadow;
  const vignette = new Rect({
    width: FRAME.w,
    height: FRAME.h,
    fill: new Gradient({
      type: 'radial',
      from: [0, -40],
      to: [0, -40],
      fromRadius: THEME ? 640 : 380, // themes: clear further out (the vignette veils world-layer text, and the inks have less margin)
      toRadius: 1250,
      stops: [
        {offset: 0, color: rgba(vig, 0)},
        {offset: 0.65, color: rgba(vig, LIGHT ? 0.35 : 0.28)},
        {offset: 1, color: rgba(vig, LIGHT ? 0.85 : 0.72)},
      ],
    }),
  });

  const grain = new Painter(ctx => {
    // fixed in screen space: grain that changes every frame makes every frame
    // incompressible (60 Mbps instead of a few). Static grain reads as paper texture.
    const pat = ctx.createPattern(grainCanvas, 'repeat')!;
    ctx.save();
    ctx.translate(-FRAME.w / 2, -FRAME.h / 2);
    ctx.fillStyle = pat;
    // original: plain blend; a theme lightens a dark ground (screen) or darkens a light one (multiply), gently
    if (THEME) ctx.globalCompositeOperation = LIGHT ? 'multiply' : 'screen';
    ctx.globalAlpha = THEME ? (LIGHT ? 0.4 : 0.45) : 0.55;
    ctx.fillRect(0, 0, FRAME.w, FRAME.h);
    ctx.restore();
  });

  if (THEME) view.fill(C.bg); // the backdrop covers the stage; this only replaces project.meta's background
  const hud = new Node({});
  const top = new Node({});
  const chrome = new Node({});
  view.add(backdrop);
  view.add(world);
  view.add(vignette);
  view.add(hud);
  view.add(top);
  view.add(grain);
  view.add(chrome);

  return {
    view,
    backdrop,
    world,
    hud,
    top,
    chrome,
    camera,
    time,
    run: function* () {
      yield* time(TOTAL, TOTAL, linear);
    },
  };
}

/** Convert a node's position into another layer's local coordinates (e.g. a graph node into the top layer). */
export function posIn(layer: Node, node: Node): Vector2 {
  return node.absolutePosition().transformAsPoint(layer.worldToLocal());
}
/** Convert a point in `from`'s local coordinates into `layer`'s local coordinates. */
export function pointIn(layer: Node, from: Node, p: PossibleVector2): Vector2 {
  return new Vector2(p).transformAsPoint(from.localToWorld()).transformAsPoint(layer.worldToLocal());
}
