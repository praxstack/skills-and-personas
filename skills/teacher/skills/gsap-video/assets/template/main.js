// main.js: boot the film and expose the page contract that capture.mjs drives. You rarely edit this file.
//   window.READY          resolves once fonts are loaded and the timeline is built
//   window.TOTAL          film length in seconds (= TIMING.total, the voice's length)
//   window.renderFrame(t) draws the exact frame for time t: master.seek(t) + the per-frame ambient layer
// Open index.html in a browser for a preview with a scrubber (and the narration, if ../voice/narration.wav exists);
// capture.mjs adds ?render=1, which hides the preview controls.
(function () {
  const params = new URLSearchParams(location.search);
  const RENDER = params.has('render');
  window.TOTAL = window.TIMING ? window.TIMING.total : 0;
  const fail = (e) => {
    const box = document.getElementById('err') || Object.assign(document.createElement('div'), { id: 'err' });
    box.textContent = `Film failed to build:\n${e && e.stack ? e.stack : e}`;
    document.body.appendChild(box);
    console.error('film build failed:', e && e.stack ? e.stack : e);
  };
  const FONTS = ['400 30px Inter', '600 30px Inter', '800 30px Inter', '900 90px Inter', '400 30px "JetBrains Mono"',
    '600 30px "JetBrains Mono"', '700 30px "JetBrains Mono"', '400 60px Bangers'];

  window.READY = (async () => {
    try {
      if (window.BOOT_ERROR) throw new Error(window.BOOT_ERROR);
      await Promise.all(FONTS.map((f) => document.fonts.load(f, '0Aa→∞≤')));
      await document.fonts.ready;
      const K = window.K;
      K.buildStage();
      window.Film.build(K);          // scenes.js: every tween placed at a TIMING line's time
      K.finalize();                  // components that collect events (code focus, table cells) emit tweens
      K.tl.set({}, {}, K.TOTAL);     // pad the master timeline to exactly the voice length
      if (K.tl.duration() > K.TOTAL + 0.001)
        K.warnings.push(`timeline runs ${K.tl.duration().toFixed(2)} s, past TIMING.total ${K.TOTAL.toFixed(2)} s: the render stops at TOTAL`);
      window.renderFrame = (t) => { K.tl.seek(t, false); K.ambient(t); };
      window.renderFrame(0);
      if (K.warnings.length) console.warn(`${K.warnings.length} timeline warnings:\n` + K.warnings.join('\n'));
      if (!RENDER) preview(K);
      return true;
    } catch (e) {
      fail(e);
      throw e;
    }
  })();
  // capture.mjs waits for this to exist; it only runs after READY resolved
  window.renderFrame = async (t) => { await window.READY; window.renderFrame(t); };

  function preview(K) {
    const fit = () => {
      const s = Math.min(innerWidth / K.W, (innerHeight - 64) / K.H);
      Object.assign(document.documentElement.style, { width: '100%', height: '100%' });
      Object.assign(document.body.style, { width: '100%', height: '100%', background: TOKENS.chrome.letterbox });
      Object.assign(K.stageEl.style, { transform: `scale(${s})`, transformOrigin: '0 0' });
    };
    fit();
    addEventListener('resize', fit);
    const bar = Object.assign(document.createElement('div'), { id: 'preview' });
    bar.innerHTML = `<button id="pp">play</button><input type="range" min="0" max="${K.TOTAL}" step="0.0333" value="0"><span class="t"></span>`;
    document.body.appendChild(bar);
    const [btn, range, label] = [bar.querySelector('#pp'), bar.querySelector('input'), bar.querySelector('.t')];
    const audio = new Audio('../voice/narration.wav');
    let playing = false, t0 = 0, w0 = 0;
    const show = (t) => {
      window.renderFrame(t);
      range.value = t;
      const l = K.lines.find((x) => t >= x.start && t < x.end);
      label.textContent = `${t.toFixed(2)} / ${K.TOTAL.toFixed(2)}  ${l ? l.id : ''}`;
    };
    const tick = () => {
      if (!playing) return;
      const t = w0 + (performance.now() - t0) / 1000;
      if (t >= K.TOTAL) { playing = false; btn.textContent = 'play'; show(K.TOTAL); return; }
      show(t);
      requestAnimationFrame(tick);
    };
    btn.onclick = () => {
      playing = !playing;
      btn.textContent = playing ? 'pause' : 'play';
      if (playing) { w0 = +range.value; t0 = performance.now(); audio.currentTime = w0; audio.play().catch(() => {}); tick(); } else audio.pause();
    };
    range.oninput = () => { playing = false; btn.textContent = 'play'; audio.pause(); show(+range.value); };
    addEventListener('keydown', (e) => {
      if (e.key === ' ') { e.preventDefault(); btn.click(); }
      if (e.key === 'ArrowRight') { range.value = Math.min(K.TOTAL, +range.value + (e.shiftKey ? 5 : 1 / 30)); range.oninput(); }
      if (e.key === 'ArrowLeft') { range.value = Math.max(0, +range.value - (e.shiftKey ? 5 : 1 / 30)); range.oninput(); }
    });
    show(+(params.get('t') || 0));
  }
})();
