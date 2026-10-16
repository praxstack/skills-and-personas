/** Pure, deterministic contracts shared by every visual lab. */
export const RUNTIME_VERSION = "prax-visual-lab/0.1.0";
export const COMPONENT_VERSIONS = Object.freeze({
  "state-stepper": "1.0.0", "parameter-lab": "1.0.0", "compare-views": "1.0.0",
  "hint-engine": "1.0.0", "receipt-panel": "1.0.0",
});
const SLUG = /^[a-z0-9][a-z0-9-]{2,63}$/;
const VERSION = /^\d+\.\d+\.\d+$/;

function exactObject(value, label, required, optional = []) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error(`${label} must be an object`);
  const missing = required.filter((key) => !Object.hasOwn(value, key));
  if (missing.length) throw new Error(`${label} missing required fields: ${missing.join(", ")}`);
  const allowed = new Set([...required, ...optional]);
  const unexpected = Object.keys(value).filter((key) => !allowed.has(key));
  if (unexpected.length) throw new Error(`${label} contains unexpected properties: ${unexpected.join(", ")}`);
}

function nonEmptyString(value, label) {
  if (typeof value !== "string" || !value.length) throw new Error(`${label} must be a non-empty string`);
}

export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") return `{${Object.keys(value).sort().map((key) => `${JSON.stringify(key)}:${canonical(value[key])}`).join(",")}}`;
  return JSON.stringify(value);
}

export function validateLesson(lesson) {
  const required = ["schema_version", "lesson_id", "lesson_version", "objective", "states", "actions", "hints", "static_fallback", "grader"];
  exactObject(lesson, "lesson", required, ["component_versions", "transfer"]);
  if (lesson.schema_version !== "prax.visual-lesson/v1") throw new Error("unsupported lesson schema_version");
  if (!SLUG.test(lesson.lesson_id)) throw new Error("invalid lesson_id");
  if (!VERSION.test(lesson.lesson_version)) throw new Error("invalid lesson_version");
  nonEmptyString(lesson.objective, "lesson objective");
  if (!Array.isArray(lesson.states) || !lesson.states.length) throw new Error("lesson states must be non-empty");
  for (const [index, item] of lesson.states.entries()) {
    exactObject(item, `lesson states[${index}]`, ["id", "label", "content"]);
    if (!SLUG.test(item.id)) throw new Error(`invalid lesson state id: ${item.id}`);
    nonEmptyString(item.label, `lesson states[${index}].label`);
    nonEmptyString(item.content, `lesson states[${index}].content`);
  }
  if (!Array.isArray(lesson.actions)) throw new Error("lesson actions must be an array");
  for (const [index, item] of lesson.actions.entries()) {
    exactObject(item, `lesson actions[${index}]`, ["id", "label"]);
    if (!SLUG.test(item.id)) throw new Error(`invalid lesson action id: ${item.id}`);
    nonEmptyString(item.label, `lesson actions[${index}].label`);
  }
  if (!Array.isArray(lesson.hints) || lesson.hints.some((hint) => typeof hint !== "string" || !hint.length)) throw new Error("lesson hints must be non-empty strings");
  if (!Array.isArray(lesson.static_fallback) || !lesson.static_fallback.length) throw new Error("static_fallback must be non-empty");
  const stateIds = new Set(lesson.states.map((state) => state.id));
  for (const [index, item] of lesson.static_fallback.entries()) {
    exactObject(item, `static_fallback[${index}]`, ["state_id", "content"]);
    if (!SLUG.test(item.state_id)) throw new Error(`invalid static fallback state id: ${item.state_id}`);
    nonEmptyString(item.content, `static_fallback[${index}].content`);
    if (!stateIds.has(item.state_id)) throw new Error(`static fallback references unknown state ${item.state_id}`);
  }
  exactObject(lesson.grader, "lesson grader", ["kind", "accepted"]);
  nonEmptyString(lesson.grader.kind, "lesson grader kind");
  if (!Array.isArray(lesson.grader.accepted)) throw new Error("lesson grader accepted must be an array");
  if (Object.hasOwn(lesson, "component_versions")) {
    exactObject(lesson.component_versions, "component_versions", [], Object.keys(lesson.component_versions || {}));
    if (Object.values(lesson.component_versions).some((version) => typeof version !== "string")) throw new Error("component versions must be strings");
  }
  if (Object.hasOwn(lesson, "transfer") && (!lesson.transfer || typeof lesson.transfer !== "object" || Array.isArray(lesson.transfer))) throw new Error("lesson transfer must be an object");
  return lesson;
}

export function createSession(lesson, initial = {}) {
  validateLesson(lesson);
  return { lesson_id: lesson.lesson_id, lesson_version: lesson.lesson_version, state_index: 0, actions: [], attempts: 0, highest_hint_level: 0, observations: {}, learner_authored: {}, uncertainty: "unknown", ...initial };
}

function allowedActions(lesson) {
  return new Set([...lesson.actions.map((action) => action.id), ...lesson.states.map((state) => `jump:${state.id}`)]);
}

export function transition(session, lesson, action) {
  validateLesson(lesson);
  if (!allowedActions(lesson).has(action)) throw new Error(`undeclared action: ${action}`);
  const next = { ...session, actions: [...session.actions, action], attempts: session.attempts + 1 };
  if (action === "previous") next.state_index = Math.max(0, session.state_index - 1);
  else if (action === "next") next.state_index = Math.min(lesson.states.length - 1, session.state_index + 1);
  else if (action.startsWith("jump:")) {
    const index = lesson.states.findIndex((state) => state.id === action.slice(5));
    if (index < 0) throw new Error("unknown jump target");
    next.state_index = index;
  } else if (action === "reset") return createSession(lesson);
  return next;
}

export function nextHint(session, lesson) {
  const index = Math.min(session.highest_hint_level, lesson.hints.length - 1);
  const hint = lesson.hints[index] ?? null;
  return { ...session, highest_hint_level: Math.min(session.highest_hint_level + 1, lesson.hints.length), hint };
}

export function recordAttempt(session, observation, explanation = "") {
  return { ...session, observations: { ...session.observations, ...observation }, learner_authored: { ...session.learner_authored, explanation } };
}

export function createReceipt(session, createdAt = "1970-01-01T00:00:00.000Z") {
  return { schema_version: "prax.learning-receipt/v1", lesson_id: session.lesson_id, lesson_version: session.lesson_version, actions: [...session.actions], attempts: session.attempts, highest_hint_level: session.highest_hint_level, observations: { ...session.observations }, learner_authored: { ...session.learner_authored }, uncertainty: session.uncertainty || "unknown", created_at: createdAt, ...(session.transfer ? { transfer: session.transfer } : {}) };
}

export function validateReceipt(receipt, lesson, maxBytes = 64 * 1024) {
  if (!receipt || typeof receipt !== "object") throw new Error("receipt must be an object");
  if (new TextEncoder().encode(JSON.stringify(receipt)).length > maxBytes) throw new Error("receipt exceeds size limit");
  const required = ["schema_version", "lesson_id", "lesson_version", "actions", "attempts", "highest_hint_level", "observations", "learner_authored", "uncertainty", "created_at"];
  const missing = required.filter((key) => !Object.hasOwn(receipt, key));
  if (missing.length) throw new Error(`receipt missing required fields: ${missing.join(", ")}`);
  const allowed = new Set([...required, "transfer"]);
  const unexpected = Object.keys(receipt).filter((key) => !allowed.has(key));
  if (unexpected.length) throw new Error(`receipt contains unexpected properties: ${unexpected.join(", ")}`);
  if (receipt.schema_version !== "prax.learning-receipt/v1") throw new Error("unsupported receipt schema_version");
  if (receipt.lesson_id !== lesson.lesson_id || receipt.lesson_version !== lesson.lesson_version) throw new Error("receipt belongs to another lesson version");
  if (!Array.isArray(receipt.actions) || !Number.isInteger(receipt.attempts) || receipt.attempts < 0) throw new Error("invalid receipt actions or attempts");
  const declaredActions = allowedActions(lesson);
  if (receipt.actions.some((action) => typeof action !== "string" || !declaredActions.has(action))) throw new Error("receipt contains an undeclared action");
  if (receipt.attempts < receipt.actions.length) throw new Error("receipt attempts cannot be less than its actions");
  if (!Number.isInteger(receipt.highest_hint_level) || receipt.highest_hint_level < 0 || receipt.highest_hint_level > lesson.hints.length) throw new Error("invalid receipt hint level");
  if (!receipt.observations || typeof receipt.observations !== "object" || Array.isArray(receipt.observations)) throw new Error("receipt observations must be an object");
  if (!receipt.learner_authored || typeof receipt.learner_authored !== "object" || Array.isArray(receipt.learner_authored)) throw new Error("receipt learner_authored must be an object");
  if (typeof receipt.uncertainty !== "string" || typeof receipt.created_at !== "string") throw new Error("receipt uncertainty and created_at must be strings");
  if (Object.hasOwn(receipt, "transfer") && (!receipt.transfer || typeof receipt.transfer !== "object" || Array.isArray(receipt.transfer))) throw new Error("receipt transfer must be an object");
  return receipt;
}

export function exportReceipt(session, lesson) {
  const receipt = createReceipt(session);
  validateReceipt(receipt, lesson);
  return `${JSON.stringify(receipt, null, 2)}\n`;
}

export function importReceipt(text, lesson) {
  let receipt;
  try { receipt = JSON.parse(text); } catch { throw new Error("receipt is not valid JSON"); }
  validateReceipt(receipt, lesson);
  let replayed = createSession(lesson);
  for (const action of receipt.actions) replayed = transition(replayed, lesson, action);
  return createSession(lesson, { ...receipt, state_index: replayed.state_index });
}

export function deleteReceipt(storage, key) {
  if (storage && typeof storage.removeItem === "function") storage.removeItem(key);
}

export function gradeExact(actual, accepted) { return accepted.some((value) => canonical(value) === canonical(actual)); }
export function gradeStructural(actual, predicate) { return Boolean(predicate(actual)); }

export function floatObservation(a = 0.1, b = 0.2, expectedDecimal = 0.3) {
  const result = a + b;
  return { intent: `${a} + ${b}`, result, exact_decimal: result === expectedDecimal, difference: result - expectedDecimal };
}

export function floatTransfer(a, b, expected) {
  const result = Number(a) + Number(b);
  const target = Number(expected);
  return { item_id: "float-transfer", result, expected: target, pass: Math.abs(result - target) <= Number.EPSILON };
}

const LEGAL_MOVE = /^(?:[URFDLB](?:2|')?)$/;
const ASCENDING = [-1, 0, 1];
const DESCENDING = [1, 0, -1];
const grid = (rows, columns, position, normal) => rows.flatMap((row) => columns.map((column) => ({ position: position(row, column), normal })));
const FACELETS = [
  ...grid(ASCENDING, ASCENDING, (z, x) => [x, 1, z], [0, 1, 0]),
  ...grid(DESCENDING, DESCENDING, (y, z) => [1, y, z], [1, 0, 0]),
  ...grid(DESCENDING, ASCENDING, (y, x) => [x, y, 1], [0, 0, 1]),
  ...grid(DESCENDING, ASCENDING, (z, x) => [x, -1, z], [0, -1, 0]),
  ...grid(DESCENDING, ASCENDING, (y, z) => [-1, y, z], [-1, 0, 0]),
  ...grid(DESCENDING, DESCENDING, (y, x) => [x, y, -1], [0, 0, -1]),
];
const FACE_LAYERS = Object.freeze({ U: [1, 1], R: [0, 1], F: [2, 1], D: [1, -1], L: [0, -1], B: [2, -1] });
const faceletKey = ({ position, normal }) => `${position.join(",")}|${normal.join(",")}`;
const FACELET_INDEX = new Map(FACELETS.map((facelet, index) => [faceletKey(facelet), index]));

function rotateQuarter([x, y, z], axis, sign) {
  if (axis === 0) return [x, sign * z, -sign * y];
  if (axis === 1) return [-sign * z, y, sign * x];
  return [sign * y, -sign * x, z];
}

function turnFace(stickers, face) {
  const [axis, sign] = FACE_LAYERS[face];
  const turned = [...stickers];
  for (let source = 0; source < FACELETS.length; source += 1) {
    const facelet = FACELETS[source];
    if (facelet.position[axis] !== sign) continue;
    const target = FACELET_INDEX.get(faceletKey({
      position: rotateQuarter(facelet.position, axis, sign),
      normal: rotateQuarter(facelet.normal, axis, sign),
    }));
    turned[target] = stickers[source];
  }
  return turned;
}

export function newCube() { return { stickers: [..."UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB"], moves: [] }; }
export function applyCubeMove(cube, notation) {
  if (!LEGAL_MOVE.test(notation)) throw new Error(`illegal cube move: ${notation}`);
  const turns = notation.endsWith("2") ? 2 : notation.endsWith("'") ? 3 : 1;
  let stickers = [...cube.stickers];
  for (let turn = 0; turn < turns; turn += 1) stickers = turnFace(stickers, notation[0]);
  return { stickers, moves: [...cube.moves, notation] };
}
export function cubeInvariant(cube) {
  if (!cube || cube.stickers.length !== 54) return false;
  const counts = Object.fromEntries("URFDLB".split("").map((color) => [color, 0]));
  for (const sticker of cube.stickers) if (!(sticker in counts)) return false; else counts[sticker] += 1;
  return Object.values(counts).every((count) => count === 9);
}
export function cubeViews(cube) {
  return { notation: cube.moves.join(" ") || "(start)", permutation: cube.stickers.join(""), spatial: cube.stickers.map((sticker, index) => `${index}:${sticker}`).join(" ") };
}

export function lostUpdate(schedule = ["A:read", "B:read", "A:write", "B:write"], start = 0) {
  const registers = { A: null, B: null }; let value = start; const timeline = [];
  for (const operation of schedule) {
    const [actor, phase] = operation.split(":");
    if (!(actor in registers) || !["read", "write"].includes(phase)) throw new Error(`invalid schedule operation: ${operation}`);
    if (phase === "read") registers[actor] = value;
    else value = registers[actor] + 1;
    timeline.push({ operation, value, cached: registers[actor] });
  }
  return { start, schedule: [...schedule], timeline, final: value, lost_update: value < start + 2 };
}
export function lostUpdateTransfer(schedule) { const result = lostUpdate(schedule); return { item_id: "lost-update-transfer", final: result.final, pass: !result.lost_update }; }

export const labs = Object.freeze({ floatObservation, floatTransfer, newCube, applyCubeMove, cubeInvariant, cubeViews, lostUpdate, lostUpdateTransfer });
