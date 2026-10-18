"""Narrated video projector: per-scene HyperFrames sub-compositions, batched Kokoro TTS,
schedule from measured durations, WebVTT captions + chapters, LUFS normalisation, sandboxed render, mux.

Timeline rule (AC-5.3, E17, D18.2):
    segment n starts after segment n-1 ends + gap (0.35 s in a scene, 0.8 s across scenes,
    plus a 3 s think pause after a question scene); durations are measured from the trimmed audio.
    A scene's state change starts at its last segment's start (`reveal`) and is settled
    0.5 s later (`shown`). The IVE uses `shown`, never a time inside the tween.

Outputs in build/video/: lesson.mp4, captions.vtt, chapters.vtt, transcript.txt, timing.json,
narration.wav, composition/ (index.html + compositions/<scene>.html), work/ (intermediates).
"""
import json
import math
import shutil

from .. import errors, fonts, host, node, text, tts
from . import path as rail
from ..text import esc

FPS = 30
W, H = 1920, 1080
LEAD, GAP_IN, GAP_SCENE, THINK, TAIL, SCENE_LEAD = 0.8, 0.35, 0.8, 3.0, 1.6, 0.35
SETTLE = 0.5
KEYWORDS = {"int", "switch", "case", "break", "return", "void", "char", "default"}


def _frame(t):
    return round(round(t * FPS) / FPS, 4)


def segments_of(lesson):
    segs = []
    for sc in lesson.data["storyboard"]:
        for i, n in enumerate(sc["narration"]):
            spoken = tts.apply_lexicon(n.get("spoken") or n["text"])
            segs.append({"id": f"{sc['id']}.{i}", "scene": sc["id"], "text": n["text"], "spoken": spoken,
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


def draw_plan(lesson, before_sid, sid, budget=None):
    """The path segments a scene draws, in execution order, with offsets from the reveal (seconds).

    Same program: only the segments past the `before` state's path. New program: the whole path,
    first dot at 0. Returns {"steps": [{"a", "b", "kind", "t0", "dur"}], "first": line or None,
    "outputs_at": offset where new output values appear, "total": offset when everything is settled}.
    """
    cur = lesson.state(sid)["state"]
    old = lesson.state(before_sid)["state"] if before_sid else None
    same = old is not None and old["program"] == cur["program"]
    old_segs = {(a, b) for a, b, _k in rail.segments(old["path"])} if same else set()
    steps, t = [], 0.0
    first = None if same else (cur["path"][0] if cur["path"] else None)
    if first is not None:
        t = 0.15
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
    ends = [st["t0"] + st["dur"] + (0.33 if st["a"] == nob else 0.1) for st in steps] + [t + 0.1]
    if new_out:
        ends.append(outputs_at + (len(new_out) - 1) * OUT_STEP + 0.3)
    total = max(max(ends), SETTLE)
    # a short scene plays the same drawing faster (a nested timeline with timeScale 1/k), never cut off
    k = min(1.0, budget / total) if budget else 1.0
    return {"steps": steps, "first": first, "outputs_at": outputs_at, "total": round(total * k, 3), "k": round(k, 4)}


def plan_screen(lesson, scenes):
    """The one owner of what the frame shows (review P1-3). Per scene it sets:

    before   the state on screen until `reveal` (the previous scene's state, or this scene's own);
    reveal   when this scene starts drawing its new path segments;
    shown    when the new state is fully drawn (the IVE switches its cue here, D18.2);
    replay   False when the state was already shown earlier (a recap): it appears settled at the
             scene start, with no reset and no replay.

    A scene that changes program reveals at its start, so the frame never shows a program the
    explorer does not. Both video.scene_html and ive.cues read these fields.
    """
    seen, prev = set(), None
    for i, s in enumerate(scenes):
        sid = s["state"]
        if i == 0 or sid == prev or sid in seen:
            s.update(before=sid, reveal=s["start"], shown=s["start"], replay=False, draw_total=0.0)
        else:
            prog_change = lesson.state(prev)["state"]["program"] != lesson.state(sid)["state"]["program"]
            reveal = s["start"] if prog_change else s["reveal"]
            plan = draw_plan(lesson, prev, sid, budget=DRAW_BUDGET * (s["end"] - reveal))
            settled = math.ceil(round((reveal + plan["total"]) * FPS, 6)) / FPS  # first frame with nothing moving
            s.update(before=prev, reveal=reveal, shown=round(min(settled, s["end"] - 1 / FPS), 4),
                     replay=True, draw_total=plan["total"])
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
        filters.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=mono,atrim=duration={c['end'] - c['start']:.4f}[a{n}]")
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

def _state_view(lesson, sid):
    st = lesson.state(sid)["state"]
    facts = lesson.by_id("facts")
    return {"program": st["program"], "line": st["line"], "path": st.get("path", []),
            "output": [{"fact": f, "text": text.display(facts[f])} for f in st["output"]],
            "vars": st.get("vars", {})}


def _code_html(line_txt):
    import re
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
#  ┌ kicker / title ─────────────────────────────────────────────── n / N ┐   56..170
#  ┌ code card ───────────────────────────┐  ┌ output card ──────────────┐   212
#  │ 4 ● int n = 2;                       │  │ OUTPUT  1 two  2 three    │
#  │ 5 ●╮ switch (n) {                    │  └───────────────────────────┘
#  │ 6  │   case 1:             skipped   │  VARIABLES n = 2
#  │ 8 ◀╯   case 2:         enters here   │  ┌ note / question card ─────┐
#  │ 9 ●      puts("two");   [no break]   │  │ claim text (Caveat)       │
#  │ ...                                  │  │                           │
#  └──────────────────────────────────────┘  └───────────────────────────┘   1016
MX, CODE_TOP, BOTTOM = 96, 212, 64
CARD_W, SIDE_X, SIDE_W = 1060, 1200, 624
ROW_PAD = 28  # minimum, rows are centred
NUM_X, RAIL_X, SRC_X, BULGE = 58, 124, 170, 46


def _layout(lesson):
    """Row height from the longest program body in the storyboard, so every scene shares one grid."""
    rows = 1
    for sc in lesson.data["storyboard"]:
        src = lesson.program_source(lesson.state(sc["state"])["state"]["program"]).split("\n")
        first, last = rail.body_range(src)
        rows = max(rows, last - first + 1)
    card_h = H - BOTTOM - CODE_TOP
    line_h = int((card_h - 2 * ROW_PAD) // rows)
    max_out = max(len(lesson.state(sc["state"])["state"]["output"]) for sc in lesson.data["storyboard"])
    return {"card_h": card_h, "line_h": line_h, "font": min(36, int(line_h * 0.64)), "max_out": max(max_out, 1)}


def _fit(font, s, width, height, lh, sizes):
    """The largest size whose wrapped lines fit the box (the last size if none does)."""
    for px in sizes:
        if len(fonts.wrap(font, px, s, width)) * px * lh <= height:
            return px
    return sizes[-1]


def scene_html(lesson, scene, index, count, timing):
    t = fonts.tokens()["themes"]["light"]
    L = _layout(lesson)
    LH = L["line_h"]
    sid = scene["id"]
    cur = _state_view(lesson, scene["state"])
    replay = scene["replay"]
    before = _state_view(lesson, scene["before"]) if replay else cur
    same_prog = before["program"] == cur["program"]
    plan = draw_plan(lesson, scene["before"], scene["state"],
                     budget=DRAW_BUDGET * (scene["end"] - scene["reveal"])) if replay else \
        {"steps": [], "first": None, "outputs_at": 0.0, "total": 0.0, "k": 1.0}
    src = lesson.program_source(cur["program"]).split("\n")
    first, last = rail.body_range(src)
    lines = [(n, src[n - 1]) for n in range(first, last + 1)]
    row = {n: i for i, (n, _) in enumerate(lines)}
    pad = round((L["card_h"] - 4 - len(lines) * LH) / 2)  # rows centred in the card
    cy = {n: pad + row[n] * LH + LH / 2 for n in row}
    old_path = before["path"] if (replay and same_prog) else ([] if replay else cur["path"])
    reveal = round(scene["reveal"] - scene["start"], 3)
    claims = lesson.by_id("claims")
    sb = next(x for x in lesson.data["storyboard"] if x["id"] == sid)
    note_claim = sb["narration"][0]["claims"][0]
    run = [n for n in cur["path"] if n in row]
    shown_lines = [n for n, _ in lines]
    nob = rail.nobreak_after(src, run)
    tags = rail.tags(src, run, shown_lines)
    old_segs = {(a, b) for a, b, _k in rail.segments([n for n in old_path if n in row])}

    code_rows = []
    for n, txt in lines:
        indent = len(txt) - len(txt.lstrip(" "))
        cls = "ln exec" if n in old_path else ("ln exec-new" if n in cur["path"] else "ln")
        code_rows.append(f'<div class="{cls}" data-line="{n}" style="top:{pad + row[n] * LH}px">'
                         f'<span class="no" data-label="line-number">{n}</span>'
                         f'<span class="src" data-code="{cur["program"]}" style="padding-left:{indent * 0.6:.2f}em">'
                         f'{_code_html(txt.strip())}</span></div>')
    # rail: segments, arrowheads, dots (seek-safe: every element has a fixed final geometry)
    segs, heads = [], []
    for a, b, kind in rail.segments(run):
        drawn = (a, b) in old_segs
        if kind == "run":
            d = f"M{RAIL_X},{cy[a]:.1f} L{RAIL_X},{cy[b]:.1f}"
        else:
            d = (f"M{RAIL_X},{cy[a]:.1f} C{RAIL_X - BULGE},{cy[a]:.1f} {RAIL_X - BULGE},{cy[b]:.1f} "
                 f"{RAIL_X - 9},{cy[b]:.1f}")
            heads.append(f'<path class="head{"" if drawn else " new"}" data-seg="{a}-{b}" '
                         f'd="M{RAIL_X - 24},{cy[b] - 10:.1f} L{RAIL_X - 6},{cy[b]:.1f} L{RAIL_X - 24},{cy[b] + 10:.1f} Z"/>')
        segs.append(f'<path class="seg{"" if drawn else " new"}" data-seg="{a}-{b}" data-kind="{kind}" pathLength="1" d="{d}"/>')
    dots = [f'<circle class="dot{"" if n in old_path else " new"}" data-line="{n}" cx="{RAIL_X}" cy="{cy[n]:.1f}" r="8"/>'
            for n in run]
    tag_html = []
    for n, key, tone in tags:
        on = any(a < n < b for a, b in old_segs) if key == "skipped_label" else n in old_path
        tag_html.append(f'<p class="tag {tone}{"" if on else " new"}" data-line="{n}" data-chrome="{key}" '
                        f'style="top:{pad + row[n] * LH}px">{esc(text.ui(key))}</p>')
    if nob:
        on = nob in old_path and (nob + 1) in old_path
        tag_html.append(f'<p id="nobreak" class="badge{"" if on else " new"}" data-after="{nob}" data-chrome="no_break" '
                        f'style="top:{pad + row[nob] * LH + LH / 2 + 4:.0f}px">{esc(text.ui("no_break"))}</p>')
    outs = []
    prev_out = {o["fact"] for o in before["output"]} if (replay and same_prog) else ({} if replay else
                                                                                     {o["fact"] for o in cur["output"]})
    OUT_H = 84
    for k, o in enumerate(cur["output"], 1):
        cls = "out" + ("" if o["fact"] in prev_out else " out-new")
        outs.append(f'<div class="{cls}" style="top:{84 + (k - 1) * OUT_H}px"><span class="step" data-label="output-step">{k}</span>'
                    f'<span class="val" data-fact="{esc(o["fact"])}">{esc(o["text"])}</span></div>')
    vars_html = " ".join(f'<span data-code="{cur["program"]}">{esc(k)} = {esc(v)}</span>' for k, v in cur["vars"].items())
    q = scene.get("question")
    out_h = 84 + L["max_out"] * OUT_H + 20
    if q:
        side = (f'<div id="qcard" class="panel qcard" data-key="question"><p class="qlabel" data-chrome="question_label">'
                f'{esc(text.ui("question_label"))}</p><p class="qtext" data-question="{esc(sid)}">{esc(q["prompt"])}</p></div>')
    else:
        note_px = _fit("hand", claims[note_claim]["text"], SIDE_W - 76, L["card_h"] - out_h - 100 - 64, 1.16,
                       (64, 58, 52, 48, 44))
        side = (f'<div class="panel notecard" data-key="note"><p class="note" data-claim="{esc(note_claim)}" '
                f'style="font-size:{note_px}px">{esc(claims[note_claim]["text"])}</p></div>')
    kicker = text.ui("kicker", topic=lesson.data["topic"]).upper()
    if not replay:
        hl_line = cur["line"]
    elif same_prog:
        hl_line = before["line"]
    else:
        hl_line = plan["first"] or cur["line"]
    hl_from = cy.get(hl_line, cy[run[0]] if run else LH / 2)
    js_steps = []
    for st in plan["steps"]:
        a, b = st["a"], st["b"]
        t0 = f"{st['t0']:.3f}"
        js_steps.append(f"d.to(q('.seg[data-seg=\"{a}-{b}\"]'), {{ strokeDashoffset: 0, duration: {st['dur']}, ease: 'power1.inOut' }}, {t0});")
        js_steps.append(f"d.to(q('#hl'), {{ y: {cy[b] - LH / 2:.1f}, duration: {st['dur']}, ease: 'power1.inOut' }}, {t0});")
        end = f"{st['t0'] + st['dur']:.3f}"
        js_steps.append(f"d.to(q('.dot[data-line=\"{b}\"], .head[data-seg=\"{a}-{b}\"], .tag[data-line=\"{b}\"]'), "
                        f"{{ opacity: 1, duration: 0.12 }}, {end} - 0.06);")
        js_steps.append(f"d.to(q('.ln[data-line=\"{b}\"]'), {{ color: '{t['ink']}', duration: 0.2 }}, {end} - 0.1);")
        if st["kind"] == "jump":
            for n in shown_lines:
                if a < n < b and (n, "skipped_label", "muted") in tags:
                    js_steps.append(f"d.to(q('.tag[data-line=\"{n}\"]'), {{ opacity: 1, duration: 0.2 }}, {t0} + {st['dur'] / 2:.3f});")
        if nob and a == nob:
            js_steps.append(f"d.fromTo(q('#nobreak'), {{ opacity: 0, scale: 0.8 }}, {{ opacity: 1, scale: 1.08, duration: 0.18, ease: 'power2.out' }}, {end} - 0.1);")
            js_steps.append(f"d.to(q('#nobreak'), {{ scale: 1, duration: 0.25, ease: 'power2.inOut' }}, {end} + 0.08);")
    if plan["first"] is not None:
        f0 = plan["first"]
        js_steps.insert(0, f"d.to(q('.dot[data-line=\"{f0}\"], .tag[data-line=\"{f0}\"]'), {{ opacity: 1, duration: 0.12 }}, 0);"
                           f"d.to(q('.ln[data-line=\"{f0}\"]'), {{ color: '{t['ink']}', duration: 0.2 }}, 0);")
    js_steps.append(f"if (q('.out-new').length) d.fromTo(q('.out-new'), {{ opacity: 0, x: -16 }}, "
                    f"{{ opacity: 1, x: 0, duration: 0.3, stagger: {OUT_STEP}, ease: 'power2.out' }}, {plan['outputs_at']:.3f});")
    font = L["font"]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(scene['title'])}</title></head>
<body><template>
<style>
{font_faces()}
#root {{ position:absolute; inset:0; background:{t['paper']}; color:{t['ink']}; font-family:'Source Serif 4',serif;
  font-variant-numeric:lining-nums tabular-nums; overflow:hidden; }}
.kicker {{ position:absolute; left:{MX}px; top:56px; margin:0; font:600 24px/1.2 'JetBrains Mono',monospace; letter-spacing:.12em; color:{t['blue']}; }}
.count {{ position:absolute; right:{MX}px; top:56px; margin:0; font:500 24px/1.2 'JetBrains Mono',monospace; color:{t['muted']}; }}
.title {{ position:absolute; left:{MX}px; top:92px; margin:0; font:600 64px/1.15 'Source Serif 4',serif; letter-spacing:-.01em; }}
.file {{ position:absolute; left:{MX}px; width:{CARD_W - 24}px; top:{CODE_TOP - 38}px; margin:0; text-align:right;
  font:600 24px/1.2 'JetBrains Mono',monospace; color:{t['muted']}; }}
.code {{ position:absolute; left:{MX}px; top:{CODE_TOP}px; width:{CARD_W}px; height:{L['card_h']}px; background:{t['card']};
  border:2px solid {t['rule']}; border-radius:22px; box-sizing:border-box; overflow:hidden; }}
.ln {{ position:absolute; left:0; right:0; height:{LH}px; font:500 {font}px/{LH}px 'JetBrains Mono',monospace; white-space:pre; color:{t['muted']}; }}
.ln.exec {{ color:{t['ink']}; }}
.no {{ position:absolute; left:0; width:{NUM_X}px; text-align:right; color:{t['faint']}; font-size:{font - 8}px; }}
.src {{ position:absolute; left:{SRC_X}px; }}
.kw {{ font-weight:800; }}
.str {{ color:{t['soft']}; }}
.hl {{ position:absolute; left:{SRC_X - 14}px; right:20px; top:0; height:{LH}px; background:{t['hl']}; border-left:6px solid {t['blue']}; border-radius:8px; }}
.rail {{ position:absolute; left:0; top:0; width:{CARD_W - 4}px; height:{L['card_h'] - 4}px; overflow:visible; }}
.seg {{ fill:none; stroke:{t['blue']}; stroke-width:4; stroke-linecap:round; stroke-dasharray:1; stroke-dashoffset:0; }}
.seg.new {{ stroke-dashoffset:1; }}
.head {{ fill:{t['blue']}; }}
.dot {{ fill:{t['blue']}; }}
.head.new, .dot.new, .tag.new, .badge.new {{ opacity:0; }}
.tag {{ position:absolute; right:28px; margin:0; height:{LH}px; font:500 24px/{LH}px 'JetBrains Mono',monospace; color:{t['blue']}; }}
.tag.muted {{ color:{t['muted']}; }}
.badge {{ position:absolute; right:24px; margin:0; padding:0 16px; height:40px; transform-origin:100% 50%;
  font:700 24px/38px 'JetBrains Mono',monospace; color:{t['red']}; background:{t['red_tint']}; border:2px solid {t['red']}; border-radius:20px; box-sizing:border-box; }}
.side {{ position:absolute; left:{SIDE_X}px; top:{CODE_TOP}px; width:{SIDE_W}px; height:{L['card_h']}px; }}
.outcard {{ position:absolute; left:0; top:0; width:{SIDE_W}px; height:{out_h}px; background:{t['card']}; border:2px solid {t['rule']}; border-radius:22px; box-sizing:border-box; }}
.outlabel {{ position:absolute; left:34px; top:28px; margin:0; font:600 22px/1.2 'JetBrains Mono',monospace; letter-spacing:.12em; color:{t['muted']}; }}
.out {{ position:absolute; left:34px; height:76px; font:600 52px/76px 'JetBrains Mono',monospace; }}
.step {{ display:inline-block; width:58px; font-size:26px; font-weight:500; color:{t['faint']}; vertical-align:top; }}
.vars {{ position:absolute; left:4px; top:{out_h + 30}px; margin:0; font:500 30px/1.3 'JetBrains Mono',monospace; color:{t['soft']}; }}
.varlabel {{ font-size:22px; letter-spacing:.12em; color:{t['muted']}; margin-right:18px; }}
.panel {{ position:absolute; left:0; top:{out_h + 100}px; width:{SIDE_W}px; bottom:0; box-sizing:border-box; border-radius:22px; padding:30px 34px; }}
.notecard {{ background:{t['blue_tint']}; border-left:8px solid {t['blue']}; }}
.note {{ margin:0; font:600 50px/1.16 'Caveat',cursive; color:{t['blue']}; }}
.qcard {{ background:{t['blue_tint']}; border:3px solid {t['blue']}; }}
.qlabel {{ margin:0 0 14px; font:700 24px/1.2 'JetBrains Mono',monospace; letter-spacing:.14em; color:{t['blue']}; }}
.qtext {{ margin:0; font:500 46px/1.24 'Source Serif 4',serif; color:{t['ink']}; }}
</style>
<div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}" data-program="{cur['program']}"
  data-state="{scene['state']}" data-before="{scene['before']}">
  <p class="kicker" data-chrome="kicker">{esc(kicker)}</p>
  <p class="count" data-label="chapter-count">{index + 1} / {count}</p>
  <h1 class="title" data-label="scene-title">{esc(scene['title'])}</h1>
  <p class="file" data-label="program-file">{esc(lesson.program(cur['program'])['path'].split('/')[-1])}</p>
  <div class="code" id="code-{sid}" data-key="code">
    <div class="hl" id="hl" style="transform:translateY({hl_from - LH / 2:.1f}px)"></div>
    {''.join(code_rows)}
    <svg class="rail" viewBox="0 0 {CARD_W - 4} {L['card_h'] - 4}" aria-hidden="true">{''.join(segs)}{''.join(heads)}{''.join(dots)}</svg>
    {''.join(tag_html)}
  </div>
  <div class="side">
    <div class="outcard" data-key="output"><p class="outlabel" data-chrome="output_label">{esc(text.ui('output_label').upper())}</p>{''.join(outs)}</div>
    <p class="vars"><span class="varlabel" data-chrome="vars_label">{esc(text.ui('vars_label').upper())}</span>{vars_html}</p>
    {side}
  </div>
</div>
<script>
  window.__timelines = window.__timelines || {{}};
  (function () {{
    var root = document.querySelector('[data-composition-id="{sid}"]');
    var q = function (s) {{ return root.querySelectorAll(s); }};
    var tl = gsap.timeline({{ paused: true }});
    var R = {reveal:.3f};
    tl.fromTo(q('.title'), {{ opacity: 0, y: 18 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, 0.05);
    tl.fromTo(q('.panel'), {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, {0.35 if not index else 0.25});
    if (q('.out-new').length) tl.set(q('.out-new'), {{ opacity: 0 }}, 0);
    if (q('.ln.exec-new').length) tl.set(q('.ln.exec-new'), {{ color: '{t['muted']}' }}, 0);
    var d = gsap.timeline({{ data: 'draw' }});
    {chr(10).join('    ' + j for j in js_steps).strip()}
    d.timeScale({1 / plan['k']:.6f});
    tl.add(d, R);
    tl.set({{}}, {{}}, {scene['duration']:.3f});
    window.__timelines["{sid}"] = tl;
  }})();
</script>
</template></body></html>
"""


def font_faces():
    faces = []
    for key in ("serif", "mono", "hand"):
        spec = fonts.tokens()["fonts"][key]
        faces.append(f"@font-face{{font-family:'{spec['family']}';src:url('fonts/{spec['file']}') format('woff2');"
                     f"font-weight:{spec['weight']};font-style:normal;font-display:block}}")
    return "".join(faces)


def host_html(lesson, timing):
    faces = [font_faces()]
    t = fonts.tokens()["themes"]["light"]
    clips = []
    for s in timing["scenes"]:
        clips.append(f'  <div id="clip-{s["id"]}" data-composition-id="{s["id"]}" data-composition-src="compositions/{s["id"]}.html" '
                     f'data-start="{s["start"]:g}" data-duration="{s["duration"]:g}" data-track-index="1" '
                     f'data-width="{W}" data-height="{H}"></div>')
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width={W}, height={H}">
<title>{esc(lesson.data['title'])}</title>
<style>{''.join(faces)}
html,body{{margin:0;width:{W}px;height:{H}px;background:{t['paper']}}}
#root{{position:relative;width:{W}px;height:{H}px;overflow:hidden;background:{t['paper']}}}</style>
<script src="vendor/gsap.min.js"></script>
</head><body>
<div id="root" data-composition-id="lesson" data-start="0" data-width="{W}" data-height="{H}" data-duration="{timing['duration']:g}" data-fps="{FPS}">
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
    for key in ("serif", "mono", "hand"):
        f = fonts.tokens()["fonts"][key]["file"]
        shutil.copyfile(host.FONTS_DIR / f, comp / "fonts" / f)
    (comp / "hyperframes.json").write_text(json.dumps({"media": {"autoProxy": False}}))
    (comp / "index.html").write_text(host_html(lesson, timing))
    scenes = timing["scenes"]
    for i, s in enumerate(scenes):
        (comp / "compositions" / f"{s['id']}.html").write_text(scene_html(lesson, s, i, len(scenes), timing))


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


def project(lesson, out, tts_engine=None):
    out.mkdir(parents=True, exist_ok=True)
    work = out / "work"
    work.mkdir(exist_ok=True)
    segs = segments_of(lesson)
    syn = tts.synthesize([{"id": s["id"], "spoken": s["spoken"]} for s in segs], work / "tts", force_engine=tts_engine)
    measured = tts.trim_and_measure(syn["segments"], work / "tts")
    timing = schedule(lesson, measured)
    audio = assemble_audio(timing, measured, work, out / "narration.wav")
    write_text_tracks(lesson, timing, out)
    comp = out / "composition"
    write_composition(lesson, timing, comp)
    timing_public = {**timing, "tts": {k: v for k, v in syn.items() if k != "segments"},
                     "segments": [{"id": m["id"], "seconds": m["seconds"]} for m in measured], "audio": audio}
    (out / "timing.json").write_text(json.dumps(timing_public, indent=2, default=str))
    return {"timing": timing_public, "composition": comp, "degraded": syn["degraded"], "tts": syn}


def finish(lesson, out, comp):
    """Render (sandboxed) and mux. Split from project() so the isolation gate can wrap the render."""
    silent, log = render(comp, out / "work", lesson.sha256())
    mp4 = out / "lesson.mp4"
    mux(silent, out / "narration.wav", out, mp4)
    return mp4, log
