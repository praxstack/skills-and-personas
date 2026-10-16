// main.js: load film.json (and its datasets), build the clip, and expose the page contract capture.mjs drives.
//   window.READY          resolves once fonts, film.json and data are loaded and the timeline is built
//   window.TOTAL          clip length in seconds (= TIMING.total, the voice's length)
//   window.renderFrame(t) draws the exact frame for time t
//   window.MOTION         {film, rebuild(film), warnings, errors, events, shots}: the editor and motion_check use it;
//                         film is film.json as read, even when it fails to build (the editor opens it to fix it)
// Serve the project folder (python3 -m http.server 8000) and open /source/index.html for a preview with a scrubber
// and the narration (../voice/narration.wav); /source/editor.html is the same clip with every prop editable.
// capture.mjs adds ?render=1 (no controls).
(function () {
  const params = new URLSearchParams(location.search);
  const RENDER = params.has('render'), EMBED = params.has('embed');
  window.TOTAL = window.TIMING ? window.TIMING.total : 0;
  const fail = (e) => {
    const box = document.getElementById('err') || Object.assign(document.createElement('div'), { id: 'err' });
    box.textContent = `The clip failed to build:\n\n${e && e.message ? e.message : e}`;
    document.body.appendChild(box);
    console.error('clip build failed:', e && e.stack ? e.stack : e);
  };
  const FONTS = ['400 30px Inter', '650 30px Inter', '760 90px Inter', '560 60px Fraunces', 'italic 560 60px Fraunces',
    '400 30px "JetBrains Mono"', '600 30px "JetBrains Mono"'];
  let current = 0;
  const draw = (t) => { current = t; M.tl.seek(t, false); M.ambient(t); };
  window.MOTION = {
    film: null,
    /** Rebuild from an edited film object (the editor calls this); returns {ok, errors, warnings}. */
    async rebuild(film) {
      try {
        await M.data.load(film.data || {});
        M.build(film);
        window.MOTION.film = film;
        window.renderFrame = draw;   // a film that failed to build at load can be repaired in the editor
        draw(current);
        return { ok: true, errors: [], warnings: M.warnings.slice() };
      } catch (e) {
        return { ok: false, errors: String(e.message || e).split('\n'), warnings: (M.warnings || []).slice() };
      }
    },
    get warnings() { return M.warnings; }, get errors() { return M.errors; }, get events() { return M.events; }, get shots() { return M.shots; },
  };

  window.READY = (async () => {
    try {
      if (window.BOOT_ERROR) throw new Error(window.BOOT_ERROR);
      await Promise.all(FONTS.map((f) => document.fonts.load(f, '0Aa→∞≤✓')));
      await document.fonts.ready;
      const r = await fetch('film.json', { cache: 'no-store' }).catch(() => null);
      if (!r || !r.ok) throw new Error('film.json could not be read. Preview through a local server (python3 -m http.server), not file://');
      const film = await r.json();
      window.MOTION.film = film;
      await M.data.load(film.data || {});
      M.build(film);
      window.renderFrame = draw;
      draw(+(params.get('t') || 0));
      if (M.warnings.length) console.warn(`${M.warnings.length} warnings:\n` + M.warnings.join('\n'));
      if (!RENDER && !EMBED) preview();
      return true;
    } catch (e) {
      fail(e);
      throw e;
    }
  })();
  // capture.mjs waits for this to exist; it only runs after READY resolved
  window.renderFrame = async (t) => { await window.READY; window.renderFrame(t); };

  function preview() {
    const stage = document.getElementById('stage');
    const fit = () => {
      const s = Math.min(innerWidth / M.W, (innerHeight - 64) / M.H);
      Object.assign(stage.style, { transform: `scale(${s})`, transformOrigin: '0 0' });
    };
    fit();
    addEventListener('resize', fit);
    const bar = Object.assign(document.createElement('div'), { id: 'preview' });
    bar.innerHTML = `<button id="pp">play</button><input type="range" min="0" max="${M.TOTAL}" step="0.0333" value="0"><span class="t"></span><a href="editor.html" style="color:#9cf">editor</a>`;
    document.body.appendChild(bar);
    const [btn, range, label] = [bar.querySelector('#pp'), bar.querySelector('input'), bar.querySelector('.t')];
    const audio = new Audio('../voice/narration.wav');
    let playing = false, t0 = 0, w0 = 0;
    const show = (t) => {
      draw(t);
      range.value = t;
      const l = M.lineAt(t);
      label.textContent = `${t.toFixed(2)} / ${M.TOTAL.toFixed(2)}  ${l ? l.id : ''}`;
    };
    const tick = () => {
      if (!playing) return;
      const t = w0 + (performance.now() - t0) / 1000;
      if (t >= M.TOTAL) { playing = false; btn.textContent = 'play'; show(M.TOTAL); return; }
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
      if (e.key === 'ArrowRight') { range.value = Math.min(M.TOTAL, +range.value + (e.shiftKey ? 5 : 1 / 30)); range.oninput(); }
      if (e.key === 'ArrowLeft') { range.value = Math.max(0, +range.value - (e.shiftKey ? 5 : 1 / 30)); range.oninput(); }
    });
    show(+(params.get('t') || 0));
  }
})();
