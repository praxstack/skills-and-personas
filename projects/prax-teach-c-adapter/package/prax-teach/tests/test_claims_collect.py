"""Round 17: what the claims collector reads from the artifacts, checked against the drawing rather than metadata.

- the wrong-belief label is rendered text inside the misconception's box (Codex 4, P3-3);
- axis tick values sit on the axis's linear scale (Codex 5);
- wrapped SVG lines are joined into one claim, in a still and in inline SVG (P3-3).
"""
import re

from _util import V21
from selftest_support import NotRun
from ptk import host, model
from ptk.verify import claims

NEURON = V21 / "lessons" / "neuron"
STILL = NEURON / "build" / "still" / "neuron-wide-light.svg"


def _still():
    if not STILL.exists():
        raise NotRun(f"no neuron still at {STILL}; build lessons/neuron")
    return STILL.read_text()


def _where(lesson, svg_text, tmp, name="s.svg"):
    p = tmp / name
    p.write_text(svg_text)
    raw = claims._svg_texts(lesson, p)
    return {r[3] for r in raw if r[0] == "misconception"}


def _label_attr(svg, attr, value):
    """Replace one attribute on the wrong-belief label element."""
    def sub(m):
        tag = m.group(0)
        if f'{attr}="' in tag:
            return re.sub(rf'{attr}="[^"]*"', f'{attr}="{value}"', tag)
        return tag.replace("<text ", f'<text {attr}="{value}" ', 1)
    return re.sub(r'<text[^>]*data-chrome="wrong_belief"[^>]*>', sub, svg, count=1)


def test_wrong_belief_label_must_be_drawn_in_the_box():
    """Codex 4: the reviewer is told a misconception is "labelled as a wrong belief" only when the label is drawn:
    a <text> carrying the chrome string, visible, and inside the same box as the misconception (by geometry, not
    by data-in). Counterexamples: the label replaced by an empty <g data-chrome="wrong_belief" data-in=...>, the
    label moved out of the box while keeping data-in, and the label painted fill="none"."""
    lesson = model.load(NEURON)
    svg = _still()
    tmp = host.make_tmp("claims-label-")
    labelled = "still (labelled as a wrong belief)"
    assert _where(lesson, svg, tmp) == {labelled}, "the real still draws the label in the box"
    label = re.search(r'<text[^>]*data-chrome="wrong_belief"[^>]*>[^<]*</text>', svg).group(0)
    box = re.search(r'data-chrome="wrong_belief"[^>]*data-in="([^"]+)"', svg).group(1)
    empty = svg.replace(label, f'<g data-chrome="wrong_belief" data-in="{box}"/>')
    assert _where(lesson, empty, tmp) == {"s.svg"}, "metadata alone is not a label"
    moved = _label_attr(svg, "y", "40")
    assert _where(lesson, moved, tmp) == {"s.svg"}, "a label outside the box does not label it"
    unpainted = _label_attr(svg, "fill", "none")
    assert _where(lesson, unpainted, tmp) == {"s.svg"}, "an unpainted label is not drawn"
    hidden = _label_attr(svg, "opacity", "0")
    assert _where(lesson, hidden, tmp) == {"s.svg"}, "a transparent label is not drawn"
    wrong_words = svg.replace(label, re.sub(r">[^<]*</text>$", ">SEE BELOW</text>", label))
    assert _where(lesson, wrong_words, tmp) == {"s.svg"}, "the label must say the chrome string"
    return {"real": labelled, "box": box}


def _tick_svg(ticks, y=468.8, axis="add"):
    named = f' data-axis="{axis}"' if axis else ""
    body = "".join(f'<text x="{x}" y="{y}" data-label="axis-tick"{named} text-anchor="middle">{v}</text>'
                   for v, x in ticks)
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600">{body}</svg>'


def _tick_problems(lesson, svg_text, tmp):
    p = tmp / "ticks.svg"
    p.write_text(svg_text)
    items = claims._index(claims._svg_texts(lesson, p))
    claims.mapping_gate(lesson, items)
    return [claims.map_item(lesson, it)[1] for it in items if it["kind"] == "label" and "axis" in it["ref"]]


def test_axis_ticks_bound_to_a_linear_scale():
    """Codex 5: an axis tick label used to pass on its number pattern alone, so a tick changed from 1.5 to 999 was
    accepted and never reviewed. Now the ticks of one axis (same SVG, same baseline) must sit on one increasing
    linear scale fitted from their own positions (residual <= 1 px), with at least three ticks to check it, and (A5)
    the axis must be named so its labels can be bound to the tick values the facts give."""
    lesson = model.load(NEURON)
    tmp = host.make_tmp("claims-ticks-")
    good = [("−0.5", 447.3), ("0", 523.7), ("1.5", 752.7)]  # the neuron still's add-axis ticks
    assert _tick_problems(lesson, _tick_svg(good), tmp) == [None, None, None]
    bad = [("−0.5", 447.3), ("0", 523.7), ("999", 752.7)]
    probs = _tick_problems(lesson, _tick_svg(bad), tmp)
    assert all(probs) and "scale" in probs[0], probs
    reversed_ = [("1.5", 447.3), ("0", 523.7), ("−0.5", 752.7)]
    assert all(_tick_problems(lesson, _tick_svg(reversed_), tmp)), "a decreasing axis is not the drawn scale"
    two = [("0", 523.7), ("1.5", 752.7)]
    assert all(_tick_problems(lesson, _tick_svg(two), tmp)), "two ticks cannot show a scale"
    # A5: an axis with no name has no tick scale computed from the facts, so its ticks are refused (stricter)
    assert all(_tick_problems(lesson, _tick_svg(good, axis=None), tmp)), "an unnamed axis passed on its own labels"
    svg = _still()
    real = _tick_problems(lesson, svg, tmp)
    assert real and not any(real), real
    return {"real_ticks": len(real)}


def test_wrapped_svg_lines_join_into_one_claim():
    """P3-3: a mapped SVG <text> wrapped over <tspan y=...> lines is one run, joined with a space, in a still and in
    inline SVG (video, IVE); a plain tspan joins with nothing. A half sentence on its own still fails."""
    lesson = model.load(NEURON)
    c = lesson.data["claims"][0]
    words = c["text"].split()
    a, b = " ".join(words[: len(words) // 2]), " ".join(words[len(words) // 2:])
    tmp = host.make_tmp("claims-join-")
    still = (f'<svg xmlns="http://www.w3.org/2000/svg"><text data-claim="{c["id"]}" x="0" y="0">'
             f'<tspan x="0" y="10">{a}</tspan><tspan x="0" y="30">{b}</tspan></text></svg>')
    p = tmp / "j.svg"
    p.write_text(still)
    raw = [r for r in claims._svg_texts(lesson, p) if r[0] == "claim"]
    assert [r[2] for r in raw] == [f"{a} {b}"], raw
    col = claims._Collector()
    col.feed(f'<div>{still}</div>')
    got = [t for k, r, t in col.items if k == "claim"]
    assert got == [f"{a} {b}"], got
    col2 = claims._Collector()
    col2.feed(f'<svg><text data-claim="{c["id"]}"><tspan>{c["text"][:5]}</tspan><tspan>{c["text"][5:]}</tspan></text></svg>')
    assert [t for k, r, t in col2.items] == [c["text"]], col2.items
    items = claims._index([("claim", c["id"], f"{a} {b}", "still"), ("claim", c["id"], a, "still")])
    claims.mapping_gate(lesson, items)
    verdict = {it["text"]: claims.map_item(lesson, it)[1] for it in items}
    assert verdict[claims._norm(f"{a} {b}")] is None and verdict[claims._norm(a)], verdict
    return {"claim": c["id"]}
