"""Media gates (AC-5.4, AC-5.5, AC-5.7 subset): streams, loudness, caption sync, answer leaks.

Gate pipeline:

    lesson.mp4 ──ffprobe──▶ streams: h264 1920x1080 30/1 + aac 48k + mov_text, chapters == scenes
        │
        ├──ebur128 (peak=true)──▶ integrated -16 ± 1 LUFS, true peak <= -1 dBTP
        │
        └──ffmpeg 16 kHz mono WAV──▶ whisper-cli (base.en, DTW token times)
                                        ├─▶ per cue: |first word - cue start| <= 0.5 s, |last word - cue end| <= 0.5 s
                                        └─▶ non-code WER <= 10 % (lexicon code tokens excluded)
    captions.vtt / chapters.vtt / transcript ──▶ no answer word before the answer cue
"""
import json
import re

from .. import host, text, tts

LUFS_TARGET, LUFS_TOL, TP_MAX = -16.0, 1.0, -1.0
SYNC_TOL = 0.5
WER_MAX = 0.10


def probe(mp4):
    ffprobe = host.which("ffprobe")
    res = host.run([ffprobe, "-v", "error", "-show_streams", "-show_chapters", "-show_format", "-of", "json", mp4],
                   check=True, timeout=120)
    return json.loads(res.stdout)


def loudness(mp4):
    ffmpeg = host.which("ffmpeg")
    res = host.run([ffmpeg, "-hide_banner", "-nostats", "-i", mp4, "-map", "0:a", "-af", "ebur128=peak=true",
                    "-f", "null", "-"], timeout=600)
    summary = res.stderr[res.stderr.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary.split("True peak:")[1]).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summary).group(1))
    return {"integrated_lufs": i, "true_peak_dbtp": tp, "lra_lu": lra}


def parse_vtt(path):
    cues = []
    for block in re.split(r"\n\s*\n", path.read_text()):
        lines = [ln for ln in block.strip().split("\n") if ln.strip()]
        idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if idx is None:
            continue
        a, b = [x.strip().split(" ")[0] for x in lines[idx].split("-->")]
        cues.append({"id": lines[idx - 1] if idx else "", "start": _secs(a), "end": _secs(b),
                     "text": "\n".join(lines[idx + 1:])})
    return cues


def _secs(ts):
    parts = [float(p) for p in ts.split(":")]
    return sum(p * 60 ** (len(parts) - 1 - i) for i, p in enumerate(parts))


def media_gate(mp4, out_dir, timing):
    d = probe(mp4)
    v = [s for s in d["streams"] if s["codec_type"] == "video"]
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    sub = [s for s in d["streams"] if s["codec_type"] == "subtitle"]
    loud = loudness(mp4)
    caps = parse_vtt(out_dir / "captions.vtt") if (out_dir / "captions.vtt").exists() else []
    chaps = parse_vtt(out_dir / "chapters.vtt") if (out_dir / "chapters.vtt").exists() else []
    checks = {
        "video_h264_1920x1080": bool(v) and v[0]["codec_name"] == "h264" and v[0]["width"] == 1920 and v[0]["height"] == 1080,
        "video_30fps": bool(v) and v[0]["r_frame_rate"] in ("30/1", "30000/1000"),
        "audio_aac": bool(a) and a[0]["codec_name"] == "aac",
        "captions_track_in_mp4": bool(sub) and sub[0]["codec_name"] == "mov_text",
        "chapters_in_mp4": len(d.get("chapters", [])) == len(timing["scenes"]),
        "captions_vtt": len(caps) == len(timing["cues"]),
        "chapters_vtt": len(chaps) == len(timing["scenes"]),
        "loudness_in_range": abs(loud["integrated_lufs"] - LUFS_TARGET) <= LUFS_TOL,
        "true_peak_ok": loud["true_peak_dbtp"] <= TP_MAX,
        "av_duration_match": bool(v and a) and abs(float(v[0].get("duration", 0)) - float(a[0].get("duration", 0))) <= 0.1,
    }
    measured = {"checks": checks, **loud, "video": {k: v[0].get(k) for k in ("codec_name", "width", "height", "r_frame_rate",
                                                                              "pix_fmt", "duration")} if v else None,
                "audio": {k: a[0].get(k) for k in ("codec_name", "sample_rate", "channels", "duration")} if a else None,
                "subtitle": sub[0].get("codec_name") if sub else None, "chapters": len(d.get("chapters", [])),
                "caption_cues": len(caps), "chapter_cues": len(chaps), "duration": float(d["format"]["duration"])}
    failed = [k for k, ok in checks.items() if not ok]
    return {"id": "video.media", "medium": "video", "status": "failed" if failed else "passed", "measured": measured,
            "reason": f"failed: {', '.join(failed)}" if failed else ""}


# ---------------------------------------------------------------- whisper sync

def whisper_words(media, work):
    """16 kHz mono WAV from the final media, then whisper-cli word timestamps (AC-0.3)."""
    ffmpeg = host.which("ffmpeg")
    whisper = host.which("whisper-cli")
    model = host.state_path("models", "whisper", "ggml-base.en.bin")
    work.mkdir(parents=True, exist_ok=True)
    wav = work / "speech-16k.wav"
    host.run([ffmpeg, "-v", "error", "-y", "-i", media, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le", wav],
             check=True, timeout=300)
    base = work / "whisper"
    host.run([whisper, "-m", model, "-f", wav, "-ojf", "-of", base, "-np", "-nfa", "--dtw", "base.en", "-l", "en"],
             check=True, timeout=900)
    data = json.loads((work / "whisper.json").read_text())
    words = []
    for seg in data["transcription"]:
        cur = None
        for tk in seg["tokens"]:
            tx = tk["text"]
            if tx.startswith("[_") or not tx.strip():
                continue
            t0, t1 = tk["offsets"]["from"] / 1000, tk["offsets"]["to"] / 1000
            dtw = tk.get("t_dtw", -1)
            start = dtw / 100 if dtw is not None and dtw >= 0 else t0
            if tx.startswith(" ") or cur is None:
                cur = {"text": tx.strip(), "start": round(start, 3), "end": round(t1, 3), "from": round(t0, 3)}
                words.append(cur)
            else:
                cur["text"] += tx
                cur["end"] = round(t1, 3)
    words = [w for w in words if re.search(r"[A-Za-z0-9]", w["text"])]
    return words, {"model": "ggml-base.en.bin", "model_sha256": host.sha256_file(model), "wav": wav.name,
                   "timestamps": "start = DTW token time (fallback segment offset), end = token end offset"}


def wer(ref, hyp):
    d = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        prev, d[0] = d[0], i
        for j, h in enumerate(hyp, 1):
            cur = min(d[j] + 1, d[j - 1] + 1, prev + (r != h))
            prev, d[j] = d[j], cur
    return d[len(hyp)] / max(len(ref), 1)


def silences(wav, noise="-40dB", min_d=0.12):
    ffmpeg = host.which("ffmpeg")
    res = host.run([ffmpeg, "-hide_banner", "-nostats", "-i", wav, "-af", f"silencedetect=n={noise}:d={min_d}", "-f", "null",
                    "-"], timeout=300)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", res.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", res.stderr)]
    return starts, ends


def refine(words_in_cue, starts, ends):
    """Speech onset/offset for one cue: whisper places the words, the audio's silence edges
    give the exact boundary (whisper segment edges snap into neighbouring silence)."""
    w0, w1 = words_in_cue[0], words_in_cue[-1]
    onset = max((e for e in ends if w0["start"] - 1.0 <= e <= w0["start"] + 0.3), default=w0["start"])
    anchor = max(w1["start"], w1["end"] - 0.6)
    offset = min((s for s in starts if anchor - 0.2 <= s <= w1["end"] + 1.0), default=w1["end"])
    return round(onset, 3), round(offset, 3)


def sync_gate(mp4, out_dir, timing, work):
    words, info = whisper_words(mp4, work)
    sil_starts, sil_ends = silences(work / "speech-16k.wav")
    info["boundaries"] = "onset/offset = nearest silencedetect edge (-40 dB, 0.12 s) around the whisper words"
    cues = timing["cues"]
    assigned = {c["id"]: [] for c in cues}
    for w in words:
        mid = (w["start"] + w["end"]) / 2
        best = min(cues, key=lambda c: 0 if c["start"] - 0.3 <= mid <= c["end"] + 0.3 else
                   min(abs(mid - c["start"]), abs(mid - c["end"])))
        assigned[best["id"]].append(w)
    rows, bad = [], []
    for c in cues:
        ws = assigned[c["id"]]
        if not ws:
            rows.append({"cue": c["id"], "error": "no words heard"})
            bad.append(c["id"])
            continue
        on, off = refine(ws, sil_starts, sil_ends)
        ds, de = on - c["start"], off - c["end"]
        row = {"cue": c["id"], "cue_start": c["start"], "speech_start": on, "start_delta": round(ds, 3),
               "cue_end": c["end"], "speech_end": off, "end_delta": round(de, 3), "words": len(ws),
               "whisper_first_word": ws[0]["start"], "whisper_last_word_end": ws[-1]["end"]}
        rows.append(row)
        if abs(ds) > SYNC_TOL or abs(de) > SYNC_TOL:
            bad.append(c["id"])
    code = tts.code_words()
    ref = [w for c in cues for w in text.norm_words(c["text"]) if w not in code]
    hyp = [w for x in words for w in text.norm_words(x["text"]) if w not in code]
    rate = wer(ref, hyp)
    ok = not bad and rate <= WER_MAX
    reason = []
    if bad:
        reason.append(f"cues out of sync by more than {SYNC_TOL}s: {', '.join(bad)}")
    if rate > WER_MAX:
        reason.append(f"non-code WER {rate:.3f} > {WER_MAX}")
    max_s = max((abs(r.get("start_delta", 99)) for r in rows), default=None)
    max_e = max((abs(r.get("end_delta", 99)) for r in rows), default=None)
    (work / "sync-words.json").write_text(json.dumps(words, indent=1))
    return {"id": "video.sync", "medium": "video", "status": "passed" if ok else "failed",
            "measured": {"cues": rows, "max_abs_start_delta": max_s, "max_abs_end_delta": max_e, "non_code_wer": round(rate, 4),
                         "ref_words": len(ref), "hyp_words": len(hyp), "whisper": info, "heard": " ".join(x["text"] for x in words)},
            "reason": "; ".join(reason)}


# ---------------------------------------------------------------- answer leaks (M20)

def answer_words(lesson, fact_id):
    return [ln.strip().lower() for ln in lesson.fact(fact_id)["value"].split("\n") if ln.strip()]


def leak_gate(lesson, timing, out_dir):
    """No answer word in captions/transcript before the answer cue, nor in any chapter title."""
    leaks, qs = [], []
    for sc in timing["scenes"]:
        if not sc.get("question"):
            continue
        ans_scene = next(s for s in timing["scenes"] if s["start"] > sc["start"])
        answer_at = ans_scene["reveal"]  # the answer cue: the first reveal after the question
        words = set(answer_words(lesson, sc["question"]["answer_fact"]))
        qs.append({"scene": sc["id"], "answer_cue": answer_at, "answer_words": sorted(words)})
        for c in parse_vtt(out_dir / "captions.vtt"):
            if c["start"] < answer_at - 0.01:
                hit = words & set(re.findall(r"[a-z']+", c["text"].lower()))
                if hit:
                    leaks.append({"where": "captions", "cue": c["id"], "words": sorted(hit)})
        for c in parse_vtt(out_dir / "chapters.vtt"):
            hit = words & set(re.findall(r"[a-z']+", c["text"].lower()))
            if hit:
                leaks.append({"where": "chapters", "title": c["text"], "words": sorted(hit)})
        tx = (out_dir / "transcript.txt").read_text()
        pre = [c["text"] for c in timing["cues"] if c["start"] < answer_at - 0.01]
        for line in pre:
            if line not in tx:
                leaks.append({"where": "transcript", "problem": "pre-answer line missing", "line": line})
    return {"id": "video.no-answer-leak", "medium": "video", "status": "failed" if leaks else ("passed" if qs else "not-run"),
            "measured": {"questions": qs, "leaks": leaks}, "reason": "answer stated before its cue" if leaks else
            ("" if qs else "no question in the storyboard")}
