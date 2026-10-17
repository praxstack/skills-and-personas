// studio.js: LAPTOP ONLY, never needed to render. Opens the same film with @theatre/studio on top so a person can
// scrub the timeline, drag keyframes and tweak values by hand, then export the state (Studio: select the project,
// "Export Explainer to JSON"). Keep the generated keyframes as the source of truth: run
//   node tools/studio-diff.mjs ~/Downloads/Explainer.theatre-project-state.json
// to list what you changed (object.prop, time, nearest line) and port it into src/film/shots.js, so re-voicing still
// re-times everything. To render an export as-is (frozen timing): index.html?state=<file>.json.
//
//   npm i --save-exact @theatre/studio@0.7.2 && npm run studio     then open http://localhost:8080/source/studio.html
import * as studioModule from '@theatre/studio';
import { onChange } from '@theatre/core';
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

// @theatre/studio is CommonJS: depending on the bundler the studio object is the namespace, .default or .default.default
const studio = [studioModule.default, studioModule.default?.default, studioModule].find((x) => x && typeof x.initialize === 'function');
studio.initialize(); // must run before getProject (createRig)

async function boot() {
  for (const [fam, url, weight] of [['Inter Var', interVar, '100 900'], ['JB Mono', jbMedium, '400 600'], ['JB Mono', jbBold, '700'], ['JB Mono', jbExtra, '800 900'], ['Bangers', bangers, '400']]) {
    const f = new FontFace(fam, `url(${url})`, { weight }); await f.load(); document.fonts.add(f);
  }
  applyCssVars(document.documentElement.style);

  const T = timeline(window.TIMING), W = world(T);
  let state = null;
  try { const res = await fetch('theatre-state.json', { cache: 'no-store' }); if (res.ok) state = await res.json(); } catch { /* compile */ }
  if (!state || (!state.pinned && state.generated?.timingHash !== T.hash)) state = compileFilm({ T, W, shots }).state;
  // Studio keeps your edits in the browser (localStorage). If it says the browser state differs from the state on
  // disk, choose "use the state on disk" after a re-voice or rebuild.
  const rig = await createRig({ projectId: PROJECT_ID, state, schema: schemaOf(W.components) });
  W.stage.mount(document.getElementById('root'));
  for (const c of W.components) if (c !== W.stage) c.mount(W.stage);
  window.TOTAL = T.total;

  // the 1920x1080 stage scaled to the window, below Studio's panels
  const fit = () => { const s = Math.min(innerWidth / 1920, innerHeight / 1080); document.getElementById('root').style.cssText = `transform:scale(${s});transform-origin:0 0;`; };
  addEventListener('resize', fit); fit();

  // draw whenever the playhead moves or a value is edited: read values where the sequence is (no seeking here)
  let queued = false;
  const draw = () => { queued = false; const t = rig.sheet.sequence.position, V = rig.current(); for (const c of W.components) c.apply(V, t); };
  const request = () => { if (!queued) { queued = true; requestAnimationFrame(draw); } };
  onChange(rig.sheet.sequence.pointer.position, request);
  for (const [, o] of rig.objs) o.onValuesChange(request);
  draw();

  // narration on the timeline (plays after the first click; Studio's play button then plays picture + sound)
  rig.sheet.sequence.attachAudio({ source: '../voice/narration.wav' }).catch((e) => console.warn('no narration attached:', e.message));
  window.STUDIO = { studio, rig, T };
  return true;
}
window.READY = boot().catch((e) => {
  console.error(e);
  const pre = document.createElement('pre'); // textContent: the stack can quote narration text, which is data, not markup
  pre.style.color = '#f66';
  pre.textContent = String(e.stack || e);
  document.body.appendChild(pre);
  throw e;
});
