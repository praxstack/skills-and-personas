"""Round-17 Codex P2, closed in round 18: axis ticks are bound to the data. A linear fit through the tick labels
alone passes ticks that are all shifted by the same amount; the bar ends and the gate dot are data marks whose
values come from the facts' independent expectations, and they must sit where the ticks put those values."""
import re

from _util import V21
from selftest_support import NotRun
from ptk import fonts, host, model
from ptk.project import still
from ptk.verify import claims

NEURON = V21 / "lessons" / "neuron"


def _svg(tmp, lesson, edit=None):
    src = still.render(lesson, "wide", "dark", fonts.tokens())
    if edit:
        src = edit(src)
    p = tmp / ("neuron-wide-dark.svg" if edit is None else "neuron-wide-dark-fx.svg")
    p.write_text(src)
    return p


def _axis_problems(lesson, path):
    return [ref for kind, ref, *_ in claims._svg_texts(lesson, path) if ref.startswith("axis-tick-off-scale|")]


def test_ticks_bound_to_the_data():
    lesson = model.load(NEURON)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun("neuron not captured yet")
    tmp = host.make_tmp("axis-")
    good = _svg(tmp, lesson)
    src = good.read_text()
    assert 'data-axis-anchor="add"' in src and 'data-axis-anchor="gate-z"' in src, "the still lost its axis anchors"
    assert _axis_problems(lesson, good) == []

    def shift(text):
        def bump(m):
            v = float(m.group(2).replace("−", "-")) + 1
            return m.group(1) + f"{v:g}".replace("-", "−") + "</text>"
        return re.sub(r'(<text [^>]*data-label="axis-tick"[^>]*data-axis="add"[^>]*>)([^<]+)</text>', bump, text)
    shifted = shift(src)
    assert shifted != src, "fixture did not shift the add axis"
    bad = _svg(tmp, lesson, lambda _s: shifted)
    # the shifted labels still fit a straight line, so only the data binding can catch them
    ticks = re.findall(r'<text [^>]*x="([\d.]+)"[^>]*data-label="axis-tick"[^>]*data-axis="add"[^>]*>([^<]+)</text>', shifted)
    assert claims.tick_scale_problem([(t, float(x)) for x, t in ticks]) is None
    probs = _axis_problems(lesson, bad)
    assert probs and any("do not match the data" in p or "does not span" in p for p in probs), probs


def _shift_axis(src, axis, f):
    def bump(m):
        v = f(float(m.group(2).replace("−", "-")))
        return m.group(1) + f"{v:g}".replace("-", "−") + "</text>"
    pat = r'(<text [^>]*data-label="axis-tick"[^>]*data-axis="' + axis + r'"[^>]*>)([^<]+)</text>'
    return re.sub(pat, bump, src)


def _no_anchors(src):
    return re.sub(r'<circle [^>]*data-axis-anchor="[^"]*"[^>]*/>', "", src)


def test_ticks_bound_without_data_marks():
    """A5 (DECISION-BRIEFS §5 row 8): a frame drawn before the bars and the gate dot appear (video scenes 1 to 3) has
    no data marks, so the anchors cannot catch ticks that are all wrong in the same way. Each tick label is now bound
    to the tick values computed from the facts' independent expectations. The still with its data marks stripped
    stands in for such a frame, and the rc1 video scene 1 (no marks at all) is checked when it is built."""
    lesson = model.load(NEURON)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun("neuron not captured yet")
    tmp = host.make_tmp("axis-bare-")
    src = _no_anchors(still.render(lesson, "wide", "dark", fonts.tokens()))
    assert "data-axis-anchor" not in src and src.count('data-label="axis-tick"') == 6
    bare = tmp / "bare.svg"
    bare.write_text(src)
    assert _axis_problems(lesson, bare) == [], _axis_problems(lesson, bare)
    out = {}
    for axis, how, f in (("add", "shifted", lambda v: v + 1), ("add", "scaled", lambda v: v * 2),
                         ("gate-z", "shifted", lambda v: v + 0.5), ("gate-z", "scaled", lambda v: v * 3)):
        wrong = _shift_axis(src, axis, f)
        assert wrong != src, f"fixture did not change the {axis} axis"
        ticks = re.findall(r'<text [^>]*x="([\d.]+)"[^>]*data-label="axis-tick"[^>]*data-axis="' + axis
                           + r'"[^>]*>([^<]+)</text>', wrong)
        assert claims.tick_scale_problem([(t, float(x)) for x, t in ticks]) is None, "the wrong labels must still fit a line"
        p = tmp / f"{axis}-{how}.svg"
        p.write_text(wrong)
        probs = _axis_problems(lesson, p)
        assert probs and all("facts" in q for q in probs), (axis, how, probs)
        out[f"{axis}-{how}"] = probs[0][:120]
    # an axis the verifier has no data scale for is refused, not passed on its own labels
    unnamed = re.sub(r' data-axis="add"', "", src)
    p = tmp / "unnamed.svg"
    p.write_text(unnamed)
    assert _axis_problems(lesson, p), "ticks of an axis without a data scale passed"
    # a real frame with no data marks: the rc1 video scene 1, when the lesson is built
    sc1 = NEURON / "build" / "video" / "composition" / "compositions" / "sc1.html"
    if sc1.exists():
        html = sc1.read_text()
        assert "data-axis-anchor" not in html and 'data-label="axis-tick"' in html
        def frame_problems(text):
            c = claims._Collector(lesson)
            c.feed(text)
            c.close()
            return [ref for _k, ref, *_ in c.items if ref.startswith("axis-tick-off-scale|")]
        assert frame_problems(html) == [], frame_problems(html)
        assert frame_problems(_shift_axis(html, "add", lambda v: v + 1)), "scene 1 passed with every add tick off by 1"
        out["sc1"] = "checked"
    return out
