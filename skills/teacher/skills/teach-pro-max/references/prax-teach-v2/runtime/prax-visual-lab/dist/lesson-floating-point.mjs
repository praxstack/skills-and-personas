import { createSession, floatObservation, recordAttempt } from "./index.mjs";

const lesson = {
  schema_version: "prax.visual-lesson/v1",
  lesson_id: "python-floating-point",
  lesson_version: "1.0.0",
  objective: "Explain why decimal intent and binary floating-point results can differ.",
  states: [
    { id: "predict", label: "Predict", content: "Commit to a prediction before stepping." },
    { id: "represent", label: "Represent", content: "A finite decimal may be a repeating binary fraction." },
    { id: "compare", label: "Compare", content: "The evaluated result is 0.30000000000000004 on common binary IEEE-754 implementations." },
    { id: "transfer", label: "Transfer", content: "Try an unfamiliar case without the answer." },
  ],
  actions: [
    { id: "previous", label: "Previous" },
    { id: "next", label: "Next" },
    { id: "reset", label: "Reset" },
  ],
  hints: [
    "Write your prediction first.",
    "Compare the stored approximation with the decimal intent.",
    "Explain the repeated binary fraction rather than blaming arithmetic.",
  ],
  static_fallback: [
    { state_id: "predict", content: "Predict before stepping." },
    { state_id: "represent", content: "Inspect the representation." },
    { state_id: "compare", content: "Compare the result." },
    { state_id: "transfer", content: "Solve a fresh case." },
  ],
  grader: { kind: "exact", accepted: [] },
};

let session = createSession(lesson);
const stepper = document.querySelector("#stepper");
stepper.lesson = lesson;
const hints = document.querySelector("#hints");
hints.lesson = lesson;
const receipt = document.querySelector("#receipt");
receipt.lesson = lesson;
const parameter = document.querySelector("prax-parameter-lab");
const compare = document.querySelector("#compare");
function syncSession(event) {
  session = event.detail;
  stepper.session = session;
  hints.session = session;
  if (event.currentTarget !== receipt) receipt.session = session;
}
function comparisonViews(expectedDecimal = 0.3) {
  const observation = floatObservation(0.1, 0.2, expectedDecimal);
  return {
    decimal: observation.intent,
    boundary: String(expectedDecimal),
    result: String(observation.result),
    difference: String(observation.difference),
  };
}
function syncParameter(event) {
  const expectedDecimal = event.detail;
  const observation = floatObservation(0.1, 0.2, expectedDecimal);
  session = recordAttempt(session, {
    rounding_boundary: expectedDecimal,
    evaluated_result: observation.result,
    difference: observation.difference,
  }, session.learner_authored.explanation || "");
  compare.views = comparisonViews(expectedDecimal);
  stepper.session = session;
  hints.session = session;
  receipt.session = session;
}
stepper.session = session;
hints.session = session;
receipt.session = session;
stepper.addEventListener("statechange", syncSession);
hints.addEventListener("hint", syncSession);
receipt.addEventListener("receiptimport", syncSession);
parameter.addEventListener("parameterchange", syncParameter);
compare.views = comparisonViews();
