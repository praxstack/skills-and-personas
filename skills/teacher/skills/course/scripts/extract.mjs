#!/usr/bin/env node
// Read a course's lessons in Node and pull out what the course map needs:
// each lesson's title, hook, notes, questions (with answers resolved from the
// model at that step's settings), whether it shows code, and its film scenes.
//
//   node extract.mjs course-dir > course-data.json

import { readFileSync, lstatSync, realpathSync, statSync } from "node:fs";
import { join, resolve, relative, isAbsolute, sep } from "node:path";
import vm from "node:vm";

if (!process.argv.includes("--trust-authored-code") && process.env.TEACHER_TRUST_AUTHORED_CODE !== "1") {
  throw new Error("refusing to execute authored lesson JavaScript; review the course, then pass --trust-authored-code explicitly");
}
const dir = realpathSync(resolve(process.argv[2] || "."));
const SAFE_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$/;

function safeId(value, label) {
  if (typeof value !== "string" || !SAFE_ID.test(value)) throw new Error(`${label} is not a portable identifier`);
  return value;
}

function safeFile(value, label, suffixes) {
  if (typeof value !== "string" || !value || value.includes("\0") || isAbsolute(value)) {
    throw new Error(`${label} must be a relative path`);
  }
  const logical = resolve(dir, value);
  const rel = relative(dir, logical);
  if (!rel || rel === ".." || rel.startsWith(`..${sep}`) || isAbsolute(rel)) throw new Error(`${label} escapes the course`);
  let current = dir;
  for (const part of rel.split(sep)) {
    current = join(current, part);
    if (lstatSync(current).isSymbolicLink()) throw new Error(`${label} must not contain links`);
  }
  const canonical = realpathSync(logical);
  const canonicalRel = relative(dir, canonical);
  if (canonicalRel === ".." || canonicalRel.startsWith(`..${sep}`) || isAbsolute(canonicalRel)) throw new Error(`${label} escapes the course`);
  const info = statSync(canonical);
  if (!info.isFile() || info.nlink !== 1) throw new Error(`${label} must be one regular, unlinked file`);
  if (process.getuid && info.uid !== process.getuid()) throw new Error(`${label} is owned by another user`);
  if (suffixes && !suffixes.some((suffix) => canonical.endsWith(suffix))) throw new Error(`${label} has an unsupported file type`);
  return canonical;
}

const course = JSON.parse(readFileSync(safeFile("course.json", "course manifest", [".json"]), "utf8"));
safeId(course.id, "course id");
if (!Array.isArray(course.shared || []) || !Array.isArray(course.lessons) || !course.lessons.length) throw new Error("invalid course arrays");
const sharedFiles = (course.shared || []).map((file) => safeFile(file, "shared file", [".js"]));
const lessonFiles = new Map();
for (const lesson of course.lessons) {
  const id = safeId(lesson?.id, "lesson id");
  if (lessonFiles.has(id)) throw new Error(`duplicate lesson id: ${id}`);
  lessonFiles.set(id, safeFile(lesson.file, `lesson file ${id}`, [".lesson.js", ".anim.js"]));
}
const strip = (html) => String(html || "").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

function load(file, lessonId) {
  const ctx = { console, Math, Number, String, Array, Object, JSON, Set, Map, Infinity, NaN, isFinite, parseFloat, parseInt };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const [index, shared] of sharedFiles.entries()) vm.runInContext(readFileSync(shared, "utf8"), ctx, { filename: course.shared[index] });
  vm.runInContext(readFileSync(lessonFiles.get(lessonId), "utf8"), ctx, { filename: file });
  return ctx.window.LESSON || ctx.window.ANIMATION;
}

const lessons = course.lessons.map((meta) => {
  const L = load(meta.file, meta.id);
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
