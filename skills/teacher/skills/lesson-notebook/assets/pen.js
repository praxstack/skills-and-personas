// The pen: everything that moves is the teacher drawing or writing.
// Adapted from the AskTheMove Timeline (praxstack/ChessLab, site/public/assets/app.js).
// Strokes are SVG paths with class "stroke" and pathLength="1", drawn by
// animating stroke-dashoffset from 1 to 0. Words are revealed left to right
// with clip-path. Under reduced motion everything is shown finished at once.
// Nothing loops, bounces or floats.

import { scratch, writing, strokeShape, hush } from "./sound.js";

const EASE_STROKE = "cubic-bezier(0.65, 0, 0.35, 1)";
const EASE_OUT = "cubic-bezier(0.23, 1, 0.32, 1)";
const EASE_WRITE = "cubic-bezier(0.4, 0, 0.6, 1)";
const CLIP_FROM = "inset(-0.3em 100% -0.45em 0)";
const CLIP_TO = "inset(-0.3em -0.3em -0.45em -0.3em)";
const CHAR_MS = 34;
const SVG_NS = "http://www.w3.org/2000/svg";

export function reducedMotion() {
  try {
    return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  } catch {
    return false;
  }
}

function screenLength(path) {
  try {
    const m = path.getScreenCTM();
    const scale = m ? Math.sqrt(Math.abs(m.a * m.d - m.b * m.c)) : 1;
    return path.getTotalLength() * scale;
  } catch {
    return 200;
  }
}

function strokeMs(path, speed) {
  const px = screenLength(path);
  const ms = px < 28 ? 140 : Math.min(1100, Math.max(260, px * 1.1));
  return Math.round(ms / speed);
}

/** Wrap each word of an element in span.w so it can be written. */
export function splitWords(el) {
  if (!el.hasAttribute("data-split")) {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    const texts = [];
    while (walker.nextNode()) texts.push(walker.currentNode);
    for (const node of texts) {
      if (!node.data.trim()) continue;
      const frag = document.createDocumentFragment();
      for (const part of node.data.split(/(\s+)/)) {
        if (!part) continue;
        if (/^\s+$/.test(part)) frag.append(part);
        else {
          const w = document.createElement("span");
          w.className = "w";
          w.textContent = part;
          frag.append(w);
        }
      }
      node.replaceWith(frag);
    }
    el.setAttribute("data-split", "");
  }
  return [...el.querySelectorAll(".w")];
}

export function unsplitWords(el) {
  for (const w of el.querySelectorAll(".w")) w.replaceWith(w.textContent);
  el.normalize();
  el.removeAttribute("data-split");
}

/** One passage of drawing and writing, laid out in time, then played. */
export class Timeline {
  constructor({ speed = 1, sound = true } = {}) {
    this.t = 0;
    this.speed = speed;
    this.anims = [];
    this.sound = sound;
  }
  wait(ms) {
    this.t += ms / this.speed;
  }
  lift() {
    this.t += Math.round(200 / this.speed);
  }
  stroke(path, { duration, easing = EASE_STROKE } = {}) {
    const d = duration || strokeMs(path, this.speed);
    this.anims.push(
      path.animate([{ strokeDashoffset: 1.01 }, { strokeDashoffset: 0 }], { duration: d, delay: this.t, easing, fill: "backwards" }),
    );
    if (this.sound) scratch(this.t, d, strokeShape(path), { gain: this.swiping ? 0.5 : 1 });
    this.t += d;
  }
  /** Every stroke of one mark, with a short pen lift between them. */
  mark(el) {
    const swipe = el.classList.contains("tone-highlight") || Boolean(el.closest?.(".tone-highlight"));
    this.swiping = swipe;
    const strokes = el.matches?.(".stroke") ? [el] : el.querySelectorAll(".stroke");
    strokes.forEach((path, i) => {
      if (i) this.wait(70);
      this.stroke(path, swipe ? { duration: 520, easing: EASE_OUT } : {});
    });
  }
  words(units, charMs = CHAR_MS / this.speed) {
    for (const unit of units) {
      const text = unit.textContent || "";
      const d = Math.max(80, Math.round(Math.max(2, text.length) * charMs));
      this.anims.push(
        unit.animate([{ clipPath: CLIP_FROM }, { clipPath: CLIP_TO }], { duration: d, delay: this.t, easing: EASE_WRITE, fill: "backwards" }),
      );
      this.t += d + Math.round(charMs * 0.8);
      if (/[.?!][’”)]?$/.test(text)) this.t += 90;
      else if (/[,;:]$/.test(text)) this.t += 45;
    }
  }
  /** A whole element written by hand; long notes go faster so none takes more than about 2.5s. */
  write(el) {
    if (el instanceof SVGElement) {
      // SVG text can't hold HTML spans, so the whole line is revealed left to right.
      const chars = (el.textContent || "").length;
      const d = Math.round(Math.min(2400, Math.max(200, chars * CHAR_MS)) / this.speed);
      this.anims.push(
        el.animate([{ clipPath: "inset(-20% 100% -20% 0)" }, { clipPath: "inset(-20% -2% -20% -2%)" }], {
          duration: d, delay: this.t, easing: EASE_WRITE, fill: "backwards",
        }),
      );
      if (this.sound) writing(this.t, d, (el.textContent || "").trim().split(/\s+/).length);
      this.t += d;
      return;
    }
    const units = splitWords(el);
    const start = this.t;
    const chars = units.reduce((n, u) => n + (u.textContent || "").length, 0);
    this.words(units, Math.min(CHAR_MS, 2400 / Math.max(chars, 1)) / this.speed);
    if (this.sound) writing(start, this.t - start, units.length);
  }
  done() {
    return Promise.all(this.anims.map((a) => a.finished.catch(() => {})));
  }
  finish() {
    hush();
    for (const a of this.anims) {
      try {
        a.finish();
      } catch {
        /* cancelled */
      }
    }
  }
  cancel() {
    hush();
    for (const a of this.anims) a.cancel();
  }
}

/**
 * Draw everything in `root` in document order: [data-pen] groups are drawn
 * stroke by stroke, [data-write] elements are handwritten. Returns a handle
 * with done() and finish(). An AbortSignal finishes the drawing instantly.
 */
export function drawIn(root, { speed = 1, signal } = {}) {
  const items = [...root.querySelectorAll("[data-pen], [data-write]")];
  const tl = new Timeline({ speed });
  if (reducedMotion() || !items.length) return { done: () => Promise.resolve(), finish() {}, timeline: tl };
  items.forEach((el, i) => {
    if (i) tl.lift();
    if (el.hasAttribute("data-write")) tl.write(el);
    else tl.mark(el);
  });
  signal?.addEventListener("abort", () => tl.finish());
  const done = tl.done().then(() =>
    items.filter((el) => el.hasAttribute("data-write") && !(el instanceof SVGElement)).forEach(unsplitWords),
  );
  return { done: () => done, finish: () => tl.finish(), timeline: tl };
}

/** Font size for SVG text at a scale: explicit size, else the class default. */
export function scaledSize(attrs, scale) {
  if (scale === 1 && attrs["font-size"] === undefined) return undefined;
  const cls = String(attrs.class || "").split(/\s+/).find((c) => TEXT_PX[c]);
  const base = attrs["font-size"] ?? TEXT_PX[cls] ?? 16;
  return Math.round(base * scale * 10) / 10;
}

/** Make an SVG element with attributes. */
// Default sizes of the SVG text voices in notebook.css, so a scale can be applied.
export const TEXT_PX = { "t-print": 14, "t-book": 17, "t-hand": 18 };

export function svgEl(tag, attrs = {}, parent) {
  const el = document.createElementNS(SVG_NS, tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (v === undefined || v === null || v === false) continue;
    if (k === "text") el.textContent = v;
    // CSS classes would override a font-size attribute, so sizes go on the style (CSSOM is CSP-safe).
    else if (k === "font-size") el.style.fontSize = `${v}px`;
    else el.setAttribute(k, String(v));
  }
  parent?.append(el);
  return el;
}

/**
 * Add a hand-drawn mark: `paths` is a list of path data strings from ink.js.
 * tone is blue (explaining), red (a mistake or a mark), graphite (workings),
 * green (right) or highlight. Set pen=false for a mark that is already there.
 */
export function inkMark(parent, paths, { tone = "blue", pen = true, label, progress } = {}) {
  // progress (0..1) draws the mark part-way, for frame-exact animation and video export.
  const g = svgEl("g", { class: `tone-${tone}`, "data-pen": pen && progress === undefined ? "" : null, "aria-hidden": label ? null : "true" }, parent);
  if (label) svgEl("title", { text: label }, g);
  const n = paths.length;
  paths.forEach((d, i) => {
    const local = progress === undefined ? null : Math.max(0, Math.min(1, progress * n - i));
    svgEl("path", { class: "stroke", pathLength: 1, d, "stroke-dashoffset": local === null ? null : (1.001 - local).toFixed(4) }, g);
  });
  return g;
}

/** Handwritten SVG text in the coach's voice. */
export function handText(parent, x, y, text, { tone = "blue", size, anchor = "start", pen = true } = {}) {
  const cls = `t-hand${tone === "red" ? " is-red" : tone === "graphite" ? " is-graphite" : ""}`;
  const t = svgEl("text", { x, y, class: cls, "text-anchor": anchor, "font-size": size, "data-write": pen ? "" : null }, parent);
  t.textContent = text;
  return t;
}
