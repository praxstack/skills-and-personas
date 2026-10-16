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

const INK = { seedFrom, rng, smoothPath, line, polyline, loop, arrow, arrowHead, curvedArrow, cross, tick, underline, swipe, ring, bracket };
const L = window.LESSON;
const KEY = `explorable:${L.id || L.title}`;

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
const load = () => {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || {};
  } catch {
    return {};
  }
};
const save = (data) => {
  try {
    localStorage.setItem(KEY, JSON.stringify(data));
  } catch {
    /* storage blocked: the lesson still works, it just won't remember */
  }
};
const fmt = (spec, v) => (spec.fmt ? spec.fmt(v) : `${+v.toFixed(spec.decimals ?? (spec.step < 1 ? 2 : 0))}${spec.unit ? ` ${spec.unit}` : ""}`);

// ---------- state ----------
const defaults = Object.fromEntries(Object.entries(L.params || {}).map(([k, s]) => [k, s.value]));
const stored = load();
const S = {
  params: { ...defaults },
  step: Math.min(stored.step ?? 0, L.steps.length - 1),
  done: new Set(stored.done || []),
  attempts: stored.attempts || {}, // step -> [{answer, right}]
  tried: stored.tried || {}, // step -> [alt labels]
  altIndex: {},
  view: "lesson",
};
const persist = () =>
  save({ step: S.step, done: [...S.done], attempts: S.attempts, tried: S.tried, notes: notesBox?.value, board: document.documentElement.dataset.board });

// ---------- figure ----------
// Narrow figures get their own layout when the lesson asks for one:
// figure.viewBox may be a function of `narrow`, and draw() receives kit.narrow
// to rearrange panels. "Narrow" is the figure's own width, not the window's,
// so a tablet column counts too.
const NARROW_PX = 600;
function makeKit(parent, pen, narrow) {
  // Narrow figures can ask for bigger text (figure.narrowText, e.g. 1.5) so labels stay readable.
  const scale = narrow ? L.figure.narrowText ?? 1 : 1;
  return {
    ink: INK,
    pen,
    narrow,
    textScale: scale,
    layer: parent,
    el: (tag, attrs = {}) => svgEl(tag, tag === "text" ? { ...attrs, "font-size": scaledSize(attrs, scale) } : attrs, parent),
    mark: (paths, opts = {}) => inkMark(parent, paths, { pen, ...opts }),
    hand: (x, y, text, opts = {}) => handText(parent, x, y, text, { pen, ...opts, size: scaledSize({ class: "t-hand", "font-size": opts.size }, scale) }),
    seed: (name) => seedFrom(`${L.id}:${name}`),
    group: (transform) => makeKit(svgEl("g", { transform: transform || null }, parent), pen, narrow),
  };
}
function makeFigure() {
  const svg = svgEl("svg", { role: "img", class: "ink-svg" });
  const title = svgEl("title", {}, svg);
  const layer = svgEl("g", {}, svg);
  let last = S.params;
  let narrow = window.innerWidth < NARROW_PX + 40;
  function render({ pen = false, params = S.params } = {}) {
    last = params;
    const vb = L.figure.viewBox;
    svg.setAttribute("viewBox", (typeof vb === "function" ? vb(narrow) : vb) || "0 0 640 380");
    const s = L.model(params);
    layer.replaceChildren();
    L.figure.draw(layer, s, params, makeKit(layer, pen, narrow));
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
  return { svg, render };
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

function header() {
  const boardBtn = h("button", {
    type: "button",
    class: "nb-btn nb-btn-quiet",
    "aria-pressed": String(document.documentElement.dataset.board === "chalk"),
    text: "Chalkboard",
    onclick: (e) => {
      const chalk = document.documentElement.dataset.board !== "chalk";
      if (chalk) document.documentElement.dataset.board = "chalk";
      else delete document.documentElement.dataset.board;
      e.currentTarget.setAttribute("aria-pressed", String(chalk));
      persist();
    },
  });
  const tabs = h(
    "div",
    { class: "xp-tabs", role: "tablist", "aria-label": "Views" },
    ["lesson", "film", "notes"].map((v) =>
      h("button", {
        type: "button",
        role: "tab",
        class: "xp-tab",
        id: `tab-${v}`,
        "aria-selected": String(S.view === v),
        "aria-controls": `view-${v}`,
        text: { lesson: "Lesson", film: "Film", notes: "Notes and report" }[v],
        onclick: () => show(v),
      }),
    ),
  );
  return h(
    "header",
    { class: "xp-head" },
    h("div", { class: "xp-head-text" }, h("p", { class: "nb-label", text: [L.subject, L.level].filter(Boolean).join(" · ") || "Lesson" }), h("h1", { text: L.title }), L.subtitle ? h("p", { class: "xp-sub", text: L.subtitle }) : null),
    h("div", { class: "xp-head-tools" }, tabs, boardBtn),
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
  );
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

function update({ pen = false } = {}) {
  const s = fig.render({ pen });
  const rows = L.readouts ? L.readouts(s, S.params) : [];
  readouts.replaceChildren(...rows.map(([k, v]) => h("span", { class: "xp-readout" }, h("span", { class: "nb-label", text: k }), ` ${v}`)));
  return s;
}

// ---------- steps ----------
function answerOf(ask) {
  const s = L.model(S.params);
  return typeof ask.answer === "function" ? ask.answer(S.params, s) : ask.answer;
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
        ask.options.map((opt, k) =>
          h("button", {
            type: "button",
            class: "xp-option",
            "aria-pressed": "false",
            text: opt,
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
    feedback.replaceChildren(
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
    feedback.replaceChildren(h("p", { class: "nb-hand is-red", "data-write": "", text: ask.hint || "Not yet. Move the slider and watch what changes, then try again." }));
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
  if (!alts.length) return slot;
  const btn = h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "Still confused? Try another way" });
  btn.addEventListener("click", () => {
    const k = (S.altIndex[i] = ((S.altIndex[i] ?? -1) + 1) % alts.length);
    const alt = alts[k];
    (S.tried[i] ||= []).includes(alt.label) || S.tried[i].push(alt.label);
    persist();
    if (alt.set) Object.assign(S.params, alt.set), paintControls(step);
    update({ pen: true });
    drawIn(stage);
    slot.replaceChildren(h("div", { class: "xp-alt nb-printout" }, h("p", { class: "nb-label", text: alt.label }), h("p", { html: alt.say })));
    btn.textContent = k + 1 < alts.length ? "Still not it? Another way" : "Back to the first other way";
  });
  return h("div", { class: "xp-confused" }, btn, slot);
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

function goStep(i, { focus = true } = {}) {
  S.step = Math.max(0, Math.min(L.steps.length - 1, i));
  const step = L.steps[S.step];
  if (step.set) Object.assign(S.params, step.set);
  persist();
  paintOutline();
  paintControls(step);
  const last = S.step === L.steps.length - 1;
  const next = h("button", {
    type: "button",
    class: "nb-btn nb-btn-primary xp-next",
    text: last ? "Where to next?" : "Next",
    disabled: step.ask && !S.done.has(S.step) ? true : null,
    onclick: () => (last ? endPanel() : goStep(S.step + 1)),
  });
  const prev = h("button", { type: "button", class: "nb-btn", text: "Back", disabled: S.step === 0 ? true : null, onclick: () => goStep(S.step - 1) });
  stage = h("figure", { class: "xp-figure nb-sheet" }, fig.svg, readouts);
  stepBox.replaceChildren(
    h("p", { class: "nb-label", text: `Step ${S.step + 1} of ${L.steps.length}` }),
    h("h2", { tabindex: "-1", text: step.title }),
    h("div", { class: "xp-say", html: step.say }),
    stage,
    controls,
    step.lookFor ? h("p", { class: "xp-lookfor" }, h("span", { class: "nb-label", text: "Look for" }), h("span", { class: "nb-hand", text: step.lookFor })) : null,
    step.ask ? askBox(step, S.step) : null,
    confusedBox(step, S.step),
    h("div", { class: "xp-row xp-nav" }, prev, next),
  );
  if (!step.ask) finishStep(S.step);
  update({ pen: true });
  drawIn(stage);
  if (focus) stepBox.querySelector("h2").focus({ preventScroll: false });
}

// ---------- the end: keep going until the learner is satisfied ----------
function report(choice, text) {
  const lines = [`Lesson: ${L.title}${L.id ? ` (${L.id})` : ""}`, `Steps done: ${S.done.size}/${L.steps.length}`];
  L.steps.forEach((st, i) => {
    const a = S.attempts[i];
    const t = S.tried[i];
    if (!a && !t) return;
    const misses = (a || []).filter((x) => !x.right).length;
    const parts = [];
    if (a) parts.push(misses ? `${misses} miss${misses > 1 ? "es" : ""}${a.some((x) => x.asked) ? ", asked to be shown" : ""}` : "right first time");
    if (t?.length) parts.push(`tried other explanations: ${t.join("; ")}`);
    lines.push(`- ${st.title}: ${parts.join(", ")}`);
  });
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
  stepBox.replaceChildren(
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
  const scenes = L.film || L.steps.map((st) => ({ chapter: st.title, say: st.filmSay || st.say.replace(/<[^>]+>/g, ""), set: st.set || {} }));
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
  const canSpeak = "speechSynthesis" in window;
  const voice = h("input", { type: "checkbox", disabled: canSpeak ? null : true });
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
        for (const k of keys) params[k] = from[k] + (target[k] - from[k]) * e;
        ffig.render({ params });
        if (p < 1) requestAnimationFrame(frame);
        else resolve();
      };
      requestAnimationFrame(frame);
    });
  }
  function speak(text, my) {
    return new Promise((resolve) => {
      if (!voice.checked || !canSpeak) return resolve(sleep(readMs(text), my));
      const u = new SpeechSynthesisUtterance(text);
      u.rate = Number(speed.value);
      u.onend = u.onerror = () => resolve();
      speechSynthesis.cancel();
      speechSynthesis.speak(u);
      setTimeout(resolve, readMs(text) * 2.5);
    });
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
    if (canSpeak) speechSynthesis.cancel();
    index = Math.max(0, Math.min(scenes.length - 1, i));
    paint();
    const sc = scenes[index];
    const moving = tweenTo({ ...defaults, ...sc.set }, animate ? 900 / Number(speed.value) : 0, my);
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
      if (canSpeak) speechSynthesis.cancel();
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
    h("div", { class: "xp-film-bar" }, play, prev, next, scrub, counter, speed, h("label", { class: "xp-voice" }, voice, " Voice")),
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
  return { el: root, stop: () => ((playing = false), token++, canSpeak && speechSynthesis.cancel(), paint()) };
}

// ---------- views ----------
let film;
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
}

function boot() {
  if (stored.board === "chalk" || (L.board === "chalk" && stored.board === undefined)) document.documentElement.dataset.board = "chalk";
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
  app.replaceChildren(header(), views.lesson, views.film, views.notes);
  paintTakeaways();
  goStep(S.step, { focus: false });
}

boot();

// For tests and for the teacher agent's QA pass.
window.__explorable = {
  get state() {
    return { step: S.step, done: [...S.done], params: { ...S.params }, attempts: S.attempts, tried: S.tried };
  },
  goStep,
  show,
  report: () => report("(not chosen yet)", ""),
  check: () => (L.checks || []).map((c) => ({ name: c.name, ok: Boolean(c.test(L.model)) })),
};
