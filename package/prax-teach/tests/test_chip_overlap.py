"""A5 (DECISION-BRIEFS §5 row 10): the returned-value chip that flies up the factorial stack carries HyperFrames'
overlap exemption (data-layout-allow-overlap, added in round 18 with no audit). The frame probe now owns it.

Audit of the rc1 factorial build (sc6 to sc8, frames every 0.05 s): the overlap is real, not a probe artefact. The
chip is drawn on top of panel text for about 1.2 s per scene: it starts over its own return value, crosses the
caller's "r =" row, an earlier return value and the WAITING tag while it moves, and rests on the caller's slot,
which shows the same value fading in under it, before it fades out. At t = 0 it sits there at opacity 0, which
the exemption also hides from HyperFrames. It never rests on another fact's text and is gone well before the scene
ends. So the exemption stays, bounded by chip_overlap_problems; a chip that rests on another fact's text, stays on
screen too long or is still shown at the end fails video.scene-layout.
"""
import re
import shutil

from _util import V21
from selftest_support import NotRun
from ptk import host, model
from ptk.project import video
from ptk.verify import frames

FACTORIAL = V21 / "lessons" / "factorial-stack"


def _row(t, o, box, hits, fact="f.ret1"):
    return {"t": t, "chips": [{"id": "chip0", "fact": fact, "o": o, "box": box,
                               "hits": [{"text": x, "fact": f, "o": 1, "frac": 1} for x, f in hits]}]}


def test_chip_overlap_rules():
    """The rules on synthetic samples: an invisible chip's overlap is ignored, a moving chip may cross any text, a
    resting chip may cover only its own value, and it must leave the screen in time."""
    ok = [_row(0.0, 0.0, [0, 0, 9, 9], [("WAITING", "f.call2")]),  # opacity 0: a probe artefact, not a defect
          _row(0.1, 1.0, [0, 0, 9, 9], [("1", "f.ret1")]),
          _row(0.2, 1.0, [0, 5, 9, 14], [("WAITING", "f.call2")]),  # crossing while it moves
          _row(0.3, 1.0, [0, 9, 9, 18], [("1", "f.ret1")]),  # landed on its own value
          _row(0.4, 1.0, [0, 9, 9, 18], [("1", "f.ret1")]),
          _row(0.5, 0.0, [0, 9, 9, 18], [])]
    assert frames.chip_overlap_problems(ok) == []
    rest = ok[:3] + [_row(0.3, 1.0, [0, 9, 9, 18], [("WAITING", "f.call2")]),
                     _row(0.4, 1.0, [0, 9, 9, 18], [("WAITING", "f.call2")]), ok[5]]
    # the landing frame still counts as moving (its box differs from the frame before); the frame after it does not
    assert [p["kind"] for p in frames.chip_overlap_problems(rest)] == ["chip-covers-text-at-rest"]
    long_ = [_row(i * 0.1, 1.0, [0, 0, 9, 9], [("1", "f.ret1")]) for i in range(20)] + [_row(2.0, 0.0, [0, 0, 9, 9], [])]
    assert [p["kind"] for p in frames.chip_overlap_problems(long_)] == ["chip-shown-too-long"]
    end = ok[:5]
    assert "chip-still-shown" in [p["kind"] for p in frames.chip_overlap_problems(end)]


def _factorial_composition():
    lesson = model.load(FACTORIAL)
    if not all(f.get("value") for f in lesson.data["facts"]):
        raise NotRun("factorial-stack not captured yet")
    measured = [{"id": s["id"], "seconds": 2.0} for s in video.segments_of(lesson)]
    timing = video.schedule(lesson, measured)
    root = host.make_tmp("chips-")
    vdir = root / "video"
    (vdir / "work").mkdir(parents=True)
    video.write_composition(lesson, timing, vdir / "composition")
    return lesson, timing, vdir


def test_factorial_chip_overlap_probe():
    """The probe on the factorial composition the projector writes now: every chip scene passes, each chip is on
    screen for at most MAX_CHIP_SHOWN and covers only its own value at rest. Two tampered compositions fail: a chip
    that never fades out, and a chip relabelled as another fact (so its landing covers text it does not own)."""
    lesson, timing, vdir = _factorial_composition()
    try:
        return _probe(timing, vdir)
    finally:
        shutil.rmtree(vdir.parent, ignore_errors=True)


def _probe(timing, vdir):
    comps = vdir / "composition" / "compositions"
    chip_files = sorted(f for f in comps.glob("*.html") if 'class="chip"' in f.read_text())
    if not chip_files:
        raise NotRun("the factorial video draws no returned-value chip any more; nothing is exempt")
    got = frames.chip_samples(vdir, timing)
    assert set(got) == {f.stem for f in chip_files}, (sorted(got), [f.stem for f in chip_files])
    out = {}
    for sid, r in got.items():
        assert r["ok"] and r["rows"], (sid, r["error"])
        assert frames.chip_overlap_problems(r["rows"]) == [], (sid, frames.chip_overlap_problems(r["rows"]))
        shown = [row["t"] for row in r["rows"] for c in row["chips"] if c["o"] > frames.CHIP_SHOWN]
        assert shown, f"{sid}: the chip never appeared"
        overlapped = sum(1 for row in r["rows"] for c in row["chips"] if c["o"] > frames.CHIP_SHOWN and c["hits"])
        out[sid] = {"shown_s": round(shown[-1] - shown[0], 2), "frames_overlapping": overlapped}
    # the audit finding: the overlap is real (a visible chip covers drawn text), so the exemption needs this probe
    assert any(v["frames_overlapping"] for v in out.values()), out

    first = chip_files[0]
    src = first.read_text()
    stuck = re.sub(r"TO\(d, '#chip\d+', \{ opacity: 0, duration: 0\.2 \}, [\d.]+\);", "", src)
    assert stuck != src, "fixture did not remove the chip's fade-out"
    first.write_text(stuck)
    kinds = {p["kind"] for p in frames.chip_overlap_problems(frames.chip_samples(vdir, timing)[first.stem]["rows"])}
    assert kinds & {"chip-still-shown", "chip-shown-too-long"}, kinds
    other = re.sub(r'(<p class="chip" id="chip\d+" data-fact=")[^"]+"', r'\1f.not-this-value"', src)
    assert other != src
    first.write_text(other)
    kinds = {p["kind"] for p in frames.chip_overlap_problems(frames.chip_samples(vdir, timing)[first.stem]["rows"])}
    assert "chip-covers-text-at-rest" in kinds, kinds
    return out
