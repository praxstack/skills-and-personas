// The board: paper or chalkboard. By default it follows the viewer's theme
// (dark means chalkboard); the learner can pin either one, and the choice is
// remembered for every page on this site. A lesson's own fallback is applied
// but never saved, so it can't override another lesson's default.

const BOARD_KEY = "notebook:board";
const MODES = ["auto", "paper", "chalk"];
const LABEL = { auto: "Board: auto", paper: "Board: paper", chalk: "Board: chalk" };

export function getBoard() {
  const b = document.documentElement.dataset.board;
  return b === "paper" || b === "chalk" ? b : "auto";
}

export function setBoard(mode, { remember = true } = {}) {
  const root = document.documentElement;
  if (mode === "paper" || mode === "chalk") root.dataset.board = mode;
  else delete root.dataset.board;
  if (!remember) return;
  try {
    localStorage.setItem(BOARD_KEY, getBoard());
  } catch {
    /* storage blocked */
  }
}

/** Apply the remembered board, or `fallback` ("auto", "paper", "chalk") when nothing is stored. */
export function restoreBoard(fallback = "auto") {
  let saved = null;
  try {
    saved = localStorage.getItem(BOARD_KEY);
  } catch {
    /* storage blocked */
  }
  // A page's own fallback isn't the learner's choice, so it isn't stored.
  if (MODES.includes(saved)) setBoard(saved);
  else setBoard(fallback, { remember: false });
}

/** A button that cycles auto, paper, chalk. */
export function boardButton(className = "nb-btn nb-btn-quiet") {
  const b = document.createElement("button");
  b.type = "button";
  b.className = className;
  const paint = () => {
    b.textContent = LABEL[getBoard()];
    b.title = "Switch between paper, chalkboard, and following your theme";
  };
  b.addEventListener("click", () => {
    setBoard(MODES[(MODES.indexOf(getBoard()) + 1) % MODES.length]);
    paint();
  });
  paint();
  return b;
}

// The chalk grain: a noise mask that breaks strokes up like chalk dragged
// across a board. notebook.css applies it through --stroke-grain, only on
// the chalkboard. Added once per page.
function ensureChalkFilter() {
  if (typeof document === "undefined" || document.getElementById("nb-chalk")) return;
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(NS, "svg");
  svg.setAttribute("width", "0");
  svg.setAttribute("height", "0");
  svg.setAttribute("aria-hidden", "true");
  svg.style.position = "absolute";
  svg.innerHTML =
    '<filter id="nb-chalk" x="-5%" y="-20%" width="110%" height="140%">' +
    '<feTurbulence type="fractalNoise" baseFrequency="1.3" numOctaves="2" seed="7" result="n"/>' +
    '<feColorMatrix in="n" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 -2.2 1.9" result="grain"/>' +
    '<feComposite in="SourceGraphic" in2="grain" operator="in" result="g"/>' +
    '<feDisplacementMap in="g" in2="n" scale="1.4" xChannelSelector="R" yChannelSelector="G"/>' +
    "</filter>";
  (document.body || document.documentElement).append(svg);
}
if (typeof document !== "undefined") {
  if (document.body) ensureChalkFilter();
  else document.addEventListener("DOMContentLoaded", ensureChalkFilter);
}
