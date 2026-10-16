#!/usr/bin/env python3
"""vstate.py: the state machine every video skill in this repo runs on.

A video is built in eight phases, always in this order:

    brief -> script -> voice -> visuals -> render -> mix -> qa -> deliver

The state lives in <project>/.video-state.json, so a run that is interrupted (a crash,
a closed laptop, a 2-hour job cap) resumes exactly where it stopped: run `status` and do
the next step it prints. `advance` refuses to move on until the current phase passes its
gate, so nothing reaches "deliver" without passing every check before it.

Commands (run from anywhere; --project defaults to the current directory):
  init     --tool <name> --slug <slug> [--format dsa-5part|general] [--width 1920 --height 1080 --fps 30]
  status   show the phase, what passed, and the exact next step
  check    [phase]           run a phase's gate without advancing
  advance                    run the current gate; if it passes, move to the next phase
  reopen   <phase> --reason "..."   go back (later phases become stale and must pass again)
  attest   <phase> "<what you looked at and what you found>" [--file path]
  note     "<decision or fact worth keeping>"
  limit    "<what is not possible here>" --tried "<attempt 1 and result>" --tried "<attempt 2 and result>"
  set      key=value [key=value ...]   (config: silent, final, deliver, source, stills, min_minutes, max_minutes)
  notes-md                   print a NOTES.md skeleton filled from the state (engine, limits, versions)
  report                     print the delivery summary for the final message

Exit codes: 0 ok, 1 gate failed, 2 usage error.
"""
import argparse
import datetime as _dt
import hashlib
import html
import json
import math
import os
import re
import subprocess
import sys
import urllib.parse

PHASES = ["brief", "script", "voice", "visuals", "render", "mix", "qa", "deliver"]
STATE = ".video-state.json"
NATURAL_ENGINES = {"kokoro", "edge-tts", "piper", "elevenlabs", "openai-tts", "azure-tts", "google-tts", "recorded"}
ROBOTIC_ENGINES = {"espeak", "espeak-ng", "say", "sapi", "speechsynthesis", "pyttsx3", "festival", "flite"}
# characters a TTS engine reads badly or not at all; write them out in `say`
TTS_HOSTILE = "→←↑↓⇒≤≥≠∞^[]{}|`_≈×÷√∑∈∉∀∃λ·•…"

SCRIPTS = os.path.dirname(os.path.abspath(__file__))  # hints print runnable paths
_HINTS = {
    "brief": "Write brief.md (sections: Topic, Audience, Format, Persistent subject, Style, Facts, Output). "
             "For code topics, compile and run the solution and paste the real outputs under Facts.",
    "script": "Write script.json (see references/script-format.md). `cap` is what is shown, `say` is what is spoken. "
              "For DSA: five chapters, think pauses on every intuition question.",
    "voice": "python3 {S}/voice.py --project . --emit <timing file your source reads>   "
             "(Kokoro by default; never ship silent, never fall back to a robotic voice without a recorded limit)",
    "visuals": "Build the scenes in source/ from the template, render stills for every chapter, LOOK at them, fix, "
               "check text size and contrast with python3 {S}/legibility.py --project . (fix every red box), "
               "then: python3 {S}/vstate.py attest visuals \"<what you checked and fixed>\"",
    "render": "Render the full silent video to the `silent` path (segmented and resumable; see the skill's render step).",
    "mix": "python3 {S}/music.py --project .  then  python3 {S}/mix.py --project .",
    "qa": "python3 {S}/qa.py --project .  then open qa/contact-sheet.png and the qa/stills, and "
          "python3 {S}/vstate.py attest qa \"<what you saw>\"",
    "deliver": "python3 {S}/package.py --project .  (copies the MP4, captions, timeline, NOTES.md, source, "
               "voice-swap script into the deliver folder), then python3 {S}/vstate.py advance",
}
SKILL_DIR = os.path.dirname(SCRIPTS)
# a skill can override hints with tool-specific commands in <skill>/tool.json: {"hints": {"render": "..."}}
try:
    with open(os.path.join(SKILL_DIR, "tool.json"), encoding="utf-8") as _f:
        _HINTS.update(json.load(_f).get("hints", {}))
except (OSError, ValueError):
    pass
HINTS = {k: v.replace("{S}", SCRIPTS).replace("{SKILL}", SKILL_DIR) for k, v in _HINTS.items()}


# ----------------------------------------------------------------------------- helpers
def now():
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


def mtime(path):
    return os.path.getmtime(path) if os.path.exists(path) else 0


def iso_to_ts(s):
    try:
        return _dt.datetime.fromisoformat(s).timestamp()
    except Exception:
        return 0


def ffprobe(path):
    try:
        out = subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries",
             "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate",
             "-of", "json", path], stderr=subprocess.STDOUT)
        return json.loads(out)
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)}


def video_facts(path):
    p = ffprobe(path)
    if "error" in p:
        return None
    v = next((s for s in p.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in p.get("streams", []) if s.get("codec_type") == "audio"), None)
    fps = None
    if v and v.get("r_frame_rate") and "/" in v["r_frame_rate"]:
        n, d = v["r_frame_rate"].split("/")
        fps = round(float(n) / float(d), 3) if float(d) else None
    return {
        "duration": float(p.get("format", {}).get("duration", 0) or 0),
        "vcodec": v and v.get("codec_name"), "width": v and v.get("width"), "height": v and v.get("height"),
        "fps": fps, "pix_fmt": v and v.get("pix_fmt"),
        "acodec": a and a.get("codec_name"), "sample_rate": a and a.get("sample_rate"),
    }


QA_HARD_CHECKS = ("format", "duration", "loudness", "voice-sync", "black", "flicker", "moving-text")


class Gate:
    """Collects pass/fail/warn results for one phase."""

    def __init__(self, phase):
        self.phase, self.items = phase, []

    def ok(self, cond, msg, fix=""):
        self.items.append(("PASS" if cond else "FAIL", msg, "" if cond else fix))
        return cond

    def warn(self, cond, msg, fix=""):
        if not cond:
            self.items.append(("WARN", msg, fix))
        return cond

    @property
    def passed(self):
        return all(s != "FAIL" for s, _, _ in self.items)

    def show(self):
        for s, m, f in self.items:
            mark = {"PASS": "  ok ", "FAIL": "  XX ", "WARN": "  !! "}[s]
            print(f"{mark}{m}" + (f"\n        fix: {f}" if f else ""))


# ----------------------------------------------------------------------------- state io
class Project:
    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.path = os.path.join(self.root, STATE)
        self.s = None

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def load(self):
        if not os.path.exists(self.path):
            sys.exit(f"no {STATE} in {self.root}. Start with: vstate.py init --tool <tool> --slug <slug>")
        with open(self.path) as f:
            self.s = json.load(f)
        return self.s

    def save(self):
        tmp = self.path + ".tmp"
        with open(tmp, "w") as f:
            json.dump(self.s, f, indent=1, ensure_ascii=False)
        os.replace(tmp, self.path)

    def cfg(self, key):
        c = self.s["config"]
        defaults = {
            "silent": "build/silent.mp4", "final": f"out/{self.s['slug']}.mp4", "deliver": "deliver",
            "source": "source", "stills": "stills",
        }
        return c.get(key, defaults.get(key))

    def log(self, kind, text, **extra):
        self.s.setdefault("log", []).append(dict(at=now(), kind=kind, text=text, **extra))


# ----------------------------------------------------------------------------- gates
def md_sections(text):
    """(heading, body) for each '#', '##' or '###' heading. A heading needs a space after its #s, and lines inside
    a ``` or ~~~ fence are body text, so `#include <vector>` or a `# comment` in a code block is not a heading.
    As in CommonMark, a fence is indented at most 3 spaces, and only a bare run of the opening character at least as
    long as the opening fence closes it."""
    out, fence, head, body = [], None, None, []
    for line in text.splitlines():
        m = re.match(r" {0,3}(`{3,}|~{3,})(.*)$", line)  # indented 4 or more, it is content, not a fence
        if m:
            run, rest = m.group(1), m.group(2)
            if fence is None:
                fence = run
            elif run[0] == fence[0] and len(run) >= len(fence) and not rest.strip():
                fence = None
        h = None if (fence or m) else re.match(r"#{1,3}[ \t]+(.+)$", line)
        if h:
            if head is not None:
                out.append((head, "\n".join(body)))
            head, body = h.group(1), []
        elif head is not None:
            body.append(line)
    if head is not None:
        out.append((head, "\n".join(body)))
    return out


def gate_brief(pr):
    g = Gate("brief")
    path = pr.p("brief.md")
    if not g.ok(os.path.exists(path), "brief.md exists", "write brief.md in the project folder"):
        return g
    text = open(path, encoding="utf-8").read()
    secs = md_sections(text)
    heads = {h.strip().lower(): i for i, (h, _) in enumerate(secs)}
    sections = [body for _, body in secs]
    need = ["topic", "audience", "format", "persistent subject", "style", "facts", "output"]
    for n in need:
        hit = next((h for h in heads if h.startswith(n)), None)
        if g.ok(hit is not None, f"brief has a '{n.title()}' section", f"add a '## {n.title()}' heading"):
            body = sections[heads[hit]].strip() if heads[hit] < len(sections) else ""
            g.ok(len(body) >= 12, f"'{n.title()}' section is filled in", "write real content under it")
    tid = pr.cfg("theme") or "original"
    if tid != "original":
        try:
            theme_expect(pr)
            known = True
        except SystemExit:
            known = False
        g.ok(known, f"theme '{tid}' is in the registry",
             f"python3 {SCRIPTS}/theme.py list  then  python3 {SCRIPTS}/vstate.py set theme=<id>  (or theme=original)")
    if pr.s.get("format") == "dsa-5part":
        facts = ""
        hit = next((h for h in heads if h.startswith("facts")), None)
        if hit is not None and heads[hit] < len(sections):
            facts = sections[heads[hit]]
        g.ok(re.search(r"verif|compiled|ran |output", facts, re.I) is not None,
             "Facts section records verified outputs (code compiled and run)",
             "compile and run the solution on every example; paste the real outputs under Facts")
    return g


def load_script(pr):
    path = pr.p("script.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def estimate_seconds(sc):
    """Rough film length of a script before it is voiced (seconds)."""
    lines = sc.get("lines") or []
    chapters = (sc.get("meta") or {}).get("chapters", [])
    words = sum(len(str(ln.get("say", "")).split()) for ln in lines)
    # Kokoro speaks about 2.9 to 3.3 words/s at speed 1.0; each line adds lead + pad (0.6 s), each chapter 0.8 s.
    # Checked against three films (62 s, 210 s, 237 s) within about 6%, and the 71 s demo voiced with pauses at
    # 72.9 s (3% over; 65.6 s, 7% under, without the two terms below). qa.py checks the real length.
    # voice.py also leaves sentence_pause between the sentences of a line and holds a chapter's first line for
    # chapter_lead (instead of the usual 0.25 s lead) while the chapter card plays.
    meta = sc.get("meta") or {}
    speed = float(meta.get("speed", 1.0) or 1.0)
    sys.path.insert(0, SCRIPTS)
    import voice as _voice  # noqa: E402  (voice.py ships next to this file; stdlib-only at import)
    pause = float(meta.get("sentence_pause", 0.3))
    breaks = sum(max(0, len(_voice.sentences(str(ln.get("say", "")))) - 1) for ln in lines)
    base_lead = float(meta.get("lead", 0.25))
    held = sum(1 for prev, ln in zip(lines, lines[1:])
               if ln.get("chapter", 0) != prev.get("chapter", 0) and "lead" not in ln)
    est = (words / (3.0 * speed) + 0.6 * len(lines) + sum(float(ln.get("think", 0) or 0) for ln in lines)
           + 0.8 * max(0, len(chapters) - 1) + 0.4
           + pause * breaks + max(0.0, float(meta.get("chapter_lead", 1.0)) - base_lead) * held)
    return est


def gate_script(pr):
    g = Gate("script")
    path = pr.p("script.json")
    if not g.ok(os.path.exists(path), "script.json exists", "write script.json (references/script-format.md)"):
        return g
    try:
        sc = load_script(pr)
    except Exception as e:  # noqa: BLE001
        g.ok(False, f"script.json parses ({e})", "fix the JSON")
        return g
    # valid JSON of another shape (a list, a string, "meta": null) would stop the gate with a traceback below
    if not g.ok(isinstance(sc, dict), "script.json is an object with meta and lines" + ("" if isinstance(sc, dict) else f" (not {type(sc).__name__})"),
                '{"meta": {"title": ..., "chapters": [...]}, "lines": [...]} (references/script-format.md)'):
        return g
    meta, lines = sc.get("meta", {}), sc.get("lines", [])
    if not g.ok(isinstance(meta, dict) and isinstance(lines, list), "meta is an object and lines a list"
                + ("" if isinstance(meta, dict) and isinstance(lines, list) else f" (meta: {type(meta).__name__}, lines: {type(lines).__name__})"),
                '"meta": {...}, "lines": [{...}, ...]'):
        return g
    g.ok(bool(meta.get("title")), "meta.title is set")
    chapters = meta.get("chapters", [])
    g.ok(isinstance(chapters, list) and len(chapters) >= 1, "meta.chapters lists chapter names (index = chapter number)")
    # a name is shown on the chapter card and names its review stills: a number, a list or an object breaks those later
    odd = [c for c in chapters if not isinstance(c, str) or not c.strip()] if isinstance(chapters, list) else []
    g.ok(not odd, "every chapter name is text" + (f" (not: {', '.join(repr(c) for c in odd[:4])})" if odd else ""),
         'name each chapter with a short text, e.g. "The trap"')
    g.ok(len(lines) >= 3, f"script has lines ({len(lines)})")
    ids, bad_ids, missing, hostile = set(), [], [], []
    for ln in lines:
        if not isinstance(ln, dict):
            bad_ids.append(str(ln)[:20])
            continue
        i = ln.get("id", "")
        # the same rule voice.py applies (ID_RE), so a script that passes here also voices
        if not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,31}", i) or i.lower() in ids:
            bad_ids.append(str(i) or "<empty>")
        i = str(i)
        ids.add(i.lower())  # it names a clip file, and macOS and Windows disks ignore case
        for k in ("chapter", "cap", "say"):
            if k not in ln or ln[k] in ("", None):
                missing.append(f"{i}.{k}")
        # the caption is drawn and the line is spoken: a list, an object or blank text would reach the voice and
        # the page as is
        for k in ("cap", "say"):
            if ln.get(k) not in ("", None) and (not isinstance(ln[k], str) or not ln[k].strip()):
                missing.append(f"{i}.{k} must be text, not {ln[k]!r}")
        if not ln.get("say_ok"):
            chars = sorted({c for c in str(ln.get("say", "")) if c in TTS_HOSTILE})
            if chars:
                hostile.append(f"{i}: {''.join(chars)}")
        ch = ln.get("chapter")
        if ch not in ("", None) and (not isinstance(ch, int) or isinstance(ch, bool)):
            missing.append(f"{i}.chapter must be a whole number, not {ch!r}")
        elif isinstance(ch, int) and chapters and not (0 <= ch < len(chapters)):
            missing.append(f"{i}.chapter out of range")
    g.ok(not bad_ids, "line ids are unique and simple" + (f" (bad: {bad_ids[:5]})" if bad_ids else ""))
    g.ok(not missing, "every line has chapter, cap and say" + (f" (missing: {missing[:6]})" if missing else ""))
    g.ok(not hostile, "`say` text has no symbols the voice would garble" + (f" ({hostile[:6]})" if hostile else ""),
         "spell symbols out in `say` (→ 'to', ≤ 'at most', ∞ 'infinity', [0,1,100] 'zero, one, one hundred')")
    # effect cues are placed by music.py, after the render: a misspelt kind or a text offset would stop it there
    def secs(v):  # what music.py's float() takes, and a finite time
        try:
            return not isinstance(v, bool) and math.isfinite(float(v))
        except (TypeError, ValueError):
            return False
    cues = []
    for ln in lines:
        sfx = ln.get("sfx") if isinstance(ln, dict) else None
        if sfx is None:
            continue
        for cue in sfx if isinstance(sfx, list) else [sfx]:
            if not isinstance(sfx, list) or not isinstance(cue, dict):
                cues.append(f"{ln.get('id')}.sfx {cue!r} (give a list of cues)")
            elif cue.get("kind") not in SFX_KINDS:
                cues.append(f"{ln.get('id')}.sfx kind {cue.get('kind')!r}")
            elif "at" in cue and not secs(cue["at"]):
                cues.append(f"{ln.get('id')}.sfx at {cue['at']!r}")
    g.ok(not cues, "sound-effect cues are ones music.py makes" + (f" (not: {', '.join(cues[:4])})" if cues else ""),
         f'"sfx": [{{"kind": "pop", "at": 0.5}}], kind one of {", ".join(SFX_KINDS)}, at in seconds after the line starts')
    mood = meta.get("music")
    known = mood in (None, "") or mood in MUSIC_MOODS
    g.ok(known, "meta.music is a mood music.py makes" + ("" if known else f" (not {mood!r})"),
         f"set meta.music to one of {', '.join(MUSIC_MOODS)}")
    # a chapter is one run of lines: one that comes back after another (0, 1, 0) plays its card twice and gives two
    # chapters the same name, so their review stills would overwrite each other
    runs = []
    for ln in lines:
        ch = ln.get("chapter") if isinstance(ln, dict) else None
        if isinstance(ch, int) and not isinstance(ch, bool) and (not runs or runs[-1] != ch):
            runs.append(ch)
    back = sorted({c for i, c in enumerate(runs) if c in runs[:i]})
    g.ok(not back, "each chapter is one run of lines" + (f" (chapter {', '.join(map(str, back))} comes back after another)" if back else ""),
         "keep a chapter's lines together, or give the later part its own chapter name in meta.chapters")
    # the length estimate and the DSA think check below read these as numbers: a text there would stop the gate with a
    # traceback instead of saying what to fix (the same rule voice.py applies: seconds, a number of 0 or more)
    lines = [ln for ln in lines if isinstance(ln, dict)]

    def num(v):
        try:
            return not isinstance(v, bool) and 0 <= float(v) < float("inf")
        except (TypeError, ValueError):
            return False
    sp = meta.get("speed")
    odd = [] if sp in (None, "") or num(sp) and float(sp) > 0 else [f"meta.speed {sp!r}"]
    odd += [f"meta.{k} {meta[k]!r}" for k in ("sentence_pause", "lead", "chapter_lead") if k in meta and not num(meta[k])]
    odd += [f"{ln.get('id')}.think {ln['think']!r}" for ln in lines if ln.get("think") not in (None, "") and not num(ln["think"])]
    if not g.ok(not odd, "speed, pauses and leads are numbers" + (f" (not: {', '.join(odd[:4])})" if odd else ""),
                'write them as numbers: "speed": 0.95 (above 0); think, lead, chapter_lead, sentence_pause in seconds (0 or more)'):
        return g
    est = estimate_seconds({**sc, "lines": lines})
    lo, hi = float(pr.s["config"].get("min_minutes", 1.0)), float(pr.s["config"].get("max_minutes", 9.0))
    g.warn(lo * 60 <= est <= hi * 60, f"estimated length {est / 60:.1f} min (about ±10%) is outside {lo}-{hi} min",
           "trim or expand the script, or `vstate.py set min_minutes=.. max_minutes=..` if the brief says so; "
           "the voice phase gives the real length")
    if pr.s.get("format") == "dsa-5part":
        by = {}
        for ln in lines:
            by.setdefault(ln.get("chapter"), []).append(ln)
        names = [str(c).lower() for c in chapters]
        want = {1: "problem", 2: "brute", 3: "intuition", 4: "approach", 5: "code"}
        for n, key in want.items():
            g.ok(n < len(names) and key in names[n] or (n < len(names) and key == "code" and
                 ("c++" in names[n] or "dry" in names[n])),
                 f"chapter {n} is the '{key}' chapter (meta.chapters[{n}] = {names[n] if n < len(names) else '-'})",
                 "dsa-5part order: 0 intro, 1 Problem, 2 Brute force, 3 Intuition, 4 Approaches, 5 Code + dry run")
            g.ok(len(by.get(n, [])) >= 1, f"chapter {n} has lines ({len(by.get(n, []))})")
        g.ok(len(by.get(1, [])) >= 4, "problem chapter decodes inputs, output and examples (>= 4 lines)",
             "one line per input, one for the output, one per example, before any approach")
        qs = [ln for ln in by.get(3, []) if float(ln.get("think", 0) or 0) >= 2.0]
        g.ok(len(qs) >= 2, f"intuition chapter has >= 2 questions with a think pause >= 2 s ({len(qs)})",
             "add think: 2.5 to each question line so the viewer can try first")
        cx = [ln for ln in by.get(2, []) + by.get(4, []) if "O(" in str(ln.get("cap", ""))]
        g.ok(len(cx) >= 3, f"brute force + approaches state time/space as O(...) in captions ({len(cx)})")
        g.ok(any(re.search(r"dry run|dry-run", str(ln.get("cap", "")) + str(ln.get("say", "")), re.I)
                 for ln in by.get(5, [])), "code chapter includes a dry run")
    # voice.py writes meta's frame into timing (1920x1080 at 30 when left out); render and QA check the project's
    c = pr.s.get("config", {})
    off = []
    for k, d in (("width", 1920), ("height", 1080), ("fps", 30)):
        v = meta.get(k, d)  # as voice.py reads it: a key that is present is used as written, even 0 or false
        # a JSON number, as written: voice.py copies it into the scene's timing, and "1920" in quotes reaches the
        # page (and the browser's viewport) as text; a frame side is a whole, even number (H.264 4:2:0 needs it)
        x = float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
        if x is None or not 0 < x < float("inf"):
            off.append(f"{k} {v!r} is not a number above 0 (no quotes)")
        elif k != "fps" and (not x.is_integer() or x % 2):
            off.append(f"{k} {v!r} is not a whole, even number of pixels")
        elif c.get(k) is not None and x != float(c[k]):
            off.append(f"{k} {v} vs {c[k]}")
    g.ok(not off, "meta width, height and fps match the project's frame" + (f" ({', '.join(off)})" if off else ""),
         "set meta.width, meta.height and meta.fps to the frame `vstate.py status` shows")
    # a script generated from script.template.json (motion-video data clips) must match the template and the data now
    fill = os.path.join(SCRIPTS, "motion_fill.py")
    if os.path.exists(pr.p("script.template.json")) and os.path.exists(fill):
        r = subprocess.run([sys.executable, fill, "--project", pr.root, "--check"], capture_output=True, text=True)
        g.ok(r.returncode == 0, "script.json matches script.template.json and the data it reads",
             f"edit script.template.json (not script.json), then: python3 {fill} --project .  and re-voice"
             + (f" ({(r.stdout + r.stderr).strip().splitlines()[-1]})" if (r.stdout + r.stderr).strip() else ""))
    return g


def key_engine(path):
    """The engine a clip's .wav.key records, or "" when the key is missing or unreadable."""
    try:
        return str(json.load(open(path)).get("engine", "")).lower()
    except (OSError, ValueError, AttributeError):
        return ""


def gate_voice(pr):
    g = Gate("voice")
    tpath = pr.p("timing.json")
    if not g.ok(os.path.exists(tpath), "timing.json exists", HINTS["voice"]):
        return g
    t = json.load(open(tpath))
    sc_hash = sha(pr.p("script.json")) if os.path.exists(pr.p("script.json")) else None
    g.ok(t.get("script_hash") == sc_hash, "timing.json was built from the current script.json",
         "the script changed after voicing: run voice.py again")
    # every clip's own record of the engine that voiced it, not just timing.json's summary: a robotic clip reused
    # from an earlier --allow-robotic run must not pass as the natural engine that voiced the rest
    found = [key_engine(pr.p("voice", "lines", f"{ln.get('id')}.wav.key")) for ln in t.get("lines", [])]
    used = {e for e in found if e}
    if not found or not all(found):  # a clip without a readable record of its own
        if t.get("engines"):  # timing.json lists every engine of the run: they count too
            used |= {str(e).lower() for e in t["engines"] if e}
        elif any(found):  # an older timing.json names one engine, not all of them: fail closed
            used.add("unrecorded")
        elif t.get("engine"):  # no clip kept a record (voiced before they did): the summary is all there is
            used.add(str(t["engine"]).lower())
    used = sorted(used) or [""]
    g.ok(len(used) == 1, "one engine voiced every line" + (f" (found {', '.join(used)})" if len(used) > 1 else ""),
         "delete voice/lines and run voice.py again, so one voice reads the whole film")
    engine = used[0] if len(used) == 1 else ", ".join(used)
    robotic = any(e in ROBOTIC_ENGINES for e in used)
    limit_ok = any(L.get("kind") == "voice" and len(L.get("tried", [])) >= 2 for L in pr.s.get("limits", []))
    if robotic:
        g.ok(limit_ok and pr.s["config"].get("allow_robotic") == "yes",
             f"voice engine '{engine}' is robotic",
             "try kokoro, edge-tts and piper first; only with all three failing record "
             "`vstate.py limit ... --tried ... --tried ...` and `vstate.py set allow_robotic=yes`")
    else:
        g.ok(all(e in NATURAL_ENGINES for e in used), f"voice engine is a natural neural voice ({engine or 'unknown'})")
    lines = t.get("lines", [])
    sc_ids = [ln["id"] for ln in load_script(pr).get("lines", [])] if sc_hash else []
    g.ok([ln["id"] for ln in lines] == sc_ids, f"timing covers every script line in order ({len(lines)})")
    miss = [ln["id"] for ln in lines if not os.path.exists(pr.p("voice", "lines", f"{ln['id']}.wav"))]
    g.ok(not miss, "a voice clip exists for every line" + (f" (missing {miss[:5]})" if miss else ""))
    short = [ln["id"] for ln in lines if float(ln.get("voiceDur", 0)) < 0.25]
    g.ok(not short, "no empty voice clips" + (f" ({short[:5]})" if short else ""))
    g.ok(os.path.exists(pr.p("voice", "narration.wav")), "voice/narration.wav exists")
    g.ok(float(t.get("total", 0)) > 5, f"total length {float(t.get('total', 0)):.1f} s")
    return g


def timing_hash(pr):
    tpath = pr.p("timing.json")
    return json.load(open(tpath)).get("hash") if os.path.exists(tpath) else None


def theme_expect(pr):
    """(theme id, 'theme-id: <id>  sha: <fingerprint>' line the emitted theme file must carry), or (None, None)
    when the film keeps its kit's own palette ('original', the default)."""
    tid = pr.cfg("theme") or "original"
    if tid == "original":
        return None, None
    sys.path.insert(0, SCRIPTS)
    import theme as _theme  # noqa: E402  (theme.py ships next to this file)
    t = _theme.resolve(tid)
    return tid, f"theme-id: {tid}  sha: {_theme.fingerprint(t)}"


def find_theme_file(pr, line):
    src = pr.p(pr.cfg("source"))
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "media", "build", "dist", "out", "__pycache__", ".venv", "venv", ".cache")]
        for f in fn:
            if f.startswith("theme"):
                fp = os.path.join(dp, f)
                try:
                    if line in open(fp, encoding="utf-8", errors="ignore").read(200_000):
                        return fp
                except OSError:
                    pass
    return None


def find_timing_consumer(pr, h):
    src = pr.p(pr.cfg("source"))
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in ("node_modules", ".git", "media", "build", "dist", "out", "__pycache__", ".venv", "venv", ".cache")]
        for f in fn:
            if f.startswith("timing"):
                fp = os.path.join(dp, f)
                try:
                    if h and h in open(fp, encoding="utf-8", errors="ignore").read(4_000_000):
                        return fp
                except OSError:
                    pass
    return None


SOURCE_SKIP_DIRS = ("node_modules", ".git", "media", "build", "dist", "out", "__pycache__", ".venv", "venv", ".cache",
                    "segments", ".parcel-cache", ".vite", "output", "renders", ".hyperframes", "snapshots")
SOURCE_SKIP_EXT = (".mp4", ".mov", ".webm", ".pyc")


SCENE_TEXT = (".js", ".mjs", ".cjs", ".jsx", ".ts", ".tsx", ".html", ".htm", ".css", ".json", ".py", ".vue", ".svelte")
VIDEO_EXT = (".mp4", ".mov", ".webm")
# the contact sheets the kits write next to their stills (stills.py's sheet.png, an overview stills-sheet.jpg): only
# these names, since a chapter still is named after its chapter and "Balance sheet" makes ch2-balance-sheet.jpg
SHEET_NAMES = re.compile(r"(contact-|stills-)?sheet\.(png|jpe?g)", re.I)


def is_sheet(path):
    return SHEET_NAMES.fullmatch(os.path.basename(path)) is not None


def still_images(stills):
    """The review stills in a stills folder: its images, contact sheets left out (gate_visuals and legibility.py)."""
    names = sorted(os.listdir(stills)) if os.path.isdir(stills) else []
    return [os.path.join(stills, n) for n in names if n.lower().endswith((".png", ".jpg", ".jpeg")) and not is_sheet(n)]


def files_hash(paths):
    """Content hash of a set of files by name and bytes (a still set: legibility.py records it, gate_visuals checks it)."""
    h = hashlib.sha256()
    for p in sorted(paths, key=os.path.basename):
        h.update(os.path.basename(p).encode() + b"\0" + sha(p).encode() + b"\0")
    return h.hexdigest()[:16]


# a JavaScript string's escapes: \x20, \u0020, \u{20}, and \<char> for the character itself (\' \" \\ \/)
JS_ESCAPE = re.compile(r"\\(?:x([0-9A-Fa-f]{2})|u\{([0-9A-Fa-f]{1,6})\}|u([0-9A-Fa-f]{4})|([^xu0-9bfnrtv\r\n]))")


def js_char(m):
    h = m.group(1) or m.group(2) or m.group(3)
    try:
        return chr(int(h, 16)) if h else m.group(4)
    except (ValueError, OverflowError):  # a code point past U+10FFFF
        return m.group(0)


def js_unescape(text):
    """A JavaScript string's text with its escapes decoded as the browser reads them: a surrogate pair written as two
    escapes (\\uD83D\\uDE00) is one character, as in JavaScript."""
    t = JS_ESCAPE.sub(js_char, text)
    return t.encode("utf-16-le", "surrogatepass").decode("utf-16-le", "surrogatepass")


def name_folds(path):
    """Whether the folder holding path finds the file by its name in other case too (Windows, and macOS by default),
    so a page that asks for clip.mp4 is served Clip.MP4."""
    d, n = os.path.split(path)
    other = n.swapcase()
    try:
        return other != n and os.path.samefile(path, os.path.join(d, other))
    except OSError:
        return False


def scene_videos(src, skip=SOURCE_SKIP_DIRS):
    """The videos under the scene source that its own code or markup names (a clip it plays). They are part of the
    scene: they count in its identity and ship with the package. Any other video there is a render or a preview."""
    vids, code = [], []
    for dp, dn, fn in os.walk(src):
        dn[:] = [d for d in dn if d not in skip]
        for n in fn:
            if n.lower().endswith(VIDEO_EXT):
                vids.append(os.path.normpath(os.path.join(dp, n)))
            elif n.lower().endswith(SCENE_TEXT):  # scene.HTML serves and renders like scene.html
                code.append(os.path.join(dp, n))
    named = set()
    want = {os.path.basename(v).encode() for v in vids}
    folds = {v for v in vids if name_folds(v)}   # matched whatever the case the page writes the name in
    keep = 10 * max(map(len, want), default=0)  # a name written in %20, &#x20; or \u{20} escapes is up to 10x as long
    for f in code if vids else []:  # read in pieces, so a big generated bundle is searched too without loading it whole
        tail = b""
        with open(f, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                buf = tail + chunk
                forms = [buf]
                # the browser reads "my&#32;clip.mp4" in markup and "my\x20clip.mp4" in a script as "my clip.mp4", and
                # the file server decodes a request for "my%20clip.mp4" to the same: match the name in each form a page
                # can write it (a name put together at run time, "my" + " clip.mp4", is out of reach of a text search)
                if b"&" in buf:
                    forms.append(html.unescape(buf.decode("utf-8", "replace")).encode("utf-8", "replace"))
                if b"\\" in buf:
                    forms.append(js_unescape(buf.decode("utf-8", "replace")).encode("utf-8", "replace"))
                forms += [urllib.parse.unquote_to_bytes(x) for x in forms if b"%" in x]
                named |= {v for v in vids if any(os.path.basename(v).encode() in x for x in forms)}
                if folds - named:
                    low = [x.decode("utf-8", "replace").casefold() for x in forms]
                    named |= {v for v in folds if any(os.path.basename(v).casefold() in x for x in low)}
                tail = buf[-keep:]
        if len(named) == len(vids):
            break
    return named


def source_files(pr):
    """Every file of the scene source that can change what the film looks like (no caches, no renders; a video only
    when the scene plays it)."""
    src = pr.p(pr.cfg("source"))
    clips = scene_videos(src)
    out = []
    for dp, dn, fn in os.walk(src):
        dn[:] = sorted(d for d in dn if d not in SOURCE_SKIP_DIRS)
        for f in sorted(fn):
            if not f.lower().endswith(SOURCE_SKIP_EXT) or os.path.normpath(os.path.join(dp, f)) in clips:
                out.append(os.path.join(dp, f))
    return out


def source_hash(pr):
    """Content hash of the scene source: the identity the stills, the render and QA are tied to. An edit to any
    scene file changes it, whatever the file's mtime says."""
    h = hashlib.sha256()
    src = pr.p(pr.cfg("source"))
    for fp in source_files(pr):
        h.update(os.path.relpath(fp, src).encode())
        h.update(b"\0")
        try:
            with open(fp, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 20), b""):
                    h.update(chunk)
        except OSError:
            pass
        h.update(b"\0")
    return h.hexdigest()[:16]


def source_newest(pr):
    return max([mtime(f) for f in source_files(pr)], default=0)


def artifact_identity(pr, name, path):
    """Pin an artifact (the silent render, the final video) to the scene source it was made from. The first time
    a given file is seen its source hash is recorded; from then on the same file with a different source hash
    means the scene source was edited after it was made. Returns (ok, detail)."""
    cur = source_hash(pr)
    ids = pr.s.setdefault("artifacts", {})
    fsha = sha(path)
    rec = ids.get(name)
    if rec is None or rec.get("sha") != fsha:
        ids[name] = {"sha": fsha, "source_hash": cur, "at": now()}
        pr.save()
        return True, "made from the current scene source (recorded)"
    if rec.get("source_hash") != cur:
        return False, f"the scene source changed after this file was made (source {rec.get('source_hash')} -> {cur})"
    return True, "made from the current scene source"


def latest_attest(pr, phase):
    a = [x for x in pr.s.get("attest", []) if x["phase"] == phase]
    return a[-1] if a else None


def gate_visuals(pr):
    g = Gate("visuals")
    src = pr.p(pr.cfg("source"))
    if not g.ok(os.path.isdir(src), f"source folder exists ({pr.cfg('source')})", "copy the skill's assets/template there"):
        return g
    h = timing_hash(pr)
    cons = find_timing_consumer(pr, h)
    g.ok(cons is not None, "the scene code reads the current timing (timing file with this hash in source/)",
         "run voice.py with --emit pointing into source/ so scenes are timed to the real voice")
    try:
        tid, line = theme_expect(pr)
    except SystemExit:
        tid, line = pr.cfg("theme"), None
        g.ok(False, f"theme '{tid}' is in the registry", f"python3 {SCRIPTS}/theme.py list")
    if line:
        g.ok(find_theme_file(pr, line) is not None,
             f"the scene code reads the current '{tid}' theme (a theme* file in source/ carrying '{line}')",
             f"python3 {SCRIPTS}/theme.py emit {tid} --format <your kit's format> --out <the theme file your kit reads>  "
             "(see the skill's Themes section)")
    stills = pr.p(pr.cfg("stills"))
    imgs = [os.path.join(stills, f) for f in os.listdir(stills)] if os.path.isdir(stills) else []
    imgs = [f for f in imgs if f.lower().endswith((".png", ".jpg", ".jpeg"))]
    nch = len(load_script(pr).get("meta", {}).get("chapters", [])) if os.path.exists(pr.p("script.json")) else 1
    shots = still_images(stills)  # a contact sheet is not a still of its own
    g.ok(len(shots) >= max(3, nch), f"review stills rendered ({len(shots)} in {pr.cfg('stills')}/, need >= {max(3, nch)})",
         "render at least one still per chapter (plus the busiest moments) into the stills folder")
    newest = max([mtime(f) for f in imgs], default=0)
    # every still, not just the newest: one re-shot still would otherwise vouch for the rest (contact sheets aside)
    oldest = min([mtime(f) for f in shots], default=0)
    g.ok(oldest >= mtime(pr.p("timing.json")), "every still is newer than timing.json",
         "re-render all the stills after re-voicing (and remove stills no longer shot)")
    g.ok(oldest >= source_newest(pr), "every still is newer than every scene source file",
         "a scene file changed after the stills were shot: re-shoot all the stills (and remove stills no longer shot), "
         "run legibility.py and attest again")
    leg = None
    try:
        with open(os.path.join(stills, "legibility.json"), encoding="utf-8") as f:
            leg = json.load(f)
    except (OSError, ValueError):
        pass
    if leg is not None and "source_hash" in leg:
        # by content: a scene edit or a re-shot still after the check counts whatever its mtime (cp -p keeps the old one)
        fresh = leg.get("source_hash") == source_hash(pr) and leg.get("stills_hash") == files_hash(shots)
    else:  # a report from before legibility.py recorded what it checked
        fresh = leg is not None and leg.get("newest_still", 0) + 1 >= max([mtime(f) for f in shots], default=0) \
            and leg.get("images", 0) >= len(shots)
    state = ("not run" if leg is None else "made for other stills or an earlier scene source" if not fresh
             else f"{leg.get('fails')} texts failing")
    g.ok(fresh and leg.get("fails", 1) == 0, f"every text in the stills is at least 26 px with 4.5:1 contrast (legibility: {state})",
         f"python3 {SCRIPTS}/legibility.py --project .  then open {pr.cfg('stills')}/legibility/ and enlarge or brighten "
         "every red box (dimmed context must stay readable), re-shoot the stills and run it again")
    rules = (leg or {}).get("rules", {})
    strict = (rules.get("min_px", 0) >= 26 and rules.get("min_contrast", 0) >= 4.5
              and rules.get("min_contrast_large", rules.get("min_contrast", 0)) >= 4.5 and rules.get("tolerance", 1) == 0)
    g.ok(leg is None or strict, "legibility.py ran with the written rules (26 px, 4.5:1 for every text, no tolerance)",
         "run legibility.py with its default rules; lower thresholds do not count")
    a = latest_attest(pr, "visuals")
    g.ok(a is not None and iso_to_ts(a["at"]) + 1 >= newest and len(a["text"]) >= 40,
         "you looked at the newest stills and wrote down what you checked (attest visuals)",
         "open every still, fix overlaps/clipped text/ligatures/empty frames, then "
         "vstate.py attest visuals \"<what you checked and fixed>\"")
    g.ok(a is None or a.get("source_hash") in (None, source_hash(pr)) and iso_to_ts(a.get("at", "")) >= source_newest(pr),
         "your review of the stills is for the current scene source",
         "a scene file changed after you attested: re-shoot the stills, run legibility.py and attest visuals again")
    return g


def gate_render(pr):
    g = Gate("render")
    path = pr.p(pr.cfg("silent"))
    if not g.ok(os.path.exists(path), f"silent render exists ({pr.cfg('silent')})", HINTS["render"]):
        return g
    vf = video_facts(path)
    if not g.ok(vf is not None, "ffprobe can read the render"):
        return g
    c = pr.s["config"]
    g.ok(vf["vcodec"] == "h264", f"video codec is h264 ({vf['vcodec']})")
    g.ok((vf["width"], vf["height"]) == (c["width"], c["height"]),
         f"resolution {vf['width']}x{vf['height']} matches {c['width']}x{c['height']}")
    g.ok(vf["fps"] and abs(vf["fps"] - c["fps"]) < 0.01, f"frame rate {vf['fps']} matches {c['fps']}")
    t = json.load(open(pr.p("timing.json")))
    tol = max(1.0, 0.01 * t["total"])
    g.ok(abs(vf["duration"] - t["total"]) <= tol,
         f"duration {vf['duration']:.2f} s matches the voice timing {t['total']:.2f} s (+/- {tol:.1f})",
         "the scenes are not following timing.json; fix the scene durations, do not stretch the audio")
    g.ok(mtime(path) >= mtime(pr.p("timing.json")), "render is newer than timing.json")
    g.ok(mtime(path) >= source_newest(pr), "render is newer than every scene source file",
         "a scene file changed after this render: render again")
    # a render's file is pinned the first time this gate sees it, which can be after an edit made while it ran
    # (renderers load the page once), so the source must also still be the one whose stills were reviewed
    a = latest_attest(pr, "visuals")
    reviewed = a.get("source_hash") if a else None
    g.ok(reviewed in (None, source_hash(pr)), "the scene source is the one whose stills you reviewed",
         "a scene file changed after attest visuals (perhaps while rendering): vstate.py reopen visuals, re-shoot "
         "the stills, attest, then render again")
    ok, why = artifact_identity(pr, "silent", path)
    g.ok(ok, f"render is {why}", "the scene source was edited after this render: render again (then mix and QA again)")
    man = pr.p("build", "segments", "manifest.json")
    if os.path.exists(man):
        m = json.load(open(man))
        todo = [s for s in m.get("segments", []) if not s.get("done")]
        g.ok(not todo, f"all render segments finished ({len(m.get('segments', [])) - len(todo)}/{len(m.get('segments', []))})",
             "re-run the render command; finished segments are skipped")
    return g


MIX_INPUTS = ("voice/narration.wav", "audio/music.wav", "audio/sfx.wav", "audio/bed.m4a")
MUSIC_MOODS = ("calm", "piano", "pulse", "none")  # music.py's beds (script-format.md: meta.music)
SFX_KINDS = ("whoosh", "pop", "chime", "tick", "click", "thud", "rise")  # music.py's effects (script-format.md: sfx)


def mix_inputs(root, final):
    """What mix.py recorded the final was mixed from ({file: content hash}, audio/mix.json), or None when there is
    no record for this final (mixed before the record existed, or by hand)."""
    try:
        rec = json.load(open(os.path.join(root, "audio", "mix.json")))
    except (OSError, ValueError):
        return None
    used = rec.get("inputs") if isinstance(rec, dict) else None
    if not isinstance(used, dict) or not os.path.isfile(final) or rec.get("final_sha") != sha(final):
        return None
    return used


def mix_changed(root, final):
    """The files that changed since `final` was mixed from them. mix.py records the content hash of each (the audio
    and the silent render) next to the final's (audio/mix.json); with that record for this final, a file counts as
    changed when its bytes differ, whatever its time. A final mixed before the record existed (or by hand) falls back
    to: an audio file newer than the final."""
    used = mix_inputs(root, final)
    if used is not None:
        now = lambda f: sha(os.path.join(root, f)) if os.path.isfile(os.path.join(root, f)) else None  # noqa: E731
        return [f for f in used if used[f] != now(f)]   # the audio, and the silent render the picture came from
    return [f for f in MIX_INPUTS if os.path.exists(os.path.join(root, f))
            and os.path.getmtime(os.path.join(root, f)) > os.path.getmtime(final)]


def mix_videos(used):
    """The videos a mix record names as the final's picture (every input but the audio files): one from mix.py
    today, none from a mix.py that recorded only the audio."""
    return [f for f in used if f not in MIX_INPUTS]


def gate_mix(pr):
    g = Gate("mix")
    path = pr.p(pr.cfg("final"))
    if not g.ok(os.path.exists(path), f"final video exists ({pr.cfg('final')})", HINTS["mix"]):
        return g
    vf = video_facts(path)
    g.ok(vf is not None and vf["acodec"] == "aac", "final has an AAC audio track (voice baked in)")
    g.ok(vf is not None and vf["pix_fmt"] == "yuv420p", f"pixel format yuv420p ({vf and vf['pix_fmt']})",
         "re-encode with -pix_fmt yuv420p (mix.py does this automatically)")
    g.ok(mtime(path) >= mtime(pr.p(pr.cfg("silent"))), "final is newer than the silent render")
    g.ok(os.path.exists(pr.p("audio", "bed.m4a")), "audio/bed.m4a (music + effects, no voice) exists for voice swaps")
    # mix.py writes the bed, then the final, from these: one changed since (a new music mood, a new voice, a replaced
    # bed) means the final still has the old sound, or the bed shipped for voice swaps no longer matches it
    newer = mix_changed(pr.root, path)
    g.ok(not newer, "final is newer than its audio (narration, music, effects, bed)" + (f"; changed since: {', '.join(newer)}" if newer else ""),
         "the audio changed after the mix: run mix.py again, then qa.py")
    return g


def gate_qa(pr):
    g = Gate("qa")
    rp = pr.p("qa", "report.json")
    if not g.ok(os.path.exists(rp), "qa/report.json exists", HINTS["qa"]):
        return g
    r = json.load(open(rp))
    final = pr.p(pr.cfg("final"))
    g.ok(os.path.exists(final) and r.get("video_sha") == sha(final), "the QA report is for the current final video",
         "the video changed after QA: run qa.py again")
    names = {c["name"] for c in r.get("checks", [])}
    # review-images: the contact sheet and stills were written (qa.py checks it; a report from before that lacks it)
    missing = [n for n in QA_HARD_CHECKS + ("review-images",) if n not in names]
    g.ok(not missing, "the QA report holds every hard check" + (f" (missing: {', '.join(missing)})" if missing else ""),
         "run qa.py in full (no --skip-flicker); a report without a check cannot pass the gate")
    for c in r.get("checks", []):
        if c["level"] == "fail":
            # a skipped check cannot be waived, and a waiver needs a reason (older qa.py wrote "waived" without one)
            skipped = c.get("skipped") or str(c.get("detail", "")).startswith("skipped")
            waived = None if skipped else str(c.get("waived") or "").strip()
            waived = waived if waived and waived != "waived" else None
            g.ok(c["ok"] or waived, f"qa: {c['name']}: {c['detail']}" + (" (waived: " + waived + ")" if waived else ""),
                 "a skipped check cannot be waived, and a waiver needs its reason" if c.get("waived") and not waived else "")
        elif not c["ok"]:
            g.warn(False, f"qa: {c['name']}: {c['detail']}")
    a = latest_attest(pr, "qa")
    g.ok(a is not None and iso_to_ts(a["at"]) + 1 >= mtime(rp) and len(a["text"]) >= 60,
         "you viewed the contact sheet and stills and wrote down what you saw (attest qa)",
         "open qa/contact-sheet.png and qa/stills/*, then vstate.py attest qa \"<what you saw, what you fixed>\"")
    return g


def gate_deliver(pr):
    g = Gate("deliver")
    d = pr.p(pr.cfg("deliver"))
    if not g.ok(os.path.isdir(d), f"deliver folder exists ({pr.cfg('deliver')})", HINTS["deliver"]):
        return g
    slug = pr.s["slug"]
    need = [f"{slug}.mp4", "captions.srt", "timeline.json", "NOTES.md", "contact-sheet.png", "edge_voice_swap.py", "bed.m4a",
            "voice/narration.wav"]   # the narration source/'s preview and editor play
    for f in need:
        g.ok(os.path.exists(os.path.join(d, f)), f"deliver/{f}")
    g.ok(os.path.isdir(os.path.join(d, "source")), "deliver/source/ (re-renderable project)")
    nm = [p for p in ("node_modules", "media", ".venv") if os.path.isdir(os.path.join(d, "source", p))]
    g.ok(not nm, "deliver/source has no dependency or cache folders" + (f" ({nm})" if nm else ""))
    rp = pr.p("qa", "report.json")
    mp4 = os.path.join(d, f"{slug}.mp4")
    if os.path.exists(rp) and os.path.exists(mp4):
        g.ok(json.load(open(rp)).get("video_sha") == sha(mp4), "delivered MP4 is the exact file that passed QA")
    notes = os.path.join(d, "NOTES.md")
    if os.path.exists(notes):
        txt = open(notes, encoding="utf-8").read().lower()
        t = json.load(open(pr.p("timing.json")))
        g.ok(str(t.get("engine", "")).lower() in txt, "NOTES.md names the voice engine")
        g.ok("limit" in txt, "NOTES.md states the environment limits (or says there were none)")
    return g


GATES = dict(brief=gate_brief, script=gate_script, voice=gate_voice, visuals=gate_visuals,
             render=gate_render, mix=gate_mix, qa=gate_qa, deliver=gate_deliver)


# ----------------------------------------------------------------------------- commands
def cmd_init(pr, a):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", a.slug):  # it names files: out/<slug>.mp4, deliver/<slug>.mp4
        sys.exit(f"--slug {a.slug!r}: use letters, digits, '.', '_' and '-' (no '/' or spaces), e.g. cheapest-flights")
    if os.path.exists(pr.path) and not a.force:
        sys.exit(f"{STATE} already exists; use `status` to resume (or --force to start over)")
    os.makedirs(pr.root, exist_ok=True)
    pr.s = {
        "version": 1, "tool": a.tool, "slug": a.slug, "format": a.format, "created": now(), "phase": "brief",
        "phases": {p: {"status": "todo"} for p in PHASES},
        "config": {"width": a.width, "height": a.height, "fps": a.fps},
        "attest": [], "limits": [], "notes": [], "log": [],
    }
    if a.format == "dsa-5part":
        pr.s["config"].update(min_minutes=2.0, max_minutes=8.0)
    pr.save()
    print(f"initialised {pr.path}\nphase: brief\nnext:  {HINTS['brief']}")


def revalidate(pr):
    """Re-run the gates of every phase already marked done. The first one that no longer passes (a script edited
    after voicing, a video changed after QA) sends the project back to that phase, so a stale phase can never be
    skipped by advancing. Returns that phase, or None."""
    cur = pr.s["phase"]
    upto = PHASES.index(cur) if cur in PHASES else len(PHASES)
    for p in PHASES[:upto]:
        if pr.s["phases"][p]["status"] != "done":
            continue
        g = GATES[p](pr)
        if g.passed:
            continue
        fails = [m for st, m, _ in g.items if st == "FAIL"]
        for q in PHASES[PHASES.index(p):]:
            if pr.s["phases"][q]["status"] == "done":
                pr.s["phases"][q]["status"] = "stale"
        pr.s["phase"] = p
        pr.log("stale", p, fails=fails)
        pr.save()
        print(f"STALE: '{p}' passed earlier but no longer does: {'; '.join(fails[:3])}\n"
              f"phase is back to {p}; later phases must pass again.")
        return p
    return None


def cmd_status(pr, a):
    s = pr.load()
    revalidate(pr)
    print(f"{s['slug']}  ({s['tool']}, {s['format']}, {s['config']['width']}x{s['config']['height']}@{s['config']['fps']})")
    for p in PHASES:
        st = s["phases"][p]["status"]
        mark = {"done": "[x]", "todo": "[ ]", "stale": "[~]"}.get(st, "[?]")
        cur = "  <- current" if p == s["phase"] else ""
        print(f"  {mark} {p}{cur}")
    if s["phase"] == "complete":
        print("\nall phases passed; the video is delivered.")
        return
    for L in s.get("limits", []):
        print(f"  limit: {L['what']}  (tried: {'; '.join(L['tried'])})")
    print(f"\nnext: {HINTS[s['phase']]}")


def run_gate(pr, phase):
    g = GATES[phase](pr)
    print(f"gate: {phase}")
    g.show()
    print("PASSED" if g.passed else "NOT PASSED")
    return g


def cmd_check(pr, a):
    pr.load()
    phase = a.phase or pr.s["phase"]
    if phase == "complete":
        print("complete")
        return 0
    return 0 if run_gate(pr, phase).passed else 1


def cmd_advance(pr, a):
    pr.load()
    if revalidate(pr):
        print(f"next: {HINTS[pr.s['phase']]}")
        return 1
    phase = pr.s["phase"]
    if phase == "complete":
        print("already complete")
        return 0
    g = run_gate(pr, phase)
    if not g.passed:
        pr.log("gate-failed", phase, fails=[m for s, m, _ in g.items if s == "FAIL"])
        pr.save()
        return 1
    pr.s["phases"][phase] = {"status": "done", "at": now(), "warnings": [m for s, m, _ in g.items if s == "WARN"]}
    nxt = PHASES[PHASES.index(phase) + 1] if phase != PHASES[-1] else "complete"
    pr.s["phase"] = nxt
    pr.log("advance", f"{phase} -> {nxt}")
    pr.save()
    print(f"\n{phase} done. phase is now: {nxt}")
    if nxt != "complete":
        print(f"next: {HINTS[nxt]}")
    return 0


def cmd_reopen(pr, a):
    pr.load()
    if a.phase not in PHASES:
        sys.exit(f"unknown phase {a.phase}")
    i = PHASES.index(a.phase)
    for p in PHASES[i:]:
        if pr.s["phases"][p]["status"] == "done":
            pr.s["phases"][p]["status"] = "stale"
    pr.s["phase"] = a.phase
    pr.log("reopen", a.reason or "", phase=a.phase)
    pr.save()
    print(f"phase is now {a.phase}; later phases must pass again.")


def cmd_attest(pr, a):
    pr.load()
    if a.phase not in PHASES:
        sys.exit(f"unknown phase {a.phase}")
    if len(a.text.strip()) < 20:
        sys.exit("say what you looked at and what you found (at least a sentence)")
    entry = {"phase": a.phase, "at": now(), "text": a.text.strip()}
    if os.path.isdir(pr.p(pr.cfg("source"))):
        entry["source_hash"] = source_hash(pr)  # the review is for this scene source; an edit after it voids it
    if a.file:
        entry["files"] = a.file
    pr.s.setdefault("attest", []).append(entry)
    pr.save()
    print("recorded")


def cmd_note(pr, a):
    pr.load()
    pr.s.setdefault("notes", []).append({"at": now(), "text": a.text})
    pr.save()
    print("noted")


def cmd_limit(pr, a):
    pr.load()
    if len(a.tried or []) < 2:
        sys.exit("a limit needs at least two --tried entries: name each alternative you tried and what happened. "
                 "Nothing is 'impossible' until the alternatives have been tried.")
    pr.s.setdefault("limits", []).append({"at": now(), "what": a.what, "tried": a.tried, "kind": a.kind,
                                          "env": not a.not_env})
    pr.save()
    print("limit recorded; it will appear in NOTES.md and the final report")


def cmd_set(pr, a):
    pr.load()
    for kv in a.kv:
        if "=" not in kv:
            sys.exit(f"expected key=value, got {kv}")
        k, v = kv.split("=", 1)
        if k in ("width", "height"):
            v = int(v)
        elif k == "fps":
            v = float(v) if "." in v else int(v)
        elif re.fullmatch(r"-?\d+(\.\d+)?", v):  # numbers stay numbers (min_minutes=0.5)
            v = float(v) if "." in v else int(v)
        pr.s["config"][k] = v
    pr.save()
    print(json.dumps(pr.s["config"], indent=1))


def cmd_notes_md(pr, a):
    s = pr.load()
    t = json.load(open(pr.p("timing.json"))) if os.path.exists(pr.p("timing.json")) else {}
    lim = s.get("limits", [])
    lines = [
        f"# {s['slug']}: how this video was made",
        "",
        f"- **Tool:** {s['tool']} (versions: fill in)",
        f"- **Voice:** {t.get('engine', '?')} `{t.get('voice', '?')}` at speed {t.get('speed', '?')}, baked into the MP4.",
        f"- **Length:** {float(t.get('total', 0)) / 60:.1f} min, {s['config']['width']}x{s['config']['height']} at {s['config']['fps']} fps.",
        f"- **Style:** theme `{s['config'].get('theme') or 'original'}` (palette, type, persistent subject: fill in)",
        "- **Re-render:** (exact commands, in order)",
        "- **Swap the voice:** `python edge_voice_swap.py en-IN-NeerjaNeural` on a laptop (needs `pip install edge-tts` and ffmpeg).",
        "- **Limits:** " + ("; ".join(f"{L['what']} (tried: {', '.join(L['tried'])})" for L in lim) if lim
                            else "none hit; nothing was cut."),
    ]
    print("\n".join(lines))


def cmd_report(pr, a):
    s = pr.load()
    revalidate(pr)
    final = pr.p(pr.cfg("deliver"), f"{s['slug']}.mp4")
    if not os.path.exists(final):
        final = pr.p(pr.cfg("final"))
    vf = video_facts(final) if os.path.exists(final) else None
    t = json.load(open(pr.p("timing.json"))) if os.path.exists(pr.p("timing.json")) else {}
    print(f"phase: {s['phase']}")
    if vf:
        print(f"video: {final}\n  {vf['duration'] / 60:.2f} min, {vf['width']}x{vf['height']} @ {vf['fps']} fps, "
              f"{vf['vcodec']}/{vf['acodec']}")
    print(f"voice: {t.get('engine')} {t.get('voice')}")
    for L in s.get("limits", []):
        print(f"limit: {L['what']} (tried: {'; '.join(L['tried'])})")
    for p in PHASES:
        w = s["phases"][p].get("warnings")
        if w:
            print(f"warnings at {p}: " + " | ".join(w))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    sub = ap.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("init")
    i.add_argument("--tool", required=True)
    i.add_argument("--slug", required=True)
    i.add_argument("--format", default="dsa-5part", choices=["dsa-5part", "general"])
    i.add_argument("--width", type=int, default=1920)
    i.add_argument("--height", type=int, default=1080)
    i.add_argument("--fps", type=int, default=30)
    i.add_argument("--force", action="store_true")
    sub.add_parser("status")
    c = sub.add_parser("check")
    c.add_argument("phase", nargs="?")
    sub.add_parser("advance")
    r = sub.add_parser("reopen")
    r.add_argument("phase")
    r.add_argument("--reason", default="")
    at = sub.add_parser("attest")
    at.add_argument("phase")
    at.add_argument("text")
    at.add_argument("--file", action="append")
    n = sub.add_parser("note")
    n.add_argument("text")
    lm = sub.add_parser("limit")
    lm.add_argument("what")
    lm.add_argument("--tried", action="append")
    lm.add_argument("--kind", default="other", help="voice | render | font | network | other")
    lm.add_argument("--not-env", action="store_true", help="the limit is a choice, not the environment")
    st = sub.add_parser("set")
    st.add_argument("kv", nargs="+")
    sub.add_parser("notes-md")
    sub.add_parser("report")
    a = ap.parse_args()
    pr = Project(a.project)
    fn = {"init": cmd_init, "status": cmd_status, "check": cmd_check, "advance": cmd_advance, "reopen": cmd_reopen,
          "attest": cmd_attest, "note": cmd_note, "limit": cmd_limit, "set": cmd_set, "notes-md": cmd_notes_md,
          "report": cmd_report}[a.cmd]
    sys.exit(fn(pr, a) or 0)


if __name__ == "__main__":
    main()
