// Textures drawn once into an offscreen canvas (deterministic, no downloads): backdrop, light pool, vignette,
// grain, dot grid, halftone.
//
// Speed: Revideo renders on the CPU here. A full-frame gradient costs ~20-25 ms per frame and an image drawn
// scaled or at a fractional offset ~20-30 ms, but an image drawn 1:1 at a whole-pixel offset only ~4-8 ms.
// So every full-frame layer is baked once into a texture and drawn unscaled at integer positions
// (kit/stage.ts rounds the moving ones). This roughly doubled the render speed.
import {rng} from './time';
import {C, TEX} from './theme';

function texture(w: number, h: number, draw: (ctx: CanvasRenderingContext2D) => void) {
  const cv = document.createElement('canvas');
  cv.width = w;
  cv.height = h;
  draw(cv.getContext('2d')!);
  return cv.toDataURL('image/png');
}
let _grain: string, _dots: string, _halftone: string, _bg: string, _vig: string, _scrim: string;
const _pool: Record<string, string> = {};
/** Backdrop: warm near-black radial gradient (a theme: its bg/bg2), centre slightly above the middle. */
export const bgTex = (w = 1920, h = 1080, warm = C.bgWarm, mid = C.bgMid, edge = C.bgEdge) => (_bg ??= texture(w, h, ctx => {
  const g = ctx.createRadialGradient(w / 2, h / 2 - 140, 0, w / 2, h / 2 - 140, 1300);
  g.addColorStop(0, warm);
  g.addColorStop(0.55, mid);
  g.addColorStop(1, edge);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}));
/** Vignette: transparent centre, dark corners (a theme: toward its `deep`; on light grounds a gentle edge). */
export const vignetteTex = (w = 1920, h = 1080, strength = TEX.vignette) => (_vig ??= texture(w, h, ctx => {
  const g = ctx.createRadialGradient(w / 2, h / 2, 380, w / 2, h / 2, 1180);
  g.addColorStop(0, `rgba(${TEX.vignetteRgb},0)`);
  g.addColorStop(1, `rgba(${TEX.vignetteRgb},${strength})`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}));
/** Caption scrim: transparent at the top, dark at the bottom (keeps captions readable over anything). */
export const scrimTex = (w = 1920, h = 300) => (_scrim ??= texture(w, h, ctx => {
  const g = ctx.createLinearGradient(0, 0, 0, h);
  g.addColorStop(0, `rgba(${TEX.scrimRgb},0)`);
  g.addColorStop(0.55, `rgba(${TEX.scrimRgb},${TEX.scrimAlpha[0]})`);
  g.addColorStop(1, `rgba(${TEX.scrimRgb},${TEX.scrimAlpha[1]})`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, w, h);
}));
/** Light pool: a soft accent-coloured glow (rgb as 'r,g,b'; a theme: one per chapter key light, fainter on light grounds). */
export const poolTex = (size = 1500, rgb = TEX.poolRgb[0]) => (_pool[`${size}|${rgb}`] ??= texture(size, size, ctx => {
  const r = size / 2;
  const g = ctx.createRadialGradient(r, r, 0, r, r, r);
  g.addColorStop(0, `rgba(${rgb},${TEX.poolAlpha[0]})`);
  g.addColorStop(0.5, `rgba(${rgb},${TEX.poolAlpha[1]})`);
  g.addColorStop(1, `rgba(${rgb},0)`);
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, size, size);
}));
/**
 * Film grain as sparse light and dark specks with their own alpha, full resolution (drawn 1:1, plain alpha
 * blending). An opaque noise image with compositeOperation 'overlay', scaled up, looks similar but is ~7x slower.
 * On a light theme only the dark specks are drawn (tinted with the theme's shadow): a multiply-like grain.
 */
const GRAIN_DARK = TEX.grainRgb.split(',').map(Number);
export const grainTex = (w = 2048, h = 1152) => (_grain ??= texture(w, h, ctx => {
  const r = rng(7);
  const img = ctx.createImageData(w, h);
  for (let i = 0; i < img.data.length; i += 4) {
    const u = r();
    if (u < 0.55) continue; // transparent
    const light = u > 0.775;
    if (light && !TEX.grainLight) continue;
    if (light) img.data[i] = img.data[i + 1] = img.data[i + 2] = 255;
    else [img.data[i], img.data[i + 1], img.data[i + 2]] = GRAIN_DARK;
    img.data[i + 3] = Math.round((light ? 9 : 14) + r() * 20);
  }
  ctx.putImageData(img, 0, 0);
}));
export const dotsTex = () => (_dots ??= texture(64, 64, ctx => {
  ctx.fillStyle = `rgba(${TEX.dotRgb},0.9)`;
  ctx.beginPath();
  ctx.arc(32, 32, 1.6, 0, Math.PI * 2);
  ctx.fill();
}));
/** Comic halftone dots (used on chapter cards). */
export const halftoneTex = () => (_halftone ??= texture(1200, 700, ctx => {
  for (let y = 0; y < 700; y += 18) {
    for (let x = 0; x < 1200; x += 18) {
      const k = Math.max(0, 1 - Math.hypot(x - 1200, y - 700) / 1100);
      const rad = 7.5 * k;
      if (rad < 0.4) continue;
      ctx.fillStyle = C.halftone;
      ctx.beginPath();
      ctx.arc(x + (y % 36 ? 9 : 0), y, rad, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}));

/** A big transparent image with a dot every 64 px (cheaper than thousands of Circle nodes). */
const _tiled: Record<string, string> = {};
export function tiledDots(_src: string, cols: number, rows: number) {
  const k = `${cols}x${rows}`;
  return (_tiled[k] ??= texture(cols * 64, rows * 64, ctx => {
    ctx.fillStyle = `rgba(${TEX.dotRgb},1)`;
    for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
      ctx.beginPath();
      ctx.arc(x * 64 + 32, y * 64 + 32, 1.7, 0, Math.PI * 2);
      ctx.fill();
    }
  }));
}

