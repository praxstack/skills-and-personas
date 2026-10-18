"""Review P1-3: the explorer state equals what the video frame shows, read from the composition.

No TTS and no render: fixed 2 s narration segments give a schedule, the projector writes the
composition, and frames.probe seeks each scene's own timeline to the frame on screen at every
pause point, deriving the state from what is drawn (code, highlight, dots, visible outputs).
"""
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
        recap_rows = [r for r in rows if recap["start"] <= r["t"] < recap["end"]]
        assert recap_rows and all(r["frame_state"] == recap["state"] == r["explorer_state"] for r in recap_rows), recap_rows
        # the comparison is not self-referential: the old cue rule fails it, in the recap
        _rows, old_bad = _check(lesson, timing, vdir, _old_rule_cues(lesson, timing))
        assert any(recap["start"] <= r["t"] < recap["end"] for r in old_bad), "old cue rule passed the frame check"
        return {"pauses": len(rows), "recap_pauses": len(recap_rows), "old_rule_mismatches": len(old_bad)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
