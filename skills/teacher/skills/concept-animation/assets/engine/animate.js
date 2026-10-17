// Concept animation: a scrubbable, captioned timeline over one model.
// window.ANIMATION = { title, viewBox, params, model, draw, keys: [{ at, set, say }] }
// Between keys, numeric params are eased from one key's values to the next,
// and draw(g, state, params, kit) runs every frame. kit.t is the time,
// kit.key the current key index and kit.u the progress through it (0..1),
// so a mark can be drawn part-way with kit.mark(paths, { progress: kit.u }).
// Everything is a pure function of time, which is what makes seek() exact
// and video export frame-perfect.

import { seedFrom, rng, smoothPath, line, polyline, loop, arrow, arrowHead, curvedArrow, cross, tick, underline, swipe, ring, bracket } from "../../../lesson-notebook/assets/ink.js";
import { svgEl, inkMark, handText, reducedMotion, scaledSize } from "../../../lesson-notebook/assets/pen.js";
import { scratch, strokeShape, soundButton, hush } from "../../../lesson-notebook/assets/sound.js";
import { boardButton, restoreBoard } from "../../../lesson-notebook/assets/board.js";

// Marks that started drawing during playback, so each one scratches once.
// Every mark's drawing is also logged (time, progress, shape), which is what
// scripts/export.mjs turns into the chalk or pencil track of a video.
const sounding = new Set();
const strokeLog = [];

const INK = { seedFrom, rng, smoothPath, line, polyline, loop, arrow, arrowHead, curvedArrow, cross, tick, underline, swipe, ring, bracket };
const A = window.ANIMATION;
const keys = A.keys.slice().sort((a, b) => a.at - b.at);
const duration = A.duration ?? keys.at(-1).at + 2;
const base = Object.fromEntries(Object.entries(A.params || {}).map(([k, v]) => [k, typeof v === "object" ? v.value : v]));
// Each key's full parameter set: earlier keys' values carry forward.
const full = [];
keys.reduce((acc, k) => (full.push({ ...acc, ...k.set }), { ...acc, ...k.set }), base);
const ease = (u) => (u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2);
const TRANSITION = A.transition ?? 1.2; // seconds each key takes to ease in

function frameAt(t) {
  let k = 0;
  while (k + 1 < keys.length && keys[k + 1].at <= t) k += 1;
  const start = keys[k].at;
  const u = Math.max(0, Math.min(1, (t - start) / TRANSITION));
  const from = full[Math.max(0, k - 1)];
  const to = full[k];
  const e = k === 0 ? 1 : ease(u);
  const params = {};
  for (const name of Object.keys(to)) {
    const a = from[name];
    const b = to[name];
    params[name] = typeof a === "number" && typeof b === "number" ? a + (b - a) * e : b;
  }
  return { k, u: k === 0 ? Math.min(1, t / TRANSITION) : u, params };
}

function h(tag, attrs = {}, ...kids) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") el.textContent = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) if (kid) el.append(kid);
  return el;
}

// Narrow stages (phones) can get their own layout: viewBox may be a function of
// `narrow`, draw() reads kit.narrow, and text grows by A.narrowText (default 1.6).
const NARROW_PX = 600;
let narrow = !new URLSearchParams(location.search).has("export") && window.innerWidth < NARROW_PX + 40;
const viewBoxFor = () => (typeof A.viewBox === "function" ? A.viewBox(narrow) : A.viewBox) || "0 0 960 540";
const svg = svgEl("svg", { viewBox: viewBoxFor(), role: "img", class: "ink-svg ca-svg" });
const title = svgEl("title", {}, svg);
const layer = svgEl("g", {}, svg);
const caption = h("p", { class: "ca-caption nb-hand", "aria-live": "polite" });
const clock = h("span", { class: "nb-print ca-clock" });
const playBtn = h("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Play" });
const scrub = h("input", { type: "range", min: 0, max: duration, step: 0.01, value: 0, "aria-label": "Time" });
const speed = h("select", { class: "nb-field", "aria-label": "Speed" }, [0.5, 0.75, 1, 1.5].map((v) => h("option", { value: v, text: `${v}×`, selected: v === 1 })));
const chapters = h("ol", { class: "ca-chapters" }, keys.map((k, i) => (k.say ? h("li", {}, h("button", { type: "button", class: "ca-chip", "data-i": i, text: `${i + 1}`, "aria-label": `Jump to: ${k.say}`, onclick: () => seek(k.at, true) })) : null)));
const transcript = h("details", { class: "ca-transcript" }, h("summary", { text: "Transcript" }), h("ol", {}, keys.filter((k) => k.say).map((k) => h("li", { text: `${k.at.toFixed(1)}s  ${k.say}` }))));

let t = 0;
let playing = false;
let last = 0;
const mm = (s) => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, "0")}`;

function render(time) {
  const { k, u, params } = frameAt(time);
  const s = A.model ? A.model(params) : params;
  layer.replaceChildren();
  svg.setAttribute("viewBox", viewBoxFor());
  const scale = narrow ? A.narrowText ?? 1.6 : 1;
  const kit = {
    ink: INK, t: time, key: k, u, layer, narrow, textScale: scale,
    el: (tag, attrs = {}) => svgEl(tag, tag === "text" ? { ...attrs, "font-size": scaledSize(attrs, scale) } : attrs, layer),
    mark: (paths, opts = {}) => {
      const g = inkMark(layer, paths, { pen: false, ...opts });
      const p = opts.progress;
      if (p !== undefined && p > 0 && p < 1) {
        const key = paths.join("|").slice(0, 120);
        const first = g.querySelector("path");
        if (logging) strokeLog.push({ t: time, key, p, shape: first ? strokeShape(first) : null, tone: opts.tone || "blue" });
        if (playing && !sounding.has(key) && first) {
          sounding.add(key);
          scratch(0, Math.max(120, (1 - p) * TRANSITION * 1000) / Number(speed.value), strokeShape(first));
        }
      }
      return g;
    },
    hand: (x, y, text, opts = {}) => handText(layer, x, y, text, { pen: false, ...opts, size: scaledSize({ class: "t-hand", "font-size": opts.size }, scale) }),
    seed: (name) => seedFrom(`${A.id || A.title}:${name}`),
    since: (i) => (k > i ? 1 : k === i ? u : 0), // how far key i's change has played
  };
  A.draw(layer, s, params, kit);
  const sayKey = keys.slice(0, k + 1).findLast((x) => x.say);
  caption.textContent = sayKey?.say || "";
  title.textContent = A.label ? A.label(s, params, k) : `${A.title}: ${caption.textContent}`;
  clock.textContent = `${mm(time)} / ${mm(duration)}`;
  scrub.value = String(time);
  chapters.querySelectorAll(".ca-chip").forEach((b) => b.classList.toggle("is-current", Number(b.dataset.i) === keys.indexOf(sayKey)));
}

let logging = false;
function seek(time, keepPlaying = false) {
  const next = Math.max(0, Math.min(duration, time));
  if (next < t || !keepPlaying) {
    sounding.clear();
    hush();
  }
  t = next;
  if (!keepPlaying) setPlaying(false);
  render(t);
}

function setPlaying(on) {
  playing = on;
  playBtn.textContent = on ? "Pause" : t >= duration ? "Replay" : "Play";
  playBtn.setAttribute("aria-pressed", String(on));
  if (on) {
    if (t >= duration) t = 0;
    last = performance.now();
    requestAnimationFrame(tickFrame);
  }
}

function tickFrame(now) {
  if (!playing) return;
  t += ((now - last) / 1000) * Number(speed.value);
  last = now;
  if (t >= duration) {
    t = duration;
    render(t);
    return setPlaying(false);
  }
  render(t);
  requestAnimationFrame(tickFrame);
}

playBtn.addEventListener("click", () => {
  if (reducedMotion() && !playing) {
    // Reduced motion: step from key to key instead of tweening.
    const next = keys.find((k) => k.at > t + 0.01);
    return seek(next ? next.at + TRANSITION : 0);
  }
  setPlaying(!playing);
});
scrub.addEventListener("input", () => seek(Number(scrub.value)));

const root = h(
  "section",
  { class: "ca-player", tabindex: "0", "aria-label": `${A.title}. Space plays or pauses, arrow keys jump between steps.` },
  h("figure", { class: "ca-stage nb-sheet" }, svg),
  caption,
  h("div", { class: "ca-bar" }, playBtn, scrub, clock, speed, boardButton(), soundButton()),
  chapters,
  transcript,
);
root.addEventListener("keydown", (e) => {
  if (["INPUT", "SELECT", "BUTTON", "SUMMARY"].includes(e.target.tagName)) return;
  if (e.key === " ") e.preventDefault(), playBtn.click();
  if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
    e.preventDefault();
    const list = keys.map((k) => k.at);
    const target = e.key === "ArrowRight" ? list.find((a) => a > t + 0.05) ?? duration : [...list].reverse().find((a) => a < t - 0.05) ?? 0;
    seek(target + (e.key === "ArrowRight" ? TRANSITION : 0));
  }
});

if ("ResizeObserver" in window && !new URLSearchParams(location.search).has("export")) {
  new ResizeObserver(([entry]) => {
    const w = entry.contentRect.width;
    if (!w || w < NARROW_PX === narrow) return;
    narrow = w < NARROW_PX;
    render(t);
  }).observe(svg);
}

const app = document.getElementById("app");
app.replaceChildren(
  h("header", { class: "ca-head" }, A.kicker ? h("p", { class: "nb-label", text: A.kicker }) : null, h("h1", { text: A.title }), A.subtitle ? h("p", { class: "ca-sub", text: A.subtitle }) : null),
  root,
);
document.documentElement.toggleAttribute("data-export", new URLSearchParams(location.search).has("export"));
restoreBoard(A.board || "auto");
seek(reducedMotion() ? Math.min(duration, keys[0].at + TRANSITION) : 0);

// Used by scripts/export.mjs and by tests.
window.__anim = {
  duration,
  keys: keys.map(({ at, say }) => ({ at, say: say || "" })),
  seek: (time) => seek(time),
  frameAt,
  render,
  // For export: record every partly drawn mark while seeking frame by frame.
  startStrokeLog: () => ((logging = true), (strokeLog.length = 0)),
  strokeLog: () => strokeLog.slice(),
};
