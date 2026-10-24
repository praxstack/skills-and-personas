// Course page: the map of a whole subject, an outline, separate notes, and a
// quick quiz, over lessons built by explorable / concept-animation.
// window.COURSE comes from scripts/build_course.py (extract.mjs output plus
// the built file of each lesson and any narrated video).
//
// Patterns borrowed (see teacher/references/DESIGN-INSPIRATION.md): roadmap.sh's
// node drawer with Learning / Done / Skip and "Quick explain / Teach me / Quiz
// me"; Educative's separate outline, lesson and notes; Brilliant's try, then
// see why. The learner can ask for the same idea in any medium, as often as
// they like.

import { arrow, curvedArrow, loop, seedFrom, rng } from "../../../lesson-notebook/assets/ink.js";
import { drawIn, svgEl, inkMark } from "../../../lesson-notebook/assets/pen.js";
import { soundButton } from "../../../lesson-notebook/assets/sound.js";
import { boardButton, restoreBoard } from "../../../lesson-notebook/assets/board.js";

const C = window.COURSE;
// "Quiz me" has no figure to look at, so questions that need one stay in the lesson.
for (const l of C.lessons) l.quiz = (l.quiz || []).filter((q) => !q.needsFigure);
const STORE = `course:${C.id}`;
const CONSENT_STORE = `${STORE}:consent`;
let rememberProgress = false;
try { rememberProgress = localStorage.getItem(CONSENT_STORE) === "yes"; } catch { /* ephemeral */ }
const STATUS = ["learning", "done", "skip"];
const STATUS_LABEL = { learning: "Learning", done: "Done", skip: "Skip" };

function el(tag, attrs = {}, ...kids) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") e.textContent = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : String(v));
  }
  for (const kid of kids.flat()) if (kid !== null && kid !== undefined && kid !== false) e.append(kid);
  return e;
}
const readStore = () => {
  if (!rememberProgress) return { status: {} };
  try {
    // Stored progress may come from an older build or a bad write: keep it
    // only if status is a plain object.
    const saved = JSON.parse(localStorage.getItem(STORE));
    const ok = saved && typeof saved === "object" && !Array.isArray(saved) && saved.status && typeof saved.status === "object" && !Array.isArray(saved.status);
    return ok ? saved : { status: {} };
  } catch {
    return { status: {} };
  }
};
const state = readStore();
const persist = () => {
  if (!rememberProgress) return;
  try {
    localStorage.setItem(STORE, JSON.stringify(state));
  } catch {
    /* storage blocked: the page still works */
  }
};

// ---------- order and layout ----------
const byId = Object.assign(Object.create(null), Object.fromEntries(C.lessons.map((l) => [l.id, l])));
const layer = Object.create(null);
const depthOf = (id, seen = new Set()) => {
  if (layer[id] !== undefined) return layer[id];
  if (seen.has(id)) return 0;
  seen.add(id);
  const needs = (byId[id].needs || []).filter((n) => byId[n]);
  layer[id] = needs.length ? 1 + Math.max(...needs.map((n) => depthOf(n, seen))) : 0;
  return layer[id];
};
C.lessons.forEach((l) => depthOf(l.id));
const layers = [];
C.lessons.forEach((l) => (layers[layer[l.id]] ||= []).push(l));
const ordered = layers.flat();

// ---------- header ----------
const doneCount = () => C.lessons.filter((l) => state.status[l.id] === "done").length;
const progressBar = el("div", { class: "cs-progress", role: "progressbar", "aria-valuemin": "0", "aria-valuemax": String(C.lessons.length) }, el("span"));
const progressText = el("span", { class: "nb-print" });
function paintProgress() {
  const n = doneCount();
  progressBar.setAttribute("aria-valuenow", String(n));
  progressBar.firstChild.style.width = `${(100 * n) / C.lessons.length}%`;
  progressText.textContent = `${n} of ${C.lessons.length} done`;
}

const views = {};
function show(v) {
  document.querySelectorAll(".cs-tab").forEach((t) => t.setAttribute("aria-selected", String(t.dataset.v === v)));
  for (const [k, node] of Object.entries(views)) node.hidden = k !== v;
  if (v === "map") requestAnimationFrame(() => drawIn(mapSvg));
}

function progressConsent() {
  const input = el("input", { type: "checkbox", id: "cs-remember", checked: rememberProgress ? true : null, style: "width:24px;height:24px;vertical-align:middle" });
  input.addEventListener("change", () => {
    rememberProgress = input.checked;
    try {
      if (rememberProgress) { localStorage.setItem(CONSENT_STORE, "yes"); persist(); }
      else { localStorage.removeItem(STORE); localStorage.removeItem(CONSENT_STORE); }
    } catch { rememberProgress = false; input.checked = false; }
  });
  return el("label", { for: "cs-remember", style: "display:flex;align-items:center;gap:.5rem;min-height:44px;font-size:.9rem" }, input, "Remember progress on this device");
}

const header = el(
  "header",
  { class: "cs-head" },
  el("p", { class: "nb-label", text: C.level || "Course" }),
  el("h1", { text: C.title }),
  C.subtitle ? el("p", { class: "cs-sub", text: C.subtitle }) : null,
  (C.prereqs || []).length
    ? el("p", { class: "cs-sub" }, "Builds on: ", ...C.prereqs.map((p, i) => [i ? ", " : "", el("a", { href: C.root ? `${C.root}${p}` : `../${p}/index.html`, text: C.prereqTitles?.[p] || p })]))
    : null,
  el("div", { class: "cs-head-row" }, progressBar, progressText),
  progressConsent(),
  el(
    "div",
    { class: "cs-head-row" },
    el(
      "div",
      { class: "cs-tabs", role: "tablist", "aria-label": "Views" },
      [["map", "Map"], ["outline", "Outline"], ["notes", "Notes"]].map(([v, t]) =>
        el("button", { type: "button", role: "tab", class: "cs-tab", "data-v": v, id: `tab-${v}`, "aria-selected": String(v === "map"), text: t, onclick: () => show(v) }),
      ),
    ),
    boardButton(),
    soundButton(),
  ),
);

// ---------- the map ----------
// Node size and text grow on the phone's top-to-bottom map, which is drawn smaller.
const baseSize = () => (narrow() ? { w: 226, h: 88, title: 21, meta: 20, wrap: 17 } : { w: 210, h: 72, title: 17, meta: 14, wrap: 22 });
// Titles wrap to as many lines as they need (never cut off); every node grows to fit the longest.
function titleLines(title, wrap) {
  const lines = [];
  for (const w of title.split(" ")) {
    const last = lines[lines.length - 1];
    if (last && (last + " " + w).length <= wrap) lines[lines.length - 1] = `${last} ${w}`;
    else lines.push(w);
  }
  return lines;
}
const size = () => {
  const b = baseSize();
  const most = Math.max(2, ...C.lessons.map((l) => titleLines(l.title, b.wrap).length));
  return { ...b, h: b.h + (most - 2) * (b.title + 3), lines: most };
};
const narrow = () => window.innerWidth < 720;
// A group, not an image: role="img" would make the lesson buttons inside it
// presentational, so screen readers couldn't reach them.
const mapSvg = svgEl("svg", { class: "ink-svg cs-map-svg", role: "group", "aria-label": `Map of ${C.title}: ${ordered.length} lessons` });
const drawer = el("aside", { class: "cs-drawer nb-sheet", "aria-live": "polite" });
let selected = ordered[0]?.id;

// Text never shrinks below about 12.5px on screen: a map that won't fit across
// at that size is drawn top to bottom instead, and one that's still too wide
// scrolls sideways inside its box (the page itself never does).
const MIN_TEXT_PX = 12;
let lastAvail = 0;
function availableWidth() {
  const box = mapSvg.parentElement;
  const w = box ? box.clientWidth - 2 * 12 : 0;
  if (w > 0) lastAvail = w;
  return lastAvail || (narrow() ? window.innerWidth - 40 : Math.min(1200, window.innerWidth) - 22 * 16 - 100);
}

const LANE = 13;
const LANE_GAP = 12;
function nodePos(vertical = narrow()) {
  const pos = Object.create(null);
  const { w: NODE_W, h: NODE_H } = size();
  const gapMain = vertical ? NODE_H + 44 : 255;
  const gapCross = vertical ? NODE_W + (narrow() ? 12 : 60) : NODE_H + 32;
  layers.forEach((ls, li) =>
    ls.forEach((l, k) => {
      const cross = (k - (ls.length - 1) / 2) * gapCross;
      pos[l.id] = vertical ? { x: cross, y: li * gapMain } : { x: li * gapMain, y: cross };
    }),
  );
  const xs = Object.values(pos).map((p) => p.x);
  const ys = Object.values(pos).map((p) => p.y);
  // Arrows that skip a row run in their own lane down the side of the map.
  const lanes = { 1: 0, "-1": 0 };
  const skips = [];
  for (const l of ordered) {
    for (const n of (l.needs || []).filter((x) => byId[x] && layer[l.id] - layer[x] > 1)) {
      const a = pos[n];
      const b = pos[l.id];
      const side = (vertical ? a.x + b.x : a.y + b.y) >= 0 ? 1 : -1;
      skips.push({ from: n, to: l.id, side, lane: lanes[side]++ });
    }
  }
  const extra = (side) => (lanes[side] ? LANE_GAP + lanes[side] * LANE : 0);
  const pad = vertical ? { l: 14 + extra(-1), r: 14 + extra(1), t: 20, b: 20 } : { l: 20, r: 20, t: 20 + extra(-1), b: 20 + extra(1) };
  const minX = Math.min(...xs) - NODE_W / 2 - pad.l;
  const minY = Math.min(...ys) - NODE_H / 2 - pad.t;
  const w = Math.max(...xs) - Math.min(...xs) + NODE_W + pad.l + pad.r;
  const h = Math.max(...ys) - Math.min(...ys) + NODE_H + pad.t + pad.b;
  const edge = { x0: Math.min(...xs) - NODE_W / 2, x1: Math.max(...xs) + NODE_W / 2, y0: Math.min(...ys) - NODE_H / 2, y1: Math.max(...ys) + NODE_H / 2 };
  return { pos, box: [minX, minY, w, h], vertical, skips, edge };
}

function drawMap() {
  const { w: NODE_W, h: NODE_H, title: TITLE, meta: META, wrap: WRAP } = size();
  const avail = availableWidth();
  const minScale = MIN_TEXT_PX / Math.min(TITLE, META);
  let layout = nodePos();
  if (!layout.vertical && layout.box[2] * minScale > avail) layout = nodePos(true);
  const { pos, box, vertical, skips, edge } = layout;
  const scale = Math.max(minScale, Math.min(1.1, avail / box[2]));
  mapSvg.setAttribute("viewBox", box.join(" "));
  mapSvg.style.width = `${Math.round(box[2] * scale)}px`;
  mapSvg.style.height = `${Math.round(box[3] * scale)}px`;
  mapSvg.dataset.layout = vertical ? "down" : "across";
  // Redrawing replaces every node, so a focused node would drop focus to the
  // page; note which lesson had it and focus its new node afterwards.
  const focusedId = mapSvg.contains(document.activeElement) ? document.activeElement.closest(".cs-node")?.getAttribute("data-id") : null;
  mapSvg.replaceChildren();
  // Arrows from what a lesson needs to the lesson.
  for (const l of ordered) {
    for (const n of (l.needs || []).filter((x) => byId[x])) {
      const a = pos[n];
      const b = pos[l.id];
      const from = vertical ? [a.x, a.y + NODE_H / 2 + 4] : [a.x + NODE_W / 2 + 4, a.y];
      const to = vertical ? [b.x, b.y - NODE_H / 2 - 8] : [b.x - NODE_W / 2 - 8, b.y];
      const seed = seedFrom(`${n}>${l.id}`);
      const skip = skips.find((k) => k.from === n && k.to === l.id);
      if (skip) {
        // Out to its lane at the side, along, and back in: it can't be read as
        // pointing at a lesson in between.
        const { side, lane } = skip;
        const off = LANE_GAP + (lane + 1) * LANE - 4;
        const pts = vertical
          ? [[a.x + side * (NODE_W / 2 + 3), a.y], [side > 0 ? edge.x1 + off : edge.x0 - off, a.y], [side > 0 ? edge.x1 + off : edge.x0 - off, b.y], [b.x + side * (NODE_W / 2 + 4), b.y]]
          : [[a.x, a.y + side * (NODE_H / 2 + 3)], [a.x, side > 0 ? edge.y1 + off : edge.y0 - off], [b.x, side > 0 ? edge.y1 + off : edge.y0 - off], [b.x, b.y + side * (NODE_H / 2 + 4)]];
        inkMark(mapSvg, arrow(pts, { seed, head: 9 }), { tone: "graphite" });
        continue;
      }
      const mid = vertical ? [(from[0] + to[0]) / 2 + 18, (from[1] + to[1]) / 2] : [(from[0] + to[0]) / 2, (from[1] + to[1]) / 2 - 18];
      inkMark(mapSvg, curvedArrow(from, mid, to, { seed, head: 9 }), { tone: "graphite" });
    }
  }
  for (const l of ordered) {
    const p = pos[l.id];
    const st = state.status[l.id];
    const g = svgEl("g", { class: `cs-node${l.id === selected ? " is-selected" : ""}${st ? ` is-${st}` : ""}`, tabindex: "0", role: "button", "data-id": l.id, "aria-current": l.id === selected ? "true" : null, "aria-label": `${l.title}${st ? `, ${STATUS_LABEL[st]}` : ""}. Open` }, mapSvg);
    svgEl("rect", { x: p.x - NODE_W / 2, y: p.y - NODE_H / 2, width: NODE_W, height: NODE_H, rx: 4, class: st === "done" ? "f-green-soft s-ink" : l.id === selected ? "f-hl s-ink" : "f-paper s-ink", "stroke-dasharray": st === "skip" ? "6 5" : null }, g);
    const lines = titleLines(l.title, WRAP);
    const top = p.y - NODE_H / 2 + 8 + TITLE + ((size().lines - lines.length) * (TITLE + 3)) / 2;
    lines.forEach((t, i) => svgEl("text", { x: p.x, y: top + i * (TITLE + 3), class: "t-book", "text-anchor": "middle", "font-size": TITLE, text: t }, g));
    svgEl("text", { x: p.x - NODE_W / 2 + 8, y: p.y + NODE_H / 2 - 7, class: "t-print", "font-size": META, text: `${l.minutes || 10} min` }, g);
    if (st === "done") inkMark(g, [loop(p.x + NODE_W / 2 - 16, p.y - NODE_H / 2 + 14, 9, 9, { seed: seedFrom(`done${l.id}`) })], { tone: "green", pen: false });
    const open = () => select(l.id);
    g.addEventListener("click", open);
    g.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), open()));
    if (l.id === focusedId) g.focus({ preventScroll: true });
  }
}

// C.base is the course folder's URL path when built with --base (root-absolute
// links for hosts with clean URLs), and empty for relative links.
function lessonHref(l, hash = "") {
  return `${C.base || ""}${l.page}${hash ? `#${hash}` : ""}`;
}

function setStatus(id, s) {
  const fromDrawer = drawer.contains(document.activeElement);
  if (state.status[id] === s) delete state.status[id];
  else state.status[id] = s;
  persist();
  paintProgress();
  drawMap();
  paintOutline();
  select(id, { keepFocus: true });
  // select() rebuilds the drawer, so the pressed button is gone: focus its
  // replacement rather than letting focus fall to the page.
  if (fromDrawer) drawer.querySelectorAll(".cs-status .cs-chip")[STATUS.indexOf(s)]?.focus();
}

function select(id, { keepFocus = false } = {}) {
  selected = id;
  const l = byId[id];
  const st = state.status[id];
  const quizBox = el("div", { class: "cs-quiz" });
  const videoBox = el("div", { class: "cs-video" });
  drawer.replaceChildren(
    el("p", { class: "nb-label", text: `${l.minutes || 10} minutes${l.kind === "animation" ? " · animation" : ""}` }),
    el("h2", { tabindex: "-1", text: l.title }),
    el(
      "div",
      { class: "cs-status", role: "group", "aria-label": "Your status" },
      STATUS.map((s) => el("button", { type: "button", class: "cs-chip", "aria-pressed": String(st === s), text: STATUS_LABEL[s], onclick: () => setStatus(id, s) })),
    ),
    el("p", { class: "nb-label", text: "Quick explain" }),
    el("p", { class: "cs-summary", text: l.summary || l.subtitle }),
    l.hook ? el("details", { class: "cs-hook" }, el("summary", { text: "Why it mattered" }), el("p", { text: l.hook })) : null,
    el("p", { class: "nb-label", text: "Learn it as" }),
    el(
      "div",
      { class: "cs-actions" },
      el("a", { class: "nb-btn nb-btn-primary", href: lessonHref(l), text: "Teach me (interactive)" }),
      l.video ? el("button", { type: "button", class: "nb-btn", text: "Watch the narrated video", onclick: () => playVideo(l, videoBox) }) : null,
      el("a", { class: "nb-btn", href: lessonHref(l, "film"), text: l.kind === "animation" ? "Watch the animation" : "Watch it as a film" }),
      l.hasCode ? el("a", { class: "nb-btn", href: lessonHref(l, "code"), text: "Read and run the code" }) : null,
      l.quiz.length ? el("button", { type: "button", class: "nb-btn", text: `Quiz me (${l.quiz.length})`, onclick: () => quiz(l, quizBox) }) : null,
      el("a", { class: "nb-btn nb-btn-quiet", href: lessonHref(l, "notes"), text: "Notes" }),
    ),
    videoBox,
    quizBox,
    l.explain.length ? el("p", { class: "nb-hand cs-explain", text: `Can you say it back? ${l.explain[0]}` }) : null,
  );
  drawMap();
  drawIn(drawer);
  if (!keepFocus && narrow()) drawer.scrollIntoView({ block: "nearest", behavior: "smooth" });
}

// ---------- narrated video, played here with its captions ----------
function playVideo(l, box) {
  if (box.firstChild) {
    box.replaceChildren();
    return;
  }
  // l.video is the MP4 beside the page (local builds) or its Vercel Blob URL.
  // A cross-origin video plays without a crossorigin attribute; leaving it off
  // means the video needs no CORS headers, and the captions below are
  // same-origin (l.captions, built next to the page), which a track loads
  // either way.
  const video = el("video", { controls: "", preload: "metadata", playsinline: "", src: l.video, "aria-label": `Narrated video: ${l.title}` });
  if (l.captions) video.append(captionTrack(l.captions));
  const open = el("a", { class: "nb-print", href: l.video, text: "Open the video on its own" });
  box.replaceChildren(video, open);
  // A host can refuse a video (a paywall, a lapsed link): say so instead of
  // leaving an empty player, and let the link show the host's own page.
  video.addEventListener("error", () => {
    open.textContent = "The video didn't load here. Open it on its own to see why";
  });
  video.play().catch(() => {
    /* autoplay with sound needs a click; the controls are there */
  });
}

function captionTrack(vtt) {
  // The captions are already burned into the picture, so the track is off by
  // default (no doubled text); it's there for screen readers and the CC menu.
  const track = el("track", { kind: "captions", srclang: "en", label: "English", src: vtt });
  // Some hosts serve .vtt with the wrong type, which a track refuses (it only
  // loads once the viewer turns captions on). Then fetch the captions and hand
  // them over as a text/vtt blob instead, still showing.
  track.addEventListener(
    "error",
    () =>
      fetch(vtt)
        .then((r) => (r.ok ? r.text() : Promise.reject(r.status)))
        .then((text) => {
          track.src = URL.createObjectURL(new Blob([text], { type: "text/vtt" }));
          track.track.mode = "showing";
        })
        .catch(() => {}),
    { once: true },
  );
  return track;
}

// ---------- quiz: try first, then see why ----------
// Choice options in a fixed shuffled order per question, so the right answer
// isn't always in the same place. Options that are all numbers keep their
// order (a scale reads best sorted), and so does a question with keepOrder: true.
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

function quiz(l, box) {
  let k = 0;
  let right = 0;
  const next = () => {
    if (k >= l.quiz.length) {
      box.replaceChildren(
        el("p", { class: "nb-hand", text: `${right} of ${l.quiz.length} right. A score is a clue, not a finish line.` }),
        el("p", {}, right < l.quiz.length ? el("a", { href: lessonHref(l, `step-${l.quiz.find((x, i) => !x._right)?.step || 1}`), text: "Go back to the step you missed" }) : "Try saying the idea back in your own words."),
      );
      return;
    }
    const q = l.quiz[k];
    const fb = el("div", { class: "cs-fb", "aria-live": "polite" });
    let choice = null;
    let input = null;
    const opts = q.kind === "choice"
      ? el("div", { class: "cs-opts" }, optionOrder(q.options, `${l.id}:${q.step}`, q.keepOrder).map((i) => el("button", { type: "button", class: "cs-opt", "aria-pressed": "false", "data-k": String(i), text: q.options[i], onclick: (e) => ((choice = i), box.querySelectorAll(".cs-opt").forEach((b) => b.setAttribute("aria-pressed", String(b === e.currentTarget)))) })))
      : el("div", { class: "cs-opts" }, (input = el("input", { type: "number", step: "any", class: "nb-field", "aria-label": q.q })), q.unit ? el("span", { class: "nb-print", text: q.unit }) : null);
    const check = el("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Check" });
    check.addEventListener("click", () => {
      let ok;
      if (q.kind === "choice") {
        if (choice === null) return;
        ok = choice === q.answer;
      } else {
        if (input.value.trim() === "") return input.focus();
        ok = Math.abs(Number(input.value) - q.answer) <= (q.tol || 1e-9);
      }
      q._right = ok;
      if (ok) right += 1;
      const ans = q.kind === "choice" ? q.options[q.answer] : `${+Number(q.answer).toFixed(q.decimals)}${q.unit ? ` ${q.unit}` : ""}`;
      fb.replaceChildren(el("p", { class: `nb-hand${ok ? "" : " is-red"}`, text: ok ? "Yes." : `It's ${ans}.` }), el("p", { class: "cs-why", text: q.why }));
      check.replaceWith(el("button", { type: "button", class: "nb-btn", text: k + 1 < l.quiz.length ? "Next question" : "Finish", onclick: () => ((k += 1), next()) }));
    });
    box.replaceChildren(el("p", { class: "nb-label", text: `Question ${k + 1} of ${l.quiz.length}` }), el("p", { class: "cs-q", text: q.q }), opts, el("div", { class: "cs-row" }, check), fb);
  };
  next();
}

// ---------- outline and notes ----------
const outlineList = el("ol", { class: "cs-outline" });
function paintOutline() {
  outlineList.replaceChildren(
    ...ordered.map((l) => {
      const st = state.status[l.id];
      return el(
        "li",
        { class: st ? `is-${st}` : "" },
        el("div", { class: "cs-outline-head" }, el("a", { href: lessonHref(l), text: l.title }), el("span", { class: "nb-print", text: `${l.minutes || 10} min${st ? ` · ${STATUS_LABEL[st]}` : ""}` })),
        el("p", { class: "cs-sub", text: l.summary || l.subtitle }),
        (l.needs || []).length ? el("p", { class: "nb-print cs-needs", text: `needs: ${l.needs.map((n) => byId[n]?.title || n).join(", ")}` }) : null,
      );
    }),
  );
}
const notesView = el(
  "section",
  { class: "cs-notes" },
  el("p", { class: "cs-sub", text: "Every lesson's key ideas on one sheet, apart from the lessons, for review." }),
  ordered.map((l) =>
    el(
      "article",
      { class: "cs-note-card" },
      el("h2", {}, el("a", { href: lessonHref(l, "notes"), text: l.title })),
      el("ul", {}, l.notes.filter((n) => n.note).map((n) => el("li", {}, el("strong", { text: `${n.title}: ` }), el("span", { class: "nb-note", text: n.note })))),
      l.misconceptions.length ? [el("p", { class: "nb-label", text: "Common mix-ups" }), el("ul", {}, l.misconceptions.map((m) => el("li", { text: m })))] : null,
      l.deeper.length ? [el("p", { class: "nb-label", text: "Go deeper" }), el("ul", {}, l.deeper.map((m) => el("li", { text: m })))] : null,
    ),
  ),
);

// ---------- boot ----------
restoreBoard("auto");
views.map = el("div", { class: "cs-mapview", id: "view-map", role: "tabpanel", "aria-labelledby": "tab-map" }, el("figure", { class: "cs-map nb-sheet" }, mapSvg), drawer);
views.outline = el("div", { id: "view-outline", role: "tabpanel", "aria-labelledby": "tab-outline", hidden: true }, outlineList);
views.notes = el("div", { id: "view-notes", role: "tabpanel", "aria-labelledby": "tab-notes", hidden: true }, notesView);
document.getElementById("app").replaceChildren(header, views.map, views.outline, views.notes);
paintProgress();
paintOutline();
const first = ordered.find((l) => !state.status[l.id] || state.status[l.id] === "learning") || ordered[0];
if (first) select(first.id, { keepFocus: true });
drawIn(mapSvg);
let lastWidth = window.innerWidth;
window.addEventListener("resize", () => {
  if (Math.abs(window.innerWidth - lastWidth) > 24) {
    lastWidth = window.innerWidth;
    lastAvail = 0;
    drawMap();
  }
});
const hash = location.hash.slice(1);
if (["outline", "notes"].includes(hash)) show(hash);

window.__course = { state, select, show, setStatus, lessons: C.lessons.map((l) => l.id) };
