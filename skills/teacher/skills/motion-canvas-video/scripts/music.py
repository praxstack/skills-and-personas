#!/usr/bin/env python3
"""music.py: compose a soft music bed and sound effects for the film, deterministically, in numpy.

No samples, no network: everything is synthesized, so it works offline and re-renders identically.
The bed thins out under think pauses, swells on chapter changes, and fades in and out. Ducking under
the voice happens later in mix.py.

Usage:
  python3 music.py --project . [--mood calm|piano|pulse|none] [--seed 787] [--no-whoosh] [--chime]
Reads timing.json (and per-line "sfx" cues from script.json). Writes:
  audio/music.wav   48 kHz stereo bed
  audio/sfx.wav     48 kHz stereo effects (whoosh on chapter changes, plus any per-line cues)

Per-line cues in script.json: "sfx": [{"at": 1.2, "kind": "pop"}]  (seconds after the line's voiceAt;
kinds: whoosh, pop, chime, tick, click, thud, rise).
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pydeps  # noqa: E402  (pydeps.py ships next to this file)

if __name__ == "__main__":
    pydeps.ensure("numpy", "soundfile")  # where pip refuses (Homebrew, Debian/Ubuntu): switch to the pipeline's environment
import numpy as np  # noqa: E402

SR = 48000


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def convolve(x, h):
    """Long convolution without allocating a 2^25-point FFT (overlap-add)."""
    try:
        from scipy.signal import oaconvolve
        return oaconvolve(x, h)[: len(x)]
    except Exception:  # noqa: BLE001
        B = 1 << 17
        n = 1 << int(np.ceil(np.log2(B + len(h) - 1)))
        H = np.fft.rfft(h, n)
        y = np.zeros(len(x) + len(h))
        for i in range(0, len(x), B):
            seg = np.fft.irfft(np.fft.rfft(x[i:i + B], n) * H, n)[: min(B, len(x) - i) + len(h) - 1]
            y[i:i + len(seg)] += seg
        return y[: len(x)]


def smooth(x, w):
    """Moving average via cumulative sums (np.convolve with long windows on long signals hangs)."""
    w = max(1, int(w))
    c = np.cumsum(np.concatenate([[0.0], x]))
    h = w // 2
    i = np.arange(len(x))
    lo, hi = np.clip(i - h, 0, len(x)), np.clip(i + h + 1, 0, len(x))
    return (c[hi] - c[lo]) / (hi - lo)


def reverb(x, rng, secs=2.6, decay=0.7):
    n = int(secs * SR)
    t = np.arange(n) / SR
    ir = rng.standard_normal(n) * np.exp(-t / decay)
    ir /= np.sqrt((ir ** 2).sum())
    return convolve(x, ir)


def piano_note(f, dur, vel, rng):
    n = int(dur * SR)
    t = np.arange(n) / SR
    y = np.zeros(n)
    for h, a in enumerate([1, .42, .22, .11, .06, .035], 1):
        fh = f * h * (1 + 0.0004 * h * h)
        y += a * np.sin(2 * np.pi * fh * t + rng.uniform(0, 6.28)) * np.exp(-t * (0.9 + 0.55 * h + f / 900))
    y *= 1 - np.exp(-t / 0.004)
    k = min(n, int(0.05 * SR))
    y[-k:] *= np.linspace(1, 0, k)
    return vel * y


MOODS = ("calm", "piano", "pulse", "none")
SFX_KINDS = ("whoosh", "pop", "chime", "tick", "click", "thud", "rise")  # what sfx_kind() makes


def mood_calm(T, rng):
    n = int(T * SR)
    t = np.arange(n) / SR
    bpm, chords = 76, [[48, 55, 59, 64], [45, 52, 55, 60], [41, 48, 52, 57], [43, 50, 52, 59]]
    beat = 60 / bpm
    bar = 4 * beat
    pad, keys, bass = np.zeros(n), np.zeros(n), np.zeros(n)
    for b in range(int(np.ceil(T / bar)) + 1):
        ch, s0 = chords[b % 4], b * bar
        i0, i1 = int(s0 * SR), min(n, int((s0 + bar + 1.6) * SR))
        if i0 >= n:
            break
        tt = t[i0:i1] - s0
        env = np.minimum(1, tt / 0.9) * np.where(tt > bar, np.exp(-(tt - bar) / 0.6), 1.0)
        for m in ch:
            for det in (-0.004, 0.0, 0.0045):
                f = midi(m + 12) * (1 + det)
                pad[i0:i1] += env * (np.sin(2 * np.pi * f * tt + det * 900) + 0.18 * np.sin(4 * np.pi * f * tt)) / 12
        bass[i0:i1] += env * np.sin(2 * np.pi * midi(ch[0] - 12) * tt) * 0.22
        pattern = [ch[1] + 24, ch[2] + 24, ch[3] + 24, ch[2] + 24]
        for k in range(4):
            if (b * 4 + k) % 8 in (3, 7) and b % 2:
                continue
            st = s0 + k * beat
            j0, j1 = int(st * SR), min(n, int((st + 2.4) * SR))
            if j0 >= n:
                break
            u = t[j0:j1] - st
            f = midi(pattern[k])
            e = np.exp(-u / 0.55) * np.minimum(1, u / 0.006)
            vel = 0.55 + 0.25 * ((b * 4 + k) % 3 == 0)
            keys[j0:j1] += vel * e * (np.sin(2 * np.pi * f * u) + 0.32 * np.sin(4 * np.pi * f * u) * np.exp(-u / 0.25)) / 7
    return pad * 0.55 + keys * 0.9 + bass * 0.8


def mood_piano(T, rng):
    n = int(T * SR) + SR
    y = np.zeros(n)
    beat = 60 / 72
    bars = [(38, [62, 66, 69, 73, 76]), (35, [59, 62, 66, 69, 74]), (43, [62, 66, 67, 71, 74]), (45, [62, 64, 67, 69, 74])]
    pattern = [0, 2, 1, 3, 2, 4, 3, 1]

    def add(sig, at):
        i = max(0, int(at * SR))
        j = min(n, i + len(sig))
        y[i:j] += sig[: j - i]
    t, b = 0.0, 0
    while t < T - 2:
        bass, chord = bars[b % 4]
        add(piano_note(midi(bass), 3.5, 0.55, rng), t)
        add(piano_note(midi(bass + 12), 3.0, 0.22, rng), t + 2 * beat)
        for i, idx in enumerate(pattern):
            add(piano_note(midi(chord[idx]), 2.6, (0.30 if i % 2 == 0 else 0.22) * rng.uniform(0.85, 1.1), rng),
                t + i * beat / 2 + rng.normal(0, 0.008))
        t += 4 * beat
        b += 1
    return y[: int(T * SR)]


def mood_pulse(T, rng):
    n = int(T * SR)
    t = np.arange(n) / SR
    chords = [[57, 60, 64, 69], [53, 57, 60, 65], [48, 55, 60, 64], [55, 59, 62, 67]]
    pad, arp, L = np.zeros(n), np.zeros(n), 8.0
    for c0 in range(int(T / L) + 2):
        ch = chords[c0 % 4]
        a, b = int(c0 * L * SR), int(min(n, (c0 * L + L + 2.5) * SR))
        if a >= n:
            break
        tt = t[a:b] - c0 * L
        env = np.minimum(1, tt / 2.5) * np.minimum(1, np.maximum(0, (L + 2.5 - tt) / 2.5))
        for m in ch:
            for det in (-0.12, 0.12):
                pad[a:b] += env * (np.sin(2 * np.pi * midi(m) * (1 + det / 100) * tt) + 0.25 * np.sin(4 * np.pi * midi(m) * tt)) / 8
        for k in range(16):
            m = ch[[0, 1, 2, 3, 2, 1, 2, 3][k % 8]] + 12
            s0 = int((c0 * L + k * 0.5) * SR)
            if s0 >= n:
                break
            m_n = min(int(1.6 * SR), n - s0)
            u = np.arange(m_n) / SR
            arp[s0:s0 + m_n] += np.sin(2 * np.pi * midi(m) * u) * np.exp(-u * 3.2) * 0.12
    return smooth(pad + arp, 24)


# ----------------------------------------------------------------------------- effects
WHOOSH_LEN = 0.95  # seconds
WHOOSH_GAP = 0.10  # the whoosh ends this long before the chapter's first word


def whoosh_start(first_word_at):
    """Start time of a chapter whoosh: it ends WHOOSH_GAP before the first word, so it never masks that word's onset
    (centred on the chapter start it covered the first syllable: ASR heard "Brute force" as "Route force")."""
    return first_word_at - WHOOSH_LEN - WHOOSH_GAP


def sfx_kind(kind, rng):
    if kind in ("whoosh", "rise"):
        d = WHOOSH_LEN if kind == "whoosh" else 1.4
        m = int(d * SR)
        u = np.arange(m) / m
        noise = rng.standard_normal((m, 2))
        band = np.stack([smooth(noise[:, c], 6) - smooth(noise[:, c], 60) for c in range(2)], 1)
        env = np.sin(np.pi * u) ** 2 * (u ** 0.6) if kind == "whoosh" else u ** 2 * np.minimum(1, (1 - u) * 12)
        pan = np.stack([1 - 0.35 * u, 0.65 + 0.35 * u], 1)
        return band * env[:, None] * pan * 0.6
    if kind == "pop":
        m = int(0.18 * SR)
        u = np.arange(m) / SR
        f = 900 * np.exp(-u * 18) + 220
        y = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-u * 26) * 0.5
        return np.stack([y, y], 1)
    if kind == "chime":
        m = int(2.6 * SR)
        u = np.arange(m) / SR
        y = np.zeros(m)
        for f0, at in ((midi(81), 0.0), (midi(78), 0.42)):
            k = int(at * SR)
            uu = u[: m - k]
            y[k:] += sum(a * np.sin(2 * np.pi * f0 * r * uu) * np.exp(-uu * d)
                         for r, a, d in [(1, 1, 1.6), (2.0, .35, 2.4), (2.76, .25, 3.5)]) * (1 - np.exp(-uu / 0.002))
        y *= 0.16
        return np.stack([y, y], 1)
    if kind in ("tick", "click"):
        m = int(0.05 * SR)
        u = np.arange(m) / SR
        y = rng.standard_normal(m) * np.exp(-u * (300 if kind == "click" else 160)) * (0.25 if kind == "click" else 0.18)
        return np.stack([y, y], 1)
    if kind == "thud":
        m = int(0.4 * SR)
        u = np.arange(m) / SR
        y = np.sin(2 * np.pi * (70 + 60 * np.exp(-u * 20)) * u) * np.exp(-u * 9) * 0.6
        return np.stack([y, y], 1)
    raise ValueError(f"unknown sfx kind {kind}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--mood", default=None, choices=MOODS, help="calm | piano | pulse | none (default: script meta.music or calm)")
    ap.add_argument("--seed", type=int, default=787)
    ap.add_argument("--no-whoosh", action="store_true")
    ap.add_argument("--chime", action="store_true", help="two-tone chime on every chapter change")
    a = ap.parse_args()
    import soundfile as sf

    root = os.path.abspath(a.project)
    tm = json.load(open(os.path.join(root, "timing.json")))
    sc = json.load(open(os.path.join(root, "script.json"), encoding="utf-8"))
    mood = a.mood or sc["meta"].get("music") or "calm"
    if mood not in MOODS:  # before any work: a typo here would otherwise stop the music step with a KeyError
        sys.exit(f"script.json meta.music is {mood!r}; it takes one of {', '.join(MOODS)} (or pass --mood)")
    for ln in sc["lines"]:  # the effect cues too: a misspelt kind would otherwise stop this step after the music
        sfx = ln.get("sfx")
        for cue in [] if sfx is None else sfx if isinstance(sfx, list) else [sfx]:
            try:
                ok = isinstance(sfx, list) and cue["kind"] in SFX_KINDS and math.isfinite(float(cue.get("at", 0)))
            except (TypeError, ValueError, KeyError, AttributeError):
                ok = False
            if not ok:
                sys.exit(f"script.json line {ln.get('id')}: the sfx cue {cue!r} is not one music.py makes; write "
                         f'{{"kind": "pop", "at": 0.5}} with kind one of {", ".join(SFX_KINDS)} and at in seconds')
    T = float(tm["total"])
    n = int(T * SR)
    rng = np.random.default_rng(a.seed)
    os.makedirs(os.path.join(root, "audio"), exist_ok=True)

    if mood == "none":
        music = np.zeros((n, 2))
    else:
        dry = {"calm": mood_calm, "piano": mood_piano, "pulse": mood_pulse}[mood](T, rng)[:n]
        dry = np.pad(dry, (0, n - len(dry)))
        wl, wr = reverb(dry, rng), reverb(dry, np.random.default_rng(a.seed + 1))
        music = np.stack([dry * 0.7 + wl * 0.5, dry * 0.7 + wr * 0.5], 1)
        t = np.arange(n) / SR
        g = np.full(n, 0.85)
        for ln in tm["lines"]:
            if ln.get("think", 0) >= 1.5:  # thinner while the viewer thinks
                s = ln["voiceAt"] + ln["voiceDur"]
                g[int(s * SR):int((s + ln["think"]) * SR)] = 0.55
        for c in tm["chapters"][1:]:  # a small swell into each chapter
            g[int(max(0, c["start"] - 0.6) * SR):int((c["start"] + 1.2) * SR)] = 1.0
        g = smooth(g, 0.8 * SR)
        g *= np.minimum(1, t / 1.5) * np.minimum(1, np.maximum(0, (T - t) / 2.5))
        music *= g[:, None]
        music /= np.abs(music).max() + 1e-9
    sf.write(os.path.join(root, "audio", "music.wav"), (music * 0.9).astype(np.float32), SR)

    fx = np.zeros((n + SR * 3, 2))

    def place(kind, at):
        s = sfx_kind(kind, rng)
        i = int(max(0, at) * SR)
        if i >= n:  # it would start after the film ends, so none of it could be heard
            print(f"skipped the {kind} at {at:.2f} s: the film ends at {T:.2f} s")
            return
        fx[i:i + len(s)] += s[: len(fx) - i]
    first_voice = {}
    for ln in tm["lines"]:
        first_voice.setdefault(ln["chapter"], ln["voiceAt"])
    for c in tm["chapters"][1:]:
        if not a.no_whoosh:
            place("whoosh", whoosh_start(first_voice.get(c["n"], c["start"] + 0.25)))
        if a.chime:
            place("chime", c["start"] + 0.1)
    by_id = {ln["id"]: ln for ln in tm["lines"]}
    for ln in sc["lines"]:
        for cue in ln.get("sfx") or []:
            place(cue["kind"], by_id[ln["id"]]["voiceAt"] + float(cue.get("at", 0)))
    sf.write(os.path.join(root, "audio", "sfx.wav"), fx[:n].astype(np.float32), SR)
    print(f"music ({mood}) and sfx written: {T:.1f}s")


if __name__ == "__main__":
    main()
