#!/usr/bin/env node
// Click through a built course page: map nodes, the lesson panel, status
// buttons, quiz, outline and notes. Usage: node check_course_page.mjs index.html
import { pathToFileURL } from "node:url";
import { resolve } from "node:path";
import { loadPlaywright, launch } from "../../visual-qa/scripts/pw.mjs";

const fails = [];
const passes = [];
const check = (name, ok, d = "") => (ok ? passes : fails).push(ok ? name : `${name} ${d}`);
const { chromium } = await loadPlaywright();
const browser = await launch(chromium);
const page = await (await browser.newContext({ viewport: { width: 1280, height: 900 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(e.message));
await page.goto(pathToFileURL(resolve(process.argv[2])).href);
await page.waitForFunction(() => window.__course);
const ids = await page.evaluate(() => window.__course.lessons);
check("map has a node per lesson", (await page.locator(".cs-node").count()) === ids.length);
await page.locator(".cs-node").last().click();
check("clicking a node opens its panel", (await page.locator(".cs-drawer h2").textContent()).length > 3);
check("panel offers Teach me", (await page.locator(".cs-drawer a", { hasText: "Teach me" }).count()) === 1);
await page.locator(".cs-drawer .cs-chip", { hasText: "Done" }).click();
check("Done updates progress", /1 of/.test(await page.locator(".cs-head .nb-print").first().textContent()));
const quizBtn = page.locator(".cs-drawer button", { hasText: "Quiz me" });
if (await quizBtn.count()) {
  await quizBtn.click();
  const opt = page.locator(".cs-quiz .cs-opt").first();
  if (await opt.count()) await opt.click();
  else await page.locator(".cs-quiz input").fill("1");
  await page.locator(".cs-quiz button", { hasText: "Check" }).click();
  check("quiz reveals why after a try", (await page.locator(".cs-quiz .cs-why").count()) === 1);
}
await page.getByRole("tab", { name: "Outline" }).click();
check("outline lists every lesson", (await page.locator(".cs-outline li").count()) === ids.length);
const unlinked = await page.evaluate(() =>
  window.COURSE.lessons.filter((l) => ![...document.querySelectorAll(".cs-outline a")].some((a) => a.getAttribute("href") === l.page)).map((l) => l.id),
);
check("every lesson links to its page", unlinked.length === 0, unlinked.join(", "));
await page.getByRole("tab", { name: "Notes" }).click();
check("notes view has a card per lesson", (await page.locator(".cs-note-card").count()) === ids.length);
await page.reload();
await page.waitForFunction(() => window.__course);
check("status survives a reload", /1 of/.test(await page.locator(".cs-head .nb-print").first().textContent()));
check("no page errors", errors.length === 0, errors.join(" | "));
await browser.close();
for (const f of fails) console.log(`FAIL ${f}`);
console.log(`course page: ${passes.length} passed, ${fails.length} failed`);
process.exit(fails.length ? 1 : 0);
