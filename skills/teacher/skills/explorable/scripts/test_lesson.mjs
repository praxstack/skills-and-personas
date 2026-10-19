#!/usr/bin/env node
// Drive a built explorable lesson end to end in Chromium.
//
//   node test_lesson.mjs lesson.html [--shots dir]
//
// For every step: the figure has a text alternative, the sliders move the
// model, a wrong answer gets a hint and Next stays locked, a second miss
// teaches it directly, and "Still confused?" swaps the explanation and is
// recorded. Then the model checks, the film (play, next, scrub, transcript),
// the end panel's report, and progress surviving a reload. Exits non-zero
// on any failure. Pair with ../../visual-qa/scripts/check_page.mjs for looks.

import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { mkdir } from "node:fs/promises";
import { loadPlaywright, launch } from "../../visual-qa/scripts/pw.mjs";

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith("--") && args[args.indexOf(a) - 1] !== "--shots");
const shots = args.includes("--shots") ? args[args.indexOf("--shots") + 1] : null;
if (!file) {
  console.error("usage: node test_lesson.mjs lesson.html [--shots dir]");
  process.exit(2);
}
const url = pathToFileURL(resolve(file)).href;
const fails = [];
const passes = [];
const check = (name, ok, detail = "") => (ok ? passes : fails).push(ok ? name : `${name} ${detail}`.trim());

const { chromium } = await loadPlaywright();
const browser = await launch(chromium);
if (shots) await mkdir(shots, { recursive: true });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 }, reducedMotion: "reduce" });
const page = await context.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));
// This frozen regression exercises explicitly requested practice. Default
// explanation-first behavior is checked independently by the v3 evaluator.
await page.goto(`${url}?practice=1`);
await page.waitForFunction(() => window.__explorable);
// Persistence is exercised only with an explicit user opt-in on newer engines.
const remember = page.getByRole("checkbox", { name: "Remember progress on this device" });
if (await remember.count()) await remember.check();

const steps = await page.evaluate(() => window.LESSON.steps.map((s) => ({ title: s.title, ask: s.ask ? { kind: s.ask.kind, n: s.ask.options?.length } : null, alts: (s.alts || []).length, line: s.line !== undefined, hasCode: Boolean(window.LESSON.code) })));
check("lesson has steps", steps.length > 0);
const modelChecks = await page.evaluate(() => window.__explorable.check());
for (const c of modelChecks) check(`model: ${c.name}`, c.ok);

for (let i = 0; i < steps.length; i++) {
  const st = steps[i];
  await page.evaluate((k) => window.__explorable.goStep(k), i);
  const step = page.locator(".xp-step");
  check(`step ${i + 1} heading`, (await step.locator("h2").textContent()) === st.title);
  const alt = await page.locator(".xp-figure svg title").first().textContent();
  check(`step ${i + 1} figure has a text alternative`, (alt || "").trim().length > 20, `got "${alt}"`);

  const slider = step.locator(".xp-control input[type=range]").first();
  if (await slider.count()) {
    const before = await page.locator(".xp-figure svg title").first().textContent();
    const max = await slider.getAttribute("max");
    const min = await slider.getAttribute("min");
    const cur = await slider.inputValue();
    await slider.fill(String(Number(cur) === Number(max) ? min : max));
    const after = await page.locator(".xp-figure svg title").first().textContent();
    check(`step ${i + 1} slider changes the figure`, before !== after);
  }

  if (st.alts) {
    await step.getByRole("button", { name: /Still confused|another way/i }).click();
    const tried = await page.evaluate((k) => window.__explorable.state.tried[k] || [], i);
    check(`step ${i + 1} other explanation shown and recorded`, tried.length === 1 && (await step.locator(".xp-alt").count()) === 1);
  }

  const next = step.locator(".xp-next");
  if (st.line && st.hasCode) {
    check(`step ${i + 1} code panel lights its line`, (await step.locator(".xp-code-line.is-active").count()) === 1);
  }
  if (st.ask && st.ask.kind === "explain") {
    check(`step ${i + 1} Next locked before explaining`, await next.isDisabled());
    await step.getByRole("button", { name: /Compare/ }).click();
    check(`step ${i + 1} an empty explanation is refused`, await next.isDisabled());
    await step.locator(".xp-explain").fill("Stored sums of slices let a query use a few boxes instead of every number.");
    await step.getByRole("button", { name: /Compare/ }).click();
    check(`step ${i + 1} explaining reveals the teacher's version and opens Next`, (await step.locator(".xp-why").count()) === 1 && !(await next.isDisabled()));
    const boxes = step.locator(".xp-points input[type=checkbox]");
    if (await boxes.count()) await boxes.first().check();
    // An edit after the reveal is kept for the report.
    await step.locator(".xp-explain").fill("Stored sums of slices, revised after reading the teacher's version.");
    await step.locator(".xp-explain").blur();
    check(`step ${i + 1} an edit after the reveal reaches the report`, (await page.evaluate(() => window.__explorable.report())).includes("revised after reading"));
  } else if (st.ask) {
    check(`step ${i + 1} Next locked before answering`, await next.isDisabled());
    // A wrong answer first.
    if (st.ask.kind === "choice") {
      const answer = await page.evaluate((k) => {
        const a = window.LESSON.steps[k].ask;
        return typeof a.answer === "function" ? a.answer(window.__explorable.state.params, window.LESSON.model(window.__explorable.state.params)) : a.answer;
      }, i);
      await step.locator(`.xp-option[data-k="${(answer + 1) % st.ask.n}"]`).click();
    } else {
      await step.locator(".xp-number input").fill("123456789");
    }
    await step.getByRole("button", { name: "Check" }).click();
    check(`step ${i + 1} a miss gets a hint and keeps Next locked`, (await step.locator(".xp-feedback").textContent()).length > 5 && (await next.isDisabled()));
    await step.getByRole("button", { name: "Check" }).click();
    check(`step ${i + 1} a second miss teaches it`, !(await next.isDisabled()) && (await step.locator(".xp-why").count()) === 1);
  } else {
    check(`step ${i + 1} no question: Next open`, !(await next.isDisabled()));
  }
  check(`step ${i + 1} shows no stray "null" or "undefined"`, !/(^|\n)\s*(null|undefined)\s*(\n|$)/.test(await step.innerText()));
  if (shots) await page.screenshot({ path: `${shots}/step-${i + 1}.png`, fullPage: true });
}

const state = await page.evaluate(() => window.__explorable.state);
check("every step done", state.done.length === steps.length, `${state.done.length}/${steps.length}`);
check("margin notes filled", (await page.locator(".xp-takeaways .nb-note").count()) > 0);

// End panel: the learner decides when it's done, and the report says what happened.
await page.locator(".xp-next").click();
await page.getByRole("button", { name: /Go deeper/ }).click();
const report = await page.locator(".xp-report").inputValue();
check("report counts steps", report.includes(`Steps done: ${steps.length}/${steps.length}`), report);
check("report records misses", /miss/.test(report));
check("report records the choice", report.includes("Go deeper"));
if (steps.some((s) => s.alts)) check("report records other explanations tried", report.includes("tried other explanations"));
if (shots) await page.screenshot({ path: `${shots}/end.png`, fullPage: true });

// Film.
await page.getByRole("tab", { name: "Film" }).click();
const film = page.locator(".xp-film");
check("film shows", await film.isVisible());
const cap1 = await film.locator(".xp-film-caption").textContent();
await film.getByRole("button", { name: "Next scene" }).click();
const cap2 = await film.locator(".xp-film-caption").textContent();
check("film next scene changes the caption", cap1 !== cap2);
await film.locator("input[type=range]").fill("0");
check("film scrub back to the start", (await film.locator(".xp-film-caption").textContent()) === cap1);
await film.getByRole("button", { name: "Play" }).click();
check("film plays", (await film.getByRole("button", { name: "Pause" }).count()) === 1);
await film.getByRole("button", { name: "Pause" }).click();
check("film transcript lists every scene", (await film.locator(".xp-transcript li").count()) >= steps.length);
if (shots) await page.screenshot({ path: `${shots}/film.png`, fullPage: true });

// Code view: languages, line numbers, what it prints.
const hasCode = await page.evaluate(() => Boolean(window.LESSON.code));
if (hasCode) {
  await page.getByRole("tab", { name: "Code" }).click();
  const panel = page.locator("#view-code .xp-code");
  check("code view shows the program", (await panel.locator(".xp-code-line").count()) > 5);
  const langs = panel.locator(".xp-code-tabs button");
  const n = await langs.count();
  if (n > 1) {
    const first = await panel.locator(".xp-code-pre").textContent();
    await langs.nth(1).click();
    check("code view switches language", (await panel.locator(".xp-code-pre").textContent()) !== first);
  }
  const printed = await panel.locator(".xp-code-out").first().textContent();
  check("code view shows what the program prints, from the model", /prints:/.test(printed || ""));
  if (shots) await page.screenshot({ path: `${shots}/code.png`, fullPage: true });
}

// Curiosity list goes into the report.
await page.getByRole("tab", { name: "Lesson" }).click();
await page.locator("#xp-curious-input").fill("what about the minimum instead of the sum?");
await page.locator(".xp-curious-box").getByRole("button", { name: "Add" }).click();
check("curiosity list keeps a question", (await page.locator(".xp-curious li").count()) === 1);
const rep2 = await page.evaluate(() => window.__explorable.report());
check("report carries the curiosity list", rep2.includes("Questions I want to chase"));

// Notes view and persistence.
await page.getByRole("tab", { name: "Notes and report" }).click();
check("notes view lists key ideas", (await page.locator(".xp-key-ideas li").count()) === steps.length);
await page.getByRole("tab", { name: "Lesson" }).click();
await page.locator(".xp-notes-box").fill("tilt matters");
await page.reload();
await page.waitForFunction(() => window.__explorable);
const again = await page.evaluate(() => window.__explorable.state);
check("progress survives a reload", again.done.length === steps.length);
check("notes survive a reload", (await page.locator(".xp-notes-box").inputValue()) === "tilt matters");

check("no console or page errors", errors.length === 0, errors.join(" | "));
await browser.close();
for (const p of passes) console.log(`ok   ${p}`);
for (const f of fails) console.log(`FAIL ${f}`);
console.log(`${passes.length} passed, ${fails.length} failed`);
process.exit(fails.length ? 1 : 0);
