// main.js: the page contract for scripts/capture.mjs, and nothing film-specific.
//   window.READY            resolves when fonts are loaded, the scene is built and shaders are compiled
//   window.TOTAL            film length = TIMING.total (from src/timing.js, written by voice.py)
//   window.renderFrame(t)   draws the exact frame for time t: seek the timeline, apply every kit object, render
// No CAPTURE_SELECTOR: capture.mjs takes page screenshots so the DOM text overlay is in every frame.
// Preview in a browser (no server needed): open index.html?preview (or ?preview&t=40). Space plays/pauses,
// arrows step one frame, shift+arrows 5 s, Home/End jump. On a laptop GPU this plays in real time.
import { TOTAL } from './kit/time.js';
import { createStage } from './kit/stage.js';
import { createOverlay } from './kit/overlay.js';
import css from './kit/film.css';
import { C, FX, FONT, THEME_ID, TONE, inkOf, strokeOf, plateOf } from './kit/style.js';
import { buildFilm } from './film.js';

import interRegular from 'inter-ui/web/Inter-Regular.woff2';
import interSemi from 'inter-ui/web/Inter-SemiBold.woff2';
import interBold from 'inter-ui/web/Inter-Bold.woff2';
import interExtra from 'inter-ui/web/Inter-ExtraBold.woff2';
import monoMedium from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-Medium.woff2';
import monoBold from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-Bold.woff2';
import bangers from '@fontsource/bangers/files/bangers-latin-400-normal.woff2';

const NOLIG = '"calt" 0, "liga" 0'; // belt and braces: the NL cut has no ligatures, and this turns them off anyway
const FACES = [
  ['Inter Film', interRegular, { weight: '400' }], ['Inter Film', interSemi, { weight: '600' }],
  ['Inter Film', interBold, { weight: '700' }], ['Inter Film', interExtra, { weight: '800' }],
  ['JetBrains Mono NL', monoMedium, { weight: '500', featureSettings: NOLIG }],
  ['JetBrains Mono NL', monoBold, { weight: '700', featureSettings: NOLIG }],
  ['Bangers', bangers, { weight: '400' }],
];

async function loadFonts() {
  await Promise.all(FACES.map(async ([family, url, desc]) => {
    const f = new FontFace(family, `url(${url})`, desc);
    await f.load(); document.fonts.add(f);
  }));
  await document.fonts.ready;
}

function cssVars() {
  const r = document.documentElement.style;
  const set = (k, v) => r.setProperty(k, v);
  set('--f-ui', FONT.ui); set('--f-mono', FONT.mono); set('--f-comic', FONT.comic);
  set('--ink', C.ink); set('--ink-soft', C.inkSoft); set('--ink-faint', C.inkFaint); set('--comment', C.comment); set('--panel', C.panel); set('--panel-line', C.panelLine);
  set('--outline', C.outline); set('--hot', C.hot); set('--good', C.good); set('--bad', C.bad); set('--cool', C.cool); set('--gold', C.gold); set('--token', C.token);
  // every other overlay colour (film.css holds none): grounds, shadows, inks in a hue, text on fills, syntax
  set('--page', C.page); set('--vig0', C.vignette[0]); set('--vig1', C.vignette[1]); set('--fade0', C.bottomFade[0]); set('--fade1', C.bottomFade[1]);
  set('--badge', C.badge); set('--badge-line', C.badgeLine); set('--wtag', C.wtag); set('--wtag-ink', C.wtagInk); set('--cap', C.cap);
  C.shadow.forEach((v, i) => set(`--sh${i + 1}`, v));
  set('--halftone', C.halftone); set('--halo1', C.halo[0]); set('--halo2', C.halo[1]);
  set('--code-bg', C.codeBg); set('--code-bar', C.codeBar); set('--code-hl', C.codeHl);
  for (const [k, v] of Object.entries(C.syntax)) set(`--syn-${k}`, v);
  set('--cell', C.cell); set('--cell-line', C.cellLine); set('--rung', C.rung);
  set('--gold-ink', inkOf(C.gold)); set('--good-ink', inkOf(C.good)); set('--token-ink', inkOf(C.token));
  set('--on-hot', C.onHot); set('--on-gold', C.onGold); set('--on-good', C.onGood);
  set('--band-ink', C.bandInk); set('--band-num', C.bandNum); set('--band-stroke', strokeOf(C.bandInk));
  set('--plate-hot', plateOf(C.hot)); set('--plate-gold', plateOf(C.gold)); set('--plate-good', plateOf(C.good));
  set('--title-shadow', C.titleShadow); set('--title-stroke', strokeOf(C.ink)); set('--title-stroke2', strokeOf(C.titleInk2));
  set('--title-ink2', C.titleInk2); set('--title-sub', C.titleSub);
  set('--stamp-pad', FX.stampPad);
  document.documentElement.dataset.theme = THEME_ID; document.documentElement.dataset.tone = TONE;
}

async function init() {
  cssVars();
  await loadFonts();
  const stage = createStage();
  const ui = createOverlay(stage, css);
  const film = buildFilm({ stage, ui });
  const renderFrame = (t) => {
    t = Math.max(0, Math.min(t, TOTAL - 1e-3));
    film.tl.seek(t);
    stage.apply(t);                                   // theme: the key light follows the chapter
    for (const thing of film.things) thing.apply(t); // camera first (labels project through it), then the 3D actors
    ui.apply(t);
    stage.render();
  };
  renderFrame(0);
  stage.warmup();
  window.renderFrame = renderFrame;
  window.STAGE = stage; window.FILM = film; // handy in the browser console
  const q = new URLSearchParams(location.search);
  if (q.has('preview')) preview(renderFrame, +(q.get('t') || 0));
}

// preview only (never used by capture.mjs, which drives renderFrame itself)
function preview(renderFrame, t0) {
  let t = t0, playing = false, last = 0;
  const hud = document.createElement('div');
  hud.style.cssText = 'position:fixed;left:8px;top:8px;z-index:9;font:600 14px monospace;color:#fff;background:#0008;padding:4px 8px;border-radius:6px';
  document.body.appendChild(hud);
  const show = () => { t = Math.max(0, Math.min(t, TOTAL)); renderFrame(t); hud.textContent = `${t.toFixed(2)} / ${TOTAL.toFixed(2)} s  ${playing ? '▶' : '❚❚'}  space, arrows`; };
  const loop = (now) => { if (!playing) return; if (last) t += (now - last) / 1000; last = now; if (t >= TOTAL) playing = false; show(); requestAnimationFrame(loop); };
  addEventListener('keydown', (e) => {
    const step = e.shiftKey ? 5 : 1 / 30;
    if (e.key === ' ') { playing = !playing; last = 0; if (playing) requestAnimationFrame(loop); }
    else if (e.key === 'ArrowRight') t += step; else if (e.key === 'ArrowLeft') t -= step;
    else if (e.key === 'Home') t = 0; else if (e.key === 'End') t = TOTAL - 0.01; else return;
    e.preventDefault(); show();
  });
  show();
}

window.TOTAL = TOTAL;
window.READY = init().catch((e) => {
  console.error(e);
  const pre = document.createElement('pre'); // textContent: the stack can quote narration text, which is data, not markup
  pre.style.cssText = 'color:#f66;position:absolute;top:0;left:0;font:20px monospace;white-space:pre-wrap;z-index:9';
  pre.textContent = String(e.stack || e);
  document.body.appendChild(pre);
  throw e;
});
