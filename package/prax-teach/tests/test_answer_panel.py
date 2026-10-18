"""Round 18: question scenes keep the mechanism panel (review neuron P2), so the gates measure that nothing on it
gives the answer away, by value (data-m, data-fact) or by geometry (data-implies: a bar whose end is the sum).
The fixtures plant the answer on the panel at the question cue and must fail."""
import json
import re
import shutil

from _util import V21
from selftest_support import NotRun
from ptk import host, model
from ptk.project import mech
from ptk.verify import frames

NEURON = V21 / "lessons" / "neuron"


def _q(lesson):
    return next(s for s in lesson.data["storyboard"] if s.get("question"))


def _ids(markup):
    out = set(re.findall(r'data-(?:m|fact)="([^"]+)"', markup))
    for imp in re.findall(r'data-implies="([^"]+)"', markup):
        out |= set(imp.split())
    return out


def test_question_state_panel_has_no_answer():
    """The drawn panel at each question's own state carries no answer fact, by value or geometry."""
    for d in sorted((V21 / "lessons").iterdir()):
        lesson = model.load(d)
        if not (lesson.data.get("figure") or {}).get("panel") or not all(f.get("value") for f in lesson.data["facts"]):
            continue
        sc = _q(lesson)
        for lay in ("wide", "portrait"):
            markup = mech.svg_fragment(lesson, sc["state"], lay, "dark")[0]
            assert frames.answer_on_panel(lesson, sc, _ids(markup)) == [], (lesson.id, lay)


def test_geometry_counts_as_showing_the_answer():
    """The neuron's bias bar ends at z, so once drawn it implies a = max(0, z) even with no value printed."""
    lesson = model.load(NEURON)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun("neuron not captured yet")
    sc = _q(lesson)
    P = lesson.data["figure"]["panel"]
    later = next(st["id"] for st in lesson.data["trace"] if P["sum"] in mech.shown_facts(lesson, st["id"])
                 and P["out"] not in mech.shown_facts(lesson, st["id"]))
    markup = mech.svg_fragment(lesson, later, "wide", "dark")[0]
    assert P["out"] not in set(re.findall(r'data-(?:m|fact)="([^"]+)"', markup)), "fixture shows a by value"
    assert frames.answer_on_panel(lesson, sc, _ids(markup)) == [P["out"]], "the bar's geometry was not counted"


def test_frame_probe_fails_a_planted_answer_bar():
    """In the rendered frame: the built question scene passes; the same scene with the answer's bar planted on its
    panel fails, measured by the frame probe, not read from the model."""
    lesson = model.load(NEURON)
    vdir = NEURON / "build" / "video"
    tpath = vdir / "timing.json"
    if not tpath.exists():
        raise NotRun("no built neuron video; run `ptk build lessons/neuron --canary`")
    timing = json.loads(tpath.read_text())
    sc = next(s for s in timing["scenes"] if s.get("question"))
    P = lesson.data["figure"]["panel"]
    tmp = host.make_tmp("answer-panel-")
    try:
        shutil.copytree(vdir / "composition", tmp / "composition", ignore=shutil.ignore_patterns("renders"))
        t = round(sc["start"] + sc["duration"] / 2, 3)
        frame, _s = frames.probe(lesson, tmp, timing, [t], work_name="clean", lesson_sha=lesson.sha256())
        assert frames.answer_on_panel(lesson, sc, frame[t]["panel_facts"]) == [], frame[t]["panel_facts"]
        f = tmp / "composition" / "compositions" / f"{sc['id']}.html"
        src = f.read_text()
        planted = src.replace('<div class="mechbox" data-key="panel">',
                              f'<div class="mechbox" data-key="panel"><svg width="200" height="20"><g data-m="{P["sum"]}" '
                              f'data-implies="{P["sum"]} {P["out"]}"><line x1="0" y1="10" x2="150" y2="10" stroke="#fff" '
                              f'stroke-width="9"/></g></svg>', 1)
        assert planted != src, "fixture out of date"
        f.write_text(planted)
        frame, _s = frames.probe(lesson, tmp, timing, [t], work_name="planted", lesson_sha=lesson.sha256())
        assert P["out"] in frames.answer_on_panel(lesson, sc, frame[t]["panel_facts"]), frame[t]["panel_facts"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
