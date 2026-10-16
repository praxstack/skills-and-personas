#!/usr/bin/env python3
"""qa.py: check the finished video the way a picky viewer would, before anyone else sees it.

Hard checks (fail the qa gate):
  format      H.264, yuv420p, the planned resolution and frame rate, AAC audio at 48 kHz
  duration    matches the voice timing (scenes follow the voice; nothing cut off)
  loudness    integrated -16 LUFS +/- 2, true peak <= -0.5 dBTP
  voice-sync  every narration line is present in the final audio at its planned time (cross-correlation,
              so a missing, silent or drifting voice is caught)
  black       no stretch of pure black longer than 1 s inside the film
  flicker     no single-frame flashes (a frame that differs from both neighbours while they match each other)
  moving-text every text in the moving film (on a 4 fps grid, any length of film) meets the
              text rule unless it is moving: a text under 26 px or 4.5:1 for 0.5 s or more fails. Chapter cards, panels
              and anything between the review stills are covered; a pop, fade or fly-through shorter than that is motion.
              A film with recorded footage (window.FOOTAGE) gets footage-map.json in the project folder first
              (node capture.mjs --page source/index.html --footage-map footage-map.json): the recording's own text is
              then listed apart, and everything the film draws, notes on the footage included, is held to the rule
  inputs-unchanged  the final, timing.json and timeline.json end the run as they started it (a mix or re-voice
              finishing meanwhile would leave the report vouching for a file the checks never saw)
Soft checks (warnings in the report):
  chapter-entry  when each chapter's first line starts, its subject is already on screen (the picture holds at
              least 60% of the detail it has a second later); otherwise the voice talks over an empty or arriving frame
  static      no shot frozen for more than 8 s (the quality bar: something should always be moving)
  length      inside the format's target length

Also writes qa/contact-sheet.png (the whole film at a glance) and qa/stills/*.jpg (one frame per chapter
plus the longest beats; QA fails if ffmpeg cannot write one). Look at them: the qa gate needs `vstate.py attest qa "<what you saw>"`.

Usage:
  python3 qa.py --project . [--video out/<slug>.mp4] [--waive flicker="frames 1203-1205 are an intended flash cut"]
"""
import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pydeps  # noqa: E402  (pydeps.py ships next to this file)

if __name__ == "__main__":
    pydeps.ensure("numpy")  # where pip refuses (Homebrew, Debian/Ubuntu): switch to the pipeline's environment
import numpy as np  # noqa: E402


def edge_fade(start, end, duration):
    """A black stretch the film may have: a short fade in at the very start or a fade out in the last 2 s.
    A long black opening, or black from the middle to the end, is not a fade."""
    return (start <= 0.6 and end <= 1.6) or start >= duration - 2.0


def sha(path, n=16):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:n]


UNWRITTEN = {}   # file name -> why ffmpeg could not write it (the contact sheet, a still); main() fails QA on any


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    # a pass over the picture (blackdetect, freezedetect) reports only what it found: one that could not read the
    # film would find nothing and read as a pass, so it stops QA instead
    if r.returncode and "-an" in cmd and cmd[-3:] == ["-f", "null", "-"]:
        raise SystemExit(f"qa.py: ffmpeg could not run {cmd[cmd.index('-vf') + 1]} over the film (exit {r.returncode}): "
                         f"{r.stderr.strip()[-400:]}")
    if r.returncode and cmd[0] == "ffmpeg" and cmd[-1] != "-":
        err = " / ".join(x for x in r.stderr.replace(cmd[-1], os.path.basename(cmd[-1])).splitlines() if x.strip())
        UNWRITTEN[os.path.basename(cmd[-1])] = f"exit {r.returncode}: {err[-200:]}"
    return r


def probe(path):
    j = json.loads(run(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration:stream=codec_type,codec_name,width,height,r_frame_rate,pix_fmt,sample_rate",
                        "-of", "json", path]).stdout)
    v = next((s for s in j["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in j["streams"] if s["codec_type"] == "audio"), {})
    n, d = (v.get("r_frame_rate") or "0/1").split("/")
    return {"duration": float(j["format"]["duration"]), "vcodec": v.get("codec_name"), "pix_fmt": v.get("pix_fmt"),
            "width": v.get("width"), "height": v.get("height"), "fps": float(n) / float(d) if float(d) else 0,
            "acodec": a.get("codec_name"), "sr": int(a.get("sample_rate") or 0)}


def loudness(path):
    err = run(["ffmpeg", "-nostats", "-i", path, "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"]).stderr
    tail = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    return (float(i.group(1)) if i else None), (float(p.group(1)) if p and p.group(1) != "-inf" else None)


def audio(path, sr=16000):
    raw = subprocess.check_output(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(sr), "-f", "f32le", "-"])
    return np.frombuffer(raw, dtype=np.float32)


def voice_sync(final, narration, tm, sr=16000):
    """Per line: best lag and normalised correlation between the narration clip and the final mix."""
    a, v = audio(final, sr), audio(narration, sr)
    res = []
    for ln in tm["lines"]:
        s, d = ln["voiceAt"], min(ln["voiceDur"], 4.0)
        i0, i1 = int(s * sr), int((s + d) * sr)
        ref = v[i0:i1]
        if len(ref) < sr * 0.2 or np.abs(ref).max() < 1e-3:
            res.append((ln["id"], None, 0.0))  # no usable voice for this line: counted as not found, never skipped
            continue
        pad = int(0.5 * sr)
        j0, j1 = max(0, i0 - pad), min(len(a), i1 + pad)
        seg = a[j0:j1]
        if len(seg) < len(ref):
            res.append((ln["id"], None, 0.0))
            continue
        n = 1 << int(np.ceil(np.log2(len(seg) + len(ref))))
        cc = np.fft.irfft(np.fft.rfft(seg, n) * np.conj(np.fft.rfft(ref, n)), n)[: len(seg) - len(ref) + 1]
        c2 = np.cumsum(np.concatenate([[0.0], seg.astype(np.float64) ** 2]))
        e_seg = np.sqrt(np.maximum(c2[len(ref):] - c2[:-len(ref)], 0)) + 1e-9
        ncc = cc / (e_seg * (np.linalg.norm(ref) + 1e-9))
        k = int(np.argmax(ncc))
        res.append((ln["id"], round((j0 + k - i0) / sr, 3), float(ncc[k])))
    return res


def intervals(err, key):
    starts = [float(x) for x in re.findall(key + r"_start:\s*([\d.]+)", err)]
    ends = [float(x) for x in re.findall(key + r"_end:\s*([\d.]+)", err)]
    return list(zip(starts, ends + [None] * (len(starts) - len(ends))))


def frames_rgb(path, w=160, h=90):
    """Every frame, small, in colour: a one-frame flash of another hue at the same brightness is a flash too."""
    import tempfile
    log = tempfile.TemporaryFile()  # a file, not a pipe: a long error log must not stall ffmpeg while frames are read
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-vf", f"scale={w}:{h},format=rgb24", "-f", "rawvideo", "-"],
                         stdout=subprocess.PIPE, stderr=log)
    size, n = w * h * 3, 0
    while True:
        b = p.stdout.read(size)
        if len(b) < size:
            break
        n += 1
        yield np.frombuffer(b, dtype=np.uint8).astype(np.int16)
    if p.wait() or not n:  # a film ffmpeg could not read has no flashes to find; that is not a pass
        log.seek(0)
        err = log.read().decode(errors="replace")
        raise SystemExit(f"qa.py: ffmpeg could not read the film's frames for the flicker check (exit {p.returncode}, "
                         f"{n} frames): {err.strip()[-400:]}")
    log.close()


def flicker(path, fps, thr=6.0):
    hits, f0, f1, i = [], None, None, 0
    for f2 in frames_rgb(path):
        if f0 is not None:
            d01, d12, d02 = (np.abs(f1 - f0).mean(), np.abs(f2 - f1).mean(), np.abs(f2 - f0).mean())
            if d01 > thr and d12 > thr and d02 < 0.35 * min(d01, d12):
                hits.append(round((i - 1) / fps, 3))
        f0, f1, i = f1, f2, i + 1
    return hits


def edge_density(path, t, w=480):
    """Share of edge pixels in the content area (caption band and header excluded) of the frame at t."""
    cv2 = pydeps.need("cv2", "opencv-python")  # chapter-entry runs even when moving-text (which installs it) is skipped
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1", "-vf",
                          f"scale={w}:-2,format=gray", "-f", "rawvideo", "-"], capture_output=True).stdout
    h = len(raw) // w
    if not h:
        return None
    g = np.frombuffer(raw[: w * h], dtype=np.uint8).reshape(h, w)[int(0.12 * h): int(0.82 * h)]
    return float((cv2.Canny(g, 60, 140) > 0).mean())


def chapter_entry(video, tm):
    """(chapter, voiceAt, detail at voiceAt / detail 1 s later) for the first line of every chapter after the first."""
    out, seen = [], set()
    for ln in tm["lines"]:
        if ln["chapter"] in seen:
            continue
        seen.add(ln["chapter"])
        if len(seen) == 1:
            continue
        a, b = edge_density(video, ln["voiceAt"] + 0.05), edge_density(video, ln["voiceAt"] + 1.0)
        if a is None or b is None:
            continue
        # blank at the first word and still blank a second later is the missing subject this check is for
        out.append((ln["chapter"], ln["voiceAt"], round(a / b, 2) if b else (1.0 if a else 0.0)))
    return out


def moving_text(video, duration, fmap=None):
    import importlib.util
    spec = importlib.util.spec_from_file_location("legibility", os.path.join(os.path.dirname(os.path.abspath(__file__)), "legibility.py"))
    L = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(L)
    import shutil
    import tempfile
    # The rule is 0.5 s on a 4 fps grid: two failing frames in a row. Reading a frame costs about a second, so
    # read every other one (2 fps), then only the in-between frames next to a frame with a failing text. A run of
    # two frames always holds a 2 fps frame, so this finds exactly the runs a full 4 fps read would.
    fps, dwell = 4.0, 0.5
    step = 1.0 / fps
    tmp = tempfile.mkdtemp(prefix="qa-moving-")
    try:
        paths, times = L.sample(video, fps / 2, tmp)
        at_ = (lambda ts: [L.map_at(fmap, t) for t in ts]) if fmap else (lambda ts: None)
        rep = L.check(paths, 26, 4.5, footage=at_(times))
        # in-between frame k sits after 2 fps frame k (k = -1: before the first one)
        want = [k for k in range(-1, len(rep)) if (k >= 0 and rep[k]["fails"]) or (k + 1 < len(rep) and rep[k + 1]["fails"])]
        want = [k for k in want if 0 <= times[max(k, 0)] + (step if k >= 0 else -step) < duration]
        at = {k: times[max(k, 0)] + (step if k >= 0 else -step) for k in want}
        files = []
        for k in want:
            files.append(os.path.join(tmp, f"b{k + 1:05d}.png"))
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{at[k]:.3f}", "-i", video, "-frames:v", "1", files[-1]], check=True)
        extra = dict(zip(want, L.check(files, 26, 4.5, footage=at_([at[k] for k in want])))) if files else {}
        grid = [(at[-1], extra[-1])] if -1 in extra else []
        for k, r in enumerate(rep):
            grid += [(times[k], r), (times[k] + step, extra.get(k, {"fails": []}))]
        return fps, dwell, L.dwell([r for _, r in grid], [t for t, _ in grid], step, dwell)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--video", default=None)
    ap.add_argument("--waive", action="append", default=[], help='name="reason" (recorded in the report)')
    ap.add_argument("--skip-flicker", action="store_true", help="only for quick re-checks; the gate still wants a full run")
    ap.add_argument("--skip-moving-text", action="store_true", help="only for quick re-checks; the gate still wants a full run")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    st = json.load(open(os.path.join(root, ".video-state.json")))
    cfg, slug = st["config"], st["slug"]
    video = a.video or os.path.join(root, cfg.get("final", f"out/{slug}.mp4"))
    # what this run checks, hashed before it starts: the report is tied to these, so a final or a timing replaced
    # while QA runs (a mix finishing, a re-voice) fails the run instead of being recorded as the one that was checked
    with open(os.path.join(root, "timing.json"), "rb") as f:
        raw = f.read()
    tm = json.loads(raw)
    inputs = {"video": video, "timing": os.path.join(root, "timing.json"), "timeline": os.path.join(root, "timeline.json")}
    checked = {"video": sha(video), "timing": hashlib.sha256(raw).hexdigest()[:16]}
    if os.path.isfile(inputs["timeline"]):
        checked["timeline"] = sha(inputs["timeline"])
    qa = os.path.join(root, "qa")
    os.makedirs(os.path.join(qa, "stills"), exist_ok=True)
    checks = []

    def check(name, ok, detail, level="fail"):
        checks.append({"name": name, "ok": bool(ok), "detail": detail, "level": level})
        print(f"  {'ok' if ok else ('XX' if level == 'fail' else '!!')}  {name}: {detail}", flush=True)

    print(f"QA {video}")
    p = probe(video)
    fmt_ok = (p["vcodec"] == "h264" and p["pix_fmt"] == "yuv420p" and (p["width"], p["height"]) == (cfg["width"], cfg["height"])
              and abs(p["fps"] - float(cfg["fps"])) < 0.01 and p["acodec"] == "aac" and p["sr"] == 48000)
    check("format", fmt_ok, f"{p['vcodec']}/{p['pix_fmt']} {p['width']}x{p['height']}@{p['fps']:.2f} audio {p['acodec']} {p['sr']} Hz")
    tol = max(1.0, 0.01 * tm["total"])
    check("duration", abs(p["duration"] - tm["total"]) <= tol, f"{p['duration']:.2f}s vs timing {tm['total']:.2f}s")
    I, peak = loudness(video)
    check("loudness", I is not None and -18 <= I <= -14 and (peak is None or peak <= -0.5),
          f"integrated {I} LUFS, true peak {peak} dBTP (target -16 LUFS; peak must be <= -0.5, mix aims for -1.5)")
    sync = voice_sync(video, os.path.join(root, "voice", "narration.wav"), tm)
    bad = [(i, lag, round(c, 2)) for i, lag, c in sync if lag is None or abs(lag) > 0.12 or c < 0.35]
    check("voice-sync", len(sync) == len(tm["lines"]) and not bad, f"{len(sync) - len(bad)}/{len(tm['lines'])} lines found at their time"
          + (f"; off: {bad[:6]}" if bad else ""))
    err = run(["ffmpeg", "-nostats", "-i", video, "-vf", "blackdetect=d=1.0:pix_th=0.03:pic_th=0.995", "-an", "-f", "null", "-"]).stderr
    blacks = [(s, e) for s, e in intervals(err, "black") if not edge_fade(s, e or p["duration"], p["duration"])]
    check("black", not blacks, f"{len(blacks)} black stretches > 1 s" + (f" at {blacks[:5]}" if blacks else ""))
    err = run(["ffmpeg", "-nostats", "-i", video, "-vf", "scale=320:-1,freezedetect=n=0.0015:d=8", "-an", "-f", "null", "-"]).stderr
    frozen = [(round(s, 1), round(e, 1) if e else None) for s, e in intervals(err, "lavfi.freezedetect.freeze")]
    check("static", not frozen, f"{len(frozen)} shots frozen > 8 s" + (f" at {frozen[:6]}" if frozen else "")
          + " (keep something moving: a drift, a highlight, a pulse)", level="warn")
    if not a.skip_flicker:
        fl = flicker(video, p["fps"])
        check("flicker", not fl, f"{len(fl)} single-frame flashes" + (f" at {fl[:10]} s" if fl else ""))
    else:
        check("flicker", False, "skipped (--skip-flicker): run the full check before the qa gate")
        checks[-1]["skipped"] = True  # a check that never ran cannot be waived
    if not a.skip_moving_text:
        print("  .. moving-text: reading the film's text a few times a second (a few minutes)", flush=True)
        mp = os.path.join(root, "footage-map.json")
        fmap = json.load(open(mp)) if os.path.isfile(mp) else None
        if fmap and abs(fmap.get("total", 0) - p["duration"]) > max(1.0, 0.01 * p["duration"]):
            check("footage-map", False, f"footage-map.json covers {fmap.get('total', 0):.1f} s but the film is {p['duration']:.1f} s: "
                  "make it again from the current page (capture.mjs --footage-map footage-map.json)")
            fmap = None
        fps, dw, runs = moving_text(video, p["duration"], fmap)
        long_ = [r for r in runs if r["long"]]
        json.dump(runs, open(os.path.join(qa, "moving-text.json"), "w"), indent=1)
        check("moving-text", not long_, f"{len(long_)} texts under 26 px / 4.5:1 for {dw:g} s or longer (sampled at {fps:g} fps; "
              f"{len(runs) - len(long_)} shorter dips are motion"
              + ("; the recording's own interface text is listed apart, per footage-map.json" if fmap else "") + ")"
              + ("; " + "; ".join(f"\"{r['text'][:30]}\" {r['start']:.1f}-{r['end']:.1f}s {r['worst_px']:.0f}px {r['worst_contrast']}:1"
                                  for r in long_[:5]) if long_ else ""))
    else:
        check("moving-text", False, "skipped (--skip-moving-text): run the full check before the qa gate")
        checks[-1]["skipped"] = True  # a check that never ran cannot be waived
    ce = chapter_entry(video, tm)
    late = [c for c in ce if c[2] < 0.6]
    check("chapter-entry", not late, f"{len(ce) - len(late)}/{len(ce)} chapters have their subject on screen as the voice starts"
          + (f"; arriving late (chapter, voice at, detail ratio): {late}" if late else ""), level="warn")
    lo, hi = float(cfg.get("min_minutes", 0)), float(cfg.get("max_minutes", 99))
    check("length", lo * 60 <= p["duration"] <= hi * 60, f"{p['duration'] / 60:.2f} min (target {lo}-{hi})", level="warn")

    for w in a.waive:
        name, _, reason = w.partition("=")
        reason = reason.strip().strip('"').strip()
        if not reason:
            sys.exit(f'--waive {name} needs a reason: --waive {name}="why this is intended"')
        for c in checks:
            if c["name"] == name and not c["ok"] and not c.get("skipped"):
                c["waived"] = reason

    # contact sheet and stills
    tiles = 36
    step = max(1.0, p["duration"] / tiles)
    run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vf", f"fps=1/{step:.3f},scale=480:-1,tile=6x6:padding=4:color=0x111111",
         "-frames:v", "1", os.path.join(qa, "contact-sheet.png")])
    for f in os.listdir(os.path.join(qa, "stills")):
        os.remove(os.path.join(qa, "stills", f))
    # 45% into the chapter, moved off a caption swap (both captions faint for ~0.35 s): to just before it, where the
    # previous line rests, or, at the chapter's first line (before it is the chapter card), just after it
    off_swap = lambda t: next(((ln["voiceAt"] + 0.4 if next(x for x in tm["lines"] if x["chapter"] == ln["chapter"]) is ln
                                else ln["voiceAt"] - 0.35) for ln in tm["lines"] if abs(t - ln["voiceAt"]) < 0.3), t)  # noqa: E731
    shots = [(f"ch{c['n']}-{re.sub(r'[^a-z0-9]+', '-', c['name'].lower()).strip('-')}", off_swap(c["start"] + 0.45 * (c["end"] - c["start"])))
             for c in tm["chapters"]]
    seen = {}  # a chapter that came back (0, 1, 0 in an older timing.json) gets its own still, not the earlier one's
    for k, (name, t) in enumerate(shots):
        seen[name] = seen.get(name, 0) + 1
        if seen[name] > 1:
            shots[k] = (f"{name}-{seen[name]}", t)
    longest = sorted(tm["lines"], key=lambda ln: -ln["dur"])[:4]
    shots += [(f"line-{ln['id']}", ln["voiceAt"] + 0.7 * ln["voiceDur"]) for ln in longest]
    for name, t in shots:
        run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.3f}", "-i", video, "-frames:v", "1", "-q:v", "3",
             os.path.join(qa, "stills", f"{name}.jpg")])
    # these are the pictures the qa gate has you look at: one ffmpeg could not write (no tile filter, a frame it could
    # not decode, a full disk) fails QA instead of passing with nothing, or an older picture, to look at
    made = [os.path.join(qa, "contact-sheet.png")] + [os.path.join(qa, "stills", f"{name}.jpg") for name, _ in shots]
    absent = [os.path.relpath(f, qa) for f in made if not os.path.isfile(f) or not os.path.getsize(f)]
    trouble = ([f"ffmpeg could not write {n} ({why})" for n, why in UNWRITTEN.items()]
               + [f"{f} is missing or empty" for f in absent if os.path.basename(f) not in UNWRITTEN])
    check("review-images", not trouble, "; ".join(trouble) if trouble else "the contact sheet and every still were written")

    def now(k):
        try:
            return sha(inputs[k]) if os.path.isfile(inputs[k]) else None
        except OSError:
            return None
    moved = [os.path.basename(inputs[k]) for k in checked if now(k) != checked[k]]
    check("inputs-unchanged", not moved, (f"{', '.join(moved)} changed while QA ran; run qa.py again" if moved
                                         else "the final, timing.json and timeline.json are the ones checked"))
    hard_ok = all(c["ok"] or c.get("waived") for c in checks if c["level"] == "fail")
    try:
        vname = os.path.relpath(video, root)
    except ValueError:  # on Windows, a --video on another drive than the project has no relative path
        vname = os.path.abspath(video)
    report = {"video": vname, "video_sha": checked["video"], "at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
              "probe": p, "checks": checks, "pass": hard_ok, "voice_sync": sync}
    # the timing this film was checked against: package.py makes the captions from it and ships the timeline
    for k in ("timing", "timeline"):
        if k in checked:
            report[k + "_sha"] = checked[k]
    json.dump(report, open(os.path.join(qa, "report.json"), "w"), indent=1)
    with open(os.path.join(qa, "report.md"), "w") as f:
        f.write(f"# QA: {slug}\n\n")
        for c in checks:
            f.write(f"- {'PASS' if c['ok'] else ('WAIVED' if c.get('waived') else c['level'].upper())} **{c['name']}**: {c['detail']}\n")
    print(f"\n{'PASS' if hard_ok else 'FAIL'}: report in qa/report.md; now LOOK at qa/contact-sheet.png and qa/stills/")
    raise SystemExit(0 if hard_ok else 1)


if __name__ == "__main__":
    main()
