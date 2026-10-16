#!/usr/bin/env python3
"""voice.py: voice every line of script.json and lay out the film's timing from the real line lengths.

The picture follows the voice, never the other way round: each line gets a slot of
    lead + spoken length + pad + think   (at least `min`)
and the scene code reads the resulting timing file, so audio and animation are in sync by construction.

Engines, tried in this order by --engine auto (the default):
  kokoro    Kokoro-82M, offline neural TTS (pip install kokoro-onnx soundfile; model auto-downloaded)
  edge-tts  Microsoft neural voices (needs network access to speech.platform.bing.com; works on most laptops)
  piper     Piper offline neural TTS (pip install piper-tts; voice model auto-downloaded)
A robotic engine (espeak-ng) is used only with --allow-robotic, which you may pass only after all three
natural engines failed and you recorded that with `vstate.py limit`. Never ship a silent video and never
tell the user a natural voice is impossible before this ladder has been tried.

Usage:
  python3 voice.py --project . [--engine auto|kokoro|edge-tts|piper] [--voice af_heart] [--speed 1.0]
                   [--chapter-lead 1.0] [--sentence-pause 0.3]
                   [--emit source/src/timing.ts] [--emit source/timing.js] ...
Each line is voiced one sentence at a time with `sentence_pause` seconds between sentences, and the first line of
every chapter after the first waits `chapter_lead` seconds so the chapter card and the next subject are on screen
before the voice starts (both also settable in script.json meta).
Outputs:
  voice/lines/<id>.wav    one clip per line (24 kHz mono, silence trimmed, cached by text+voice)
  voice/narration.wav     every clip placed at its time (what the final mix uses)
  timing.json             {total, chapters, scenes, lines:[{id,start,voiceAt,voiceDur,think,end,dur,chapter,cap,say}]}
  timeline.json           deliverable: [{id,start,dur,chapter,text,say,pause}] (used by edge_voice_swap.py)
  each --emit target      the same timing as .json / .js (window.TIMING) / .ts / .mjs / .py, stamped with its hash
"""
import argparse
import asyncio
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pydeps  # noqa: E402  (pydeps.py ships next to this file)

SR = 24000
KOKORO_FILES = {
    "kokoro-v1.0.onnx": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
    "voices-v1.0.bin": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}
# SHA-256 of the files above, checked after every download (a swapped or truncated model is refused)
KOKORO_SHA256 = {
    "kokoro-v1.0.onnx": "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5",
    "voices-v1.0.bin": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
}
# exact versions for what pip installs at run time (kokoro-onnx 0.6.1 needs Python 3.10 to 3.13)
PINS = {"kokoro-onnx": "kokoro-onnx==0.6.1", "soundfile": "soundfile==0.14.0", "edge-tts": "edge-tts==7.2.8",
        "piper-tts": "piper-tts==1.8.0", "numpy": "numpy>=1.24"}
PIPER_VOICE = "en_US-lessac-medium"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US/lessac/medium/"
# MD5 of the files above as rhasspy publishes them (voices.json in rhasspy/piper-samples; upstream lists no SHA-256),
# checked after every download and on cached files
PIPER_MD5 = {".onnx": "2fc642b535197b6305c7c8f92dc8b24f", ".onnx.json": "c1f2b7bddefe113f3255ff9ef234cfd3"}
ROBOTIC = {"espeak-ng"}  # engines that need --allow-robotic, for new clips and for reusing cached ones
DEFAULT_VOICE = {"kokoro": "af_heart", "edge-tts": "en-US-AriaNeural", "piper": PIPER_VOICE, "espeak-ng": "en-us"}


def log(*a):
    print(*a, flush=True)


def need(mod, pip_name=None):
    """Import a module, installing it with pip once if it is missing; where pip refuses (Homebrew, Debian/Ubuntu,
    Python 3.14) pydeps.py re-runs this script in the pipeline's own environment."""
    return pydeps.need(mod, pip_name)


def sha256_of(path, algo="sha256"):
    h = hashlib.new(algo)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verified(path, sha256, algo="sha256"):
    """True when the file exists and matches the digest (remembered in <file>.sha256 so it is hashed once). The memory
    is keyed on the file's inode and change time (ctime), which every write sets and neither utime nor cp -p can put
    back, so a same-size rewrite with its old mtime is hashed again."""
    if not os.path.exists(path):
        return False
    mark = path + ".sha256"
    st = os.stat(path)
    stamp = f"{algo}:{sha256} {st.st_size} {st.st_ino} {st.st_ctime_ns}"
    try:
        with open(mark, encoding="utf-8") as f:
            if f.read().strip() == stamp:
                return True
    except OSError:
        pass
    if sha256_of(path, algo) != sha256:
        return False
    with open(mark, "w", encoding="utf-8") as f:
        f.write(stamp)
    return True


def download(url, dest, tries=4, sha256=None, md5=None):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    last = None
    tmp = dest + ".part"
    for i in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=120) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f, 1 << 20)
        except Exception as e:  # noqa: BLE001
            last = e
            if not (shutil.which("curl") and subprocess.run(["curl", "-sSfL", "--retry", "3", "-o", tmp, url]).returncode == 0):
                import time
                time.sleep(2 ** (i + 1))
                continue
        if (sha256 and sha256_of(tmp) != sha256) or (md5 and sha256_of(tmp, "md5") != md5):
            os.remove(tmp)
            raise RuntimeError(f"{url} does not match its pinned digest; refusing to use it (file deleted)")
        os.replace(tmp, dest)
        if not (sha256 or md5):
            log(f"  {os.path.basename(dest)} sha256 {sha256_of(dest)} (no pinned hash for this file; compare it with the source)")
        return
    raise RuntimeError(f"download failed for {url}: {last}")


# ----------------------------------------------------------------------------- engines
class Kokoro:
    name = "kokoro"

    def __init__(self, voice, speed, model_dir=None, lang=None):
        np = need("numpy", PINS["numpy"])  # noqa: F841
        need("soundfile", PINS["soundfile"])
        need("kokoro_onnx", PINS["kokoro-onnx"])
        from kokoro_onnx import Kokoro as K
        d = model_dir or os.environ.get("KOKORO_DIR") or os.path.expanduser("~/.cache/kokoro")
        for f, url in KOKORO_FILES.items():
            p = os.path.join(d, f)
            if verified(p, KOKORO_SHA256[f]):
                continue
            if os.path.exists(p) and os.environ.get("KOKORO_ALLOW_UNPINNED") == "1":
                log(f"WARNING: {p} does not match the pinned SHA-256; using it because KOKORO_ALLOW_UNPINNED=1 "
                    f"(sha256 {sha256_of(p)}). Record this in NOTES.md.")
                continue
            log(f"downloading {f} (Kokoro model) to {d} ...")
            download(url, p, sha256=KOKORO_SHA256[f])
        self.k = K(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
        self.voice, self.speed = voice, speed
        # en-gb for British voices, en-us otherwise; pass lang ("hi", "es", "fr-fr"...) to narrate in another language
        self.lang = lang or ("en-gb" if voice.startswith(("bf_", "bm_")) else "en-us")
        if voice not in self.k.get_voices():
            raise RuntimeError(f"unknown Kokoro voice {voice}; try one of {sorted(self.k.get_voices())[:12]}")

    def say(self, text):
        import numpy as np
        x, sr = self.k.create(text, voice=self.voice, speed=self.speed, lang=self.lang)
        x = np.asarray(x, dtype=np.float32)
        return resample(x, sr, SR) if sr != SR else x


class EdgeTTS:
    name = "edge-tts"

    def __init__(self, voice, speed):
        need("edge_tts", PINS["edge-tts"])
        self.voice, self.rate = voice, f"{int(round((speed - 1) * 100)):+d}%"
        self.say("Test.")  # fail fast if the service is blocked

    def say(self, text):
        import edge_tts
        with tempfile.TemporaryDirectory() as td:
            mp3 = os.path.join(td, "a.mp3")
            asyncio.run(edge_tts.Communicate(text, self.voice, rate=self.rate).save(mp3))
            return decode(mp3)


class Piper:
    name = "piper"

    def __init__(self, voice, speed):
        need("piper", PINS["piper-tts"])
        d = os.path.expanduser("~/.cache/piper")
        model = os.path.join(d, f"{voice}.onnx")
        if voice == PIPER_VOICE:
            for ext in (".onnx", ".onnx.json"):
                p = os.path.join(d, voice + ext)
                if not verified(p, PIPER_MD5[ext], "md5"):
                    log(f"downloading piper voice {voice}{ext} ...")
                    download(PIPER_BASE + voice + ext + "?download=true", p, md5=PIPER_MD5[ext])
        from piper import PiperVoice
        self.v = PiperVoice.load(model)
        self.speed = speed

    def say(self, text):
        import numpy as np
        import wave
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.wav")
            with wave.open(p, "wb") as w:
                try:
                    from piper import SynthesisConfig
                    self.v.synthesize_wav(text, w, syn_config=SynthesisConfig(length_scale=1 / self.speed))
                except ImportError:
                    self.v.synthesize(text, w, length_scale=1 / self.speed)
            return decode(p) if os.path.getsize(p) > 100 else np.zeros(1, np.float32)


class Espeak:
    name = "espeak-ng"

    def __init__(self, voice, speed):
        if not shutil.which("espeak-ng"):
            raise RuntimeError("espeak-ng not installed")
        self.voice, self.speed = voice, speed

    def say(self, text):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "a.wav")
            subprocess.run(["espeak-ng", "-v", self.voice, "-s", str(int(165 * self.speed)), "-w", p, text], check=True)
            return decode(p)


ENGINES = {"kokoro": Kokoro, "edge-tts": EdgeTTS, "piper": Piper, "espeak-ng": Espeak}


def decode(path):
    import numpy as np
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"])
    return np.frombuffer(raw, dtype=np.float32).copy()


def resample(x, sr, to):
    import numpy as np
    n = int(round(len(x) * to / sr))
    return np.interp(np.arange(n) * sr / to, np.arange(len(x)), x).astype(np.float32)


def trim(x, thr=0.004):
    import numpy as np
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    a = max(0, idx[0] - int(0.03 * SR))
    b = min(len(x), idx[-1] + int(0.08 * SR))
    return x[a:b]


def voice_engine(voice):
    """The engine a voice name belongs to: en-IN-NeerjaNeural is edge-tts, en_US-lessac-medium is piper,
    af_heart is kokoro. None when the name fits none of them."""
    if not voice:
        return None
    if voice.endswith("Neural"):
        return "edge-tts"
    if re.fullmatch(r"[a-z]{2,3}_[A-Z]{2}-[A-Za-z0-9_]+-(x_low|low|medium|high)", voice):
        return "piper"
    if re.fullmatch(r"[a-z]{2}_[a-z]+", voice):
        return "kokoro"
    return None


# a sentence ends at . ? ! (with any closing quotes or brackets) before a space, or at a full-width 。？！ (with
# its closers) whether or not a space follows; "1.5" and "e.g.x" do not end one
SENTENCE_END = re.compile(r"[.?!][\"'\u201d\u2019)\]]*\s+(?=\S)|[\u3002\uff1f\uff01][\u300d\u300f\u201d\u2019\uff09\"']*\s*(?=\S)")


# a period after these is not a sentence end ("e.g. a list", "Dr. Rao", "J. K."), so the line is not cut there
ABBREV = {"mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "e.g", "i.e", "cf", "approx", "fig", "eq"}


def _abbrev(text, end):
    word = re.search(r"(\S*)$", text[:end]).group(1).lstrip("\"'\u201c\u2018([")
    return word.lower() in ABBREV or (len(word) == 1 and word.isupper())


def sentences(text):
    out, at = [], 0
    for m in SENTENCE_END.finditer(text):
        if text[m.start()] == "." and _abbrev(text, m.start()):
            continue
        out.append(text[at:m.end()].strip())
        at = m.end()
    out.append(text[at:].strip())
    return [p for p in out if p]


def say_line(eng, text, pause):
    """Voice a line one sentence at a time with `pause` seconds between them. Engines run sentences together
    (Kokoro gives a full stop about 0.1 s), which made short numeric lines read at 220-250 wpm; a real pause
    between sentences is what a narrator does. pause <= 0 voices the line in one call, as before."""
    import numpy as np
    parts = sentences(text.strip()) if pause > 0 else [text]
    if len(parts) <= 1:
        return trim(eng.say(text))
    gap = np.zeros(int(pause * SR), dtype=np.float32)
    out = []
    for i, p in enumerate(parts):
        x = trim(eng.say(p))
        if i:
            out.append(gap)
        out.append(x)
    return np.concatenate(out)


def pick_engine(want, voice, speed, model_dir, allow_robotic, lang=None):
    order = ["kokoro", "edge-tts", "piper"] if want == "auto" else [want]
    if want == "auto" and voice_engine(voice) in order:  # an explicit voice is honoured: its engine goes first
        order.remove(voice_engine(voice))
        order.insert(0, voice_engine(voice))
    tried = []
    for name in order:
        if name == "espeak-ng" and not allow_robotic:
            sys.exit("espeak-ng is robotic. Use it only after kokoro, edge-tts and piper all failed, with --allow-robotic "
                     "and a recorded `vstate.py limit`.")
        mine = voice_engine(voice) in (name, None) and name == order[0]  # auto: only the first engine gets it
        v = voice if (voice and (want != "auto" or mine)) else DEFAULT_VOICE[name]
        try:
            eng = Kokoro(v, speed, model_dir, lang) if name == "kokoro" else ENGINES[name](v, speed)
            eng.voice_name = v
            if tried:
                log("fell back after:", *[f"\n  {t}" for t in tried])
            return eng, tried
        except SystemExit:
            raise
        except Exception as e:  # noqa: BLE001
            tried.append(f"{name}: {str(e).strip()[:240]}")
            log(f"engine {name} unavailable: {tried[-1]}")
    if allow_robotic and want == "auto":
        eng = Espeak(DEFAULT_VOICE["espeak-ng"], speed)
        eng.voice_name = DEFAULT_VOICE["espeak-ng"]
        return eng, tried
    msg = "\n  ".join(tried)
    sys.exit(f"No natural voice engine worked:\n  {msg}\n"
             "Fix what the errors say (network, pip, disk) and run again. If a step is truly blocked by the "
             "environment, record it: vstate.py limit \"<what>\" --kind voice --tried \"kokoro: ...\" --tried \"edge-tts: ...\"")


# ----------------------------------------------------------------------------- timing
def build_timing(script, durs, a):
    meta, lines = script["meta"], script["lines"]
    chapters = meta.get("chapters", [])
    t = float(meta.get("intro_lead", a.intro_lead))
    out, prev_ch = [], None
    # the seconds that place each line: a negative one would start a line while the one before is still speaking
    opts = ("intro_lead", "chapter_gap", "lead", "pad", "outro_tail")
    for where, src, keys in [("script meta", meta, opts), ("voice.py option", vars(a), opts)] + \
            [(f"line {ln.get('id')}", ln, ("lead", "pad", "think", "min")) for ln in lines]:
        for k in keys:
            v = src.get(k)
            if v is None or (v == "" and k in ("think", "min")):
                continue
            try:
                x = None if isinstance(v, bool) else float(v)
            except (TypeError, ValueError):
                x = None
            if x is None or not 0 <= x < float("inf"):
                sys.exit(f"{where}: {k} is {v!r}; it is seconds, a number of 0 or more")
    for ln in lines:
        ch = ln.get("chapter", 0)
        if prev_ch is not None and ch != prev_ch:
            t += float(meta.get("chapter_gap", a.chapter_gap))
        lead = float(ln.get("lead", meta.get("lead", a.lead)))
        if prev_ch is not None and ch != prev_ch and "lead" not in ln:
            # the first line of a chapter waits for the chapter card: the card plays from the chapter's start and the
            # next subject comes back as it leaves, so the voice starts once both are on screen, not under the card
            lead = max(lead, float(meta.get("chapter_lead", a.chapter_lead)))
        pad = float(ln.get("pad", meta.get("pad", a.pad)))
        think = float(ln.get("think", 0) or 0)
        vd = durs[ln["id"]]
        slot = max(lead + vd + pad + think, float(ln.get("min", 0) or 0))
        out.append({"id": ln["id"], "chapter": ch, "scene": ln.get("scene", f"ch{ch}"),
                    "start": round(t, 3), "voiceAt": round(t + lead, 3), "voiceDur": round(vd, 3),
                    "think": think, "end": round(t + slot, 3), "dur": round(slot, 3),
                    "cap": ln["cap"], "say": ln["say"], **({"tag": ln["tag"]} if "tag" in ln else {})})
        t += slot
        prev_ch = ch
    total = round(t + float(meta.get("outro_tail", a.outro_tail)), 3)
    if out:
        out[-1]["end"] = total
        out[-1]["dur"] = round(total - out[-1]["start"], 3)
    chs, scenes = [], []
    for ln in out:
        if not chs or chs[-1]["n"] != ln["chapter"]:
            name = chapters[ln["chapter"]] if ln["chapter"] < len(chapters) else f"Chapter {ln['chapter']}"
            chs.append({"n": ln["chapter"], "name": name, "start": ln["start"], "end": ln["end"]})
        chs[-1]["end"] = ln["end"]
        if not scenes or scenes[-1]["id"] != ln["scene"]:
            scenes.append({"id": ln["scene"], "chapter": ln["chapter"], "start": ln["start"], "end": ln["end"], "lines": []})
        scenes[-1]["end"] = ln["end"]
        scenes[-1]["lines"].append(ln["id"])
    return {"total": total, "fps": meta.get("fps", 30), "width": meta.get("width", 1920),
            "height": meta.get("height", 1080), "title": meta.get("title", ""), "chapters": chs,
            "scenes": scenes, "lines": out}


def write_if_changed(path, text):
    """Leave unchanged files alone so their timestamps keep meaning 'nothing changed' to the gates."""
    if os.path.exists(path) and open(path, encoding="utf-8").read() == text:
        return
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def emit(path, timing, h):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    body = json.dumps(timing, ensure_ascii=False, indent=1)
    ext = os.path.splitext(path)[1]
    stamp = f"timing-hash: {h} (generated by voice.py from script.json; do not edit)"
    if ext == ".json":
        txt = body
    elif ext == ".js":
        txt = f"// {stamp}\nwindow.TIMING = {body};\n"
    elif ext == ".ts":
        txt = f"// {stamp}\nexport const TIMING = {body};\nexport default TIMING;\n"
    elif ext == ".mjs":
        txt = f"// {stamp}\nexport const TIMING = {body};\nexport default TIMING;\n"
    elif ext == ".py":
        txt = f"# {stamp}\nimport json\nTIMING = json.loads({body!r})\n"  # repr: no caption text can end the literal
    else:
        sys.exit(f"--emit: unsupported extension {ext}")
    write_if_changed(path, txt)


ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")


def valid_id(i):
    """Line ids name files under voice/lines/, so they are restricted to one safe path segment."""
    return isinstance(i, str) and bool(ID_RE.match(i))


def same_request(key, request):
    """A cached clip is reusable when it was made for the same request (engine, voice, speed, lang as asked),
    even if the engine that actually served it was a fallback: the key records both."""
    if "request" in key:
        return key["request"] == request
    # keys written before the request was recorded: compare the effective settings. Those clips were voiced as one
    # call, with no pause between sentences, so they only stand in for a request with sentence_pause 0
    return (not request.get("sentence_pause") and key.get("voice") == (request["voice"] or key.get("voice")) and key.get("speed") == request["speed"]
            and (request["engine"] == "auto" or key.get("engine") == request["engine"])
            and key.get("lang") == request["lang"])


def made_with(k):
    """How a cached clip sounds: its engine and voice, speed, language, and the pause between its sentences (0 for a
    clip from before sentence pauses, voiced as one call)."""
    req = k.get("request") if isinstance(k.get("request"), dict) else {}
    got = (k.get("engine"), k.get("voice"), k.get("speed"), k.get("lang"), req.get("sentence_pause") or 0)
    return tuple(json.dumps(x) if isinstance(x, (list, dict)) else x for x in got)  # a hand-edited record still compares


def read_key(path):
    """A clip's cache record, or None when it is missing or unreadable (a run cut off while writing it): the line is
    then voiced again instead of the run stopping."""
    try:
        with open(path, encoding="utf-8") as f:
            k = json.load(f)
    except (OSError, ValueError):
        return None
    return k if isinstance(k, dict) and isinstance(k.get("engine"), str) and "voice" in k else None


def write_key(path, k):
    """Written whole or not at all: a temporary file renamed over the record."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(k, f)
    os.replace(tmp, path)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--engine", default="auto", choices=["auto", "kokoro", "edge-tts", "piper", "espeak-ng"])
    ap.add_argument("--voice", default=None, help="kokoro: af_heart, am_michael, bf_emma...; edge-tts: en-IN-NeerjaNeural...")
    ap.add_argument("--speed", type=float, default=None)
    ap.add_argument("--kokoro-dir", default=None)
    ap.add_argument("--lang", default=None, help="Kokoro language (en-us, en-gb, hi, es, fr-fr, it, pt-br, ja, cmn); default from the voice")
    ap.add_argument("--emit", action="append", default=[], help="extra timing file for the scene code (.json/.js/.ts/.mjs/.py)")
    ap.add_argument("--lead", type=float, default=0.25, help="silence before each line")
    ap.add_argument("--pad", type=float, default=0.35, help="breath after each line")
    ap.add_argument("--chapter-gap", type=float, default=0.8, help="extra pause between chapters")
    ap.add_argument("--chapter-lead", type=float, default=1.0,
                    help="silence before the first line of each chapter after the first (the card's time on screen)")
    ap.add_argument("--sentence-pause", type=float, default=None,
                    help="silence between the sentences of a line (voiced one at a time); default meta.sentence_pause or 0.3")
    ap.add_argument("--intro-lead", type=float, default=0.4)
    ap.add_argument("--outro-tail", type=float, default=1.2)
    ap.add_argument("--allow-robotic", action="store_true")
    ap.add_argument("--only-timing", action="store_true", help="re-time from cached clips without synthesizing")
    a = ap.parse_args()

    np = need("numpy", PINS["numpy"])
    sf = need("soundfile", PINS["soundfile"])  # installed here on a fresh machine, before anything else needs it

    root = os.path.abspath(a.project)
    spath = os.path.join(root, "script.json")
    script = json.load(open(spath, encoding="utf-8"))
    meta = script["meta"]
    voice = a.voice or meta.get("voice")
    speed = a.speed or float(meta.get("speed", 1.0))
    engine_name = a.engine if a.engine != "auto" else meta.get("engine", "auto")
    lang = a.lang or meta.get("lang")
    cache = os.path.join(root, "voice", "lines")
    os.makedirs(cache, exist_ok=True)
    if not script.get("lines"):
        sys.exit("script.json has no lines to voice")
    bad = [ln.get("id") for ln in script["lines"] if not valid_id(ln.get("id"))]
    if bad:
        sys.exit(f"script.json: line ids must match {ID_RE.pattern} (they name files under voice/lines/): {bad!r}")
    # two lines with one id would share a clip, so one would speak the other's words; ids differing only in case
    # share it too where the disk ignores case (macOS, Windows)
    seen, twice = set(), []
    for ln in script["lines"]:
        k = ln["id"].lower()
        if k in seen:
            twice.append(ln["id"])
        seen.add(k)
    if twice:
        sys.exit(f"script.json: line ids must be unique (ignoring case, as they name files under voice/lines/): {twice!r}")
    pause = a.sentence_pause if a.sentence_pause is not None else float(meta.get("sentence_pause", 0.3))
    request = {"engine": engine_name, "voice": voice, "speed": speed, "lang": lang, "sentence_pause": pause}

    eng, tried = (None, [])
    durs, clips, made = {}, {}, {}
    for ln in script["lines"]:
        p = os.path.join(cache, f"{ln['id']}.wav")
        keyf = p + ".key"
        robotic_ok = True
        k = read_key(keyf) if os.path.exists(p) else None
        if k is not None:
            robotic_ok = a.allow_robotic or k.get("engine") not in ROBOTIC  # a natural run re-voices robotic clips
            if k.get("say") == ln["say"] and robotic_ok and (a.only_timing or same_request(k, request)):
                x, _ = sf.read(p, dtype="float32")
                clips[ln["id"]], durs[ln["id"]] = x, len(x) / SR
                engine_used, voice_used, speed_used = k["engine"], k["voice"], k.get("speed", speed)
                made.setdefault(made_with(k), []).append(ln["id"])
                continue
        if a.only_timing:
            sys.exit(f"--only-timing: no usable cached clip for {ln['id']}"
                     + ("" if robotic_ok else " (it is robotic: pass --allow-robotic or re-voice it)"))
        if eng is None:
            eng, tried = pick_engine(engine_name, voice, speed, a.kokoro_dir, a.allow_robotic, lang)
            log(f"voice: {eng.name} {eng.voice_name} speed {speed}")
        x = say_line(eng, ln["say"], pause)
        if os.path.lexists(keyf):  # the old record goes first, so a clip cut off mid-write is never paired with it
            os.remove(keyf)
        sf.write(p, x, SR)
        write_key(keyf, {"engine": eng.name, "voice": eng.voice_name, "speed": speed, "lang": lang, "say": ln["say"],
                         "request": request})
        clips[ln["id"]], durs[ln["id"]] = x, len(x) / SR
        engine_used, voice_used, speed_used = eng.name, eng.voice_name, speed
        log(f"  {ln['id']:<14} {durs[ln['id']]:6.2f}s  {ln['say'][:60]}")

    # --only-timing takes whatever is cached, so clips left by an interrupted change of voice, speed or pause would
    # make a narration that changes voice or pace between lines (the voice gate compares only engines)
    if a.only_timing and len(made) > 1:
        sys.exit("--only-timing: the cached clips were not all voiced alike, so the narration would change voice or pace "
                 "between lines; run voice.py without --only-timing to voice them again as one. "
                 + "; ".join(f"{', '.join(ids[:3])}{' ...' if len(ids) > 3 else ''}: {e} {v}, speed {sp}, lang {lg}, "
                             f"sentence pause {pa}" for (e, v, sp, lg, pa), ids in made.items()))
    engines = sorted({read_key(os.path.join(cache, f"{ln['id']}.wav.key"))["engine"] for ln in script["lines"]})
    if len(engines) > 1:
        log(f"warning: clips come from more than one engine {engines}; the voice gate fails until one engine voices "
            "every line (delete voice/lines and run again)")

    timing = build_timing(script, durs, a)
    timing["engine"] = engine_used if len(engines) == 1 else "mixed: " + ", ".join(engines)
    timing["voice"], timing["speed"] = voice_used, speed_used   # the clips' own speed (--only-timing keeps theirs)
    timing["script_hash"] = hashlib.sha256(open(spath, "rb").read()).hexdigest()[:16]
    # the hash covers what the film is made of. Fallbacks only say how a run reached its engine (a run served from
    # the cache has none), so the hash always counts them as empty: a no-op re-run keeps the hash and the render,
    # and a timing made without fallbacks keeps the hash it had before this rule
    h = hashlib.sha256(json.dumps(dict(timing, fallbacks=[]), sort_keys=True).encode()).hexdigest()[:16]
    timing["engines"] = engines
    tpath = os.path.join(root, "timing.json")
    old = json.load(open(tpath, encoding="utf-8")) if os.path.exists(tpath) else {}
    timing["fallbacks"] = tried if eng is not None else old.get("fallbacks", [])
    head = {k: timing.pop(k) for k in ("script_hash", "engine", "engines", "voice", "speed", "fallbacks")}
    timing = {"hash": h, **head, **timing}

    track = np.zeros(int((timing["total"] + 0.5) * SR), dtype=np.float32)
    for ln in timing["lines"]:
        x = clips[ln["id"]]
        i = int(ln["voiceAt"] * SR)
        track[i:i + len(x)] += x[: len(track) - i]
    peak = float(np.abs(track).max() or 1)
    track *= min(1.0, 0.89 / peak)
    # written when its samples differ, not only when the timing does: clips re-made with the same lengths (a cleared
    # cache, a re-recorded line) change the voice without the hash; an identical track keeps the file and its time
    nar = os.path.join(root, "voice", "narration.wav")
    new = nar + ".new.wav"
    sf.write(new, track[: int(timing["total"] * SR)], SR)
    if os.path.exists(nar) and sha256_of(new) == sha256_of(nar):
        os.remove(new)
    else:
        os.replace(new, nar)

    write_if_changed(os.path.join(root, "timing.json"), json.dumps(timing, ensure_ascii=False, indent=1))
    chapters = meta.get("chapters", [])
    tl = [{"id": ln["id"], "start": ln["voiceAt"], "dur": round(ln["end"] - ln["voiceAt"], 3),
           "chapter": chapters[ln["chapter"]] if ln["chapter"] < len(chapters) else ln["chapter"],
           "text": ln["cap"], "say": ln["say"], "pause": pause} for ln in timing["lines"]]
    write_if_changed(os.path.join(root, "timeline.json"), json.dumps(tl, ensure_ascii=False, indent=1))
    for e in a.emit:
        emit(os.path.join(root, e) if not os.path.isabs(e) else e, timing, h)

    log(f"\n{len(timing['lines'])} lines, total {timing['total']:.1f}s ({timing['total'] / 60:.2f} min), "
        f"engine {engine_used} {voice_used}, hash {h}")
    for c in timing["chapters"]:
        log(f"  ch{c['n']} {c['name']:<22} {c['start']:7.2f} -> {c['end']:7.2f}")


if __name__ == "__main__":
    main()
