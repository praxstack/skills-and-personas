// ptk WP4 browser driver: opens an explorer or Q&A page from file:// in Chromium, drives every
// control, and records what the page shows. It judges nothing about values: ptk/project/explorer.py
// and qa.py compare the records with expect.py in Python.
// Usage: node drive.mjs <job.json> <result.json>
//   job: {"mode": "explorer" | "qa", "page": "/abs/index.html", "shots": "/abs/dir" | null,
//         "domain": [..], "toggle": true}
import { createRequire } from 'node:module';
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

const prefix = process.env.PTK_NODE_PREFIX;
if (!prefix) { console.error('PTK_NODE_PREFIX not set (run through ptk/node.py)'); process.exit(2); }
const require = createRequire(prefix + '/package.json');
const { chromium } = require('playwright');

const [jobPath, outPath] = process.argv.slice(2);
const job = JSON.parse(readFileSync(jobPath, 'utf8'));
const URL = pathToFileURL(job.page).href;
const browser = await chromium.launch({ args: ['--force-color-profile=srgb', '--font-render-hinting=none'] });
const result = { url: URL, mode: job.mode, contexts: [] };

async function open(opts = {}) {
  const ctx = await browser.newContext({
    viewport: { width: opts.width || 1440, height: opts.height || 900 },
    colorScheme: opts.scheme || 'light',
    reducedMotion: opts.reducedMotion || 'no-preference',
    javaScriptEnabled: opts.js !== false,
  });
  const rec = { name: opts.name, requests: [], console: [], pageErrors: [] };
  await ctx.route('**/*', (route) => {
    const u = route.request().url();
    if (/^(file:|data:|about:)/.test(u)) return route.continue();
    rec.requests.push(u);
    return route.abort('blockedbyclient');
  });
  if (opts.js !== false) {
    await ctx.addInitScript(() => {
      window.__csp = [];
      document.addEventListener('securitypolicyviolation', (e) => window.__csp.push({ directive: e.violatedDirective, blocked: e.blockedURI, sample: e.sample }));
    });
  }
  const page = await ctx.newPage();
  page.on('console', (m) => { if (m.type() === 'error' || m.type() === 'warning') rec.console.push(`${m.type()}: ${m.text()}`); });
  page.on('pageerror', (e) => rec.pageErrors.push(String(e)));
  await page.goto(URL, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready.then(() => true));
  result.contexts.push(rec);
  return { ctx, page, rec };
}

async function finish(o) {
  if (o.page && !o.rec.closed) {
    try { o.rec.csp = await o.page.evaluate(() => window.__csp || null); } catch (e) { o.rec.csp = null; }
  }
  await o.ctx.close();
}

// ---------------------------------------------------------------- shared in-page probes

function a11yProbe() {
  const meta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
  return {
    csp: meta ? meta.getAttribute('content') : null,
    jsClass: document.documentElement.classList.contains('js'),
    scripts: [...document.scripts].map((s) => ({ type: s.type || 'text/javascript', src: s.src || null, inline: !s.src })),
    styles: document.querySelectorAll('style').length,
    links: [...document.querySelectorAll('link[href]')].map((l) => l.href),
    styleAttrs: [...document.querySelectorAll('[style]')].length,
    lang: document.documentElement.lang,
    title: document.title,
  };
}

function layoutProbe() {
  const iw = window.innerWidth, ih = window.innerHeight;
  const problems = [];
  const sw = document.documentElement.scrollWidth;
  if (sw > iw + 1) problems.push({ kind: 'page-overflow', scrollWidth: sw, innerWidth: iw });
  const keys = [...document.querySelectorAll('[data-key]')].filter((e) => getComputedStyle(e).display !== 'none' && e.offsetParent !== null);
  const nodes = [];
  for (const k of keys) {
    const r = k.getBoundingClientRect();
    const n = { key: k.dataset.key, left: +r.left.toFixed(1), right: +r.right.toFixed(1), width: +r.width.toFixed(1), height: +r.height.toFixed(1) };
    nodes.push(n);
    if (r.left < -0.5 || r.right > iw + 0.5) problems.push({ kind: 'key-node-offscreen', ...n });
    if (r.height > ih) problems.push({ kind: 'key-node-taller-than-screen', ...n, viewport: ih });
    if (k.scrollWidth > k.clientWidth + 1) problems.push({ kind: 'key-node-inner-scroll', key: n.key, scrollWidth: k.scrollWidth, clientWidth: k.clientWidth });
    for (const d of k.querySelectorAll('*')) {
      const st = getComputedStyle(d);
      if (st.display === 'none') continue;
      const b = d.getBoundingClientRect();
      if (!b.width) continue;
      if (b.right > r.right + 0.5 || b.left < r.left - 0.5) { problems.push({ kind: 'key-node-content-outside', key: n.key, tag: d.tagName, text: d.textContent.slice(0, 40), right: b.right, boxRight: r.right }); break; }
      if (d.scrollWidth > d.clientWidth + 1 && (st.overflowX === 'auto' || st.overflowX === 'scroll')) problems.push({ kind: 'key-node-inner-scroll', key: n.key, tag: d.tagName });
    }
  }
  let minPx = 1e9;
  for (const el of document.querySelectorAll('body *')) {
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || el.closest('noscript')) continue;
    const own = [...el.childNodes].some((c) => c.nodeType === 3 && c.textContent.trim());
    if (!own || !el.getBoundingClientRect().width) continue;
    const px = parseFloat(st.fontSize);
    minPx = Math.min(minPx, px);
    if (px < 11) problems.push({ kind: 'min-size', text: el.textContent.trim().slice(0, 40), px });
  }
  // no orphaned values: a `name = value` pair never breaks across lines (integration finding, WP9)
  const pair = /[A-Za-z_][\w()]* = [-+]?\d[\w.]*/g;
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let tn = walker.nextNode(); tn; tn = walker.nextNode()) {
    const el = tn.parentElement;
    if (!el || el.closest('noscript, script, style, svg') || getComputedStyle(el).display === 'none' || !el.getBoundingClientRect().width) continue;
    for (const m of tn.textContent.matchAll(pair)) {
      const r = document.createRange();
      r.setStart(tn, m.index); r.setEnd(tn, m.index + m[0].length);
      const tops = new Set([...r.getClientRects()].filter((b) => b.width > 0).map((b) => Math.round(b.top)));
      if (tops.size > 1) problems.push({ kind: 'value-split-across-lines', text: m[0] });
    }
  }
  return { problems, nodes, minPx, width: iw, height: ih };
}

// ---------------------------------------------------------------- explorer

function snapExplorer() {
  const s = document.getElementById('x-state');
  const checked = document.querySelector('#x-n input:checked');
  const oo = document.getElementById('x-brk-state');
  return {
    n: s.getAttribute('data-n'), brk: s.getAttribute('data-brk'), program: s.getAttribute('data-program'),
    enter: s.getAttribute('data-enter'), exit: s.getAttribute('data-exit'), ran: s.getAttribute('data-ran'),
    file: document.getElementById('x-file').textContent,
    ranLines: [...document.querySelectorAll('#x-code li.ran')].map((li) => +li.dataset.line),
    code: [...document.querySelectorAll('#x-code li')].map((li) => ({
      line: +li.dataset.line, text: li.querySelector('code').textContent,
      tags: [...li.querySelectorAll('.tag')].map((t) => ({ key: t.dataset.chrome, text: t.textContent, tone: t.classList[1] })) })),
    nval: (document.querySelector('#x-code [data-n]') || {}).textContent,
    ...(() => { const f = [...document.querySelectorAll('svg.flow')].find((e) => getComputedStyle(e).display !== 'none');
                return { flow: f ? f.dataset.flow : null, flowRan: f ? f.dataset.ran : null }; })(),
    output: [...document.querySelectorAll('#x-out .val')].map((e) => e.textContent),
    prose: [...document.querySelectorAll('#x-live > span')].map((e) => ({ key: e.dataset.chrome || null, claim: e.dataset.claim || null, claims: e.dataset.claims || null, text: e.textContent })),
    prov: { key: document.getElementById('x-prov').dataset.chrome, text: document.getElementById('x-prov').textContent },
    controls: { checked: checked ? checked.value : null, pressed: document.getElementById('x-brk').getAttribute('aria-pressed'),
                onoff: oo ? oo.textContent : null, resetDisabled: document.getElementById('x-reset').disabled },
  };
}

async function setN(page, n, how) {
  if (how === 'keyboard') {
    for (let i = 0; i < 12; i++) {
      const cur = await page.evaluate(() => (document.querySelector('#x-n input:checked') || {}).value);
      if (cur === String(n)) return;
      await page.focus('#x-n input:checked');
      await page.keyboard.press(Number(cur) < n ? 'ArrowRight' : 'ArrowLeft');
    }
  } else {
    await page.click(`#x-n label:has(input[value="${n}"])`);
  }
}

async function explorer() {
  const steps = [];
  const domain = job.domain;
  // --- AC-4.1: CSP, keyboard, focus, reduced motion, noscript; AC-4.8: file:// (every context is file://)
  let o = await open({ name: 'a11y-1440-light' });
  result.a11y = await o.page.evaluate(a11yProbe);
  if (!result.a11y.jsClass) { result.scriptBlocked = true; await finish(o); return; }
  const tabs = [];
  await o.page.keyboard.press('Tab');
  for (let i = 0; i < 4; i++) {
    tabs.push(await o.page.evaluate(() => {
      const a = document.activeElement;
      const ring = a.matches('input') ? a.nextElementSibling : a;
      const st = getComputedStyle(ring);
      return { tag: a.tagName, id: a.id, name: a.name || null, value: a.value || null, outline: `${st.outlineStyle} ${st.outlineWidth}`, visible: a.matches(':focus-visible') };
    }));
    await o.page.keyboard.press('Tab');
  }
  result.tabOrder = tabs;
  // keyboard-only operation, each step's effect recorded
  const kb = [];
  await o.page.focus('#x-n input:checked');
  await o.page.keyboard.press('ArrowRight');
  kb.push({ action: 'ArrowRight on n', snap: await o.page.evaluate(snapExplorer) });
  await o.page.keyboard.press('Tab');
  kb.push({ action: 'focus after Tab', active: await o.page.evaluate(() => document.activeElement.id) });
  await o.page.keyboard.press('Space');
  kb.push({ action: 'Space on toggle', snap: await o.page.evaluate(snapExplorer) });
  await o.page.keyboard.press('Enter');
  kb.push({ action: 'Enter on toggle', snap: await o.page.evaluate(snapExplorer) });
  await o.page.keyboard.press('Tab');
  kb.push({ action: 'focus after Tab 2', active: await o.page.evaluate(() => document.activeElement.id) });
  await o.page.keyboard.press('Enter');
  kb.push({ action: 'Enter on reset', snap: await o.page.evaluate(snapExplorer) });
  result.keyboard = kb;
  result.transitionsNormal = await o.page.evaluate(() => getComputedStyle(document.querySelector('.ln')).transitionDuration);
  await finish(o);

  o = await open({ name: 'reduced-motion', reducedMotion: 'reduce' });
  result.transitionsReduced = await o.page.evaluate(() => [...document.querySelectorAll('.ln, .pill, .seg label span')].map((e) => getComputedStyle(e).transitionDuration));
  await finish(o);

  o = await open({ name: 'no-js', js: false });
  result.noscript = await o.page.evaluate(() => ({
    note: [...document.querySelectorAll('.nojs p')].map((p) => p.textContent),
    table: [...document.querySelectorAll('.nojs tbody tr')].map((tr) => ({ n: tr.dataset.n, cells: [...tr.querySelectorAll('td')].map((td) => td.textContent) })),
    controlsVisible: [...document.querySelectorAll('.controls')].some((e) => getComputedStyle(e).display !== 'none'),
    tableVisible: !!document.querySelector('.nojs table') && getComputedStyle(document.querySelector('.nojs table')).display !== 'none',
  }));
  result.noscript.snap = await o.page.evaluate(snapExplorer);
  await finish(o);

  // --- AC-4.2 / AC-4.6: every control step over the whole domain
  o = await open({ name: 'domain-1440-light' });
  const p = o.page;
  let want = { n: job.n0, brk: false };
  steps.push({ action: 'load', want: { ...want }, snap: await p.evaluate(snapExplorer) });
  for (const brk of [false, true]) {
    if (want.brk !== brk) { await p.click('#x-brk'); want.brk = brk; steps.push({ action: 'toggle', want: { ...want }, snap: await p.evaluate(snapExplorer) }); }
    for (const [i, n] of domain.entries()) {
      const how = i % 2 ? 'keyboard' : 'click';
      await setN(p, n, how); want.n = n;
      steps.push({ action: `n=${n} (${how})`, want: { ...want }, snap: await p.evaluate(snapExplorer) });
    }
  }
  for (const n of domain) {
    await setN(p, n, 'click'); want.n = n;
    steps.push({ action: `n=${n}`, want: { ...want }, snap: await p.evaluate(snapExplorer) });
    await p.click('#x-brk'); want.brk = !want.brk;
    steps.push({ action: 'toggle', want: { ...want }, snap: await p.evaluate(snapExplorer) });
    await p.click('#x-brk'); want.brk = !want.brk;
    steps.push({ action: 'toggle back', want: { ...want }, snap: await p.evaluate(snapExplorer) });
  }
  await setN(p, domain[domain.length - 1], 'click'); want.n = domain[domain.length - 1];
  if (!want.brk) { await p.click('#x-brk'); want.brk = true; }
  steps.push({ action: 'far from default', want: { ...want }, snap: await p.evaluate(snapExplorer) });
  await p.click('#x-reset'); want = { n: job.n0, brk: false };
  steps.push({ action: 'reset', want: { ...want }, snap: await p.evaluate(snapExplorer) });
  result.steps = steps;
  await finish(o);

  // --- AC-4.7 (+ 1440 and dark): key nodes in every state; screenshots
  result.layout = [];
  for (const width of [390, 1440]) {
    for (const scheme of ['light', 'dark']) {
      o = await open({ name: `layout-${width}-${scheme}`, width, height: width === 390 ? 844 : 900, scheme });
      for (const brk of [false, true]) {
        if (brk) await o.page.click('#x-brk');
        for (const n of domain) {
          await setN(o.page, n, 'click');
          result.layout.push({ width, scheme, n, brk, ...(await o.page.evaluate(layoutProbe)) });
        }
      }
      if (job.shots) {
        mkdirSync(job.shots, { recursive: true });
        await setN(o.page, 4, 'click');
        await o.page.mouse.move(0, 0);
        await o.page.waitForTimeout(400);
        await o.page.screenshot({ path: `${job.shots}/explorer-${width}-${scheme}-n4-break.png`, fullPage: true });
        await o.page.click('#x-reset');
        await o.page.mouse.move(0, 0);
        await o.page.waitForTimeout(400);
        await o.page.screenshot({ path: `${job.shots}/explorer-${width}-${scheme}.png`, fullPage: true });
      }
      await finish(o);
    }
  }
}

// ---------------------------------------------------------------- step-through explorer (panel lessons)

function snapStepper() {
  const vis = (e) => e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0;
  const steps = [...document.querySelectorAll('section.step')];
  const shown = steps.filter(vis);
  const s = shown[0];
  const checked = document.querySelector('#s-steps input:checked');
  const svg = s ? [...s.querySelectorAll('svg.mech')].find(vis) : null;
  return {
    visibleSteps: shown.length, state: s ? s.dataset.state : null, checked: checked ? checked.value : null,
    label: s ? s.querySelector('.slabel').textContent : null,
    line: s && s.querySelector('.ln.cur') ? +s.querySelector('.ln.cur').dataset.line : null,
    ran: s ? [...s.querySelectorAll('.ln.ran')].map((li) => +li.dataset.line) : [],
    output: s ? [...s.querySelectorAll('.out .val')].map((e) => e.textContent) : [],
    output_facts: s ? [...s.querySelectorAll('.out .val')].map((e) => e.dataset.fact) : [],
    prose: s ? [...s.querySelectorAll('.live [data-claim]')].map((e) => ({ claim: e.dataset.claim, text: e.textContent })) : [],
    panelLayout: svg ? svg.dataset.layout : null, panelState: svg ? svg.dataset.panelState : null,
    panelTheme: svg ? svg.dataset.theme : null,
    panelFacts: svg ? [...svg.querySelectorAll('[data-fact]')].map((e) => e.dataset.fact) : [],
    prevDisabled: document.getElementById('s-prev').disabled, nextDisabled: document.getElementById('s-next').disabled,
  };
}

function snapKnobValues() {
  const vis = (e) => e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0;
  return {
    selected: [...document.querySelectorAll('#k-table thead th.sel')].map((th) => th.dataset.value),
    row: [...document.querySelectorAll('#k-table td.sel [data-fact]')].map((e) => [e.dataset.fact, e.textContent]),
    prose: [...document.querySelectorAll('.kprose')].filter(vis).flatMap((d) => [...d.querySelectorAll('[data-claim]')].map((p) => p.dataset.claim)),
  };
}

function snapKnobCalls() {
  const vis = (e) => e && getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0;
  const st = [...document.querySelectorAll('.kcalls .kstep')].filter(vis);
  const s = st[0];
  return {
    visible: st.length,
    frames: s ? [...s.querySelectorAll('li.kframe')].map((li) => ({ label: li.querySelector('code').textContent,
      status: li.dataset.status, vars: [...li.querySelectorAll('.kvar')].map((e) => e.textContent), slot: !!li.querySelector('.kslot') })) : [],
    printed: s ? [...s.querySelectorAll('.kout li .val')].map((e) => e.textContent) : [],
  };
}

function snapKnobNeuron() {
  const t = (id) => document.getElementById(id).textContent;
  const d = document.getElementById('k-dot');
  return { w2: t('k-w2-v'), b: t('k-b-v'), t1: t('k-t1'), t2: t('k-t2'), bs: t('k-bs'), z: t('k-z'), a: t('k-a'),
           dot: d ? [+d.getAttribute('cx'), +d.getAttribute('cy')] : null };
}

async function stepper() {
  const S = job.states;
  let o = await open({ name: 'a11y-1440-light' });
  result.a11y = await o.page.evaluate(a11yProbe);
  if (!result.a11y.jsClass) { result.scriptBlocked = true; await finish(o); return; }
  const tabs = [];
  await o.page.keyboard.press('Tab');
  for (let i = 0; i < 3; i++) {
    tabs.push(await o.page.evaluate(() => {
      const a = document.activeElement;
      const ring = a.matches('input') ? a.nextElementSibling : a;
      const st = getComputedStyle(ring);
      return { tag: a.tagName, id: a.id, name: a.name || null, value: a.value || null, outline: `${st.outlineStyle} ${st.outlineWidth}`, visible: a.matches(':focus-visible') };
    }));
    await o.page.keyboard.press('Tab');
  }
  result.tabOrder = tabs;
  const kb = [];
  await o.page.focus('#s-steps input:checked');
  await o.page.keyboard.press('ArrowRight');
  kb.push({ action: 'ArrowRight on step', snap: await o.page.evaluate(snapStepper) });
  await o.page.keyboard.press('Tab');
  kb.push({ action: 'focus after Tab', active: await o.page.evaluate(() => document.activeElement.id) });
  await o.page.keyboard.press('Tab');
  kb.push({ action: 'focus after Tab 2', active: await o.page.evaluate(() => document.activeElement.id) });
  await o.page.keyboard.press('Enter');
  kb.push({ action: 'Enter on Next', snap: await o.page.evaluate(snapStepper) });
  await o.page.focus('#s-prev');
  await o.page.keyboard.press('Space');
  kb.push({ action: 'Space on Previous', snap: await o.page.evaluate(snapStepper) });
  result.keyboard = kb;
  result.transitionsNormal = await o.page.evaluate(() => getComputedStyle(document.querySelector('.pill')).transitionDuration);
  await finish(o);

  o = await open({ name: 'reduced-motion', reducedMotion: 'reduce' });
  result.transitionsReduced = await o.page.evaluate(() => [...document.querySelectorAll('.pill, .seg label span')].map((e) => getComputedStyle(e).transitionDuration));
  await finish(o);

  o = await open({ name: 'no-js', js: false });
  result.noscript = await o.page.evaluate(() => ({
    note: [...document.querySelectorAll('.nojs')].map((p) => p.textContent),
    controlsVisible: [...document.querySelectorAll('.controls')].some((e) => getComputedStyle(e).display !== 'none'),
    visibleSteps: [...document.querySelectorAll('section.step')].filter((e) => getComputedStyle(e).display !== 'none').map((e) => e.dataset.state),
  }));
  await finish(o);

  // every step through every control: radios (click and keys), Next to the end, Previous to the start
  o = await open({ name: 'steps-1440-light' });
  const p = o.page;
  const steps = [{ action: 'load', want: S[0], snap: await p.evaluate(snapStepper) }];
  for (let i = 1; i < S.length; i++) {
    await p.click('#s-next');
    steps.push({ action: `next to ${i + 1}`, want: S[i], snap: await p.evaluate(snapStepper) });
  }
  for (let i = S.length - 2; i >= 0; i--) {
    await p.click('#s-prev');
    steps.push({ action: `previous to ${i + 1}`, want: S[i], snap: await p.evaluate(snapStepper) });
  }
  for (const [i, sid] of S.entries()) {
    await p.click(`#s-steps label:has(input[value="${sid}"])`);
    steps.push({ action: `radio ${i + 1}`, want: sid, snap: await p.evaluate(snapStepper) });
  }
  result.steps = steps;
  await finish(o);

  // the knob (round 18): every value, every call step, the slider check points and corners
  if (job.knob) {
    o = await open({ name: 'knob-1440-light' });
    const q = o.page, rec = [];
    if (job.knob.kind === 'values') {
      for (const v of job.knob.values) {
        await q.click(`#k-vals label:has(input[value="${v}"])`);
        rec.push({ value: v, ...(await q.evaluate(snapKnobValues)) });
      }
    } else if (job.knob.kind === 'calls') {
      for (const v of job.knob.values) {
        await q.click(`#k-vals label:has(input[value="${v}"])`);
        for (let i = 0; i < 40 && !(await q.$eval('#k-prev', (b) => b.disabled)); i++) await q.click('#k-prev');
        for (let i = 0; i < 40; i++) {
          rec.push({ value: v, ...(await q.evaluate(snapKnobCalls)) });
          if (await q.$eval('#k-next', (b) => b.disabled)) break;
          await q.click('#k-next');
        }
      }
    } else {
      for (const pt of job.knob.points) {
        await q.evaluate(([i, j]) => window.__ptkKnob.set(i, j), [pt.w2, pt.b]);
        rec.push(await q.evaluate(snapKnobNeuron));
      }
      // and one real slider move from the keyboard
      await q.focus('#k-b');
      await q.keyboard.press('ArrowLeft');
      rec.push({ ...(await q.evaluate(snapKnobNeuron)), via: 'keyboard' });
    }
    result.knob = rec;
    await finish(o);
  }

  result.layout = [];
  for (const width of [390, 1440]) {
    for (const scheme of ['light', 'dark']) {
      o = await open({ name: `layout-${width}-${scheme}`, width, height: width === 390 ? 844 : 900, scheme });
      for (const [i, sid] of S.entries()) {
        await o.page.click(`#s-steps label:has(input[value="${sid}"])`);
        const snap = await o.page.evaluate(snapStepper);
        const lay = await o.page.evaluate(layoutProbe);
        if (snap.panelTheme !== scheme) lay.problems.push({ kind: 'panel-theme', shown: snap.panelTheme, scheme });
        if (snap.panelLayout !== (width < 860 ? 'portrait' : 'wide')) lay.problems.push({ kind: 'panel-layout', shown: snap.panelLayout });
        result.layout.push({ width, scheme, n: i + 1, brk: null, ...lay });
        if (job.shots && (i === S.length - 1 || i === Math.floor(S.length / 2))) {
          mkdirSync(job.shots, { recursive: true });
          await o.page.mouse.move(0, 0);
          await o.page.waitForTimeout(300);
          await o.page.screenshot({ path: `${job.shots}/explorer-${width}-${scheme}${i === S.length - 1 ? '' : '-mid'}.png`, fullPage: true });
        }
      }
      await finish(o);
    }
  }
}

// ---------------------------------------------------------------- Q&A

function snapQa() {
  return {
    layers: [...document.querySelectorAll('[data-layer]')].map((l) => ({
      i: +l.dataset.layer, open: l.dataset.open === 'true',
      bodyVisible: (() => { const b = l.querySelector('.layer-body'); return !!b && getComputedStyle(b).display !== 'none' && b.getBoundingClientRect().height > 0; })(),
      revealDisabled: (() => { const b = l.querySelector('button.reveal'); return b ? b.disabled : null; })(),
      text: l.querySelector('.layer-body') ? l.querySelector('.layer-body').textContent : '' })),
    feedback: (() => {
      const f = document.getElementById('qa-feedback');
      if (!f) return null;
      const vis = (e) => getComputedStyle(e).display !== 'none' && e.getBoundingClientRect().height > 0;
      return { kind: f.dataset.kind || null, entries: [...f.querySelectorAll('li[data-opt]')].map((li) => ({
        opt: li.dataset.opt, visible: vis(li),
        items: [...li.querySelectorAll('[data-chrome],[data-claim],[data-misconception],[data-fact],[data-option]')].map((e) => ({
          chrome: e.dataset.chrome || null, claim: e.dataset.claim || null, misconception: e.dataset.misconception || null,
          fact: e.dataset.fact || null, option: e.dataset.option || null, text: e.textContent })) })) };
    })(),
    checkDisabled: document.getElementById('qa-check') ? document.getElementById('qa-check').disabled : null,
    titles: [...document.querySelectorAll('[data-layer] h3[data-label="scene-title"]')].map((h) => ({ text: h.textContent,
      visible: getComputedStyle(h).display !== 'none' && h.getBoundingClientRect().height > 0 })),
  };
}

async function qa() {
  let o = await open({ name: 'qa-1440-light' });
  const p = o.page;
  result.a11y = await p.evaluate(a11yProbe);
  if (!result.a11y.jsClass) { result.scriptBlocked = true; await finish(o); return; }
  const seq = [];
  seq.push({ action: 'load', snap: await p.evaluate(snapQa) });
  // try to open layer 2 before predicting
  const r2 = p.locator('[data-layer="2"] button.reveal');
  if (await r2.count()) { await r2.click({ force: true, timeout: 2000 }).catch(() => {}); }
  seq.push({ action: 'reveal 2 before predicting', snap: await p.evaluate(snapQa) });
  const options = await p.$$eval('#qa-options input', (xs) => xs.map((x) => x.value));
  for (const v of options) {
    await p.check(`#qa-options input[value="${v}"]`);
    await p.click('#qa-check');
    seq.push({ action: `choose ${v}`, option: v, snap: await p.evaluate(snapQa) });
  }
  const n = await p.$$eval('[data-layer]', (xs) => xs.length);
  // out of order: try the last layer first, then open in order
  const last = p.locator(`[data-layer="${n}"] button.reveal`);
  if (n > 2 && await last.count()) { await last.click({ force: true, timeout: 2000 }).catch(() => {}); seq.push({ action: `reveal ${n} out of order`, snap: await p.evaluate(snapQa) }); }
  for (let i = 2; i <= n; i++) {
    await p.focus(`[data-layer="${i}"] button.reveal`).catch(() => {});
    await p.keyboard.press('Enter');
    seq.push({ action: `reveal ${i} (keyboard)`, snap: await p.evaluate(snapQa) });
  }
  result.sequence = seq;
  result.focusRing = await p.evaluate(() => { const b = document.querySelector('button'); b.focus(); const s = getComputedStyle(b); return `${s.outlineStyle} ${s.outlineWidth}`; });
  await finish(o);

  o = await open({ name: 'qa-print' });
  await o.page.emulateMedia({ media: 'print' });
  result.print = await o.page.evaluate(snapQa);
  if (job.shots) { mkdirSync(job.shots, { recursive: true }); await o.page.pdf({ path: `${job.shots}/qa-print.pdf` }).catch(() => {}); }
  await finish(o);

  o = await open({ name: 'qa-no-js', js: false });
  result.noscript = await o.page.evaluate(snapQa);
  result.noscript.note = await o.page.evaluate(() => [...document.querySelectorAll('.nojs')].map((e) => e.textContent));
  await finish(o);

  o = await open({ name: 'qa-reduced', reducedMotion: 'reduce' });
  result.transitionsReduced = await o.page.evaluate(() => [...document.querySelectorAll('.pill, .opt span')].map((e) => getComputedStyle(e).transitionDuration));
  await finish(o);

  result.layout = [];
  for (const width of [390, 1440]) {
    for (const scheme of ['light', 'dark']) {
      o = await open({ name: `qa-${width}-${scheme}`, width, height: width === 390 ? 844 : 900, scheme });
      await o.page.check('#qa-options input >> nth=0');
      await o.page.click('#qa-check');
      for (let i = 2; i <= n; i++) await o.page.click(`[data-layer="${i}"] button.reveal`);
      result.layout.push({ width, scheme, ...(await o.page.evaluate(layoutProbe)) });
      if (job.shots) await o.page.screenshot({ path: `${job.shots}/qa-${width}-${scheme}.png`, fullPage: true });
      await finish(o);
    }
  }
}

try {
  if (job.mode === 'explorer') await explorer();
  else if (job.mode === 'qa') await qa();
  else if (job.mode === 'stepper') await stepper();
  else throw new Error(`unknown mode ${job.mode}`);
  result.ok = true;
} catch (e) {
  result.ok = false;
  result.error = String((e && e.stack) || e);
}
await browser.close();
writeFileSync(outPath, JSON.stringify(result, null, 1));
