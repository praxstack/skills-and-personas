#!/usr/bin/env node
// Read a course's lessons in Node and pull out what the course map needs:
// each lesson's title, hook, notes, questions (with answers resolved from the
// model at that step's settings), whether it shows code, and its film scenes.
//
//   node extract.mjs course-dir > course-data.json

import { readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import vm from "node:vm";

const dir = resolve(process.argv[2] || ".");
const course = JSON.parse(readFileSync(join(dir, "course.json"), "utf8"));
const strip = (html) => String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

function load(file) {
  const ctx = { console, Math, Number, String, Array, Object, JSON, Set, Map, Infinity, NaN, isFinite, parseFloat, parseInt };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const s of course.shared || []) vm.runInContext(readFileSync(join(dir, s), "utf8"), ctx, { filename: s });
  vm.runInContext(readFileSync(join(dir, file), "utf8"), ctx, { filename: file });
  return ctx.window.LESSON || ctx.window.ANIMATION;
}

const lessons = course.lessons.map((meta) => {
  const L = load(meta.file);
  const kind = meta.file.endsWith(".anim.js") ? "animation" : "explorable";
  const quiz = [];
  if (kind === "explorable") {
    const params = Object.fromEntries(Object.entries(L.params || {}).map(([k, v]) => [k, v.value]));
    L.steps.forEach((st, i) => {
      if (st.set) Object.assign(params, st.set);
      const ask = st.ask;
      if (!ask || ask.kind === "explain") return;
      const s = L.model({ ...params });
      const answer = typeof ask.answer === "function" ? ask.answer({ ...params }, s) : ask.answer;
      quiz.push({
        step: i + 1,
        title: st.title,
        kind: ask.kind,
        q: ask.q,
        options: ask.options || null,
        keepOrder: Boolean(ask.keepOrder),
        answer,
        tol: ask.tol ?? 0,
        unit: ask.unit || "",
        decimals: ask.decimals ?? 2,
        hint: ask.hint || "",
        why: strip(ask.why),
        // Answerable only with the lesson's figure in front of you (its values aren't in the question).
        needsFigure: Boolean(ask.needsFigure),
      });
    });
  }
  return {
    ...meta,
    kind,
    title: meta.title || L.title,
    subtitle: L.subtitle || "",
    hook: strip(L.hook),
    notes: (L.steps || []).map((st) => ({ title: st.title, note: st.note || "" })),
    misconceptions: L.misconceptions || [],
    deeper: L.deeper || [],
    hasCode: Boolean(L.code),
    explain: (L.steps || []).filter((st) => st.ask?.kind === "explain").map((st) => st.ask.q),
    quiz,
  };
});

process.stdout.write(JSON.stringify({ ...course, lessons }, null, 2));
