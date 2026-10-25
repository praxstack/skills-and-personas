#!/usr/bin/env node
// Focused real-Chromium regression fixture. Uses only provisioned Playwright.
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdtemp, rm, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';
import { createServer } from 'node:http';
import { loadPlaywright, launch } from '../../skills/visual-qa/scripts/pw.mjs';
import { videoLesson } from '../../skills/explorable/scripts/bundle_templates.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const folder = await mkdtemp(join(tmpdir(), 'reading-themes-'));
const screenshots = process.argv[2] ? resolve(process.argv[2]) : null;
const palettes = JSON.parse(await readFile(join(root, 'assets/reading-themes/themes.json'), 'utf8')).palettes;
const notebook = (await readFile(join(root, 'skills/lesson-notebook/assets/notebook.css'), 'utf8')).replace(/@font-face\s*\{[^}]*\}/g, '');
const courseCSS = await readFile(join(root, 'skills/course/assets/engine/course.css'), 'utf8');
const boardTitle = 'Switch between paper, chalkboard, and following your theme';
const markup = `<!doctype html><html><head><meta charset="utf-8"><title>Theme fixture</title>
<script>window.beforeEngine={theme:document.documentElement.dataset.readingTheme,paper:getComputedStyle(document.documentElement).getPropertyValue('--paper').trim()}</script>
<style>${notebook}\nmain{max-width:800px;margin:40px auto;padding-bottom:70px}svg{width:100%;max-width:600px}a{display:inline-block;margin:8px}.fixture-panel{padding:16px;background:var(--card);border:1px solid var(--rule)}</style>
<script>document.documentElement.dataset.board='chalk';</script></head><body><main>
<h1>What a boundary changes</h1><p>A reading fixture keeps model colors and plotted geometry.</p>
<div class="fixture-panel"><p style="color:var(--muted)">A secondary explanation on a panel.</p>
<svg viewBox="0 0 600 180" role="img" aria-label="Three semantic curves"><path id="geometry" d="M20 140 L220 40 L420 140" style="stroke:var(--blue);fill:none;stroke-width:4"/><path d="M20 160 L220 60 L420 160" style="stroke:var(--red);fill:none;stroke-width:4"/><path d="M40 160 L240 60 L440 160" style="stroke:var(--green);fill:none;stroke-width:4"/><text x="24" y="28" style="fill:var(--ink);font-size:20px">Semantic blue, coral and green</text></svg></div>
<button title="${boardTitle}">Board: chalk</button><button title="Board">Unrelated board control</button>
<a id="local" href="next.html?lesson=2#proof">Next lesson</a><a id="external" href="https://example.org/source.html?source=1#fact">Source</a><a id="fragment" href="#proof">In-page</a><a id="media" href="data:video/mp4,AAAA">Media data</a><a id="download" download href="notes.html?keep=1">Download</a>
</main></body></html>`;
const build = async (name, source, direct = false) => {
  const path = join(folder, name);
  await writeFile(path, source);
  const directScript = 'import importlib.util,sys; from pathlib import Path; s=importlib.util.spec_from_file_location("themes",sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); p=Path(sys.argv[2]); p.write_bytes(m.embed_reading_themes(p.read_bytes().decode("utf-8")).encode("utf-8"))';
  const args = direct ? ['-c', directScript, join(root, 'scripts/embed_reading_themes.py'), path] : [join(root, 'scripts/embed_reading_themes.py'), path, '-o', path];
  const result = spawnSync(process.env.PYTHON || 'python3', args, { encoding: 'utf8' });
  assert.equal(result.status, 0, result.stderr);
};
const headless = [
  '<!doctype html><title>T</title><p>Lesson</p>',
  '<!-- Before -->\n<!DOCTYPE html>\n<!-- After -->\n<title>T</title><p>Lesson</p>',
  '<!doctype html>Lesson'
];
for (const [i, source] of headless.entries()) {
  await writeFile(join(folder, `headless-original-${i}.html`), source);
  await build(`headless-embedded-${i}.html`, source);
}
const exportedVideo = videoLesson({title:'Exported reading surfaces',subtitle:'Actual export-template contrast fixture',sources:[],video:{captions:'WEBVTT\n\n1\n00:00:00.000 --> 00:00:01.000\nA readable caption.\n',scenes:[{start:0,dur:1,chapter:'Boundary',say:'A readable caption.',step:0,params:{}}]}});
await writeFile(join(folder, 'export-original.html'), exportedVideo);
await writeFile(join(folder, 'explorer.html'), '<!doctype html><title>Local fixture explorer</title>');
await build('export.html', exportedVideo);
await build('lesson.html', markup);
await build('next.html', markup);
await build('blocked.html', markup.replace('<meta charset="utf-8">', '<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src \'none\'; script-src \'none\'; style-src \'none\'">'));
await build('primary.html', `<!doctype html><html><head><meta charset="utf-8"><style>${notebook}\n${courseCSS}</style></head><body><main><div class="cs-actions"><a id="primary" class="nb-btn nb-btn-primary" href="next.html">Teach me (interactive)</a></div></main></body></html>`);
await build('svg-authored.html', '<!doctype html><html><head><meta charset="utf-8"></head><body><svg><a id="svg-course" href="next.html?keep=1#svg"><text x="10" y="30">Next</text></a></svg></body></html>');
await build('svg-dynamic.html', '<!doctype html><html><head><meta charset="utf-8"></head><body></body></html>');
const separatorFixtures = [];
for (const [i, separator] of ['\r','\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029'].entries()) {
  for (const blocked of [false, true]) {
    const policy = blocked ? "default-src 'none'; script-src 'none'; style-src 'none'" : "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'";
    const name = `separator-${i}-${blocked}.html`;
    await build(name, `<!doctype html><!-- α${separator}β -->\n<html><head><!-- γ${separator}δ -->\n<meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="${policy}"></head><body><p id="copy">Lesson π</p></body></html>`, true);
    separatorFixtures.push({ name, blocked, separator: JSON.stringify(separator), policy });
  }
}
const requests = [];
const server = createServer(async (req, res) => {
  const path = new URL(req.url, 'http://localhost').pathname;
  requests.push(path);
  if (!['/lesson.html', '/next.html', '/blocked.html'].includes(path)) { res.writeHead(404).end(); return; }
  res.setHeader('Content-Type', 'text/html; charset=utf-8');
  res.end(await readFile(join(folder, path.slice(1))));
});
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const origin = `http://127.0.0.1:${server.address().port}`;
let browser;
const results = [];
const contrast = (foreground, background) => {
  const luminance = color => color.match(/[\d.]+/g).slice(0, 3).map(Number).map(c => c / 255).map(c => c <= .04045 ? c / 12.92 : ((c + .055) / 1.055) ** 2.4).reduce((sum, c, i) => sum + c * [.2126, .7152, .0722][i], 0);
  const [low, high] = [luminance(foreground), luminance(background)].sort((a, b) => a - b);
  return (high + .05) / (low + .05);
};
const rgb = hex => `rgb(${[1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16)).join(', ')})`;
try {
  browser = await launch((await loadPlaywright()).chromium);
  const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, colorScheme: 'light', reducedMotion: 'reduce' });
  const modePage = await context.newPage();
  for (const i of headless.keys()) {
    const modes = [];
    for (const variant of ['original', 'embedded']) {
      await modePage.goto(pathToFileURL(join(folder, `headless-${variant}-${i}.html`)).href);
      modes.push(await modePage.evaluate(() => ({ mode: document.compatMode, doctype: document.doctype?.name ?? null })));
      if (variant === 'embedded') assert.equal(await modePage.evaluate(() => window.__readingThemes.current), null);
    }
    assert.deepEqual(modes, [{ mode: 'CSS1Compat', doctype: 'html' }, { mode: 'CSS1Compat', doctype: 'html' }]);
  }
  await modePage.close();
  results.push('Omitted html/head tags preserve the prolog, actual doctype and CSS1Compat');
  await context.addInitScript(() => {
    window.themeStorageCalls = [];
    for (const method of ['getItem', 'setItem', 'removeItem', 'clear']) {
      const original = Storage.prototype[method];
      Storage.prototype[method] = function (...args) { window.themeStorageCalls.push(method); return original.apply(this, args); };
    }
    const cookie = Object.getOwnPropertyDescriptor(Document.prototype, 'cookie');
    Object.defineProperty(document, 'cookie', { get() { window.themeStorageCalls.push('cookie:get'); return cookie.get.call(this); }, set(value) { window.themeStorageCalls.push('cookie:set'); return cookie.set.call(this, value); } });
  });
  await context.route('https://**/*', route => { throw Error(`Unexpected external request: ${route.request().url()}`); });
  const round2Failures = [];
  const round2Evidence = { svg: [], primaryMinimum: Infinity, separators: [] };
  // Bounded watchdog: suppress after 20 SVG href writes so a regression cannot
  // trap Chromium in an unbounded observer microtask loop.
  const svgContext = await browser.newContext();
  await svgContext.addInitScript(() => {
    window.svgWrites = { count: 0, tripped: false };
    const original = Element.prototype.setAttribute;
    Element.prototype.setAttribute = function (name, value) {
      if (this instanceof SVGAElement && name === 'href') {
        window.svgWrites.count++;
        if (window.svgWrites.count > 20) { window.svgWrites.tripped = true; return; }
      }
      return original.call(this, name, value);
    };
  });
  for (const variant of ['authored', 'dynamic']) {
    const svgPage = await svgContext.newPage();
    await svgPage.goto(pathToFileURL(join(folder, `svg-${variant}.html`)).href);
    const observed = await svgPage.evaluate(async variant => {
      if (variant === 'dynamic') {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        const a = document.createElementNS(svg.namespaceURI, 'a'); a.id='svg-course';
        a.setAttribute('href', 'next.html?keep=1#svg'); svg.append(a); document.body.append(svg);
      }
      window.__readingThemes.apply('graphite');
      await new Promise(resolve => setTimeout(resolve, 20));
      const settled = window.svgWrites.count;
      window.__readingThemes.apply('graphite');
      await new Promise(resolve => setTimeout(resolve, 20));
      const a = document.getElementById('svg-course');
      return { variant, ...window.svgWrites, settled, hrefType: Object.prototype.toString.call(a.href), href: a.getAttribute('href') };
    }, variant);
    round2Evidence.svg.push(observed);
    if (observed.tripped || observed.count !== observed.settled || observed.count > 3) round2Failures.push({ finding:'SVG observer loop', ...observed });
    else {
      assert.equal(observed.hrefType, '[object SVGAnimatedString]');
      const href = new URL(observed.href); assert.equal(href.searchParams.get('theme'), 'graphite'); assert.equal(href.searchParams.get('keep'), '1'); assert.equal(href.hash, '#svg');
      await svgPage.getByRole('button', {name:'Reading theme: Graphite'}).click();
      await svgPage.getByRole('button', {name:'Done', exact:true}).click();
      assert.equal(await svgPage.evaluate(() => document.activeElement.classList.contains('rt-launch')), true);
      await svgPage.evaluate(() => window.__readingThemes.apply(null));
      assert.equal(new URL(await svgPage.locator('#svg-course').getAttribute('href')).searchParams.has('theme'), false);
      const resetWrites = await svgPage.evaluate(async () => { await new Promise(resolve => setTimeout(resolve, 20)); return window.svgWrites; });
      assert.equal(resetWrites.tripped, false); assert.equal(resetWrites.count, observed.count + 1);
    }
    await svgPage.close();
  }
  await svgContext.close();
  const primaryPage = await context.newPage();
  await primaryPage.goto(pathToFileURL(join(folder, 'primary.html')).href);
  const primary = primaryPage.locator('#primary');
  for (const scheme of ['light', 'dark']) {
    await primaryPage.emulateMedia({colorScheme:scheme});
    for (const palette of palettes) {
      await primaryPage.evaluate(id => window.__readingThemes.apply(id), palette.id);
      for (const state of ['normal', 'hover', 'focus']) {
        await primaryPage.mouse.move(0, 0); await primary.evaluate(node => node.blur());
        if (state === 'hover') await primary.hover();
        if (state === 'focus') {
          await primaryPage.keyboard.press('Tab'); await primary.focus();
          assert.equal(await primary.evaluate(node => node.matches(':focus-visible')), true);
          assert.ok(await primary.evaluate(node => parseFloat(getComputedStyle(node).outlineWidth) >= 3));
        }
        const colors = await primary.evaluate(node => { const s=getComputedStyle(node); return {foreground:s.color, background:s.backgroundColor}; });
        const ratio = contrast(colors.foreground, colors.background);
        round2Evidence.primaryMinimum = Math.min(round2Evidence.primaryMinimum, ratio);
        if (ratio < 7) round2Failures.push({finding:'Course primary link contrast', scheme, palette:palette.id, state, ...colors, contrast:ratio});
      }
    }
  }
  await primaryPage.close();
  const separatorPage = await context.newPage();
  for (const fixture of separatorFixtures) {
    await separatorPage.goto(pathToFileURL(join(folder, fixture.name)).href);
    const observed = await separatorPage.evaluate(() => ({mode:document.compatMode,doctype:document.doctype?.name,copy:document.getElementById('copy')?.textContent,api:typeof window.__readingThemes,policy:document.querySelector('meta[http-equiv="Content-Security-Policy"]')?.content}));
    if (observed.mode !== 'CSS1Compat' || observed.doctype !== 'html' || observed.copy !== 'Lesson π' || observed.api !== (fixture.blocked ? 'undefined' : 'object') || observed.policy !== fixture.policy) round2Failures.push({finding:'LF offset/CSP preservation', ...fixture, ...observed});
    round2Evidence.separators.push({...fixture,...observed});
  }
  await separatorPage.close();
  console.log(JSON.stringify({round2Evidence:{svg:round2Evidence.svg, primaryMinimum:round2Evidence.primaryMinimum, separatorFixtures:round2Evidence.separators.length}, round2Failures}, null, 2));
  assert.deepEqual(round2Failures, []);
  results.push('Authored/dynamic SVG anchors settle with responsive controls; actual notebook/course primary links >=7:1 in normal/hover/focus; Unicode/control/CR separator CSP and standards mode preserved');
  const page = await context.newPage();
  const errors = [];
  page.on('pageerror', error => errors.push(String(error)));
  await page.goto(`${origin}/lesson.html?unit=3#proof`);
  assert.equal(await page.evaluate(() => window.__readingThemes.current), null);
  assert.equal(await page.locator('html').getAttribute('data-reading-theme'), null);
  assert.equal(await page.evaluate(() => location.search + location.hash), '?unit=3#proof');
  assert.equal(await page.locator(`[title="${boardTitle}"]`).isVisible(), true);
  assert.deepEqual(await page.evaluate(() => window.themeStorageCalls), []);
  assert.equal(await context.cookies().then(c => c.length), 0);
  const original = await page.evaluate(() => ({ paper: getComputedStyle(document.body).backgroundColor, font: getComputedStyle(document.body).fontFamily, geometry: document.getElementById('geometry').getAttribute('d') }));
  assert.equal(await page.evaluate(() => Object.isFrozen(window.__readingThemes) && Object.isFrozen(window.__readingThemes.palettes) && window.__readingThemes.palettes.every(Object.isFrozen)), true);
  assert.equal(await page.evaluate(() => { try { window.__readingThemes.apply('invalid'); return false; } catch (e) { return e instanceof RangeError; } }), true);
  results.push('Original default, read-only API, zero storage/cookies');
  const exportPage = await context.newPage();
  await exportPage.goto(pathToFileURL(join(folder, 'export-original.html')).href);
  assert.equal(await exportPage.evaluate(() => getComputedStyle(document.querySelector('.note')).backgroundColor), rgb('#edf2ec'));
  await exportPage.goto(pathToFileURL(join(folder, 'export.html')).href);
  let exportMin = Infinity;
  const exportSurfaces = async () => exportPage.evaluate(() => ['.note', '#readable-captions', '.chapters button[aria-current="true"]'].map(selector => {
    const node = document.querySelector(selector), style = getComputedStyle(node);
    return { selector, foreground: style.color, background: style.backgroundColor };
  }));
  for (const scheme of ['light', 'dark']) {
    await exportPage.emulateMedia({ colorScheme: scheme });
    for (const palette of palettes) {
      await exportPage.evaluate(id => window.__readingThemes.apply(id), palette.id);
      const surfaces = await exportSurfaces();
      for (const surface of surfaces) {
        const ratio = contrast(surface.foreground, surface.background);
        exportMin = Math.min(exportMin, ratio);
        assert.ok(ratio >= 7, JSON.stringify({template:'videoLesson',scheme,palette:palette.id,...surface,contrast:ratio}));
        assert.equal(surface.background, rgb(palette.panel));
      }
    }
  }
  await exportPage.evaluate(() => window.__readingThemes.apply('graphite'));
  await exportPage.emulateMedia({ media: 'print', colorScheme: 'light' });
  for (const surface of await exportSurfaces()) {
    assert.equal(surface.background, rgb('#f3f4f5'));
    assert.ok(contrast(surface.foreground, surface.background) >= 7, JSON.stringify(surface));
  }
  await exportPage.emulateMedia({ media: 'screen' });
  await exportPage.evaluate(() => { document.getElementById('readable-captions').textContent='A readable caption.'; });
  if (screenshots) {
    await mkdir(screenshots, { recursive: true });
    await exportPage.screenshot({ path: join(screenshots, 'actual-export-graphite.png'), fullPage: true });
  }
  await exportPage.evaluate(() => window.__readingThemes.apply(null));
  for (const surface of await exportSurfaces()) assert.equal(surface.background, rgb('#edf2ec'));
  await exportPage.close();
  results.push(`Actual videoLesson export note/captions/current chapter: all palettes/device schemes and print, minimum contrast ${exportMin.toFixed(3)}:1`);

  const launcher = page.getByRole('button', { name: 'Reading theme: Original', exact: true });
  await launcher.click();
  const dialog = page.getByRole('dialog', { name: 'Reading themes', exact: true });
  await dialog.waitFor({ state: 'visible' });
  assert.equal(await dialog.getByRole('group', { name: 'Dark', exact: true }).getByRole('radio').count(), 5);
  assert.equal(await dialog.getByRole('group', { name: 'Night', exact: true }).getByRole('radio').count(), 5);
  for (const scheme of ['light', 'dark']) {
    await page.emulateMedia({ colorScheme: scheme });
    for (const palette of palettes) {
      await dialog.getByRole('radio', { name: palette.name, exact: true }).check();
      const observed = await page.evaluate(() => {
        const style = getComputedStyle(document.documentElement);
        return { current: window.__readingThemes.current, ink: getComputedStyle(document.body).color, panelInk: getComputedStyle(document.querySelector('.fixture-panel')).color, muted: getComputedStyle(document.querySelector('.fixture-panel p')).color, bg: getComputedStyle(document.body).backgroundColor, panel: getComputedStyle(document.querySelector('.fixture-panel')).backgroundColor,
          blue: getComputedStyle(document.getElementById('geometry')).stroke, red: style.getPropertyValue('--red').trim(), green: style.getPropertyValue('--green').trim(), grain: style.getPropertyValue('--stroke-grain').trim(), grid: style.getPropertyValue('--grid').trim(), font: getComputedStyle(document.body).fontFamily, geometry: document.getElementById('geometry').getAttribute('d'), url: location.href, local: document.getElementById('local').href,
          external: document.getElementById('external').getAttribute('href'), fragment: document.getElementById('fragment').getAttribute('href'), media: document.getElementById('media').getAttribute('href'), download: document.getElementById('download').getAttribute('href') };
      });
      assert.equal(observed.current, palette.id);
      assert.equal(observed.bg, rgb(palette.bg));
      assert.equal(observed.panel, rgb(palette.panel));
      for (const [foreground, background, floor] of [[observed.ink, observed.bg, 7], [observed.panelInk, observed.panel, 7], [observed.muted, observed.panel, 4.5]]) {
        const ratio = contrast(foreground, background);
        assert.ok(ratio >= floor, JSON.stringify({ scheme, palette: palette.id, foreground, background, floor, contrast: ratio }));
      }
      assert.equal(observed.blue, rgb(palette.group === 'Night' ? '#adc7e6' : '#9ecbff'));
      assert.equal(observed.red, '#efaa9f'); assert.equal(observed.green, '#afd2a6');
      assert.equal(observed.grain, 'none'); assert.equal(observed.grid, 'transparent');
      assert.equal(observed.font, original.font); assert.equal(observed.geometry, original.geometry);
      assert.equal(new URL(observed.url).searchParams.get('unit'), '3');
      assert.equal(new URL(observed.url).hash, '#proof');
      assert.equal(new URL(observed.local).searchParams.get('theme'), palette.id);
      assert.equal(new URL(observed.local).searchParams.get('lesson'), '2');
      assert.equal(new URL(observed.local).hash, '#proof');
      assert.equal(observed.external, 'https://example.org/source.html?source=1#fact');
      assert.equal(observed.fragment, '#proof'); assert.equal(observed.media, 'data:video/mp4,AAAA'); assert.equal(observed.download, 'notes.html?keep=1');
      assert.equal(await page.locator(`[title="${boardTitle}"]`).isVisible(), false);
      assert.equal(await page.locator('[title="Board"]').isVisible(), true, 'Only the exact known Board selector is hidden');
      assert.equal(await page.evaluate(() => { const b = document.querySelector('[title="Board"]'); b.focus(); return document.activeElement === b; }), false, 'Background controls must be inert inside modal');
      assert.equal(await dialog.getByRole('radio', { checked: true }).count(), 1);
      if (screenshots && scheme === 'light') {
        await mkdir(screenshots, { recursive: true });
        await page.screenshot({ path: join(screenshots, `${palette.id}-desktop.png`) });
      }
    }
  }
  results.push('All ten palettes in system light/dark, semantic SVG colors, unchanged typography/geometry, URL/link boundaries');

  await dialog.getByRole('radio', { name: 'Graphite', exact: true }).focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.evaluate(() => window.__readingThemes.current), 'slate');
  await page.keyboard.press('ArrowLeft');
  assert.equal(await page.evaluate(() => window.__readingThemes.current), 'graphite');
  // Tab trapping is native modal behavior; repeated tabbing cannot reach lesson controls.
  for (let i = 0; i < 15; i++) {
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement === document.body || !!document.activeElement.closest('dialog')), true);
  }
  await page.keyboard.press('Escape');
  assert.equal(await dialog.isVisible(), false);
  assert.equal(await page.evaluate(() => document.activeElement.classList.contains('rt-launch')), true);
  assert.equal(await page.locator('[title="Board"]').isVisible(), true);
  results.push('Native radios/arrows, modal tab boundary, Escape and focus return');

  await page.reload();
  assert.equal(await page.evaluate(() => window.__readingThemes.current), 'graphite');
  assert.deepEqual(await page.evaluate(() => window.beforeEngine), { theme: 'graphite', paper: '#202328' });
  assert.equal(await page.locator('html').getAttribute('data-board'), 'chalk');
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), rgb('#202328'));
  await page.evaluate(() => { const a = document.createElement('a'); a.id='dynamic'; a.href='next.html?dynamic=1#later'; a.textContent='Dynamic lesson'; document.querySelector('main').append(a); });
  await page.waitForFunction(() => new URL(document.getElementById('dynamic').href).searchParams.get('theme') === 'graphite');
  await page.locator('#local').click();
  assert.equal(new URL(page.url()).pathname, '/next.html');
  assert.equal(await page.evaluate(() => window.__readingThemes.current), 'graphite');
  await page.getByRole('button', { name: 'Reading theme: Graphite' }).click();
  await page.getByRole('button', { name: 'Original', exact: true }).click();
  assert.equal(await page.evaluate(() => window.__readingThemes.current), null);
  assert.equal(new URL(page.url()).searchParams.has('theme'), false);
  assert.equal(new URL(page.url()).searchParams.get('lesson'), '2');
  assert.equal(new URL(page.url()).hash, '#proof');
  assert.equal(await dialog.getByRole('radio', { checked: true }).count(), 0);
  await page.getByRole('button', { name: 'Done', exact: true }).click();
  assert.equal(await page.locator(`[title="${boardTitle}"]`).isVisible(), true);
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), original.paper);
  assert.equal(new URL(await page.locator('#local').getAttribute('href')).searchParams.has('theme'), false);
  assert.equal(await page.evaluate(() => document.activeElement.classList.contains('rt-launch')), true);
  results.push('Early apply survives board setup, reload, dynamic/course links, Original reset, Done focus return');

  await page.evaluate(() => window.__readingThemes.apply('amber'));
  await page.emulateMedia({ media: 'print' });
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).backgroundColor), 'rgb(255, 255, 255)');
  assert.equal(await page.evaluate(() => getComputedStyle(document.body).color), 'rgb(32, 35, 40)');
  assert.equal(await page.locator('.rt-launch').isVisible(), false);
  await page.emulateMedia({ media: 'screen' });
  assert.deepEqual(await page.evaluate(() => window.themeStorageCalls), []);
  assert.deepEqual(errors, []);
  results.push('Readable light print, no script errors, zero feature storage');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.getByRole('button', { name: 'Reading theme: Amber' }).click();
  for (const palette of palettes) {
    await dialog.getByRole('radio', { name: palette.name, exact: true }).check();
    const bounds = await page.evaluate(() => {
      const dialog = document.querySelector('dialog'), box = dialog.getBoundingClientRect();
      return { pageOverflow: document.documentElement.scrollWidth > innerWidth, dialogOverflow: dialog.scrollWidth > dialog.clientWidth, left: box.left, right: box.right,
        cards: [...dialog.querySelectorAll('.rt-card')].map(card => ({ height: card.getBoundingClientRect().height, width: card.getBoundingClientRect().width })),
        inputs: [...dialog.querySelectorAll('input')].map(input => ({ width: input.getBoundingClientRect().width, height: input.getBoundingClientRect().height, appearance: getComputedStyle(input).appearance })), motion: getComputedStyle(dialog).animationName };
    });
    assert.equal(bounds.pageOverflow, false); assert.equal(bounds.dialogOverflow, false);
    assert.ok(bounds.left >= 0 && bounds.right <= 390);
    assert.ok(bounds.cards.every(card => card.height >= 44 && card.width >= 44));
    assert.ok(bounds.inputs.every(input => input.width >= 24 && input.height >= 24 && input.appearance === 'auto'));
    assert.equal(bounds.motion, 'none');
  }
  if (screenshots) await page.screenshot({ path: join(screenshots, 'plum-mobile.png') });
  await page.keyboard.press('Escape');
  results.push('390px all-palette bounds, >=44px cards, >=24px native inputs, reduced motion');
  const blocked = await context.newPage();
  await blocked.goto(`${origin}/blocked.html?theme=amber`);
  assert.equal(await blocked.evaluate(() => typeof window.__readingThemes), 'undefined');
  assert.equal(await blocked.locator('.rt-launch').count(), 0);
  assert.equal(await blocked.locator('meta[http-equiv="Content-Security-Policy"]').getAttribute('content'), "default-src 'none'; script-src 'none'; style-src 'none'");
  results.push('Existing CSP remains blocking');
  const offline = await context.newPage();
  await offline.goto(pathToFileURL(join(folder, 'lesson.html')).href + '?unit=offline#proof');
  assert.equal(await offline.evaluate(() => window.__readingThemes.current), null);
  await offline.evaluate(() => window.__readingThemes.apply('moss'));
  assert.equal(new URL(offline.url()).searchParams.get('theme'), 'moss');
  assert.equal(new URL(await offline.locator('#local').getAttribute('href')).protocol, 'file:');
  assert.equal(new URL(await offline.locator('#local').getAttribute('href')).searchParams.get('theme'), 'moss');
  await offline.reload();
  assert.equal(await offline.evaluate(() => window.__readingThemes.current), 'moss');
  assert.equal(new URL(offline.url()).searchParams.get('unit'), 'offline');
  assert.equal(new URL(offline.url()).hash, '#proof');
  assert.deepEqual(await offline.evaluate(() => window.themeStorageCalls), []);
  results.push('Direct file:// offline URL persistence, reload and local links');
  assert.ok(requests.every(path => ['/lesson.html', '/next.html', '/blocked.html', '/favicon.ico'].includes(path)), requests.join(', '));
  console.log(JSON.stringify({ ok: true, palettes: palettes.length, checks: results, screenshots }, null, 2));
} finally {
  if (browser) await browser.close();
  await new Promise(resolve => server.close(resolve));
  await rm(folder, { recursive: true, force: true });
}
