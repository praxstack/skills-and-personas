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
// Videos on Blob are not fetched here: the check is about what the page offers.
await page.route(/^https:\/\/[^/]*\.vercel-storage\.com\//, (r) => r.abort());
await page.goto(pathToFileURL(resolve(process.argv[2])).href);
await page.waitForFunction(() => window.__course);
const ids = await page.evaluate(() => window.__course.lessons);
check("map has a node per lesson", (await page.locator(".cs-node").count()) === ids.length);
// Keyboard: Enter on a focused node opens it and keeps focus on that lesson's
// node (the map is redrawn, which replaces every node).
const nodeIds = await page.locator(".cs-node").evaluateAll((els) => els.map((e) => e.getAttribute("data-id")));
await page.locator(".cs-node").first().focus();
await page.keyboard.press("Enter");
const kb = await page.evaluate(() => {
  const a = document.activeElement;
  return { node: Boolean(a && a.classList && a.classList.contains("cs-node")), selected: Boolean(a && a.classList.contains("is-selected")), id: a && a.getAttribute("data-id") };
});
// Screen readers must reach the nodes: inside the map group, each is a named button.
const firstTitle = await page.evaluate((id) => window.COURSE.lessons.find((l) => l.id === id).title, nodeIds[0]);
const a11y = await page.evaluate(() => {
  const svg = document.querySelector(".cs-map-svg");
  return { role: svg.getAttribute("role"), label: svg.getAttribute("aria-label") };
});
check("map is a labelled group, not an image", a11y.role === "group" && Boolean(a11y.label), JSON.stringify(a11y));
const nodeButton = page.getByRole("group", { name: /^Map of/ }).getByRole("button", { name: `${firstTitle}. Open`, exact: false });
check("a map node is a button by its lesson's name", (await nodeButton.count()) >= 1, firstTitle);
check("the open lesson's node is marked current", (await page.evaluate(() => document.querySelector('.cs-node[aria-current="true"]')?.getAttribute("data-id"))) === nodeIds[0]);
check("Enter on a node keeps focus on its node", kb.node && kb.selected && kb.id === nodeIds[0], JSON.stringify(kb));
if (nodeIds.length > 1) {
  await page.keyboard.press("Tab");
  await page.keyboard.press("Enter");
  check("Tab then Enter opens the next lesson", (await page.evaluate(() => document.activeElement && document.activeElement.getAttribute("data-id"))) === nodeIds[1]);
}
// Keyboard on a status button: the drawer is rebuilt, focus stays on the new button.
await page.locator(".cs-drawer .cs-chip").first().focus();
const chipLabel = await page.locator(".cs-drawer .cs-chip").first().textContent();
await page.keyboard.press("Enter");
const chip = await page.evaluate(() => {
  const a = document.activeElement;
  return { chip: Boolean(a && a.classList.contains("cs-chip")), text: a && a.textContent, pressed: a && a.getAttribute("aria-pressed") };
});
check("Enter on a status button keeps focus on it", chip.chip && chip.text === chipLabel && chip.pressed === "true", JSON.stringify(chip));
await page.keyboard.press("Space");
check("pressing it again clears it, focus kept", await page.evaluate(() => document.activeElement?.classList.contains("cs-chip") && document.activeElement.getAttribute("aria-pressed") === "false"));
await page.locator(".cs-node").last().click();
check("clicking a node opens its panel", (await page.locator(".cs-drawer h2").textContent()).length > 3);
check("panel offers Teach me", (await page.locator(".cs-drawer a", { hasText: "Teach me" }).count()) === 1);
await page.locator(".cs-drawer .cs-chip", { hasText: "Done" }).click();
check("Done updates progress", /1 of/.test(await page.locator(".cs-head .nb-print").first().textContent()));
const quizBtn = page.locator(".cs-drawer button", { hasText: "Quiz me" });
if (await quizBtn.count()) {
  await quizBtn.click();
  check("quiz leaves out questions that need the figure", await page.evaluate(() => window.COURSE.lessons.every((l) => l.quiz.every((q) => !q.needsFigure))));
  // Options are shuffled: the right one is found by its original index, and must still count as right.
  const q = await page.evaluate(() => {
    const id = document.querySelector('.cs-node[aria-current="true"]')?.getAttribute("data-id");
    const l = window.COURSE.lessons.find((x) => x.id === id);
    return l.quiz[0];
  });
  if (q.kind === "choice") await page.locator(`.cs-quiz .cs-opt[data-k="${q.answer}"]`).click();
  else await page.locator(".cs-quiz input").fill(String(q.answer));
  await page.locator(".cs-quiz button", { hasText: "Check" }).click();
  check("quiz reveals why after a try", (await page.locator(".cs-quiz .cs-why").count()) === 1);
  check("the right answer counts as right", (await page.locator(".cs-quiz .cs-fb").textContent()).startsWith("Yes."));
}
// A Watch button only where the build found a video (the local MP4 or its
// Blob URL from courses/videos.json); captions always from beside the page.
const videos = await page.evaluate(() => window.COURSE.lessons.map((l) => ({ id: l.id, video: l.video || "", captions: l.captions || "" })));
for (const l of videos) {
  await page.evaluate((id) => window.__course.select(id), l.id);
  const watch = page.locator(".cs-drawer button", { hasText: "Watch the narrated video" });
  check(`${l.id}: video button only when there is a video`, (await watch.count()) === (l.video ? 1 : 0), l.video || "(none)");
  if (!l.video) continue;
  await watch.click();
  const got = await page.evaluate(() => {
    const v = document.querySelector(".cs-drawer .cs-video video");
    const t = v && v.querySelector("track");
    return v ? { src: v.getAttribute("src"), crossorigin: v.hasAttribute("crossorigin"), track: t ? t.getAttribute("src") : "" } : null;
  });
  check(`${l.id}: the video plays ${l.video}`, got && got.src === l.video && !got.crossorigin, JSON.stringify(got));
  check(`${l.id}: captions come from beside the page`, got && Boolean(l.captions) && got.track === l.captions && !/^[a-z]+:/i.test(got.track), JSON.stringify(got));
  await watch.click();
}
await page.getByRole("tab", { name: "Outline" }).click();
check("outline lists every lesson", (await page.locator(".cs-outline li").count()) === ids.length);
const unlinked = await page.evaluate(() =>
  window.COURSE.lessons.filter((l) => ![...document.querySelectorAll(".cs-outline a")].some((a) => a.getAttribute("href") === (window.COURSE.base || "") + l.page)).map((l) => l.id),
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
