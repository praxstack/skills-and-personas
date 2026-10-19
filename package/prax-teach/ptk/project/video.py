"""Narrated video projector: per-scene HyperFrames sub-compositions, batched Kokoro TTS,
schedule from measured durations, WebVTT captions + chapters, LUFS normalisation, sandboxed render, mux.

Timeline rule (AC-5.3, E17, D18.2):
    segment n starts after segment n-1 ends + gap (0.35 s in a scene, 0.8 s across scenes, a
    question scene included: explanation first, so the answer follows the question at the normal pace
    and no think pause is baked into the MP4); durations are measured from the trimmed audio.
    A scene's state change starts at its last segment's start (`reveal`) and is settled when its
    drawing ends (`shown`). The IVE uses `shown`, never a time inside the tween. A change of
    program starts MORPH_LEAD after the scene start with a diff of the two programs, then draws the
    new path; a recap of a state already shown on the same program is settled at the scene start
    (see plan_screen).

Renderer-neutral (D20.11): everything up to the timing is shared; a Renderer writes, checks and
renders the per-scene source. HyperFramesRenderer is the only backend today.

Outputs in build/video/: lesson.mp4, captions.vtt, chapters.vtt, transcript.txt, timing.json,
narration.wav, composition/ (index.html + compositions/<scene>.html), work/ (intermediates).
"""
import difflib
import json
import math
import os
import re
import shutil

from .. import errors, fonts, host, node, text, tts
from . import mech
from . import path as rail
from ..text import esc

FPS = 30
W, H = 1920, 1080
# No think gap (SPEC v1.4, AC-6.8): v2.1 held 3.8 s on a bar after each question. Now the answer scene follows
# at GAP_SCENE like any other; the IVE's practice mode pauses the player itself at the question
# (ive.question_plan), so no silence is baked into the MP4 for it.
LEAD, GAP_IN, GAP_SCENE, TAIL, SCENE_LEAD = 0.8, 0.35, 0.8, 1.6, 0.35
SETTLE = 0.5
MINUS = "\u2212"
KEYWORDS = {"int", "switch", "case", "break", "return", "void", "char", "default"}


def _frame(t):
    return round(round(t * FPS) / FPS, 4)


def segments_of(lesson):
    segs = []
    for sc in lesson.data["storyboard"]:
        for i, n in enumerate(sc["narration"]):
            said = n["text"]  # round 18: never hand-respelled; the lexicon makes the spoken form
            spoken = tts.apply_lexicon(said)
            segs.append({"id": f"{sc['id']}.{i}", "scene": sc["id"], "text": n["text"], "said": said, "spoken": spoken,
                         "claims": n["claims"]})
    return segs


def schedule(lesson, measured):
    """Cue and scene times from measured segment durations (AC-5.3)."""
    dur = {m["id"]: m["seconds"] for m in measured}
    segs = segments_of(lesson)
    t, prev_scene, cues = LEAD, None, []
    scenes = {sc["id"]: sc for sc in lesson.data["storyboard"]}
    for s in segs:
        if prev_scene is not None:
            t += GAP_IN if s["scene"] == prev_scene else GAP_SCENE
        start = _frame(t)
        end = _frame(start + dur[s["id"]])
        cues.append({**s, "start": start, "end": end, "seconds": dur[s["id"]]})
        t = end
        prev_scene = s["scene"]
    total = _frame(t + TAIL)
    out_scenes = []
    order = [sc["id"] for sc in lesson.data["storyboard"]]
    for i, sid in enumerate(order):
        sc_cues = [c for c in cues if c["scene"] == sid]
        start = 0.0 if i == 0 else _frame(sc_cues[0]["start"] - SCENE_LEAD)
        k = reveal_line(lesson, i)
        out_scenes.append({"id": sid, "title": scenes[sid]["title"], "state": scenes[sid]["state"], "start": start,
                           "reveal": sc_cues[k]["start"] if i else 0.0, "reveal_line": k,
                           "question": scenes[sid].get("question")})
    for i, s in enumerate(out_scenes):
        s["end"] = out_scenes[i + 1]["start"] if i + 1 < len(out_scenes) else total
        s["duration"] = round(s["end"] - s["start"], 4)
    plan_screen(lesson, out_scenes)
    return {"fps": FPS, "duration": total, "cues": cues, "scenes": out_scenes,
            "rule": "start(n) = end(n-1) + gap; durations measured from trimmed TTS audio; see plan_screen for "
                    "before/reveal/shown"}


def reveal_line(lesson, i):
    """The narration line at which scene i starts drawing its new state (round 18: values are shown when they
    are spoken). The first line that cites a claim stating a fact the new state shows for the first time;
    with no such line, the first line, so a change that states no value (the UB lane) appears with the
    sentence about it."""
    sb = lesson.data["storyboard"]
    sc = sb[i]
    if i == 0 or sb[i - 1]["state"] == sc["state"]:
        return len(sc["narration"]) - 1
    new = mech.shown_facts(lesson, sc["state"]) - mech.shown_facts(lesson, sb[i - 1]["state"])
    claims = lesson.by_id("claims")
    for k, n in enumerate(sc["narration"]):
        if any(set(claims[c].get("facts", [])) & new for c in n["claims"]):
            return k
    return 0


# ---------------------------------------------------------------- what is on screen when

SEG_RUN, SEG_JUMP, OUT_STEP = 0.32, 0.62, 0.12
DRAW_BUDGET = 0.7  # at most this share of the time left in a scene goes to drawing
MORPH = 1.25       # a change of program: the old code turns into the new code as a diff (see scene_html)
MORPH_LEAD = 0.4   # the morph starts once the scene title is in
FLIGHT = 0.75      # a returned value flies from its frame into the caller's slot before the panel changes


def draw_plan(lesson, before_sid, sid, budget=None):
    """The path segments a scene draws, in execution order, with offsets from the reveal (seconds).

    Same program: only the segments past the `before` state's path. New program: first the diff
    morph (MORPH seconds), then the whole path, first dot at the morph's end. Returns
    {"steps": [{"a", "b", "kind", "t0", "dur"}], "first": line or None, "first_at", "morph",
    "outputs_at": offset where new output values appear, "total": offset when everything is settled}.
    """
    cur = lesson.state(sid)["state"]
    old = lesson.state(before_sid)["state"] if before_sid else None
    same = old is not None and old["program"] == cur["program"]
    morph = MORPH if (old is not None and not same) else 0.0
    old_segs = {(a, b) for a, b, _k in rail.segments(old["path"])} if same else set()
    steps, t = [], morph
    first = None if same else (cur["path"][0] if cur["path"] else None)
    first_at = round(t, 3)
    if first is not None:
        t += 0.15
    for a, b, kind in rail.segments(cur["path"]):
        if (a, b) in old_segs:
            continue
        dur = SEG_JUMP if kind == "jump" else SEG_RUN
        steps.append({"a": a, "b": b, "kind": kind, "t0": round(t, 3), "dur": dur})
        t += dur
    # the highlight ends on the state's own line, even when the last segment to that line was drawn before
    end_line = steps[-1]["b"] if steps else (old["line"] if same else first)
    hl_to = cur["line"] if cur["line"] != end_line else None
    if hl_to is not None:
        t += 0.3
    new_out = [f for f in cur["output"] if not same or f not in old["output"]]
    outputs_at = round(t + 0.05, 3)
    # settled = the end of the last tween scene_html schedules (dots/tags +0.06, line colour +0.1,
    # the no-break pulse +0.33, the last output value outputs_at + (k-1) * step + 0.3)
    src = lesson.program_source(cur["program"]).split("\n")
    nob = rail.nobreak_after(src, cur["path"])
    ends = [st["t0"] + st["dur"] + (0.33 if st["a"] == nob else 0.1) for st in steps] + [t + 0.1, morph]
    if new_out:
        ends.append(outputs_at + (len(new_out) - 1) * OUT_STEP + 0.3)
    if morph:
        ends.append(outputs_at + 0.32)  # the old output's fade (scene_html) ends here
    if (lesson.data.get("figure") or {}).get("panel") and before_sid and before_sid != sid:
        # the panel's cross-fade (scene_html): 0.45 s in, then 0.3 s out (it ends at 0.75); after a returned value's flight
        # into its caller's slot (FLIGHT s) when the stack has one
        ends.append(0.75 + (FLIGHT if mech.flows(lesson, before_sid, sid) else 0.0))
    total = max(max(ends), SETTLE)
    # a short scene plays the same drawing faster (a nested timeline with timeScale 1/k), never cut off
    k = min(1.0, budget / total) if budget else 1.0
    return {"steps": steps, "first": first, "first_at": first_at, "morph": morph, "outputs_at": outputs_at,
            "total": round(total * k, 3), "k": round(k, 4), "hl_to": hl_to, "hl_at": round(outputs_at - 0.35, 3)}


def plan_screen(lesson, scenes):
    """The one owner of what the frame shows (review P1-3). Per scene it sets:

    before   the state on screen until `reveal` (the previous scene's state, or this scene's own);
    reveal   when this scene starts changing the frame;
    shown    when the new state is fully drawn (the IVE switches its cue here, D18.2);
    replay   False when the state appears settled at the scene start, with no drawing: the first
             scene, or a recap of a state already shown on the same program;
    morph    True for a change of program.

    A change of program is a diff, not a cut (WP5): from `reveal` the old program's rows turn into
    the new program's (deleted rows strike out, kept rows slide to their new line, added rows
    fade in), then the new path draws. Until `shown` the rows on screen still belong to the old
    program, and the explorer holds the old state (a transition cue); at `shown` the new
    program's own rows replace them, pixel for pixel, and both switch together. Both
    video.scene_html and ive.cues read these fields.
    """
    seen, prev = set(), None
    for i, s in enumerate(scenes):
        sid = s["state"]
        prog_change = i > 0 and lesson.state(prev)["state"]["program"] != lesson.state(sid)["state"]["program"]
        if i == 0 or sid == prev or (sid in seen and not prog_change):
            s.update(before=sid, reveal=s["start"], shown=s["start"], replay=False, morph=False, draw_total=0.0)
        else:
            reveal = _frame(s["start"] + MORPH_LEAD) if prog_change else s["reveal"]
            plan = draw_plan(lesson, prev, sid, budget=DRAW_BUDGET * (s["end"] - reveal))
            settled = math.ceil(round((reveal + plan["total"]) * FPS, 6)) / FPS  # first frame with nothing moving
            s.update(before=prev, reveal=reveal, shown=round(min(settled, s["end"] - 1 / FPS), 4),
                     replay=True, morph=prog_change, draw_total=plan["total"])
        seen.add(sid)
        prev = sid
    return scenes


# ---------------------------------------------------------------- audio

def assemble_audio(timing, measured, work, out_wav):
    ffmpeg = host.which("ffmpeg")
    wav = {m["id"]: m["wav"] for m in measured}
    inputs, filters, labels, t, n = [], [], [], 0.0, 0
    for c in timing["cues"]:
        gap = c["start"] - t
        if gap > 0.0005:
            filters.append(f"anullsrc=r=48000:cl=mono,atrim=duration={gap:.4f}[s{n}]")
            labels.append(f"[s{n}]")
            n += 1
        inputs += ["-i", str(wav[c["id"]])]
        idx = len(inputs) // 2 - 1
        # pad as well as trim: a cue's frame-rounded window can be a few ms longer than its clip, and those ms add
        # up over a lesson until the audio ends before the picture
        d = c['end'] - c['start']
        filters.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=mono,atrim=duration={d:.4f},"
                       f"apad=whole_dur={d:.4f}[a{n}]")
        labels.append(f"[a{n}]")
        n += 1
        t = c["end"]
    filters.append(f"anullsrc=r=48000:cl=mono,atrim=duration={timing['duration'] - t:.4f}[s{n}]")
    labels.append(f"[s{n}]")
    raw = work / "narration-raw.wav"
    graph = ";".join(filters) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=0:a=1[out]"
    host.run([ffmpeg, "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]", "-c:a", "pcm_s16le", raw],
             check=True, timeout=600)
    # Two-pass EBU R128 to -16 LUFS / -1.5 dBTP on the stereo upmix the MP4 carries.
    first = host.run([ffmpeg, "-hide_banner", "-i", raw, "-af",
                      "aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2.0:LRA=11:print_format=json", "-f", "null", "-"],
                     timeout=600)
    err = first.stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    af = (f"aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-2.0:LRA=11:measured_I={m['input_i']}:"
          f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
          f"offset={m['target_offset']}:linear=true")
    host.run([ffmpeg, "-v", "error", "-y", "-i", raw, "-af", af, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
              out_wav], check=True, timeout=600)
    return {"loudnorm_first_pass": m}


# ---------------------------------------------------------------- captions, chapters, transcript

def write_text_tracks(lesson, timing, out):
    lines = ["WEBVTT", "", f"NOTE {lesson.id}: cue times come from measured TTS segment durations.", ""]
    for c in timing["cues"]:
        lines += [c["id"], f"{text.vtt_time(c['start'])} --> {text.vtt_time(c['end'])}", c["text"], ""]
    (out / "captions.vtt").write_text("\n".join(lines))
    ch = ["WEBVTT", ""]
    meta = [";FFMETADATA1", f"title={lesson.data['title']}", ""]
    for s in timing["scenes"]:
        ch += [s["id"], f"{text.vtt_time(s['start'])} --> {text.vtt_time(s['end'])}", s["title"], ""]
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={int(round(s['start'] * 1000))}",
                 f"END={int(round(s['end'] * 1000))}", f"title={s['title']}", ""]
    (out / "chapters.vtt").write_text("\n".join(ch))
    (out / "work" / "chapters.ffmeta").write_text("\n".join(meta))
    tx = [lesson.data["title"], ""]
    for s in timing["scenes"]:
        tx.append(f"[{text.vtt_time(s['start'])}] {s['title']}")
        if s.get("question"):
            tx.append(s["question"]["prompt"])  # the transcript asks the question it then invites an answer to
        tx += [c["text"] for c in timing["cues"] if c["scene"] == s["id"]]
        tx.append("")
    (out / "transcript.txt").write_text("\n".join(tx))


# ---------------------------------------------------------------- composition

THEMES = ("dark", "light")
DEFAULT_THEME = "dark"  # the Neuron Atlas palette Prax approved (D20.1); `light` is the paper theme


def _state_view(lesson, sid):
    st = lesson.state(sid)["state"]
    facts = lesson.by_id("facts")
    return {"program": st["program"], "line": st["line"], "path": st.get("path", []),
            "output": [{"fact": f, "text": text.display(facts[f])} for f in st["output"]],
            "vars": st.get("vars", {})}


def _code_html(line_txt):
    out = []
    for tok in re.findall(r'"[^"]*"|[A-Za-z_]\w*|\s+|.', line_txt):
        if tok.startswith('"'):
            out.append(f'<span class="str">{esc(tok)}</span>')
        elif tok in KEYWORDS:
            out.append(f'<span class="kw">{esc(tok)}</span>')
        else:
            out.append(esc(tok))
    return "".join(out)


# Frame layout (1920 x 1080). Sized to the frame, not fixed: the code card and the side column
# both run from CODE_TOP to H - BOTTOM, and LINE_H is the card height over the longest body.
#
#  96                                   1156  1200                       1824
#  kicker / n of N ── title ───────────────────────────────────────────────    48..170
#  ┌ code card ───────────────────────────┐  ┌ output card (hidden until  ┐   212
#  │ 4 ● int n = 2;                       │  │ the first value) 1 two     │
#  │ 5 ●╮ switch (n) {                    │  └────────────────────────────┘
#  │ 6  │   case 1:             skipped   │  VARIABLES n = 2
#  │ 8 ◀╯   case 2:         enters here   │  │ note / question             │
#  │ 9 ●      puts("two");  (1)  no break │  │ (claim text)               │
#  └──────────────────────────────────────┘  │                             │   996
#  ─────────────────────────────────────────────────────── captured: clang ─   1020..1056
MX, CODE_TOP, BOTTOM = 96, 212, 84
CARD_W, SIDE_X, SIDE_W = 1060, 1200, 624
ROW_PAD = 28  # minimum, rows are centred
NUM_X, RAIL_X, SRC_X, BULGE = 58, 124, 170, 46
OUT_H, OUT_TOP = 84, 84


# B3 (AC-10.3): the stage. Every scene that shows the mechanism draws it, the code it runs and the output it prints
# as one figure under the title (data-role="mechanism"), so the mechanism carries the frame and every number on it is
# bound to a fact, a source line or an axis. Type sizes: teaching text >= 28 px, output never smaller than code.
#
#   hero (neuron)                         side (views, stack)                 path (switch, figure program)
#   kicker / title ───────────────────    kicker / title ──────── file        kicker / title ──────── file
#   ┌ panel 1776 x 520 ─────────────┐     ┌ panel 1090 x 874 ┐ ┌ code ┐       ┌ path figure ─────┐ ┌ code ┐
#   │                               │     │                  │ │ 662  │       │ 1120 x 874       │ │ 632  │
#   └───────────────────────────────┘     │                  │ └──────┘       │                  │ └──────┘
#   ┌ code 1052 ─────┐ ┌ output 700 ┐     │                  │ ┌ out  ┐       │                  │ ┌ out  ┐
#   └────────────────┘ └────────────┘     └──────────────────┘ └──────┘       └──────────────────┘ └──────┘
# A question scene puts the question under the title, over the panel's column, and the panel gives up that height.
# A switch scene on another program (the compare runs) keeps the classic code card, output and note.
SX0, SX1, STOP, SBOT = 48, 1872, 128, 1036
QH = 132  # the question block under the title: the prompt and its options


def _path_scene(lesson, sid_state):
    """A switch lesson's scene on its figure program once control has run a case (the state has printed): the path
    figure (AC-10.2 control-path) is the hero. Before that (the opening and the question) there is no path yet, and
    the program's code leads the frame."""
    fig = lesson.data.get("figure") or {}
    if fig.get("panel") or mech.panel_kind(lesson) != "control-path":
        return False
    st = lesson.state(sid_state)["state"]
    return st["program"] == fig.get("program") and bool(st["output"])


def _layout(lesson, scene=None):
    """The frame grid. Row height comes from the longest listing among the scenes that share this layout, so every
    such scene draws its code on the same rows (a morph turns rows into rows).

    None (classic): the code card (1060 wide) and the side column (output, variables, note), as drawn above; a
    switch lesson's scenes on its compare programs. hero, side and path: the stage drawn above.
    """
    panel = (lesson.data.get("figure") or {}).get("panel")
    if panel:
        mode = "side" if panel["kind"] == "stack" or panel["place"] == "side" else "hero"
    else:
        mode = "path" if scene is not None and _path_scene(lesson, scene["state"]) else None
    L = {"mode": mode, "code_x": MX, "code_top": CODE_TOP, "card_w": CARD_W, "side_x": SIDE_X, "side_w": SIDE_W,
         "num_x": NUM_X, "rail_x": RAIL_X, "src_x": SRC_X, "bulge": BULGE, "row_pad": ROW_PAD}
    if mode is None and scene is not None and mech.panel_kind(lesson) == "control-path" \
            and not lesson.state(scene["state"])["state"]["output"]:
        # B3: before control has run a case no tag is drawn beside the code, so the card is as wide as its rows and
        # the note or the question takes the rest of the frame
        L.update(card_w=760, side_x=MX + 760 + 48, side_w=W - MX - (MX + 760 + 48))
    if mode == "side" and panel["kind"] == "stack":
        # the stack: the column holds the stack and, under its last frame, the output; the code fills the right
        cx = 1186
        n_out = max(len(lesson.state(sc["state"])["state"]["output"]) for sc in lesson.data["storyboard"])
        L.update(code_x=cx, code_top=STOP, card_w=SX1 - cx, card_h=SBOT - STOP, side_x=SX0, side_w=cx - 24 - SX0,
                 side_top=STOP, side_h=SBOT - STOP, out_h=64 + -(-max(n_out, 2) // 2) * 58, line_cap=46,
                 panel_box=(SX0, STOP, cx - 24 - SX0, SBOT - STOP),
                 q_panel_box=(SX0, STOP + QH, cx - 24 - SX0, SBOT - STOP - QH), q_box=(SX0, 120, cx - 24 - SX0, QH),
                 num_x=40, rail_x=78, src_x=112, bulge=30, row_pad=14)
    elif mode == "side":
        # views: the panel's column is as wide as the drawing at its largest; the code and the output get the rest
        cx = 972
        n_out = max(len(lesson.state(sc["state"])["state"]["output"]) for sc in lesson.data["storyboard"])
        oh = 64 + max(n_out, 2) * 40
        ch = SBOT - STOP - 24 - oh
        L["font_cap"] = 18  # the panel's smallest printed value (the double's bits) stays at least this large
        L.update(code_x=cx, code_top=STOP, card_w=SX1 - cx, card_h=ch, side_x=cx, side_w=SX1 - cx, side_top=STOP + ch + 24,
                 side_h=oh, panel_box=(SX0, STOP, cx - 24 - SX0, SBOT - STOP),
                 q_panel_box=(SX0, STOP + QH, cx - 24 - SX0, SBOT - STOP - QH), q_box=(SX0, 120, cx - 24 - SX0, QH),
                 num_x=40, rail_x=78, src_x=112, bulge=30, row_pad=14)
    elif mode == "hero":
        # the output card sits left of the code: before the first value is printed the empty stretch is the card's
        # place plus what lies right of the code text, never one block across both (AC-10.3 empty region)
        top, ow = 668, 640
        L.update(code_x=SX0 + ow + 24, code_top=top, card_w=SX1 - SX0 - ow - 24, card_h=SBOT - top, side_x=SX0,
                 side_w=ow, side_top=top, side_h=SBOT - top, panel_box=(SX0, STOP, SX1 - SX0, top - STOP - 40),
                 q_panel_box=(SX0, STOP + QH, SX1 - SX0, top - STOP - 44 - QH), q_box=(SX0, 120, SX1 - SX0, QH),
                 num_x=40, rail_x=78, src_x=112, bulge=30, row_pad=10)
    elif mode == "path":
        # the right column: the code, the switch's controlling variable, then the output
        cx, vh = 1040, 64
        ch = SBOT - STOP - vh
        L.update(code_x=cx, code_top=STOP, card_w=SX1 - cx, card_h=ch, side_x=cx, side_w=SX1 - cx, line_cap=50,
                 side_top=SBOT, side_h=1, vars_top=STOP + ch + 12,
                 panel_box=(SX0, STOP, cx - 24 - SX0, SBOT - STOP),
                 q_panel_box=(SX0, STOP + QH, cx - 24 - SX0, SBOT - STOP - QH), q_box=(SX0, 120, cx - 24 - SX0, QH),
                 num_x=40, rail_x=78, src_x=112, bulge=30, row_pad=14)
    if mode:
        # the question: beside the scene title in the header band when it fits there (the mechanism keeps its whole
        # box), else under the title, over the mechanism's column, which gives up that height
        qs = [sc for sc in lesson.data["storyboard"] if sc.get("question")]
        disp = fonts.tokens()["themes"][DEFAULT_THEME]["type"]["display"]["font"]
        kick = fonts.width(fonts.tokens()["themes"][DEFAULT_THEME]["type"]["kicker"]["font"], 24,
                           text.kicker(lesson).upper(), bold=True) * 1.15 + 160  # its letter spacing and the n / N count
        tx = SX0 + max([fonts.width(disp, 48, sc["title"], bold=True) for sc in qs] + [kick]) + 64
        beside = max([_q_height(lesson, sc, SX1 - tx) for sc in qs] + [0])
        bx, by, bw, bh = L["panel_box"]
        if qs and beside <= STOP - 24:
            L.update(q_box=(tx, 16, SX1 - tx, beside), q_panel_box=L["panel_box"])
        else:
            qx, _qy, qw, _qh = L["q_box"]
            qh = max(max([_q_height(lesson, sc, qw) for sc in qs] + [0]), 96)
            L.update(q_box=(qx, 112, qw, qh), q_panel_box=(bx, max(by, 112 + qh + 16), bw, by + bh - max(by, 112 + qh + 16)))
    rows, longest, per_line = 1, 1, 1
    for sc in lesson.data["storyboard"]:
        if not panel and (mode == "path") != _path_scene(lesson, sc["state"]):
            continue  # a switch lesson's two layouts each size their own rows
        st = lesson.state(sc["state"])["state"]
        src = lesson.program_source(st["program"]).split("\n")
        first, last = rail.listing(lesson, st["program"])
        rows = max(rows, last - first + 1)
        longest = max(longest, max(len(src[n - 1].rstrip()) for n in range(first, last + 1)))
        made = rail.print_lines(src, st.get("path", []), [text.display(lesson.fact(f)) for f in st["output"]]) or []
        per_line = max([per_line] + [made.count(n) for n in made])
    L.setdefault("card_h", H - BOTTOM - L["code_top"])
    L.setdefault("side_top", L["code_top"])
    L.setdefault("side_h", L["card_h"])
    line_h = int(min((L["card_h"] - 2 * L["row_pad"]) // rows, L.get("line_cap", 999)))
    L["badge"] = int(min(40, line_h - 4))
    # the longest line, its output-step badges and the tag column must fit the card
    fit = (L["card_w"] - L["src_x"] - 40 - per_line * (L["badge"] + 6)) / (longest * 0.6)
    L.update(line_h=line_h, font=int(min(36, line_h * 0.64, fit, L.get("font_cap", 99))))
    max_out = max(len(lesson.state(sc["state"])["state"]["output"]) for sc in lesson.data["storyboard"])
    L["max_out"] = max(max_out, 1)
    return L


Q_PROMPT, Q_OPT = 32, 26  # px: the question's prompt (teaching text) and its options (values) in the film


def _q_height(lesson, sc, width):
    """The question block's height in a stage layout: the prompt wrapped to `width`, then its options as chips."""
    q = sc["question"]
    body = fonts.tokens()["themes"][DEFAULT_THEME]["type"]["body"]["font"]
    lines = len(fonts.wrap(body, Q_PROMPT, q["prompt"], width))
    rows, x = 1, 0
    for o in q.get("options") or []:
        w = fonts.width("mono", Q_OPT, o["text"]) + 2 * 16 + 4 + 14
        if x and x + w > width:
            rows, x = rows + 1, 0
        x += w
    return round(lines * Q_PROMPT * 1.2 + 12 + rows * (Q_OPT * 1.3 + 12 + 4) + (rows - 1) * 10 + 4)


def _film_sizes(lesson, L, pw, ph, width, states=None):
    """(sizes, scale) for a panel scaled into a pw x ph box: labels large enough that a 4-word label reads at
    >= 28 px, and code in the panel no larger than the code card's rows, so every output, label and value in the
    frame is at least as large as its code (AC-10.3)."""
    base = mech.SIZES["wide"]
    lab_scale = fonts.tokens()["themes"][DEFAULT_THEME]["type"]["label"].get("scale", 1)
    sizes, k = None, 1.0
    for _ in range(3):
        if states:
            from . import still
            svg = still.Svg("light", fonts.tokens())
            mh = mech.draw(svg, lesson, states[-1], 4, 4, width or mech.WIDTHS[("wide", mech.page_place(lesson))], "wide",
                           still.Flow(svg, {}), key=False, notes=False, states=states, sizes=sizes)
        else:
            mh = mech.max_height(lesson, "wide", notes=False, width=width, sizes=sizes)
        w = width or mech.WIDTHS[("wide", mech.page_place(lesson))]
        k = min(pw / (w + 8), ph / (mh + 8))
        head = max(base["label"], 29.0 / (lab_scale * k))
        code = min(base["code"], L["font"] / k)
        sizes = {"head": round(head, 2), "label": round(max(base["label"], code, L["font"] / (lab_scale * k)), 2),
                 "code": round(code, 2),
                 "chip": round(max(base["chip"], code * 1.08), 2)}
    return sizes, k


PATH_OUT_PX = 32  # a printed value on its code row in the path layout (the figure's code chips are drawn smaller)
STACK_W, VIEWS_W = 440, 520  # natural widths the film draws a stack column and a views panel at
FILM_CODE_PX = 20  # the largest code the film draws inside a panel (lanes, the gate's fmax): outputs are never smaller


MIN_SVG_PX = 11.2  # the frame layout gate reads an SVG text's own font size (AC-5.6: nothing under 11 px)


def _zoom(lesson, sid, pw, ph, w, states=None, extra=None, kmax=None):
    """(sizes, scale, natural height) of a side panel at state `sid` drawn `w` wide and fitted into pw x ph (B3): the
    camera fits the state, so a short stack or a value with few views is drawn large. Labels of four or more words
    read at >= 28 px; code in the panel reads at FILM_CODE_PX at most; labels at least as large as that code."""
    from . import still
    base = mech.SIZES["wide"]
    lab_scale = fonts.tokens()["themes"][DEFAULT_THEME]["type"]["label"].get("scale", 1)
    sizes, k, h = dict(extra or {}), 1.0, 0
    for _ in range(4):
        svg = still.Svg("light", fonts.tokens())
        h = mech.draw(svg, lesson, sid, 4, 4, w, "wide", still.Flow(svg, {}), key=False, notes=False, states=states,
                      sizes=sizes)
        k = min(pw / (w + 8), ph / (h + 8), kmax or 99)
        code = max(MIN_SVG_PX, min(base["code"], FILM_CODE_PX / k))
        sizes = {"head": round(max(base["label"], 29.0 / (lab_scale * k)), 2),
                 "label": round(max(base["label"], FILM_CODE_PX / (lab_scale * k)), 2), "code": round(code, 2),
                 "chip": round(max(base["chip"], code * 1.08), 2), "var": round(max(code, 26.0 / k, MIN_SVG_PX), 2),
                 "own_depth": True, **(extra or {})}
    return sizes, k, h


_SIDE_W = {}


def _side_width(lesson, pw, ph):
    """The one natural width a side panel is drawn at in every scene: the width whose least-filled state fills the
    most of the box's height, with every state drawn at 1.3x or more."""
    key = (lesson.id, lesson.sha256(), pw, ph)
    if key not in _SIDE_W:
        best = None
        for w in range(280, 761, 40):
            ks = [_zoom(lesson, st["id"], pw, ph, w)[1:] for st in lesson.data["trace"]]
            fill = min(k * (h + 8) / ph for k, h in ks)
            kmin = min(k for k, _h in ks)
            cand = (kmin >= 1.3, round(fill, 3), kmin, w)
            best = cand if best is None or cand > best else best
        _SIDE_W[key] = best[3]
    return _SIDE_W[key]


def _out_rect(L):
    """The output card in panel layouts (x, y, w, h) relative to the side column: under the panel (side) or the
    whole column (hero). The note is left to the narration and its captions; the panel carries the picture."""
    return (0, 0, L["side_w"], L.get("out_h", L["side_h"]))


def _out_grid(L, n):
    """(row height, rows per column, column width) for n output values in a panel layout's output card:
    one column when rows of at least 46 px fit, else two."""
    _x, _y, w, h = _out_rect(L)
    rows = n if (h - 72) / max(n, 1) >= 38 else -(-n // 2)
    cols = -(-n // rows)
    return min(OUT_H, int((h - 72) / rows)), rows, (w - 34) / cols


def _grid(lesson, program, L):
    """Rows of one program in the shared grid: lines, row index, top and centre y per line."""
    src = lesson.program_source(program).split("\n")
    first, last = rail.listing(lesson, program)
    lines = [(n, src[n - 1]) for n in range(first, last + 1)]
    LH = L["line_h"]
    pad = round((L["card_h"] - 4 - len(lines) * LH) / 2)  # rows centred in the card
    top = {n: pad + i * LH for i, (n, _) in enumerate(lines)}
    return {"src": src, "lines": lines, "top": top, "cy": {n: top[n] + LH / 2 for n in top}}


def _fit(font, s, width, height, lh, sizes):
    """The largest size whose wrapped lines fit the box (the last size if none does)."""
    for px in sizes:
        if len(fonts.wrap(font, px, s, width)) * px * lh <= height:
            return px
    return sizes[-1]


def _rgba(hexcol, a):
    h = hexcol.lstrip("#")
    return f"rgba({int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)},{a})"


def _theme(name):
    th = fonts.tokens()["themes"][name]
    fam = {k: f"'{v['family']}',{v['fallback']}" for k, v in fonts.tokens()["fonts"].items()}
    ty = {k: {"family": fam[v["font"]], "key": v["font"], "weight": v["weight"], "scale": v.get("scale", 1),
              "caps": v.get("caps", False)} for k, v in th["type"].items()}
    return th, ty


def _program_set(lesson, L, g, view, set_name, drawn_path, drawn_out, morph_to=None):
    """One program's rows, rail, tags and output-step badges, tagged data-set=<set_name>.

    drawn_path   lines already drawn when the scene starts (the rest carry class `new`);
    drawn_out    how many output values (and their step badges) are already shown;
    morph_to     for the old program in a morph: {old line: new line} for kept rows (data-to).
    """
    LH, font = L["line_h"], L["font"]
    RAIL_X, SRC_X, BULGE = L["rail_x"], L["src_x"], L["bulge"]
    src, top, cy = g["src"], g["top"], g["cy"]
    shown_lines = [n for n, _ in g["lines"]]
    run = [n for n in view["path"] if n in top]
    S = f'data-set="{set_name}"'
    rows = []
    for n, txt in g["lines"]:
        indent = len(txt) - len(txt.lstrip(" "))
        cls = "ln exec" if n in drawn_path else ("ln exec-new" if n in run else "ln")
        to = (morph_to or {}).get(n, n) if morph_to is None or n in morph_to else None
        extra = f' data-to="{to}"' if to is not None else ' data-gone="1"'
        moves = morph_to is not None and to is not None and to != n
        # only a row whose number changes cross-fades it; every other gutter number stays put (WP9 Part A)
        no2 = (f'<span class="no no2" data-label="line-number" data-axis="source-line" data-tick="{to}">{to}</span>'
               if moves else "")
        rows.append(f'<div class="{cls}" {S} data-line="{n}"{extra} style="top:{top[n]}px">'
                    f'<span class="no no1{" moves" if moves else ""}" data-label="line-number" data-axis="source-line" '
                    f'data-tick="{n}">{n}</span>{no2}'
                    f'<span class="src" data-code="{view["program"]}" data-src-line="{n}" '
                    f'style="padding-left:{indent * 0.6:.2f}em">'
                    f'{_code_html(txt.strip())}</span></div>')
    drawn_run = [n for n in drawn_path if n in top]
    old_segs = {(a, b) for a, b, _k in rail.segments(drawn_run)}
    segs, heads = [], []
    for a, b, kind in rail.segments(run):
        drawn = (a, b) in old_segs
        if kind == "run":
            d = f"M{RAIL_X},{cy[a]:.1f} L{RAIL_X},{cy[b]:.1f}"
        else:
            d = (f"M{RAIL_X},{cy[a]:.1f} C{RAIL_X - BULGE},{cy[a]:.1f} {RAIL_X - BULGE},{cy[b]:.1f} "
                 f"{RAIL_X - 9},{cy[b]:.1f}")
            heads.append(f'<path class="head{"" if drawn else " new"}" {S} data-seg="{a}-{b}" '
                         f'd="M{RAIL_X - 24},{cy[b] - 10:.1f} L{RAIL_X - 6},{cy[b]:.1f} L{RAIL_X - 24},{cy[b] + 10:.1f} Z"/>')
        segs.append(f'<path class="seg{"" if drawn else " new"}" {S} data-seg="{a}-{b}" data-kind="{kind}" pathLength="1" d="{d}"/>')
    dots = [f'<circle class="dot{"" if n in drawn_path else " new"}" {S} data-line="{n}" cx="{RAIL_X}" cy="{cy[n]:.1f}" r="8"/>'
            for n in dict.fromkeys(run)]  # one dot per line, however often the path passes it
    svg = (f'<svg class="rail" {S} viewBox="0 0 {L["card_w"] - 4} {L["card_h"] - 4}" aria-hidden="true">'
           f'{"".join(segs)}{"".join(heads)}{"".join(dots)}</svg>')
    tags = []
    for n, key, tone in rail.tags(src, run, shown_lines):
        on = any(a < n < b for a, b in old_segs) if key == "skipped_label" else n in drawn_path
        tags.append(f'<p class="tag {tone}{"" if on else " new"}" {S} data-line="{n}" data-chrome="{key}" '
                    f'style="top:{top[n]}px">{esc(text.ui(key))}</p>')
    nob = rail.nobreak_after(src, run)
    if nob:
        on = nob in drawn_path and (nob + 1) in drawn_path
        tags.append(f'<p class="badge nobreak{"" if on else " new"}" {S} data-after="{nob}" data-chrome="no_break" '
                    f'style="top:{(top[nob + 1] + (LH - 40) / 2) if L["mode"] == "path" and nob + 1 in top else top[nob] + LH / 2 + 4:.0f}px">'
                    f'{esc(text.ui("no_break"))}</p>')
    steps, out_xy = [], {}
    made = rail.print_lines(src, view["path"], [o["text"] for o in view["output"]]) or []
    for k, n in enumerate(made, 1):
        txt = src[n - 1]
        indent = len(txt) - len(txt.lstrip(" "))
        # a line that printed several values (a recursive call, a loop) carries one badge per value, side by side
        B = L["badge"]
        x = SRC_X + indent * 0.6 * font + fonts.width("mono", font, txt.strip()) + B * 0.55 + made[:k - 1].count(n) * (B + 6)
        steps.append(f'<p class="ostep{"" if k <= drawn_out else " new"}" {S} data-step="{k}" data-line="{n}" '
                     f'data-label="output-step" data-axis="output-step" data-tick="{k}" '
                     f'style="left:{x:.0f}px;top:{top[n] + (LH - B) / 2:.0f}px">{k}</p>')
        out_xy[k] = (x + B + 18 + (made[k:].count(n)) * (B + 6), top[n])  # after the line's last badge
    return {"rows": f'<div class="rows" {S}>{"".join(rows)}</div>', "rail": svg, "tags": "".join(tags),
            "steps": "".join(steps), "run": run, "nob": nob, "tag_list": rail.tags(src, run, shown_lines),
            "out_xy": out_xy}


def scene_html(lesson, scene, index, count, timing):
    theme = timing.get("theme", DEFAULT_THEME)
    t, ty = _theme(theme)
    frame = t["frame"]
    L = _layout(lesson, scene)
    LH = L["line_h"]
    sid = scene["id"]
    cur = _state_view(lesson, scene["state"])
    replay = scene["replay"]
    before = _state_view(lesson, scene["before"]) if replay else cur
    morph = bool(scene.get("morph")) and replay
    same_prog = before["program"] == cur["program"]
    plan = draw_plan(lesson, scene["before"], scene["state"],
                     budget=DRAW_BUDGET * (scene["end"] - scene["reveal"])) if replay else \
        {"steps": [], "first": None, "first_at": 0.0, "morph": 0.0, "outputs_at": 0.0, "total": 0.0, "k": 1.0}
    gc = _grid(lesson, cur["program"], L)
    claims = lesson.by_id("claims")
    sb = next(x for x in lesson.data["storyboard"] if x["id"] == sid)
    note_claim = sb["narration"][0]["claims"][0]
    reveal = round(scene["reveal"] - scene["start"], 3)
    swap = round(scene["shown"] - scene["start"], 4)
    # the note states the new program's behaviour, so at a change of program it waits until the diff
    # morph is complete (WP6); otherwise it fades in with the title
    note_at = reveal + MORPH * plan["k"] if morph else 0.05

    # --- code card: one program set, or two for a morph (old rows turn into new rows, then swap)
    morph_html, morph_js = "", []
    if morph:
        go = _grid(lesson, before["program"], L)
        old_lines = [txt.strip() for _n, txt in go["lines"]]
        new_lines = [txt.strip() for _n, txt in gc["lines"]]
        sm = difflib.SequenceMatcher(a=old_lines, b=new_lines, autojunk=False)
        keep, added, removed = {}, [], []
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                for k in range(i2 - i1):
                    keep[go["lines"][i1 + k][0]] = gc["lines"][j1 + k][0]
            else:
                removed += [go["lines"][i][0] for i in range(i1, i2)]
                added += [gc["lines"][j][0] for j in range(j1, j2)]
        old = _program_set(lesson, L, go, before, "old", before["path"], len(before["output"]), morph_to=keep)
        new = _program_set(lesson, L, gc, cur, "cur", [], 0)
        new["rows"] = new["rows"].replace('class="rows"', 'class="rows hidden"', 1)
        ghosts, bands = [], []
        for n in added:  # the new program's added rows, drawn in the old set until the swap
            txt = gc["src"][n - 1]
            indent = len(txt) - len(txt.lstrip(" "))
            ghosts.append(f'<div class="ln add" data-to="{n}" style="top:{gc["top"][n]}px">'
                          f'<span class="no no2" data-label="line-number">{n}</span>'
                          f'<span class="src" data-code="{cur["program"]}" style="padding-left:{indent * 0.6:.2f}em">'
                          f'{_code_html(txt.strip())}</span></div>')
            bands.append(f'<div class="band plus" data-diff="added" style="top:{gc["top"][n]}px"></div>')
        for n in removed:
            bands.append(f'<div class="band minus" data-diff="removed" style="top:{go["top"][n]}px">'
                         f'<div class="strike"></div></div>')
        old["rows"] = old["rows"][:-len("</div>")] + "".join(ghosts) + "</div>"
        morph_html = "".join(bands)
        sets = [old, new]
        hl_from = go["cy"].get(before["line"], LH / 2)
        # the morph, on the drawing timeline (offsets from the reveal)
        O = "[data-set=\"old\"]"
        morph_js += [
            # the old path's lines and tags go; its dots and output-step badges stay with their rows (they pair the
            # output, which stays on screen through the diff, with the lines that printed it) until the diff ends
            f"d.to(q('.seg{O}, .head{O}, .badge{O}'), {{ opacity: 0, duration: 0.3, ease: 'power1.out' }}, 0);",
            # the old rows' tags stay beside their rows (they slide with them) until the new path starts, so the
            # code card never stands half empty mid-diff (B3, AC-10.3 pixel check)
            f"d.to(q('.tag{O}'), {{ opacity: 0, duration: 0.25 }}, {MORPH - 0.25:.2f});",
            f"d.to(q('.hl'), {{ opacity: 0, duration: 0.25 }}, 0);",
            # the output, the gutter and the file name stay on screen through the diff (WP9 Part A)
            f"d.fromTo(q('.band.minus'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.05);",
            f"d.fromTo(q('.band.minus .strike'), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.25, ease: 'power2.out' }}, 0.08);",
            f"d.to(q('.ln[data-gone]'), {{ color: '{t['correction']}', duration: 0.2 }}, 0.05);",
            # a removed row fades while the rows below close over it, so no hole opens
            f"d.to(q('.ln[data-gone], .band.minus'), {{ opacity: 0, duration: 0.6, ease: 'none' }}, 0.45);",
            *[f"d.to(q('.tag{O}[data-line=\"{n}\"]'), {{ opacity: 0, duration: 0.6, ease: 'none' }}, 0.45);" for n in removed],
            f"d.to(q('.ln{O}[data-to]'), {{ color: '{t['label']}', duration: 0.3 }}, 0.45);",
            f"d.to(q('.ln{O} .no1.moves'), {{ opacity: 0, duration: 0.3 }}, 0.45);",
        ]
        for n_old, n_new in keep.items():
            dy = gc["top"][n_new] - go["top"][n_old]
            if abs(dy) > 0.01:
                morph_js.append(f"d.to(q('.ln{O}[data-line=\"{n_old}\"], .dot{O}[data-line=\"{n_old}\"], "
                                f".ostep{O}[data-line=\"{n_old}\"], .tag{O}[data-line=\"{n_old}\"]'), "
                                f"{{ y: {dy:.1f}, duration: 0.6, ease: 'power2.inOut' }}, 0.45);")
        morph_js += [
            # a moving row's number cross-fades while it slides; an added row fills its slot as the slot opens
            f"d.fromTo(q('.ln{O} .no2'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, 0.45);",
            f"d.fromTo(q('.ln.add'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6, ease: 'power2.out' }}, 0.45);",
            f"d.fromTo(q('.ln.add .src'), {{ x: 18 }}, {{ x: 0, duration: 0.6, ease: 'power2.out' }}, 0.45);",
            f"d.to(q('.file[data-set=\"old\"]'), {{ opacity: 0, duration: 0.2 }}, 0.85);",
            f"d.fromTo(q('.file[data-set=\"cur\"]'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.85);",
            f"d.fromTo(q('.band.plus'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.45 }}, 0.45);",
            # the diff is done: the old output no longer matches the code on screen, so it dims with its markers
            # the old output's dots and badges pair it with its lines (D20.5) until it cross-fades out with them
            f"d.to(q('.dot{O}, .ostep{O}'), {{ opacity: 0, duration: 0.15 }}, {plan['outputs_at'] + 0.16:.3f});",
            # the old output stays fully shown until the new output cross-fades over it (r17 morph-stable rule)
            f"d.set(q('.hl'), {{ y: {gc['cy'][plan['first']] - LH / 2 if plan['first'] else 0:.1f} }}, {MORPH - 0.05});",
            f"d.to(q('.hl'), {{ opacity: 1, duration: 0.2 }}, {MORPH - 0.05});",
        ]
    else:
        drawn = before["path"] if (replay and same_prog) else ([] if replay else cur["path"])
        drawn_out = len(before["output"]) if (replay and same_prog) else (0 if replay else len(cur["output"]))
        sets = [_program_set(lesson, L, gc, cur, "cur", drawn, drawn_out)]
        if not replay:
            hl_line = cur["line"]
        elif same_prog:
            hl_line = before["line"]
        else:
            hl_line = plan["first"] or cur["line"]
        hl_from = gc["cy"].get(hl_line, LH / 2)
    curset = sets[-1]
    C = "[data-set=\"cur\"]"

    # --- side column: output (hidden until the first value), variables, note or question
    before_out = before["output"] if (replay and (same_prog or morph)) else ([] if replay else cur["output"])
    has_out = bool(cur["output"] or before_out)
    mode = L["mode"]
    grow = has_out and not before_out and mode is None  # the output card appears with this scene's first value
    if mode is None:
        out_h = OUT_TOP + L["max_out"] * OUT_H + 20
        place = lambda k: (34, OUT_TOP + (k - 1) * OUT_H)  # noqa: E731
        val_px = None
    else:
        out_h = _out_rect(L)[3]
        oh, per_col, col_w = _out_grid(L, L["max_out"])
        place = lambda k: (34 + ((k - 1) // per_col) * col_w, 64 + ((k - 1) % per_col) * oh)  # noqa: E731
        vt_ = ty["value"]
        longest = max([len(text.display(lesson.fact(f))) for sc in lesson.data["storyboard"]
                       for f in lesson.state(sc["state"])["state"]["output"]] + [1])
        val_px = int(min(oh * 0.66, 52, (col_w - 34 - 58 - 20) / (longest * 0.6)))
    shift = out_h + 30 if has_out and mode is None else 0
    outs = []

    def out_div(cls, set_name, k, o):
        x_, y_ = place(k)
        size = f";font-size:{val_px}px;line-height:{oh}px;height:{oh}px" if val_px else ""
        return (f'<div class="{cls}" data-set="{set_name}" data-step="{k}" style="left:{x_:.0f}px;top:{y_}px{size}">'
                f'<span class="step" data-label="output-step" data-axis="output-step" data-tick="{k}">{k}</span>'
                f'<span class="val" data-fact="{esc(o["fact"])}">{esc(o["text"])}</span></div>')
    for k, o in enumerate(before_out if morph else [], 1):
        outs.append(out_div("out", "old", k, o))
    prev_out = {o["fact"] for o in before_out} if not morph else set()
    for k, o in enumerate(cur["output"], 1):
        outs.append(out_div("out" + ("" if o["fact"] in prev_out else " out-new"), "cur", k, o))
    outcard = (f'<div class="outcard" data-key="output"><p class="outlabel" data-chrome="output_label">'
               f'{esc(text.ui("output_label").upper())}</p>{"".join(outs)}</div>') if has_out else ""
    inline_outs = ""
    if mode == "path":
        # B3: in the path layout each printed value stands on the code row that printed it, after its step badge,
        # as the path figure shows it; the code column runs the frame's full height and needs no output card
        outcard = ""
        oset = {s_["out_xy"].get(1) and "x" for s_ in sets}
        del oset
        ipx = PATH_OUT_PX

        def in_div(cls, set_name, k, o, xy):
            return (f'<div class="{cls}" data-set="{set_name}" data-step="{k}" style="left:{xy[0]:.0f}px;top:{xy[1]}px;'
                    f'font-size:{ipx}px;line-height:{LH}px;height:{LH}px">'
                    f'<span class="val" data-fact="{esc(o["fact"])}">{esc(o["text"])}</span></div>')
        if morph:
            for k, o in enumerate(before_out, 1):
                if k in sets[0]["out_xy"]:
                    inline_outs += in_div("out", "old", k, o, sets[0]["out_xy"][k])
        for k, o in enumerate(cur["output"], 1):
            if k in sets[-1]["out_xy"]:
                inline_outs += in_div("out" + ("" if o["fact"] in prev_out else " out-new"), "cur", k, o, sets[-1]["out_xy"][k])
    # in a panel lesson's question scene the panel steps up to make room for the question card under it; code
    # and output stay, so the frame still shows the whole state
    vars_html = " ".join(f'<span data-code="{cur["program"]}">{esc(k)} = {esc(v)}</span>' for k, v in cur["vars"].items())
    q = scene.get("question")
    panel_top = shift + 70
    panel_w = L["side_w"]
    panel_h = L["card_h"] - panel_top
    nt = ty["note"]
    if q and mode:
        # a stage layout: the question under the title, over the mechanism's column (the scene title names it)
        opts = "".join(f'<p class="qopt" data-option="{esc(sid)}.{k}">{esc(o["text"])}</p>'
                       for k, o in enumerate(q.get("options") or []))
        side = (f'<div class="qhead" data-key="question"><p class="qtext" data-question="{esc(sid)}">{esc(q["prompt"])}</p>'
                f'<div class="qopts">{opts}</div></div>')
    elif q:
        # the question and its options, as in the Q&A and the IVE; the answer scene follows at the normal pace
        opts = "".join(f'<p class="qopt" data-option="{esc(sid)}.{k}">{esc(o["text"])}</p>'
                       for k, o in enumerate(q.get("options") or []))
        side = (f'<div class="panel qcard" data-key="question"><p class="qlabel" data-chrome="question_label">'
                f'{esc(text.ui("question_label"))}</p><p class="qtext" data-question="{esc(sid)}">{esc(q["prompt"])}</p>'
                f'<div class="qopts">{opts}</div></div>')
    elif mode is None:
        # B3: the note as large as fills about two thirds of its column (it sits centred there, so no empty half
        # opens beside the code)
        sizes = tuple(round(x * nt["scale"]) for x in (96, 88, 80, 72, 64, 58, 52, 48, 44))
        note_px = _fit(nt["key"], claims[note_claim]["text"], panel_w - 84, (panel_h - 76) * 0.66, 1.18, sizes)
        side = (f'<div class="panel notecard" data-key="note"><p class="note" data-claim="{esc(note_claim)}" '
                f'style="font-size:{note_px}px">{esc(claims[note_claim]["text"])}</p></div>')
    elif mode == "path" and morph:
        # a change of program in the path layout (the recap returns to the figure's program): the note states the
        # new program's behaviour once the diff is complete, in the header band where the change card stood (WP6)
        qx_ = L["q_box"][0]
        npx = _fit(nt["key"], claims[note_claim]["text"], SX1 - qx_ - 24, STOP - 24, 1.18, (34, 32, 30, 28))
        side = (f'<div class="panel notecard pnote" data-key="note"><p class="note" data-claim="{esc(note_claim)}" '
                f'style="font-size:{npx}px;line-height:1.18">{esc(claims[note_claim]["text"])}</p></div>')
    else:
        side = ""
    if morph and mode in (None, "path"):
        # while the program changes, the note column says what changes (the note itself states the new
        # program's behaviour, so it waits for the diff to finish); the path layout shows it in the header band
        fo, fn = lesson.program(before["program"])["path"].split("/")[-1], lesson.program(cur["program"])["path"].split("/")[-1]
        diff_rows = "".join(f'<p class="dl {k}"><span class="mark" data-label="diff-mark">{"+" if k == "plus" else MINUS}</span>'
                            f'<span data-code="{pid}">{esc(src_[n - 1].strip())}</span></p>'
                            for k, ns, src_, pid in (("minus", removed, go["src"], before["program"]), ("plus", added, gc["src"], cur["program"]))
                            for n in ns)
        side += (f'<div class="panel changecard{" pchange" if mode == "path" else ""}"><p class="qlabel" data-chrome="morph_label">{esc(text.ui("morph_label"))}</p>'
                 f'<p class="files" data-chrome="morph_files">{esc(text.ui("morph_files", program=fo, file=fn))}</p>{diff_rows}</div>')
    # --- the mechanism panel: the state before this scene, with this scene's state faded in over it
    mech_html = ""
    film_k = 1.0
    stack_out = None
    if mode == "path":
        # the path through the switch (AC-10.2 control-path), the still's figure, as the hero: drawn at half the box
        # and scaled 2x, its rows spread to the box's height
        px, py, pw, ph = L["q_panel_box"] if q else L["panel_box"]
        PK = 2.0
        fit = 'preserveAspectRatio="xMidYMid meet"'
        kw = dict(width=round(pw / PK - 8), fit_h=round(ph / PK - 8), height=round(ph / PK - 8), notes=False, mark=False,
                  kind="control-path")
        sizes = None
        for _ in range(3):  # the figure's own scale in its box: its 4-word heading reads at >= 28 px
            from . import still
            _svg = still.Svg("light", fonts.tokens())
            hh = mech.draw(_svg, lesson, scene["state"], 4, 4, kw["width"], "wide", still.Flow(_svg, {}), key=False,
                           notes=False, kind="control-path", fit_h=kw["fit_h"], sizes=sizes)
            k_ = min(pw / (kw["width"] + 8), ph / (max(hh, kw["height"]) + 8))
            sizes = {"head": round(max(mech.SIZES["wide"]["label"], 29.0 / (1.04 * k_)), 2),
                     "code": round(min(mech.SIZES["wide"]["code"], (PATH_OUT_PX - 2) / (1.2 * k_)), 2)}
        kw["sizes"] = sizes
        layers, _f, _c = mech.svg_fragment(lesson, scene["state"], "wide", theme, attrs=f'class="mlayer mcur" {fit}', **kw)
        if replay and scene["before"] != scene["state"]:
            # the previous scene's path (a compare program's own figure when the recap returns from it) until the
            # reveal, so the frame shows the state the IVE says is on screen
            bef_svg, _f, _c = mech.svg_fragment(lesson, scene["before"], "wide", theme,
                                                attrs=f'class="mlayer mbefore" data-layout-allow-overlap="" {fit}', **kw)
            layers = bef_svg + layers
        mech_html = f'<div class="mechbox" data-key="panel">{layers}</div>'
    elif mode == "side":
        px, py, pw, ph = L["q_panel_box"] if q else L["panel_box"]
        recap = sb.get("view") == "summary" and lesson.data["figure"]["panel"]["kind"] == "stack"
        fit = 'preserveAspectRatio="xMidYMin meet"'
        st_ = lesson.data["figure"]["states"] if recap else None
        stack = lesson.data["figure"]["panel"]["kind"] == "stack"
        if stack:
            # the camera fits the stack at this state (a short stack is drawn large) over the output it has printed
            pw_ = STACK_W
            kmax = (val_px or 30) / MIN_SVG_PX  # code in the panel never larger than the printed values
            per_col_ = _out_grid(L, L["max_out"])[1]
            out_need = lambda sid_: 64 + min(per_col_, max(1, len(lesson.state(sid_)["state"]["output"]))) * 58 + 16  # noqa: E731
            avail = lambda sid_: ph - 24 - out_need(sid_)  # noqa: E731
            sizes, film_k, h1 = _zoom(lesson, scene["state"], pw, avail(scene["state"]), pw_, states=st_, kmax=kmax)
        else:
            # every lane on screen from the start (its value fades in when it prints); the camera fits the state
            pw_ = VIEWS_W
            kmax = (val_px or 30) / MIN_SVG_PX
            avail = lambda sid_: ph  # noqa: E731
            sizes, film_k, h1 = _zoom(lesson, scene["state"], pw, ph, pw_, extra={"pending": True}, kmax=kmax)
        # each layer's own box: the state's fit, centred across the column (the camera fits the state)
        lbox = lambda k_, h_: (f'style="left:{(pw - (pw_ + 8) * k_) / 2:.1f}px;width:{(pw_ + 8) * k_:.1f}px;'  # noqa: E731
                               f'height:{(h_ + 8) * k_:.1f}px"')
        cur_svg, _f, _c = mech.svg_fragment(lesson, scene["state"], "wide", theme,
                                            attrs=f'class="mlayer mcur" {fit} {lbox(film_k, h1)}', notes=False, states=st_,
                                            mark=False, width=pw_, sizes=sizes)
        layers = cur_svg
        has_before = replay and scene["before"] != scene["state"]
        bsizes, k0 = sizes, film_k
        if has_before:
            bsizes, k0, _h0 = _zoom(lesson, scene["before"], pw, avail(scene["before"]), pw_,
                                    extra=None if stack else {"pending": True}, kmax=kmax)
            bef_svg, _f, _c = mech.svg_fragment(lesson, scene["before"], "wide", theme,
                                                attrs=f'class="mlayer mbefore" data-layout-allow-overlap="" {fit} '
                                                f'{lbox(k0, _h0)}', notes=False, width=pw_, mark=False, sizes=bsizes)
            layers = bef_svg + cur_svg
        if stack:
            # the output stands on the column's floor and grows upward as lines are printed
            n0_ = out_need(scene["before"] if has_before else scene["state"])
            stack_out = (py + ph - n0_, py + ph - out_need(scene["state"]), n0_, out_need(scene["state"]))
        chips = ""
        fl = mech.flows(lesson, scene["before"], scene["state"]) if has_before else []
        if fl:
            A0 = mech.stack_anchors(lesson, scene["before"], "wide", pw_, sizes=bsizes)
            A1 = mech.stack_anchors(lesson, scene["state"], "wide", pw_, sizes=sizes)
            ox0, ox1 = (pw - (pw_ + 8) * k0) / 2, (pw - (pw_ + 8) * film_k) / 2
            for n_, (i, j, fid) in enumerate(fl):
                if i not in A0["rets"] or j not in A1["slots"]:
                    continue
                x0, y0 = A0["rets"][i]
                x1, y1 = A1["slots"][j]
                fpx = round({**mech.SIZES["wide"], **bsizes}["value"] * k0, 1)
                chips += (f'<p class="chip" id="chip{n_}" data-fact="{esc(fid)}" data-layout-allow-overlap="" '
                          f'style="left:{ox0 + x0 * k0:.1f}px;top:{y0 * k0:.1f}px;font-size:{fpx}px">'
                          f'{esc(text.display(lesson.fact(fid)))}</p>')
                dx, dy = ox1 + x1 * film_k - ox0 - x0 * k0, y1 * film_k - y0 * k0
                # the value leaves its frame, swings out to the right and lands in the caller's slot
                morph_js.append(f"d.set(q('#chip{n_}'), {{ xPercent: -50, yPercent: -50 }}, 0);")
                morph_js.append(f"d.fromTo(q('#chip{n_}'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, 0);")
                morph_js.append(f"d.to(q('#chip{n_}'), {{ x: {dx:.1f}, duration: {FLIGHT - 0.1}, ease: 'power1.inOut' }}, 0.1);")
                morph_js.append(f"d.to(q('#chip{n_}'), {{ y: {dy:.1f}, duration: {FLIGHT - 0.1}, ease: 'back.in(1.4)' }}, 0.1);")
                morph_js.append(f"d.to(q('#chip{n_}'), {{ opacity: 0, duration: 0.2 }}, {FLIGHT + 0.35});")
        mech_html = f'<div class="mechbox" data-key="panel">{layers}{chips}</div>'
    elif mode:
        px, py, pw, ph = L["q_panel_box"] if q else L["panel_box"]
        pw_ = None
        recap = sb.get("view") == "summary" and lesson.data["figure"]["panel"]["kind"] == "stack"
        sizes, film_k = _film_sizes(lesson, L, pw, ph, pw_, states=lesson.data["figure"]["states"] if recap else None)
        mh = mech.max_height(lesson, "wide", notes=False, width=pw_, sizes=sizes)
        fit = 'preserveAspectRatio="xMidYMin meet"'
        if recap:
            # a summary of the stack is the whole run, step by step (the still's strip), not the last state alone
            cur_svg, _f, _c = mech.svg_fragment(lesson, scene["state"], "wide", theme, attrs=f'class="mlayer mcur" {fit}',
                                                notes=False, states=lesson.data["figure"]["states"], mark=False,
                                                width=pw_, sizes=sizes)
        else:
            cur_svg, _f, _c = mech.svg_fragment(lesson, scene["state"], "wide", theme, attrs=f'class="mlayer mcur" {fit}',
                                                height=mh, notes=False, width=pw_, mark=False, sizes=sizes)
        layers = cur_svg
        if replay and scene["before"] != scene["state"]:
            bef_svg, _f, _c = mech.svg_fragment(lesson, scene["before"], "wide", theme, attrs=f'class="mlayer mbefore" data-layout-allow-overlap="" {fit}',
                                                height=mh, notes=False, width=pw_, mark=False, sizes=sizes)
            layers = bef_svg + cur_svg
        chips = ""
        if replay and scene["before"] != scene["state"]:
            fl = mech.flows(lesson, scene["before"], scene["state"])
            if fl:
                vbw = (pw_ or mech.WIDTHS[("wide", mech.page_place(lesson))]) + 8
                vbh = mh + 8
                k_ = min(pw / vbw, ph / vbh)
                ox = (pw - vbw * k_) / 2
                A0 = mech.stack_anchors(lesson, scene["before"], "wide", pw_, sizes=sizes)
                A1 = mech.stack_anchors(lesson, scene["state"], "wide", pw_, sizes=sizes)
                vt0 = ty["value"]
                for n_, (i, j, fid) in enumerate(fl):
                    if i not in A0["rets"] or j not in A1["slots"]:
                        continue
                    x0, y0 = A0["rets"][i]
                    x1, y1 = A1["slots"][j]
                    fpx = round({**mech.SIZES["wide"], **sizes}["value"] * k_, 1)
                    chips += (f'<p class="chip" id="chip{n_}" data-fact="{esc(fid)}" data-layout-allow-overlap="" '
                              f'style="left:{ox + x0 * k_:.1f}px;top:{y0 * k_:.1f}px;font-size:{fpx}px">'
                              f'{esc(text.display(lesson.fact(fid)))}</p>')
                    dx, dy = (x1 - x0) * k_, (y1 - y0) * k_
                    # the value leaves its frame, swings out to the right and lands in the caller's slot
                    morph_js.append(f"d.set(q('#chip{n_}'), {{ xPercent: -50, yPercent: -50 }}, 0);")
                    morph_js.append(f"d.fromTo(q('#chip{n_}'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.12 }}, 0);")
                    morph_js.append(f"d.to(q('#chip{n_}'), {{ x: {dx:.1f}, duration: {FLIGHT - 0.1}, ease: 'power1.inOut' }}, 0.1);")
                    morph_js.append(f"d.to(q('#chip{n_}'), {{ y: {dy:.1f}, duration: {FLIGHT - 0.1}, ease: 'back.in(1.4)' }}, 0.1);")
                    morph_js.append(f"d.to(q('#chip{n_}'), {{ opacity: 0, duration: 0.2 }}, {FLIGHT + 0.35});")
        mech_html = f'<div class="mechbox" data-key="panel">{layers}{chips}</div>'
    kicker = text.kicker(lesson).upper()
    fname = lambda prog: esc(lesson.program(prog)["path"].split("/")[-1])  # noqa: E731
    files = (f'<p class="file" data-set="old" data-label="program-file">{fname(before["program"])}</p>' if morph else "") + \
        f'<p class="file" data-set="cur" data-label="program-file">{fname(cur["program"])}</p>'
    compiler = next((f["source"]["compiler"].split(" (")[0] for f in lesson.data["facts"] if f.get("source")), None)
    foot = (f'<p class="foot" data-chrome="provenance_short">{esc(text.ui("provenance_short", compiler=compiler))}</p>'
            if compiler else "")

    # --- the drawing (offsets from the reveal), on a nested timeline played at 1/k speed
    js = list(morph_js)
    S = C
    for st in plan["steps"]:
        a, b = st["a"], st["b"]
        t0 = f"{st['t0']:.3f}"
        js.append(f"d.to(q('.seg{S}[data-seg=\"{a}-{b}\"]'), {{ strokeDashoffset: 0, duration: {st['dur']}, ease: 'power1.inOut' }}, {t0});")
        js.append(f"d.to(q('.hl'), {{ y: {gc['cy'][b] - LH / 2:.1f}, duration: {st['dur']}, ease: 'power1.inOut' }}, {t0});")
        end = f"{st['t0'] + st['dur']:.3f}"
        js.append(f"d.to(q('.dot{S}[data-line=\"{b}\"], .head{S}[data-seg=\"{a}-{b}\"], .tag{S}[data-line=\"{b}\"]'), "
                  f"{{ opacity: 1, duration: 0.12 }}, {end} - 0.06);")
        js.append(f"d.to(q('.ln[data-to=\"{b}\"]'), {{ color: '{t['ink']}', duration: 0.2 }}, {end} - 0.1);")
        if st["kind"] == "jump":
            for n, key, tone in curset["tag_list"]:
                if key == "skipped_label" and a < n < b:
                    js.append(f"d.to(q('.tag{S}[data-line=\"{n}\"]'), {{ opacity: 1, duration: 0.2 }}, {t0} + {st['dur'] / 2:.3f});")
        if curset["nob"] and a == curset["nob"]:
            js.append(f"d.fromTo(q('.nobreak{S}'), {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1.08, duration: 0.18, ease: 'power2.out' }}, {end} - 0.1);")
            js.append(f"d.to(q('.nobreak{S}'), {{ scale: 1, duration: 0.25, ease: 'power2.inOut' }}, {end} + 0.08);")
    if plan["first"] is not None:
        f0, fa = plan["first"], plan["first_at"]
        js.insert(len(morph_js), f"d.to(q('.dot{S}[data-line=\"{f0}\"], .tag{S}[data-line=\"{f0}\"]'), {{ opacity: 1, duration: 0.12 }}, {fa});"
                                 f"d.to(q('.ln[data-to=\"{f0}\"]'), {{ color: '{t['ink']}', duration: 0.2 }}, {fa});")
    oa = plan["outputs_at"]
    if plan.get("hl_to") is not None and plan["hl_to"] in gc["cy"]:
        js.append(f"d.to(q('.hl'), {{ y: {gc['cy'][plan['hl_to']] - LH / 2:.1f}, duration: 0.3, ease: 'power1.inOut' }}, {plan['hl_at']:.3f});")
    if grow:
        js.append(f"d.fromTo(q('.sidebody'), {{ y: {-shift} }}, {{ y: 0, duration: 0.45, ease: 'power2.inOut' }}, {max(0.0, oa - 0.5):.3f});")
        js.append(f"d.fromTo(q('.outcard'), {{ opacity: 0, y: -12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }}, {max(0.0, oa - 0.15):.3f});")
    js.append(f"if (q('.out-new').length) d.fromTo(q('.out-new'), {{ opacity: 0, x: -16 }}, "
              f"{{ opacity: 1, x: 0, duration: 0.3, stagger: {OUT_STEP}, ease: 'power2.out' }}, {oa:.3f});")
    js.append(f"if (q('.ostep{S}.new').length) d.fromTo(q('.ostep{S}.new'), {{ opacity: 0, scale: 0.6 }}, "
              f"{{ opacity: 1, scale: 1, duration: 0.3, stagger: {OUT_STEP}, ease: 'back.out(2)' }}, {oa:.3f});")
    if morph:
        # held at full until the first new value is half in (0.3 s fade from oa), then gone in 0.15 s
        js.append(f"d.to(q('.out[data-set=\"old\"]'), {{ opacity: 0, duration: 0.15 }}, {oa + 0.16:.3f});")

    if stack_out:
        t0_, t1_, h0_, h1_ = stack_out
        if abs(t0_ - t1_) > 0.5 or h0_ != h1_:
            f0 = FLIGHT if mech.flows(lesson, scene["before"], scene["state"]) else 0.0
            js.append(f"d.fromTo(q('.outcard'), {{ top: {t0_ - L['side_top']:.1f}, height: {h0_} }}, "
                      f"{{ top: {t1_ - L['side_top']:.1f}, height: {h1_}, duration: 0.45, ease: 'power2.inOut' }}, {f0});")
    if mode and has_out and not before_out:
        js.append(f"d.fromTo(q('.outcard'), {{ opacity: 0, y: -12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }}, {max(0.0, oa - 0.15):.3f});")
    if mode and not q and replay and scene["before"] != scene["state"]:
        # the panel: this scene's state fades in over the previous one, which then fades out (removed parts go)
        # autoAlpha: a layer at opacity 0 is also visibility:hidden, so only the cross-fade overlaps the two
        f0 = FLIGHT if mech.flows(lesson, scene["before"], scene["state"]) else 0.0
        js.append(f"d.fromTo(q('.mcur'), {{ autoAlpha: 0 }}, {{ autoAlpha: 1, duration: 0.45, ease: 'power1.out' }}, {f0});")
        js.append(f"d.to(q('.mbefore'), {{ autoAlpha: 0, duration: 0.3, ease: 'power1.in' }}, {f0 + 0.45});")
    if mode == "path":
        # the controlling variable, bound to the line that sets it (every number on the stage is bound, AC-10.2)
        nl = rail.listing(lesson, cur["program"])[0]
        src_ = lesson.program_source(cur["program"]).split("\n")
        vline = next((i for i in range(1, len(src_) + 1) if all(f"{k} = {v}" in src_[i - 1] for k, v in cur["vars"].items())), None)
        vars_html = " ".join(f'<span data-code="{cur["program"]}"{f" data-src-line={chr(34)}{vline}{chr(34)}" if vline else ""}>'
                             f'{esc(k)} = {esc(v)}</span>' for k, v in cur["vars"].items())
        del nl
    vars_p = (f'<p class="vars"><span class="varlabel" data-chrome="vars_label">{esc(text.ui("vars_label").upper())}</span>'
              f'{vars_html}</p>') if mode in (None, "path") else ""
    panel_css = ""
    if mode:
        bx, by, bw, bh = L["q_panel_box"] if q else L["panel_box"]
        qx, qy, qw, qh = L["q_box"]
        ox, oy, ow, ohh = _out_rect(L)
        if mode == "path":
            out_css_v = (f".vars {{ left:{L['code_x'] + 4}px; top:{L['vars_top']}px; }}\n"
                         f".panel.pnote {{ left:{L['q_box'][0]}px; top:12px; width:{SX1 - L['q_box'][0]}px; height:{STOP - 20}px; bottom:auto;"
                         f" padding:4px 0 4px 24px; display:flex; align-items:center; }}\n"
                         f".panel.pchange {{ left:{L['q_box'][0]}px; top:12px; width:{SX1 - L['q_box'][0]}px; height:auto; bottom:auto;"
                         f" padding:6px 0 6px 24px; display:grid; grid-template-columns:auto 1fr; column-gap:24px; align-items:baseline; }}\n"
                         f".pchange .qlabel {{ margin:0; }} .pchange .files {{ margin:0; }} .pchange .dl {{ grid-column:1 / -1; margin:0; }}\n")
        else:
            out_css_v = ""
        out_css = out_css_v + (f".outcard {{ left:0px; top:{stack_out[1] - L['side_top']:.1f}px; width:{ow}px; height:{stack_out[3]}px; }}\n"
                   if stack_out else f".outcard {{ left:{ox}px; top:{oy}px; width:{ow}px; height:{ohh}px; }}\n")
        panel_css = (f".mechbox {{ position:absolute; left:{bx}px; top:{by}px; width:{bw}px; height:{bh}px; }}\n"
                     f".mlayer {{ position:absolute; left:0; top:0; width:100%; height:100%; }}\n"
                     f".chip {{ position:absolute; margin:0; padding:2px 12px; opacity:0; border-radius:10px; white-space:nowrap; "
                     f"font-family:{ty['value']['family']}; font-weight:700; line-height:1.25; color:{t['ground']}; background:{t['value']}; }}\n"
                     f"{out_css}"
                     f".qhead {{ position:absolute; left:{qx}px; top:{qy}px; width:{qw}px; height:{qh}px; margin:0; }}\n"
                     f".qhead .qtext {{ font-size:{Q_PROMPT}px; line-height:1.2; color:{t['note']}; font-weight:600; }}\n"
                     f".qhead .qopts {{ margin-top:12px; gap:10px 14px; }}\n"
                     f".qhead .qopt {{ font-size:{Q_OPT}px; padding:4px 16px; }}\n")
    font = L["font"]
    # B3: in a stage layout the mechanism, the code it runs and the output it prints are one figure (AC-10.2 markup)
    mk = mech.MECH_KIND.get(mech.panel_kind(lesson) or "", "")
    stage_open = (f'<div class="stage" data-role="figure"><div class="stagemech" data-role="mechanism" data-kind="{mk}">'
                  if mode else "")
    stage_close = "</div></div>" if mode else ""
    kt, dt, bt, lt, vt, ct = ty["kicker"], ty["display"], ty["body"], ty["label"], ty["value"], ty["code"]
    card_border = f"border:2px solid {t['rule']};" if frame.get("card_border") else ""
    panel_fill = f"background:{t['note_tint']};" if frame.get("panel_fill") else ""
    panel_rule = f"border-left:4px solid {t['rule'] if frame.get('panel_divider') else t['note']};"
    title_px = 60 if dt["key"] == "sans" else 64
    kick_top, title_top = (52, 90) if mode is None else (22, 48)
    if mode:
        title_px = 48
    return _guard_tweens(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(scene['title'])}</title></head>
<body><template>
<style>
{font_faces()}
#root-{sid} {{ position:absolute; inset:0; color:{t['ink']}; font-family:{bt['family']};
  font-variant-numeric:lining-nums tabular-nums; overflow:hidden; }}
.bg {{ position:absolute; inset:0; background:{t['ground']}; }}
.kicker {{ position:absolute; left:{SX0 if mode else MX}px; top:{kick_top}px; margin:0; display:flex; align-items:center; font:{kt['weight']} 24px/1.2 {kt['family']};
  letter-spacing:.12em; color:{t['label']}; }}
.count {{ margin-left:24px; padding-left:24px; border-left:2px solid {t['rule']}; font:500 24px/1.2 {ct['family']}; letter-spacing:.04em; color:{t['label']}; }}
.title {{ position:absolute; left:{SX0 if mode else MX}px; top:{title_top}px; margin:0; font:{dt['weight']} {title_px}px/1.15 {dt['family']}; letter-spacing:-.015em; color:{t['ink']}; }}
.file[data-set="cur"] {{ opacity:{0 if morph else 1}; }}
.file {{ position:absolute; left:{L['code_x']}px; width:{L['card_w'] - 24}px; top:{L['code_top'] - 38}px; margin:0; text-align:right;
  font:600 24px/1.2 {ct['family']}; color:{t['label']}; }}
.code {{ position:absolute; left:{L['code_x']}px; top:{L['code_top']}px; width:{L['card_w']}px; height:{L['card_h']}px; background:{t['surface']};
  {card_border} border-radius:22px; box-sizing:border-box; overflow:hidden; }}
.rows {{ position:absolute; inset:0; }}
.rows.hidden {{ opacity:0; }}
.ln {{ position:absolute; left:0; right:0; height:{LH}px; font:400 {font}px/{LH}px {ct['family']}; white-space:pre; color:{t['label']}; }}
.ln.exec {{ color:{t['ink']}; }}
.ln.add {{ color:{t['label']}; }}
.no {{ position:absolute; left:0; width:{L['num_x']}px; text-align:right; color:{t['faint']}; font-size:{max(13, font - 8)}px; }}
.no2 {{ opacity:1; }}
.ln[data-to] .no2 {{ opacity:0; }}
.ln.add .no2 {{ color:{t['value']}; opacity:1; }}
.src {{ position:absolute; left:{L['src_x']}px; }}
.kw {{ font-weight:700; }}
.str {{ color:{t['ink_soft']}; }}
.band {{ position:absolute; left:0; right:0; height:{LH}px; opacity:0; }}
.band.plus {{ background:{_rgba(t['value'], 0.07)}; border-left:6px solid {t['value']}; box-sizing:border-box; }}
.band.minus {{ background:{_rgba(t['correction'], 0.16)}; border-left:6px solid {t['correction']}; box-sizing:border-box; }}
.strike {{ position:absolute; left:{L['src_x'] - 6}px; right:300px; top:{LH / 2 - 1.5:.1f}px; height:3px; background:{t['correction']}; transform-origin:0 50%; }}
.hl {{ position:absolute; left:{L['src_x'] - 14}px; right:20px; top:0; height:{LH}px; background:{t['highlight']}; border-left:6px solid {t['note']}; border-radius:8px; }}
.rail {{ position:absolute; left:0; top:0; width:{L["card_w"] - 4}px; height:{L['card_h'] - 4}px; overflow:visible; }}
.seg {{ fill:none; stroke:{t['note']}; stroke-width:4; stroke-linecap:round; stroke-dasharray:1; stroke-dashoffset:0; }}
.seg.new {{ stroke-dashoffset:1; }}
.head, .dot {{ fill:{t['note']}; }}
.head.new, .dot.new, .tag.new, .badge.new, .ostep.new {{ opacity:0; }}
.tag {{ position:absolute; right:28px; margin:0; height:{LH}px; font:500 24px/{LH}px {ct['family']}; color:{t['note']}; }}
.tag.muted {{ color:{t['label']}; }}
.badge {{ position:absolute; right:24px; margin:0; padding:0 16px; height:40px; transform-origin:100% 50%;
  font:700 24px/38px {ct['family']}; color:{t['correction']}; background:{t['correction_tint']}; border:2px solid {t['correction']}; border-radius:20px; box-sizing:border-box; }}
.ostep {{ position:absolute; margin:0; width:{L['badge']}px; height:{L['badge']}px; border-radius:{L['badge'] / 2}px; box-sizing:border-box; text-align:center;
  font:700 {max(12, round(L['badge'] * 0.55))}px/{L['badge']}px {ct['family']}; color:{t['ground']}; background:{t['value']}; }}
.side {{ position:absolute; left:{L['side_x']}px; top:{L['side_top']}px; width:{L['side_w']}px; height:{L['side_h']}px; overflow:hidden; }}
.sidebody {{ position:absolute; inset:0; }}
.outcard {{ position:absolute; left:0; top:0; width:{L['side_w']}px; height:{out_h}px; background:{t['surface']}; {card_border} border-radius:22px; box-sizing:border-box; }}
.outlabel {{ position:absolute; left:34px; top:28px; margin:0; font:{lt['weight']} 22px/1.2 {lt['family']}; letter-spacing:.12em; color:{t['label']}; }}
.out {{ position:absolute; left:34px; height:76px; font:{vt['weight']} 52px/76px {vt['family']}; color:{t['value']}; }}
.step {{ display:inline-block; width:58px; font-size:26px; font-weight:500; color:{t['faint']}; vertical-align:top; }}
.vars {{ position:absolute; left:4px; top:{shift}px; margin:0; font:500 30px/1.3 {ct['family']}; color:{t['ink_soft']}; }}
.varlabel {{ font:{lt['weight']} 22px/1.3 {lt['family']}; letter-spacing:.12em; color:{t['label']}; margin-right:18px; }}
.panel {{ position:absolute; left:0; top:{panel_top}px; width:{L['side_w']}px; bottom:0; box-sizing:border-box; border-radius:{22 if frame.get('panel_fill') else 0}px; padding:30px 38px; }}
.notecard {{ {panel_fill} {panel_rule} display:flex; flex-direction:column; justify-content:center; }}
.pathcard {{ {panel_rule} padding:12px 0 12px 22px; }}
.pathfig {{ display:block; width:100%; height:100%; }}
.note {{ margin:0; font:{nt['weight']} 50px/1.18 {nt['family']}; color:{t['note']}; }}
.qcard {{ {panel_fill} border:3px solid {t['note']}; border-radius:22px; display:flex; flex-direction:column; justify-content:center; }}
.changecard {{ {panel_fill} {panel_rule} }}
.changecard .files {{ margin:0 0 18px; font:600 30px/1.3 {ct['family']}; color:{t['ink']}; }}
.changecard .dl {{ margin:0 0 8px; font:400 30px/1.3 {ct['family']}; color:{t['ink']}; white-space:pre; }}
.changecard .mark {{ display:inline-block; width:40px; font-weight:700; }}
.changecard .plus .mark {{ color:{t['value']}; }}
.changecard .minus .mark {{ color:{t['correction']}; }}
.qlabel {{ margin:0 0 14px; font:700 24px/1.2 {lt['family']}; letter-spacing:.14em; text-transform:uppercase; color:{t['note']}; }}
.qtext {{ margin:0; font:500 {round(46 * bt['scale'])}px/1.24 {bt['family']}; color:{t['ink']}; }}
.qopts {{ display:flex; flex-wrap:wrap; gap:10px 14px; margin-top:18px; }}
.qopt {{ margin:0; padding:6px 18px; border:2px solid {t['rule']}; border-radius:12px; background:{t['surface']};
  font:{vt['weight']} 28px/1.3 {vt['family']}; color:{t['ink']}; white-space:pre; }}
{panel_css}
.stage, .stagemech {{ position:absolute; inset:0; }}
.footrule {{ position:absolute; left:{SX0 if mode else MX}px; right:{W - SX1 if mode else MX}px; top:{SBOT + 8 if mode else H - BOTTOM + 22}px; height:2px; background:{t['rule']}; opacity:.6; }}
.foot {{ position:absolute; right:{W - SX1 if mode else MX}px; top:{SBOT + 16 if mode else H - BOTTOM + 36}px; margin:0; font:400 20px/1.2 {ct['family']}; letter-spacing:.06em; color:{t['label']}; }}
</style>
<div id="root-{sid}" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-program="{cur['program']}"
  data-state="{scene['state']}" data-before="{scene['before']}" data-theme="{theme}" data-swap="{swap if morph else ''}">
  <div class="bg"></div>
  <p class="kicker"><span data-chrome="kicker">{esc(kicker)}</span><span class="count" data-label="chapter-count">{index + 1} / {count}</span></p>
  <h1 class="title" data-label="scene-title">{esc(scene['title'])}</h1>
  {files}
  {stage_open}
  <div class="code" id="code-{sid}" data-key="code">
    {morph_html}
    <div class="hl" style="transform:translateY({hl_from - LH / 2:.1f}px)"></div>
    {''.join(s['rows'] for s in sets)}
    {''.join(s['rail'] for s in sets)}
    {''.join(s['tags'] + s['steps'] for s in sets)}
    {inline_outs}
  </div>
  {mech_html}
  <div class="side">
    {outcard}
    <div class="sidebody">
      {vars_p if mode is None else ''}
      {side if mode is None else ''}
    </div>
  </div>
  {vars_p if mode == "path" else ''}
  {stage_close}
  {side if mode else ''}
  <div class="footrule"></div>
  {foot}
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  (function () {{
    var root = document.querySelector('[data-composition-id="{sid}"]');
    var q = function (s) {{ return root.querySelectorAll(s); }};
    // tweens skip a selector that matches nothing in this scene (GSAP would warn)
    var TO = function (t, s, v, p) {{ var n = q(s); if (n.length) t.to(n, v, p); }};
    var FT = function (t, s, a, b, p) {{ var n = q(s); if (n.length) t.fromTo(n, a, b, p); }};
    var SET = function (t, s, v, p) {{ var n = q(s); if (n.length) t.set(n, v, p); }};
    var tl = gsap.timeline({{ paused: true }});
    var R = {reveal:.3f};
    // scene boundary: the title and the note dip through the ground (out over the last 0.3 s, in
    // over the first 0.4 s of the next scene); the code card and output stay, so nothing jumps
    tl.fromTo(q('.title'), {{ opacity: 0, y: 12 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }}, 0);
    tl.fromTo(q('.panel:not(.changecard)'), {{ opacity: 0, y: 10 }}, {{ opacity: 1, y: 0, duration: 0.4, ease: 'power2.out' }}, {note_at:.3f});
    {f"tl.fromTo(q('.changecard'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.4, ease: 'power2.out' }}, 0.05); tl.to(q('.changecard'), {{ opacity: 0, duration: 0.3 }}, {note_at + 0.05:.3f});" if morph else ""}
    {f"tl.to(q('.title, .panel'), {{ opacity: 0, duration: 0.3, ease: 'power1.in' }}, {scene['duration'] - 0.3:.3f});" if index + 1 < count else ""}
    if (q('.out-new').length) tl.set(q('.out-new'), {{ opacity: 0 }}, 0);
    if (q('.ln.exec-new').length) tl.set(q('.ln.exec-new'), {{ color: '{t['label']}' }}, 0);
    var d = gsap.timeline({{ data: 'draw' }});
    {chr(10).join('    ' + j for j in js).strip()}
    d.timeScale({1 / plan['k']:.6f});
    tl.add(d, R);
    {f"tl.set(q('.rows[data-set=\"old\"]'), {{ opacity: 0 }}, {swap});" if morph else ""}
    {f"tl.set(q('.rows[data-set=\"cur\"]'), {{ opacity: 1 }}, {swap});" if morph else ""}
    tl.set({{}}, {{}}, {scene['duration']:.3f});
    window.__timelines["{sid}"] = tl;
  }})();
</script>
</template></body></html>
""")


_TWEEN = re.compile(r"\b(tl|d)\.(to|fromTo|set)\(q\('([^']*)'\), ")


def _guard_tweens(page):
    """`d.to(q('sel'), ...)` -> `TO(d, 'sel', ...)`: the guarded helpers defined in the scene script."""
    return _TWEEN.sub(lambda m: f"{ {'to': 'TO', 'fromTo': 'FT', 'set': 'SET'}[m.group(2)]}({m.group(1)}, '{m.group(3)}', ",
                      page)


def font_faces():
    faces = []
    for key in ("serif", "sans", "mono", "hand"):
        spec = fonts.tokens()["fonts"][key]
        faces.append(f"@font-face{{font-family:'{spec['family']}';src:url('fonts/{spec['file']}') format('woff2');"
                     f"font-weight:{spec['weight']};font-style:normal;font-display:block}}")
    return "".join(faces)


def host_html(lesson, timing):
    t = fonts.tokens()["themes"][timing.get("theme", DEFAULT_THEME)]
    clips = []
    for s in timing["scenes"]:
        clips.append(f'  <div id="clip-{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
                     f'data-start="{s["start"]:g}" data-duration="{s["duration"]:g}" data-track-index="1" '
                     f'data-width="{W}" data-height="{H}"></div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width={W}, height={H}">
<title>{esc(lesson.data['title'])}</title>
<style>{font_faces()}
html,body{{margin:0;width:{W}px;height:{H}px;background:{t['ground']}}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden}}
#root .ground{{position:absolute;inset:0;background:{t['ground']}}}</style>
<script src="vendor/gsap.min.js"></script>
</head><body>
<div id="root" data-composition-id="lesson" data-start="0" data-width="{W}" data-height="{H}" data-duration="{timing['duration']:g}" data-fps="{FPS}">
  <div class="ground"></div>
{chr(10).join(clips)}
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  var tl = gsap.timeline({{ paused: true }});
  tl.set({{}}, {{}}, {timing['duration']:g});
  window.__timelines["lesson"] = tl;
</script>
</body></html>
"""


def write_composition(lesson, timing, comp):
    if comp.exists():
        shutil.rmtree(comp)
    (comp / "compositions").mkdir(parents=True)
    (comp / "vendor").mkdir()
    (comp / "fonts").mkdir()
    shutil.copyfile(host.PKG / "ptk" / "templates" / "video" / "vendor" / "gsap.min.js", comp / "vendor" / "gsap.min.js")
    for key in ("serif", "sans", "mono", "hand"):
        f = fonts.tokens()["fonts"][key]["file"]
        shutil.copyfile(host.FONTS_DIR / f, comp / "fonts" / f)
    (comp / "hyperframes.json").write_text(json.dumps({"media": {"autoProxy": False}}))
    (comp / "index.html").write_text(host_html(lesson, timing))
    scenes = timing["scenes"]
    for i, s in enumerate(scenes):
        (comp / "compositions" / f"{s['id']}.html").write_text(scene_html(lesson, s, i, len(scenes), timing))


# ---------------------------------------------------------------- renderer-neutral interface (D20.11)

class Renderer:
    """What the video projector needs from a renderer. Everything else (TTS, the schedule, the
    screen plan, captions, chapters, loudness, mux and the media, sync and leak gates) is shared.

    A backend gets the lesson and the timing (scenes with start/end/reveal/shown/before/morph,
    cues, fps, theme) and must draw, for every scene, the `before` state until `reveal` and the
    scene's own state from `shown` on, so the IVE's cues stay true. A Manim backend would
    implement the same four methods; frame probing (verify/frames.py) is HyperFrames-specific
    and a backend without it reports the frame gates `not-run`.
    """
    name = "abstract"

    def available(self):
        raise NotImplementedError

    def write(self, lesson, timing, out_dir):
        """Write the renderer's source for every scene; return the source directory."""
        raise NotImplementedError

    def check(self, lesson, src_dir):
        """Static check of the source: {"clean": bool, "counts": {...}, "reason": str, "raw": ...}."""
        raise NotImplementedError

    def render(self, src_dir, work, lesson_sha):
        """Render a silent 1920x1080 30 fps H.264 MP4; return (path, log). Raise RenderFailed."""
        raise NotImplementedError

    def frame_probe(self):
        """True when verify/frames.py can probe this renderer's source frame by frame."""
        return False


class HyperFramesRenderer(Renderer):
    name = "hyperframes"

    def available(self):
        return host.state_path("tools", "node", "node_modules", ".bin", "hyperframes").exists()

    def write(self, lesson, timing, out_dir):
        comp = out_dir / "composition"
        write_composition(lesson, timing, comp)
        return comp

    def check(self, lesson, src_dir):
        from ..build import hf_check_clean
        chk = node.hyperframes(["check", ".", "--json"], cwd=src_dir, timeout=900, lesson_sha256=lesson.sha256(),
                               sandbox_tmp=host.make_tmp("check-"), check=False)
        try:
            hf = json.loads(chk.stdout)
        except json.JSONDecodeError:
            hf = {"ok": False, "raw": (chk.stdout or chk.stderr)[-2000:]}
        clean, counts, why = hf_check_clean(hf)
        return {"clean": clean, "counts": counts, "reason": why, "exit": chk.code,
                "scenes": len(list((src_dir / "compositions").glob("*.html")))}

    def render(self, src_dir, work, lesson_sha):
        return render(src_dir, work, lesson_sha)

    def frame_probe(self):
        return True


RENDERERS = {"hyperframes": HyperFramesRenderer}


def get_renderer(name="hyperframes"):
    if name not in RENDERERS:
        raise errors.ModelSchemaError(f"unknown video renderer {name!r}; known: {sorted(RENDERERS)}",
                                      pointer="/video/renderer")
    return RENDERERS[name]()


# ---------------------------------------------------------------- render + mux

def render(comp, work, lesson_sha):
    """hyperframes render under the sandbox render profile (loopback only). Returns (mp4, log)."""
    tmp = host.make_tmp("render-")
    silent = comp / "renders" / "silent.mp4"
    (comp / "renders").mkdir(exist_ok=True)
    res = node.hyperframes(["render", ".", "-o", str(silent), "--fps", str(FPS), "--quality", "standard",
                            "--workers", "1", "--no-browser-gpu", "--strict"],
                           cwd=comp, timeout=1800, lesson_sha256=lesson_sha, sandbox_tmp=tmp, check=False)
    log = (res.stdout or "") + (res.stderr or "")
    (work / "render.log").write_text(log)
    shutil.rmtree(tmp, ignore_errors=True)
    if res.code != 0 or not silent.exists():
        raise errors.RenderFailed(f"hyperframes render exited {res.code}", log_tail=log[-3000:])
    return silent, log


def mux(silent, wav, out, mp4):
    ffmpeg = host.which("ffmpeg")
    host.run([ffmpeg, "-v", "error", "-y", "-i", silent, "-i", wav, "-i", out / "captions.vtt", "-i",
              out / "work" / "chapters.ffmeta", "-map", "0:v", "-map", "1:a", "-map", "2:s", "-map_metadata", "3",
              "-map_chapters", "3", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-c:s", "mov_text",
              "-metadata:s:s:0", "language=eng", "-movflags", "+faststart", mp4], check=True, timeout=600)


def resolve_theme(theme=None):
    """The video theme: the argument, else $PTK_VIDEO_THEME, else DEFAULT_THEME (Atlas dark)."""
    theme = theme or os.environ.get("PTK_VIDEO_THEME") or DEFAULT_THEME
    if theme not in THEMES:
        raise errors.ModelSchemaError(f"unknown video theme {theme!r}; known: {list(THEMES)}", pointer="/video/theme")
    return theme


def project(lesson, out, tts_engine=None, theme=None, renderer="hyperframes"):
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    rnd = get_renderer(renderer)
    segs = segments_of(lesson)
    syn = tts.synthesize([{"id": s["id"], "spoken": s["spoken"]} for s in segs], work / "tts", force_engine=tts_engine)
    measured = tts.trim_and_measure(syn["segments"], work / "tts")
    timing = schedule(lesson, measured)
    timing["theme"] = resolve_theme(theme)
    timing["renderer"] = rnd.name
    audio = assemble_audio(timing, measured, work, out / "narration.wav")
    write_text_tracks(lesson, timing, out)
    comp = rnd.write(lesson, timing, out)
    timing_public = {**timing, "tts": {k: v for k, v in syn.items() if k != "segments"},
                     "segments": [{"id": m["id"], "seconds": m["seconds"]} for m in measured], "audio": audio}
    (out / "timing.json").write_text(json.dumps(timing_public, indent=2, default=str))
    return {"timing": timing_public, "composition": comp, "degraded": syn["degraded"], "tts": syn, "renderer": rnd}


def finish(lesson, out, comp, renderer=None):
    """Render (sandboxed) and mux. Split from project() so the isolation gate can wrap the render."""
    rnd = renderer or get_renderer()
    silent, log = rnd.render(comp, out / "work", lesson.sha256())
    mp4 = out / "lesson.mp4"
    mux(silent, out / "narration.wav", out, mp4)
    return mp4, log
