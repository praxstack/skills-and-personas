r"""IVE prediction gate: explanation first by default (AC-6.8), the prediction stop in practice mode (review X1).

By default (the page opens with the "Practice mode" toggle off) the film plays through each question:
it never stops for a prediction, and the MP4 itself has no think gap (the answer scene follows the
question at the normal scene pace). With the toggle on, the player pauses itself:

    question scene narration ──"…answers this question."──┤ q_end
                                               ├─ ≤ 0.6 s ─┤ pause_at: the film stops here, options on screen
                                                            │   play() does nothing until a pick
                                                            │   no answer anywhere: sealed chapter titles show
                                                            │   a placeholder
                                                pick ──────▶ resume_at (answer scene start)
                                                            ├─ ≤ 0.6 s ─┤ the next narration line starts

Two halves, both reading the built artifacts only (never the projector's internals):

static   ive-data.js `questions` against the storyboard and captions.vtt: every question with options is
         gated, its options are the storyboard's, the question narration never asks the learner to predict,
         pick, choose or commit (that is the default film; the invitation is the practice-mode hint on the
         page) and is spoken at a calm pace, the film is silent for at most MAX_SILENCE before the pause
         and after the jump, and the next line follows the question within MAX_ANSWER_GAP (no think gap:
         v2.1 baked 3.8 s of silence under a bar into the MP4).
browser  the page from file://, driven in Chromium, in two jobs per width:
         ive-explain  practice off (as opened): the toggle is visible and off; play through the question
                      and check the film never stops or pauses, plays no silent gap and reaches the answer.
         ive-predict  turn the toggle on, play into the question, wait for the stop, hold (wait, then try
                      play()), check the options, the sealed chapter titles and the absence of the answer,
                      take a screenshot, pick a wrong option, check the verdict and that the film resumes
                      at the answer scene and the titles open.

`python -m ptk.verify.ive_predict <lesson dir>` runs both and prints the gate (exit 1 when it fails).
"""
import json
import re
import sys
from pathlib import Path

from .. import model, text
from . import media

GATE_ID = "ive.predict-gated"
MAX_SILENCE = 0.6       # seconds of dead air allowed on each side of the pause
MAX_WPM = 205           # the question line at a calm pace: the review measured 220; Kokoro reads about 195 at speed 0.9
PAUSE_TOL = 0.12        # where the film stops, against pause_at
MAX_ANSWER_GAP = 1.0    # question's last word to the next line: the normal 0.8 s scene gap plus a margin
BARRIER = re.compile(r"\b(predict\w*|pick|choose|commit|guess)\b", re.I)


def page_data(ive_dir):
    """window.__ptkIveData from ive-data.js (the file the page loads)."""
    src = (Path(ive_dir) / "ive-data.js").read_text()
    m = re.fullmatch(r"\s*window\.__ptkIveData\s*=\s*(\{.*\})\s*;\s*", src, re.S)
    if not m:
        raise ValueError("ive-data.js does not assign window.__ptkIveData")
    return json.loads(m.group(1))


def _words(s):
    return len(re.findall(r"[A-Za-z0-9%']+", s))


def static_check(lesson, data, captions):
    """Problems with the gating plan, from the artifacts: [str], plus the measured rows."""
    probs, rows = [], []
    plan = {q["scene"]: q for q in data.get("questions") or []}
    sb = lesson.data["storyboard"]
    for sc in sb:
        q = sc.get("question")
        if not q or not q.get("options"):
            continue
        p = plan.get(sc["id"])
        if not p:
            probs.append(f"{sc['id']}: the question is not gated (no pause plan in ive-data.js)")
            continue
        want = [o["text"] for o in q["options"]]
        got = [o.get("text") for o in p.get("options", [])]
        if got != want:
            probs.append(f"{sc['id']}: options {got} differ from the storyboard's {want}")
        if [o.get("correct") for o in p.get("options", [])] != [bool(o["correct"]) for o in q["options"]]:
            probs.append(f"{sc['id']}: the correct option differs from the storyboard")
        mine = [c for c in captions if c["id"].startswith(sc["id"] + ".")]
        if not mine:
            probs.append(f"{sc['id']}: no caption for the question scene")
            continue
        last = max(mine, key=lambda c: c["end"])
        asks = [c["text"] for c in mine if BARRIER.search(c["text"])]
        if asks:
            probs.append(f"{sc['id']}: the question narration asks for a prediction in the default film: {asks[0]!r}")
        wpm = [round(_words(c["text"]) / max(c["end"] - c["start"], 0.01) * 60) for c in mine]
        if max(wpm) > MAX_WPM:
            probs.append(f"{sc['id']}: question narration at {max(wpm)} wpm (max {MAX_WPM})")
        before = round(p["pause_at"] - last["end"], 3)
        nxt = min((c for c in captions if c["start"] >= p["resume_at"] - 0.001), key=lambda c: c["start"], default=None)
        after = round(nxt["start"] - p["resume_at"], 3) if nxt else 0.0
        if not 0 <= before <= MAX_SILENCE:
            probs.append(f"{sc['id']}: {before} s between the last spoken word and the pause (allowed 0..{MAX_SILENCE})")
        if not 0 <= after <= MAX_SILENCE:
            probs.append(f"{sc['id']}: {after} s of silence after the jump to the answer (max {MAX_SILENCE})")
        follow = round(nxt["start"] - last["end"], 3) if nxt else 0.0
        if follow > MAX_ANSWER_GAP:
            probs.append(f"{sc['id']}: a {follow} s think gap after the question in the MP4 (max {MAX_ANSWER_GAP})")
        if not p["pause_at"] < p["resume_at"] <= p["answer_at"]:
            probs.append(f"{sc['id']}: pause {p['pause_at']}, resume {p['resume_at']}, answer {p['answer_at']} out of order")
        rows.append({"scene": sc["id"], "pause_at": p["pause_at"], "resume_at": p["resume_at"],
                     "answer_at": p["answer_at"], "silence_before_pause": before, "silence_after_jump": after,
                     "answer_follows_after": follow, "question_wpm": wpm, "question_line": last["text"],
                     "sealed_chapters": p.get("sealed", [])})
    return probs, rows


# ---------------------------------------------------------------- browser

def _js(expr):
    return {"eval": f"(async () => {{ const D = window.__iveDrive; const I = window.__ptkIve; {expr} }})()"}


VISIBLE = """
const vis = (e) => { const r = e.getBoundingClientRect(), s = getComputedStyle(e);
  return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
const opts = [...document.querySelectorAll('#state .opt')].filter(vis).map((b) => b.textContent);
const chapters = [...document.querySelectorAll('#chapters .ttl')].map((e) => e.textContent);
const root = document.body.cloneNode(true);
root.querySelectorAll('noscript, script, video, track, .opts.ask, [data-code]').forEach((e) => e.remove());
const page = root.textContent.replace(/\\s+/g, ' ');
const panel = [...new Set([...document.querySelectorAll('#state .mechbox [data-m], #state .mechbox [data-fact], #state .mechbox [data-implies]')]
  .filter(vis).flatMap((e) => [e.dataset.m, e.dataset.fact, ...(e.dataset.implies || '').split(' ')]).filter(Boolean))];
"""


def _explain_job(url, q, w, ready, drive, start):
    """Practice off, as the page opens: the film plays through the question without stopping."""
    steps = [ready, drive,
             {**_js("const v = D.v(), b = document.getElementById('practice'); "
                    "const vis = !!b && !b.hidden && b.offsetParent !== null && b.getBoundingClientRect().width > 0; "
                    "const toggle = {visible: vis, pressed: b && b.getAttribute('aria-pressed'), practice: I.practice ? I.practice() : null}; "
                    f"await D.seek({start:.3f}); const r = v.play(); if (r && r.catch) r.catch(() => {{}}); "
                    "const modes = new Set(), ts = []; let paused = false; "
                    f"for (let i = 0; i < 200 && v.currentTime < {q['answer_at'] + 0.3:.3f}; i++) {{ await D.sleep(50); "
                    "modes.add(I.mode()); ts.push(Math.round(v.currentTime * 1000) / 1000); if (v.paused && !v.ended) paused = true; } "
                    f"const in_gap = ts.filter((t) => t > {q['pause_at'] + 0.3:.3f} && t < {q['resume_at'] - 0.1:.3f}); v.pause(); "
                    "return {toggle, modes: [...modes], paused, t_end: ts[ts.length - 1], in_gap};"), "as": "default"}]
    return {"id": f"ive-explain:{q['scene']}:{w}", "type": "script", "url": url, "width": w,
            "height": 900 if w > 400 else 844, "steps": steps}


def browser_jobs(url, q, titles, shots):
    """Two jobs per width: the default film plays through; with the practice toggle on, play into the
    question, hold, pick a wrong option (or the only one), resume."""
    wrong = next((k for k, o in enumerate(q["options"]) if not o["correct"]), 0)
    start = max(0.0, q["pause_at"] - 3.0)
    ready = {"waitFor": "window.__ptkReady && window.__ptkReady()", "timeout": 30000}
    drive = {"eval": (Path(__file__).resolve().parents[1] / "templates" / "ive" / "drive.js").read_text(), "as": "drive"}
    jobs = []
    for w in (1440, 390):
        jobs.append(_explain_job(url, q, w, ready, drive, start))
        steps = [ready, drive,
                 {**_js("document.getElementById('practice').click(); const b = document.getElementById('practice'); await D.sleep(30); "
                        "return {pressed: b && b.getAttribute('aria-pressed'), practice: I.practice ? I.practice() : null};"),
                  "as": "practice_on"},
                 {**_js(f"await D.seek({start:.3f}); const p = I.questions().find((x) => x.scene === {json.dumps(q['scene'])}); "
                        "const v = D.v(); const r = v.play(); if (r && r.catch) r.catch(() => {}); "
                        "for (let i = 0; i < 300 && I.mode() !== 'ask'; i++) await D.sleep(50); "
                        "await D.sleep(150);" + VISIBLE +
                        "return {mode: I.mode(), asking: I.asking(), t: v.currentTime, paused: v.paused, options: opts, "
                        "chapters, page, panel, plan: p};"), "as": "stopped"},
                 {"shot": str(shots / f"ive-ask-{q['scene']}-{w}.png"), "full": False},
                 {**_js("await D.sleep(2500); const v = D.v(); return {mode: I.mode(), t: v.currentTime, paused: v.paused};"),
                  "as": "held"},
                 {**_js("const v = D.v(); const r = v.play(); if (r && r.catch) r.catch(() => {}); await D.sleep(600); "
                        "return {mode: I.mode(), t: v.currentTime, paused: v.paused};"), "as": "play_refused"},
                 {**_js(f"const b = document.querySelectorAll('#state .opt')[{wrong}]; const v = D.v(); "
                        "const p = D.once(v, 'playing', 4000); b.click(); await p; await D.sleep(120); "
                        "const t0 = v.currentTime; await D.sleep(1500);" + VISIBLE +
                        "const vd = document.querySelector('#state .verdict'); "
                        "return {mode: I.mode(), t_after_pick: t0, t_later: v.currentTime, paused: v.paused, "
                        "verdict: vd && vd.getAttribute('data-verdict'), verdict_text: vd && vd.textContent, chapters, "
                        "picked: I.picked()};"), "as": "picked"},
                 {"shot": str(shots / f"ive-after-pick-{q['scene']}-{w}.png"), "full": False}]
        jobs.append({"id": f"ive-predict:{q['scene']}:{w}", "type": "script", "url": url, "width": w,
                     "height": 900 if w > 400 else 844, "steps": steps})
    return jobs


def browser_check(lesson, data, plan_rows, ive_dir, run=None, shots=None):
    """Drive the built page. `run(jobs, work)` returns shoot results (default: verify.visual.shoot)."""
    if run is None:
        from .visual import shoot

        def run(jobs, work):
            return shoot(jobs, work, lesson.sha256())
    ive_dir = Path(ive_dir)
    shots = Path(shots) if shots else ive_dir.parent / "shots"
    url = (ive_dir / "index.html").resolve().as_uri()
    sb = {s["id"]: s for s in lesson.data["storyboard"]}
    titles = [s["title"] for s in lesson.data["storyboard"]]
    placeholder = text.ui("ive_chapter_sealed")
    jobs, probs = [], []
    for q in data.get("questions") or []:
        jobs += browser_jobs(url, q, titles, shots)
    if not jobs:
        return ["no gated question to drive"], {}
    res = run(jobs, ive_dir.parent / "work" / "ive-predict")
    out = {}
    for r in res["results"]:
        kind, scene, w = r["id"].split(":")
        q = next(x for x in data["questions"] if x["scene"] == scene)
        V = r.get("values") or {}
        s, h, pr, pk = (V.get(k) or {} for k in ("stopped", "held", "play_refused", "picked"))
        tag = f"{scene}@{w}" + (" (practice off)" if kind == "ive-explain" else "")
        if not r.get("ok"):
            probs.append(f"{tag}: the driver failed: {r.get('error', '')[:300]}")
            continue
        if kind == "ive-explain":
            dp = default_problems(V.get("default") or {}, q)
            probs += [f"{tag}: {p}" for p in dp]
            out[tag] = V.get("default") or {}
            continue
        on = V.get("practice_on") or {}
        if on.get("pressed") != "true" or on.get("practice") is not True:
            probs.append(f"{tag}: the practice toggle did not turn practice mode on: {on}")
        if s.get("mode") != "ask" or not s.get("paused"):
            probs.append(f"{tag}: the film did not stop for the prediction (mode {s.get('mode')}, paused {s.get('paused')})")
        if s.get("t") is None or abs(s["t"] - q["pause_at"]) > PAUSE_TOL:
            probs.append(f"{tag}: stopped at {s.get('t')}, the pause point is {q['pause_at']}")
        if s.get("t") is not None and s["t"] >= q["answer_at"]:
            probs.append(f"{tag}: the film reached the answer cue before a pick")
        want = [o["text"] for o in sb[scene]["question"]["options"]]
        if s.get("options") != want:
            probs.append(f"{tag}: options on screen {s.get('options')}, expected {want}")
        for k in q.get("sealed", []):
            ch = (s.get("chapters") or [None] * (k + 1))[k]
            if ch != placeholder:
                probs.append(f"{tag}: chapter {k + 1} shows {ch!r} while the question is open")
            if titles[k] in (s.get("page") or ""):
                probs.append(f"{tag}: the sealed title {titles[k]!r} is in the page while the question is open")
        from ..project import seal
        qi = next(i for i, x in enumerate(lesson.data["storyboard"]) if x["id"] == scene)
        leak = sorted(seal.answer_facts(lesson.data, qi) & set(s.get("panel") or []))
        if leak:
            probs.append(f"{tag}: the panel shows the answer {leak} while the question is open")
        if h.get("mode") != "ask" or not h.get("paused") or abs((h.get("t") or 0) - (s.get("t") or 0)) > 0.02:
            probs.append(f"{tag}: the film did not hold for 2.5 s: {h}")
        if pr.get("mode") != "ask" or not pr.get("paused") or abs((pr.get("t") or 0) - (s.get("t") or 0)) > 0.05:
            probs.append(f"{tag}: play() went past the question without a pick: {pr}")
        if pk.get("paused") or pk.get("mode") != "film":
            probs.append(f"{tag}: the film did not resume after the pick: {pk}")
        if pk.get("t_after_pick") is None or not q["resume_at"] - 0.05 <= pk["t_after_pick"] <= q["resume_at"] + 0.6:
            probs.append(f"{tag}: resumed at {pk.get('t_after_pick')}, the answer scene starts at {q['resume_at']}")
        if not pk.get("verdict"):
            probs.append(f"{tag}: no verdict after the pick")
        if placeholder in (pk.get("chapters") or []):
            probs.append(f"{tag}: chapter titles stay sealed after the pick")
        out[tag] = {"stopped": {k: v for k, v in s.items() if k != "page"}, "held": h, "play_refused": pr,
                    "picked": pk, "shots": [f"shots/ive-ask-{scene}-{w}.png", f"shots/ive-after-pick-{scene}-{w}.png"]}
    if res.get("outbound"):
        probs.append(f"outbound requests: {res['outbound'][:3]}")
    return probs, out


def default_problems(d, q):
    """AC-6.8, practice off: the toggle is visible and off, and the film plays through the question."""
    t = d.get("toggle") or {}
    v = [] if t.get("visible") and t.get("pressed") == "false" and t.get("practice") is False else \
        [f"the practice toggle is not visible and off when the page opens: {t}"]
    v += [] if "ask" not in (d.get("modes") or []) and not d.get("paused") else \
        [f"the film stopped for a prediction with practice mode off (modes {d.get('modes')}, paused {d.get('paused')})"]
    v += [] if (d.get("t_end") or 0) >= q["answer_at"] else [f"the film did not play on to the answer ({d.get('t_end')})"]
    return v + ([f"the film played a silent think gap: {d['in_gap'][:3]}"] if d.get("in_gap") else [])


def gate(lesson, ive_dir, browser=True, run=None, shots=None):
    ive_dir = Path(ive_dir)
    if not (ive_dir / "ive-data.js").exists():
        return {"id": GATE_ID, "medium": "ive", "status": "not-run", "measured": {}, "reason": "no built IVE"}
    data = page_data(ive_dir)
    caps = media.parse_vtt(ive_dir / "captions.vtt")
    probs, rows = static_check(lesson, data, caps)
    if not rows and not probs:
        return {"id": GATE_ID, "medium": "ive", "status": "not-run", "measured": {},
                "reason": "the storyboard has no question with options"}
    drove = {}
    if browser and not probs:
        bp, drove = browser_check(lesson, data, rows, ive_dir, run, shots=shots)
        probs += bp
    return {"id": GATE_ID, "medium": "ive", "status": "failed" if probs else ("passed" if browser else "not-run"),
            "measured": {"questions": rows, "driven": drove, "problems": probs[:30],
                         "rule": "practice mode off (the default, AC-6.8): the toggle is visible and off and the film plays "
                                 "through the question without stopping, its question narration asks for no prediction, and the next "
                                 f"line follows within {MAX_ANSWER_GAP} s (no think gap in the MP4); practice mode on: the film stops "
                                 f"within {PAUSE_TOL} s of the pause point, at most {MAX_SILENCE} s after "
                                 "the last spoken word, shows the storyboard's options, holds through a wait and a play(), "
                                 "keeps answer-stating chapter titles sealed, and resumes at the answer scene after a pick"},
            "reason": "; ".join(probs[:3])[:500] if probs else ("" if browser else "browser half not run")}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m ptk.verify.ive_predict <lesson dir> [--static]", file=sys.stderr)
        return 2
    lesson = model.load(argv[0])
    g = gate(lesson, lesson.dir / "build" / "ive", browser="--static" not in argv)
    out = lesson.dir / "build" / "work" / "ive-predict.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(g, indent=1))
    print(json.dumps({"id": g["id"], "status": g["status"], "reason": g["reason"],
                      "questions": g["measured"].get("questions")}, indent=1))
    return 0 if g["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
