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
import shutil

from .. import errors, fonts, host, node, text, tts
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
        s["shown"] = round(min(s["reveal"] + SETTLE, s["end"]), 3) if i else 0.0
    return {"fps": FPS, "duration": total, "cues": cues, "scenes": out_scenes,
            "rule": "start(n) = end(n-1) + gap; durations measured from trimmed TTS audio; shown = reveal + 0.5 s"}


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


def _code_lines(lesson, pid, path):
    """The body of main: from the first statement through `return`, the same in every scene."""
    src = lesson.program_source(pid).split("\n")
    first = min(path) if path else 4
    last = next((i + 1 for i, ln in enumerate(src) if ln.strip().startswith("return")), len(src))
    return [(n, src[n - 1]) for n in range(first, last + 1)]


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


LINE_H = 46
CODE_TOP = 250


def scene_html(lesson, scene, prev_sid, index, count, timing):
    t = fonts.tokens()["themes"]["light"]
    cur = _state_view(lesson, scene["state"])
    prev = _state_view(lesson, prev_sid) if prev_sid else cur
    if prev["program"] != cur["program"]:
        prev = {"program": cur["program"], "line": cur["path"][0] if cur["path"] else cur["line"], "path": [],
                "output": [], "vars": cur["vars"]}
    lines = _code_lines(lesson, cur["program"], cur["path"])
    row = {n: i for i, (n, _) in enumerate(lines)}
    reveal = round(scene["reveal"] - scene["start"], 3) if index else 0.0
    sid = scene["id"]
    claims = lesson.by_id("claims")
    sb = next(s for s in lesson.data["storyboard"] if s["id"] == sid)
    note_claim = sb["narration"][0]["claims"][0]

    code_rows = []
    for n, txt in lines:
        indent = len(txt) - len(txt.lstrip(" "))
        cls = ["ln"]
        if n in prev["path"]:
            cls.append("exec")
        elif n in cur["path"]:
            cls.append("exec-new")
        code_rows.append(f'<div class="{" ".join(cls)}" style="top:{row[n] * LINE_H}px">'
                         f'<span class="no" data-label="line-number">{n}</span>'
                         f'<span class="src" data-code="{cur["program"]}" style="padding-left:{indent * 0.6:.2f}em">'
                         f'{_code_html(txt.strip())}</span></div>')
    dots = []
    for n in cur["path"]:
        if n in row:
            cls = "dot" + ("" if n in prev["path"] else " dot-new")
            dots.append(f'<div class="{cls}" style="top:{row[n] * LINE_H + LINE_H / 2 - 7}px"></div>')
    hl_from = row.get(prev["line"], row.get(cur["line"], 0)) * LINE_H
    hl_to = row.get(cur["line"], 0) * LINE_H
    outs = []
    prev_out = {o["fact"] for o in prev["output"]}
    for k, o in enumerate(cur["output"], 1):
        cls = "out" + ("" if o["fact"] in prev_out else " out-new")
        outs.append(f'<div class="{cls}" style="top:{80 + (k - 1) * 72}px"><span class="step" data-label="output-step">{k}</span>'
                    f'<span class="val" data-fact="{esc(o["fact"])}">{esc(o["text"])}</span></div>')
    vars_html = " ".join(f'<span data-code="{cur["program"]}">{esc(k)} = {esc(v)}</span>' for k, v in cur["vars"].items())
    q = scene.get("question")
    side = ""
    if q:
        side = (f'<div id="qcard" class="qcard"><p class="qlabel" data-chrome="question_label">{esc(text.ui("question_label"))}</p>'
                f'<p class="qtext" data-question="{esc(sid)}">{esc(q["prompt"])}</p></div>')
    else:
        side = f'<p class="note" data-claim="{esc(note_claim)}">{esc(claims[note_claim]["text"])}</p>'
    kicker = text.ui("kicker", topic=lesson.data["topic"]).upper()
    out_h = 80 + max(len(cur["output"]), 1) * 72 + 10
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{esc(scene['title'])}</title></head>
<body><template>
<style>
{font_faces()}
#root {{ position:absolute; inset:0; background:{t['paper']}; color:{t['ink']}; font-family:'Source Serif 4',serif;
  font-variant-numeric:lining-nums tabular-nums; overflow:hidden; }}
.kicker {{ position:absolute; left:120px; top:78px; margin:0; font:600 24px/1.2 'JetBrains Mono',monospace; letter-spacing:.12em; color:{t['blue']}; }}
.count {{ position:absolute; right:120px; top:78px; margin:0; font:500 24px/1.2 'JetBrains Mono',monospace; color:{t['muted']}; }}
.title {{ position:absolute; left:120px; top:118px; margin:0; font:600 66px/1.15 'Source Serif 4',serif; letter-spacing:-.01em; }}
.code {{ position:absolute; left:120px; top:{CODE_TOP}px; width:1000px; height:{len(lines) * LINE_H + 48}px; background:{t['card']};
  border:2px solid {t['rule']}; border-radius:20px; }}
.rows {{ position:absolute; left:0; top:24px; right:0; }}
.ln {{ position:absolute; left:0; right:0; height:{LINE_H}px; font:500 32px/{LINE_H}px 'JetBrains Mono',monospace; white-space:pre; color:{t['muted']}; }}
.ln.exec, .ln.exec-new {{ color:{t['ink']}; }}
.no {{ position:absolute; left:0; width:70px; text-align:right; color:{t['faint']}; font-size:26px; }}
.src {{ position:absolute; left:130px; }}
.kw {{ font-weight:800; }}
.str {{ color:{t['soft']}; }}
.hl {{ position:absolute; left:112px; right:16px; top:0; height:{LINE_H}px; background:{t['hl']}; border-left:6px solid {t['blue']}; border-radius:8px; }}
.rail {{ position:absolute; left:96px; top:24px; }}
.dot {{ position:absolute; left:-7px; width:14px; height:14px; border-radius:7px; background:{t['blue']}; }}
.side {{ position:absolute; left:1180px; top:{CODE_TOP}px; width:620px; }}
.outcard {{ position:absolute; left:0; top:0; width:620px; height:{out_h}px; background:{t['card']}; border:2px solid {t['rule']}; border-radius:20px; }}
.outlabel {{ position:absolute; left:32px; top:26px; margin:0; font:600 22px/1.2 'JetBrains Mono',monospace; letter-spacing:.12em; color:{t['muted']}; }}
.out {{ position:absolute; left:32px; height:64px; font:600 46px/64px 'JetBrains Mono',monospace; }}
.step {{ display:inline-block; width:56px; font-size:24px; font-weight:500; color:{t['faint']}; }}
.vars {{ position:absolute; left:0; top:{out_h + 28}px; margin:0; font:500 30px/1.3 'JetBrains Mono',monospace; color:{t['soft']}; }}
.varlabel {{ font-size:22px; letter-spacing:.12em; color:{t['muted']}; margin-right:18px; }}
.note {{ position:absolute; left:0; top:{out_h + 100}px; width:620px; margin:0; font:600 44px/1.18 'Caveat',cursive; color:{t['blue']}; }}
.qcard {{ position:absolute; left:0; top:{out_h + 96}px; width:620px; padding:28px 32px; box-sizing:border-box; background:{t['blue_tint']};
  border:3px solid {t['blue']}; border-radius:20px; }}
.qlabel {{ margin:0 0 10px; font:700 22px/1.2 'JetBrains Mono',monospace; letter-spacing:.14em; color:{t['blue']}; }}
.qtext {{ margin:0; font:500 40px/1.25 'Source Serif 4',serif; color:{t['ink']}; }}
</style>
<div id="root" data-composition-id="{sid}" data-width="{W}" data-height="{H}">
  <p class="kicker" data-chrome="kicker">{esc(kicker)}</p>
  <p class="count" data-label="chapter-count">{index + 1} / {count}</p>
  <h1 class="title" data-label="scene-title">{esc(scene['title'])}</h1>
  <div class="code" id="code-{sid}">
    <div class="hl" id="hl" style="transform:translateY({hl_from + 24}px)"></div>
    <div class="rows">{''.join(code_rows)}</div>
    <div class="rail">{''.join(dots)}</div>
  </div>
  <div class="side">
    <div class="outcard"><p class="outlabel" data-chrome="output_label">{esc(text.ui('output_label').upper())}</p>{''.join(outs)}</div>
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
    tl.fromTo(q('.note, .qcard'), {{ opacity: 0, y: 14 }}, {{ opacity: 1, y: 0, duration: 0.5, ease: 'power2.out' }}, {0.35 if not index else 0.25});
    if (q('.out-new').length) tl.set(q('.out-new'), {{ opacity: 0 }}, 0);
    if (q('.dot-new').length) tl.set(q('.dot-new'), {{ opacity: 0 }}, 0);
    if (q('.exec-new').length) tl.set(q('.exec-new'), {{ color: '{t['muted']}' }}, 0);
    tl.to(q('#hl'), {{ y: {hl_to + 24}, duration: 0.45, ease: 'power2.inOut' }}, R);
    if (q('.exec-new').length) tl.to(q('.exec-new'), {{ color: '{t['ink']}', duration: 0.3 }}, R + 0.1);
    if (q('.dot-new').length) tl.to(q('.dot-new'), {{ opacity: 1, duration: 0.2, stagger: 0.06 }}, R + 0.1);
    if (q('.out-new').length) tl.fromTo(q('.out-new'), {{ opacity: 0, x: -14 }}, {{ opacity: 1, x: 0, duration: 0.35, stagger: 0.12, ease: 'power2.out' }}, R + 0.15);
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
    prev = None
    for i, s in enumerate(scenes):
        (comp / "compositions" / f"{s['id']}.html").write_text(scene_html(lesson, s, prev, i, len(scenes), timing))
        prev = s["state"]


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
