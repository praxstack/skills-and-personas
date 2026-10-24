#!/usr/bin/env python3
"""Turn a built explorable into a narrated video with a natural voice.

  python3 narrate.py lesson.html -o lesson.mp4 [--engine auto|kokoro|chatterbox] [--voice af_heart] [--speed 0.95] [--board paper|chalk] [--fps 24]

1. Reads the lesson's film scenes (what each step says).
2. Voices every scene with a natural neural voice, never the browser's robotic
   speechSynthesis. --engine auto (the default) picks Chatterbox (MIT, more
   expressive, with emotion control; it beat ElevenLabs in its maker's blind
   test) when it's installed and a GPU is there, and Kokoro-82M otherwise
   (Apache, ranked above Chatterbox on public human-preference arenas, and
   faster than real time on a CPU).
   Chatterbox on a CPU is about 40 times slower than real time, so it's never
   picked automatically there. Sentences are voiced one at a time with a short
   pause, at a teaching pace.
3. Times each scene to its voice, then renders every frame in Chromium: the
   figure eases to the scene's settings and the coach's marks draw in one
   after another.
4. Mixes the voice over a faint room tone (so pauses never drop to digital
   silence), normalises to -16 LUFS, and writes the MP4 with WebVTT captions
   beside it. No pen sound unless you pass --pen: it is placed by an estimate
   of when strokes draw, not by the strokes themselves, and a listener found it
   distracting and out of sync. --remux keeps an existing video's picture and
   remakes only its sound (minutes instead of a full render).
5. Runs visual-qa's check_video.py on the result, and check_speech.py (does
   the voice say what the captions say?) when faster-whisper is installed.

Needs: kokoro-onnx, soundfile and numpy in the Python running this script
(pip install kokoro-onnx==0.6.1 soundfile==0.14.0), the Kokoro model files
(downloaded only with TEACHER_ALLOW_NETWORK=1 and SHA-256 checked into ~/.cache/kokoro; KOKORO_DIR
moves them), Node with Playwright, and ffmpeg. Spoken clips are cached in
~/.cache/kai-mori-voice; NARRATE_CACHE moves the cache. The bundled explainer-video skill documents the full
voice ladder (Kokoro, then edge-tts, then Piper) if Kokoro can't run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import soundfile as sf

HERE = Path(__file__).resolve().parent
QA = HERE.parent.parent / "visual-qa" / "scripts"
SOUNDS = HERE.parent.parent / "lesson-notebook" / "assets" / "sounds"
PEN_FILES = {"chalk": ["chalk-1.mp3", "chalk-2.mp3"], "paper": ["pencil.mp3"]}
PEN_UNDER_VOICE_DB = {"chalk": -15.0, "paper": -17.0}  # pen loudness against the voice, while it draws
ROOM_TONE_DB = -42.0  # the room's hush against the voice
SR = 24000
KOKORO_DIR = Path(os.environ.get("KOKORO_DIR", Path.home() / ".cache" / "kokoro"))
KOKORO_FILES = {
    "kokoro-v1.0.onnx": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
                         "7d5df8ecf7d4b1878015a32686053fd0eebe2bc377234608764cc0ef3636a6c5"),
    "voices-v1.0.bin": ("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
                        "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d"),
}
CACHE = Path(os.environ.get("NARRATE_CACHE", Path.home() / ".cache" / "kai-mori-voice"))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def kokoro():
    from kokoro_onnx import Kokoro

    KOKORO_DIR.mkdir(parents=True, exist_ok=True)
    for name, (url, digest) in KOKORO_FILES.items():
        path = KOKORO_DIR / name
        if not path.exists() or sha256(path) != digest:
            if os.environ.get("TEACHER_ALLOW_NETWORK") != "1":
                raise RuntimeError(f"Missing or invalid Kokoro model {path}. Install verified assets separately, "
                                   "or explicitly opt in to downloading with TEACHER_ALLOW_NETWORK=1.")
            print(f"downloading {name}…")
            urllib.request.urlretrieve(url, path)
            if sha256(path) != digest:
                raise SystemExit(f"{name}: checksum mismatch, refusing to use it")
    return Kokoro(str(KOKORO_DIR / "kokoro-v1.0.onnx"), str(KOKORO_DIR / "voices-v1.0.bin"))


def speakable(text: str) -> str:
    """Read symbols the way a teacher would say them."""
    t = text
    t = re.sub(r"∂(\w+)\s*/\s*∂([\w₀-₉]+)", r" the slope of \1 with respect to \2 ", t)  # ∂L/∂w
    t = re.sub(r"\|(\w)\|", r" the length of \1 ", t)  # |a|
    t = re.sub(r"\^\(([^)]*)\)", r" to the power \1, ", t)  # e^(z + 3)
    t = re.sub(r"\^(\w+)", r" to the \1 ", t)  # e^z
    t = re.sub(r"\bln\b", "the natural log of", t)  # ln p
    t = re.sub(r"(?<=\d)/(?=\d)", " over ", t)  # 1/3
    t = re.sub(r"\s=\s", " equals ", t)
    t = t.replace("³", " cubed")
    for a, b in [("×", " times "), ("≤", " at most "), ("≥", " at least "), ("−", " minus "), ("→", " to "), ("²", " squared"),
                 ("°", " degrees"), ("%", " percent"), ("&", " and "), ("a[", "a of "), ("[", " "), ("]", " "),
                 ("·", " dot "), ("÷", " divided by "), ("≈", " is about "), ("√", " square root of "), ("∞", "infinity"),
                 ("∂", " partial "), ("θ", " theta "), ("Σ", " the sum of "), ("∑", " the sum of "), ("λ", " lambda "), ("σ", " sigma "),
                 ("′′", " double prime "), ("′", " prime "), ("₀", "0"), ("₁", "1"), ("₂", "2"), ("₃", "3"), ("⁻¹", " inverse"), ("−", " minus "), ("ŷ", "y hat"), ("î", "i hat"), ("ĵ", "j hat"),
                 ("XOR", "ex-or"), ("xor", "ex-or"), ("O(log n)", "O of log n"), ("O(n)", "O of n"), ("O(1)", "O of 1"), ("log2(", "log base 2 of ("), ("log2", "log base 2")]:
        t = t.replace(a, b)
    t = re.sub(r"(?<=[\w)])\s*\.\.(?=\s*[\w(])(?!\.)", " to ", t)  # ranges: 2..5, l..r (an ellipsis stays an ellipsis)
    t = re.sub(r"\s*\+\s*…\s*\+\s*|\s*\+\s*\.\.\.\s*\+\s*", " plus and so on, plus ", t)
    t = t.replace("+", " plus ")
    return re.sub(r"\s+", " ", t).strip()


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])", text.strip())
    return [p for p in parts if p.strip()]


def trim(x: np.ndarray, thr: float = 0.004) -> np.ndarray:
    idx = np.where(np.abs(x) > thr)[0]
    return x[max(0, idx[0] - 240): idx[-1] + 480] if len(idx) else x


def chatterbox():
    # Configure Hugging Face before Chatterbox imports it. The constants update
    # also covers a host that imported huggingface_hub earlier in this process.
    # This is the HF cache policy, not a general network sandbox.
    if os.environ.get("TEACHER_ALLOW_NETWORK") != "1":
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from huggingface_hub import constants
        constants.HF_HUB_OFFLINE = True
        loaded = sys.modules.get("transformers.utils.hub")
        if loaded is not None:
            loaded._is_offline_mode = True
    import torch
    from chatterbox.tts import ChatterboxTTS

    try:
        return ChatterboxTTS.from_pretrained(device="cuda" if torch.cuda.is_available() else "cpu")
    except Exception as exc:
        if os.environ.get("TEACHER_ALLOW_NETWORK") != "1":
            raise RuntimeError("Chatterbox could not load from its local Hugging Face cache. "
                               "Prepare the models separately or explicitly opt in with "
                               "TEACHER_ALLOW_NETWORK=1. " + str(exc)) from exc
        raise


def has_gpu_chatterbox() -> bool:
    try:
        import importlib.util

        if importlib.util.find_spec("chatterbox") is None:
            return False
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


KOKORO_SPEED = 0.95  # Kokoro's teaching pace when --speed isn't given


def make_voice(engine: str, voice: str, speed: float | None):
    """Return (name, speak) where speak(sentence) gives float32 audio at SR.
    speed is None when --speed wasn't given: Kokoro then uses KOKORO_SPEED."""
    # Chatterbox has no speed control, so only an explicit speed other than
    # 1.0 rules it out (for auto too); without --speed it's free to pick.
    fixed = speed is None or speed == 1.0
    if engine == "auto":
        engine = "chatterbox" if fixed and has_gpu_chatterbox() else "kokoro"
    if engine == "chatterbox" and not fixed:
        raise SystemExit("chatterbox can't change speed; drop --speed or use --engine kokoro")
    if engine == "chatterbox":
        model = chatterbox()

        def speak(sentence: str) -> np.ndarray:
            wav = model.generate(sentence).squeeze(0).cpu().numpy().astype(np.float32)
            if model.sr != SR:
                wav = np.interp(np.arange(0, len(wav), model.sr / SR), np.arange(len(wav)), wav).astype(np.float32)
            return wav

        return "chatterbox", speak
    if speed is None:
        speed = KOKORO_SPEED
    tts = kokoro()

    def speak(sentence: str) -> np.ndarray:
        audio, sr = tts.create(sentence, voice=voice, speed=speed, lang="en-gb" if voice.startswith("b") else "en-us")
        if sr != SR:
            raise SystemExit(f"unexpected sample rate {sr}")
        return np.asarray(audio, dtype=np.float32)

    return f"kokoro|{voice}|{speed}", speak


def voice_scene(engine: tuple, text: str, pause: float) -> np.ndarray:
    name, speak = engine
    said = speakable(text)
    # Key on what the voice is told to say, so improving speakable() re-voices
    # the scenes it changes instead of reusing stale audio.
    key = hashlib.sha1(f"{name}|{pause}|{said}".encode()).hexdigest()[:20]
    CACHE.mkdir(parents=True, exist_ok=True)
    cached = CACHE / f"{key}.wav"
    if cached.exists():
        return sf.read(cached, dtype="float32")[0]
    chunks = []
    for s in sentences(said):
        chunks += [trim(speak(s)), np.zeros(int(pause * SR), dtype=np.float32)]
    out = np.concatenate(chunks[:-1]) if chunks else np.zeros(SR, dtype=np.float32)
    sf.write(cached, out, SR)
    return out


def band_noise(n: int, f0: float, width: float, rng) -> np.ndarray:
    """Noise band-passed around f0 (FFT filter; no scipy needed)."""
    noise = rng.standard_normal(n).astype(np.float32)
    spec = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(n, 1 / SR)
    spec *= np.exp(-0.5 * ((freqs - f0) / width) ** 2)
    out = np.fft.irfft(spec, n).astype(np.float32)
    return out / (np.max(np.abs(out)) + 1e-9)


def friction(dur: float, chalk: bool, rng) -> np.ndarray:
    """The fallback pen: soft broadband hiss with sparse clicks that pulse about
    every 20 ms, matching what the recordings measure (see sounds/SOUNDS.md)."""
    n = max(int(dur * SR), 400)
    hiss = band_noise(n, rng.uniform(4200, 5600) if chalk else rng.uniform(5200, 7000), 1800 if chalk else 3200, rng)
    clicks = (rng.random(n) < 0.012) * rng.uniform(-1, 1, n) * 1.6
    x = 0.45 * hiss + clicks.astype(np.float32)
    pulse = np.repeat(rng.uniform(0.6, 1.0, n // int(0.02 * SR) + 1), int(0.02 * SR))[:n]
    if chalk:
        pulse *= np.where(rng.random(len(pulse)) < 0.004, 0.35, 1.0)
    env = np.ones(n, dtype=np.float32)
    a = min(int(0.02 * SR), n // 4)
    env[:a] = np.linspace(0, 1, a)
    env[-a:] = np.linspace(1, 0, a)
    return (x * pulse * env).astype(np.float32)


def load_pen(kind: str) -> list[tuple[np.ndarray, np.ndarray]]:
    """Decode the recordings for a board, with the offsets where each is loudest."""
    bank = []
    for name in PEN_FILES[kind]:
        path = SOUNDS / name
        if not path.exists() or not shutil.which("ffmpeg"):
            continue
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
        x = np.frombuffer(raw, dtype=np.float32).copy()
        hop = int(0.01 * SR)
        rms = np.sqrt(np.mean(x[: len(x) // hop * hop].reshape(-1, hop) ** 2, axis=1))
        starts = np.nonzero(rms > 0.3 * rms.max())[0] * hop
        starts = starts[starts < len(x) - int(GRAIN * SR * 1.2)]
        if len(starts):
            bank.append((x, starts))
    return bank


GRAIN = 0.085  # seconds; grains overlap by about half, as in sound.js


def grains(dur: float, bank, rng) -> np.ndarray:
    """One stroke from the recordings: short grains from where they're loudest,
    each at a different level, faded in and out as a stroke."""
    n = max(int(dur * SR), 400)
    g = int(GRAIN * SR)
    out = np.zeros(n + g, dtype=np.float32)
    a = int(g * 0.3)
    win = np.concatenate([np.linspace(0, 1, a, dtype=np.float32), np.linspace(1, 0, g - a, dtype=np.float32)])
    t = 0
    while t < n:
        x, starts = bank[rng.integers(len(bank))]
        # Whole-sample slices, sometimes reversed: resampling would act as a
        # low-pass at 24 kHz and dull the grit, which lives up near 8 kHz.
        grain = x[int(rng.choice(starts)):][:g]
        if rng.random() < 0.5:
            grain = grain[::-1]
        edge = min(1.0, t / (0.025 * SR) + 0.15, (n - t) / (0.15 * n) + 0.1)
        out[t: t + g] += grain * win * edge * rng.uniform(0.65, 1.0)
        t += int(g * rng.uniform(0.4, 0.6))
    return out[:n]


def tap(rng) -> np.ndarray:
    """The click of chalk landing on the board."""
    m = int(0.05 * SR)
    return band_noise(m, 4500, 2500, rng) * np.exp(-np.linspace(0, 9, m)).astype(np.float32)


def scratch(dur: float, chalk: bool, rng, bank=None) -> np.ndarray:
    x = grains(dur, bank, rng) if bank else friction(dur, chalk, rng)
    if chalk:
        t = tap(rng)
        x[: len(t)] += 1.2 * np.max(np.abs(x)) * t[: len(x)]
    return x


def room_tone(n: int, rng) -> np.ndarray:
    """A quiet room: pink-ish noise rolled off above 6 kHz, so a pause sounds
    like a pause in a real room rather than a dropout."""
    spec = np.fft.rfft(rng.standard_normal(n).astype(np.float32))
    f = np.fft.rfftfreq(n, 1 / SR)
    spec *= 1 / np.sqrt(np.maximum(f, 40.0)) * np.exp(-((f / 6000) ** 2))
    x = np.fft.irfft(spec, n).astype(np.float32)
    return x / (np.sqrt(np.mean(x**2)) + 1e-9)


def db(x: float) -> float:
    return 10 ** (x / 20)


def active_rms(x: np.ndarray) -> float:
    """RMS over the parts that actually make sound (ignoring silence)."""
    hop = int(0.05 * SR)
    r = np.sqrt(np.mean(x[: len(x) // hop * hop].reshape(-1, hop) ** 2, axis=1))
    on = r[r > 0.1 * (r.max() + 1e-12)]
    return float(np.sqrt(np.mean(on**2))) if len(on) else 0.0


def run(cmd: list[str]) -> str:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"failed: {' '.join(cmd[:3])}…\n{r.stdout[-2000:]}\n{r.stderr[-3000:]}")
    return r.stdout


def cue_text(text: str) -> str:
    """WebVTT cue text is markup: a bare < starts a tag and swallows the rest
    of the line ("det < 0" showed as "det "), so escape &, < and >."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def vtt(timing: dict, texts: list[str]) -> str:
    def stamp(s: float) -> str:
        ms = int(round(s * 1000))
        return f"{ms // 3600000:02d}:{ms % 3600000 // 60000:02d}:{ms % 60000 // 1000:02d}.{ms % 1000:03d}"
    cues = [f"{i + 1}\n{stamp(sc['voiceAt'])} --> {stamp(sc['start'] + sc['dur'])}\n{cue_text(texts[i])}\n" for i, sc in enumerate(timing["scenes"])]
    return "WEBVTT\n\n" + "\n".join(cues)


def video_length(path: Path) -> tuple[float, float]:
    """(seconds, frames per second) of a file's video stream."""
    out = json.loads(run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=duration,r_frame_rate:format=duration", "-of", "json", str(path)]))
    st = (out.get("streams") or [{}])[0]
    num, _, den = st.get("r_frame_rate", "24/1").partition("/")
    fps = float(num) / float(den or 1) or 24.0
    return float(st.get("duration") or out.get("format", {}).get("duration") or 0), fps


def picture_scene_ends(video: Path) -> list[float] | None:
    """When each scene ends in an existing video's picture: from its .timing.json,
    else from its .vtt (each cue ends where its scene ends; videos made before the
    sidecar only have that). None when neither file is there."""
    side = video.with_suffix(".timing.json")
    if side.exists():
        return [sc["start"] + sc["dur"] for sc in json.loads(side.read_text())["scenes"]]
    cap = video.with_suffix(".vtt")
    if cap.exists():
        # Cue text escapes ">", so "-->" only appears in timing lines.
        return [int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000
                for h, m, s, ms in re.findall(r"--> (\d+):(\d\d):(\d\d)\.(\d{3})", cap.read_text())]
    return None


def remux_drift(total: float, length: float, fps: float) -> str | None:
    """Why the old picture can't carry the new sound, or None if it can. The
    picture was rendered as ceil(total * fps) frames, so a length more than a
    frame away from the new total means the scene timings changed."""
    if abs(length - total) > 1 / fps + 1e-6:
        return (f"the new timing runs {total:.2f} s but the video is {length:.2f} s: the voice or the scenes changed, "
                "so the picture would drift out of step. Render it again without --remux")
    return None


def true_peak(path: Path) -> float | None:
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(path), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    m = re.search(r"Peak:\s*(-?[\d.]+) dBFS", r.stderr[r.stderr.rfind("Summary:"):])
    return float(m.group(1)) if m else None


def settle_peak(out: Path, ceiling: float = -1.5) -> None:
    """AAC can push sharp pen clicks over the limiter's ceiling. Measure the
    finished file's true peak and, if it's over, turn the audio down by the
    excess (the picture is copied untouched)."""
    peak = true_peak(out)
    if peak is None or peak <= ceiling:
        return
    cut = peak - ceiling + 0.3
    tmp = out.with_name(out.stem + ".peak" + out.suffix)
    run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(out), "-c:v", "copy", "-af", f"volume=-{cut:.2f}dB", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(tmp)])
    tmp.replace(out)
    print(f"true peak was {peak:.1f} dBTP; audio lowered {cut:.1f} dB to {true_peak(out):.1f}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("lesson", type=Path, help="a built explorable .html")
    ap.add_argument("-o", "--out", type=Path, required=True)
    ap.add_argument("--engine", choices=["auto", "kokoro", "chatterbox"], default="auto")
    ap.add_argument("--voice", default="af_heart", help="Kokoro voice")
    ap.add_argument("--speed", type=float, default=None, help=f"Kokoro's pace (default {KOKORO_SPEED}); Chatterbox only takes 1.0")
    ap.add_argument("--pause", type=float, default=0.3, help="seconds between sentences")
    ap.add_argument("--board", choices=["paper", "chalk"], default="paper")
    ap.add_argument("--fps", type=int, default=24)
    ap.add_argument("--crf", type=int, default=28, help="x264 quality: lower is bigger and sharper")
    ap.add_argument("--keep", action="store_true", help="keep the frames folder")
    ap.add_argument("--pen", action="store_true", help="add the pen's sound under the marks (off by default: it follows an estimate of the strokes, not the strokes)")
    ap.add_argument("--remux", action="store_true", help="keep the picture of the existing --out video and only remake its sound (refused if the new timing is more than a frame off its length)")
    a = ap.parse_args()
    for tool in ("node", "ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise SystemExit(f"{tool} not found")

    info = json.loads(run(["node", str(HERE / "film_export.mjs"), str(a.lesson), "--scenes"]))
    scenes = info["scenes"]
    print(f"{info['title']}: {len(scenes)} scenes")
    engine = make_voice(a.engine, a.voice, a.speed)
    print(f"voice: {engine[0]}")
    clips = [voice_scene(engine, sc["say"], a.pause) for sc in scenes]

    # Time every scene to its voice: the picture moves first, then the voice, then a breath.
    lead, tail, t = 0.7, 0.9, 0.4
    timing = {"scenes": []}
    for sc, clip in zip(scenes, clips):
        think = 1.6 if sc["say"].startswith("Quick check") else 0.0  # time to think before the answer
        dur = max(3.5, lead + len(clip) / SR + tail + think)
        timing["scenes"].append({"start": t, "dur": dur, "voiceAt": t + lead, "voiceDur": len(clip) / SR})
        t += dur
    timing["total"] = t + 0.8
    work = Path(tempfile.mkdtemp(prefix="narrate-"))
    # The frames and audio go in a temp folder that is removed however the
    # render ends (kept only with --keep), so a failure leaves no frames behind.
    try:
        (work / "timing.json").write_text(json.dumps(timing))

        frames = work / "frames"
        if a.remux:
            if not a.out.exists():
                raise SystemExit(f"--remux needs the existing video at {a.out}")
            if a.pen:
                raise SystemExit("--remux can't add the pen: it needs the marks from a fresh render")
            # The picture was drawn against the old scene timings. Refuse when the new narration changes
            # them, or the voice and captions would drift from the picture and -shortest would cut one.
            # A matching total alone isn't enough: one scene longer and another shorter would pass it.
            before = picture_scene_ends(a.out)
            if before is None:
                raise SystemExit(f"--remux needs {a.out.with_suffix('.timing.json').name} or {a.out.with_suffix('.vtt').name} "
                                 "to check the scene timings; render the picture again without --remux")
            after = [sc["start"] + sc["dur"] for sc in timing["scenes"]]
            if len(before) != len(after) or any(abs(x - y) > 0.05 for x, y in zip(before, after)):
                raise SystemExit("--remux: the new narration moves the scene timings; render the picture again without --remux")
            # And the picture's length must still match the new total, to the frame.
            drift = remux_drift(timing["total"], *video_length(a.out))
            if drift:
                raise SystemExit(f"--remux refused: {drift}")
            marks = [0] * len(scenes)
        else:
            print("rendering frames…")
            run(["node", str(HERE / "film_export.mjs"), str(a.lesson), "--timing", str(work / "timing.json"), "--out", str(frames), "--fps", str(a.fps), "--board", a.board])
            marks = json.loads((frames / "marks.json").read_text())["marks"]

        # Voice track plus the pen: each scene's marks draw one after another over its first 45%.
        total = int(timing["total"] * SR) + SR
        voice = np.zeros(total, dtype=np.float32)
        pen = np.zeros(total, dtype=np.float32)
        rng = np.random.default_rng(7)
        kind = "chalk" if a.board == "chalk" else "paper"
        bank = load_pen(kind)
        if a.pen:
            print(f"pen: {'recordings' if bank else 'friction synth'} ({kind})")
        for sc, clip, m in zip(timing["scenes"], clips, marks):
            s = int(sc["voiceAt"] * SR)
            voice[s: s + len(clip)] += clip[: total - s]
            if m and a.pen:
                window = 0.45 * sc["dur"]
                for j in range(m):
                    st = int((sc["start"] + window * j / m) * SR)
                    sx = scratch(window / m * 0.85, kind == "chalk", rng, bank)
                    pen[st: st + len(sx)] += sx[: total - st]
        voice /= max(1e-6, np.max(np.abs(voice))) / 0.9
        v = active_rms(voice)
        p = active_rms(pen)
        if p:
            pen *= v * db(PEN_UNDER_VOICE_DB[kind]) / p
        mix = voice + pen + room_tone(total, rng) * v * db(ROOM_TONE_DB)
        mix /= max(1.0, np.max(np.abs(mix)) / 0.95)
        sf.write(work / "audio.wav", mix, SR)

        a.out.parent.mkdir(parents=True, exist_ok=True)
        # Write and check a .partial copy; the real file is only replaced once it
        # passes, so a failed render never clobbers a good video.
        out = a.out.with_name(a.out.stem + ".partial" + a.out.suffix)
        print("encoding…")
        # Limit short peaks without automatic makeup gain. Whole-track peak cuts
        # can satisfy TP while pushing otherwise normal speech below the LUFS gate.
        # Oversampling and latency compensation preserve timing and codec headroom.
        master = ("loudnorm=I=-16:TP=-2:LRA=7,aresample=192000,"
                  "alimiter=limit=0.70794578:level=false:latency=true,aresample=48000")
        if a.remux:
            run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(a.out), "-i", str(work / "audio.wav"), "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                 "-af", master, "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)])
        else:
            run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(a.fps), "-i", str(frames / "%06d.png"), "-i", str(work / "audio.wav"),
                 "-af", master, "-c:v", "libx264", "-preset", "slow", "-pix_fmt", "yuv420p", "-crf", str(a.crf),
                 "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)])
        settle_peak(out)
        out.with_suffix(".vtt").write_text(vtt(timing, [sc["say"] for sc in scenes]))
        out.with_suffix(".timing.json").write_text(json.dumps(timing))  # lets a later --remux check the picture still fits
    finally:
        if a.keep:
            print(f"work files in {work}")
        else:
            shutil.rmtree(work, ignore_errors=True)
    print(f"wrote {out} ({timing['total']:.1f} s) and {out.with_suffix('.vtt').name}")
    r = subprocess.run([sys.executable, str(QA / "check_video.py"), str(out), "--sheet", str(out.with_suffix(".sheet.png"))], capture_output=True, text=True)
    print(r.stdout.strip())
    code = r.returncode
    # Does the voice say what the captions say? (Only when Whisper is installed.)
    import importlib.util

    if importlib.util.find_spec("faster_whisper"):
        sp = subprocess.run([sys.executable, str(QA / "check_speech.py"), str(out)], capture_output=True, text=True)
        print(sp.stdout.strip() or sp.stderr.strip()[-400:])
        code = code or sp.returncode
    if code == 0:
        for ext in (a.out.suffix, ".vtt", ".timing.json", ".sheet.png"):
            src = out.with_suffix(ext) if ext != a.out.suffix else out
            if ext == ".sheet.png":
                src = out.with_name(out.stem + ".sheet.png")
            if src.exists():
                src.replace(a.out.with_name(a.out.stem + ext))
        print(f"passed: {a.out}")
    else:
        print(f"kept the failed render as {out} for a look; {a.out} is unchanged")
    return code


if __name__ == "__main__":
    sys.exit(main())
