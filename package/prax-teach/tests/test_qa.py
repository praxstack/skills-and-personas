"""WP4 Q&A expander: AC-4.3. Layers open in order, each wrong option routes to its named
misconception and that misconception's correction claim, and print expands every layer.
Each property is also shown to fail on a tampered copy of the page."""
from functools import lru_cache

from _util import SLICE
from ptk import host, model
from ptk.project import explorer as kit
from ptk.project import qa
from ptk.text import esc


@lru_cache(maxsize=1)
def _built():
    lesson = model.load(SLICE)
    out = host.make_tmp("t-qa-") / "qa"
    r = qa.project(lesson, out)
    return lesson, r["model"], out / "index.html"


def _variant(edit):
    """Write a copy of the page changed by edit(src) -> src (script and style hashes recomputed) and drive it."""
    _lesson, _m, page = _built()
    src = page.read_text()
    new = edit(src)

    def block(s, tag, end):
        i = s.rindex(tag) + len(tag)
        return s[i:s.index(end, i)]
    for tag, end in (("<script>", "</script>"), ("<style>", "</style>")):
        old_b, new_b = block(src, tag, end), block(new, tag, end)
        new = new.replace(kit.csp_hash(old_b), kit.csp_hash(new_b))
    dst = host.make_tmp("t-qa-bad-") / "index.html"
    dst.write_text(new)
    return kit.drive("qa", dst)


def test_layers_misconceptions_print():
    lesson, m, page = _built()
    rec = kit.drive("qa", page)
    probs = qa.check_layers(lesson, m, rec) + qa.check_page(rec)
    assert not probs, probs[:10]
    wrong = [o for o in m["options"] if not o["correct"]]
    assert wrong and all(o["misconception"]["id"] in lesson.by_id("misconceptions") for o in wrong)
    assert {o["misconception"]["id"] for o in wrong} >= {"m.stops"}, wrong
    # negative 1: a wrong option routed to the other misconception's statement
    a, b = wrong[0]["misconception"], wrong[1]["misconception"]
    row = f'data-misconception="{a["id"]}">{esc(a["statement"])}</span>'
    assert row in page.read_text(), "tamper fixture out of date"
    swapped = _variant(lambda s: s.replace(row, f'data-misconception="{a["id"]}">{esc(b["statement"])}</span>'))
    bad = qa.check_layers(lesson, m, swapped)
    assert any(f"does not name misconception {a['id']}" in p for p in bad), f"misrouted option passed: {bad[:3]}"
    # negative 2: every layer may open before the prediction
    loose = _variant(lambda s: s.replace("var ready = i === 1 ? answered : prevOpen;", "var ready = true;"))
    bad = qa.check_layers(lesson, m, loose)
    assert any("before a prediction" in p or "out of order" in p for p in bad), f"out-of-order layers passed: {bad[:3]}"
    # negative 3: print no longer expands the closed layers
    noprint = _variant(lambda s: s.replace("html.js .layer .layer-body,html.js .key li{display:grid!important}", ""))
    bad = qa.check_layers(lesson, m, noprint)
    assert any(p.startswith("print:") for p in bad), f"print without expanded layers passed: {bad[:3]}"
    return {"layers": len(m["layers"]) + 1, "options": len(m["options"]), "wrong_routed": [o["misconception"]["id"] for o in wrong]}


def test_sealed_titles_wait_for_the_answer():
    """Round 18, review X2: a layer title that states the open question's answer is hidden until the learner
    answers, checked in the rendered DOM, and a page that shows it fails."""
    lesson, m, page = _built()
    sealed = [L["title"] for L in m["layers"] if L["sealed"]]
    assert sealed, "the switch lesson should seal at least one title"
    rec = kit.drive("qa", page)
    assert not [p for p in qa.check_layers(lesson, m, rec) if "sealed" in p or "states the open" in p]
    leaky = _variant(lambda s: s.replace('html.js .layer h3[data-sealed="true"]{display:none}', ""))
    bad = qa.check_layers(lesson, m, leaky)
    assert any("states the open question's answer" in p for p in bad), bad[:3]
