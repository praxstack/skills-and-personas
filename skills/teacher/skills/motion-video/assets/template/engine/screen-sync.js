// engine/screen-sync.js: loaded after main.js. Once the film is built, renderFrame also waits until the screen
// block's frame images have decoded, so a captured frame never shows the previous image; and window.FOOTAGE()
// reports where recorded footage is on the frame (capture.mjs writes it beside each still for legibility.py).
(function () {
  if (!window.READY) return;
  window.READY.then(() => {
    const draw = window.renderFrame;
    window.renderFrame = async (t) => { draw(t); if (window.M && M.screenFrames) await M.screenFrames(); };
    window.FOOTAGE = () => (window.M && M.footage ? M.footage() : { rects: [], keep: [] });
  }).catch(() => {});
})();
