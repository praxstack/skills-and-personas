r"""Step-through explorer for lessons with a mechanism panel (WP9; AC-4.1, 4.2, 4.6, 4.7, 4.8).

The switch explorer (explorer.py) recomputes a C rule for any input. A panel lesson (views, stack, neuron)
is a captured run, so its explorer steps through the run's trace states, one per figure state:

    controls   step radios 1..N, Previous / Next (keyboard: arrows on the radios, Tab to the buttons)
       │
       ▼  stepper.js shows exactly one pre-rendered step; it computes nothing
    a step     the program with its executed lines and current line, the mechanism panel at that state
               (light and dark, wide and narrow copies), the output printed so far, the claims the video
               narrates over that state, and the captured run's provenance

Every value is a fact (the values gate reads them all), and each step's panel, output and prose are the
ones the Python side computes for that state (expected_view); tests and the build gates compare every
step the driver reaches with it. Without JavaScript every step is shown, in order.
"""
import json
import re

from .. import errors, text
from ..text import esc
from . import explorer as kit
from . import mech
from . import path as rail

UI_KEYS = ("prev_state", "next_state")


def states(lesson):
    return list(lesson.data["figure"]["states"])


def _prose(lesson, sid):
    """The claims narrated over this state (first scene that shows it), in order; a state no scene shows
    gets its own label only."""
    out, seen = [], set()
    for sc in lesson.data["storyboard"]:
        if sc["state"] != sid or sc.get("question"):
            continue
        for n in sc["narration"]:
            for cid in n["claims"]:
                if cid not in seen:
                    seen.add(cid)
                    out.append({"claim": cid, "text": lesson.claim(cid)["text"]})
        break
    return out


def expected_view(lesson, sid):
    st = lesson.state(sid)
    s = st["state"]
    facts = lesson.by_id("facts")
    first, last = rail.listing(lesson, s["program"])
    panel = {}
    for layout in ("wide", "portrait"):
        _m, drawn, _c = mech.svg_fragment(lesson, sid, layout, "light")
        panel[layout] = sorted(set(drawn))
    return {"state": sid, "step": states(lesson).index(sid) + 1, "label": st["label"], "program": s["program"],
            "line": s["line"], "ran": sorted(n for n in set(s.get("path", [])) if first <= n <= last),
            "output": [{"fact": f, "text": text.display(facts[f])} for f in s["output"]],
            "panel": panel, "prose": _prose(lesson, sid)}


def _sha(lesson, pid):
    return next((f["source"]["stdout_sha256"][:12] for f in lesson.data["facts"]
                 if f["program"] == pid and f.get("source", {}).get("stdout_sha256")), None)


def nobr(s):
    """Escape s and keep each `name = value` together on one line (no orphaned values)."""
    out, pos = [], 0
    for m in re.finditer(r"[A-Za-z_][\w()]* = [-+]?\d[\w.]*", s):
        out.append(esc(s[pos:m.start()]))
        out.append(f'<span class="nobr">{esc(m.group(0))}</span>')
        pos = m.end()
    out.append(esc(s[pos:]))
    return "".join(out)


def _code(lesson, v):
    src = lesson.program_source(v["program"]).split("\n")
    first, last = rail.listing(lesson, v["program"])
    rows = []
    for no in range(first, last + 1):
        cls = "ln" + (" ran" if no in v["ran"] else "") + (" cur" if no == v["line"] else "")
        rows.append(f'<li class="{cls}" data-line="{no}"><span class="no">{no}</span>'
                    f'<code class="src">{esc(src[no - 1])}</code></li>')
    return "".join(rows)


def _step_html(lesson, sid, n):
    v = expected_view(lesson, sid)
    prog = lesson.program(v["program"])
    fname = prog["path"].split("/")[-1]
    svgs = "".join(mech.svg_fragment(lesson, sid, lay, th, attrs=f'class="mech mech-{lay[0]}-{th}"')[0]
                   for lay in ("wide", "portrait") for th in ("light", "dark"))
    outs = "".join(f'<li><span class="k">{k}</span><span class="val" data-fact="{o["fact"]}">{esc(o["text"])}</span></li>'
                   for k, o in enumerate(v["output"], 1)) or f'<li class="empty" data-chrome="s_no_output">{esc(text.ui("s_no_output"))}</li>'
    prose = "".join(f'<p data-claim="{p["claim"]}">{nobr(p["text"])}</p>' for p in v["prose"])
    prov = text.ui("x_captured_run", file=fname, sha=_sha(lesson, v["program"]))
    return (f'<section class="step place-{mech.page_place(lesson)}" id="step-{sid}" data-state="{sid}" data-step="{v["step"]}" '
            f'aria-labelledby="h-{sid}">'
            f'<h3 class="shead" id="h-{sid}"><span class="lbl" data-chrome="s_step">{esc(text.ui("s_step", k=v["step"], n=n))}</span> '
            f'<span class="slabel" data-trace="{sid}">{esc(v["label"])}</span></h3>'
            f'<div class="sgrid">'
            f'<figure class="panel mechbox" data-key="panel" role="group" aria-label="{esc(v["label"])}">{svgs}</figure>'
            f'<figure class="panel codepanel" data-key="code"><figcaption class="lbl"><span data-chrome="code_label">'
            f'{esc(text.ui("code_label"))}</span> · <span data-label="program-file">{esc(fname)}</span></figcaption>'
            f'<ol class="code" data-code="{v["program"]}">{_code(lesson, v)}</ol></figure>'
            f'<div class="side">'
            f'<section class="panel" data-key="output"><h4 class="lbl" data-chrome="output_label">{esc(text.ui("output_label"))}</h4>'
            f'<ol class="out">{outs}</ol></section>'
            f'<section class="panel" data-key="note"><h4 class="lbl" data-chrome="x_live_label">{esc(text.ui("x_live_label"))}</h4>'
            f'<div class="live">{prose}</div></section>'
            f'<p class="prov" data-chrome="x_captured_run">{nobr(prov)}</p></div></div></section>')


def _body(lesson):
    sids = states(lesson)
    fig = lesson.data["figure"]
    lede = fig.get("title_claim")
    radios = "".join(f'<label><input type="radio" name="step" value="{sid}"{" checked" if i == 0 else ""}>'
                     f'<span>{i + 1}</span></label>' for i, sid in enumerate(sids))
    steps = "".join(_step_html(lesson, sid, len(sids)) for sid in sids)
    paths = [f"lessons/{lesson.id}/{p['path']}" for p in lesson.data["programs"] if p["run"]]
    src_links = "".join(f'<p data-role="source" data-chrome="source_link">{esc(text.ui("source_link", path=p))}</p>'
                        for p in paths)
    return f"""<div class="wrap">
<header class="mast"><p class="kicker" data-chrome="kicker">{esc(text.kicker(lesson))}</p>
<h1 data-label="title">{esc(lesson.data['title'])}</h1>
{f'<p class="lede" data-claim="{lede}">{esc(lesson.claim(lede)["text"])}</p>' if lede else ''}</header>
<main class="explorer stepper" aria-labelledby="x-h">
<h2 id="x-h" class="sec" data-chrome="s_section">{esc(text.ui('s_section'))}</h2>
<noscript><p class="nojs" data-chrome="s_noscript">{esc(text.ui('s_noscript'))}</p></noscript>
<div class="controls js-only">
<fieldset class="seg" id="s-steps"><legend class="lbl" data-chrome="s_steps_label">{esc(text.ui('s_steps_label'))}</legend>
<div class="opts">{radios}</div></fieldset>
<div class="toggles"><button type="button" class="pill" id="s-prev" data-chrome="prev_state">{esc(text.ui('prev_state'))}</button>
<button type="button" class="pill" id="s-next" data-chrome="next_state">{esc(text.ui('next_state'))}</button></div></div>
<div class="steps" id="s-steps-box">{steps}</div>
</main>
<footer class="foot"><p data-chrome="provenance">{esc(text.provenance(lesson))}</p>
{src_links}</footer>
</div>"""


def project(lesson, out):
    out.mkdir(parents=True, exist_ok=True)
    if not lesson.data.get("figure", {}).get("panel"):
        raise errors.ModelReferenceError("the step explorer needs figure.panel", pointer="/figure")
    body = _body(lesson)
    script = (kit.HTML_DIR / "stepper.js").read_text()
    chars = " ".join(mech.svg_fragment(lesson, sid, lay, "light")[2] for sid in states(lesson)
                     for lay in ("wide", "portrait"))
    used = " ".join([body, kit.all_chrome_text(), chars, *[c["text"] for c in lesson.data["claims"]], "0123456789-·×−"])
    css = kit.page_css(used, "base.css", "explorer.css", "stepper.css")
    html = kit.page(lesson.data["title"], body, css, script, "ptk-stepper", {"states": states(lesson)})
    (out / "index.html").write_text(html)
    (out / "texts.json").write_text(json.dumps(_texts(lesson), indent=1, ensure_ascii=False))
    (out / "domain.json").write_text(json.dumps({"states": [expected_view(lesson, s) for s in states(lesson)]},
                                                indent=1, ensure_ascii=False))
    return {"page": out / "index.html", "model": None}


def _texts(lesson):
    where = "explorer/index.html"
    sids = states(lesson)
    items = [{"text": lesson.data["title"], "claims": [], "source": "label:title", "where": where}]
    lede = lesson.data["figure"].get("title_claim")
    if lede:
        items.append({"text": lesson.claim(lede)["text"], "claims": [lede], "source": f"claim:{lede}", "where": where})
    for key in ("s_section", "s_steps_label", "prev_state", "next_state", "code_label", "output_label", "x_live_label",
                "s_noscript"):
        items.append({"text": text.ui(key), "claims": [], "source": f"chrome:{key}", "where": where})
    items.append({"text": text.kicker(lesson), "claims": [], "source": "chrome:kicker", "where": where})
    items.append({"text": text.provenance(lesson), "claims": [], "source": "chrome:provenance", "where": where})
    for sid in sids:
        v = expected_view(lesson, sid)
        here = f"{where} step {v['step']}"
        items.append({"text": text.ui("s_step", k=v["step"], n=len(sids)), "claims": [], "source": "chrome:s_step", "where": here})
        items.append({"text": v["label"], "claims": [], "source": f"trace:{sid}", "where": here})
        for p in v["prose"]:
            items.append({"text": p["text"], "claims": [p["claim"]], "source": f"claim:{p['claim']}", "where": here})
    return items


# ---------------------------------------------------------------- browser checks

def drive(lesson, page_path, shots=None):
    return kit.drive("stepper", page_path, shots, states=states(lesson))


def check_step(lesson, snap, sid):
    """Problems where one recorded page step differs from expected_view(sid)."""
    exp = expected_view(lesson, sid)
    probs = []
    want = {"state": sid, "checked": sid, "label": exp["label"], "line": exp["line"], "ran": exp["ran"],
            "output": [o["text"] for o in exp["output"]], "output_facts": [o["fact"] for o in exp["output"]],
            "prose": [{"claim": p["claim"], "text": p["text"]} for p in exp["prose"]],
            "prevDisabled": exp["step"] == 1, "nextDisabled": exp["step"] == len(states(lesson))}
    probs += [f"{k}: page {snap.get(k)!r}, expected {v!r}" for k, v in want.items() if snap.get(k) != v]
    lay = snap.get("panelLayout")
    if lay not in ("wide", "portrait"):
        probs.append(f"no visible panel (layout {lay!r})")
    elif sorted(set(snap.get("panelFacts") or [])) != exp["panel"][lay]:
        probs.append(f"panel facts {sorted(set(snap.get('panelFacts') or []))} expected {exp['panel'][lay]}")
    if snap.get("panelState") != sid:
        probs.append(f"panel shows state {snap.get('panelState')!r}, expected {sid!r}")
    if snap.get("visibleSteps") != 1:
        probs.append(f"{snap.get('visibleSteps')} steps visible at once")
    return probs


def check_steps(lesson, rec, prose=None):
    probs, seen = [], set()
    for st in rec["steps"]:
        seen.add(st["want"])
        p = check_step(lesson, st["snap"], st["want"])
        if prose is True:
            p = [x for x in p if x.startswith(("prose", "label"))]
        elif prose is False:
            p = [x for x in p if not x.startswith(("prose", "label"))]
        probs += [f"{st['action']} -> {x}" for x in p]
    missing = [s for s in states(lesson) if s not in seen]
    if missing:
        probs.append(f"steps never reached through the controls: {missing}")
    return probs, len(rec["steps"])


def check_a11y(lesson, rec):
    a, probs = rec["a11y"], []
    csp_s = a["csp"] or ""
    probs += [f"CSP lacks {d}" for d in kit.CSP_REQUIRED if d not in csp_s]
    if "unsafe-inline" in csp_s or "unsafe-eval" in csp_s:
        probs.append("CSP allows unsafe-inline or unsafe-eval")
    if not a["jsClass"]:
        return probs + ["the page script did not run under its CSP"]
    if a["links"] or any(s["src"] for s in a["scripts"]) or a["styleAttrs"]:
        probs.append(f"external resources or style attributes: {a['links']}, {a['styleAttrs']}")
    for ctx in rec["contexts"]:
        if ctx.get("csp"):
            probs.append(f"{ctx['name']}: CSP violations {ctx['csp']}")
        if ctx["pageErrors"] or [m for m in ctx["console"] if m.startswith("error")]:
            probs.append(f"{ctx['name']}: errors {ctx['pageErrors'] + ctx['console']}")
    t = rec["tabOrder"]
    sids = states(lesson)
    if not (t and t[0]["tag"] == "INPUT" and t[0]["name"] == "step" and t[0]["value"] == sids[0]):
        probs.append(f"first Tab does not land on the step control: {t[:1]}")
    if len(t) < 2 or t[1]["id"] != "s-next":
        probs.append(f"second Tab does not land on Next (Previous is disabled at step 1): {t[1:2]}")
    for f in t[:2]:
        if f["outline"].split()[0] in ("none", "") or f["outline"].endswith(" 0px") or not f["visible"]:
            probs.append(f"no visible focus ring on {f}")
    kb = rec["keyboard"]
    want = [sids[1], None, None, sids[2], sids[1]]
    for step, w in zip(kb, want):
        if w is not None:
            probs += [f"keyboard {step['action']}: {x}" for x in check_step(lesson, step["snap"], w)]
    if [kb[1].get("active"), kb[2].get("active")] != ["s-prev", "s-next"]:
        probs.append(f"keyboard focus order: {kb[1].get('active')}, {kb[2].get('active')}")
    if rec["transitionsNormal"] in ("0s", "") or any(d != "0s" for d in rec["transitionsReduced"]):
        probs.append(f"reduced motion not respected: {rec['transitionsNormal']} / {rec['transitionsReduced']}")
    ns = rec["noscript"]
    if ns["note"] != [text.ui("s_noscript")]:
        probs.append(f"noscript note {ns['note']}")
    if ns["controlsVisible"] or ns["visibleSteps"] != sids:
        probs.append(f"without JS the controls show or not every step is shown in order: {ns['visibleSteps']}")
    return probs


def gates(lesson, out, shots):
    rec = drive(lesson, out / "index.html", shots)
    (out.parent / "work").mkdir(exist_ok=True)
    (out.parent / "work" / "explorer-drive.json").write_text(json.dumps(rec, indent=1))

    def g(gid, probs, measured):
        return {"id": gid, "medium": "explorer", "status": "failed" if probs else "passed",
                "measured": {**measured, "problems": probs[:30]}, "reason": "; ".join(probs[:3])[:500]}

    if rec.get("scriptBlocked"):
        why = check_a11y(lesson, rec)
        return [g(gid, why, {}) for gid in ("values.explorer", "explorer.prose-follows-state", "explorer.a11y-csp-noscript",
                                             "explorer.layout", "explorer.file-protocol")]
    vp, nsteps = check_steps(lesson, rec, prose=False)
    pp, _ = check_steps(lesson, rec, prose=True)
    lp, nl = kit.check_layout({**rec, "mode": "stepper"})
    return [g("values.explorer", vp, {"control_steps": nsteps, "states": len(states(lesson)),
                                      "against": "stepper.expected_view (facts, mech.shown_facts)"}),
            g("explorer.prose-follows-state", pp, {"control_steps": nsteps}),
            g("explorer.a11y-csp-noscript", check_a11y(lesson, rec), {"csp": rec["a11y"]["csp"][:120]}),
            g("explorer.layout", lp, {"layouts": nl, "widths": [390, 1440], "schemes": ["light", "dark"]}),
            g("explorer.file-protocol", kit.check_file(rec), {"url": rec["url"]})]

