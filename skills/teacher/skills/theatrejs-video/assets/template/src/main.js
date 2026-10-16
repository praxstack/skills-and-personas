// main.js: boots the film page and implements the capture contract used by scripts/capture.mjs:
//   window.READY (a Promise), window.TOTAL (seconds), window.renderFrame(t) (deterministic: seeks Theatre, applies)
// Query flags for a browser: ?t=12.5 (show one frame), ?debug=1 (safe area, time, line id), ?play=1 (real-time
// preview with the narration), ?state=other.json (preview a Studio export in a browser; to render one, see the
// guide: theatre-state.pinned.json).
import './kit/style.css';
import interVar from 'inter-ui/variable/InterVariable.woff2';
import jbMedium from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-Medium.woff2';
import jbBold from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-Bold.woff2';
import jbExtra from 'jetbrains-mono/fonts/webfonts/JetBrainsMonoNL-ExtraBold.woff2';
import bangers from '@fontsource/bangers/files/bangers-latin-400-normal.woff2';
import { applyCssVars } from './kit/tokens.js';
import { timeline } from './theatre/timing.js';
import { compileFilm, schemaOf } from './theatre/keys.js';
import { createRig } from './theatre/rig.js';
import world, { PROJECT_ID } from './film/world.js';
import shots from './film/shots.js';

const Q = new URLSearchParams(location.search);

async function loadFonts() {
  // JetBrains Mono "NL" files have no ligatures at all, so != <= ++ can never turn into single glyphs
  const faces = [
    new FontFace('Inter Var', `url(${interVar})`, { weight: '100 900' }),
    new FontFace('JB Mono', `url(${jbMedium})`, { weight: '400 600' }),
    new FontFace('JB Mono', `url(${jbBold})`, { weight: '700' }),
    new FontFace('JB Mono', `url(${jbExtra})`, { weight: '800 900' }),
    new FontFace('Bangers', `url(${bangers})`, { weight: '400' }),
  ];
  for (const f of faces) { await f.load(); document.fonts.add(f); }
  for (const spec of ['600 40px "Inter Var"', '800 30px "JB Mono"', '500 30px "JB Mono"', '400 60px "Bangers"']) await document.fonts.load(spec, '0123 !=<=→∞');
  await document.fonts.ready;
}

async function loadState(T, W) {
  const want = Q.get('state') || 'theatre-state.json';
  try {
    const r = await fetch(want, { cache: 'no-store' });
    if (r.ok) {
      const st = await r.json();
      if (Q.get('state') || st.pinned || st.generated?.timingHash === T.hash) return { state: st, from: st.pinned ? 'theatre-state.pinned.json' : want };
      console.warn(`theatre-state.json was built for timing ${st.generated?.timingHash}, timing.js is ${T.hash}: compiling shots in the page (run npm run build)`);
    }
  } catch { /* no file: compile below */ }
  return { state: compileFilm({ T, W, shots }).state, from: 'compiled in page' };
}

async function boot() {
  const TIMING = window.TIMING;
  if (!TIMING) throw new Error('window.TIMING is missing: timing.js did not load (voice.py --emit source/timing.js writes it)');
  applyCssVars(document.documentElement.style); // every colour style.css uses, from tokens.js (and the theme)
  await loadFonts();
  const T = timeline(TIMING);
  const W = world(T);
  const { state, from } = await loadState(T, W);
  const schema = schemaOf(W.components);
  const rig = await createRig({ projectId: PROJECT_ID, state, schema });
  const root = document.getElementById('root');
  W.stage.mount(root);
  for (const c of W.components) if (c !== W.stage) c.mount(W.stage);
  const dbg = Q.get('debug') ? debugOverlay(W.stage, T) : null;
  window.TOTAL = TIMING.total;
  window.STATE_SOURCE = from;
  window.renderFrame = (t) => {
    const V = rig.values(t);
    for (const c of W.components) c.apply(V, t);
    if (dbg) dbg(t);
  };
  window.renderFrame(Q.has('t') ? +Q.get('t') : 0);
  if (Q.get('play')) play();
  return true;
}

function debugOverlay(stage, T) {
  const d = document.createElement('div');
  d.style.cssText = 'position:absolute;inset:0;pointer-events:none;';
  d.innerHTML = '<div style="position:absolute;left:96px;top:96px;right:96px;bottom:96px;outline:2px dashed rgba(0,255,255,.5)"></div>' +
    '<div style="position:absolute;left:0;right:0;top:900px;border-top:2px dashed rgba(255,0,255,.6)"></div>' +
    '<div id="dbg-t" style="position:absolute;right:20px;top:16px;font:600 24px monospace;color:#0ff;background:#000a;padding:4px 10px"></div>';
  stage.vp.appendChild(d);
  const lab = d.querySelector('#dbg-t');
  return (t) => { const l = T.lineAt(t); lab.textContent = `${t.toFixed(2)} s  ${l ? l.id : '-'}`; };
}

function play() {
  // real-time preview for a person at a browser: click to start (autoplay rules), narration from the project
  const audio = new Audio(Q.get('audio') || '../voice/narration.wav');
  document.body.addEventListener('click', () => { audio.paused ? audio.play() : audio.pause(); });
  const tick = () => { window.renderFrame(audio.currentTime); requestAnimationFrame(tick); };
  requestAnimationFrame(tick);
}

window.READY = boot().catch((e) => {
  console.error(e);
  const msg = String(e && e.stack || e);
  window.renderFrame = () => { throw new Error(msg); };
  document.body.insertAdjacentHTML('beforeend', `<pre style="position:absolute;inset:40px;color:#f66;font:20px monospace;white-space:pre-wrap">${msg.replace(/</g, '&lt;')}</pre>`);
  throw e;
});
