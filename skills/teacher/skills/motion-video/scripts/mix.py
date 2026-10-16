#!/usr/bin/env python3
"""mix.py: mix voice + music + effects and mux them onto the silent render.

The voice is the star: music is ducked under every spoken line (smooth attack/release), effects sit on
top, and the result is loudness-normalised to -16 LUFS (true peak -1.5 dB), the level YouTube and most
players expect. If the silent render is not H.264 yuv420p (Remotion writes yuvj420p, some tools write
ProRes or VP9), the video is re-encoded so it plays everywhere; otherwise it is copied untouched.

Usage:
  python3 mix.py --project . [--video build/silent.mp4] [--out out/<slug>.mp4]
                 [--music-db -17] [--sfx-db -12] [--duck 0.6]
Writes audio/mix.wav, audio/bed.wav + audio/bed.m4a (music + effects without voice, for voice swaps),
and the final MP4.
"""
import argparse
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pydeps  # noqa: E402  (pydeps.py ships next to this file)
import vstate  # noqa: E402

if __name__ == "__main__":
    pydeps.ensure("numpy", "soundfile")  # where pip refuses (Homebrew, Debian/Ubuntu): switch to the pipeline's environment
import numpy as np  # noqa: E402

SR = 48000


def smooth(x, w):
    w = max(1, int(w))
    c = np.cumsum(np.concatenate([[0.0], x]))
    h = w // 2
    i = np.arange(len(x))
    lo, hi = np.clip(i - h, 0, len(x)), np.clip(i + h + 1, 0, len(x))
    return (c[hi] - c[lo]) / (hi - lo)


def load(path, n, stereo=True):
    import soundfile as sf
    if not os.path.exists(path):
        return np.zeros((n, 2) if stereo else n)
    x, sr = sf.read(path, dtype="float64", always_2d=True)
    if sr != SR:
        m = int(round(len(x) * SR / sr))
        x = np.stack([np.interp(np.arange(m) * sr / SR, np.arange(len(x)), x[:, c]) for c in range(x.shape[1])], 1)
    if stereo and x.shape[1] == 1:
        x = np.repeat(x, 2, 1)
    if not stereo:
        x = x.mean(1)
    out = np.zeros((n, 2) if stereo else n)
    k = min(n, len(x))
    out[:k] = x[:k]
    return out


def probe(path):
    out = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                   "stream=codec_name,pix_fmt:format=duration", "-of", "json", path])
    j = json.loads(out)
    s = j["streams"][0]
    return s["codec_name"], s.get("pix_fmt"), float(j["format"]["duration"])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--video", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--music-db", type=float, default=-17.0, help="bed level relative to the voice peak")
    ap.add_argument("--sfx-db", type=float, default=-12.0)
    ap.add_argument("--duck", type=float, default=0.6, help="how far music dips under speech (0..1)")
    ap.add_argument("--crf", type=int, default=18)
    a = ap.parse_args()
    import soundfile as sf

    root = os.path.abspath(a.project)
    st = {}
    sp = os.path.join(root, ".video-state.json")
    if os.path.exists(sp):
        st = json.load(open(sp))
    slug = st.get("slug", "video")
    cfg = st.get("config", {})
    video = a.video or os.path.join(root, cfg.get("silent", "build/silent.mp4"))
    out = a.out or os.path.join(root, cfg.get("final", f"out/{slug}.mp4"))
    vcodec, pix, vdur = probe(video)
    tm = json.load(open(os.path.join(root, "timing.json")))
    T = max(vdur, float(tm["total"]))
    n = int(T * SR)

    # what this mix is made from, by content (a file swapped in with an old time, as cp -p leaves it, still counts)
    used = {f: (vstate.sha(os.path.join(root, f)) if os.path.isfile(os.path.join(root, f)) else None)
            for f in ("voice/narration.wav", "audio/music.wav", "audio/sfx.wav")}
    video_sha = vstate.sha(video)
    voice = load(os.path.join(root, "voice", "narration.wav"), n, stereo=False)
    music = load(os.path.join(root, "audio", "music.wav"), n)
    fx = load(os.path.join(root, "audio", "sfx.wav"), n)
    vpk = np.abs(voice).max() or 1.0
    voice = voice / vpk * 0.89

    # duck: speech activity from a 50 ms RMS envelope, then a ~0.35 s smoothed gate (attack + release)
    env = np.sqrt(smooth(voice ** 2, 0.05 * SR))
    act = (env > 0.02).astype(float)
    act = smooth(act, 0.35 * SR)
    gain = 10 ** (a.music_db / 20) * (1 - a.duck * np.clip(act, 0, 1))
    bed = music * gain[:, None] + fx * 10 ** (a.sfx_db / 20)
    mix = bed + voice[:, None]
    peak = np.abs(mix).max()
    if peak > 0.97:
        mix *= 0.97 / peak
        bed *= 0.97 / peak
    os.makedirs(os.path.join(root, "audio"), exist_ok=True)
    sf.write(os.path.join(root, "audio", "mix.wav"), mix.astype(np.float32), SR)
    sf.write(os.path.join(root, "audio", "bed.wav"), bed.astype(np.float32), SR)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", os.path.join(root, "audio", "bed.wav"), "-c:a", "aac", "-b:a", "160k",
                    os.path.join(root, "audio", "bed.m4a")], check=True)

    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)  # --out final.mp4 has no folder part
    reencode = not (vcodec == "h264" and pix == "yuv420p")
    vargs = (["-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf), "-pix_fmt", "yuv420p"] if reencode
             else ["-c:v", "copy"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", video, "-i", os.path.join(root, "audio", "mix.wav"),
           "-map", "0:v:0", "-map", "1:a:0", *vargs,
           "-af", "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000", "-c:a", "aac", "-b:a", "192k",
           "-t", f"{vdur:.3f}", "-movflags", "+faststart", out]
    subprocess.run(cmd, check=True)
    # package.py and the mix gate compare these with the files as they are now, so a narration or bed replaced after
    # the mix is caught whatever its modification time
    used["audio/bed.m4a"] = vstate.sha(os.path.join(root, "audio", "bed.m4a"))
    try:
        vkey = os.path.relpath(video, root)
    except ValueError:  # on Windows, a video on another drive than the project has no relative path
        vkey = os.path.abspath(video)
    used[vkey] = video_sha   # the picture: a render swapped in after the mix counts too
    json.dump({"final_sha": vstate.sha(out), "inputs": used}, open(os.path.join(root, "audio", "mix.json"), "w"), indent=1)
    print(f"wrote {out}  ({vdur:.1f}s, video {'re-encoded' if reencode else 'copied'} from {vcodec}/{pix})")


if __name__ == "__main__":
    main()
