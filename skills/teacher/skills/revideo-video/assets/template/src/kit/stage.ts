// The stage: backdrop with depth (light pool, parallax dot grid, dust, vignette), grain, a camera over the
// world, screen-space layers, the HUD, the caption band and the chapter cards. Build it once per film:
//
//   const st = setupStage(view, {kicker: 'LC 787'});
//   st.world.add(graph.root);     // the persistent subject lives in the world (the camera moves it)
//   st.fg.add(panel);             // screen-space panels (code, tables, question cards)
//   st.fx.add(...)                // bursts and flying copies, above everything but HUD/captions/cards
//   st.lower.add(lowerThird.root) // lower thirds: above the caption scrim (in fg the scrim darkened them to 3.7:1)
//   yield st.run();               // background: ticker, captions, chapter cards, HUD (spawn, don't wait)
import {Circle, Img, Node, Rect, Txt, View2D, Gradient} from '@revideo/2d';
import {
  all, createSignal, easeInOutCubic, easeOutCubic, SimpleSignal, ThreadGenerator, Vector2, waitFor,
} from '@revideo/core';
import {C, F, H, lightIndexOf, S, TEX, THEMED, W} from './theme';
import {CARD, CHAPTERS, clock, onFrame, resetFrameUpdaters, rng, ticker, TIMING} from './time';

// Grain: 0 = static (default). n > 0 = a new speck pattern every n frames: livelier, but the MP4 grows
// about 6x (measured: 3.3 Mbit/s static, 18 at n = 3, 23 at n = 1), because moving noise defeats H.264.
const GRAIN_HOLD = 0;
import {captionTrack, Captions} from './captions';
import {bgTex, dotsTex, grainTex, poolTex, tiledDots, vignetteTex} from './textures';
import {chapterCards, Hud} from './cards';

// ---------------------------------------------------------------- camera
/**
 * A camera over the world. focus(x, y) puts world point (x, y) at the centre of the frame; zoom scales.
 *   yield* st.cam.to({x: 200, y: -40, zoom: 1.25}, 1.2);   // push in on a node
 *   yield* st.cam.reset(1.0);                                 // pull back to the whole
 * A gentle drift (a few px, a fraction of a degree) runs all the time so holds never look frozen.
 */
export class Camera {
  readonly fx = createSignal(0);
  readonly fy = createSignal(0);
  readonly zoom = createSignal(1);
  readonly rot = createSignal(0);
  constructor(readonly node: Node) {
    node.scale(() => this.zoom());
    node.rotation(() => this.rot());
    node.position(() => {
      const r = (this.rot() * Math.PI) / 180, z = this.zoom(), x = -this.fx() * z, y = -this.fy() * z;
      return new Vector2(x * Math.cos(r) - y * Math.sin(r), x * Math.sin(r) + y * Math.cos(r));
    });
  }
  set(o: {x?: number; y?: number; zoom?: number; rot?: number}) {
    if (o.x !== undefined) this.fx(o.x);
    if (o.y !== undefined) this.fy(o.y);
    if (o.zoom !== undefined) this.zoom(o.zoom);
    if (o.rot !== undefined) this.rot(o.rot);
  }
  *to(o: {x?: number; y?: number; zoom?: number; rot?: number}, d = 1.2, ease = easeInOutCubic): ThreadGenerator {
    yield* all(
      o.x !== undefined ? this.fx(o.x, d, ease) : waitFor(0),
      o.y !== undefined ? this.fy(o.y, d, ease) : waitFor(0),
      o.zoom !== undefined ? this.zoom(o.zoom, d, ease) : waitFor(0),
      o.rot !== undefined ? this.rot(o.rot, d, ease) : waitFor(0),
    );
  }
  /** Push in on a world point. */
  push(x: number, y: number, zoom = 1.3, d = 1.2) {
    return this.to({x, y, zoom}, d);
  }
  reset(d = 1.0) {
    return this.to({x: 0, y: 0, zoom: 1, rot: 0}, d);
  }
}

// ---------------------------------------------------------------- stage
export interface Stage {
  view: View2D;
  backdrop: Node;
  /** The light pool (a theme: one image per chapter key light inside this node, shown one at a time). */
  pool: Node;
  drift: Node;
  camNode: Node;
  world: Node;
  fg: Node;
  fx: Node;
  /** Screen-space layer above the world and panels (no drift): flying copies land here. */
  top: Node;
  hud: Hud;
  captions: Captions;
  /** Lower thirds: screen space, above the caption scrim and below the caption text. */
  lower: Node;
  cards: Node;
  cam: Camera;
  /** Background work: ticker, captions, chapter cards, HUD. `yield st.run()` (no star) at the top. */
  run: () => ThreadGenerator;
  /** Screen position (view space, centre origin) of a node anywhere in the tree. */
  screenPos: (n: Node) => Vector2;
}

export interface StageOptions {
  kicker?: string;          // short tag at the top left, e.g. 'LC 787'
  title?: string;           // defaults to TIMING.title
  captions?: boolean;       // default true
  chapterCards?: boolean;   // default true
  drift?: number;           // drift amplitude in px (default 7)
}

export function setupStage(view: View2D, o: StageOptions = {}): Stage {
  // the scene function runs several times per render (reset/seek); start the ticker list empty each time
  resetFrameUpdaters();
  view.fill(C.bg);
  // design space is 1920x1080; scale it to the timing's size (e.g. 1280x720 drafts)
  const root = new Node({scale: TIMING.width / W});
  view.add(root);

  // ---- backdrop: gradient, light pool, parallax dot grid, dust motes
  const backdrop = new Node({});
  root.add(backdrop);
  backdrop.add(new Img({src: bgTex(W, H, C.bgWarm, C.bgMid, C.bgEdge), width: W, height: H}));
  // the light pool lags the camera (parallax); positions are rounded so the texture is drawn 1:1 (fast)
  let pool: Node;
  if (!THEMED) {
    pool = new Img({src: poolTex(1500), width: 1500, height: 1500, opacity: 0.9});
  } else {
    // a theme: the pool takes the chapter's key light (theme `lights`), switched while the chapter card covers
    // the frame; hidden images (opacity 0) are not drawn, so this costs no more than one pool
    pool = new Node({});
    const imgs = TEX.poolRgb.map(rgb => new Img({src: poolTex(1500, rgb), width: 1500, height: 1500, opacity: 0}));
    imgs.forEach(i => pool.add(i));
    const starts = CHAPTERS.filter(c => c.n > 0 && CARD[c.n]).map(c => [CARD[c.n].coveredAt, c.n] as [number, number]);
    onFrame(() => {
      const t = clock();
      let n = 0;
      for (const [at, cn] of starts) if (t >= at) n = cn;
      const k = lightIndexOf(n);
      imgs.forEach((im, i) => im.opacity(i === k ? 0.9 : 0));
    });
  }
  backdrop.add(pool);
  const grid = new Node({});
  backdrop.add(grid);
  // dot grid: one tiled image row/column set, moved with a parallax factor of the camera
  const dots = dotsTex();
  const tile = 64;
  grid.add(new Img({src: tiledDots(dots, 40, 23), width: 40 * tile, height: 23 * tile, opacity: TEX.dotsOpacity}));
  const motes = new Node({});
  backdrop.add(motes);
  // the vignette darkens the backdrop only: drawn over the corners of the frame, it took a lower third or a
  // HUD chip from 6:1 down to 2:1, so every layer with text sits above it
  backdrop.add(new Img({src: vignetteTex(W, H), width: W, height: H}));
  const mr = rng(11);
  for (let i = 0; i < 34; i++) {
    const x0 = (mr() - 0.5) * W, y0 = (mr() - 0.5) * H, sp = 6 + mr() * 14, ph = mr() * 10, sz = 2 + mr() * 3.5;
    const m = new Circle({size: sz, fill: i % 5 === 0 ? C.acc : C.ink, opacity: 0.08 + mr() * 0.18});
    m.position(() => {
      const t = clock();
      const y = ((y0 - t * sp + H / 2) % H + H) % H - H / 2;
      return new Vector2(x0 + Math.sin(t * 0.4 + ph) * 14, y);
    });
    motes.add(m);
  }

  // ---- drift > camera > world ; fg and fx drift too (so the whole frame breathes)
  const amp = o.drift ?? 7;
  const drift = new Node({});
  drift.position(() => new Vector2(Math.sin(clock() * 0.23) * amp, Math.cos(clock() * 0.19) * amp * 0.7));
  root.add(drift);
  const camNode = new Node({});
  drift.add(camNode);
  const world = new Node({});
  camNode.add(world);
  const cam = new Camera(camNode);
  const fg = new Node({});
  drift.add(fg);
  const fx = new Node({});
  drift.add(fx);
  // parallax: the grid and the light pool lag the camera
  grid.position(() => new Vector2(Math.round(-cam.fx() * 0.18), Math.round(-cam.fy() * 0.18)));
  pool.position(() => new Vector2(Math.round(-cam.fx() * 0.45 + Math.sin(clock() * 0.3) * 30), Math.round(-60 - cam.fy() * 0.45)));

  const top = new Node({});
  root.add(top);

  // ---- overlay: grain (static unless GRAIN_HOLD > 0); the vignette is part of the backdrop (above)
  const overlay = new Node({});
  root.add(overlay);
  // film grain: one speck texture drawn 1:1 at a whole-pixel offset (cheap); see GRAIN_HOLD for animating it
  const grain = new Img({src: grainTex(2048, 1152), width: 2048, height: 1152, opacity: TEX.grainOpacity});
  overlay.add(grain);
  if (GRAIN_HOLD > 0) onFrame(() => {
    const r = rng(Math.floor(clock() * TIMING.fps / GRAIN_HOLD + 1e-6) * 7919 + 13);
    grain.position([Math.round((r() - 0.5) * 120), Math.round((r() - 0.5) * 70)]);
  });

  // ---- HUD, captions, cards (screen space, above everything)
  const hud = new Hud(root, {kicker: o.kicker ?? '', title: o.title ?? TIMING.title});
  const captions = new Captions(root);
  const cards = new Node({});
  root.add(cards);

  const screenPos = (n: Node) => {
    const p = n.absolutePosition();
    const s = TIMING.width / W;
    return new Vector2((p.x - TIMING.width / 2) / s, (p.y - TIMING.height / 2) / s);
  };

  const st: Stage = {view, backdrop, pool, drift, camNode, world, fg, fx, top, hud, captions, lower: captions.lower, cards, cam, screenPos,
    run: null as any};
  st.run = function* () {
    yield* all(
      ticker(),
      o.captions === false ? waitFor(0) : captionTrack(captions),
      hud.track(),
      o.chapterCards === false ? waitFor(0) : chapterCards(st),
    );
  };
  return st;
}
