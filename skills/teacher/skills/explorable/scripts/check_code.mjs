#!/usr/bin/env node
// Run a lesson's shown code against its model.
//
//   node check_code.mjs lesson.js [--quiet] [--trust-authored-code]
//
// For every case in LESSON.code.cases (parameter sets), feeds code.stdin(params)
// to the C++ (g++ -std=c++17) and Python (python3) sources the learner sees,
// and compares what they print with code.expect(params), which comes from the
// lesson's model. A missing compiler is reported as skipped, not passed, and
// if neither g++ nor python3 is there, nothing ran and the check fails.
// Exits non-zero on any mismatch, compile error or crash.

import { readFileSync, writeFileSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import vm from "node:vm";
import { fileURLToPath } from "node:url";

const file = process.argv[2];
const includes = [];
for (let i = 3; i < process.argv.length; i += 1) if (process.argv[i] === "--include") includes.push(process.argv[++i]);
if (!file) {
  console.error("usage: node check_code.mjs lesson.js");
  process.exit(2);
}
if (process.argv.includes("--sandbox")) {
  const value = (flag) => { const i = process.argv.indexOf(flag); return i >= 0 ? process.argv[i + 1] : undefined; };
  const image = value("--sandbox-image");
  if (!image) { console.error("--sandbox requires --sandbox-image sha256:<reviewed-local-image-id>"); process.exit(2); }
  const args = [fileURLToPath(new URL("./sandbox_code.py", import.meta.url)), file, "--image", image];
  for (const include of includes) args.push("--include", include);
  if (value("--docker-context")) args.push("--docker-context", value("--docker-context"));
  const result = spawnSync("python3", args, { stdio: "inherit", timeout: 120000 });
  process.exit(result.status ?? 2);
}
const trusted = process.argv.includes("--trust-authored-code") || process.env.TEACHER_TRUST_AUTHORED_CODE === "1";
if (!trusted) {
  const shown = [file, ...includes].map((path) => readFileSync(resolve(path), "utf8")).join("\n");
  if (/\bcode\s*:/.test(shown)) {
    console.log("UNVERIFIED: shown code was not executed. Review the lesson, then pass --trust-authored-code or use an external restricted sandbox.");
  } else {
    console.log(`${file}: no shown code detected by the structural check`);
  }
  process.exit(0);
}
const ctx = { console, Math, Number, String, Array, Object, JSON, Set, Map };
ctx.window = ctx;
vm.createContext(ctx);
for (const inc of includes) vm.runInContext(readFileSync(resolve(inc), "utf8"), ctx, { filename: inc, timeout: 5000 });
vm.runInContext(readFileSync(resolve(file), "utf8"), ctx, { filename: file, timeout: 5000 });
const L = ctx.window.LESSON;
if (!L?.code) {
  console.log(`${file}: no code to check`);
  process.exit(0);
}
const code = L.code;
if (!code.cpp && !code.python) {
  // Other languages (js, java, go, rust) are shown to read, not run here.
  console.log(`${L.title}: no C++ or Python to run; the other languages are shown, not checked`);
  process.exit(0);
}
const strip = (src) => String(src).replace(/^\n/, "").split("\n").map((l) => l.replace(/\s*(?:\/\/|#)@[\w-]+\s*$/, "")).join("\n");
const have = (bin) => spawnSync(bin, ["--version"]).status === 0;
const dir = mkdtempSync(join(tmpdir(), "code-"));
const fails = [];
let passes = 0;
const skipped = [];
const cases = code.cases?.length ? code.cases : [Object.fromEntries(Object.entries(L.params || {}).map(([k, v]) => [k, v.value]))];

let cppBin = null;
if (code.cpp) {
  if (!have("g++")) skipped.push("C++ (no g++)");
  else {
    writeFileSync(join(dir, "main.cpp"), strip(code.cpp));
    const c = spawnSync("g++", ["-std=c++17", "-O2", "-o", join(dir, "main"), join(dir, "main.cpp")], { encoding: "utf8", timeout: 30000, maxBuffer: 1024 * 1024 });
    if (c.status !== 0) fails.push(`C++ does not compile:\n${c.stderr.slice(0, 1200)}`);
    else cppBin = join(dir, "main");
  }
}
if (code.python && !have("python3")) skipped.push("Python (no python3)");
if (code.python) writeFileSync(join(dir, "main.py"), strip(code.python));

for (const params of cases) {
  const stdin = code.stdin ? String(code.stdin(params)) : "";
  const want = String(code.expect(params)).trim();
  const runs = [];
  if (cppBin) runs.push(["C++", spawnSync(cppBin, [], { input: stdin, encoding: "utf8", timeout: 10000 })]);
  if (code.python && have("python3")) runs.push(["Python", spawnSync("python3", [join(dir, "main.py")], { input: stdin, encoding: "utf8", timeout: 20000 })]);
  for (const [lang, r] of runs) {
    const got = (r.stdout || "").trim();
    if (r.status !== 0) fails.push(`${lang} crashed on ${JSON.stringify(params)}: ${(r.stderr || "").slice(0, 400)}`);
    else if (got !== want) fails.push(`${lang} on ${JSON.stringify(params)}\n  printed: ${got.slice(0, 300)}\n  model:   ${want.slice(0, 300)}`);
    else passes += 1;
  }
}
rmSync(dir, { recursive: true, force: true });
if (!process.argv.includes("--quiet")) {
  for (const f of fails) console.log(`FAIL ${f}`);
  for (const s of skipped) console.log(`SKIP ${s}`);
}
// Code that never ran was not checked: with no compiler at all that's a failure, not a pass.
const nothingRan = passes === 0 && fails.length === 0;
if (nothingRan) console.log(`FAIL nothing ran: ${skipped.join(", ") || "no C++ or Python source"}. Install g++ or python3 to check this lesson's code.`);
console.log(`${L.title}: ${passes} runs match the model, ${fails.length + (nothingRan ? 1 : 0)} problems${skipped.length ? `, skipped ${skipped.join(", ")}` : ""}`);
process.exit(fails.length || nothingRan ? 1 : 0);
