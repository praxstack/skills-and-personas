"""Narration TTS (AC-5.2): every segment in one kokoro-onnx process, with lexicon respellings.

Fallback order when Kokoro is unavailable: `hyperframes tts` (pinned), then macOS `say`.
Any fallback marks the build `degraded`. Segments are cached by the full effective input
(text, engine, engine version, model and voices sha256, voice, speed, language, lexicon version), D17.9.
"""
import hashlib
import json
import platform
import re
import shutil
from pathlib import Path

from . import errors, host, node, text

LEXICON = host.PKG / "lexicon" / "c.json"
VOICE = "af_heart"
SPEED = 0.75  # B5 (AC-10.5): measured from the film audio, 0.9 ran up to 221 wpm on short lines. 0.7 is slower still, but whisper then misheard code tokens and lost cue sync, and the IVE question drive ran past its window; 0.75 with the tightest short lines reworded keeps every line under 170
SAY_VOICE = "Samantha"


def lexicon():
    return json.loads(LEXICON.read_text())


def apply_lexicon(text, lex=None):
    """The spoken form of a written narration line: token respellings, then the regex `patterns` in order
    (factorial(3) -> factorial of 3, 66.000000 -> 66 followed by a point and six zeros). The voice only
    ever reads this, so captions (the written form) and audio cannot drift in meaning (round 18)."""
    lex = lex or lexicon()
    out = text
    for e in lex["entries"]:
        out = re.sub(r"(?<![\w\\])" + re.escape(e["token"]) + r"(?![\w])", lambda m, s=e["spoken"]: s, out)
    for e in lex.get("patterns", []):
        out = re.sub(e["pattern"], e["spoken"], out)
    return re.sub(r"\s+", " ", out).strip()


def code_tokens(said, lex=None):
    """Lexicon code tokens in a narration line (before respelling), with the forms whisper may
    write for a correct reading: [{"token", "count", "heard": [[word, ...], ...]}]."""
    lex = lex or lexicon()
    out = []
    for e in lex["entries"]:
        n = len(re.findall(r"(?<![\w\\])" + re.escape(e["token"]) + r"(?![\w])", said))
        if n and e.get("code"):
            heard = [text.norm_words(h) for h in e.get("heard") or [e["spoken"]]]
            out.append({"token": e["token"], "count": n, "heard": heard})
    return out


def code_words(lex=None):
    """Spoken words of code tokens; excluded from the non-code WER."""
    lex = lex or lexicon()
    words = set()
    for e in lex["entries"]:
        if e.get("code"):
            words |= set(re.findall(r"[a-z0-9']+", e["spoken"].lower().replace("-", " ")))
            words |= set(re.findall(r"[a-z0-9']+", e["token"].lower()))
    return words


def _kokoro_paths():
    st = host.state_dir()
    py = st / "venvs" / "kokoro" / "bin" / "python"
    model = st / "models" / "kokoro" / "kokoro-v1.0.onnx"
    voices = st / "models" / "kokoro" / "voices-v1.0.bin"
    return py, model, voices


def kokoro_available():
    return all(p.exists() for p in _kokoro_paths())


def _file_sha(path, _memo={}):
    """sha256 of a model file, memoised on (path, size, mtime) so a 300 MB model is hashed once."""
    st = Path(path).stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _memo:
        _memo[key] = host.sha256_file(path)
    return _memo[key]


def kokoro_version():
    """kokoro-onnx version from the venv's dist-info (no subprocess)."""
    py = _kokoro_paths()[0]
    for d in sorted(py.parent.parent.glob("lib/python*/site-packages/kokoro_onnx-*.dist-info")):
        return d.name[len("kokoro_onnx-"):-len(".dist-info")]
    return "unknown"


LANG = "en-us"


def engine_inputs(engine):
    """Everything besides the text that changes the audio an engine makes (D17.9).
    The model and voice files are identified by sha256, not by path."""
    if engine == "kokoro":
        _py, model, voices = _kokoro_paths()
        return {"engine": "kokoro-onnx", "engine_version": kokoro_version(), "model_sha256": _file_sha(model),
                "voices_sha256": _file_sha(voices), "voice": VOICE, "speed": SPEED, "lang": LANG}
    if engine == "hyperframes-tts":
        return {"engine": "hyperframes-tts", "engine_version": node.hyperframes_version(), "model_sha256": None,
                "voices_sha256": None, "voice": VOICE, "speed": SPEED, "lang": LANG}
    return {"engine": "say", "engine_version": "macOS " + (platform.mac_ver()[0] or "unknown"),
            "model_sha256": None, "voices_sha256": None, "voice": SAY_VOICE, "speed": 1.0, "lang": LANG}


def cache_key(text, inputs, lexicon_version):
    """The cache key is the full effective input: text, engine, engine version, model and voices
    sha256, voice, speed, language and lexicon version. Changing any of them misses the cache."""
    raw = json.dumps({"text": text, "lexicon_version": lexicon_version, **inputs}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def synthesize(segments, out_dir, force_engine=None):
    """segments: [{"id", "spoken"}]. Returns {"engine", "degraded", "segments": [{"id","wav"}], ...}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = host.state_path("cache", "tts")
    cache.mkdir(parents=True, exist_ok=True)
    for s in segments:
        if not s["spoken"].strip():
            raise errors.NarrationEmpty(f"segment {s['id']} has no text", segment=s["id"])
    engine = force_engine or ("kokoro" if kokoro_available() else "hyperframes-tts")
    if engine == "hyperframes-tts" and not _hyperframes_tts_available():
        engine = "say"
    inputs = engine_inputs(engine)
    lex_v = lexicon()["version"]
    keyed = [{**s, "wav": cache / f"{engine}-{cache_key(s['spoken'], inputs, lex_v)}.wav"} for s in segments]
    todo = [s for s in keyed if not s["wav"].exists()]
    run = {"kokoro": _kokoro, "hyperframes-tts": _hyperframes, "say": _say}[engine]
    loads = run(todo, out_dir, inputs) if todo else 0
    return {"engine": {"kokoro": f"kokoro-onnx {inputs['engine_version']} (Kokoro-82M v1.0)",
                       "hyperframes-tts": "hyperframes tts (fallback)", "say": "macOS say (fallback)"}[engine],
            "voice": inputs["voice"], "speed": inputs["speed"], "degraded": engine != "kokoro",
            "cache_inputs": {**inputs, "lexicon_version": lex_v},
            "process_count": (1 if todo else 0) if engine == "kokoro" else len(todo), "model_loads": loads,
            "synthesised_now": len(todo), "cached": len(segments) - len(todo),
            "segments": [{"id": s["id"], "wav": s["wav"]} for s in keyed]}


def _hyperframes_tts_available():
    return (host.state_path("tools", "node", "node_modules", ".bin", "hyperframes").exists()
            and _kokoro_paths()[0].exists())


def _kokoro(todo, out_dir, inputs):
    """Every uncached segment in ONE kokoro-onnx process (E11). Returns the model load count."""
    py, model, voices = _kokoro_paths()
    job = out_dir / "kokoro-job.json"
    job.write_text(json.dumps({"model": str(model), "voices": str(voices), "voice": inputs["voice"],
                               "speed": inputs["speed"], "lang": inputs["lang"],
                               "segments": [{"id": s["id"], "text": s["spoken"], "out": str(s["wav"])} for s in todo]}))
    res = host.run([py, host.PKG / "ptk" / "tts_kokoro.py", job], timeout=1800, check=True)
    return json.loads(res.stdout.strip().splitlines()[-1])["loads"]


def _hyperframes(todo, out_dir, inputs):
    """Fallback 1: the pinned `hyperframes tts`, with the Kokoro venv as its Python (EXTERNAL-INPUTS)."""
    env = node.env(extra={"HYPERFRAMES_PYTHON": str(_kokoro_paths()[0])})
    for s in todo:
        host.run([node.bin_path("hyperframes"), "tts", s["spoken"], "-v", inputs["voice"], "-s", str(inputs["speed"]),
                  "-o", s["wav"]], cwd=out_dir, env=env, timeout=600, check=True)
    return 0


def _say(todo, out_dir, inputs):
    """Fallback 2: macOS `say`."""
    say = host.which("say", required=False)
    if not say:
        raise errors.TTSUnavailable("no TTS engine: Kokoro, hyperframes tts and say are all unavailable")
    for s in todo:
        host.run([say, "-v", inputs["voice"], "--file-format=WAVE", "--data-format=LEI16@24000", "-o", s["wav"],
                  s["spoken"]], check=True, timeout=120)
    return 0


def trim_and_measure(seg_wavs, out_dir, rate=48000):
    """Trim leading/trailing silence, resample to 48 kHz mono, measure each duration (E17)."""
    ffmpeg = host.which("ffmpeg")
    out = []
    trim = ("silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.02,areverse,"
            "silenceremove=start_periods=1:start_threshold=-50dB:start_silence=0.05,areverse")
    for s in seg_wavs:
        dst = out_dir / f"{s['id']}.wav"
        host.run([ffmpeg, "-v", "error", "-y", "-i", s["wav"], "-af", trim, "-ar", str(rate), "-ac", "1",
                  "-c:a", "pcm_s16le", dst], check=True, timeout=120)
        out.append({"id": s["id"], "wav": dst, "seconds": probe_duration(dst)})
    return out


def probe_duration(path):
    ffprobe = host.which("ffprobe")
    res = host.run([ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                   check=True, timeout=60)
    return round(float(res.stdout.strip()), 3)


def clear_cache():
    shutil.rmtree(host.state_path("cache", "tts"), ignore_errors=True)
