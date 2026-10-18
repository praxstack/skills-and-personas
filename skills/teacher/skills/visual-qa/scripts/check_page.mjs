#!/usr/bin/env node
// Check a teaching page in real Chromium before a learner sees it.
//
//   node check_page.mjs page.html [--out shots/] [--board chalk] [--eval "expr"] [--all-steps] [--json]
//
// Runs desktop and phone, light and dark (prefers-color-scheme), with and
// without reduced motion. Fails on: console or page errors, sideways scroll,
// text under 4.5:1 contrast (3:1 for large text), text under 12px, tap targets
// under 24px, images or figures without a text alternative, controls without a
// name. --eval runs an expression in the page that returns a list of
// {name, ok} results (for example "window.__explorable.check()").
// --all-steps, on an explorable lesson, also audits every later step (not
// just the first screen) in the four runs with motion, with a screenshot each.
//
// Needs the playwright package (npm i playwright). Set CHROMIUM_PATH to use an
// already-installed Chromium instead of downloading one.

import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { mkdir } from "node:fs/promises";
import { loadPlaywright, launch } from "./pw.mjs";

const args = process.argv.slice(2);
const opt = (name, fallback) => {
  const i = args.indexOf(name);
  return i >= 0 ? args[i + 1] : fallback;
};
const target = args.find((a, i) => !a.startsWith("--") && !["--out", "--board", "--eval"].includes(args[i - 1]));
if (!target) {
  console.error("usage: node check_page.mjs <page.html|url> [--out dir] [--board chalk] [--eval expr] [--json]");
  process.exit(2);
}
const url = /^https?:|^file:/.test(target) ? target : pathToFileURL(resolve(target)).href;
const out = opt("--out");
const evalExpr = opt("--eval");
const board = opt("--board");
const asJson = args.includes("--json");
const allSteps = args.includes("--all-steps");

const VIEWS = [
  { name: "desktop", viewport: { width: 1280, height: 860 } },
  { name: "phone", viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, deviceScaleFactor: 2 },
];
const SCHEMES = ["light", "dark"];

// Runs inside the page. Returns a list of problems.
function audit() {
  const problems = [];
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  const rgba = (css) => {
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = "#000";
    ctx.fillStyle = css;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    return [r, g, b, a / 255];
  };
  const over = (top, bottom) => top.slice(0, 3).map((c, i) => c * top[3] + bottom[i] * (1 - top[3])).concat(1);
  const lum = ([r, g, b]) => {
    const f = (c) => ((c /= 255) <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4);
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const ratio = (a, b) => {
    const [x, y] = [lum(a), lum(b)].sort((m, n) => n - m);
    return (x + 0.05) / (y + 0.05);
  };
  function background(el) {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const c = rgba(getComputedStyle(n).backgroundColor);
      if (c[3] > 0) layers.push(c);
      if (c[3] >= 1) break;
    }
    let base = [255, 255, 255, 1];
    for (const layer of layers.reverse()) base = over(layer, base);
    return base;
  }
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    const st = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && st.visibility !== "hidden" && st.display !== "none" && Number(st.opacity) > 0.05;
  };
  const describe = (el) => `${el.tagName.toLowerCase()}${el.id ? `#${el.id}` : ""}${el.className && typeof el.className === "string" ? `.${el.className.trim().split(/\s+/).join(".")}` : ""} "${(el.textContent || "").trim().slice(0, 40)}"`;

  const doc = document.scrollingElement || document.documentElement;
  if (doc.scrollWidth > window.innerWidth + 1) problems.push(`sideways scroll: page is ${doc.scrollWidth}px wide in a ${window.innerWidth}px window`);

  const seen = new Set();
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const node = walker.currentNode;
    if (!node.data.trim()) continue;
    const el = node.parentElement;
    if (!el || seen.has(el) || el.closest("svg, script, style, noscript, [hidden], .sr-only, option")) continue;
    seen.add(el);
    if (!visible(el)) continue;
    const st = getComputedStyle(el);
    const size = parseFloat(st.fontSize);
    if (size < 12) problems.push(`small text (${size}px): ${describe(el)}`);
    const fg = rgba(st.color);
    const bg = background(el);
    const r = ratio(over(fg, bg), bg);
    const large = size >= 24 || (size >= 18.66 && Number(st.fontWeight) >= 700);
    const need = large ? 3 : 4.5;
    if (r < need - 0.05) problems.push(`contrast ${r.toFixed(2)}:1 (needs ${need}): ${describe(el)}`);
  }
  for (const el of document.querySelectorAll("button, a[href], input:not([type=hidden]), select, textarea, summary, [role=tab]")) {
    if (!visible(el)) continue;
    const r = el.getBoundingClientRect();
    const inline = el.tagName === "A" && getComputedStyle(el).display === "inline";
    if (!inline && (r.width < 24 || r.height < 24)) problems.push(`tap target ${Math.round(r.width)}x${Math.round(r.height)}: ${describe(el)}`);
    const labelled = el.getAttribute("aria-label") || el.getAttribute("aria-labelledby") || el.title || (el.labels && el.labels.length) || (el.textContent || "").trim() || el.getAttribute("placeholder") || (el.tagName === "INPUT" && ["submit", "button", "reset"].includes(el.type) && el.value);
    if (!labelled) problems.push(`control without a name: ${describe(el)}`);
  }
  for (const img of document.querySelectorAll("img")) if (!img.hasAttribute("alt")) problems.push(`img without alt: ${img.src.slice(0, 60)}`);
  for (const svg of document.querySelectorAll("svg")) {
    if (svg.closest("[aria-hidden=true]") || svg.getAttribute("aria-hidden") === "true" || !visible(svg)) continue;
    const r = svg.getBoundingClientRect();
    if (r.width < 40 && r.height < 40) continue; // icons
    const named = svg.getAttribute("aria-label") || svg.getAttribute("aria-labelledby") || svg.querySelector(":scope > title")?.textContent.trim();
    if (!named) problems.push(`figure without a text alternative (add <title> or aria-label): svg ${Math.round(r.width)}x${Math.round(r.height)}`);
  }
  // Figure text at the size it is actually drawn (viewBox scaling shrinks it on phones).
  const tiny = [];
  for (const t of document.querySelectorAll("svg text")) {
    if (!visible(t) || t.closest("[aria-hidden=true]") || !(t.textContent || "").trim()) continue;
    const m = t.getScreenCTM();
    const px = parseFloat(getComputedStyle(t).fontSize) * (m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1);
    if (px < 11) tiny.push(`"${t.textContent.trim().slice(0, 24)}" ${px.toFixed(1)}px`);
  }
  if (tiny.length) problems.push(`figure text drawn under 11px (${tiny.length}): ${tiny.slice(0, 4).join(", ")}`);
  for (const v of document.querySelectorAll("video")) if (!v.querySelector("track[kind=captions], track[kind=subtitles]")) problems.push("video without captions track");
  return problems;
}

const { chromium } = await loadPlaywright();
const browser = await launch(chromium);
if (out) await mkdir(out, { recursive: true });
const results = [];
for (const view of VIEWS) {
  for (const scheme of SCHEMES) {
    for (const reduced of [false, true]) {
      if (reduced && scheme === "dark") continue; // three motion-agnostic runs + one reduced run per view
      const label = `${view.name}-${scheme}${reduced ? "-reduced" : ""}`;
      const context = await browser.newContext({ ...view, colorScheme: scheme, reducedMotion: reduced ? "reduce" : "no-preference" });
      const page = await context.newPage();
      const errors = [];
      page.on("pageerror", (e) => errors.push(`page error: ${e.message}`));
      page.on("console", (m) => m.type() === "error" && errors.push(`console error: ${m.text()}`));
      await page.goto(url, { waitUntil: "load" });
      if (board) await page.evaluate((b) => (document.documentElement.dataset.board = b), board);
      // Let the pen finish: wait until no animation is still running (at most 12s).
      await page
        .waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" && a.playState !== "pending"), null, { timeout: 12000, polling: 200 })
        .catch(() => {});
      await page.waitForTimeout(200);
      const problems = [...errors, ...(await page.evaluate(audit))];
      if (evalExpr) {
        const checks = await page.evaluate((expr) => Promise.resolve(eval(expr)), evalExpr).catch((e) => [{ name: `eval failed: ${e.message}`, ok: false }]);
        for (const c of checks || []) if (!c.ok) problems.push(`check failed: ${c.name}`);
      }
      if (out) await page.screenshot({ path: `${out}/${label}.png`, fullPage: true });
      if (allSteps && !reduced) {
        const n = await page.evaluate(() => (window.LESSON && window.__explorable ? window.LESSON.steps.length : 0));
        for (let i = 1; i < n; i += 1) {
          await page.evaluate((k) => window.__explorable.goStep(k, { focus: false }), i);
          await page
            .waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" && a.playState !== "pending"), null, { timeout: 12000, polling: 200 })
            .catch(() => {});
          await page.waitForTimeout(150);
          for (const pr of await page.evaluate(audit)) problems.push(`step ${i + 1}: ${pr}`);
          if (out) await page.screenshot({ path: `${out}/${label}-step-${i + 1}.png`, fullPage: true });
        }
      }
      problems.push(...errors.filter((e) => !problems.includes(e)));
      results.push({ run: label, problems: [...new Set(problems)] });
      await context.close();
    }
  }
}
await browser.close();
const failed = results.filter((r) => r.problems.length);
if (asJson) console.log(JSON.stringify({ url, results }, null, 2));
else {
  for (const r of results) {
    console.log(`${r.problems.length ? "FAIL" : "ok  "} ${r.run}`);
    for (const p of r.problems.slice(0, 25)) console.log(`     ${p}`);
    if (r.problems.length > 25) console.log(`     ...and ${r.problems.length - 25} more`);
  }
  console.log(failed.length ? `${failed.length} of ${results.length} runs have problems` : `all ${results.length} runs clean`);
}
process.exit(failed.length ? 1 : 0);
