"""Narration TTS (AC-5.2): every segment in one kokoro-onnx process, with lexicon respellings.

Fallback order when Kokoro is unavailable: `hyperframes tts` (pinned), then macOS `say`.
Any fallback marks the build `degraded`. Segments are cached by the full effective input
(engine, model sha256, voice, speed, lexicon version, text), D17.9.
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

from . import errors, host, node

LEXICON = host.PKG / "lexicon" / "c.json"
VOICE = "af_heart"
SPEED = 1.0


def lexicon():
    return json.loads(LEXICON.read_text())


def apply_lexicon(text, lex=None):
    lex = lex or lexicon()
    out = text
    for e in lex["entries"]:
        out = re.sub(r"(?<![\w\\])" + re.escape(e["token"]) + r"(?![\w])", e["spoken"], out)
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


def _key(engine, text, model_sha):
    raw = json.dumps([engine, model_sha, VOICE, SPEED, lexicon()["version"], text])
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def synthesize(segments, out_dir, force_engine=None):
    """segments: [{"id", "spoken"}]. Returns {"engine", "degraded", "segments": [{"id","wav","raw_seconds"}]}."""
    out_dir.mkdir(parents=True, exist_ok=True)
    cache = host.state_path("cache", "tts")
    cache.mkdir(parents=True, exist_ok=True)
    engine = force_engine or ("kokoro" if kokoro_available() else "hyperframes-tts")
    if engine == "kokoro":
        return _kokoro(segments, out_dir, cache)
    if engine == "hyperframes-tts":
        if not (host.state_path("tools", "node", "node_modules", ".bin", "hyperframes").exists()
                and host.state_path("venvs", "kokoro", "bin", "python").exists()):
            engine = "say"
        else:
            return _hyperframes(segments, out_dir, cache)
    return _say(segments, out_dir, cache)


def _kokoro(segments, out_dir, cache):
    py, model, voices = _kokoro_paths()
    msha = host.sha256_file(model)[:16]
    todo, result = [], []
    for s in segments:
        if not s["spoken"].strip():
            raise errors.NarrationEmpty(f"segment {s['id']} has no text", segment=s["id"])
        wav = cache / f"kokoro-{_key('kokoro', s['spoken'], msha)}.wav"
        result.append({"id": s["id"], "wav": wav})
        if not wav.exists():
            todo.append({"id": s["id"], "text": s["spoken"], "out": str(wav)})
    loads = 0
    if todo:
        job = out_dir / "kokoro-job.json"
        job.write_text(json.dumps({"model": str(model), "voices": str(voices), "voice": VOICE, "speed": SPEED,
                                   "lang": "en-us", "segments": todo}))
        res = host.run([py, host.PKG / "ptk" / "tts_kokoro.py", job], timeout=1800, check=True)
        loads = json.loads(res.stdout.strip().splitlines()[-1])["loads"]
    return {"engine": "kokoro-onnx 0.6.1 (Kokoro-82M v1.0)", "voice": VOICE, "speed": SPEED, "degraded": False,
            "process_count": 1 if todo else 0, "model_loads": loads, "synthesised_now": len(todo),
            "cached": len(segments) - len(todo), "segments": result}


def _hyperframes(segments, out_dir, cache):
    result = []
    for s in segments:
        wav = cache / f"hftts-{_key('hftts', s['spoken'], 'hf')}.wav"
        if not wav.exists():
            node.hyperframes(["tts", s["spoken"], "-v", VOICE, "-s", str(SPEED), "-o", str(wav)], cwd=out_dir,
                             timeout=600)
        result.append({"id": s["id"], "wav": wav})
    return {"engine": "hyperframes tts (fallback)", "voice": VOICE, "speed": SPEED, "degraded": True,
            "segments": result}


def _say(segments, out_dir, cache):
    say = host.which("say", required=False)
    if not say:
        raise errors.TTSUnavailable("no TTS engine: Kokoro, hyperframes tts and say are all unavailable")
    result = []
    for s in segments:
        wav = cache / f"say-{_key('say', s['spoken'], 'say')}.wav"
        if not wav.exists():
            host.run([say, "-v", "Samantha", "--file-format=WAVE", "--data-format=LEI16@24000", "-o", wav,
                      s["spoken"]], check=True, timeout=120)
        result.append({"id": s["id"], "wav": wav})
    return {"engine": "macOS say (fallback)", "voice": "Samantha", "speed": 1.0, "degraded": True, "segments": result}


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
