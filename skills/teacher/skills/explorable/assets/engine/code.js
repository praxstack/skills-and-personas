// Code panel for explorables: C++ / Python (or any languages the lesson
// gives), line highlighting synced to lesson steps, editable Python that runs
// in the browser with Pyodide (in a worker, stoppable) when the page is allowed to load it, and the
// output the lesson's model says the program prints for the current inputs.
//
// Sources mark lines with a trailing comment, stripped for display:
//   C++:     dist[src] = 0;    //@init
//   Python:  dist[src] = 0     #@init
// A step with `line: "init"` lights that line in either language.
// Ported from Kai Mori's learner loop (public/learn/src/engine/code.js).

const CODE_MARKER = /\s*(?:\/\/|#)@([\w-]+)\s*$/;
const LANG_NAMES = { cpp: "C++", python: "Python", js: "JavaScript", javascript: "JavaScript", java: "Java", go: "Go", rust: "Rust" };
const PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@0.26.4/pyodide.js";
// Subresource integrity: the browser refuses the loader if the CDN ever serves different bytes.
const PYODIDE_SRI = "sha384-i3R37b3tF+HWudsUf1VSEOY2YxwSNMqY8DQa9Z0O3xh+NkJ9o+yjcGyIi5huj+nB";
const LANG_KEY = "explorable:lang";

export function parseSource(source) {
  const lines = [];
  const ids = {};
  String(source)
    .replace(/^\n/, "")
    .replace(/\s+$/, "")
    .split("\n")
    .forEach((raw, index) => {
      const m = raw.match(CODE_MARKER);
      if (m) ids[m[1]] = index;
      lines.push(m ? raw.slice(0, m.index) : raw);
    });
  return { lines, ids, text: lines.join("\n") };
}

const KEYWORDS = {
  cpp: /\b(int|long|const|for|auto|if|else|return|vector|string|char|while|bool|struct|class|public|void|using|namespace|include|std|static|size_t)\b/g,
  python: /\b(def|for|in|if|elif|else|return|range|while|and|or|not|None|True|False|class|import|from|print|len|lambda)\b/g,
  js: /\b(const|let|var|function|for|of|in|if|else|return|while|class|new|true|false|null)\b/g,
};

function tokens(line, lang) {
  const mark = lang === "python" ? "#" : "//";
  const at = line.indexOf(mark);
  const code = at >= 0 ? line.slice(0, at) : line;
  const comment = at >= 0 ? line.slice(at) : "";
  const out = [];
  const kw = KEYWORDS[lang] || KEYWORDS.js;
  const re = new RegExp(`(${kw.source})|('[^']*'|"[^"]*")|(\\b\\d+(?:\\.\\d+)?(?:e\\d+)?\\b)`, "g");
  let last = 0;
  for (const m of code.matchAll(re)) {
    if (m.index > last) out.push([null, code.slice(last, m.index)]);
    out.push([m[1] ? "tok-kw" : m[2] ? "tok-str" : "tok-num", m[0]]);
    last = m.index + m[0].length;
  }
  if (last < code.length) out.push([null, code.slice(last)]);
  if (comment) out.push(["tok-com", comment]);
  return out;
}

// Python runs in a Web Worker so a program that never ends (`while True:
// pass`) can be stopped without freezing the lesson. The worker comes from a
// blob: URL so it works from file:// and inside artifact hosts, and it fetches
// Pyodide with the same integrity pin before loading it with importScripts.
const PYODIDE_INDEX = PYODIDE.slice(0, PYODIDE.lastIndexOf("/") + 1);
const RUN_LIMIT_MS = 10000; // a run longer than this is stopped
const LOAD_LIMIT_MS = 45000; // the first run downloads Pyodide
const OUT_LIMIT = 100000; // characters of output kept from one run

// (Indented so the bundler doesn't take its lines for top-level declarations.)
const WORKER_SRC = `
  let ready = null;
  function load(url, sri, index) {
    return (async () => {
      let text;
      try {
        const r = await fetch(url, { integrity: sri, mode: "cors", credentials: "omit" });
        if (!r.ok) throw new Error(String(r.status));
        text = await r.text();
      } catch (e) {
        throw new Error("couldn't load Pyodide (" + (e.message || e) + ")");
      }
      importScripts(URL.createObjectURL(new Blob([text], { type: "text/javascript" })));
      return loadPyodide({ indexURL: index });
    })();
  }
  // One run at a time: runs share one Pyodide and its sys.stdin, stdout and
  // stderr, so a second run waits for the first instead of mixing with it.
  let queue = Promise.resolve();
  self.onmessage = (e) => {
    queue = queue.then(() => run(e)).catch(() => {});
  };
  async function run({ data }) {
    const { id, url, sri, index, src, stdin, limit } = data;
    postMessage({ id, type: "turn" }); // its turn now: the page starts its load timer here
    let py;
    try {
      py = await (ready ||= load(url, sri, index));
    } catch (e) {
      ready = null;
      return postMessage({ id, type: "error", load: true, message: String(e.message || e) });
    }
    let out = "";
    let cut = false;
    const add = (s) => {
      if (cut) return;
      const line = s + "\\n";
      const room = limit - out.length;
      if (line.length <= room) {
        out += line;
      } else {
        out += line.slice(0, Math.max(0, room)) + "\\n[output truncated]\\n";
        cut = true;
      }
    };
    py.setStdout({ batched: add });
    py.setStderr({ batched: add });
    postMessage({ id, type: "started" });
    // Each run gets its own globals, as a fresh "python3 file.py" would: a
    // name defined by an earlier run must not leak into this one.
    const scope = py.globals.get("dict")();
    try {
      scope.set("__name__", "__main__");
      scope.set("__stdin_text", stdin);
      await py.runPythonAsync("import sys, io\\nsys.stdin = io.StringIO(__stdin_text)\\ndel __stdin_text, sys, io\\n", { globals: scope });
      await py.runPythonAsync(src, { globals: scope });
      postMessage({ id, type: "done", out });
    } catch (e) {
      postMessage({ id, type: "error", message: String(e.message || e), out });
    } finally {
      scope.destroy();
    }
  }
`;

let pyWorker = null;
let runSeq = 0;
function workerOnce() {
  if (!pyWorker) {
    const url = URL.createObjectURL(new Blob([WORKER_SRC], { type: "text/javascript" }));
    try {
      pyWorker = new Worker(url);
    } finally {
      URL.revokeObjectURL(url);
    }
  }
  return pyWorker;
}
// Every run still waiting on a worker, by worker: ending a worker (Stop, a
// timeout) must settle all of them, not only the run that ended it.
const jobs = new Map();
function killWorker(w) {
  w.terminate();
  if (pyWorker === w) pyWorker = null;
  const waiting = [...(jobs.get(w) || [])];
  jobs.delete(w);
  for (const abort of waiting) abort();
}

// Runs src; resolves { out } or rejects. The returned stop() ends the run
// (and the worker; the next run starts a fresh one). Each timer and stop()
// acts on the worker this run was given, never on a newer one.
export function runPython(src, stdin, onStarted) {
  const id = ++runSeq;
  let stop;
  const done = new Promise((resolve, reject) => {
    let w;
    try {
      w = workerOnce();
    } catch {
      return reject(Object.assign(new Error("couldn't start Pyodide's worker"), { load: true }));
    }
    let settled = false;
    // A load that times out ends the worker too: it may finish loading later and
    // run this program, and the next run must not queue behind it. The timer
    // starts at this run's turn, so time spent queued behind another run
    // doesn't count (that run has its own timers).
    let timer = null;
    const finish = (fn, v, kill = false) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      w.removeEventListener("message", onMsg);
      w.removeEventListener("error", onErr);
      jobs.get(w)?.delete(abort);
      if (kill) killWorker(w);
      fn(v);
    };
    // Another run ended this worker while this one was queued or running.
    const abort = () => finish(reject, Object.assign(new Error("stopped"), { stopped: "restart" }));
    const onMsg = ({ data }) => {
      if (data.id !== id) return;
      if (data.type === "turn") {
        timer = setTimeout(() => finish(reject, Object.assign(new Error("Pyodide took too long to load"), { load: true }), true), LOAD_LIMIT_MS);
      } else if (data.type === "started") {
        clearTimeout(timer);
        timer = setTimeout(() => finish(reject, Object.assign(new Error("timeout"), { stopped: "timeout" }), true), RUN_LIMIT_MS);
        onStarted?.();
      } else if (data.type === "done") finish(resolve, { out: data.out });
      else finish(reject, Object.assign(new Error(data.message), { load: data.load, out: data.out }), data.load);
    };
    const onErr = (e) => {
      e.preventDefault?.();
      finish(reject, Object.assign(new Error(e.message || "couldn't load Pyodide"), { load: true }), true);
    };
    if (!jobs.has(w)) jobs.set(w, new Set());
    jobs.get(w).add(abort);
    w.addEventListener("message", onMsg);
    w.addEventListener("error", onErr);
    stop = () => finish(reject, Object.assign(new Error("stopped"), { stopped: "user" }), true);
    w.postMessage({ id, url: PYODIDE, sri: PYODIDE_SRI, index: PYODIDE_INDEX, src, stdin, limit: OUT_LIMIT });
  });
  return { done, stop: () => stop?.() };
}

/**
 * createCodePanel(code, { el: h, getParams })
 * code: { title, cpp, python, ..., stdin(params) -> string, expect(params) -> string, runnable: ["python"] }
 */
export function createCodePanel(code, { h, getParams = () => ({}) }) {
  const langs = Object.keys(LANG_NAMES).filter((k) => typeof code[k] === "string");
  const parsed = Object.fromEntries(langs.map((k) => [k, parseSource(code[k])]));
  let lang = (() => {
    try {
      const saved = localStorage.getItem(LANG_KEY);
      return parsed[saved] ? saved : langs[0];
    } catch {
      return langs[0];
    }
  })();
  let activeId = null;
  let editing = false;

  const pre = h("pre", { class: "xp-code-pre", tabindex: "0", "aria-label": `${code.title || "Code"}, ${LANG_NAMES[lang]}` });
  const editor = h("textarea", { class: "xp-code-edit nb-field", spellcheck: "false", "aria-label": "Edit the Python code", hidden: true });
  const tabs = h("div", { class: "xp-code-tabs", role: "group", "aria-label": "Code language" });
  const runBtn = h("button", { type: "button", class: "nb-btn nb-btn-primary", text: "Run" });
  const networkConsent = h("input", { type: "checkbox", "aria-label": "Allow Python runtime download from jsDelivr" });
  const networkNotice = h("label", { class: "xp-muted" }, networkConsent,
    " Allow downloading Python (Pyodide) and its runtime files from cdn.jsdelivr.net to run this code. This uses an external service and requires an internet connection on first use.");
  const stopBtn = h("button", { type: "button", class: "nb-btn", text: "Stop", hidden: true });
  const editBtn = h("button", { type: "button", class: "nb-btn", text: "Edit" });
  const copyBtn = h("button", { type: "button", class: "nb-btn nb-btn-quiet", text: "Copy" });
  const expectBox = h("pre", { class: "xp-code-out nb-printout", "aria-live": "polite" });
  const runBox = h("pre", { class: "xp-code-out xp-code-run", "aria-live": "polite", hidden: true });
  const note = h("p", { class: "xp-muted" });
  const status = h("p", { class: "sr-only", "aria-live": "polite" });

  langs.forEach((k) =>
    tabs.append(
      h("button", {
        type: "button",
        class: "xp-chip",
        "data-lang": k,
        text: LANG_NAMES[k],
        onclick: () => {
          lang = k;
          editing = false;
          try {
            localStorage.setItem(LANG_KEY, k);
          } catch {
            /* storage blocked */
          }
          render();
        },
      }),
    ),
  );

  function render() {
    const { lines, ids } = parsed[lang];
    const active = activeId !== null ? ids[activeId] : undefined;
    pre.replaceChildren(
      ...lines.map((line, i) =>
        h(
          "span",
          { class: `xp-code-line${i === active ? " is-active" : ""}` },
          h("span", { class: "xp-code-gutter", "aria-hidden": "true", text: String(i + 1) }),
          h("span", { class: "xp-code-text" }, tokens(line, lang).map(([cls, text]) => (cls ? h("span", { class: cls, text }) : text))),
        ),
      ),
    );
    pre.setAttribute("aria-label", `${code.title || "Code"}, ${LANG_NAMES[lang]}`);
    tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
    const canRun = lang === "python" && (code.runnable || ["python"]).includes("python");
    runBtn.hidden = !canRun;
    networkNotice.hidden = !canRun;
    editBtn.hidden = !canRun;
    editor.hidden = !editing;
    pre.hidden = editing;
    editBtn.textContent = editing ? "Show the lesson's code" : "Edit";
    note.textContent = canRun
      ? "Edit the code and run it right here. The box below shows what the lesson's model says it prints."
      : `To run this, save it and compile it, for example: ${lang === "cpp" ? "g++ -std=c++17 main.cpp && ./a.out" : "run it with your language's tools"}. The box below shows what it prints for the current inputs.`;
    if (active !== undefined) {
      status.textContent = `Line ${active + 1}: ${lines[active].trim()}`;
      const el = pre.querySelector(".is-active");
      if (el && !pre.hidden) {
        const top = el.offsetTop;
        const bottom = top + el.offsetHeight;
        if (top < pre.scrollTop) pre.scrollTop = top - 8;
        else if (bottom > pre.scrollTop + pre.clientHeight) pre.scrollTop = bottom - pre.clientHeight + 8;
      }
    }
    updateExpected();
  }

  function stdinFor(params = getParams()) {
    return code.stdin ? String(code.stdin(params)) : "";
  }

  function updateExpected() {
    if (!code.expect) {
      expectBox.hidden = true;
      return;
    }
    const input = stdinFor();
    expectBox.hidden = false;
    expectBox.textContent = `${input ? `input:\n${input.trim()}\n\n` : ""}prints:\n${String(code.expect(getParams())).trim()}`;
  }

  let running = null;
  runBtn.addEventListener("click", async () => {
    runBox.hidden = false;
    if (!networkConsent.checked) {
      runBox.textContent = "To run Python here, first allow the external runtime download above. You can also copy the code and run it locally.";
      networkConsent.focus();
      return;
    }
    runBox.textContent = "Starting Python in your browser (the first run downloads it)…";
    runBtn.disabled = true;
    stopBtn.hidden = false;
    const src = editing ? editor.value : parsed.python.text;
    try {
      // stdin and the expected output come from the same parameters, taken now,
      // so moving a slider during the run can't make a correct run look wrong.
      const params = { ...getParams() }; // a copy: the page updates its params in place
      const stdin = stdinFor(params);
      const expected = code.expect ? String(code.expect(params)).trim() : null;
      running = runPython(src, stdin, () => (runBox.textContent = "Running…"));
      const { out } = await running.done;
      const got = out.trim();
      runBox.textContent = `${got || "(printed nothing)"}${expected === null ? "" : got === expected ? "\n\n✓ matches the lesson's model" : "\n\n✗ differs from the lesson's model (fine if you changed the code on purpose)"}`;
    } catch (e) {
      runBox.textContent = e.stopped
        ? e.stopped === "timeout"
          ? `Stopped after ${RUN_LIMIT_MS / 1000} s: the program was still running (a loop that never ends?). Python starts fresh on the next run.`
          : e.stopped === "restart"
            ? "Stopped: Python was restarted for another run on this page. Run it again."
            : "Stopped. Python starts fresh on the next run."
        : e.load
          ? "Python can't start on this page (some hosts block it). Copy the code and run it with python3, or open the lesson as a file in your browser."
          : `${e.out?.trim() ? `${e.out.trim()}\n\n` : ""}Error:\n${e.message || e}`; // what it printed before failing, then why
    } finally {
      running = null;
      runBtn.disabled = false;
      stopBtn.hidden = true;
    }
  });
  stopBtn.addEventListener("click", () => running?.stop());
  editBtn.addEventListener("click", () => {
    editing = !editing;
    if (editing && !editor.value) editor.value = parsed.python.text;
    render();
    if (editing) editor.focus();
  });
  copyBtn.addEventListener("click", async () => {
    const text = editing ? editor.value : parsed[lang].text;
    try {
      await navigator.clipboard.writeText(text);
      copyBtn.textContent = "Copied";
    } catch {
      copyBtn.textContent = "Select and copy";
      if (editing) {
        // the learner's edits live in the editor; the hidden <pre> has the original
        editor.focus();
        editor.select();
      } else {
        const r = document.createRange();
        r.selectNodeContents(pre);
        const sel = getSelection();
        sel.removeAllRanges();
        sel.addRange(r);
      }
    }
    setTimeout(() => (copyBtn.textContent = "Copy"), 1800);
  });

  const root = h(
    "figure",
    { class: "xp-code nb-sheet" },
    h("figcaption", { class: "xp-code-head" }, h("span", { class: "nb-label", text: code.title || "Code" }), tabs),
    pre,
    editor,
    networkNotice,
    h("div", { class: "xp-row" }, runBtn, stopBtn, editBtn, copyBtn),
    note,
    expectBox,
    runBox,
    status,
  );
  render();
  return {
    el: root,
    setLine(id) {
      activeId = id ?? null;
      render();
    },
    refresh: updateExpected,
    get lang() {
      return lang;
    },
  };
}
