// WP6 browser checks of the built IVE, opened from disk (file://) in Chrome.
// Usage: node tests/test_ive.mjs <spec.json> <out.json>   (run by tests/test_ive.py through ptk's node env)
// spec: {url, drive, boundaries: [{t, expected}], answers: [{cue, start, words}], counts: {captions, chapters, metadata},
//        film_t, domain, repeats, questions: [{scene, pause_at, resume_at, answer_at, options, wrong}], sealed_text}
// Each named check writes {ok, detail} to out.json; the Python side asserts them.
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync } from 'node:fs';

const require = createRequire(process.env.PTK_NODE_PREFIX + '/package.json');
const { chromium } = require('playwright');
const [specPath, outPath] = process.argv.slice(2);
const spec = JSON.parse(readFileSync(specPath, 'utf8'));
const drive = readFileSync(spec.drive, 'utf8');
const out = { browser: null, checks: {} };

let browser;
try { browser = await chromium.launch({ channel: 'chrome' }); out.browser = 'chrome ' + browser.version(); }
catch (e) { browser = await chromium.launch(); out.browser = 'chromium ' + browser.version() + ' (Chrome not installed)'; }

const allowed = (u) => /^(file:|data:|blob:|about:)/.test(u);
async function open(opts = {}) {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 1000 }, javaScriptEnabled: opts.js !== false });
  const outbound = [], consoleMsgs = [], messages = [];
  await ctx.route('**/*', (r) => { if (allowed(r.request().url())) return r.continue(); outbound.push(r.request().url()); return r.abort(); });
  if (opts.js !== false) await ctx.addInitScript(() => { window.__msgs = []; window.addEventListener('message', (e) => window.__msgs.push(e.data)); });
  const page = await ctx.newPage();
  page.on('console', (m) => consoleMsgs.push(`${m.type()}: ${m.text()}`));
  page.on('pageerror', (e) => consoleMsgs.push(`pageerror: ${e.message}`));
  await page.goto(spec.url, { waitUntil: 'load' });
  if (opts.js !== false) {
    await page.waitForFunction('window.__ptkReady && window.__ptkReady()', null, { timeout: 30000 });
    await page.evaluate(drive);
  }
  return { ctx, page, outbound, consoleMsgs };
}
const run = (page, body) => page.evaluate(`(async () => { const D = window.__iveDrive; ${body} })()`);
async function check(name, fn) {
  try { out.checks[name] = await fn(); } catch (e) { out.checks[name] = { ok: false, detail: String(e && e.stack || e) }; }
}

// AC-6.1: the metadata track's cues carry {scene_id, state_id}; each question has a question and an answer cue
await check('cue_track', async () => {
  const { ctx, page } = await open();
  const cues = await run(page, `const t = [...D.v().textTracks].find((x) => x.kind === 'metadata');
    return [...t.cues].map((c) => ({ start: c.startTime, end: c.endTime, p: JSON.parse(c.text) }));`);
  await ctx.close();
  const bad = cues.filter((c) => !c.p.scene || !c.p.state || !c.p.state.state_id);
  const questions = cues.filter((c) => c.p.kind === 'question').map((c) => c.p.scene);
  const answered = cues.filter((c) => c.p.kind === 'answer').map((c) => c.p.answer_for);
  const contiguous = cues.every((c, i) => i === 0 || Math.abs(c.start - cues[i - 1].end) < 1e-6);
  return { ok: cues.length === spec.counts.metadata && !bad.length && questions.length > 0
             && questions.every((q) => answered.includes(q)) && contiguous,
           detail: { cues: cues.length, questions, answered, malformed: bad.length, contiguous } };
});

// AC-6.2 / D20.6: seeks around every boundary, through the real media clock, and chapter jumps
await check('pause_state', async () => {
  const { ctx, page } = await open();
  const rows = [];
  for (const b of spec.boundaries) {
    const s = await run(page, `const s = await D.seek(${b.t}); return { ...s, resolved: window.__ptkIve.resolve(s.t) };`);
    rows.push({ ...b, actual_t: s.t, shown: s.cue, resolved: s.resolved });
  }
  const chapters = await run(page, `const out = []; for (const b of document.querySelectorAll('#chapters button')) {
    const p = D.once(D.v(), 'seeked'); b.click(); await p; await D.sleep(60);
    out.push({ ...D.state(), current: b.getAttribute('aria-current'), expected: window.__ptkIve.resolve(D.v().currentTime) }); } return out;`);
  await ctx.close();
  const bad = rows.filter((r) => r.shown !== r.expected || r.resolved !== r.expected);
  const chapBad = chapters.filter((c) => c.cue !== c.expected || c.current !== 'true');
  return { ok: rows.length > 0 && !bad.length && chapters.length === spec.counts.chapters && !chapBad.length,
           detail: { seeks: rows.length, mismatches: bad, chapter_mismatches: chapBad,
                     strict_rule_would_fail: rows.filter((r) => r.strict_half_open !== r.expected).length,
                     sample: rows.filter((r) => r.boundary === rows[0].boundary) } };
});

// AC-6.3: paused (EXPLORE) 0.1 s before each answer cue, no answer anywhere outside <noscript>
await check('no_leak_before_answer', async () => {
  const res = [];
  for (const a of spec.answers) {
    const { ctx, page } = await open();
    await run(page, `await D.seek(${a.start - 0.1}); document.getElementById('explore').click(); await D.sleep(80); return 1;`);
    const leak = await run(page, `return D.leak(${JSON.stringify(a.words)});`);
    // the controls that could compute the answer are locked until the answer cue
    const locked = await run(page, `const l = document.getElementById('live'); return l ? l.dataset.locked : 'no-live';`);
    res.push({ cue: a.cue, ...leak, locked });
    await ctx.close();
  }
  return { ok: res.length > 0 && res.every((r) => !r.hits.length && r.mode === 'explore' && r.locked !== 'false'), detail: res };
});

// AC-6.4 (+ the WP5 poster flake): controls and the no-JS page, five times in a row, fresh each time
await check('controls_and_noscript', async () => {
  const runs = [];
  for (let i = 0; i < (spec.repeats || 5); i++) {
    const { ctx, page } = await open();
    const c = await run(page, `const v = D.v(); await D.seek(v.duration - 0.05); const n = document.querySelectorAll('#tx li').length;
      const p = D.once(v, 'seeked'); document.querySelector('#tx li button').click(); await p;
      const caps = [...v.textTracks].find((t) => t.kind === 'captions'); const cb = document.getElementById('caps');
      const el = document.getElementById('captext');
      const seen = () => { const cs = getComputedStyle(el), r = el.getBoundingClientRect(); let on = cs.visibility === 'visible'
        && r.width >= 1 && r.height >= 1 && el.textContent.trim() !== ''; for (let e = el; e; e = e.parentElement) {
        const s = getComputedStyle(e); if (s.display === 'none' || parseFloat(s.opacity) === 0) on = false; } return String(on); };
      await D.sleep(150); const m0 = seen(); cb.click(); await D.frame(); const m1 = seen(); cb.click(); await D.frame(); const m2 = seen();
      return { transcript_at_end: n, transcript_after_seek: document.querySelectorAll('#tx li').length, seek_to: v.currentTime,
               caption_modes: [m0, m1, m2], track_mode: caps.mode, chapters: document.querySelectorAll('#chapters li').length };`);
    await ctx.close();
    const nj = await open({ js: false });
    const n = await nj.page.evaluate(async () => {
      const imgs = [...document.images];
      await Promise.all(imgs.map((im) => im.decode().then(() => true, () => false)));
      const h = document.getElementById('answers'), tx = document.querySelector('noscript ol.tx');
      return { images: imgs.length, decoded: imgs.filter((im) => im.complete && im.naturalWidth > 0).length,
               heading_before_transcript: !!(h && tx && (h.compareDocumentPosition(tx) & Node.DOCUMENT_POSITION_FOLLOWING)),
               heading: h && h.textContent, transcript_items: tx ? tx.querySelectorAll('li').length : 0 };
    });
    await nj.ctx.close();
    const ok = c.transcript_at_end === spec.counts.captions && c.chapters === spec.counts.chapters
      && Math.abs(c.seek_to - spec.first_caption) < 0.01 && c.caption_modes.join() === 'true,false,true' && c.track_mode === 'hidden'
      && n.images === spec.counts.chapters && n.decoded === n.images && n.heading_before_transcript
      && n.transcript_items === spec.counts.captions;
    runs.push({ ok, controls: c, nojs: n });
  }
  return { ok: runs.length === (spec.repeats || 5) && runs.every((r) => r.ok), detail: runs };
});

// AC-6.6 FILM / EXPLORE / RETURN, plus every live view and AC-6.5 events
await check('film_explore_return', async () => {
  const { ctx, page } = await open();
  const film = await run(page, `await D.seek(${spec.film_t}); return D.state();`);
  const explore = await run(page, `const v = D.v(); await v.play(); await D.sleep(400); document.getElementById('explore').click();
    await D.sleep(100); return { ...D.state(), returnTime: window.__ptkIve.returnTime(), expected: window.__ptkIve.resolve(window.__ptkIve.returnTime()) };`);
  const edited = await run(page, `document.querySelector('#live-n input[value="3"]').click(); document.getElementById('live-brk').click();
    await D.sleep(60); const s = D.state(); const b = document.querySelector('#xp'); const o = document.getElementById('origin');
    return { ...s, badge_visible: o.offsetParent !== null && o.getBoundingClientRect().width > 0 };`);
  const returned = await run(page, `const v = D.v(); const p = D.once(v, 'playing'); document.getElementById('return').click(); await p; await D.sleep(150);
    const r = window.__ptkNav.filter((e) => e.action === 'return').pop();
    return { ...D.state(), return_position: r && r.position, film_cue: window.__ptkIve.resolve(v.currentTime),
             edits_left: document.querySelectorAll('[data-edit], .nval.changed, #xp[data-origin="yours"]').length };`);
  const repaused = await run(page, `D.v().pause(); await D.sleep(100); const n = document.querySelector('#live-n input:checked');
    return { ...D.state(), n_checked: n && n.value, brk: document.getElementById('live-brk').getAttribute('aria-pressed') };`);
  const live = await run(page, `const out = []; for (const brk of [false, true]) for (const n of ${JSON.stringify(spec.domain)})
    out.push({ n, brk, ...window.__ptkIve.live(n, brk) }); return out;`);
  const events = await page.evaluate(() => ({ nav: window.__ptkNav, posted: window.__msgs }));
  await ctx.close();
  const rt = explore.returnTime;
  const checks = {
    film_follows_clock: film.mode === 'film' && film.origin === 'film',
    explore_on_pause: explore.mode === 'explore' && explore.paused && explore.origin === 'film' && explore.cue === explore.expected,
    edit_marked_yours: edited.origin === 'yours' && edited.border === 'dashed' && explore.border !== 'dashed'
      && edited.badge_visible && edited.origin_text === spec.yours_text && !!edited.edit,
    return_resumes_at_pause: returned.mode === 'film' && !returned.paused && Math.abs(returned.return_position - rt) < 0.002
      && returned.t >= rt - 0.001 && returned.t < rt + 1,
    film_state_after_return: returned.origin === 'film' && returned.cue === returned.film_cue && returned.edits_left === 0
      && JSON.stringify(returned.output) === JSON.stringify(film.output),
    no_edit_on_next_pause: repaused.origin === 'film' && repaused.edit === null && repaused.n_checked === spec.film_n
      && repaused.brk === spec.film_brk,
  };
  return { ok: Object.values(checks).every(Boolean), detail: { checks, film, explore, edited, returned, repaused }, live, events };
});

// AC-6.8: by default the film plays through each question and explains; it never stops for a prediction.
// The practice-mode toggle is visible and off.
await check('explanation_first_default', async () => {
  const res = [];
  for (const q of spec.questions) {
    const { ctx, page } = await open();
    const r = await run(page, `const v = D.v(), I = window.__ptkIve, b = document.getElementById('practice');
      const vis = !!b && b.offsetParent !== null && b.getBoundingClientRect().width > 0 && !b.hidden;
      const toggle = { visible: vis, pressed: b && b.getAttribute('aria-pressed'), practice: I.practice() };
      await D.seek(${Math.max(0, q.pause_at - 2)}); const p = v.play(); if (p && p.catch) p.catch(() => {});
      const modes = new Set(), samples = []; let paused = false;
      for (let i = 0; i < 260 && v.currentTime < ${q.answer_at} + 0.3; i++) {  // B5: 13 s, the 0.75 narration puts the answer 7.4 s after the question
        await D.sleep(50); modes.add(I.mode()); samples.push(Math.round(v.currentTime * 1000) / 1000);
        if (v.paused && !v.ended) paused = true; }
      const chapters = [...document.querySelectorAll('#chapters .ttl')].map((e) => e.textContent);
      v.pause();
      return { toggle, modes: [...modes], paused, t_end: samples[samples.length - 1],
               in_gap: samples.filter((t) => t > ${q.pause_at} + 0.3 && t < ${q.resume_at} - 0.1), chapters };`);
    await ctx.close();
    res.push({ scene: q.scene, ...r });
  }
  const ok = res.length > 0 && res.every((r) => r.toggle.visible && r.toggle.pressed === 'false' && r.toggle.practice === false
    && !r.modes.includes('ask') && !r.paused && r.t_end >= spec.questions.find((q) => q.scene === r.scene).answer_at
    && !r.in_gap.length && !r.chapters.includes(spec.sealed_text));
  return { ok, detail: res };
});

// AC-6.8: with practice mode turned on, the film stops at the question, holds through a wait and a play(),
// shows the options, and resumes at the answer scene after a pick; turning practice off releases the hold
await check('practice_mode_pauses', async () => {
  const res = [];
  for (const q of spec.questions) {
    const { ctx, page } = await open();
    const r = await run(page, `const v = D.v(), I = window.__ptkIve, b = document.getElementById('practice');
      b.click(); await D.sleep(30); const on = { pressed: b.getAttribute('aria-pressed'), practice: I.practice() };
      await D.seek(${Math.max(0, q.pause_at - 2)}); let p = v.play(); if (p && p.catch) p.catch(() => {});
      for (let i = 0; i < 120 && I.mode() !== 'ask'; i++) await D.sleep(50);
      await D.sleep(150); const stopped = { mode: I.mode(), t: v.currentTime, paused: v.paused,
        options: [...document.querySelectorAll('#state .opt')].map((e) => e.textContent) };
      await D.sleep(1500); p = v.play(); if (p && p.catch) p.catch(() => {}); await D.sleep(500);
      const held = { mode: I.mode(), t: v.currentTime, paused: v.paused };
      const wrong = [...document.querySelectorAll('#state .opt')][${q.wrong}];
      const pl = D.once(v, 'playing', 4000); wrong.click(); await pl; await D.sleep(120);
      const picked = { mode: I.mode(), t: v.currentTime, paused: v.paused,
        verdict: (document.querySelector('#state .verdict') || {}).getAttribute ? document.querySelector('#state .verdict').getAttribute('data-verdict') : null };
      v.pause(); return { on, stopped, held, picked };`);
    await ctx.close();
    const second = await open();
    const off = await run(second.page, `const v = D.v(), I = window.__ptkIve, b = document.getElementById('practice');
      b.click(); await D.seek(${Math.max(0, q.pause_at - 2)}); let p = v.play(); if (p && p.catch) p.catch(() => {});
      for (let i = 0; i < 120 && I.mode() !== 'ask'; i++) await D.sleep(50);
      const asked = I.mode(); b.click(); await D.sleep(30); p = v.play(); if (p && p.catch) p.catch(() => {});
      for (let i = 0; i < 240 && v.currentTime < ${q.answer_at} + 0.2; i++) await D.sleep(50);
      const out = { asked, mode: I.mode(), t: v.currentTime, pressed: b.getAttribute('aria-pressed') }; v.pause(); return out;`);
    await second.ctx.close();
    res.push({ scene: q.scene, ...r, off });
  }
  const ok = res.length > 0 && res.every((r) => {
    const q = spec.questions.find((x) => x.scene === r.scene);
    return r.on.pressed === 'true' && r.on.practice === true
      && r.stopped.mode === 'ask' && r.stopped.paused && Math.abs(r.stopped.t - q.pause_at) <= 0.12
      && JSON.stringify(r.stopped.options) === JSON.stringify(q.options)
      && r.held.mode === 'ask' && r.held.paused && Math.abs(r.held.t - r.stopped.t) <= 0.05
      && r.picked.mode === 'film' && !r.picked.paused && r.picked.t >= q.resume_at - 0.05 && r.picked.t <= q.resume_at + 0.6
      && !!r.picked.verdict
      && r.off.asked === 'ask' && r.off.mode === 'film' && r.off.pressed === 'false' && r.off.t >= q.answer_at;
  });
  return { ok, detail: res };
});

// AC-6.7: from file://, every track loads (as blob: tracks), the MP4 decodes, nothing is fetched, no console errors
await check('file_protocol', async () => {
  const { ctx, page, outbound, consoleMsgs } = await open();
  const f = await run(page, `const v = D.v(); await D.seek(1.0); await D.frame();
    return { protocol: location.protocol, tracks: D.tracks(), track_src: [...document.querySelectorAll('track')].map((t) => t.src.split(':')[0]),
             readyState: v.readyState, error: v.error && v.error.code, h264: v.canPlayType('video/mp4; codecs="avc1.640028"') };`);
  await ctx.close();
  const got = Object.fromEntries(f.tracks.map((t) => [t.kind, t.cues]));
  const errs = consoleMsgs.filter((m) => /^(error|pageerror)/.test(m));
  return { ok: f.protocol === 'file:' && JSON.stringify(got) === JSON.stringify(spec.counts_by_kind) && f.readyState >= 2 && !f.error
             && f.track_src.every((s) => s === 'blob') && !outbound.length && !errs.length,
           detail: { ...f, outbound, console_errors: errs } };
});

await browser.close();
writeFileSync(outPath, JSON.stringify(out, null, 1));
