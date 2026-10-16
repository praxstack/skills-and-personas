import assert from "node:assert/strict";
import test from "node:test";
import { applyCubeMove, canonical, createReceipt, createSession, cubeInvariant, cubeViews, exportReceipt, floatObservation, floatTransfer, importReceipt, lostUpdate, newCube, nextHint, transition, validateLesson } from "../src/core.mjs";
import { readFile } from "node:fs/promises";
import path from "node:path";

const lesson = { schema_version:"prax.visual-lesson/v1", lesson_id:"test-lesson", lesson_version:"1.0.0", objective:"Test deterministic state transitions and local evidence.", states:[{id:"one",label:"One",content:"one"},{id:"two",label:"Two",content:"two"}], actions:[{id:"previous",label:"Previous"},{id:"next",label:"Next"},{id:"reset",label:"Reset"}], hints:["first","second"], static_fallback:[{state_id:"one",content:"one"},{state_id:"two",content:"two"}], grader:{kind:"exact",accepted:["ok"]} };
test("lesson reducer is deterministic and bounded", () => { validateLesson(lesson); const a = transition(createSession(lesson), lesson, "next"); const b = transition(createSession(lesson), lesson, "next"); assert.equal(canonical(a), canonical(b)); assert.equal(a.state_index, 1); assert.equal(transition(a, lesson, "next").state_index, 1); });
test("state jumps are valid receipt actions", () => { const session = transition(createSession(lesson), lesson, "jump:two"); assert.equal(session.state_index, 1); assert.doesNotThrow(() => exportReceipt(session, lesson)); assert.throws(() => transition(session, lesson, "jump:missing"), /undeclared action/); });
test("hints are ordered and receipts round-trip", () => { const session = nextHint(createSession(lesson), lesson); assert.equal(session.hint, "first"); const receipt = createReceipt(session); assert.deepEqual(createReceipt(importReceipt(JSON.stringify(receipt), lesson)), receipt); assert.throws(() => importReceipt(JSON.stringify({ ...receipt, lesson_id:"other" }), lesson), /another lesson/); });
test("imported receipts resume deterministic lesson state", () => {
  const progressed = transition(createSession(lesson), lesson, "next");
  const resumed = importReceipt(exportReceipt(progressed, lesson), lesson);
  assert.equal(resumed.state_index, 1);
  assert.equal(transition(resumed, lesson, "previous").state_index, 0);
});
test("imported receipts reject undeclared actions and non-object evidence", () => {
  const receipt = createReceipt(createSession(lesson));
  assert.throws(() => importReceipt(JSON.stringify({ ...receipt, actions:["forged-action"] }), lesson), /undeclared action/);
  assert.throws(() => importReceipt(JSON.stringify({ ...receipt, observations:"forged" }), lesson), /observations/);
  assert.throws(() => importReceipt(JSON.stringify({ ...receipt, learner_authored:[] }), lesson), /learner_authored/);
});
test("runtime receipt imports enforce the shipped exact schema", () => {
  const receipt = createReceipt(createSession(lesson));
  const { uncertainty: _uncertainty, ...missingUncertainty } = receipt;
  const { created_at: _createdAt, ...missingCreatedAt } = receipt;
  assert.throws(() => importReceipt(JSON.stringify(missingUncertainty), lesson), /missing required fields/);
  assert.throws(() => importReceipt(JSON.stringify(missingCreatedAt), lesson), /missing required fields/);
  assert.throws(() => importReceipt(JSON.stringify({ ...receipt, transfer:"forged" }), lesson), /transfer/);
  assert.throws(() => importReceipt(JSON.stringify({ ...receipt, unexpected_privilege:true }), lesson), /unexpected properties/);
});
test("floating point model matches independent literal parity vectors", async () => {
  const vectors = JSON.parse(await readFile(path.join(import.meta.dirname, "../../../examples/visual-lab/python-floating-point/parity-vectors.json"), "utf8"));
  for (const vector of vectors) assert.deepEqual(floatObservation(vector.a, vector.b, vector.expected_decimal), vector.expected);
  assert.equal(floatTransfer("0.7", "0.1", "0.8").pass, true);
});
test("cube moves apply exact facelet permutations", () => {
  const cube = applyCubeMove(newCube(), "R");
  assert.equal(cube.stickers.join(""), "UUFUUFUUFRRRRRRRRRFFDFFDFFDDDBDDBDDBLLLLLLLLLUBBUBBUBB");
  assert.equal(cubeInvariant(cube), true);
  assert.equal(cubeViews(cube).notation, "R");
  assert.throws(() => applyCubeMove(cube, "X"), /illegal/);
});
test("every cube move has an inverse and a consistent double turn", () => {
  const solved = newCube().stickers.join("");
  for (const face of "URFDLB") {
    const moved = applyCubeMove(newCube(), face);
    assert.equal(applyCubeMove(moved, `${face}'`).stickers.join(""), solved, `${face} inverse`);
    assert.equal(
      applyCubeMove(newCube(), `${face}2`).stickers.join(""),
      applyCubeMove(applyCubeMove(newCube(), face), face).stickers.join(""),
      `${face} double`,
    );
  }
});
test("lost update exposes causal interleaving", () => { const result = lostUpdate(); assert.equal(result.final, 1); assert.equal(result.lost_update, true); assert.equal(lostUpdate(["A:read","A:write","B:read","B:write"]).final, 2); });
test("all domain lesson manifests reference the shared public components", async () => { for (const name of ["python-floating-point", "rubiks-move-lab", "lost-update-lab"]) { const lesson = JSON.parse(await readFile(path.join(import.meta.dirname, "../../../examples/visual-lab", name, "lesson.json"), "utf8")); assert.equal(lesson.component_versions["state-stepper"], "1.0.0"); assert.equal(lesson.component_versions["hint-engine"], "1.0.0"); assert.equal(lesson.component_versions["receipt-panel"], "1.0.0"); } });
test("static lesson keeps CSP valid and bootstraps through an external module", async () => { const html = await readFile(path.join(import.meta.dirname, "../src/index.html"), "utf8"); assert.match(html, /form-action 'none';/); assert.doesNotMatch(html, /<script type="module">/); assert.match(html, /src="\.\/lesson-floating-point\.mjs"/); });
test("no-script lesson preserves the result, cause, and unanswered transfer", async () => {
  const html = await readFile(path.join(import.meta.dirname, "../src/index.html"), "utf8");
  assert.match(html, /0\.30000000000000004/);
  assert.match(html, /cannot be represented exactly as finite binary fractions/);
  assert.match(html, /0\.7 \+ 0\.1/);
  assert.doesNotMatch(html, /0\.7 \+ 0\.1\s*=\s*0\.7999999999999999/);
});
