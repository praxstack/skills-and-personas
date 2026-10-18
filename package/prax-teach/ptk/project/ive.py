r"""Interactive video explorer (IVE): the narrated MP4 plus a WebVTT `metadata` cue track.

Cue-to-state rule (D17.2, D18.2):

    time ─────────────────────────────────────────────────────────────────────────▶
    scene k-1 shown          scene k reveal   scene k shown (= reveal + 0.5 s)
          │ state cue (s_{k-1})      │ [answer cue: still s_{k-1}] │ state cue (s_k) ...
          ▼                          ▼                             ▼
    paused here → explorer at s_{k-1}   paused mid-tween → s_{k-1}    paused here → s_k

    * a cue's state is the last state already settled on screen, never a tween target;
    * a question scene adds a `question` cue (state before the answer);
    * the first reveal after a question adds an `answer` cue at the reveal time; pausing
      0.1 s before it shows no answer anywhere in the DOM, alt text or transcript;
    * a recap of a state already shown on the same program is a cut: frame and explorer switch
      together at the scene start, and no transition cue is needed;
    * a change of program is a diff morph: its transition cue holds the old program's state
      until `shown`, when the frame's rows become the new program's (video.plan_screen).

Clock rule (D20.6): the video's currentTime is the only time source. Cue and chapter windows are
half-open [start, next start), and a time less than one frame before a boundary resolves to the
later window, because browsers round seek targets:

    ──── window k-1 ────┤◀ 1 frame ▶│──── window k ────
                        └─ resolves to k ─┘

FILM / EXPLORE / RETURN (AC-6.6): in FILM the panel follows the cue at currentTime. Pausing or
"Pause and explore" enters EXPLORE, seeded at the film's state; steps and live edits there are
marked as the learner's (a dashed panel, "Your edit, not in the film"). RETURN drops every edit,
seeks back to the paused time and resumes, so the panel shows the film's state again.

file:// (AC-6.7): Chrome refuses <track src="x.vtt"> from a file:// page, so ive-data.js carries the
exact text of captions.vtt, chapters.vtt and states.vtt and the page loads each as a blob: track.
That file is a separate script, not part of the document, so no future state or answer text sits
in the DOM before its cue. Without JS the page shows the poster sequence and the full transcript,
after a heading that says they contain the answers.
"""
import json
import os
import re
import shutil

from .. import errors, host, text
from . import explorer
from . import path as rail
from ..text import esc


def _view(lesson, sid):
    st = lesson.state(sid)
    s = st["state"]
    facts = lesson.by_id("facts")
    src = lesson.program_source(s["program"]).split("\n")
    first, last = rail.body_range(src)
    return {"state_id": sid, "label": st["label"], "program": s["program"],
            "program_path": lesson.program(s["program"])["path"], "line": s["line"], "path": s.get("path", []),
            "code": [[n, src[n - 1]] for n in range(first, last + 1)],
            "output": [{"fact": f, "text": text.display(facts[f])} for f in s["output"]], "vars": s.get("vars", {})}


def cues(lesson, timing):
    """Metadata cues from the screen plan (video.plan_screen): the explorer and the frame read the
    same before/reveal/shown fields, so they cannot disagree about what is on screen."""
    out = []
    answer_pending, prev = None, None
    for sc in timing["scenes"]:
        start = sc["start"]
        # a cut to a new state (recap or change of program, no tween) answers a pending question itself
        cut_answer = answer_pending if sc["before"] == sc["state"] != prev and prev is not None else None
        prev = sc["state"]
        if cut_answer:
            answer_pending = None
        if sc["before"] != sc["state"]:
            kind = "answer" if answer_pending else "transition"
            if sc["reveal"] > sc["start"]:
                out.append({"kind": "state", "scene": sc["id"], "start": sc["start"], "end": sc["reveal"],
                            "state": _view(lesson, sc["before"])})
            out.append({"kind": kind, "scene": sc["id"], "start": sc["reveal"], "end": sc["shown"],
                        "state": _view(lesson, sc["before"]),
                        **({"answer_for": answer_pending} if answer_pending else {})})
            answer_pending = None
            start = sc["shown"]
        q = sc.get("question")
        cue = {"kind": "question" if q else ("answer" if cut_answer else "state"), "scene": sc["id"], "start": start,
               "end": sc["end"], "state": _view(lesson, sc["state"]), **({"answer_for": cut_answer} if cut_answer else {})}
        if q:
            cue["question"] = {"prompt": q["prompt"], "scene": sc["id"]}
            answer_pending = sc["id"]
        out.append(cue)
    out.sort(key=lambda c: c["start"])
    merged = []
    for c in out:
        # a plain state cue that continues the previous cue's state (and adds no question) is the same cue
        if merged and c["kind"] == "state" and merged[-1]["kind"] in ("state", "question") \
                and merged[-1]["state"]["state_id"] == c["state"]["state_id"]:
            continue
        merged.append(c)
    for i, c in enumerate(merged):
        c["end"] = merged[i + 1]["start"] if i + 1 < len(merged) else timing["duration"]
        c["cue"] = f"m{i + 1}"
    return [c for c in merged if c["end"] - c["start"] > 0.001]


def write_metadata_vtt(path, cue_list):
    lines = ["WEBVTT", "", "NOTE ptk IVE state cues: payload = last state already shown (D18.2)", ""]
    for c in cue_list:
        payload = {k: v for k, v in c.items() if k not in ("start", "end")}
        lines += [c["cue"], f"{text.vtt_time(c['start'])} --> {text.vtt_time(c['end'])}",
                  json.dumps(payload, ensure_ascii=False, separators=(",", ":")), ""]
    path.write_text("\n".join(lines))


IVE_DIR = host.PKG / "ptk" / "templates" / "ive"
JS_UI = ("chapters", "code_label", "output_label", "vars_label", "question_label", "captions_on", "captions_off",
         "ive_from_film", "ive_yours", "ive_mode_label_explore", "ive_mode_label_film", "ive_mode_explore",
         "ive_mode_film", "x_on", "x_off", "x_captured", "x_computed", "x_tag_changed", "x_tag_nomatch", "enter_label",
         "x_tag_fall", "exit_label", "x_tag_end")
DECL_VAR = re.compile(r"^\s*int\s+(\w+)\s*=")


def clock(t):
    """m:ss, the same as the page's clock()."""
    return f"{int(t // 60)}:{int(t % 60):02d}"


def live_model(lesson):
    """The EXPLORE panel's live edit: the WP4 switch model (case tables checked against the program
    source and the facts' expect args), or None when the lesson is not a two-program switch lesson.
    The page computes each view with the C17 switch rule; tests/test_ive.py checks every view
    against explorer.expected_view (expect.py), which never shares code with the page."""
    try:
        m = explorer.switch_model(lesson)
    except errors.ModelReferenceError:
        return None
    progs = {}
    for pid, P in m["programs"].items():
        first, last = rail.body_range(lesson.program_source(pid).split("\n"))
        progs[pid] = {**{k: P[k] for k in ("id", "file", "sha", "n0", "n_line", "n_prefix", "n_suffix", "switch_line",
                                           "close_line", "cases", "tail")},
                      "lines": [row for row in P["lines"] if first <= row[0] <= last]}
    var = DECL_VAR.match(progs[m["base"]]["n_prefix"]).group(1)
    return {"base": m["base"], "alt": m["alt"], "n0": m["n0"], "domain": m["domain"], "toggle_label": m["toggle_label"],
            "var": var, "programs": progs}


def page_data(lesson, timing, cue_list, ive_dir, live):
    """window.__ptkIveData, written to ive-data.js: the exact text of the three .vtt files (the page
    turns them into blob: tracks, so they load from file://) plus UI strings and the live model.
    It is a separate file, so no cue payload or answer is in the document."""
    answers = [c for c in cue_list if c["kind"] == "answer"]
    return {"fps": timing["fps"], "ui": {k: text.ui(k) for k in JS_UI}, "captions_label": "English",
            "artifact_id": f"{lesson.id}:ive", "session_id": "local",
            "tracks": {k: (ive_dir / f"{k}.vtt").read_text() for k in ("captions", "chapters", "states")},
            "unlock_cue": answers[-1]["cue"] if answers else None, "live": live}


def _live_html(lesson, live, unlock):
    if not live:
        return ""
    lock = (f'<p class="locked" id="locked" hidden data-chrome="ive_locked">{esc(text.ui("ive_locked", time=clock(unlock)))}</p>'
            if unlock is not None else '<p class="locked" id="locked" hidden></p>')
    return (f'<div class="live" id="live" data-locked="false"><p class="lbl" data-chrome="ive_live_label">'
            f'{esc(text.ui("ive_live_label"))}</p>{lock}<div class="livectl">'
            f'<fieldset class="seg" id="live-n"><legend class="lbl" data-chrome="x_n_label">{esc(text.ui("x_n_label"))}</legend>'
            f'<div class="opts" id="live-opts"></div></fieldset>'
            f'<button type="button" class="pill" id="live-brk" aria-pressed="false"><span data-chrome="x_toggle">'
            f'{esc(text.ui("x_toggle", k=live["toggle_label"]))}</span><span class="onoff" id="live-brk-state" '
            f'data-chrome="x_off">{esc(text.ui("x_off"))}</span></button>'
            f'<button type="button" class="pill" id="live-reset" disabled data-chrome="ive_live_reset">'
            f'{esc(text.ui("ive_live_reset"))}</button></div></div>')


def page(lesson, timing, cue_list, posters, live=None):
    """The IVE page. Static text is chrome.json, the title, or narration in the no-JS block."""
    script = (IVE_DIR / "ive.js").read_text()
    answers = [c for c in cue_list if c["kind"] == "answer"]
    unlock = answers[-1]["start"] if answers else None
    used = " ".join([lesson.data["title"], text.ui("kicker", topic=lesson.data["topic"]), explorer.all_chrome_text(),
                     *[c["text"] for c in timing["cues"]], *[s["title"] for s in timing["scenes"]],
                     *[json.dumps(c, ensure_ascii=False) for c in cue_list],
                     *[ln for P in (live or {}).get("programs", {}).values() for _, ln in P["lines"]],
                     "0123456789:—·=; English"])
    css = explorer.page_css(used, "base.css") + (IVE_DIR / "ive.css").read_text()
    src = lesson.program(lesson.data["figure"]["program"]) if lesson.data.get("figure") else lesson.data["programs"][0]
    tx_full = "".join(f'<li data-narration="{esc(c["id"])}"><span class="time" data-label="time">'
                      f'{esc(clock(c["start"]))}</span><span>{esc(c["text"])}</span></li>' for c in timing["cues"])
    poster_html = "".join(f'<figure><img src="{esc(p["file"])}" alt="{esc(p["alt"])}" width="960" height="540">'
                          f'<figcaption data-label="scene-title">{esc(p["title"])}</figcaption></figure>' for p in posters)
    csp = (f"default-src 'none'; script-src 'self' {explorer.csp_hash(script)}; style-src {explorer.csp_hash(css)}; "
           f"img-src 'self' data:; media-src 'self' blob:; font-src data:; connect-src 'none'; base-uri 'none'; "
           f"form-action 'none'")
    ui = text.ui
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta http-equiv="Content-Security-Policy" content="{csp}">
<title>{esc(lesson.data['title'])}</title>
<style>{css}</style>
</head><body><div class="wrap">
<header class="mast"><p class="kicker" data-chrome="kicker">{esc(ui('kicker', topic=lesson.data['topic']))}</p>
<h1 data-label="title">{esc(lesson.data['title'])}</h1></header>
<main class="ive">
<div class="ivegrid">
<section class="film">
<video id="v" controls preload="metadata" playsinline poster="{esc(posters[0]['file'])}" aria-label="{esc(lesson.data['title'])}">
<source src="lesson.mp4" type="video/mp4">
</video>
<div class="modebar js-only"><p class="mode" id="mode" role="status" data-nodata="{esc(ui('ive_no_data'))}"><span class="tagm" id="mode-label" data-chrome="ive_mode_label_film">{esc(ui('ive_mode_label_film'))}</span><span id="mode-text" data-chrome="ive_mode_film">{esc(ui('ive_mode_film'))}</span></p>
<div class="acts"><button type="button" class="pill primary" id="explore" data-chrome="ive_explore">{esc(ui('ive_explore'))}</button>
<button type="button" class="pill primary" id="return" hidden data-chrome="ive_return">{esc(ui('ive_return'))}</button>
<button type="button" class="pill" id="caps" aria-pressed="true" data-chrome="captions_on">{esc(ui('captions_on'))}</button></div></div>
</section>
<section class="xpanel js-only" id="xp" data-origin="film" data-mode="film" aria-labelledby="xp-h">
<div class="xhead"><h2 class="lbl" id="xp-h" data-chrome="state_label">{esc(ui('state_label'))}</h2><p class="origin" id="origin" aria-live="polite"></p></div>
<div id="state"></div>
<div class="tools" id="tools" hidden>
<div class="steps"><p class="lbl" data-chrome="ive_steps_label">{esc(ui('ive_steps_label'))}</p>
<button type="button" class="pill" id="prev" data-chrome="prev_state">{esc(ui('prev_state'))}</button>
<button type="button" class="pill" id="next" data-chrome="next_state">{esc(ui('next_state'))}</button></div>
{_live_html(lesson, live, unlock)}
</div>
</section>
<section class="chap js-only"><h2 class="lbl" data-chrome="chapters">{esc(ui('chapters'))}</h2><ol id="chapters" class="chapters"></ol></section>
<section class="txw js-only"><h2 class="lbl" data-chrome="transcript">{esc(ui('transcript'))}</h2><ol id="tx" class="tx"></ol></section>
</div>
<noscript><section class="nojs"><p data-chrome="noscript">{esc(ui('noscript'))}</p>
<h2 class="lbl" id="answers" data-chrome="ive_answers">{esc(ui('ive_answers'))}</h2>
<div class="posters">{poster_html}</div>
<ol class="tx">{tx_full}</ol></section></noscript>
</main>
<footer class="foot"><p data-chrome="provenance">{esc(text.provenance(lesson))}</p>
<p data-role="source" data-chrome="source_link">{esc(ui('source_link', path=f"lessons/{lesson.id}/{src['path']}"))}</p></footer>
</div>
<script src="ive-data.js"></script>
<script>{script}</script>
</body></html>
"""


def project(lesson, out, video_dir, timing):
    out.mkdir(parents=True, exist_ok=True)
    mp4 = out / "lesson.mp4"
    if mp4.exists():
        mp4.unlink()
    os.link(video_dir / "lesson.mp4", mp4)
    for f in ("captions.vtt", "chapters.vtt"):
        shutil.copyfile(video_dir / f, out / f)
    cue_list = cues(lesson, timing)
    write_metadata_vtt(out / "states.vtt", cue_list)
    pdir = out / "posters"
    pdir.mkdir(exist_ok=True)
    ffmpeg = host.which("ffmpeg")
    posters = []
    for sc in timing["scenes"]:
        t = min(max(sc["shown"], sc["start"] + 1.0) + 0.3, sc["end"] - 0.1)
        f = pdir / f"{sc['id']}.jpg"
        host.run([ffmpeg, "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", mp4, "-frames:v", "1", "-vf", "scale=960:-2",
                  "-q:v", "3", f], check=True, timeout=120)
        posters.append({"file": f"posters/{f.name}", "title": sc["title"],
                        "alt": f"{sc['title']} ({text.vtt_time(t)[3:8]})"})
    live = live_model(lesson)
    data = page_data(lesson, timing, cue_list, out, live)
    (out / "ive-data.js").write_text("window.__ptkIveData = " + json.dumps(data, ensure_ascii=False) + ";\n")
    (out / "index.html").write_text(page(lesson, timing, cue_list, posters, live))
    (out / "cues.json").write_text(json.dumps(cue_list, indent=1, ensure_ascii=False))
    return {"page": out / "index.html", "cues": cue_list, "posters": posters}
