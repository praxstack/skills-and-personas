r"""Interactive explorer projector (WP4: AC-4.1, 4.2, 4.6, 4.7, 4.8), plus the HTML page kit
that the Q&A expander shares.

One self-contained HTML file per lesson: inline CSS and JS under a hash-based CSP (E20), fonts
as data: URIs, no network, works from file://. For a switch lesson with two programs that
differ by one break (figure.program and figure.compare.program):

    controls        n ∈ domain (every case label, plus one value below and one above)
                    "break after case k" (switches between the two captured programs)
       │
       ▼  explorer.js: C17 6.8.4.2p5 / 6.8.1p4 / 6.8.6.3p2 on the program's case table
    view            executed lines, path tags, output lines, live prose, provenance
       │
       ▼  checked by verify() and tests/test_explorer.py against expect.switch_output and
          expect_switch.switch_trace (Python, independent of the page) for every state

Where the values come from:
    case table      parsed from the program source and required to equal the facts'
                    expect args (switch_line / switch_stdout), else ModelReferenceError
    n = captured n  the captured run (provenance shows its stdout sha256)
    any other n     computed with the switch rule, and the page says so (x_computed)

Every sentence is a chrome.json template or a claim's text. The templates that state C rules
are bound to the claims that justify them (ROLE_RULES), and teaching_texts() lists every
sentence any state can show, with those claim ids, for the claims gate.
"""
import base64
import hashlib
import json
import re

from .. import errors, expect, expect_switch, fonts, host, text
from ..text import esc

HTML_DIR = host.PKG / "ptk" / "templates" / "html"
TYPE_ROLES = ("kicker", "display", "body", "caption", "label", "note", "tag", "code", "value", "foot")
COLOR_ROLES = ("ground", "surface", "ink", "ink_soft", "label", "faint", "rule", "note", "note_tint", "correction",
               "correction_tint", "value", "highlight")


# ---------------------------------------------------------------- page kit (shared with qa.py)

def csp_hash(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode()).digest()).decode() + "'"


def csp(script, style):
    """E20. `track-src` is not a CSP directive (Chrome warns on it); media-src covers tracks."""
    return (f"default-src 'none'; script-src {csp_hash(script)}; style-src {csp_hash(style)}; img-src data:; "
            f"font-src data:; media-src 'self'; connect-src 'none'; base-uri 'none'; form-action 'none'")


def _family(key):
    spec = fonts.tokens()["fonts"][key]
    return f"{fonts.FAMILY[key]},{spec['fallback']}"


def theme_vars(name):
    th = fonts.tokens()["themes"][name]
    v = [f"--{r}:{th[r]}" for r in COLOR_ROLES]
    fr = th.get("frame", {})
    v.append(f"--panel-bg:{th['surface'] if fr.get('panel_fill', True) else 'transparent'}")
    v.append(f"--panel-border:{th['rule'] if fr.get('card_border', True) or fr.get('panel_divider') else 'transparent'}")
    for role in TYPE_ROLES:
        t = th["type"][role]
        v += [f"--{role}-font:{_family(t['font'])}", f"--{role}-weight:{t['weight']}",
              f"--{role}-caps:{'uppercase' if t.get('caps') else 'none'}",
              f"--{role}-track:{round(t.get('spacing', 0) * 0.06, 3)}em", f"--{role}-scale:{t.get('scale', 1)}"]
    return ";".join(v)


def font_keys():
    tk = fonts.tokens()["themes"]
    return sorted({tk[th]["type"][r]["font"] for th in ("light", "dark") for r in TYPE_ROLES})


def page_css(used_text, *sheets):
    """@font-face (subset to used_text) + light tokens + dark tokens + print (light) + the sheets."""
    faces = fonts.face_css({k: used_text for k in font_keys()})
    light, dark = theme_vars("light"), theme_vars("dark")
    body = "".join((HTML_DIR / s).read_text() for s in sheets)
    return (f"{faces}:root{{{light}}}@media (prefers-color-scheme:dark){{:root{{{dark}}}}}"
            f"@media print{{:root{{{light}}}}}{body}")


def page(title, body, css, script, data_id, data):
    data_json = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return (f'<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<meta name="color-scheme" content="light dark">'
            f'<meta http-equiv="Content-Security-Policy" content="{csp(script, css)}">'
            f'<title>{esc(title)}</title><style>{css}</style></head>\n<body>{body}'
            f'<script type="application/json" id="{data_id}">{data_json}</script>'
            f'<script>{script}</script></body></html>\n')


def ui_strings(keys):
    return {k: text.ui(k) for k in keys}


def all_chrome_text():
    return " ".join(text.chrome()["strings"].values())


# ---------------------------------------------------------------- switch model

DECL = re.compile(r"^(\s*int\s+(\w+)\s*=\s*)(-?\d+)(\s*;\s*)$")
SWITCH = re.compile(r"^\s*switch\s*\(\s*(\w+)\s*\)\s*\{\s*$")
CASE = re.compile(r"^\s*case\s+(-?\d+)\s*:\s*$")
DEFAULT = re.compile(r"^\s*default\s*:\s*$")
PUTS = re.compile(r'^\s*puts\("([^"\\]*)"\);\s*$')
BREAK = re.compile(r"^\s*break\s*;\s*$")
CLOSE = re.compile(r"^\s*\}\s*$")
RETURN = re.compile(r"^\s*return\b")


def parse_switch(src, pid="?"):
    """Line layout of a `int n = K; switch (n) { case ...: puts(...); [break;] ... } puts(...);` program.
    Anything else in the switch body is refused, so the page can never draw a statement it does not model."""
    lines = src.rstrip("\n").split("\n")

    def bad(i, why):
        return errors.ModelReferenceError(f"{pid}: line {i + 1}: {why}", pointer="/programs", line=i + 1)

    sw = next((i for i, ln in enumerate(lines) if SWITCH.match(ln)), None)
    if sw is None:
        raise bad(0, "no `switch (var) {` line")
    var = SWITCH.match(lines[sw]).group(1)
    decl = next((i for i in range(sw) if DECL.match(lines[i]) and DECL.match(lines[i]).group(2) == var), None)
    if decl is None:
        raise bad(sw, f"no `int {var} = <integer>;` before the switch")
    m = DECL.match(lines[decl])
    cases, cur, close = [], None, None
    for i in range(sw + 1, len(lines)):
        ln = lines[i]
        if CLOSE.match(ln):
            close = i
            break
        if not ln.strip():
            continue
        cm, dm = CASE.match(ln), DEFAULT.match(ln)
        if cm or dm:
            cur = {"label": int(cm.group(1)) if cm else "default", "line": i + 1, "stmts": [], "out": [],
                   "brk": False, "brk_line": None}
            cases.append(cur)
        elif cur is None:
            raise bad(i, "statement before the first case label")
        elif cur["brk"]:
            raise bad(i, "statement after break in the same case (unreachable)")
        elif PUTS.match(ln):
            cur["stmts"].append(i + 1)
            cur["out"].append(PUTS.match(ln).group(1))
        elif BREAK.match(ln):
            cur["brk"], cur["brk_line"] = True, i + 1
        else:
            raise bad(i, f"the explorer models case labels, puts(\"...\") and break only: {ln.strip()!r}")
    if close is None:
        raise bad(sw, "switch body has no closing brace on its own line")
    tail = []
    for i in range(close + 1, len(lines)):
        ln = lines[i]
        if RETURN.match(ln) or CLOSE.match(ln):
            break
        if PUTS.match(ln):
            tail.append({"line": i + 1, "out": PUTS.match(ln).group(1)})
        elif ln.strip():
            raise bad(i, f"after the switch the explorer models puts(\"...\") only: {ln.strip()!r}")
    return {"lines": [[i + 1, ln] for i, ln in enumerate(lines)], "n_line": decl + 1, "n_prefix": m.group(1),
            "n_value": int(m.group(3)), "n_suffix": m.group(4), "switch_line": sw + 1, "close_line": close + 1,
            "cases": cases, "tail": tail}


def _switch_expect(lesson, pid):
    for f in lesson.data["facts"]:
        if f["program"] == pid and f["expect"].get("fn") in ("switch_line", "switch_stdout"):
            return f
    raise errors.ModelReferenceError(f"the switch explorer needs a switch_line or switch_stdout fact for {pid!r}",
                                     pointer="/facts")


# Claims the explorer's rule sentences rest on, found by the C17 text they quote (so a lesson
# cannot bind a template to an unrelated claim).
ROLE_RULES = {
    "match": ("If a converted value matches", None),
    "nomatch": ("If no converted case constant expression matches", None),
    "labels": ("Labels in themselves do not alter the flow of control", None),
    "brk": ("A break statement terminates execution of the smallest enclosing switch", "rule"),
    "bodyend": ("Except as indicated, statements are executed in sequence", None),
}


def _role_claim(lesson, role):
    quote, extra = ROLE_RULES[role]
    for c in lesson.data["claims"]:
        if any(s.get("quote", "").startswith(quote) for s in c.get("sources", [])) and extra in (None, c["kind"]):
            return c["id"]
    raise errors.ModelReferenceError(f"the switch explorer needs a claim for the {role!r} rule, quoting C17: "
                                     f"{quote!r}", pointer="/claims")


def _tail_claim(lesson, base, tail):
    facts = [f for f in lesson.data["facts"] if f["program"] == base and f["kind"] == "stdout-line"
             and f.get("value") == tail[-1]]
    for c in lesson.data["claims"]:
        if any(f["id"] in c.get("facts", []) for f in facts):
            return {"id": c["id"], "text": c["text"]}
    raise errors.ModelReferenceError("the switch explorer needs a claim that states the line printed after the switch",
                                     pointer="/claims")


def switch_model(lesson):
    fig = lesson.data.get("figure") or {}
    base, alt = fig.get("program"), (fig.get("compare") or {}).get("program")
    if not base or not alt:
        raise errors.ModelReferenceError("the switch explorer needs figure.program and figure.compare.program",
                                         pointer="/figure")
    progs = {}
    for pid in (base, alt):
        f = _switch_expect(lesson, pid)
        cases, n0, tail = f["expect"]["args"][:3]
        lay = parse_switch(lesson.program_source(pid), pid)
        got = [{"label": c["label"], "out": c["out"], "brk": c["brk"]} for c in lay["cases"]]
        if got != cases or [t["out"] for t in lay["tail"]] != list(tail) or lay["n_value"] != n0:
            raise errors.ModelReferenceError(f"{pid}: the program source and its facts' expect args disagree",
                                             pointer=f"/facts/{lesson.data['facts'].index(f)}/expect/args",
                                             source=got, expect=cases)
        sha = next((x["source"]["stdout_sha256"] for x in lesson.data["facts"]
                    if x["program"] == pid and x.get("source", {}).get("stdout_sha256")), None)
        if sha is None:
            raise errors.ModelReferenceError(f"{pid} has no captured stdout; run `ptk capture` first", pointer="/facts")
        path = lesson.program(pid)["path"]
        progs[pid] = {**lay, "id": pid, "path": path, "file": path.split("/")[-1], "sha": sha[:12], "n0": n0,
                      "expect_cases": cases, "expect_tail": list(tail)}
    a, b = progs[base], progs[alt]
    if [c["label"] for c in a["cases"]] != [c["label"] for c in b["cases"]] or a["n0"] != b["n0"]:
        raise errors.ModelReferenceError("the two programs need the same case labels and the same n", pointer="/figure")
    diff = [x["label"] for x, y in zip(a["cases"], b["cases"]) if x["brk"] != y["brk"]]
    if len(diff) != 1 or a["cases"][[c["label"] for c in a["cases"]].index(diff[0])]["brk"]:
        raise errors.ModelReferenceError("figure.compare.program must add exactly one break to figure.program",
                                         pointer="/figure/compare")
    ints = sorted(c["label"] for c in a["cases"] if c["label"] != "default")
    domain = sorted(set([ints[0] - 1, *ints, ints[-1] + 1]))
    roles = {r: _role_claim(lesson, r) for r in ROLE_RULES}
    return {"base": base, "alt": alt, "toggle_label": diff[0], "domain": domain, "n0": a["n0"], "programs": progs,
            "roles": roles, "tail_claim": _tail_claim(lesson, base, a["expect_tail"])}


# ---------------------------------------------------------------- independent expected view

def expected_view(model, brk, n):
    """What the page must show for (brk, n), from expect.py and expect_switch.py only. The page's
    own script computes the same view separately; verify() and the tests compare the two."""
    pid = model["alt"] if brk else model["base"]
    P = model["programs"][pid]
    tr = expect_switch.switch_trace(P["expect_cases"], n)
    out = expect.switch_output(P["expect_cases"], n, P["expect_tail"])
    by = {c["label"]: c for c in P["cases"]}
    path = [P["n_line"], P["switch_line"]]
    for lab in tr["ran"]:
        c = by[lab]
        path += [c["line"], *c["stmts"]] + ([c["brk_line"]] if c["brk"] else [])
    path += [t["line"] for t in P["tail"]]
    tags, prose = {}, []
    roles = model["roles"]

    def tag(line, key, tone, **kw):
        tags.setdefault(line, []).append({"key": key, "tone": tone, "text": text.ui(key, **kw) if kw else text.ui(key)})

    def say(key, role, **kw):
        prose.append({"key": key, "claims": [roles[role]], "text": text.ui(key, **kw)})

    if n != P["n0"]:
        tag(P["n_line"], "x_tag_changed", "muted", n0=P["n0"])
    if tr["enter"] is None:
        tag(P["switch_line"], "x_tag_nomatch", "muted")
        say("x_nomatch", "nomatch", n=n)
    else:
        e = by[tr["enter"]]
        tag(e["line"], "enter_label", "path")
        say("x_match", "match", n=n, k=e["label"], line=e["stmts"][0] if e["stmts"] else e["line"])
        for a, b in expect_switch.falls(P["expect_cases"], n):
            tag(by[b]["line"], "x_tag_fall", "warn")
            say("x_fall", "labels", a=a, b=b, line=by[b]["line"])
        last = by[tr["ran"][-1]]
        if tr["exit"] == "break":
            tag(last["brk_line"], "exit_label", "path")
            say("x_break", "brk", line=last["brk_line"])
        else:
            tag(P["close_line"], "x_tag_end", "path")
            say("x_end", "bodyend", k=last["label"], line=P["close_line"])
    prose.append({"claim": model["tail_claim"]["id"], "claims": [model["tail_claim"]["id"]],
                  "text": model["tail_claim"]["text"]})
    if n == P["n0"]:
        prov = {"key": "x_captured", "text": text.ui("x_captured", file=P["file"], n=n, sha=P["sha"])}
    else:
        prov = {"key": "x_computed", "text": text.ui("x_computed", n0=P["n0"])}
    return {"program": pid, "n": n, "brk": brk, "enter": tr["enter"], "exit": tr["exit"], "ran": tr["ran"],
            "path": path, "output": out, "tags": tags, "prose": prose, "prov": prov, "file": P["file"]}


def states(model):
    return [(brk, n) for brk in (False, True) for n in model["domain"]]


# ---------------------------------------------------------------- page

UI_KEYS = ("x_on", "x_off", "x_match", "x_nomatch", "x_fall", "x_break", "x_end", "x_tag_fall", "x_tag_nomatch",
           "x_tag_end", "x_tag_changed", "x_captured", "x_computed", "enter_label", "exit_label")


def _code_html(P, v):
    rows = []
    for no, src in P["lines"]:
        cls = "ln ran" if no in v["path"] else "ln"
        if no == P["n_line"]:
            code = f'{esc(P["n_prefix"])}<b class="nval" data-n="">{v["n"]}</b>{esc(P["n_suffix"])}'
        else:
            code = esc(src)
        tags = "".join(f'<span class="tag {t["tone"]}" data-chrome="{t["key"]}">{esc(t["text"])}</span>'
                       for t in v["tags"].get(no, []))
        rows.append(f'<li class="{cls}" data-line="{no}"><span class="no">{no}</span><span class="body">'
                    f'<code class="src">{code}</code>' + (f'<span class="tags">{tags}</span>' if tags else "")
                    + "</span></li>")
    return "".join(rows)


def _prose_html(v):
    out = []
    for p in v["prose"]:
        attr = f'data-chrome="{p["key"]}" data-claims="{",".join(p["claims"])}"' if "key" in p \
            else f'data-claim="{p["claim"]}"'
        out.append(f"<span {attr}>{esc(p['text'])}</span>")
    return "".join(out)


def _body(lesson, model, v):
    P = model["programs"][model["base"]]
    radios = "".join(f'<label><input type="radio" name="n" value="{n}"{" checked" if n == model["n0"] else ""}>'
                     f'<span>{n}</span></label>' for n in model["domain"])
    outs = "".join(f'<li><span class="k">{k + 1}</span><span class="val" data-value="">{esc(o)}</span></li>'
                   for k, o in enumerate(v["output"]))
    lede = next(c for c in lesson.data["claims"] if c["id"] == model["roles"]["labels"])
    files = [model["programs"][p]["file"] for p in (model["base"], model["alt"])]
    rows = []
    for n in model["domain"]:
        cells = "".join(f'<td class="v" data-computed="{b}">{esc(" · ".join(expected_view(model, b, n)["output"]))}</td>'
                        for b in (False, True))
        rows.append(f'<tr data-n="{n}"><th scope="row" class="mono">{n}</th>{cells}</tr>')
    table = (f'<table><caption data-chrome="x_table_caption">{esc(text.ui("x_table_caption", n0=model["n0"]))}</caption>'
             f'<thead><tr><th scope="col" data-chrome="x_col_n">{esc(text.ui("x_col_n"))}</th>'
             + "".join(f'<th scope="col" data-label="program-file">{esc(f)}</th>' for f in files)
             + f'</tr></thead><tbody>{"".join(rows)}</tbody></table>')
    paths = [f"lessons/{lesson.id}/{model['programs'][p]['path']}" for p in (model["base"], model["alt"])]
    src_links = "".join(f'<p data-role="source" data-chrome="source_link">{esc(text.ui("source_link", path=p))}</p>'
                        for p in paths)
    return f"""<div class="wrap">
<header class="mast"><p class="kicker" data-chrome="kicker">{esc(text.kicker(lesson))}</p>
<h1 data-label="title">{esc(lesson.data['title'])}</h1>
<p class="lede" data-claim="{lede['id']}">{esc(lede['text'])}</p></header>
<main class="explorer" aria-labelledby="x-h">
<h2 id="x-h" class="sec" data-chrome="x_section">{esc(text.ui('x_section'))}</h2>
<div class="controls js-only">
<fieldset class="seg" id="x-n"><legend class="lbl" data-chrome="x_n_label">{esc(text.ui('x_n_label'))}</legend>
<div class="opts">{radios}</div></fieldset>
<div class="toggles">
<button type="button" class="pill" id="x-brk" aria-pressed="false"><span data-chrome="x_toggle">{esc(text.ui('x_toggle', k=model['toggle_label']))}</span><span class="onoff" id="x-brk-state" data-chrome="x_off">{esc(text.ui('x_off'))}</span></button>
<button type="button" class="pill" id="x-reset" disabled data-chrome="x_reset">{esc(text.ui('x_reset'))}</button>
</div></div>
<div class="stage" id="x-state" data-n="{v['n']}" data-brk="false" data-program="{v['program']}" data-enter="{v['enter'] if v['enter'] is not None else ''}" data-exit="{v['exit']}" data-ran="{','.join(map(str, v['ran']))}">
<figure class="panel codepanel" data-key="code"><figcaption class="lbl"><span data-chrome="code_label">{esc(text.ui('code_label'))}</span> · <span id="x-file" data-label="program-file">{esc(v['file'])}</span></figcaption>
<ol class="code" id="x-code" data-code="{v['program']}">{_code_html(P, v)}</ol></figure>
<div class="side">
<section class="panel" data-key="output"><h3 class="lbl" data-chrome="output_label">{esc(text.ui('output_label'))}</h3><ol class="out" id="x-out">{outs}</ol></section>
<section class="panel" data-key="note"><h3 class="lbl" data-chrome="x_live_label">{esc(text.ui('x_live_label'))}</h3><p class="live" id="x-live" aria-live="polite">{_prose_html(v)}</p></section>
<p class="prov" id="x-prov" data-chrome="{v['prov']['key']}">{esc(v['prov']['text'])}</p>
</div></div>
<noscript><section class="nojs"><p data-chrome="x_noscript">{esc(text.ui('x_noscript', n0=model['n0']))}</p>{table}</section></noscript>
</main>
<footer class="foot"><p data-chrome="provenance">{esc(text.provenance(lesson))}</p>
{src_links}</footer>
</div>"""


def page_data(lesson, model):
    progs = {}
    for pid, P in model["programs"].items():
        progs[pid] = {k: P[k] for k in ("id", "file", "sha", "n0", "lines", "n_line", "n_prefix", "n_suffix",
                                        "switch_line", "close_line", "cases", "tail")}
    return {"base": model["base"], "alt": model["alt"], "n0": model["n0"], "domain": model["domain"],
            "programs": progs, "ui": ui_strings(UI_KEYS), "roles": model["roles"],
            "claims": {"tail": model["tail_claim"]}}


def project(lesson, out):
    """Write out/index.html and out/texts.json. Returns {"page", "model"}. A lesson with a mechanism panel
    gets the step-through explorer (stepper.py) instead of the switch explorer."""
    if (lesson.data.get("figure") or {}).get("panel"):
        from . import stepper
        return stepper.project(lesson, out)
    out.mkdir(parents=True, exist_ok=True)
    model = switch_model(lesson)
    v0 = expected_view(model, False, model["n0"])
    body = _body(lesson, model, v0)
    script = (HTML_DIR / "explorer.js").read_text()
    used = " ".join([body, all_chrome_text(), *[ln for P in model["programs"].values() for _, ln in P["lines"]],
                     *[c["text"] for c in lesson.data["claims"]], "0123456789-·"])
    css = page_css(used, "base.css", "explorer.css")
    html = page(lesson.data["title"], body, css, script, "ptk-explorer", page_data(lesson, model))
    (out / "index.html").write_text(html)
    (out / "texts.json").write_text(json.dumps(_texts(lesson, model), indent=1, ensure_ascii=False))
    (out / "domain.json").write_text(json.dumps({"domain": model["domain"], "toggle_label": model["toggle_label"],
                                                 "states": [expected_view(model, b, n) for b, n in states(model)]},
                                                indent=1, ensure_ascii=False, default=str))
    return {"page": out / "index.html", "model": model}


# ---------------------------------------------------------------- claims gate hand-off

def _texts(lesson, model):
    where = "explorer/index.html"
    items = [{"text": lesson.data["title"], "claims": [], "source": "label:title", "where": where}]
    lede = model["roles"]["labels"]
    items.append({"text": lesson.claim(lede)["text"], "claims": [lede], "source": f"claim:{lede}", "where": where})
    for key in ("kicker", "x_section", "x_n_label", "x_on", "x_off", "x_reset", "code_label", "output_label",
                "x_live_label", "x_col_n", "provenance"):
        kw = {"kicker": {"topic": lesson.data["topic"]}}.get(key, {})
        t = text.provenance(lesson) if key == "provenance" else text.ui(key, **kw)
        items.append({"text": t, "claims": [], "source": f"chrome:{key}", "where": where})
    for p in (model["base"], model["alt"]):
        items.append({"text": text.ui("source_link", path=f"lessons/{lesson.id}/{model['programs'][p]['path']}"),
                      "claims": [], "source": "chrome:source_link", "where": where})
    items.append({"text": text.ui("x_toggle", k=model["toggle_label"]), "claims": [], "source": "chrome:x_toggle",
                  "where": where})
    items.append({"text": text.ui("x_noscript", n0=model["n0"]), "claims": [], "source": "chrome:x_noscript",
                  "where": where + " <noscript>"})
    items.append({"text": text.ui("x_table_caption", n0=model["n0"]), "claims": [],
                  "source": "chrome:x_table_caption", "where": where + " <noscript>"})
    seen = set()
    for brk, n in states(model):
        v = expected_view(model, brk, n)
        state = f"{where} state n={n} break={'on' if brk else 'off'}"
        for p in v["prose"]:
            src = f"chrome:{p['key']}" if "key" in p else f"claim:{p['claim']}"
            items.append({"text": p["text"], "claims": p["claims"], "source": src, "where": state})
        for line, ts in v["tags"].items():
            for t in ts:
                items.append({"text": t["text"], "claims": [], "source": f"chrome:{t['key']}", "where": f"{state} line {line}"})
        items.append({"text": v["prov"]["text"], "claims": [], "source": f"chrome:{v['prov']['key']}", "where": state})
    out = []
    for it in items:
        k = (it["text"], it["source"])
        if k in seen:
            continue
        seen.add(k)
        out.append(it)
    return out


def teaching_texts(build_dir):
    """Every sentence and label the explorer can show, in any state: [{"text", "claims", "where",
    "source"}]. `claims` lists the claim ids a sentence states; chrome UI labels have none."""
    p = build_dir / "explorer" / "texts.json"
    return json.loads(p.read_text()) if p.exists() else []


# ---------------------------------------------------------------- browser checks (build gates and tests)

def drive(mode, page_path, shots=None, **extra):
    """Run templates/html/drive.mjs on a page opened from file:// and return its record."""
    from .. import node
    tmp = host.make_tmp(f"drive-{mode}-")
    job, res = tmp / "job.json", tmp / "result.json"
    job.write_text(json.dumps({"mode": mode, "page": str(page_path.resolve()),
                              "shots": str(shots.resolve()) if shots else None, **extra}))
    node.run_script(HTML_DIR / "drive.mjs", [job, res], timeout=900, check=False)
    if not res.exists():
        raise errors.ToolFailed(f"the {mode} browser driver wrote no result", job=str(job))
    out = json.loads(res.read_text())
    if not out.get("ok"):
        raise errors.ToolFailed(f"the {mode} browser driver failed", error=out.get("error", "")[-2000:])
    return out


def drive_explorer(model, page_path, shots=None):
    return drive("explorer", page_path, shots, domain=model["domain"], n0=model["n0"])


def _bool(b):
    return "true" if b else "false"


def check_view(model, snap, brk, n, prose=True):
    """Problems where one recorded page state differs from expected_view(brk, n)."""
    exp = expected_view(model, brk, n)
    P = model["programs"][exp["program"]]
    want = {"n": str(n), "brk": _bool(brk), "program": exp["program"], "file": exp["file"],
            "enter": "" if exp["enter"] is None else str(exp["enter"]), "exit": exp["exit"],
            "ran": ",".join(map(str, exp["ran"])), "ranLines": sorted(exp["path"]), "nval": str(n),
            "output": exp["output"]}
    probs = [f"{k}: page {snap.get(k)!r}, expected {v!r}" for k, v in want.items() if snap.get(k) != v]
    src = {no: s for no, s in P["lines"]}
    for row in snap["code"]:
        line_want = f"{P['n_prefix']}{n}{P['n_suffix']}" if row["line"] == P["n_line"] else src.get(row["line"])
        if row["text"] != line_want:
            probs.append(f"code line {row['line']}: {row['text']!r}, expected {line_want!r}")
        tw = [{"key": t["key"], "text": t["text"], "tone": t["tone"]} for t in exp["tags"].get(row["line"], [])]
        if row["tags"] != tw:
            probs.append(f"tags on line {row['line']}: {row['tags']}, expected {tw}")
    if [r["line"] for r in snap["code"]] != [no for no, _ in P["lines"]]:
        probs.append("code lines are not the program's lines")
    c = snap["controls"]
    cw = {"checked": str(n), "pressed": _bool(brk), "onoff": text.ui("x_on" if brk else "x_off"),
          "resetDisabled": n == model["n0"] and not brk}
    probs += [f"control {k}: {c.get(k)!r}, expected {v!r}" for k, v in cw.items() if c.get(k) != v]
    if prose:
        probs += check_prose(model, snap, exp)
    return probs


def check_prose(model, snap, exp=None):
    """AC-4.6: the live sentences and the provenance line equal those recomputed for this state, and
    none of the default state's state-specific sentences survives a change."""
    exp = exp or expected_view(model, snap["brk"] == "true", int(snap["n"]))
    got = [{"key": p["key"], "claim": p["claim"], "claims": p["claims"], "text": p["text"]} for p in snap["prose"]]
    want = [{"key": p.get("key"), "claim": p.get("claim"), "claims": ",".join(p["claims"]) if "key" in p else None,
             "text": p["text"]} for p in exp["prose"]]
    probs = [] if got == want else [f"prose {[g['text'] for g in got]} expected {[w['text'] for w in want]}"]
    if snap["prov"] != exp["prov"]:
        probs.append(f"provenance {snap['prov']} expected {exp['prov']}")
    if (exp["brk"], exp["n"]) != (False, model["n0"]):
        d = expected_view(model, False, model["n0"])
        stale = ({p["text"] for p in d["prose"]} - {p["text"] for p in exp["prose"]}) | {d["prov"]["text"]}
        left = [g["text"] for g in got if g["text"] in stale] + ([snap["prov"]["text"]] if snap["prov"]["text"] in stale else [])
        if left:
            probs.append(f"default-state sentences still shown after a change: {left}")
    return probs


def check_domain(model, rec, prose=True):
    """AC-4.2 (prose=False) / AC-4.6 (prose only): every recorded control step against its intended state."""
    probs, seen = [], set()
    for st in rec["steps"]:
        w = st["want"]
        seen.add((w["brk"], w["n"]))
        if prose:
            p = check_prose(model, st["snap"], expected_view(model, w["brk"], w["n"]))
        else:
            p = check_view(model, st["snap"], w["brk"], w["n"], prose=False)
        probs += [f"{st['action']} -> {x}" for x in p]
    missing = [s for s in states(model) if s not in seen]
    if missing:
        probs.append(f"states never reached through the controls: {missing}")
    return probs, len(rec["steps"])


CSP_REQUIRED = ("default-src 'none'", "script-src 'sha256-", "style-src 'sha256-", "img-src data:", "font-src data:")


def check_a11y(model, rec):
    """AC-4.1: CSP enforced (no violations, script ran under it), keyboard operable, visible focus,
    reduced motion, and a complete noscript explanation."""
    a, probs = rec["a11y"], []
    csp_s = a["csp"] or ""
    probs += [f"CSP lacks {d}" for d in CSP_REQUIRED if d not in csp_s]
    if "unsafe-inline" in csp_s or "unsafe-eval" in csp_s:
        probs.append("CSP allows unsafe-inline or unsafe-eval")
    if not a["jsClass"]:
        probs.append("the page script did not run under its CSP")
    if rec.get("scriptBlocked"):
        return probs + [f"{c['name']}: CSP violations {c['csp']}" for c in rec["contexts"] if c.get("csp")]
    if a["links"] or any(s["src"] for s in a["scripts"]) or a["styleAttrs"]:
        probs.append(f"external resources or style attributes: {a['links']}, {a['styleAttrs']}")
    for ctx in rec["contexts"]:
        if ctx.get("csp"):
            probs.append(f"{ctx['name']}: CSP violations {ctx['csp']}")
        if ctx["pageErrors"] or [m for m in ctx["console"] if m.startswith("error")]:
            probs.append(f"{ctx['name']}: errors {ctx['pageErrors'] + ctx['console']}")
    t = rec["tabOrder"]
    if not (t and t[0]["tag"] == "INPUT" and t[0]["name"] == "n" and t[0]["value"] == str(model["n0"])):
        probs.append(f"first Tab does not land on the n control: {t[:1]}")
    if len(t) < 2 or t[1]["id"] != "x-brk":
        probs.append(f"second Tab does not land on the break toggle: {t[1:2]}")
    for f in t[:2]:
        if f["outline"].split()[0] in ("none", "") or f["outline"].endswith(" 0px") or not f["visible"]:
            probs.append(f"no visible focus ring on {f}")
    kb = rec["keyboard"]
    i = model["domain"].index(model["n0"])
    n1 = model["domain"][min(i + 1, len(model["domain"]) - 1)]
    want = [(False, n1), None, (True, n1), (False, n1), None, (False, model["n0"])]
    for step, w in zip(kb, want):
        if w is None:
            continue
        probs += [f"keyboard {step['action']}: {x}" for x in check_view(model, step["snap"], *w)]
    if kb[1].get("active") != "x-brk" or kb[4].get("active") != "x-reset":
        probs.append(f"keyboard focus order: {kb[1].get('active')}, {kb[4].get('active')}")
    if rec["transitionsNormal"] in ("0s", "") or any(d != "0s" for d in rec["transitionsReduced"]):
        probs.append(f"reduced motion not respected: {rec['transitionsNormal']} / {rec['transitionsReduced']}")
    ns = rec["noscript"]
    if ns["note"] != [text.ui("x_noscript", n0=model["n0"])]:
        probs.append(f"noscript note {ns['note']}")
    if ns["controlsVisible"] or not ns["tableVisible"]:
        probs.append("without JS the controls show or the table is hidden")
    rows = {r["n"]: r["cells"] for r in ns["table"]}
    for n in model["domain"]:
        w = [" · ".join(expect.switch_output(model["programs"][p]["expect_cases"], n,
                                             model["programs"][p]["expect_tail"])) for p in (model["base"], model["alt"])]
        if rows.get(str(n)) != w:
            probs.append(f"noscript table n={n}: {rows.get(str(n))} expected {w}")
    probs += [f"noscript static state: {x}" for x in check_view(model, ns["snap"], False, model["n0"])
              if not x.startswith("control")]
    return probs


def check_layout(rec, width=None):
    """AC-4.7 (width=390) and the 1440 px companion: key nodes inside the screen, no inner scroll,
    nothing under 11 px, no page overflow, in every state and both themes."""
    probs, n = [], 0
    for L in rec["layout"]:
        if width and L["width"] != width:
            continue
        n += 1
        keys = {k["key"] for k in L["nodes"]}
        need = {"explorer": {"code", "output", "note"}, "stepper": {"code", "output", "note", "panel"}}.get(
            rec["mode"], {"question", "code", "options"})
        if not need <= keys:
            probs.append(f"{L['width']} {L['scheme']} n={L.get('n')}: key nodes {sorted(keys)} lack {sorted(need - keys)}")
        probs += [f"{L['width']} {L['scheme']} n={L.get('n')} brk={L.get('brk')}: {p}" for p in L["problems"]]
    return probs, n


def check_file(rec):
    """AC-4.8: opened from file:// with no server; nothing requested beyond file: and data:."""
    probs = [] if rec["url"].startswith("file://") else [f"not a file:// URL: {rec['url']}"]
    for ctx in rec["contexts"]:
        if ctx["requests"]:
            probs.append(f"{ctx['name']}: requests {ctx['requests']}")
    if not rec["a11y"]["jsClass"]:
        probs.append("the script did not run from file://")
    return probs


def gates(lesson, out, shots):
    """Build gates for the explorer (one browser run)."""
    if (lesson.data.get("figure") or {}).get("panel"):
        from . import stepper
        return stepper.gates(lesson, out, shots)
    model = switch_model(lesson)
    rec = drive_explorer(model, out / "index.html", shots)
    (out.parent / "work").mkdir(exist_ok=True)
    (out.parent / "work" / "explorer-drive.json").write_text(json.dumps(rec, indent=1))

    def g(gid, probs, measured):
        return {"id": gid, "medium": "explorer", "status": "failed" if probs else "passed",
                "measured": {**measured, "problems": probs[:30]}, "reason": "; ".join(probs[:3])[:500]}

    if rec.get("scriptBlocked"):
        why = check_a11y(model, rec)
        return [g(gid, why, {}) for gid in ("values.explorer", "explorer.prose-follows-state", "explorer.a11y-csp-noscript",
                                             "explorer.layout", "explorer.file-protocol")]
    vp, nsteps = check_domain(model, rec, prose=False)
    pp, _ = check_domain(model, rec, prose=True)
    lp, nl = check_layout(rec)
    return [g("values.explorer", vp, {"control_steps": nsteps, "states": len(states(model)), "domain": model["domain"],
                                      "against": "expect.switch_output + expect_switch.switch_trace"}),
            g("explorer.prose-follows-state", pp, {"control_steps": nsteps}),
            g("explorer.a11y-csp-noscript", check_a11y(model, rec), {"csp": rec["a11y"]["csp"][:120]}),
            g("explorer.layout", lp, {"layouts": nl, "widths": [390, 1440], "schemes": ["light", "dark"]}),
            g("explorer.file-protocol", check_file(rec), {"url": rec["url"]})]
