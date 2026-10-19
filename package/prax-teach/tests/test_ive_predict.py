"""The IVE prediction gate (ptk/verify/ive_predict.py): round 18 review X1 and AC-6.8 (SPEC v1.4).

By default the film plays through each question and explains (AC-6.8); with the practice-mode toggle on,
it stops for the prediction (review X1). The static half reads ive-data.js and captions.vtt; the browser
half drives the built page in both modes. Each unit test plants one defect (no pause plan, "Pause here and
predict" with no invitation, a 3.8 s silent gap, 220 wpm, options that differ, a default film that stops,
a practice toggle that is missing or on by default) and checks the gate names it."""
import copy
import json

from _util import V21
from selftest_support import NotRun
from ptk import model, text
from ptk.verify import ive_predict as P

LESSON = V21 / "lessons" / "one-byte-four-views"


def _fixture():
    lesson = model.load(LESSON)
    sc = next(s for s in lesson.data["storyboard"] if s.get("question"))
    opts = [{"text": o["text"], "correct": o["correct"]} for o in sc["question"]["options"]]
    caps = [{"id": f"{sc['id']}.0", "start": 10.0, "end": 15.0,
             "text": "Which answer do you predict? Pick one of the three before the answer plays."},
            {"id": "next.0", "start": 15.6, "end": 18.0, "text": "The next line."}]
    data = {"questions": [{"scene": sc["id"], "options": opts, "pause_at": 15.25, "resume_at": 15.3,
                           "answer_at": 17.0, "sealed": []}]}
    return lesson, data, caps, sc


def test_static_passes_a_gated_plan():
    lesson, data, caps, _sc = _fixture()
    probs, rows = P.static_check(lesson, data, caps)
    assert probs == [], probs
    assert rows[0]["silence_before_pause"] == 0.25 and rows[0]["silence_after_jump"] == 0.3


def test_static_fails_without_a_pause_plan():
    """The round-17 builds: ive-data.js has no `questions`, the film plays through the question."""
    lesson, _data, caps, sc = _fixture()
    probs, _ = P.static_check(lesson, {}, caps)
    assert any("not gated" in p and sc["id"] in p for p in probs), probs


def test_static_fails_on_the_old_line_and_its_silence():
    """'Pause here and predict' at 220 wpm, then 3.8 s of nothing."""
    lesson, data, caps, _sc = _fixture()
    caps[0].update(text="Pause here and predict the output before you go on.", start=10.0, end=12.7)
    data["questions"][0].update(pause_at=16.5, resume_at=16.55)
    caps[1]["start"] = 16.8
    probs, _ = P.static_check(lesson, data, caps)
    assert any("does not invite a pick" in p for p in probs), probs
    assert any("wpm" in p for p in probs), probs
    assert any("between the last spoken word and the pause" in p for p in probs), probs


def test_static_fails_when_options_differ():
    lesson, data, caps, _sc = _fixture()
    data["questions"][0]["options"] = list(reversed(data["questions"][0]["options"]))
    probs, _ = P.static_check(lesson, data, caps)
    assert any("differ from the storyboard" in p for p in probs), probs


def _fake_results(q, scene, opts, *, stop_t, held_t, refuse_t, resume_t, sealed_title, default=None):
    out = []
    for w in (1440, 390):
        out.append({"id": f"ive-explain:{scene}:{w}", "ok": True, "values": {"default": {
            "toggle": {"visible": True, "pressed": "false", "practice": False}, "modes": ["film"], "paused": False,
            "t_end": q["answer_at"] + 0.3, "in_gap": [], **(default or {})}}})
        out.append({"id": f"ive-predict:{scene}:{w}", "ok": True, "values": {
            "practice_on": {"pressed": "true", "practice": True},
            "stopped": {"mode": "ask", "asking": scene, "t": stop_t, "paused": True, "options": opts,
                        "chapters": [sealed_title], "page": ""},
            "held": {"mode": "ask", "t": held_t, "paused": True},
            "play_refused": {"mode": "ask" if refuse_t == stop_t else "film", "t": refuse_t, "paused": refuse_t == stop_t},
            "picked": {"mode": "film", "t_after_pick": resume_t, "t_later": resume_t + 1.5, "paused": False,
                       "verdict": "wrong", "chapters": ["Real title"], "picked": {scene: {"i": 1}}}}})
    return {"results": out, "outbound": []}


def test_browser_check_reads_a_good_run():
    lesson, data, _caps, sc = _fixture()
    q = {**data["questions"][0], "sealed": [0]}
    data = {"questions": [q]}
    opts = [o["text"] for o in sc["question"]["options"]]
    res = _fake_results(q, sc["id"], opts, stop_t=15.26, held_t=15.26, refuse_t=15.26, resume_t=15.31,
                        sealed_title=text.ui("ive_chapter_sealed"))
    probs, _ = P.browser_check(lesson, data, [], LESSON / "build" / "ive", run=lambda jobs, work: res)
    assert probs == [], probs


def test_browser_check_fails_when_play_runs_through():
    """What the reviewer saw: play() from before the question ran on into the answer."""
    lesson, data, _caps, sc = _fixture()
    q = {**data["questions"][0], "sealed": [0]}
    opts = [o["text"] for o in sc["question"]["options"]]
    res = _fake_results(q, sc["id"], opts, stop_t=15.26, held_t=15.26, refuse_t=18.0, resume_t=15.31,
                        sealed_title=lesson.data["storyboard"][0]["title"])
    probs, _ = P.browser_check(lesson, {"questions": [q]}, [], LESSON / "build" / "ive", run=lambda jobs, work: res)
    assert any("play() went past the question" in p for p in probs), probs
    assert any("while the question is open" in p for p in probs), probs


def test_browser_check_fails_when_the_default_film_stops():
    """AC-6.8: with practice mode off the film must not stop for the prediction, and the toggle must be visible and off."""
    lesson, data, _caps, sc = _fixture()
    q = {**data["questions"][0], "sealed": [0]}
    opts = [o["text"] for o in sc["question"]["options"]]
    seal = text.ui("ive_chapter_sealed")
    for default, why in (({"modes": ["film", "ask"], "paused": True, "t_end": 15.26}, "practice mode off"),
                         ({"toggle": {"visible": True, "pressed": "true", "practice": True}}, "toggle"),
                         ({"toggle": {"visible": False, "pressed": None, "practice": False}}, "toggle"),
                         ({"in_gap": [16.0, 16.5]}, "silent think gap")):
        res = _fake_results(q, sc["id"], opts, stop_t=15.26, held_t=15.26, refuse_t=15.26, resume_t=15.31,
                            sealed_title=seal, default=default)
        probs, _ = P.browser_check(lesson, {"questions": [q]}, [], LESSON / "build" / "ive", run=lambda jobs, work: res)
        assert any(why in p for p in probs), (default, probs)


def test_browser_jobs_cover_both_modes():
    """The gate drives the default film and, separately, the film with the practice toggle turned on."""
    lesson, data, _caps, sc = _fixture()
    jobs = P.browser_jobs("file:///x/index.html", {**data["questions"][0], "sealed": []}, [], LESSON / "build" / "shots")
    kinds = sorted({j["id"].split(":")[0] for j in jobs})
    assert kinds == ["ive-explain", "ive-predict"], kinds
    practice = [j for j in jobs if j["id"].startswith("ive-predict:")]
    assert all("getElementById('practice').click()" in json.dumps(j["steps"]) for j in practice)
    assert not any("getElementById('practice').click()" in json.dumps(j["steps"]) for j in jobs if j not in practice)


def test_built_ive_stops_for_every_prediction():
    """The real thing, on every built lesson whose IVE has a pause plan (Chromium from $PTK_STATE): the default film
    plays through, and with the practice toggle on it stops for the prediction."""
    ran = 0
    for d in sorted((V21 / "lessons").iterdir()):
        ive = d / "build" / "ive"
        if not (ive / "ive-data.js").exists() or not P.page_data(ive).get("questions"):
            continue
        lesson = model.load(d)
        g = P.gate(lesson, ive)
        assert g["status"] == "passed", json.dumps(g["measured"]["problems"], indent=1)
        ran += 1
    if not ran:
        raise NotRun("no built IVE with a pause plan; rebuild a lesson (`ptk build lessons/<slug> --canary`)")
