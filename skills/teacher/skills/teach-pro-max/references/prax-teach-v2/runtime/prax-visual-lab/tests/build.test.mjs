import assert from "node:assert/strict";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import test from "node:test";
const root = path.resolve(import.meta.dirname, "..");
test("build is local, deterministic, and emits a manifest", async () => { const run = spawnSync(process.execPath, [path.join(root,"build.mjs")], { cwd: root, encoding:"utf8" }); assert.equal(run.status, 0, run.stderr); const manifest = JSON.parse(await readFile(path.join(root,"dist","manifest.json"),"utf8")); assert.equal(manifest.schema_version,"prax.visual-manifest/v1"); assert.ok(manifest.files.length >= 5); await stat(path.join(root,"dist","index.html")); assert.doesNotMatch(await readFile(path.join(root,"dist","index.html"),"utf8"), /https?:\/\//); });
test("components do not render data through HTML injection sinks", async () => {
  const source = await readFile(path.join(root, "src", "components.mjs"), "utf8");
  assert.doesNotMatch(source, /\.innerHTML\s*=/);
  assert.doesNotMatch(source, /insertAdjacentHTML|document\.write/);
});
test("lesson components share hint and state evidence with the receipt", async () => {
  const components = await readFile(path.join(root, "src", "components.mjs"), "utf8");
  const lesson = await readFile(path.join(root, "src", "lesson-floating-point.mjs"), "utf8");
  assert.equal((components.match(/set session\(value\)/g) || []).length, 3);
  assert.match(lesson, /function syncSession/);
  assert.match(lesson, /addEventListener\("statechange", syncSession\)/);
  assert.match(lesson, /addEventListener\("hint", syncSession\)/);
  assert.match(lesson, /addEventListener\("receiptimport", syncSession\)/);
  assert.match(lesson, /addEventListener\("parameterchange", syncParameter\)/);
  assert.match(lesson, /recordAttempt\(session/);
  assert.match(lesson, /compare\.views = comparisonViews\(expectedDecimal\)/);
});
test("shadow components use system canvas colors", async () => {
  const stylesheet = await readFile(path.join(root, "src", "components.css"), "utf8");
  assert.match(stylesheet, /color:CanvasText/);
  assert.match(stylesheet, /background:Canvas/);
  assert.doesNotMatch(stylesheet, /color:#17202a/);
});
