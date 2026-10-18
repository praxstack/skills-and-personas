// In-page helpers that drive and read the IVE (verify/visual.py ive_gates and tests/test_ive.mjs).
// Evaluated as one expression; defines window.__iveDrive.
(() => {
  const v = () => document.getElementById('v');
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const once = (el, ev, ms) => new Promise((r) => { const t = setTimeout(() => r(false), ms || 5000); el.addEventListener(ev, () => { clearTimeout(t); r(true); }, { once: true }); });
  const state = () => {
    const s = document.getElementById('state'), xp = document.getElementById('xp');
    return { t: v().currentTime, paused: v().paused, mode: window.__ptkIve.mode(), origin: xp.dataset.origin,
             state: s.dataset.state || null, cue: s.dataset.cue || null, kind: s.dataset.kind || null,
             edit: s.dataset.edit || null, program: s.dataset.program || null,
             output: [...s.querySelectorAll('.out .val')].map((e) => e.textContent),
             origin_text: document.getElementById('origin').textContent,
             border: getComputedStyle(xp).borderTopStyle };
  };
  // a frame is on screen once the seek has finished and the element has decoded data
  const frame = async () => {
    const el = v();
    for (let i = 0; i < 100 && (el.seeking || el.readyState < 3); i++) await sleep(30);
    if (el.requestVideoFrameCallback) await Promise.race([new Promise((r) => el.requestVideoFrameCallback(() => r())), sleep(800)]);
    await sleep(60);
  };
  // before a screenshot: the frame is on screen and Chrome's media-controls loading spinner, which fades out
  // over about a second after any seek (measured: still visible at 0.9 s, gone by 1.2 s), has cleared
  const settled = async () => { await frame(); await sleep(1500); };
  const seek = async (t) => {
    const el = v(), p = once(el, 'seeked');
    el.currentTime = t;
    await p; await sleep(40);
    return state();
  };
  const leak = (words) => {
    const root = document.body.cloneNode(true);
    root.querySelectorAll('noscript, script, [data-code], video, track').forEach((e) => e.remove());
    const texts = [root.textContent];
    document.querySelectorAll('[alt], [aria-label], [title]').forEach((e) => {
      if (e.closest('noscript')) return;
      ['alt', 'aria-label', 'title'].forEach((a) => e.getAttribute(a) && texts.push(e.getAttribute(a)));
    });
    const found = new Set(texts.join(' ').toLowerCase().match(/[a-z']+/g) || []);
    return { hits: words.filter((w) => found.has(w)), transcript_items: document.querySelectorAll('#tx li').length, ...state() };
  };
  // D20.3 in any state: no page overflow, key nodes inside the viewport with no inner scroll
  const layout = () => {
    const problems = [], iw = window.innerWidth;
    if (document.documentElement.scrollWidth > iw + 1) problems.push({ kind: 'page-overflow', scrollWidth: document.documentElement.scrollWidth, innerWidth: iw });
    for (const e of document.querySelectorAll('[data-key]')) {
      const r = e.getBoundingClientRect();
      if (r.left < -1 || r.right > iw + 1) problems.push({ kind: 'key-node-offscreen', key: e.dataset.key });
      if (e.scrollWidth > e.clientWidth + 1 || e.scrollHeight > e.clientHeight + 1) problems.push({ kind: 'key-node-inner-scroll', key: e.dataset.key });
    }
    // captions sit in their own band: below the film, never over it or its controls, holding every line it shows
    const band = document.getElementById('capband'), vr = v().getBoundingClientRect();
    if (band) {
      const b = band.getBoundingClientRect();
      if (b.top < vr.bottom - 0.5 && b.bottom > vr.top + 0.5 && b.right > vr.left && b.left < vr.right)
        problems.push({ kind: 'captions-over-film', band: [b.top, b.bottom].map(Math.round), film: [vr.top, vr.bottom].map(Math.round) });
      if (band.scrollHeight > band.clientHeight + 1) problems.push({ kind: 'caption-band-overflow' });
    } else problems.push({ kind: 'no-caption-band' });
    if ([...v().textTracks].some((t) => t.kind === 'captions' && t.mode === 'showing'))
      problems.push({ kind: 'captions-drawn-on-film' });
    return { problems, keys: [...document.querySelectorAll('[data-key]')].map((e) => e.dataset.key) };
  };
  const tracks = () => [...v().textTracks].map((t) => ({ kind: t.kind, mode: t.mode, cues: t.cues ? t.cues.length : null }));
  window.__iveDrive = { v, sleep, once, state, frame, settled, seek, leak, layout, tracks };
  return true;
})()
