// Explorable lesson engine. One executable model drives every view: the
// figure, the readouts, the checks, the film and the report. A lesson is a
// plain object on window.LESSON (see ../SKILL.md for the shape).
//
// The flow per step, borrowed from manipulate-first courses: the learner moves
// the thing, commits an answer, and only then sees why. One hint after a miss,
// taught directly after a second miss. "Still confused?" swaps in a different
// explanation and records which ones were tried, so the teacher agent knows
// what didn't land.

import { seedFrom, rng, smoothPath, line, polyline, loop, arrow, arrowHead, curvedArrow, cross, tick, underline, swipe, ring, bracket } from "../../../lesson-notebook/assets/ink.js";
import { drawIn, svgEl, inkMark, handText, reducedMotion, scaledSize } from "../../../lesson-notebook/assets/pen.js";
import { soundButton } from "../../../lesson-notebook/assets/sound.js";
import { boardButton, restoreBoard } from "../../../lesson-notebook/assets/board.js";
import { createCodePanel } from "./code.js";
import { stepKeys, restoreProgress } from "./progress.js";

const INK = { seedFrom, rng, smoothPath, line, polyline, loop, arrow, arrowHead, curvedArrow, cross, tick, underline, swipe, ring, bracket };
const L = window.LESSON;
const query = new URLSearchParams(location.search);
const PRACTICE = query.has("practice") ? !["0", "false"].includes(query.get("practice")) : L.style === "practice-first";
const KEY = `explorable:v3:${L.id || L.title}:${PRACTICE ? "practice" : "explain"}`;
const CONSENT_KEY = `${KEY}:consent`;
document.documentElement.dataset.teachingStyle = PRACTICE ? "practice-first" : "visual-explain";
let rememberProgress = false;
try { rememberProgress = localStorage.getItem(CONSENT_KEY) === "yes"; } catch { /* ephemeral */ }
// Saved progress follows each step by key, so inserting, removing or
// reordering steps never hands a learner the answers of a different step.
const STEP_KEYS = stepKeys(L.steps);

// ---------- small DOM helpers ----------
function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") el.textContent = v;
    else if (k === "html") el.innerHTML = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) el.append(kid);
  return el;
}
// replaceChildren, minus the empty slots that optional parts leave behind.
// HTML to spoken/caption text: tags become spaces (so paragraphs don't run
// together, and one with no full stop gets one), then no space is left
// before punctuation ("outside , it").
function plainText(html) {
  return String(html || "")
    // A paragraph that ends without a stop gets one (looking past closing </strong> and the like),
    // unless a formula follows: "the points with</p><p class="nb-print">w₁x₁ + ..." reads on into it.
    .replace(/([^\s>])((?:<\/(?:strong|em|b|i|span|a|code|var|sub|sup)>)*)\s*<\/(p|li|h\d)>(?=[\s\S]*\S)(?!\s*<(?:pre\b|(?:p|div)\b[^>]*\bclass="[^"]*\b(?:nb-print|formula|math)\b))/g, (m, c, inl, tag) => `${c}${/[.!?:;]/.test(c) ? "" : "."}${inl}</${tag}>`)
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .replace(/\s+([,.;:!?)])/g, "$1")
    .replace(/\(\s+/g, "(")
    .trim();
}

function put(el, ...kids) {
  el.replaceChildren(...kids.flat().filter((k) => k !== null && k !== undefined && k !== false));
}
const load = () => {
  if (!rememberProgress) return {};
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
};
const save = (data) => {
  if (!rememberProgress) return;
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    /* storage blocked: the lesson still works, it just won't remember */
  }
};
const fmt = (spec, v) => (spec.fmt ? spec.fmt(v) : `${+v.toFixed(spec.decimals ?? (spec.step < 1 ? 2 : 0))}${spec.unit ? ` ${spec.unit}` : ""}`);

// ---------- state ----------
const defaults = Object.fromEntries(Object.entries(L.params || {}).map(([k, s]) => [k, s.value]));
// Eased values snap to their slider's step, so a whole-number setting never
// passes through 0.4 on its way from 0 to 1 (figures branch on those values).
const snap = (k, v) => {
  const st = L.params?.[k]?.step;
  return st >= 1 ? Math.round(v / st) * st : v;
};
const stored = restoreProgress(load(), STEP_KEYS);
const S = {
  params: { ...defaults },
  step: Math.min(stored.step, L.steps.length - 1),
  done: new Set(stored.done),
  attempts: stored.attempts, // step -> [{answer, right}]
  tried: stored.tried, // step -> [alt labels]
  curious: stored.curious, // questions the learner wants to chase
  explained: stored.explained, // step -> { text, covered: [point indexes] }
  altIndex: {},
  view: "lesson",
};
const persist = () =>
  save({ steps: STEP_KEYS, step: S.step, done: [...S.done], attempts: S.attempts, tried: S.tried, notes: notesBox?.value, curious: S.curious, explained: S.explained });

// ---------- figure ----------
// Narrow figures get their own layout when the lesson asks for one:
// figure.viewBox may be a function of `narrow`, and draw() receives kit.narrow
// to rearrange panels. "Narrow" is the figure's own width, not the window's,
// so a tablet column counts too.
const NARROW_PX = 600;
function makeKit(parent, pen, narrow, progress, counter = { n: 0 }) {
  // progress may be a number or a function of the mark's order (one pen, one mark after another).
  const pr = () => (typeof progress === "function" ? progress(counter.n++) : progress);
  // Narrow figures can ask for bigger text (figure.narrowText, e.g. 1.5) so labels stay readable.
  const scale = narrow ? L.figure.narrowText ?? 1 : 1;
  return {
    ink: INK,
    pen,
    narrow,
    textScale: scale,
    layer: parent,
    el: (tag, attrs = {}) => svgEl(tag, tag === "text" ? { ...attrs, "font-size": scaledSize(attrs, scale) } : attrs, parent),
    // progress (0..1) draws marks and handwriting part-way: used for frame-exact video export.
    mark: (paths, opts = {}) => {
      const p = pr();
      return inkMark(parent, paths, { pen, ...opts, ...(p === undefined ? {} : { progress: p }) });
    },
    hand: (x, y, text, opts = {}) => {
      const p = pr();
      const t = handText(parent, x, y, text, { pen: p === undefined && pen, ...opts, size: scaledSize({ class: "t-hand", "font-size": opts.size }, scale) });
      if (p !== undefined && p < 1) t.style.clipPath = `inset(-20% ${(100 * (1 - p)).toFixed(1)}% -20% -2%)`;
      return t;
    },
    seed: (name) => seedFrom(`${L.id}:${name}`),
    group: (transform) => makeKit(svgEl("g", { transform: transform || null }, parent), pen, narrow, progress, counter),
  };
}
function makeFigure() {
  const svg = svgEl("svg", { role: "img", class: "ink-svg" });
  const title = svgEl("title", {}, svg);
  const layer = svgEl("g", {}, svg);
  let last = S.params;
  let narrow = window.innerWidth < NARROW_PX + 40;
  function render({ pen = false, params = S.params, progress } = {}) {
    last = params;
    const vb = L.figure.viewBox;
    svg.setAttribute("viewBox", (typeof vb === "function" ? vb(narrow) : vb) || "0 0 640 380");
    const s = L.model(params);
    layer.replaceChildren();
    L.figure.draw(layer, s, params, makeKit(layer, pen, narrow, progress));
    title.textContent = L.figure.label ? L.figure.label(s, params) : L.title;
    return s;
  }
  if ("ResizeObserver" in window) {
    new ResizeObserver(([entry]) => {
      const w = entry.contentRect.width;
      if (!w || w < NARROW_PX === narrow) return;
      narrow = w < NARROW_PX;
      render({ params: last });
    }).observe(svg);
  }
  return { svg, render, setNarrow: (v) => (narrow = v) };
}

// ---------- layout ----------
const app = document.getElementById("app");
const fig = makeFigure();
const readouts = h("div", { class: "xp-readouts nb-print", "aria-live": "polite" });
const controls = h("div", { class: "xp-controls" });
const stepBox = h("article", { class: "xp-step" });
const outlineList = h("ol", { class: "xp-outline-list" });
const takeaways = h("ul", { class: "xp-takeaways" });
let notesBox;

function progressConsent() {
  const input = h("input", { type: "checkbox", id: "xp-remember", checked: rememberProgress ? true : null });
  input.addEventListener("change", () => {
    rememberProgress = input.checked;
    try {
      if (rememberProgress) { localStorage.setItem(CONSENT_KEY, "yes"); persist(); }
      else { localStorage.removeItem(KEY); localStorage.removeItem(CONSENT_KEY); }
    } catch { rememberProgress = false; input.checked = false; }
  });
  return h("label", { class: "xp-consent nb-print", for: "xp-remember" }, input, " Remember progress on this device");
}
function sourcePanel() {
  const items = (L.sources || []).map((source) => typeof source === "string" ? { title: source, url: source } : source)
    .filter((source) => /^https?:\/\//.test(source.url || source.href || ""));
  if (!items.length) return null;
  return h("aside", { class: "xp-sources", "aria-label": "Sources and scope" }, h("h3", { class: "nb-label", text: "Sources and scope" }),
    h("ul", {}, items.map((source) => h("li", {}, h("a", { href: source.url || source.href, target: "_blank", rel: "noopener noreferrer", text: source.title || source.label || source.url }), source.note ? `: ${source.note}` : ""))),
    L.limits ? h("p", { text: L.limits }) : null);
}
function header() {
  const tabs = h(
    "div",
    { class: "xp-tabs", role: "tablist", "aria-label": "Views" },
    ["lesson", "film", ...(L.code ? ["code"] : []), "notes"].map((v) =>
      h("button", {
        type: "button",
        role: "tab",
        class: "xp-tab",
        id: `tab-${v}`,
        "aria-selected": String(S.view === v),
        "aria-controls": `view-${v}`,
        text: { lesson: "Lesson", film: "Film", code: "Code", notes: "Notes and report" }[v],
        onclick: () => show(v),
      }),
    ),
  );
  return h(
    "header",
    { class: "xp-head" },
    h("div", { class: "xp-head-text" }, h("p", { class: "nb-label", text: [L.subject, L.level].filter(Boolean).join(" · ") || "Lesson" }), h("h1", { text: L.title }), L.subtitle ? h("p", { class: "xp-sub", text: L.subtitle }) : null),
    h("div", { class: "xp-head-tools" }, tabs, boardButton(), soundButton(), progressConsent()),
    PRACTICE ? h("p", { class: "xp-mode" }, "Practice mode. ", h("a", { href: `${location.pathname}?practice=0`, text: "Read the complete explanation instead" })) : null,
  );
}

function outlinePanel() {
  return h(
    "nav",
    { class: "xp-outline", "aria-label": "Contents" },
    h("h2", { class: "nb-label", text: "Contents" }),
    outlineList,
    h("div", { class: "xp-progress", role: "progressbar", "aria-label": "Steps done", "aria-valuemin": "0", "aria-valuemax": String(L.steps.length) }, h("span")),
  );
}

function paintOutline() {
  outlineList.replaceChildren(
    ...L.steps.map((st, i) =>
      h(
        "li",
        {},
        h(
          "button",
          {
            type: "button",
            class: `xp-outline-item${S.done.has(i) ? " is-done" : ""}`,
            "aria-current": i === S.step ? "step" : null,
            onclick: () => goStep(i),
          },
          h("span", { class: "xp-num nb-print", text: String(i + 1) }),
          h("span", { text: st.title }),
          S.done.has(i) ? h("span", { class: "xp-tick nb-hand is-red", "aria-label": "done", text: "✓" }) : null,
        ),
      ),
    ),
  );
  const bar = document.querySelector(".xp-progress");
  if (bar) {
    bar.setAttribute("aria-valuenow", String(S.done.size));
    bar.firstChild.style.width = `${(100 * S.done.size) / L.steps.length}%`;
  }
}

function paintTakeaways() {
  const items = L.steps.map((st, i) => (S.done.has(i) && st.note ? st.note : null)).filter(Boolean);
  takeaways.replaceChildren(...(items.length ? items.map((t) => h("li", { class: "nb-note", text: t })) : [h("li", { class: "xp-muted", text: "The coach's notes appear here as you finish each step." })]));
}

function notesPanel() {
  notesBox = h("textarea", { class: "nb-field xp-notes-box", "aria-label": "Your notes", placeholder: "Your own words. Explaining it back is the fastest way to find a gap." });
  notesBox.value = stored.notes || "";
  notesBox.addEventListener("input", persist);
  return h(
    "aside",
    { class: "xp-margin", "aria-label": "Margin notes" },
    h("h2", { class: "nb-label", text: "In the margin" }),
    takeaways,
    h("h2", { class: "nb-label", text: "Your notes" }),
    notesBox,
    curiousPanel(),
  );
}

// Questions the learner wants to chase. Each one becomes a next step for the teacher.
function curiousPanel() {
  const list = h("ul", { class: "xp-curious" });
  const input = h("input", { type: "text", class: "nb-field", id: "xp-curious-input", "aria-label": "Something you're curious about", placeholder: "I'm curious about…" });
  const paint = () => list.replaceChildren(...S.curious.map((q, k) => h("li", {}, h("span", { class: "nb-hand", text: q }), h("button", { type: "button", class: "nb-btn nb-btn-quiet", "aria-label": `Remove: ${q}`, text: "×", onclick: () => (S.curious.splice(k, 1), persist(), paint()) }))));
  const add = () => {
    const q = input.value.trim();
    if (!q) return;
    S.curious.push(q);
    input.value = "";
    persist();
    paint();
  };
  input.addEventListener("keydown", (e) => e.key === "Enter" && (e.preventDefault(), add()));
  paint();
  return h("div", { class: "xp-curious-box" }, h("h2", { class: "nb-label", text: "Questions to chase" }), list, h("div", { class: "xp-row" }, input, h("button", { type: "button", class: "nb-btn", text: "Add", onclick: add })));
}

// ---------- controls ----------
function paintControls(step) {
  const names = step.controls ?? Object.keys(L.params || {});
  controls.replaceChildren(
    ...names.map((name) => {
      const spec = L.params[name];
      const id = `p-${name}`;
      const out = h("output", { for: id, class: "nb-print", text: fmt(spec, S.params[name]) });
      const input = h("input", { type: "range", id, min: spec.min, max: spec.max, step: spec.step ?? 1, value: S.params[name] });
      input.addEventListener("input", () => {
        S.params[name] = Number(input.value);
        out.textContent = fmt(spec, S.params[name]);
        update();
      });
      return h("div", { class: "xp-control" }, h("label", { for: id }, h("span", { text: spec.label }), out), input, spec.hint ? h("p", { class: "xp-muted", text: spec.hint }) : null);
    }),
  );
}

let stepCode = null;
function lineFor(step, s) {
  return typeof step.line === "function" ? step.line(S.params, s) : step.line;
}
function update({ pen = false } = {}) {
  const s = fig.render({ pen });
  if (stepCode) {
    stepCode.setLine(lineFor(L.steps[S.step], s));
  }
  codeView?.refresh();
  const rows = L.readouts ? L.readouts(s, S.params) : [];
  // A row is [label, value] or [label, value, { keepCase: true }] for labels
  // where case matters (|a| vs |A|); labels are otherwise set in capitals.
  readouts.replaceChildren(...rows.map(([k, v, o]) => h("span", { class: "xp-readout" }, h("span", { class: `nb-label${o && o.keepCase ? " xp-keep-case" : ""}`, text: k }), ` ${v}`)));
  return s;
}

// ---------- steps ----------
function answerOf(ask) {
  const s = L.model(S.params);
  return typeof ask.answer === "function" ? ask.answer(S.params, s) : ask.answer;
}

// Explain it back: the learner answers in their own words, then compares with
// the teacher's version and ticks the key points they covered. The text goes
// into the report, so the teacher can correct it in the next turn.
function explainBox(step, i) {
  const ask = step.ask;
  const prev = S.explained[i];
  const text = h("textarea", { class: "nb-field xp-explain", id: `xp-explain-${i}`, rows: 4, "aria-label": ask.q, placeholder: "In your own words…" });
  text.value = prev?.text || "";
  const reveal = h("div", { class: "xp-feedback", "aria-live": "polite" });
  const go = h("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Compare with the teacher's version" });
  const box = h("div", { class: "xp-ask nb-sheet", role: "group", "aria-label": "Explain it back" }, h("p", { class: "xp-q", text: ask.q }), h("p", { class: "xp-muted", text: "Write it before you look. A rough answer is fine; the gaps are the point." }), text, h("div", { class: "xp-row" }, go), reveal);
  const covered = new Set(prev?.covered || []);
  const keep = () => {
    S.explained[i] = { text: text.value.trim(), covered: [...covered] };
    persist();
  };
  // Once the teacher's version is shown, later edits are saved too (the report
  // reads them), a moment after typing stops and when the box loses focus.
  let revealed = false;
  let typing;
  text.addEventListener("input", () => {
    if (!revealed) return;
    clearTimeout(typing);
    typing = setTimeout(keep, 400);
  });
  text.addEventListener("change", () => revealed && (clearTimeout(typing), keep()));
  const showModel = () => {
    revealed = true;
    const checks = (ask.points || []).map((pt, k) => {
      const cb = h("input", { type: "checkbox", id: `xp-pt-${i}-${k}`, checked: covered.has(k) ? true : null });
      cb.addEventListener("change", () => {
        cb.checked ? covered.add(k) : covered.delete(k);
        keep();
      });
      return h("li", {}, cb, " ", h("label", { for: `xp-pt-${i}-${k}`, text: pt }));
    });
    put(reveal, 
      h("p", { class: "nb-label", text: "How the teacher would put it" }),
      h("div", { class: "xp-why", html: ask.model || "" }),
      checks.length ? h("p", { class: "nb-label", text: "Tick what your answer covered" }) : null,
      checks.length ? h("ul", { class: "xp-points" }, checks) : null,
      h("p", { class: "nb-hand", text: "Missed something? That's the bit to say out loud once more." }),
    );
    keep();
    finishStep(i);
  };
  go.addEventListener("click", () => {
    if (PRACTICE && text.value.trim().length < 12) {
      put(reveal, h("p", { class: "nb-hand is-red", text: "Give it a go first: a sentence or two." }));
      return text.focus();
    }
    showModel();
  });
  if (prev) showModel();
  return box;
}

// Choice options in a fixed shuffled order per question, so the right answer
// isn't always in the same place. Options that are all numbers keep their
// order (a scale reads best sorted), and so does an ask with keepOrder: true.
// Returns the original indices in display order.
function optionOrder(options, key, keepOrder = false) {
  const idx = options.map((_, k) => k);
  if (keepOrder || options.every((o) => /^\s*[-−+]?\d*\.?\d+\s*$/.test(String(o)))) return idx;
  const rand = rng(seedFrom(key));
  for (let k = idx.length - 1; k > 0; k -= 1) {
    const j = Math.floor(rand() * (k + 1));
    [idx[k], idx[j]] = [idx[j], idx[k]];
  }
  return idx;
}

function askBox(step, i) {
  const ask = step.ask;
  const box = h("div", { class: "xp-ask nb-sheet", role: "group", "aria-label": "Your answer" });
  const feedback = h("div", { class: "xp-feedback", "aria-live": "polite" });
  const log = (S.attempts[i] ||= []);
  let choice = null;
  let input;
  const inputs = [];
  if (ask.kind === "number") {
    input = h("input", { type: "number", class: "nb-field", inputmode: "decimal", step: "any", "aria-label": ask.q });
    inputs.push(h("div", { class: "xp-number" }, input, ask.unit ? h("span", { class: "nb-print", text: ask.unit }) : null));
  } else {
    inputs.push(
      h(
        "div",
        { class: "xp-options" },
        optionOrder(ask.options, `${L.id}:${i}`, ask.keepOrder).map((k) =>
          h("button", {
            type: "button",
            class: "xp-option",
            "aria-pressed": "false",
            "data-k": String(k),
            text: ask.options[k],
            onclick: (e) => {
              choice = k;
              box.querySelectorAll(".xp-option").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget)));
            },
          }),
        ),
      ),
    );
  }
  const check = h("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Check" });
  const giveUp = h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "Show me" });
  function resolve(right, revealed) {
    box.classList.toggle("is-right", right);
    box.classList.toggle("is-taught", !right);
    check.disabled = true;
    giveUp.hidden = true;
    const ans = answerOf(ask);
    const answerText = ask.kind === "number" ? `${+Number(ans).toFixed(ask.decimals ?? 2)}${ask.unit ? ` ${ask.unit}` : ""}` : ask.options[ans];
    put(feedback, 
      h("p", { class: `nb-hand ${right ? "" : "is-red"}`, "data-write": "", text: right ? "Yes. Here's why." : revealed ? `It's: ${answerText}.` : `Not quite. It's: ${answerText}.` }),
      h("p", { class: "xp-why", html: ask.why || "" }),
    );
    drawIn(feedback);
    finishStep(i);
  }
  check.addEventListener("click", () => {
    const ans = answerOf(ask);
    let right;
    let given;
    if (ask.kind === "number") {
      if (input.value.trim() === "") return input.focus();
      given = Number(input.value);
      right = Math.abs(given - ans) <= (ask.tol ?? 1e-9);
    } else {
      if (choice === null) return;
      given = ask.options[choice];
      right = choice === ans;
    }
    log.push({ given, right });
    persist();
    if (right) return resolve(true);
    if (log.filter((a) => !a.right).length >= 2) return resolve(false);
    put(feedback, h("p", { class: "nb-hand is-red", "data-write": "", text: ask.hint || "Not yet. Move the slider and watch what changes, then try again." }));
    drawIn(feedback);
  });
  giveUp.addEventListener("click", () => {
    log.push({ given: null, right: false, asked: true });
    persist();
    resolve(false, true);
  });
  box.append(h("p", { class: "xp-q", text: ask.q }), ...inputs, h("div", { class: "xp-row" }, check, giveUp), feedback);
  return box;
}

function confusedBox(step, i) {
  const alts = step.alts || [];
  const slot = h("div", { class: "xp-alt-slot", "aria-live": "polite" });
  const media = h(
    "div",
    { class: "xp-row xp-media" },
    h("span", { class: "nb-label", text: "Or see it as" }),
    h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "a film", onclick: () => (S.mediaAsked = [...(S.mediaAsked || []), `film at step ${i + 1}`], show("film")) }),
    L.code ? h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "code", onclick: () => (S.mediaAsked = [...(S.mediaAsked || []), `code at step ${i + 1}`], show("code")) }) : null,
  );
  if (!alts.length) return h("div", { class: "xp-confused" }, media, slot);
  const btn = h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "Still confused? Try another way" });
  btn.addEventListener("click", () => {
    const k = (S.altIndex[i] = ((S.altIndex[i] ?? -1) + 1) % alts.length);
    const alt = alts[k];
    (S.tried[i] ||= []).includes(alt.label) || S.tried[i].push(alt.label);
    persist();
    if (alt.set) Object.assign(S.params, alt.set), paintControls(step);
    update({ pen: true });
    drawIn(stage);
    put(slot, h("div", { class: "xp-alt nb-printout" }, h("p", { class: "nb-label", text: alt.label }), h("p", { html: alt.say })));
    btn.textContent = k + 1 < alts.length ? "Still not it? Another way" : "Back to the first other way";
  });
  return h("div", { class: "xp-confused" }, btn, media, slot);
}

let stage;
function finishStep(i) {
  S.done.add(i);
  persist();
  paintOutline();
  paintTakeaways();
  const next = stepBox.querySelector(".xp-next");
  if (next) next.disabled = false;
}

// A step's settings are the defaults plus every step's `set` up to it, so a
// reload, a #step-N link or an outline jump shows the same figure (and the
// same quiz answer) as walking there. Slider moves last until the step changes.
const paramsAt = (i) => L.steps.slice(0, i + 1).reduce((acc, st) => Object.assign(acc, st.set || {}), { ...defaults });
let paramsStep = null;

function goStep(i, { focus = true } = {}) {
  S.step = Math.max(0, Math.min(L.steps.length - 1, i));
  const step = L.steps[S.step];
  if (paramsStep !== S.step) (S.params = paramsAt(S.step)), (paramsStep = S.step);
  persist();
  paintOutline();
  paintControls(step);
  const last = S.step === L.steps.length - 1;
  const next = h("button", {
    type: "button",
    class: "nb-btn nb-btn-primary xp-next",
    text: last ? "Where to next?" : "Next",
    disabled: PRACTICE && step.ask && !S.done.has(S.step) ? true : null,
    onclick: () => (last ? endPanel() : goStep(S.step + 1)),
  });
  const prev = h("button", { type: "button", class: "nb-btn", text: "Back", disabled: S.step === 0 ? true : null, onclick: () => goStep(S.step - 1) });
  stage = h("figure", { class: "xp-figure nb-sheet" }, fig.svg, readouts);
  stepCode = L.code && step.line !== undefined ? createCodePanel(L.code, { h, getParams: () => S.params }) : null;
  const hook = S.step === 0 && L.hook ? h("aside", { class: "xp-hook nb-printout" }, h("p", { class: "nb-label", text: "Why this mattered" }), h("div", { html: L.hook })) : null;
  put(stepBox, 
    ...[
    h("p", { class: "nb-label", text: `Step ${S.step + 1} of ${L.steps.length}` }),
    h("h2", { tabindex: "-1", text: step.title }),
    PRACTICE ? hook : null,
    stage,
    controls,
    !PRACTICE ? hook : null,
    h("div", { class: "xp-say", html: step.say }),
    stepCode ? stepCode.el : null,
    step.lookFor ? h("p", { class: "xp-lookfor" }, h("span", { class: "nb-label", text: "Look for" }), h("span", { class: "nb-hand", text: step.lookFor })) : null,
    !PRACTICE && step.ask && (step.ask.why || step.ask.model) ? h("div", { class: "xp-explanation nb-printout", html: step.ask.why || step.ask.model }) : null,
    step.ask ? (PRACTICE ? (step.ask.kind === "explain" ? explainBox(step, S.step) : askBox(step, S.step))
      : h("details", { class: "xp-optional-practice" }, h("summary", { text: "Optional practice" }), step.ask.kind === "explain" ? explainBox(step, S.step) : askBox(step, S.step))) : null,
    sourcePanel(),
    confusedBox(step, S.step),
    h("div", { class: "xp-row xp-nav" }, prev, next),
    ].filter(Boolean),
  );
  if (!PRACTICE || !step.ask) finishStep(S.step);
  update({ pen: true });
  drawIn(stage);
  if (focus) stepBox.querySelector("h2").focus({ preventScroll: false });
}

// ---------- the end: keep going until the learner is satisfied ----------
function report(choice, text) {
  const lines = [`Lesson: ${L.title}${L.id ? ` (${L.id})` : ""}`, `${PRACTICE ? "Steps done" : "Steps viewed"}: ${S.done.size}/${L.steps.length}`, `Practice: ${PRACTICE ? "requested" : "optional; viewing is not proof of learning"}`];
  L.steps.forEach((st, i) => {
    const a = S.attempts[i];
    const t = S.tried[i];
    if (!a?.length && !t?.length) return;
    const misses = (a || []).filter((x) => !x.right).length;
    const parts = [];
    if (a?.length) parts.push(misses ? `${misses} miss${misses > 1 ? "es" : ""}${a.some((x) => x.asked) ? ", asked to be shown" : ""}` : "right first time");
    if (t?.length) parts.push(`tried other explanations: ${t.join("; ")}`);
    lines.push(`- ${st.title}: ${parts.join(", ")}`);
  });
  L.steps.forEach((st, i) => {
    const e = S.explained[i];
    if (e?.text) lines.push(`- My explanation of "${st.title}": ${e.text}${st.ask?.points ? ` (covered ${e.covered.length}/${st.ask.points.length} key points)` : ""}`);
  });
  if (S.mediaAsked?.length) lines.push(`Asked to see it as: ${S.mediaAsked.join("; ")}`);
  if (S.curious.length) lines.push(`Questions I want to chase: ${S.curious.join(" | ")}`);
  if (notesBox?.value.trim()) lines.push(`My notes: ${notesBox.value.trim()}`);
  lines.push(`Next: ${choice}${text ? `. ${text}` : ""}`);
  return lines.join("\n");
}

function endPanel() {
  const out = h("textarea", { class: "nb-field xp-report", readonly: true, "aria-label": "Message for your teacher" });
  const extra = h("input", { type: "text", class: "nb-field", "aria-label": "Anything else? (optional)", placeholder: "Anything else? What's still fuzzy?" });
  const copy = h("button", { type: "button", class: "nb-btn", text: "Copy for the teacher" });
  const copied = h("span", { class: "nb-hand", "aria-live": "polite" });
  let choice = "";
  const choices = [
    ["satisfied", "I've got it. I'm done with this."],
    ["deeper", "Go deeper. Show me how it really works."],
    ["example", "Give me another example."],
    ["differently", "Explain it a different way."],
    ["practice", "Let me practise it."],
  ];
  const fill = () => (out.value = report(choice, extra.value.trim()));
  copy.addEventListener("click", async () => {
    fill();
    try {
      await navigator.clipboard.writeText(out.value);
      copied.textContent = "Copied. Paste it back to your teacher.";
    } catch {
      out.focus();
      out.select();
      copied.textContent = "Selected. Copy it with your keyboard.";
    }
  });
  extra.addEventListener("input", fill);
  put(stepBox, 
    h("p", { class: "nb-label", text: "End of the lesson, not the end of learning" }),
    h("h2", { tabindex: "-1", text: "Where to next?" }),
    h("p", { text: "You decide when this is done. Pick what you want, then send the note below to your teacher so the next part fits you." }),
    h(
      "div",
      { class: "xp-choices" },
      choices.map(([key, label]) =>
        h("button", {
          type: "button",
          class: "xp-option",
          "aria-pressed": "false",
          "data-choice": key,
          text: label,
          onclick: (e) => {
            choice = label;
            stepBox.querySelectorAll("[data-choice]").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget)));
            fill();
          },
        }),
      ),
    ),
    (L.deeper || []).length ? h("div", { class: "nb-printout" }, h("p", { class: "nb-label", text: "Questions to chase next" }), h("ul", {}, L.deeper.map((q) => h("li", { text: q })))) : null,
    extra,
    out,
    h("div", { class: "xp-row" }, copy, copied, h("button", { type: "button", class: "nb-btn", text: "Back to the lesson", onclick: () => goStep(S.step) })),
  );
  fill();
  stepBox.querySelector("h2").focus();
}

// ---------- the film: the same model, narrated ----------
function filmView() {
  const scenes = L.film || L.steps.map((st) => ({ chapter: st.title, say: st.filmSay || plainText(st.say), set: st.set || {} }));
  // Each scene's "set" adds to the ones before it, as in the narrated export,
  // so a scene that sets one value keeps the rest from earlier scenes.
  const sceneParams = [];
  scenes.reduce((acc, sc) => {
    const next = { ...acc, ...(sc.set || {}) };
    sceneParams.push(next);
    return next;
  }, { ...defaults });
  const chapters = [];
  scenes.forEach((sc, i) => (!chapters.length || chapters.at(-1).name !== sc.chapter) && chapters.push({ name: sc.chapter, start: i }));
  const ffig = makeFigure();
  const params = { ...defaults };
  const caption = h("p", { class: "xp-film-caption nb-hand", "aria-live": "polite" });
  const counter = h("span", { class: "nb-print" });
  const play = h("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Play" });
  const prev = h("button", { type: "button", class: "nb-btn", "aria-label": "Previous scene", text: "‹" });
  const next = h("button", { type: "button", class: "nb-btn", "aria-label": "Next scene", text: "›" });
  const scrub = h("input", { type: "range", min: 0, max: scenes.length - 1, value: 0, "aria-label": "Scene" });
  const speed = h("select", { class: "nb-field", "aria-label": "Speed" }, [0.75, 1, 1.25, 1.5].map((v) => h("option", { value: v, text: `${v}×`, selected: v === 1 ? true : null })));
  // No browser speech voice: it sounds robotic. The human-sounding voice is in
  // the narrated video (scripts/narrate.py), linked from the course map.
  const chips = h("ol", { class: "xp-chapters" }, chapters.map((c, i) => h("li", {}, h("button", { type: "button", class: "xp-chip", "data-start": c.start, text: `${i + 1}. ${c.name}`, onclick: () => go(c.start, { keep: true }) }))));
  const transcript = h("details", { class: "xp-transcript" }, h("summary", { text: "Transcript" }), h("ol", {}, scenes.map((s) => h("li", { text: s.say }))));
  let index = 0;
  let playing = false;
  let token = 0;
  const sleep = (ms, my) => new Promise((r) => setTimeout(r, ms)).then(() => my === token);
  const readMs = (t) => Math.max(2600, t.split(/\s+/).length * 360 + 1100) / Number(speed.value);

  function tweenTo(target, ms, my) {
    const from = { ...params };
    const keys = Object.keys(target).filter((k) => typeof target[k] === "number");
    if (reducedMotion() || ms <= 0 || !keys.length) {
      Object.assign(params, target);
      ffig.render({ params });
      return Promise.resolve();
    }
    return new Promise((resolve) => {
      const t0 = performance.now();
      const frame = (now) => {
        if (my !== token) return resolve();
        const p = Math.min(1, (now - t0) / ms);
        const e = p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2;
        for (const k of keys) params[k] = snap(k, from[k] + (target[k] - from[k]) * e);
        ffig.render({ params });
        if (p < 1) requestAnimationFrame(frame);
        else resolve();
      };
      requestAnimationFrame(frame);
    });
  }
  function speak(text, my) {
    return sleep(readMs(text), my);
  }
  function paint() {
    const sc = scenes[index];
    caption.textContent = sc.say;
    counter.textContent = `${index + 1} / ${scenes.length}`;
    scrub.value = index;
    play.textContent = playing ? "Pause" : index === scenes.length - 1 ? "Replay" : "Play";
    play.setAttribute("aria-pressed", String(playing));
    prev.disabled = index === 0;
    next.disabled = index === scenes.length - 1;
    const ch = chapters.findLast((c) => c.start <= index);
    chips.querySelectorAll(".xp-chip").forEach((b) => b.classList.toggle("is-current", Number(b.dataset.start) === ch.start));
  }
  async function go(i, { keep = false, animate = true } = {}) {
    const my = ++token;
    if (!keep) playing = false;
    index = Math.max(0, Math.min(scenes.length - 1, i));
    const sc = scenes[index];
    // Captions make claims about this scene, so the displayed state must
    // already agree when the caption appears. Controls provide exploration.
    const moving = tweenTo(sceneParams[index], 0, my);
    paint();
    if (!playing) return moving;
    await Promise.all([moving, speak(sc.say, my)]);
    if (my !== token || !playing) return;
    if (index < scenes.length - 1) go(index + 1, { keep: true });
    else (playing = false), paint();
  }
  play.addEventListener("click", () => {
    if (playing) {
      playing = false;
      token++;
        return paint();
    }
    playing = true;
    go(index === scenes.length - 1 ? 0 : index, { keep: true });
  });
  prev.addEventListener("click", () => go(index - 1, { keep: playing }));
  next.addEventListener("click", () => go(index + 1, { keep: playing }));
  scrub.addEventListener("input", () => go(Number(scrub.value), { animate: false }));
  const root = h(
    "section",
    { class: "xp-film", tabindex: "0", "aria-label": `${L.title} film. Space plays or pauses, arrow keys change scene.` },
    h("figure", { class: "xp-figure nb-sheet" }, ffig.svg),
    caption,
    h("div", { class: "xp-film-bar" }, play, prev, next, scrub, counter, speed),
    chips,
    transcript,
  );
  root.addEventListener("keydown", (e) => {
    if (["INPUT", "SELECT", "TEXTAREA", "BUTTON", "SUMMARY"].includes(e.target.tagName)) return;
    if (e.key === " ") e.preventDefault(), play.click();
    else if (e.key === "ArrowRight") e.preventDefault(), next.click();
    else if (e.key === "ArrowLeft") e.preventDefault(), prev.click();
  });
  go(0, { animate: false });
  return { el: root, stop: () => ((playing = false), token++, paint()) };
}

// ---------- views ----------
let film;
let codeView = null;
const views = {};
function show(v) {
  S.view = v;
  document.querySelectorAll(".xp-tab").forEach((t) => t.setAttribute("aria-selected", String(t.id === `tab-${v}`)));
  for (const [k, el] of Object.entries(views)) el.hidden = k !== v;
  if (v !== "film") film?.stop();
  if (v === "film" && !film) {
    film = filmView();
    views.film.append(film.el);
  }
  if (v === "notes") paintTakeaways();
  if (v === "code" && !codeView) {
    codeView = createCodePanel(L.code, { h, getParams: () => S.params });
    views.code.append(h("p", { class: "xp-muted", text: "The lesson's code, using the inputs you set in the lesson." }), codeView.el);
  }
}

function boot() {
  restoreBoard(L.board || "auto");
  views.lesson = h("div", { class: "xp-layout", id: "view-lesson", role: "tabpanel", "aria-labelledby": "tab-lesson" }, outlinePanel(), h("main", { class: "xp-main" }, stepBox), notesPanel());
  views.film = h("div", { class: "xp-single", id: "view-film", role: "tabpanel", "aria-labelledby": "tab-film", hidden: true });
  views.notes = h(
    "div",
    { class: "xp-single", id: "view-notes", role: "tabpanel", "aria-labelledby": "tab-notes", hidden: true },
    h(
      "section",
      { class: "xp-notes-page" },
      h("h2", { text: "Notes" }),
      h("p", { class: "xp-muted", text: "The lesson's key ideas, kept apart from the lesson so you can review them on their own." }),
      h("ol", { class: "xp-key-ideas" }, L.steps.map((st) => h("li", {}, h("strong", { text: st.title }), st.note ? h("span", { class: "nb-note", text: ` ${st.note}` }) : null))),
      L.misconceptions?.length ? [h("h3", { text: "Common mix-ups" }), h("ul", {}, L.misconceptions.map((m) => h("li", { text: m })))] : null,
      L.deeper?.length ? [h("h3", { text: "Go deeper" }), h("ul", {}, L.deeper.map((m) => h("li", { text: m })))] : null,
      h("p", {}, h("button", { type: "button", class: "nb-btn", text: "Write the message for your teacher", onclick: () => (show("lesson"), endPanel()) })),
    ),
  );
  views.code = h("div", { class: "xp-single", id: "view-code", role: "tabpanel", "aria-labelledby": "tab-code", hidden: true });
  app.replaceChildren(header(), views.lesson, views.film, views.code, views.notes);
  paintTakeaways();
  goStep(S.step, { focus: false });
  // Deep links from a course map: #film, #code, #notes open that view; #step-3 opens a step.
  const hash = location.hash.slice(1);
  if (["film", "code", "notes"].includes(hash) && views[hash]) show(hash);
  else if (/^step-\d+$/.test(hash)) goStep(Number(hash.slice(5)) - 1, { focus: false });
}

// ---------- video export: ?film-export renders one frame at a time ----------
// window.__filmExport.frame(i, u) shows scene i at progress u (0..1): params
// ease from the previous scene's over the first 30% and the coach's marks draw
// in over the first 45%. scripts/narrate.py voices the scenes and sets the timing.
function exportMode() {
  // A video can't be dragged, so the narration drops the "drag this" lines,
  // asks each check question, pauses, and then answers it. The explain-back
  // step becomes a recap in the teacher's words.
  const plain = plainText;
  const noDrag = (t) => t.split(/(?<=[.!?])\s+/).filter((x) => !/^(Drag|Move|Slide|Push|Switch|Set|Try|Build one|Change it|Play with)\b/.test(x)).join(" ");
  const scenes = L.film || L.steps.flatMap((st) => {
    const base = { chapter: st.title, set: st.set || {} };
    const out = [];
    const said = st.filmSay || noDrag(plain(st.say));
    if (said) out.push({ ...base, say: said });
    const ask = st.ask;
    if (ask && ask.kind === "explain") out.push({ ...base, say: `In one breath: ${plain(ask.model)}` });
    else if (ask && PRACTICE) {
      const q = plainText(ask.q);
      out.push({ ...base, say: `Quick check: ${q}${/[.?!…]$/.test(q) ? "" : "."} Think about it for a second.` });
      if (ask.why) out.push({ ...base, say: plain(ask.why) });
    } else if (ask?.why && !said.includes(plain(ask.why))) out.push({ ...base, say: plain(ask.why) });
    return out.length ? out : [{ ...base, say: st.title }];
  }).flatMap((sc) => {
    // Keep each caption to about two lines: split long narration at sentence ends.
    const parts = sc.say.split(/(?<=[.!?])\s+/);
    const chunks = [];
    for (const p of parts) {
      const last = chunks[chunks.length - 1];
      if (last && (last + " " + p).length <= 165) chunks[chunks.length - 1] = `${last} ${p}`;
      else chunks.push(p);
    }
    return chunks.map((say) => ({ ...sc, say }));
  });
  const full = [];
  scenes.reduce((acc, sc) => (full.push({ ...acc, ...(sc.set || {}) }), { ...acc, ...(sc.set || {}) }), { ...defaults });
  document.documentElement.toggleAttribute("data-film-export", true);
  const ef = makeFigure();
  ef.setNarrow(false);
  const chapter = h("p", { class: "nb-label xp-ex-chapter" });
  const caption = h("p", { class: "xp-ex-caption" });
  const titleEl = h("p", { class: "xp-ex-title", text: L.title });
  app.replaceChildren(h("div", { class: "xp-ex-stage" }, h("div", { class: "xp-ex-top" }, titleEl, chapter), h("div", { class: "xp-ex-fig" }, ef.svg), caption));
  const ease = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
  window.__filmExport = {
    title: L.title,
    scenes: scenes.map((sc) => ({ chapter: sc.chapter, say: sc.say })),
    sceneStates: full.map((params) => ({ ...params })),
    frame(i, u, cu = 1, settled = Math.min(1, u / 0.3)) {
      const from = full[Math.max(0, i - 1)];
      const to = full[i];
      const e = i === 0 ? 1 : ease(Math.max(0, Math.min(1, settled)));
      const params = {};
      for (const k of Object.keys(to)) params[k] = typeof to[k] === "number" && typeof from[k] === "number" ? snap(k, from[k] + (to[k] - from[k]) * e) : to[k];
      // Count this scene's marks, then draw them one after another over the first 45%.
      let count = 0;
      ef.render({ params, progress: () => (count += 1, 1) });
      const w = Math.min(1, u / 0.45) * Math.max(1, count);
      ef.render({ params, progress: (j) => Math.max(0, Math.min(1, w - j)) });
      chapter.textContent = scenes[i].chapter;
      caption.textContent = scenes[i].say;
      caption.hidden = cu <= 0;
      // The caption is written as it's spoken, and the camera drifts in a little,
      // so the picture never sits still while the voice talks.
      const lineH = parseFloat(getComputedStyle(caption).lineHeight) || 35;
      const lines = Math.max(1, Math.round(caption.scrollHeight / lineH));
      const shown = Math.min(lines, Math.ceil(Math.max(0.01, cu) * lines));
      caption.style.clipPath = shown >= lines ? "" : `inset(0 0 ${((lines - shown) * lineH).toFixed(1)}px 0)`;
      ef.svg.style.transform = `scale(${(1 + 0.03 * u).toFixed(4)})`;
      const marks = [...ef.svg.querySelectorAll("g[class^='tone-']")].map((g) => {
        const p = g.querySelector("path");
        let len = 100;
        let angle = 0;
        try {
          len = p.getTotalLength();
          const a = p.getPointAtLength(0);
          const b = p.getPointAtLength(len);
          angle = Math.atan2(b.y - a.y, b.x - a.x);
        } catch {
          /* no geometry */
        }
        return { tone: g.getAttribute("class"), len, angle };
      });
      return { marks, params: { ...params }, captionVisible: cu > 0 };
    },
  };
}

if (new URLSearchParams(location.search).has("film-export")) exportMode();
else boot();

// For tests and for the teacher agent's QA pass.
window.__explorable = {
  get state() {
    return { step: S.step, done: [...S.done], params: { ...S.params }, attempts: S.attempts, tried: S.tried };
  },
  goStep,
  paramsAt: (index) => ({ ...paramsAt(index) }),
  setParams(params) {
    for (const [key, value] of Object.entries(params || {})) {
      const spec = L.params?.[key];
      if (spec && Number.isFinite(Number(value))) S.params[key] = snap(key, Math.max(spec.min, Math.min(spec.max, Number(value))));
    }
    update();
    paintControls(L.steps[S.step]);
    return { ...S.params };
  },
  show,
  report: () => report("(not chosen yet)", ""),
  check: () => (L.checks || []).map((c) => ({ name: c.name, ok: Boolean(c.test(L.model)) })),
};

// A local interactive-video parent can pause at a narrated state and let the
// learner manipulate the same model. No persistence is enabled by this message.
window.addEventListener("message", (event) => {
  if (event.source !== window.parent || event.data?.type !== "teach:set-params") return;
  window.__explorable.show("lesson");
  if (Number.isInteger(event.data.step)) window.__explorable.goStep(event.data.step, { focus: false });
  window.__explorable.setParams(event.data.params);
});
