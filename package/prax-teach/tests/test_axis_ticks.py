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
