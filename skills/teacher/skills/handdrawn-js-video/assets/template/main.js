// main.js: boot, the frame function, and the page contract for capture.mjs. You rarely need to edit this file.
//   window.READY            resolves once fonts, textures and the film are built
//   window.TOTAL            film length in seconds (= TIMING.total, exactly)
//   window.renderFrame(t)   draws the frame for time t, from scratch (pure function of t)
//   window.CAPTURE_SELECTOR '#c' -> capture.mjs grabs the canvas with toDataURL (fast)
// Opened without ?render (python3 -m http.server in the project folder, then /source/index.html) it plays as a
// preview: click to start with the narration, space = pause, left/right = -/+ 2 s, number keys jump to chapters.
'use strict';
const CANVAS = document.getElementById('c'), CTX = CANVAS.getContext('2d');
CANVAS.width = TIMING_.width || W; CANVAS.height = TIMING_.height || H;
window.TOTAL = TIMING_.total;
window.CAPTURE_SELECTOR = '#c';

function drawFrame(ctx, t) {
  ctx.setTransform(CANVAS.width / W, 0, 0, CANVAS.height / H, 0, 0);
  ctx.globalAlpha = 1; ctx.globalCompositeOperation = 'source-over';
  if (STYLE.beginFrame) STYLE.beginFrame(t);
  const cam = camAt(t), still = camAt(t, false); // backdrop + scenery skip the drift (see camAt)
  drawBackdrop(ctx, S.backDepth ? cam : still);   // a style with backDepth (whiteboard: 1) locks the board to the world
  for (const l of LAYERS.back) { ctx.save(); applyCam(ctx, still, l.depth); l.draw(ctx, t); ctx.restore(); }
  ctx.save(); applyCam(ctx, cam, 1);
  for (const l of LAYERS.world) l.draw(ctx, t);
  ctx.restore();
  for (const l of LAYERS.screen) l.draw(ctx, t);
  drawOverlay(ctx, t);
}

window.READY = (async () => {
  await loadFonts();
  initTextures();
  buildFilm(); // scenes.js
  const silent = TIMING_.lines.map((l) => l.id).filter((id) => !USED_IDS.has(id));
  if (silent.length) console.error(`scenes.js never uses these line ids (every line should change something on screen): ${silent.join(', ')}`);
  return true;
})();
window.renderFrame = (t) => drawFrame(CTX, Math.max(0, Math.min(t, TIMING_.total)));

// ------------------------------------------------------------------ preview player (not used when rendering)
if (!/render/.test(location.search)) {
  window.READY.then(() => {
    const q = new URLSearchParams(location.search);
    let t0 = performance.now() / 1000 - (+q.get('t') || 0), paused = false, pausedAt = 0;
    const audio = new Audio(q.get('audio') || '../voice/narration.wav'); let started = false;
    const now = () => (paused ? pausedAt : performance.now() / 1000 - t0);
    const seek = (t) => { t = Math.max(0, Math.min(TIMING_.total, t)); t0 = performance.now() / 1000 - t; pausedAt = t; if (started) audio.currentTime = t; };
    CANVAS.onclick = () => { if (!started) { started = true; audio.currentTime = now(); audio.play().catch(() => {}); } };
    addEventListener('keydown', (e) => {
      if (e.key === ' ') { paused = !paused; if (paused) { pausedAt = now(); audio.pause(); } else { seek(pausedAt); if (started) audio.play(); } }
      if (e.key === 'ArrowRight') seek(now() + 2); if (e.key === 'ArrowLeft') seek(now() - 2);
      const ch = TIMING_.chapters.find((c) => String(c.n) === e.key); if (ch) seek(ch.start - 0.8);
    });
    const hud = document.getElementById('hud');
    const loop = () => { const t = now() % TIMING_.total; drawFrame(CTX, t); if (hud) { const l = lineAt(t); hud.textContent = `${t.toFixed(2)} s  ${l ? l.id : ''}`; } requestAnimationFrame(loop); };
    loop();
  });
}
