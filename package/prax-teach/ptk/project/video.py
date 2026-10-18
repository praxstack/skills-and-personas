"""Narrated video projector: per-scene HyperFrames sub-compositions, batched Kokoro TTS,
schedule from measured durations, WebVTT captions + chapters, LUFS normalisation, sandboxed render, mux.

Timeline rule (AC-5.3, E17, D18.2):
    segment n starts after segment n-1 ends + gap (0.35 s in a scene, 0.8 s across scenes,
    plus a 3 s think pause after a question scene); durations are measured from the trimmed audio.
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
LEAD, GAP_IN, GAP_SCENE, THINK, TAIL, SCENE_LEAD = 0.8, 0.35, 0.8, 3.0, 1.6, 0.35
SETTLE = 0.5
MINUS = "\u2212"
KEYWORDS = {"int", "switch", "case", "break", "return", "void", "char", "default"}


def _frame(t):
    return round(round(t * FPS) / FPS, 4)


def segments_of(lesson):
    segs = []
    for sc in lesson.data["storyboard"]:
        for i, n in enumerate(sc["narration"]):
            said = n.get("spoken") or n["text"]
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
            t += GAP_IN if s["scene"] == prev_scene else GAP_SCENE + (THINK if "question" in scenes[prev_scene] else 0)
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
        out_scenes.append({"id": sid, "title": scenes[sid]["title"], "state": scenes[sid]["state"], "start": start,
                           "reveal": sc_cues[-1]["start"] if i else 0.0,
                           "question": scenes[sid].get("question")})
    for i, s in enumerate(out_scenes):
        s["end"] = out_scenes[i + 1]["start"] if i + 1 < len(out_scenes) else total
        s["duration"] = round(s["end"] - s["start"], 4)
    plan_screen(lesson, out_scenes)
    return {"fps": FPS, "duration": total, "cues": cues, "scenes": out_scenes,
            "rule": "start(n) = end(n-1) + gap; durations measured from trimmed TTS audio; see plan_screen for "
                    "before/reveal/shown"}


# ---------------------------------------------------------------- what is on screen when

SEG_RUN, SEG_JUMP, OUT_STEP = 0.32, 0.62, 0.12
DRAW_BUDGET = 0.7  # at most this share of the time left in a scene goes to drawing
MORPH = 1.25       # a change of program: the old code turns into the new code as a diff (see scene_html)
MORPH_LEAD = 0.4   # the morph starts once the scene title is in


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
    new_out = [f for f in cur["output"] if not same or f not in old["output"]]
    outputs_at = round(t + 0.05, 3)
    # settled = the end of the last tween scene_html schedules (dots/tags +0.06, line colour +0.1,
    # the no-break pulse +0.33, the last output value outputs_at + (k-1) * step + 0.3)
    src = lesson.program_source(cur["program"]).split("\n")
    nob = rail.nobreak_after(src, cur["path"])
    ends = [st["t0"] + st["dur"] + (0.33 if st["a"] == nob else 0.1) for st in steps] + [t + 0.1, morph]
    if new_out:
        ends.append(outputs_at + (len(new_out) - 1) * OUT_STEP + 0.3)
    if (lesson.data.get("figure") or {}).get("panel") and before_sid and before_sid != sid:
        ends.append(0.8)  # the panel's cross-fade (scene_html): 0.45 s in, then 0.3 s out from 0.45
    total = max(max(ends), SETTLE)
    # a short scene plays the same drawing faster (a nested timeline with timeScale 1/k), never cut off
    k = min(1.0, budget / total) if budget else 1.0
    return {"steps": steps, "first": first, "first_at": first_at, "morph": morph, "outputs_at": outputs_at,
            "total": round(total * k, 3), "k": round(k, 4)}


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
                      "aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                     timeout=600)
    err = first.stderr
    m = json.loads(err[err.rindex("{"):err.rindex("}") + 1])
    af = (f"aformat=channel_layouts=stereo,loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
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


def _layout(lesson):
    """The frame grid, shared by every scene. Row height comes from the longest listing in the storyboard.

    No panel: the code card (1060 wide) and the side column (output, variables, note) as drawn above.
    Panel beside the code (views, stack): a narrower code card; the side column holds the panel on top and
    the output and the note side by side under it.
    Panel above the code (neuron): the panel spans the frame under the title; the code card and the side
    column (output, then the note) share the rest.
    """
    panel = (lesson.data.get("figure") or {}).get("panel")
    mode = None if not panel else ("side" if panel["kind"] == "stack" or panel["place"] == "side" else "hero")
    L = {"mode": mode, "code_top": CODE_TOP, "card_w": CARD_W, "side_x": SIDE_X, "side_w": SIDE_W}
    if mode == "side":
        L.update(card_w=840, side_x=976, side_w=848, panel_box=(976, CODE_TOP, 848, 520))
    elif mode == "hero":
        L.update(code_top=616, card_w=840, side_x=976, side_w=848, panel_box=(MX, 176, W - 2 * MX, 420))
    rows, longest, per_line = 1, 1, 1
    for sc in lesson.data["storyboard"]:
        st = lesson.state(sc["state"])["state"]
        src = lesson.program_source(st["program"]).split("\n")
        first, last = rail.listing(lesson, st["program"])
        rows = max(rows, last - first + 1)
        longest = max(longest, max(len(src[n - 1].rstrip()) for n in range(first, last + 1)))
        made = rail.print_lines(src, st.get("path", []), [text.display(lesson.fact(f)) for f in st["output"]]) or []
        per_line = max([per_line] + [made.count(n) for n in made])
    L["card_h"] = H - BOTTOM - L["code_top"]
    line_h = int((L["card_h"] - 2 * ROW_PAD) // rows)
    # the longest line, its output-step badges and the tag column must fit the card
    fit = (L["card_w"] - SRC_X - 40 - per_line * 46) / (longest * 0.6)
    L.update(line_h=line_h, font=int(min(36, line_h * 0.64, fit)))
    max_out = max(len(lesson.state(sc["state"])["state"]["output"]) for sc in lesson.data["storyboard"])
    L["max_out"] = max(max_out, 1)
    return L


def _out_rect(L):
    """The output card in panel layouts (x, y, w, h) relative to the side column: under the panel (side) or the
    whole column (hero). The note is left to the narration and its captions; the panel carries the picture."""
    if L["mode"] == "side":
        top = L["panel_box"][3] + 12
        return (0, top, L["side_w"], L["card_h"] - top)
    return (0, 0, L["side_w"], L["card_h"])


def _out_grid(L, n):
    """(row height, rows per column, column width) for n output values in a panel layout's output card:
    one column when rows of at least 46 px fit, else two."""
    _x, _y, w, h = _out_rect(L)
    rows = n if (h - 72) / max(n, 1) >= 46 else -(-n // 2)
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
        no2 = f'<span class="no no2" data-label="line-number">{to}</span>' if moves else ""
        rows.append(f'<div class="{cls}" {S} data-line="{n}"{extra} style="top:{top[n]}px">'
                    f'<span class="no no1{" moves" if moves else ""}" data-label="line-number">{n}</span>{no2}'
                    f'<span class="src" data-code="{view["program"]}" style="padding-left:{indent * 0.6:.2f}em">'
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
            for n in run]
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
                    f'style="top:{top[nob] + LH / 2 + 4:.0f}px">{esc(text.ui("no_break"))}</p>')
    steps = []
    made = rail.print_lines(src, view["path"], [o["text"] for o in view["output"]]) or []
    for k, n in enumerate(made, 1):
        txt = src[n - 1]
        indent = len(txt) - len(txt.lstrip(" "))
        # a line that printed several values (a recursive call, a loop) carries one badge per value, side by side
        x = SRC_X + indent * 0.6 * font + fonts.width("mono", font, txt.strip()) + 22 + made[:k - 1].count(n) * 46
        steps.append(f'<p class="ostep{"" if k <= drawn_out else " new"}" {S} data-step="{k}" data-line="{n}" '
                     f'data-label="output-step" style="left:{x:.0f}px;top:{top[n] + (LH - 40) / 2:.0f}px">{k}</p>')
    return {"rows": f'<div class="rows" {S}>{"".join(rows)}</div>', "rail": svg, "tags": "".join(tags),
            "steps": "".join(steps), "run": run, "nob": nob, "tag_list": rail.tags(src, run, shown_lines)}


def scene_html(lesson, scene, index, count, timing):
    theme = timing.get("theme", DEFAULT_THEME)
    t, ty = _theme(theme)
    frame = t["frame"]
    L = _layout(lesson)
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
            f"d.to(q('.rail{O}, .tag{O}, .badge{O}, .ostep{O}'), {{ opacity: 0, duration: 0.3, ease: 'power1.out' }}, 0);",
            f"d.to(q('.hl'), {{ opacity: 0, duration: 0.25 }}, 0);",
            # the output, the gutter and the file name stay on screen through the diff (WP9 Part A)
            f"d.fromTo(q('.band.minus'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.05);",
            f"d.fromTo(q('.band.minus .strike'), {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.25, ease: 'power2.out' }}, 0.08);",
            f"d.to(q('.ln[data-gone]'), {{ color: '{t['correction']}', duration: 0.2 }}, 0.05);",
            # a removed row fades while the rows below close over it, so no hole opens
            f"d.to(q('.ln[data-gone], .band.minus'), {{ opacity: 0, duration: 0.6, ease: 'none' }}, 0.45);",
            f"d.to(q('.ln{O}[data-to]'), {{ color: '{t['label']}', duration: 0.3 }}, 0.45);",
            f"d.to(q('.ln{O} .no1.moves'), {{ opacity: 0, duration: 0.3 }}, 0.45);",
        ]
        for n_old, n_new in keep.items():
            dy = gc["top"][n_new] - go["top"][n_old]
            if abs(dy) > 0.01:
                morph_js.append(f"d.to(q('.ln{O}[data-line=\"{n_old}\"]'), {{ y: {dy:.1f}, duration: 0.6, ease: 'power2.inOut' }}, 0.45);")
        morph_js += [
            # a moving row's number cross-fades while it slides; an added row fills its slot as the slot opens
            f"d.fromTo(q('.ln{O} .no2'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.3 }}, 0.45);",
            f"d.fromTo(q('.ln.add'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.6, ease: 'power2.out' }}, 0.45);",
            f"d.fromTo(q('.ln.add .src'), {{ x: 18 }}, {{ x: 0, duration: 0.6, ease: 'power2.out' }}, 0.45);",
            f"d.to(q('.file[data-set=\"old\"]'), {{ opacity: 0, duration: 0.2 }}, 0.85);",
            f"d.fromTo(q('.file[data-set=\"cur\"]'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.2 }}, 0.85);",
            f"d.fromTo(q('.band.plus'), {{ opacity: 0 }}, {{ opacity: 1, duration: 0.45 }}, 0.45);",
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
                f'<span class="step" data-label="output-step">{k}</span>'
                f'<span class="val" data-fact="{esc(o["fact"])}">{esc(o["text"])}</span></div>')
    for k, o in enumerate(before_out if morph else [], 1):
        outs.append(out_div("out", "old", k, o))
    prev_out = {o["fact"] for o in before_out} if not morph else set()
    for k, o in enumerate(cur["output"], 1):
        outs.append(out_div("out" + ("" if o["fact"] in prev_out else " out-new"), "cur", k, o))
    outcard = (f'<div class="outcard" data-key="output"><p class="outlabel" data-chrome="output_label">'
               f'{esc(text.ui("output_label").upper())}</p>{"".join(outs)}</div>') if has_out else ""
    vars_html = " ".join(f'<span data-code="{cur["program"]}">{esc(k)} = {esc(v)}</span>' for k, v in cur["vars"].items())
    q = scene.get("question")
    panel_top = shift + 70
    panel_w = L["side_w"]
    panel_h = L["card_h"] - panel_top
    nt = ty["note"]
    if q:
        side = (f'<div class="panel qcard" data-key="question"><p class="qlabel" data-chrome="question_label">'
                f'{esc(text.ui("question_label"))}</p><p class="qtext" data-question="{esc(sid)}">{esc(q["prompt"])}</p></div>')
    elif mode is None:
        sizes = tuple(round(x * nt["scale"]) for x in (64, 58, 52, 48, 44))
        note_px = _fit(nt["key"], claims[note_claim]["text"], panel_w - 84, panel_h - 76, 1.18, sizes)
        side = (f'<div class="panel notecard" data-key="note"><p class="note" data-claim="{esc(note_claim)}" '
                f'style="font-size:{note_px}px">{esc(claims[note_claim]["text"])}</p></div>')
    else:
        side = ""
    if morph:
        # while the program changes, the note column says what changes (the note itself states the new
        # program's behaviour, so it waits for the diff to finish)
        fo, fn = lesson.program(before["program"])["path"].split("/")[-1], lesson.program(cur["program"])["path"].split("/")[-1]
        diff_rows = "".join(f'<p class="dl {k}"><span class="mark" data-label="diff-mark">{"+" if k == "plus" else MINUS}</span>'
                            f'<span data-code="{pid}">{esc(src_[n - 1].strip())}</span></p>'
                            for k, ns, src_, pid in (("minus", removed, go["src"], before["program"]), ("plus", added, gc["src"], cur["program"]))
                            for n in ns)
        side += (f'<div class="panel changecard"><p class="qlabel" data-chrome="morph_label">{esc(text.ui("morph_label"))}</p>'
                 f'<p class="files" data-chrome="morph_files">{esc(text.ui("morph_files", old=fo, new=fn))}</p>{diff_rows}</div>')
    # --- the mechanism panel: the state before this scene, with this scene's state faded in over it
    mech_html = ""
    if mode:
        px, py, pw, ph = L["panel_box"]
        # a side panel is drawn wider when the frame's box is wider than the panel is tall, so it fills the box
        pw_ = None
        if mode == "side":
            h0 = mech.max_height(lesson, "wide", notes=False)
            pw_ = int(min(640, max(mech.WIDTHS[("wide", "side")], pw * h0 / ph)))
        mh = mech.max_height(lesson, "wide", notes=False, width=pw_)
        fit = 'preserveAspectRatio="xMidYMin meet"'
        cur_svg, _f, _c = mech.svg_fragment(lesson, scene["state"], "wide", theme, attrs=f'class="mlayer mcur" {fit}', height=mh,
                                            notes=False, width=pw_)
        layers = cur_svg
        if replay and scene["before"] != scene["state"]:
            bef_svg, _f, _c = mech.svg_fragment(lesson, scene["before"], "wide", theme, attrs=f'class="mlayer mbefore" {fit}',
                                                height=mh, notes=False, width=pw_)
            layers = bef_svg + cur_svg
        mech_html = f'<div class="mechbox" data-key="panel">{layers}</div>' if not q else ""
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
    if grow:
        js.append(f"d.fromTo(q('.sidebody'), {{ y: {-shift} }}, {{ y: 0, duration: 0.45, ease: 'power2.inOut' }}, {max(0.0, oa - 0.5):.3f});")
        js.append(f"d.fromTo(q('.outcard'), {{ opacity: 0, y: -12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }}, {max(0.0, oa - 0.15):.3f});")
    js.append(f"if (q('.out-new').length) d.fromTo(q('.out-new'), {{ opacity: 0, x: -16 }}, "
              f"{{ opacity: 1, x: 0, duration: 0.3, stagger: {OUT_STEP}, ease: 'power2.out' }}, {oa:.3f});")
    js.append(f"if (q('.ostep{S}.new').length) d.fromTo(q('.ostep{S}.new'), {{ opacity: 0, scale: 0.6 }}, "
              f"{{ opacity: 1, scale: 1, duration: 0.3, stagger: {OUT_STEP}, ease: 'back.out(2)' }}, {oa:.3f});")
    if morph:
        js.append(f"d.to(q('.out[data-set=\"old\"]'), {{ opacity: 0, duration: 0.25 }}, {oa:.3f});")

    if mode and has_out and not before_out:
        js.append(f"d.fromTo(q('.outcard'), {{ opacity: 0, y: -12 }}, {{ opacity: 1, y: 0, duration: 0.3, ease: 'power2.out' }}, {max(0.0, oa - 0.15):.3f});")
    if mode and not q and replay and scene["before"] != scene["state"]:
        # the panel: this scene's state fades in over the previous one, which then fades out (removed parts go)
        js.append("d.fromTo(q('.mcur'), { opacity: 0 }, { opacity: 1, duration: 0.45, ease: 'power1.out' }, 0);")
        js.append("d.to(q('.mbefore'), { opacity: 0, duration: 0.3, ease: 'power1.in' }, 0.45);")
    vars_p = (f'<p class="vars"><span class="varlabel" data-chrome="vars_label">{esc(text.ui("vars_label").upper())}</span>'
              f'{vars_html}</p>') if mode is None else ""
    panel_css = ""
    if mode:
        bx, by, bw, bh = L["panel_box"]
        ox, oy, ow, ohh = _out_rect(L)
        panel_css = (f".mechbox {{ position:absolute; left:{bx}px; top:{by}px; width:{bw}px; height:{bh}px; }}\n"
                     f".mlayer {{ position:absolute; left:0; top:0; width:100%; height:100%; }}\n"
                     f".outcard {{ left:{ox}px; top:{oy}px; width:{ow}px; height:{ohh}px; }}\n"
                     f".panel.pbox {{ left:{bx}px; top:{by}px; width:{bw}px; height:{bh}px; bottom:auto; }}\n")
        side = side.replace('class="panel qcard"', 'class="panel qcard pbox"')
    font = L["font"]
    kt, dt, bt, lt, vt, ct = ty["kicker"], ty["display"], ty["body"], ty["label"], ty["value"], ty["code"]
    card_border = f"border:2px solid {t['rule']};" if frame.get("card_border") else ""
    panel_fill = f"background:{t['note_tint']};" if frame.get("panel_fill") else ""
    panel_rule = f"border-left:4px solid {t['rule'] if frame.get('panel_divider') else t['note']};"
    title_px = 60 if dt["key"] == "sans" else 64
    return _guard_tweens(f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(scene['title'])}</title></head>
<body><template>
<style>
{font_faces()}
#root-{sid} {{ position:absolute; inset:0; color:{t['ink']}; font-family:{bt['family']};
  font-variant-numeric:lining-nums tabular-nums; overflow:hidden; }}
.bg {{ position:absolute; inset:0; background:{t['ground']}; }}
.kicker {{ position:absolute; left:{MX}px; top:52px; margin:0; display:flex; align-items:center; font:{kt['weight']} 24px/1.2 {kt['family']};
  letter-spacing:.12em; color:{t['label']}; }}
.count {{ margin-left:24px; padding-left:24px; border-left:2px solid {t['rule']}; font:500 24px/1.2 {ct['family']}; letter-spacing:.04em; color:{t['label']}; }}
.title {{ position:absolute; left:{MX}px; top:90px; margin:0; font:{dt['weight']} {title_px}px/1.15 {dt['family']}; letter-spacing:-.015em; color:{t['ink']}; }}
.file[data-set="cur"] {{ opacity:{0 if morph else 1}; }}
.file {{ position:absolute; left:{MX}px; width:{L['card_w'] - 24}px; top:{L['code_top'] - 38}px; margin:0; text-align:right;
  font:600 24px/1.2 {ct['family']}; color:{t['label']}; }}
.code {{ position:absolute; left:{MX}px; top:{L['code_top']}px; width:{L['card_w']}px; height:{L['card_h']}px; background:{t['surface']};
  {card_border} border-radius:22px; box-sizing:border-box; overflow:hidden; }}
.rows {{ position:absolute; inset:0; }}
.rows.hidden {{ opacity:0; }}
.ln {{ position:absolute; left:0; right:0; height:{LH}px; font:400 {font}px/{LH}px {ct['family']}; white-space:pre; color:{t['label']}; }}
.ln.exec {{ color:{t['ink']}; }}
.ln.add {{ color:{t['label']}; }}
.no {{ position:absolute; left:0; width:{NUM_X}px; text-align:right; color:{t['faint']}; font-size:{max(13, font - 8)}px; }}
.no2 {{ opacity:1; }}
.ln[data-to] .no2 {{ opacity:0; }}
.ln.add .no2 {{ color:{t['value']}; opacity:1; }}
.src {{ position:absolute; left:{SRC_X}px; }}
.kw {{ font-weight:700; }}
.str {{ color:{t['ink_soft']}; }}
.band {{ position:absolute; left:0; right:0; height:{LH}px; opacity:0; }}
.band.plus {{ background:{_rgba(t['value'], 0.14)}; border-left:6px solid {t['value']}; box-sizing:border-box; }}
.band.minus {{ background:{_rgba(t['correction'], 0.16)}; border-left:6px solid {t['correction']}; box-sizing:border-box; }}
.strike {{ position:absolute; left:{SRC_X - 6}px; right:300px; top:{LH / 2 - 1.5:.1f}px; height:3px; background:{t['correction']}; transform-origin:0 50%; }}
.hl {{ position:absolute; left:{SRC_X - 14}px; right:20px; top:0; height:{LH}px; background:{t['highlight']}; border-left:6px solid {t['note']}; border-radius:8px; }}
.rail {{ position:absolute; left:0; top:0; width:{L["card_w"] - 4}px; height:{L['card_h'] - 4}px; overflow:visible; }}
.seg {{ fill:none; stroke:{t['note']}; stroke-width:4; stroke-linecap:round; stroke-dasharray:1; stroke-dashoffset:0; }}
.seg.new {{ stroke-dashoffset:1; }}
.head, .dot {{ fill:{t['note']}; }}
.head.new, .dot.new, .tag.new, .badge.new, .ostep.new {{ opacity:0; }}
.tag {{ position:absolute; right:28px; margin:0; height:{LH}px; font:500 24px/{LH}px {ct['family']}; color:{t['note']}; }}
.tag.muted {{ color:{t['label']}; }}
.badge {{ position:absolute; right:24px; margin:0; padding:0 16px; height:40px; transform-origin:100% 50%;
  font:700 24px/38px {ct['family']}; color:{t['correction']}; background:{t['correction_tint']}; border:2px solid {t['correction']}; border-radius:20px; box-sizing:border-box; }}
.ostep {{ position:absolute; margin:0; width:40px; height:40px; border-radius:20px; box-sizing:border-box; text-align:center;
  font:700 22px/40px {ct['family']}; color:{t['ground']}; background:{t['value']}; }}
.side {{ position:absolute; left:{L['side_x']}px; top:{L['code_top']}px; width:{L['side_w']}px; height:{L['card_h']}px; overflow:hidden; }}
.sidebody {{ position:absolute; inset:0; }}
.outcard {{ position:absolute; left:0; top:0; width:{L['side_w']}px; height:{out_h}px; background:{t['surface']}; {card_border} border-radius:22px; box-sizing:border-box; }}
.outlabel {{ position:absolute; left:34px; top:28px; margin:0; font:{lt['weight']} 22px/1.2 {lt['family']}; letter-spacing:.12em; color:{t['label']}; }}
.out {{ position:absolute; left:34px; height:76px; font:{vt['weight']} 52px/76px {vt['family']}; color:{t['value']}; }}
.step {{ display:inline-block; width:58px; font-size:26px; font-weight:500; color:{t['faint']}; vertical-align:top; }}
.vars {{ position:absolute; left:4px; top:{shift}px; margin:0; font:500 30px/1.3 {ct['family']}; color:{t['ink_soft']}; }}
.varlabel {{ font:{lt['weight']} 22px/1.3 {lt['family']}; letter-spacing:.12em; color:{t['label']}; margin-right:18px; }}
.panel {{ position:absolute; left:0; top:{panel_top}px; width:{L['side_w']}px; bottom:0; box-sizing:border-box; border-radius:{22 if frame.get('panel_fill') else 0}px; padding:30px 38px; }}
.notecard {{ {panel_fill} {panel_rule} }}
.note {{ margin:0; font:{nt['weight']} 50px/1.18 {nt['family']}; color:{t['note']}; }}
.qcard {{ {panel_fill} border:3px solid {t['note']}; border-radius:22px; }}
.changecard {{ {panel_fill} {panel_rule} }}
.changecard .files {{ margin:0 0 18px; font:600 30px/1.3 {ct['family']}; color:{t['ink']}; }}
.changecard .dl {{ margin:0 0 8px; font:400 30px/1.3 {ct['family']}; color:{t['ink']}; white-space:pre; }}
.changecard .mark {{ display:inline-block; width:40px; font-weight:700; }}
.changecard .plus .mark {{ color:{t['value']}; }}
.changecard .minus .mark {{ color:{t['correction']}; }}
.qlabel {{ margin:0 0 14px; font:700 24px/1.2 {lt['family']}; letter-spacing:.14em; text-transform:uppercase; color:{t['note']}; }}
.qtext {{ margin:0; font:500 {round(46 * bt['scale'])}px/1.24 {bt['family']}; color:{t['ink']}; }}
{panel_css}
.footrule {{ position:absolute; left:{MX}px; right:{MX}px; top:{H - BOTTOM + 22}px; height:2px; background:{t['rule']}; opacity:.6; }}
.foot {{ position:absolute; right:{MX}px; top:{H - BOTTOM + 36}px; margin:0; font:400 20px/1.2 {ct['family']}; letter-spacing:.06em; color:{t['label']}; }}
</style>
<div id="root-{sid}" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-program="{cur['program']}"
  data-state="{scene['state']}" data-before="{scene['before']}" data-theme="{theme}" data-swap="{swap if morph else ''}">
  <div class="bg"></div>
  <p class="kicker"><span data-chrome="kicker">{esc(kicker)}</span><span class="count" data-label="chapter-count">{index + 1} / {count}</span></p>
  <h1 class="title" data-label="scene-title">{esc(scene['title'])}</h1>
  {files}
  <div class="code" id="code-{sid}" data-key="code">
    {morph_html}
    <div class="hl" style="transform:translateY({hl_from - LH / 2:.1f}px)"></div>
    {''.join(s['rows'] for s in sets)}
    {''.join(s['rail'] for s in sets)}
    {''.join(s['tags'] + s['steps'] for s in sets)}
  </div>
  {mech_html}
  <div class="side">
    {outcard}
    <div class="sidebody">
      {vars_p}
      {side if mode is None else ''}
    </div>
  </div>
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
