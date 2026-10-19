#!/usr/bin/env node
// Render a built explorable's film frame by frame (used by narrate.py).
//
//   node film_export.mjs lesson.html --scenes                         # print the scenes as JSON
//   node film_export.mjs lesson.html --timing t.json --out frames/ [--fps 24] [--board paper|chalk]
//
// timing.json: { scenes: [{ start, dur }], total }. Writes frames/000000.png...
// and frames/marks.json: per scene, how many marks the pen draws (for the
// chalk or pencil sound track).

import { pathToFileURL } from "node:url";
import { resolve, join } from "node:path";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { loadPlaywright, launch } from "../../visual-qa/scripts/pw.mjs";

const args = process.argv.slice(2);
const opt = (n, d) => (args.includes(n) ? args[args.indexOf(n) + 1] : d);
const file = args[0];
const { chromium } = await loadPlaywright();
const browser = await launch(chromium);
const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1, colorScheme: opt("--board", "paper") === "chalk" ? "dark" : "light", reducedMotion: "no-preference" });
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(`${pathToFileURL(resolve(file)).href}?film-export`);
await page.waitForFunction(() => window.__filmExport);
await page.evaluate(() => document.fonts.ready);
if (args.includes("--scenes")) {
  console.log(JSON.stringify(await page.evaluate(() => ({ title: window.__filmExport.title, scenes: window.__filmExport.scenes }))));
  await browser.close();
  process.exit(errors.length ? 1 : 0);
}
const timing = JSON.parse(readFileSync(opt("--timing"), "utf8"));
const out = opt("--out");
const fps = Number(opt("--fps", 24));
mkdirSync(out, { recursive: true });
const frames = Math.ceil(timing.total * fps);
const marks = timing.scenes.map(() => 0);
let n = 0;
for (let f = 0; f < frames; f++) {
  const t = f / fps;
  let i = timing.scenes.findLastIndex((s) => s.start <= t);
  if (i < 0) i = 0;
  const sc = timing.scenes[i];
  const u = Math.max(0, Math.min(1, (t - sc.start) / sc.dur));
  // Caption written line by line as the voice speaks it.
  const voiceAt = sc.voiceAt ?? sc.start + 0.7;
  const cu = t < voiceAt ? 0 : sc.voiceDur ? Math.max(0.12, Math.min(1, (t - voiceAt + 0.2) / sc.voiceDur)) : 1;
  // Settle all parameters before the first spoken/captioned claim. A fixed
  // fraction of scene duration can keep stale values visible for seconds.
  const settleDuration = Math.max(1 / fps, voiceAt - sc.start - 0.1);
  const settled = Math.max(0, Math.min(1, (t - sc.start) / settleDuration));
  const info = await page.evaluate(([k, uu, c, ss]) => window.__filmExport.frame(k, uu, c, ss), [i, u, cu, settled]);
  marks[i] = Math.max(marks[i], info.marks.length);
  await page.screenshot({ path: join(out, `${String(n++).padStart(6, "0")}.png`) });
}
writeFileSync(join(out, "marks.json"), JSON.stringify({ fps, frames: n, marks }));
await browser.close();
if (errors.length) {
  console.error(errors.join("\n"));
  process.exit(1);
}
console.log(`rendered ${n} frames`);
