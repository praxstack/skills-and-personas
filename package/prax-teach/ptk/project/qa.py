r"""Q&A expander projector (WP4: AC-4.3, D4.4).

    layer 1   the storyboard's first question: the program, the prompt, the options
              Check my answer ─▶ the chosen option's row of the answer key:
                  correct  → "Correct." + the answer fact's captured lines
                  wrong    → the named misconception (its statement) + its correction claim
    layer 2…  one per storyboard scene after the question: scene title, "predict, then reveal",
              then the scene's narration lines and the output facts its state has printed
              layer k+1's Reveal is enabled only once layer k is open (layer 2: once answered)

Everything is in the static document; qa.js only opens parts. With no JS every layer and the
whole answer key show (a note says to predict first); in print every layer and every option's
routing show. Same page kit and CSP as the explorer (explorer.page).
"""
import json

from .. import errors, text
from ..text import esc
from . import explorer as kit
from . import seal

HTML_DIR = kit.HTML_DIR


def _question(lesson):
    for i, sc in enumerate(lesson.data["storyboard"]):
        q = sc.get("question")
        if q and q.get("options"):
            return i, sc, q
    raise errors.ModelReferenceError("the Q&A expander needs a storyboard question with options", pointer="/storyboard")


def model(lesson):
    i, sc, q = _question(lesson)
    mis = lesson.by_id("misconceptions")
    facts = lesson.by_id("facts")
    state = lesson.state(sc["state"])["state"]
    options = []
    for k, o in enumerate(q["options"]):
        row = {"i": k, "text": o["text"], "correct": o["correct"]}
        if o["correct"]:
            row["answer"] = {"fact": q["answer_fact"], "lines": text.display(facts[q["answer_fact"]]).split("\n")}
        else:
            m = mis[o["misconception"]]
            row["misconception"] = {"id": m["id"], "statement": m["statement"],
                                    "correction": {"id": m["correction"], "text": lesson.claim(m["correction"])["text"]}}
        options.append(row)
    layers = []
    sealed = seal.sealed(lesson.data)
    for sc2 in lesson.data["storyboard"][i + 1:]:
        st = lesson.state(sc2["state"])["state"]
        layers.append({"scene": sc2["id"], "title": sc2["title"], "sealed": sealed.get(sc2["id"]) == sc["id"],
                       "ask": sc2.get("ask"),
                       "narration": [{"id": f"{sc2['id']}.{j}", "text": n["text"], "claims": n["claims"]}
                                     for j, n in enumerate(sc2["narration"])],
                       "output": [{"fact": f, "text": text.display(facts[f])} for f in st["output"]],
                       "program": lesson.program(st["program"])["path"].split("/")[-1]})
    return {"scene": sc["id"], "prompt": q["prompt"], "program": state["program"], "options": options, "layers": layers}


def _key_html(m):
    rows = []
    for o in m["options"]:
        head = (f'<span class="opttext" data-option="{m["scene"]}.{o["i"]}">{esc(o["text"])}</span>')
        if o["correct"]:
            vals = "".join(f'<span data-fact="{o["answer"]["fact"]}">{esc(v)}</span>' for v in o["answer"]["lines"])
            body = (f'<span class="verdict" data-chrome="qa_correct">{esc(text.ui("qa_correct"))}</span>'
                    f'<span class="lbl" data-chrome="answer_label">{esc(text.ui("answer_label"))}</span>'
                    f'<span class="ans">{vals}</span>')
        else:
            mc = o["misconception"]
            body = (f'<span class="verdict" data-chrome="qa_wrong">{esc(text.ui("qa_wrong"))}</span>'
                    f'<span class="belief" data-misconception="{mc["id"]}">{esc(mc["statement"])}</span>'
                    f'<span class="lbl" data-chrome="qa_correction">{esc(text.ui("qa_correction"))}</span>'
                    f'<span class="fix" data-claim="{mc["correction"]["id"]}">{esc(mc["correction"]["text"])}</span>')
        rows.append(f'<li data-opt="{o["i"]}" data-verdict="{"correct" if o["correct"] else "wrong"}">{head}{body}</li>')
    return "".join(rows)


def _layers_html(m):
    n = len(m["layers"]) + 1
    out = []
    for k, L in enumerate(m["layers"], start=2):
        lines = "".join(f'<p data-narration="{x["id"]}">{esc(x["text"])}</p>' for x in L["narration"])
        vals = "".join(f'<span data-fact="{o["fact"]}">{esc(o["text"])}</span>' for o in L["output"])
        out_html = (f'<p class="lbl"><span data-chrome="output_label">{esc(text.ui("output_label"))}</span> · '
                    f'<span data-label="program-file">{esc(L["program"])}</span></p><p class="vals">{vals}</p>') if vals else ""
        # a title that states the open question's answer stays sealed until the learner answers (seal.py)
        title = (f'<h3 data-label="scene-title" data-sealed="true">{esc(L["title"])}</h3>'
                 f'<h3 class="sealed-ph" data-chrome="qa_sealed">{esc(text.ui("qa_sealed"))}</h3>') if L["sealed"] else \
            f'<h3 data-label="scene-title">{esc(L["title"])}</h3>'
        hint = (f'<p class="ask" data-chrome="qa_ask">{esc(text.ui("qa_ask", ask=L["ask"][:-1]))}</p>' if L["ask"] else
                f'<p class="hint" data-chrome="qa_walk">{esc(text.ui("qa_walk"))}</p>')
        out.append(f'<li class="layer" data-layer="{k}" data-open="true" id="qa-l{k}">'
                   f'<div class="layer-head"><p class="lbl" data-chrome="qa_layer">{esc(text.ui("qa_layer", i=k, n=n))}</p></div>'
                   f'{title}{hint}'
                   f'<p><button type="button" class="pill reveal" aria-controls="qa-b{k}" data-chrome="qa_reveal">'
                   f'{esc(text.ui("qa_reveal"))}</button></p>'
                   f'<div class="layer-body" id="qa-b{k}" tabindex="-1">{lines}{out_html}</div></li>')
    return "".join(out), n


def _body(lesson, m):
    src = lesson.program_source(m["program"]).rstrip("\n").split("\n")
    code = "".join(f'<li class="ln"><span class="no">{i}</span><code class="src">{esc(s)}</code></li>'
                   for i, s in enumerate(src, 1))
    pfile = lesson.program(m["program"])["path"].split("/")[-1]
    opts = "".join(f'<label class="opt"><input type="radio" name="opt" value="{o["i"]}" data-correct="{str(o["correct"]).lower()}">'
                   f'<span data-option="{m["scene"]}.{o["i"]}">{esc(o["text"])}</span></label>' for o in m["options"])
    layers, n = _layers_html(m)
    return f"""<div class="wrap">
<header class="mast"><p class="kicker" data-chrome="kicker">{esc(text.kicker(lesson))}</p>
<h1 data-label="title">{esc(lesson.data['title'])}</h1></header>
<main class="qa">
<noscript><p class="nojs" data-chrome="qa_noscript">{esc(text.ui('qa_noscript'))}</p></noscript>
<ol class="layers">
<li class="layer qcard" data-layer="1" data-open="true">
<div class="layer-head"><p class="lbl" data-chrome="qa_layer">{esc(text.ui('qa_layer', i=1, n=n))}</p>
<p class="lbl" data-chrome="question_label">{esc(text.ui('question_label'))}</p></div>
<div class="layer-body qcard">
<h2 class="qtext" data-question="{m['scene']}" data-key="question">{esc(m['prompt'])}</h2>
<figure class="panel" data-key="code"><figcaption class="lbl"><span data-chrome="code_label">{esc(text.ui('code_label'))}</span> · <span data-label="program-file">{esc(pfile)}</span></figcaption>
<ol class="code" data-code="{m['program']}">{code}</ol></figure>
<fieldset class="opts" id="qa-options" data-key="options"><legend class="lbl" data-chrome="qa_choose">{esc(text.ui('qa_choose'))}</legend>{opts}</fieldset>
<p><button type="button" class="pill" id="qa-check" disabled data-chrome="qa_check">{esc(text.ui('qa_check'))}</button></p>
<ol class="key" id="qa-feedback" aria-live="polite">{_key_html(m)}</ol>
</div></li>
{layers}
</ol>
</main>
<footer class="foot"><p data-chrome="provenance">{esc(text.provenance(lesson))}</p></footer>
</div>"""


def project(lesson, out):
    out.mkdir(parents=True, exist_ok=True)
    m = model(lesson)
    body = _body(lesson, m)
    script = (HTML_DIR / "qa.js").read_text()
    used = " ".join([body, kit.all_chrome_text(), "0123456789"])
    css = kit.page_css(used, "base.css", "qa.css")
    (out / "index.html").write_text(kit.page(lesson.data["title"], body, css, script, "ptk-qa", {"scene": m["scene"]}))
    (out / "texts.json").write_text(json.dumps(_texts(lesson, m), indent=1, ensure_ascii=False))
    return {"page": out / "index.html", "model": m}


def _texts(lesson, m):
    w = "qa/index.html"
    n = len(m["layers"]) + 1
    items = [{"text": lesson.data["title"], "claims": [], "source": "label:title", "where": w},
             {"text": m["prompt"], "claims": [], "source": f"question:{m['scene']}", "where": w}]
    for key, kw in (("kicker", {"subject": lesson.data.get("subject", "C"), "topic": lesson.data["topic"]}), ("question_label", {}), ("code_label", {}),
                    ("qa_choose", {}), ("qa_check", {}), ("qa_correct", {}), ("qa_wrong", {}), ("qa_correction", {}),
                    ("answer_label", {}), ("qa_walk", {}), ("qa_sealed", {}), ("qa_reveal", {}), ("output_label", {}),
                    ("qa_noscript", {})):
        items.append({"text": text.ui(key, **kw), "claims": [], "source": f"chrome:{key}", "where": w})
    items.append({"text": text.provenance(lesson), "claims": [], "source": "chrome:provenance", "where": w})
    for i in range(1, n + 1):
        items.append({"text": text.ui("qa_layer", i=i, n=n), "claims": [], "source": "chrome:qa_layer", "where": w})
    for o in m["options"]:
        items.append({"text": o["text"], "claims": [], "source": f"option:{m['scene']}.{o['i']}",
                      "facts": [o["answer"]["fact"]] if o["correct"] else [],
                      "misconception": None if o["correct"] else o["misconception"]["id"], "where": w})
        if not o["correct"]:
            mc = o["misconception"]
            items.append({"text": mc["statement"], "claims": [], "source": f"misconception:{mc['id']}",
                          "where": w + " (labelled as a wrong belief)"})
            items.append({"text": mc["correction"]["text"], "claims": [mc["correction"]["id"]],
                          "source": f"claim:{mc['correction']['id']}", "where": w})
    for L in m["layers"]:
        items.append({"text": L["title"], "claims": [], "source": f"label:scene-title:{L['scene']}", "where": w})
        if L["ask"]:
            items.append({"text": text.ui("qa_ask", ask=L["ask"][:-1]), "claims": [], "source": "chrome:qa_ask", "where": w})
        for x in L["narration"]:
            items.append({"text": x["text"], "claims": x["claims"], "source": f"narration:{x['id']}", "where": w})
    seen, out = set(), []
    for it in items:
        k = (it["text"], it["source"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


def teaching_texts(build_dir):
    """Every sentence and label in the Q&A expander: [{"text", "claims", "where", "source"}]."""
    p = build_dir / "qa" / "texts.json"
    return json.loads(p.read_text()) if p.exists() else []


# ---------------------------------------------------------------- browser checks

def _visible_entries(snap):
    return [e for e in (snap.get("feedback") or {}).get("entries", []) if e["visible"]]


def check_layers(lesson, m, rec):
    """AC-4.3: layers open in order; each wrong option routes to its named misconception and that
    misconception's correction claim; the correct one shows the captured answer; print and no-JS
    show every layer and every option's routing."""
    probs = []
    n = len(m["layers"]) + 1
    seq = rec["sequence"]

    def opened(snap):
        return [L["i"] for L in snap["layers"] if L["open"] and L["bodyVisible"]]

    s0 = seq[0]["snap"]
    sealed = [L["title"] for L in m["layers"] if L["sealed"]]
    shown0 = [t["text"] for t in s0.get("titles", []) if t["visible"]]
    for t in sealed:
        if t in shown0:
            probs.append(f"the title {t!r} states the open question's answer and is visible before an answer")
    answered = next((s["snap"] for s in seq if s["action"].startswith("choose")), None)
    if answered is not None and sealed:
        shown1 = [t["text"] for t in answered.get("titles", []) if t["visible"]]
        if not all(t in shown1 for t in sealed):
            probs.append(f"sealed titles stay hidden after an answer: {[t for t in sealed if t not in shown1]}")
    if opened(s0) != [1]:
        probs.append(f"on load the open layers are {opened(s0)}, expected [1]")
    if _visible_entries(s0):
        probs.append("the answer key shows before any prediction")
    if not s0["checkDisabled"]:
        probs.append("Check is enabled before an option is chosen")
    if opened(seq[1]["snap"]) != [1]:
        probs.append(f"layer 2 opened before a prediction: {opened(seq[1]['snap'])}")
    by_i = {str(o["i"]): o for o in m["options"]}
    choices = [s for s in seq if s["action"].startswith("choose")]
    if sorted(s["option"] for s in choices) != sorted(by_i):
        probs.append("not every option was tried")
    for s in choices:
        o, vis = by_i[s["option"]], _visible_entries(s["snap"])
        if [e["opt"] for e in vis] != [s["option"]]:
            probs.append(f"option {s['option']}: shown rows {[e['opt'] for e in vis]}")
            continue
        items = vis[0]["items"]
        if o["correct"]:
            facts = [x["text"] for x in items if x["fact"] == o["answer"]["fact"]]
            if facts != o["answer"]["lines"] or not any(x["chrome"] == "qa_correct" for x in items):
                probs.append(f"correct option {o['text']!r}: answer shown {facts}, expected {o['answer']['lines']}")
            if s["snap"]["feedback"]["kind"] != "correct":
                probs.append(f"correct option marked {s['snap']['feedback']['kind']}")
        else:
            mc = o["misconception"]
            got_m = [x for x in items if x["misconception"] == mc["id"]]
            got_c = [x for x in items if x["claim"] == mc["correction"]["id"]]
            if not got_m or got_m[0]["text"] != mc["statement"]:
                probs.append(f"wrong option {o['text']!r} does not name misconception {mc['id']}")
            if not got_c or got_c[0]["text"] != mc["correction"]["text"]:
                probs.append(f"wrong option {o['text']!r} does not give correction claim {mc['correction']['id']}")
            if s["snap"]["feedback"]["kind"] != "wrong":
                probs.append(f"wrong option marked {s['snap']['feedback']['kind']}")
    oo = [s for s in seq if "out of order" in s["action"]]
    if n > 2 and (not oo or opened(oo[0]["snap"]) != [1]):
        probs.append(f"the last layer opened out of order: {opened(oo[0]['snap']) if oo else 'not tried'}")
    reveals = [s for s in seq if s["action"].startswith("reveal") and "keyboard" in s["action"]]
    for s in reveals:
        i = int(s["action"].split()[1])
        if opened(s["snap"]) != list(range(1, i + 1)):
            probs.append(f"after revealing layer {i} the open layers are {opened(s['snap'])}")
    if len(reveals) != n - 1:
        probs.append(f"revealed {len(reveals)} layers, expected {n - 1}")
    for L, snapL in zip(m["layers"], seq[-1]["snap"]["layers"][1:]):
        for x in L["narration"]:
            if x["text"] not in snapL["text"]:
                probs.append(f"layer {L['scene']} lacks narration {x['text']!r}")
        for o in L["output"]:
            if o["text"] not in snapL["text"]:
                probs.append(f"layer {L['scene']} lacks output {o['text']!r}")
    for name in ("print", "noscript"):
        snap = rec[name]
        shown = [L["i"] for L in snap["layers"] if L["bodyVisible"]]
        if shown != list(range(1, n + 1)):
            probs.append(f"{name}: expanded layers {shown}, expected all {n}")
        if sorted(e["opt"] for e in _visible_entries(snap)) != sorted(by_i):
            probs.append(f"{name}: answer key rows {[e['opt'] for e in _visible_entries(snap)]}, expected all")
    if rec["noscript"]["note"] != [text.ui("qa_noscript")]:
        probs.append(f"noscript note {rec['noscript']['note']}")
    return probs


def check_page(rec):
    """CSP, focus ring, reduced motion, file://, layout at 390/1440 (shared with the explorer checks)."""
    probs = []
    a = rec["a11y"]
    probs += [f"CSP lacks {d}" for d in kit.CSP_REQUIRED if d not in (a["csp"] or "")]
    if not a["jsClass"]:
        probs.append("the page script did not run under its CSP")
    for ctx in rec["contexts"]:
        if ctx.get("csp"):
            probs.append(f"{ctx['name']}: CSP violations {ctx['csp']}")
        if ctx["pageErrors"] or [x for x in ctx["console"] if x.startswith("error")]:
            probs.append(f"{ctx['name']}: errors {ctx['pageErrors'] + ctx['console']}")
    if rec["focusRing"].split()[0] in ("none", ""):
        probs.append(f"no focus ring: {rec['focusRing']}")
    if any(d != "0s" for d in rec["transitionsReduced"]):
        probs.append(f"reduced motion not respected: {rec['transitionsReduced']}")
    lp, _ = kit.check_layout(rec)
    return probs + lp + kit.check_file(rec)


def gates(lesson, out, shots):
    m = model(lesson)
    rec = kit.drive("qa", out / "index.html", shots)
    (out.parent / "work").mkdir(exist_ok=True)
    (out.parent / "work" / "qa-drive.json").write_text(json.dumps(rec, indent=1))
    if rec.get("scriptBlocked"):
        lp = pp = ["the page script did not run under its CSP"]
    else:
        lp, pp = check_layers(lesson, m, rec), check_page(rec)
    return [{"id": "qa.layers-misconceptions-print", "medium": "qa", "status": "failed" if lp else "passed",
             "measured": {"layers": len(m["layers"]) + 1, "options": len(m["options"]), "problems": lp[:30]},
             "reason": "; ".join(lp[:3])[:500]},
            {"id": "qa.page", "medium": "qa", "status": "failed" if pp else "passed",
             "measured": {"problems": pp[:30], "widths": [390, 1440], "schemes": ["light", "dark"]},
             "reason": "; ".join(pp[:3])[:500]}]
