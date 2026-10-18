"""WP5: the narrated video projector (AC-5.1, AC-5.3, AC-5.6, AC-5.7, D20.11)."""
import json
import re
import shutil

from _util import SLICE
from selftest_support import NotRun
from ptk import errors, host, model, tts
from ptk.project import video
from ptk.verify import frames, media


def _built():
    vdir = SLICE / "build" / "video"
    if not (vdir / "composition" / "index.html").exists() or not (vdir / "timing.json").exists():
        raise NotRun(f"no built video at {vdir}; run `ptk build lessons/switch-fallthrough --only video,ive`")
    return vdir, json.loads((vdir / "timing.json").read_text())


# ---------------------------------------------------------------- AC-5.1

def test_per_scene_check():
    """One sub-composition per storyboard scene, and `hyperframes check` reports 0 errors, 0 warnings."""
    vdir, timing = _built()
    lesson = model.load(SLICE)
    comp = vdir / "composition"
    subs = sorted(p.stem for p in (comp / "compositions").glob("*.html"))
    assert subs == sorted(sc["id"] for sc in lesson.data["storyboard"]), subs
    host_page = (comp / "index.html").read_text()
    assert len(re.findall(r'data-composition-src="compositions/', host_page)) == len(subs)
    rnd = video.get_renderer("hyperframes")
    if not rnd.available():
        raise NotRun("pinned HyperFrames missing")
    chk = rnd.check(lesson, comp)
    assert chk["clean"], chk
    assert all(c == {"errors": 0, "warnings": 0} for c in chk["counts"].values()), chk["counts"]
    return {"sub_compositions": len(subs), "counts": chk["counts"]}


# ---------------------------------------------------------------- AC-5.3

def test_schedule_from_durations():
    """Cue lengths equal the measured segment durations within one frame, gaps follow the rule, and
    every scene holds its narration; changing one measured duration moves every later cue."""
    lesson = model.load(SLICE)
    segs = video.segments_of(lesson)
    measured = [{"id": s["id"], "seconds": 1.0 + 0.137 * i} for i, s in enumerate(segs)]
    timing = video.schedule(lesson, measured)
    frame = 1 / video.FPS
    dur = {m["id"]: m["seconds"] for m in measured}
    for c in timing["cues"]:
        assert abs((c["end"] - c["start"]) - dur[c["id"]]) <= frame + 1e-6, c
    for a, b in zip(timing["cues"], timing["cues"][1:]):
        gap = b["start"] - a["end"]
        assert gap >= video.GAP_IN - frame, (a["id"], b["id"], gap)
    for sc in timing["scenes"]:
        own = [c for c in timing["cues"] if c["scene"] == sc["id"]]
        assert sc["start"] <= own[0]["start"] and own[-1]["end"] <= sc["end"], sc["id"]
        spoken = sum(dur[c["id"]] for c in own) + video.GAP_IN * (len(own) - 1)
        span = own[-1]["end"] - own[0]["start"]
        assert abs(span - spoken) <= frame * len(own) + 1e-6, (sc["id"], span, spoken)
    longer = [dict(m) for m in measured]
    longer[0]["seconds"] += 0.4
    moved = video.schedule(lesson, longer)
    deltas = [round(b["start"] - a["start"], 3) for a, b in zip(timing["cues"], moved["cues"])]
    assert deltas[0] == 0 and all(abs(d - 0.4) <= frame for d in deltas[1:]), deltas
    out = {"synthetic": "ok"}
    # the built lesson: cue lengths against the trimmed TTS wavs actually on disk
    vdir = SLICE / "build" / "video"
    if (vdir / "timing.json").exists():
        built = json.loads((vdir / "timing.json").read_text())
        worst = 0.0
        for c in built["cues"]:
            wav = vdir / "work" / "tts" / f"{c['id']}.wav"
            if not wav.exists():
                raise NotRun(f"trimmed segment {wav.name} missing; rebuild the video")
            worst = max(worst, abs((c["end"] - c["start"]) - tts.probe_duration(wav)))
        assert worst <= frame + 1e-3, f"a cue differs from its measured audio by {worst:.3f} s"
        out["built_worst_cue_vs_audio"] = round(worst, 4)
    return out


# ---------------------------------------------------------------- AC-5.6

def _copy_video(vdir):
    tmp = host.make_tmp("scene-fixture-")
    dst = tmp / "video"
    shutil.copytree(vdir / "composition", dst / "composition")
    (dst / "work").mkdir()
    return tmp, dst


def test_scene_snapshots():
    """Snapshots at each scene's midpoint and settled point: no overflow, no text under 11 px, key nodes
    inside the frame, no empty output panel, and every output value paired with its mechanism (the
    step badge on the printing line, on the drawn path). Fixtures without the badges, or with an
    empty output card on screen, fail."""
    vdir, timing = _built()
    lesson = model.load(SLICE)
    g = frames.scene_layout_gate(lesson, vdir, timing, lesson.sha256())
    assert g["status"] == "passed", json.dumps(g["measured"]["problems"])[:2000]
    assert len(g["measured"]["snapshots"]) == 2 * len(timing["scenes"])
    # mechanism-pairing and empty-panel fixtures on a copy of the composition
    tmp, fx = _copy_video(vdir)
    try:
        sc5 = fx / "composition" / "compositions" / "sc5.html"
        sc5.write_text(sc5.read_text().replace('class="ostep', 'class="ostep-removed'))
        sc1 = fx / "composition" / "compositions" / "sc1.html"
        empty = ('<div class="outcard" data-key="output"><p class="outlabel" data-chrome="output_label">OUTPUT</p></div>'
                 '\n    <div class="sidebody">')
        sc1.write_text(sc1.read_text().replace('<div class="sidebody">', empty, 1))
        bad = frames.scene_layout_gate(lesson, fx, timing, lesson.sha256())
        kinds = {sid: {p["kind"] for p in probs} for sid, probs in bad["measured"]["problems"].items()}
        assert bad["status"] == "failed"
        assert "summary-without-mechanism" in kinds.get("sc5", set()), kinds
        assert "empty-panel" in kinds.get("sc1", set()), kinds
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return {"scenes": g["measured"]["scenes"], "fixture_failures": {k: sorted(v) for k, v in kinds.items()}}


def test_morph_frames_follow_the_explorer():
    """The program change is a diff morph: until `shown` the rows on screen are the old program's (the
    explorer's state), and a moving frame of a third program, or with dots off both paths, is rejected."""
    lo = {"state_id": "s3", "program": "p1", "path": [4, 5, 8, 9, 10, 11, 12, 16]}
    hi = {"state_id": "s4", "program": "p2", "path": [4, 5, 8, 9, 10, 17]}
    cue_list = [{"cue": "m1", "kind": "transition", "start": 0.0, "end": 1.0, "state": lo},
                {"cue": "m2", "kind": "state", "start": 1.0, "end": 2.0, "state": hi}]
    explorer = {("m1", 0.5): "s3", ("m2", 1.5): "s4"}

    def bad(frame):
        frame_at = {0.5: frame, 1.5: {"state": "s4", "program": "p2", "line": 17, "path": hi["path"], "output": []}}
        return frames.compare_pauses(cue_list, frame_at, explorer, lambda c: [c["start"] + 0.5])[1]

    assert not bad({"state": "moving", "program": "p1", "path": [], "output": []}), "morph start rejected"
    assert not bad({"state": "moving", "program": "p1", "path": [4, 5, 8], "output": []}), "new path drawing rejected"
    assert bad({"state": "moving", "program": "p2", "path": [4, 5], "output": []}), "new rows before the swap accepted"
    assert bad({"state": "moving", "program": "p3", "path": [], "output": []}), "a third program accepted"
    assert bad({"state": "moving", "program": "p1", "path": [4, 17, 11], "output": []}), "dots off both paths accepted"
    lesson = model.load(SLICE)
    measured = [{"id": s["id"], "seconds": 2.0} for s in video.segments_of(lesson)]
    t = video.schedule(lesson, measured)
    sc6 = next(s for s in t["scenes"] if s["id"] == "sc6")
    assert sc6["morph"] and sc6["start"] < sc6["reveal"] < sc6["shown"] < sc6["end"], sc6
    html = video.scene_html(lesson, sc6, 5, len(t["scenes"]), t)
    assert 'class="band plus"' in html and 'data-set="old"' in html and 'data-gone="1"' not in html
    sc7 = next(s for s in t["scenes"] if s["id"] == "sc7")
    assert sc7["morph"] and 'data-gone="1"' in video.scene_html(lesson, sc7, 6, len(t["scenes"]), t)
    return {"sc6": {k: sc6[k] for k in ("start", "reveal", "shown", "end")}}


def test_theme_option_and_renderer_interface():
    """The video takes the Atlas dark palette by default and the light paper theme on request; the
    projector talks to its renderer only through the Renderer interface (D20.11)."""
    lesson = model.load(SLICE)
    measured = [{"id": s["id"], "seconds": 2.0} for s in video.segments_of(lesson)]
    t = video.schedule(lesson, measured)
    from ptk import fonts
    toks = fonts.tokens()["themes"]
    for theme in ("dark", "light"):
        html = video.scene_html(lesson, t["scenes"][2], 2, len(t["scenes"]), {**t, "theme": theme})
        assert f'data-theme="{theme}"' in html and toks[theme]["ground"] in html and toks[theme]["note"] in html
    assert video.resolve_theme() == video.DEFAULT_THEME == "dark"
    try:
        video.resolve_theme("sepia")
        raise AssertionError("an unknown theme was accepted")
    except errors.ModelSchemaError:
        pass
    rnd = video.get_renderer()
    assert isinstance(rnd, video.Renderer) and rnd.name == "hyperframes" and rnd.frame_probe()
    for m in ("available", "write", "check", "render"):
        assert getattr(type(rnd), m) is not getattr(video.Renderer, m), f"{m} not implemented"
    try:
        video.get_renderer("manim")
        raise AssertionError("an unbuilt renderer was accepted")
    except errors.ModelSchemaError:
        pass
    return {"themes": ["dark", "light"], "renderers": sorted(video.RENDERERS)}


# ---------------------------------------------------------------- AC-5.7

class _Lesson:
    def __init__(self, value):
        self.value = value

    def fact(self, _fid):
        return {"value": self.value}


def _leak_dir(tmp, caps, chapters, transcript):
    def vtt(items):
        return "WEBVTT\n\n" + "".join(f"{i}\n{a} --> {b}\n{t}\n\n" for i, a, b, t in items)
    tmp.mkdir(parents=True, exist_ok=True)
    (tmp / "captions.vtt").write_text(vtt(caps))
    (tmp / "chapters.vtt").write_text(vtt(chapters))
    (tmp / "transcript.txt").write_text("\n".join(transcript))
    return tmp


def test_no_answer_leak_text():
    """M20 and review P2-5. A word answer leaks anywhere it is said; a numeric answer leaks only as the
    answer value in a sentence about the question's subject, never in code or line numbers."""
    vdir, timing = _built()
    lesson = model.load(SLICE)
    g = media.leak_gate(lesson, timing, vdir)
    assert g["status"] == "passed", g["measured"]["leaks"]
    # the leak rule, both ways
    subj = media.subject_terms("The byte is 0x42. What does the program print?")
    num = [{"kind": "number", "value": "66"}]
    leak = ["The program prints 66.", "It prints sixty-six.", "The output is 66 here.", "So the program prints 0x42."]
    clean = ["Line 66 calls printf.", "The program prints on line 66.", "`putchar(66)` is how the program prints it.",
             "The array has 66 slots.", "The program prints 67.", "Step 66 of the program prints nothing new."]
    got_leak = {s: media.leaks_in(s, num if "0x42" not in s else [{"kind": "number", "value": "66"}], subj) for s in leak}
    assert got_leak["So the program prints 0x42."] == ["66"], "0x42 is 66 and is the printed value"
    assert all(got_leak.values()), got_leak
    got_clean = {s: media.leaks_in(s, num, subj) for s in clean}
    assert not any(got_clean.values()), got_clean
    words = [{"kind": "words", "phrase": ["two"]}, {"kind": "words", "phrase": ["x", "2"]}]
    assert media.leaks_in("Case 2 runs puts.", words, subj) == [], "a digit is not the word answer two"
    assert media.leaks_in("It prints two.", words, subj) == ["two"]
    assert media.leaks_in("Then x = 2 holds.", words, subj) == ["x 2"]
    # the whole gate on fixtures: a numeric question answered in a caption, the transcript and a chapter
    q = {"prompt": "c holds 'B'. What does printf(\"%d\", c) print?", "answer_fact": "f.x"}
    tm = {"cues": [{"id": "a.0", "scene": "a", "start": 0.8, "end": 3.0, "text": "c holds the letter B."},
                   {"id": "b.0", "scene": "b", "start": 4.0, "end": 6.0, "text": "Pause and predict."},
                   {"id": "c.0", "scene": "c", "start": 7.0, "end": 9.0, "text": "It prints 66."}],
          "scenes": [{"id": "a", "start": 0.0, "end": 3.5, "reveal": 0.0, "title": "Setup"},
                     {"id": "b", "start": 3.5, "end": 6.5, "reveal": 3.5, "title": "Predict", "question": q},
                     {"id": "c", "start": 6.5, "end": 10.0, "reveal": 7.0, "title": "Answer"}]}

    def gate(caps, chapters, tx, cues=None):
        tmp = host.make_tmp("leak-")
        try:
            return media.leak_gate(_Lesson("66\n"), {**tm, "cues": cues or tm["cues"]},
                                   _leak_dir(tmp / "v", caps, chapters, tx))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    caps_ok = [(c["id"], "00:00:00.800", "00:00:03.000", c["text"]) for c in tm["cues"][:2]] + \
        [("c.0", "00:00:07.000", "00:00:09.000", "It prints 66.")]
    chaps_ok = [("a", "00:00:00.000", "00:00:03.500", "Setup"), ("b", "00:00:03.500", "00:00:06.500", "Predict"),
                ("c", "00:00:06.500", "00:00:10.000", "Answer")]
    tx_ok = ["T", "[00:00:00.000] Setup", "c holds the letter B.", "[00:00:03.500] Predict", "Pause and predict.",
             "[00:00:06.500] Answer", "It prints 66."]
    ok = gate(caps_ok, chaps_ok, tx_ok)
    assert ok["status"] == "passed", ok["measured"]["leaks"]
    early = [dict(c) for c in tm["cues"]]
    early[1]["text"] = "The program prints 66, but predict first."
    caps_bad = caps_ok[:1] + [("b.0", "00:00:04.000", "00:00:06.000", early[1]["text"])] + caps_ok[2:]
    tx_bad = tx_ok[:4] + [early[1]["text"]] + tx_ok[5:]
    bad = gate(caps_bad, chaps_ok, tx_bad, early)
    where = sorted({x["where"] for x in bad["measured"]["leaks"]})
    assert bad["status"] == "failed" and where == ["captions", "narration", "transcript"], bad["measured"]["leaks"]
    chap_bad = gate(caps_ok, chaps_ok[:2] + [("c", "00:00:06.500", "00:00:10.000", "The program prints 66")], tx_ok)
    assert chap_bad["status"] == "failed" and chap_bad["measured"]["leaks"][0]["where"] == "chapters"
    incidental = [dict(c) for c in tm["cues"]]
    incidental[1]["text"] = "Line 66 has the printf call; predict what the program prints."
    inc = gate(caps_ok[:1] + [("b.0", "00:00:04.000", "00:00:06.000", incidental[1]["text"])] + caps_ok[2:],
               chaps_ok, tx_ok[:4] + [incidental[1]["text"]] + tx_ok[5:], incidental)
    assert inc["status"] == "passed", inc["measured"]["leaks"]
    return {"built": g["measured"]["questions"], "leak_cases": len(leak), "clean_cases": len(clean)}
