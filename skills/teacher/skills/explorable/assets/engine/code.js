// Code panel for explorables: C++ / Python (or any languages the lesson
// gives), line highlighting synced to lesson steps, editable Python that runs
// in the browser with Pyodide when the page is allowed to load it, and the
// output the lesson's model says the program prints for the current inputs.
//
// Sources mark lines with a trailing comment, stripped for display:
//   C++:     dist[src] = 0;    //@init
//   Python:  dist[src] = 0     #@init
// A step with `line: "init"` lights that line in either language.
// Ported from Kai Mori's learner loop (public/learn/src/engine/code.js).

const CODE_MARKER = /\s*(?:\/\/|#)@([\w-]+)\s*$/;
const LANG_NAMES = { cpp: "C++", python: "Python", js: "JavaScript", java: "Java", go: "Go", rust: "Rust" };
const PYODIDE = "https://cdn.jsdelivr.net/npm/pyodide@0.26.4/pyodide.js";
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

let pyodideLoading = null;
function loadPyodideOnce() {
  if (pyodideLoading) return pyodideLoading;
  pyodideLoading = new Promise((resolve, reject) => {
    if (window.loadPyodide) return resolve(window.loadPyodide());
    const s = document.createElement("script");
    s.src = PYODIDE;
    s.onload = () => window.loadPyodide().then(resolve, reject);
    s.onerror = () => reject(new Error("couldn't load Pyodide"));
    document.head.append(s);
    setTimeout(() => reject(new Error("Pyodide took too long to load")), 45000);
  }).catch((e) => {
    pyodideLoading = null;
    throw e;
  });
  return pyodideLoading;
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

  function stdinFor() {
    return code.stdin ? String(code.stdin(getParams())) : "";
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

  runBtn.addEventListener("click", async () => {
    runBox.hidden = false;
    runBox.textContent = "Starting Python in your browser (the first run downloads it)…";
    runBtn.disabled = true;
    try {
      const py = await loadPyodideOnce();
      const src = editing ? editor.value : parsed.python.text;
      let out = "";
      py.setStdout({ batched: (s) => (out += `${s}\n`) });
      py.setStderr({ batched: (s) => (out += `${s}\n`) });
      const input = stdinFor();
      py.globals.set("__stdin_text", input);
      await py.runPythonAsync(`import sys, io\nsys.stdin = io.StringIO(__stdin_text)\n`);
      await py.runPythonAsync(src);
      const expected = code.expect ? String(code.expect(getParams())).trim() : null;
      const got = out.trim();
      runBox.textContent = `${got || "(printed nothing)"}${expected === null ? "" : got === expected ? "\n\n✓ matches the lesson's model" : "\n\n✗ differs from the lesson's model (fine if you changed the code on purpose)"}`;
    } catch (e) {
      runBox.textContent = /Pyodide/.test(String(e.message))
        ? "Python can't start on this page (some hosts block it). Copy the code and run it with python3, or open the lesson as a file in your browser."
        : `Error:\n${e.message || e}`;
    } finally {
      runBtn.disabled = false;
    }
  });
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
      const r = document.createRange();
      r.selectNodeContents(pre);
      const sel = getSelection();
      sel.removeAllRanges();
      sel.addRange(r);
    }
    setTimeout(() => (copyBtn.textContent = "Copy"), 1800);
  });

  const root = h(
    "figure",
    { class: "xp-code nb-sheet" },
    h("figcaption", { class: "xp-code-head" }, h("span", { class: "nb-label", text: code.title || "Code" }), tabs),
    pre,
    editor,
    h("div", { class: "xp-row" }, runBtn, editBtn, copyBtn),
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
