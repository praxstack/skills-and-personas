"""Review P1-3: the explorer state equals what the video frame shows, read from the composition.

No TTS and no render: fixed 2 s narration segments give a schedule, the projector writes the
composition, and frames.probe seeks each scene's own timeline to the frame on screen at every
pause point, deriving the state from what is drawn (code, highlight, dots, visible outputs).
"""
import math
import shutil

from _util import SLICE
from ptk import host, model
from ptk.project import ive, video
from ptk.verify import frames, visual


def _timing(lesson):
    measured = [{"id": s["id"], "seconds": 2.0} for s in video.segments_of(lesson)]
    return video.schedule(lesson, measured)


def _composition(lesson, timing, root):
    vdir = root / "video"
    (vdir / "work").mkdir(parents=True)
    video.write_composition(lesson, timing, vdir / "composition")
    return vdir


def _old_rule_cues(lesson, timing):
    """The WP0 round-1 cue rule (before the fix): a scene whose state differs from the previous
    scene's always got a transition at its last narration segment, even a recap of a state already
    shown. Kept here only to prove the comparison catches it."""
    out, prev = [], None
    for i, sc in enumerate(timing["scenes"]):
        reveal = [c for c in timing["cues"] if c["scene"] == sc["id"]][-1]["start"] if i else 0.0
        shown = reveal + 0.5 if i else 0.0
        if prev is not None and sc["state"] != prev:
            out.append({"kind": "transition", "scene": sc["id"], "start": reveal, "end": shown, "state": ive._view(lesson, prev)})
        out.append({"kind": "state", "scene": sc["id"], "start": shown if sc["state"] != prev else sc["start"],
                    "end": sc["end"], "state": ive._view(lesson, sc["state"])})
        prev = sc["state"]
    out.sort(key=lambda c: c["start"])
    for i, c in enumerate(out):
        c["end"] = out[i + 1]["start"] if i + 1 < len(out) else timing["duration"]
        c["cue"] = f"old{i + 1}"
    return [c for c in out if c["end"] - c["start"] > 0.001]


def _check(lesson, timing, vdir, cue_list):
    times = [t for c in cue_list for t in visual._pause_points(c)]
    frame_at, _scenes = frames.probe(lesson, vdir, timing, times, work_name="frames-test")
    explorer = {(c["cue"], t): c["state"]["state_id"] for c in cue_list for t in visual._pause_points(c)}
    return frames.compare_pauses(cue_list, frame_at, explorer, visual._pause_points)


def test_explorer_matches_frame_at_every_pause():
    lesson = model.load(SLICE)
    timing = _timing(lesson)
    tmp = host.make_tmp("frame-state-")
    try:
        vdir = _composition(lesson, timing, tmp)
        cue_list = ive.cues(lesson, timing)
        rows, bad = _check(lesson, timing, vdir, cue_list)
        assert rows and not bad, f"explorer and frame disagree: {bad[:4]}"
        recap = next(s for s in timing["scenes"] if s["id"] == lesson.data["storyboard"][-1]["id"])
        recap_rows = [r for r in rows if recap["shown"] <= r["t"] < recap["end"]]
        assert recap_rows and all(r["frame_state"] == recap["state"] == r["explorer_state"] for r in recap_rows), recap_rows
        # WP5: the recap changes program, so it opens with a diff morph whose cue holds the old state
        morph_rows = [r for r in rows if recap["start"] <= r["t"] < recap["shown"]]
        assert recap["morph"] and morph_rows and all(r["explorer_state"] == recap["before"] for r in morph_rows), morph_rows
        # the comparison is not self-referential: the old cue rule fails it, in the recap
        _rows, old_bad = _check(lesson, timing, vdir, _old_rule_cues(lesson, timing))
        assert any(recap["start"] <= r["t"] < recap["end"] for r in old_bad), "old cue rule passed the frame check"
        return {"pauses": len(rows), "recap_pauses": len(recap_rows), "old_rule_mismatches": len(old_bad)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_program_change_frame_shows_the_explorers_program():
    """Review P1-A: at every pause point the frame draws the explorer's program, including the
    cues around a program change (sc5 fallthrough.c -> sc6 with_break.c)."""
    lesson = model.load(SLICE)
    timing = _timing(lesson)
    progs = {st["id"]: st["state"]["program"] for st in lesson.data["trace"]}
    changes = [s for p, s in zip(timing["scenes"], timing["scenes"][1:]) if progs[p["state"]] != progs[s["state"]]]
    assert changes, "the slice has no program change to test"
    tmp = host.make_tmp("frame-prog-")
    try:
        vdir = _composition(lesson, timing, tmp)
        rows, _bad = _check(lesson, timing, vdir, ive.cues(lesson, timing))
        wrong = [r for r in rows if r["frame"]["program"] != progs.get(r["explorer_state"])]
        assert not wrong, f"frame and explorer show different programs: {wrong[:3]}"
        for sc in changes:
            assert any(sc["start"] <= r["t"] < sc["end"] for r in rows), f"no pause point inside {sc['id']}"
        return {"pauses": len(rows), "program_changes": [s["id"] for s in changes]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_compare_pauses_rejects_a_moving_frame_of_another_program():
    """A transition cue may meet a frame in mid-tween only when it draws the explorer's program,
    on a path between the cue's state and the next cue's."""
    before = {"state_id": "s3", "program": "p1", "path": [4, 5, 8]}
    after = {"state_id": "s4", "program": "p1", "path": [4, 5, 8, 9]}
    cue_list = [{"cue": "m1", "kind": "transition", "start": 0.0, "end": 1.0, "state": before},
                {"cue": "m2", "kind": "state", "start": 1.0, "end": 2.0, "state": after}]
    explorer = {("m1", 0.5): "s3", ("m2", 1.5): "s4"}

    def run(frame):
        frame_at = {0.5: frame, 1.5: {"state": "s4", "program": "p1", "line": 9, "path": [4, 5, 8, 9], "output": []}}
        return frames.compare_pauses(cue_list, frame_at, explorer, lambda c: [c["start"] + 0.5])[1]

    assert not run({"state": "moving", "program": "p1", "path": [4, 5, 8], "output": []})
    assert run({"state": "moving", "program": "p2", "path": [4, 5, 8], "output": []}), "other program accepted"
    assert run({"state": "moving", "program": "p1", "path": [4, 5], "output": []}), "path behind the cue accepted"
    assert run({"state": "moving", "program": "p1", "path": [4, 5, 8, 9, 11], "output": []}), "path past the target accepted"


def test_a_program_change_after_a_question_answers_at_its_morph():
    """WP5: a program change right after a question is a diff morph, not a cut. The morph's
    transition cue is the answer cue (it still holds the question's state), and the new state
    follows when the morph is drawn."""
    lesson = model.load(SLICE)
    scenes = [{"id": "a", "state": "s0", "start": 0.0, "end": 5.0, "question": {"prompt": "?"}},
              {"id": "b", "state": "s4", "start": 5.0, "end": 9.0}]
    video.plan_screen(lesson, scenes)
    out = ive.cues(lesson, {"scenes": scenes, "duration": 9.0})
    assert scenes[1]["morph"] and scenes[1]["start"] < scenes[1]["reveal"] < scenes[1]["shown"] < scenes[1]["end"]
    assert [(c["kind"], c["state"]["state_id"], c.get("answer_for")) for c in out] == \
        [("question", "s0", None), ("answer", "s0", "a"), ("state", "s4", None)], out


def _diff_done(fr):
    """The diff morph is complete when the frame no longer shows the old program in any form: the
    old file label is gone, the new one is fully in, no struck-out band is left and every added row
    is fully drawn (until the swap to the new program's own rows, which hides them with the old set)."""
    d = fr.get("diff") or {}
    return ((d.get("file_old") or 0) < 0.01 and (d.get("file_cur") or 0) >= 0.99
            and all(x < 0.01 for x in d.get("removed", []))
            and ((d.get("rows_cur") or 0) >= 0.99 or all(x >= 0.99 for x in d.get("added", []))))


def test_note_waits_for_the_diff():
    """WP6 (WP5 open item): at a change of program the side note (which states the new program's
    behaviour) stays hidden until the diff morph is complete, checked at every frame of each morph
    scene, and is fully shown before the scene ends."""
    lesson = model.load(SLICE)
    timing = _timing(lesson)
    morphs = [s for s in timing["scenes"] if s.get("morph")]
    assert morphs, "the slice has no program change"
    fps = timing["fps"]
    times = sorted({round((math.floor(s["start"] * fps) + k) / fps + 0.001, 4) for s in morphs
                    for k in range(1, int((s["end"] - s["start"]) * fps))})
    tmp = host.make_tmp("frame-note-")
    try:
        vdir = _composition(lesson, timing, tmp)
        frame_at, _sc = frames.probe(lesson, vdir, timing, times, work_name="frames-note")
        early, shown = [], {}
        for t in times:
            fr = frame_at[t]
            if fr.get("note") is None:
                continue
            if fr["note"] > 0.01 and not _diff_done(fr):
                early.append({"t": t, "scene": fr["scene"], "note": fr["note"], "diff": fr["diff"]})
            if fr["note"] >= 0.99:
                shown.setdefault(fr["scene"], t)
        assert not early, f"the note is on screen before the diff is complete: {early[:3]}"
        assert set(shown) == {s["id"] for s in morphs}, shown
        return {"frames_checked": len(times), "note_first_full": shown}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_morph_output_stays_readable_until_the_new_output_is_on_screen():
    """Round-17 Codex 8: the morph gate's output obligation is measured on the frames, not taken from the
    renderer's own planner. Until a replacement output value is visibly on screen (opacity >= 0.5), every old output
    value stays fully shown. Codex's counterexample: the old output fades at 1.0 s, the new one only arrives at
    2.0 s. The planner-shortened deadline (the diff's end) accepted that gap; now it fails."""
    def samples(old_until, old_after, cur_from, end=3.0):
        return [{"t": t / 10, "out": [1.0 if t / 10 < old_until else old_after] * 2,
                 "cur": [1.0 if t / 10 >= cur_from else (0.6 if t / 10 >= cur_from - 0.1 else 0.0)]}
                for t in range(int(end * 10) + 1)]
    gap = frames.morph_output_problems(samples(old_until=1.0, old_after=0.3, cur_from=2.0))
    assert gap and gap[0]["kind"] == "output-not-readable" and gap[0]["t"] == 1.0, gap
    cross = frames.morph_output_problems(samples(old_until=1.9, old_after=0.3, cur_from=2.0))
    assert cross == [], f"a cross-fade into the new output is fine: {cross}"
    never = frames.morph_output_problems([{"t": t / 10, "out": [1.0 if t < 25 else 0.2], "cur": []} for t in range(31)])
    assert [p["t"] for p in never][:1] == [2.5], "with no replacement on screen the old output must stay to the end"
    none_old = frames.morph_output_problems([{"t": t / 10, "out": [], "cur": [0.0]} for t in range(5)])
    assert none_old == [], none_old
    return {"gap_caught_at": gap[0]["t"], "cross_fade_ok": True}


def _layer_rows(out_curve, in_curve, step=0.05):
    return [{"t": round(i * step, 2), "layers": [{"state": "s1", "flagged": True, "o": a},
                                                 {"state": "s2", "flagged": False, "o": b}]}
            for i, (a, b) in enumerate(zip(out_curve, in_curve))]


def test_panel_overlap_only_while_cross_fading():
    """Round-17 P2-3: the outgoing panel layer carries HyperFrames' overlap exemption, so the probe owns the
    cross-fade check, measured on the frames. Two layers may both be on screen only while one of them is fading,
    for at most MAX_CROSSFADE seconds, and the exempt (outgoing) layer must be gone by the scene's end. The
    auditor's counterexample: drop the outgoing layer's fade-out tween, so it stays fully shown under the new one
    for the whole scene. That is now a failure."""
    real_in = [0, 0, 0.074, 0.276, 0.452, 0.605, 0.732, 0.835, 0.913, 0.966, 0.995, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
    real_out = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0.997, 0.95, 0.848, 0.69, 0.477, 0.208, 0, 0, 0, 0]
    assert frames.layer_overlap_problems(_layer_rows(real_out, real_in)) == [], "the measured neuron sc4 cross-fade"
    stuck = frames.layer_overlap_problems(_layer_rows([1] * len(real_in), real_in))
    kinds = {p["kind"] for p in stuck}
    assert {"layer-never-fades-out", "overlap-not-fading"} <= kinds, stuck
    half = frames.layer_overlap_problems(_layer_rows([1] * 11 + [0.5] * 10, real_in))
    assert "layer-never-fades-out" in {p["kind"] for p in half}, half
    slow_out = [1] * 11 + [round(1 - i / 30, 3) for i in range(1, 31)] + [0] * 3
    slow = frames.layer_overlap_problems(_layer_rows(slow_out, real_in + [1] * (len(slow_out) - len(real_in))))
    assert "cross-fade-too-long" in {p["kind"] for p in slow}, slow
    one = [{"t": i / 20, "layers": [{"state": "s1", "flagged": False, "o": 1}]} for i in range(10)]
    assert frames.layer_overlap_problems(one) == []
    return {"stuck": sorted(kinds), "max_crossfade_s": frames.MAX_CROSSFADE}


def test_path_set_matching_refuses_ambiguity():
    """Round-17 P3-1: the frame probe compares visited lines as sets (a dot per line). Two trace states that are the
    same program, line, output and path set would be indistinguishable, and match_state used to return the first.
    Now such a frame is `ambiguous`, never a state. For a lesson with a figure.panel, a frame whose panel is missing
    (`none`) is unknown, not a match, in every scene (round 18: question scenes keep the panel too)."""
    import copy
    lesson = model.load(SLICE)
    s0 = lesson.data["trace"][0]
    twin = copy.deepcopy(lesson)
    clone = copy.deepcopy(s0)
    clone["id"] = "s-twin"
    clone["state"]["path"] = list(s0["state"]["path"]) + list(s0["state"]["path"])  # same set, repeated lines
    twin.data["trace"].append(clone)
    probe = {"program": s0["state"]["program"], "line": s0["state"]["line"], "path": list(s0["state"]["path"]),
             "output": list(s0["state"]["output"]), "panel": "none", "moving": False}
    assert frames.match_state(lesson, probe) == s0["id"]
    assert frames.match_state(twin, probe) == "ambiguous", frames.match_state(twin, probe)
    assert frames.set_collisions(twin) == [[s0["id"], "s-twin"]], frames.set_collisions(twin)
    assert frames.set_collisions(lesson) == [], "the slice has no set collisions"
    panel = model.load(SLICE.parent / "neuron")
    p0 = panel.data["trace"][-1]
    pp = {"program": p0["state"]["program"], "line": p0["state"]["line"], "path": list(p0["state"]["path"]),
          "output": list(p0["state"]["output"]), "moving": False}
    scene = next(sc for sc in panel.data["storyboard"] if sc["state"] == p0["id"] and not sc.get("question"))
    assert frames.match_state(panel, {**pp, "panel": p0["id"]}, scene) == p0["id"]
    assert frames.match_state(panel, {**pp, "panel": "none"}, scene) == "unknown", "a lost panel must not match"
    assert frames.match_state(panel, {**pp, "panel": "none"}) == "unknown", "with no scene known, the panel is expected"
    q = {"id": "q", "state": p0["id"], "question": {"prompt": "?"}}
    # round 18: a question scene keeps its panel (answer_on_panel measures that it shows no answer)
    assert frames.match_state(panel, {**pp, "panel": "none"}, q) == "unknown", "a question scene keeps its panel"
    assert frames.match_state(panel, {**pp, "panel": p0["id"]}, q) == p0["id"]
    return {"collision": "ambiguous", "lost_panel": "unknown"}
