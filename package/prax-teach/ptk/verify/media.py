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


def media_checks(info, loud, caps, chaps, timing):
    """AC-5.4 thresholds on already-measured values (pure, so out-of-range fixtures can be checked)."""
    v = [x for x in info["streams"] if x["codec_type"] == "video"]
    a = [x for x in info["streams"] if x["codec_type"] == "audio"]
    sub = [x for x in info["streams"] if x["codec_type"] == "subtitle"]
    return {
        "video_h264_1920x1080": bool(v) and v[0]["codec_name"] == "h264" and v[0]["width"] == 1920 and v[0]["height"] == 1080,
        "video_30fps": bool(v) and v[0]["r_frame_rate"] in ("30/1", "30000/1000"),
        "audio_aac": bool(a) and a[0]["codec_name"] == "aac",
        "captions_track_in_mp4": bool(sub) and sub[0]["codec_name"] == "mov_text",
        "chapters_in_mp4": len(info.get("chapters", [])) == len(timing["scenes"]),
        "captions_vtt": bool(caps) and len(caps) == len(timing["cues"]),
        "chapters_vtt": bool(chaps) and len(chaps) == len(timing["scenes"]),
        "loudness_in_range": abs(loud["integrated_lufs"] - LUFS_TARGET) <= LUFS_TOL,
        "true_peak_ok": loud["true_peak_dbtp"] <= TP_MAX,
        "av_duration_match": bool(v and a) and abs(float(v[0].get("duration", 0)) - float(a[0].get("duration", 0))) <= 0.1,
    }


def media_gate(mp4, out_dir, timing):
    d = probe(mp4)
    v = [s for s in d["streams"] if s["codec_type"] == "video"]
    a = [s for s in d["streams"] if s["codec_type"] == "audio"]
    sub = [s for s in d["streams"] if s["codec_type"] == "subtitle"]
    loud = loudness(mp4)
    caps = parse_vtt(out_dir / "captions.vtt") if (out_dir / "captions.vtt").exists() else []
    chaps = parse_vtt(out_dir / "chapters.vtt") if (out_dir / "chapters.vtt").exists() else []
    checks = media_checks(d, loud, caps, chaps, timing)
    measured = {"checks": checks, **loud, "video": {k: v[0].get(k) for k in ("codec_name", "width", "height", "r_frame_rate",
                                                                              "pix_fmt", "duration")} if v else None,
                "audio": {k: a[0].get(k) for k in ("codec_name", "sample_rate", "channels", "duration")} if a else None,
                "subtitle": sub[0].get("codec_name") if sub else None, "chapters": len(d.get("chapters", [])),
                "caption_cues": len(caps), "chapter_cues": len(chaps), "duration": float(d["format"]["duration"]),
                "thresholds": {"lufs": [LUFS_TARGET - LUFS_TOL, LUFS_TARGET + LUFS_TOL], "true_peak_max": TP_MAX}}
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
                cur = {"text": tx.strip(), "start": round(start, 3), "end": round(max(t1, start), 3), "from": round(t0, 3)}
                words.append(cur)
            else:
                cur["text"] += tx
                cur["end"] = round(max(t1, cur["start"]), 3)
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
    # whisper stretches the last token of a segment across the silence after it (its DTW start stays put): a
    # "word" longer than a second is that stretch, so its end says nothing about where the speech stops
    stretched = w1["end"] - w1["start"] > 1.0
    anchor = w1["start"] if stretched else max(w1["start"], w1["end"] - 0.6)
    last = w1["start"] + 1.0 if stretched else w1["end"] + 1.0
    offset = min((s for s in starts if anchor - 0.2 <= s <= last), default=w1["end"])
    return round(onset, 3), round(offset, 3)


def _count_seq(words, seq):
    return sum(1 for i in range(len(words) - len(seq) + 1) if words[i:i + len(seq)] == seq)


def mispronounced(said, heard_words):
    """Code tokens in a cue (lexicon, before respelling) that whisper did not hear as one of the
    token's accepted forms, as often as the line says them (E17 mispronounced-token fixture)."""
    out = []
    for tk in tts.code_tokens(said):
        got = sum(_count_seq(heard_words, h) for h in tk["heard"])
        if got < tk["count"]:
            out.append({"token": tk["token"], "said": tk["count"], "heard_ok": got,
                        "accepted": [" ".join(h) for h in tk["heard"]]})
    return out


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
    rows, bad, bad_tokens = [], [], []
    for c in cues:
        ws = assigned[c["id"]]
        if not ws:
            rows.append({"cue": c["id"], "error": "no words heard"})
            bad.append(c["id"])
            continue
        heard = [x for w in ws for x in text.norm_words(w["text"])]
        said = c.get("said") or c["text"]
        mis = mispronounced(said, heard)
        on, off = refine(ws, sil_starts, sil_ends)
        ds, de = on - c["start"], off - c["end"]
        row = {"cue": c["id"], "cue_start": c["start"], "speech_start": on, "start_delta": round(ds, 3),
               "cue_end": c["end"], "speech_end": off, "end_delta": round(de, 3), "words": len(ws),
               "whisper_first_word": ws[0]["start"], "whisper_last_word_end": ws[-1]["end"]}
        if mis:
            row["mispronounced"] = mis
            bad_tokens.append({"cue": c["id"], "tokens": mis})
        rows.append(row)
        if abs(ds) > SYNC_TOL or abs(de) > SYNC_TOL:
            bad.append(c["id"])
    code = tts.code_words()
    ref = [w for c in cues for w in text.norm_words(c["text"]) if w not in code]
    hyp = [w for x in words for w in text.norm_words(x["text"]) if w not in code]
    rate = wer(ref, hyp)
    ok = not bad and rate <= WER_MAX and not bad_tokens
    reason = []
    if bad_tokens:
        reason.append("code tokens not heard as their lexicon forms: " +
                      ", ".join(f"{b['cue']} {[m['token'] for m in b['tokens']]}" for b in bad_tokens))
    if bad:
        reason.append(f"cues out of sync by more than {SYNC_TOL}s: {', '.join(bad)}")
    if rate > WER_MAX:
        reason.append(f"non-code WER {rate:.3f} > {WER_MAX}")
    max_s = max((abs(r.get("start_delta", 99)) for r in rows), default=None)
    max_e = max((abs(r.get("end_delta", 99)) for r in rows), default=None)
    (work / "sync-words.json").write_text(json.dumps(words, indent=1))
    return {"id": "video.sync", "medium": "video", "status": "passed" if ok else "failed",
            "measured": {"cues": rows, "mispronounced": bad_tokens, "max_abs_start_delta": max_s, "max_abs_end_delta": max_e, "non_code_wer": round(rate, 4),
                         "ref_words": len(ref), "hyp_words": len(hyp), "whisper": info, "heard": " ".join(x["text"] for x in words)},
            "reason": "; ".join(reason)}


# ---------------------------------------------------------------- answer leaks (M20)
#
# Leak rule (AC-5.7, review P2-5), applied to narration/captions, the transcript up to the answer
# cue, and every chapter title:
#   * a word answer line ("two", "x = 2") leaks wherever its words appear as a phrase;
#   * a numeric answer line ("66", "0x42", "-1") leaks only when the value appears as a number
#     (digits or number words) in a sentence that refers to the question's subject, and not
#     incidentally: inside `code` or "quotes", or as a line/column/step/scene/chapter/page number.
#   The subject is the content words of the question's interrogative sentence (plus print/output
#   synonyms), compared on crude stems.

_UNITS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90}
_INCIDENTAL = {"line", "lines", "column", "columns", "step", "steps", "scene", "scenes", "chapter", "chapters", "page",
               "pages", "row", "rows"}
_STOP = {"what", "which", "who", "whom", "whose", "when", "where", "why", "how", "does", "do", "did", "is", "are", "was",
         "were", "the", "a", "an", "this", "that", "these", "those", "it", "its", "of", "to", "in", "on", "for", "and",
         "or", "be", "will", "would", "can", "could", "should", "has", "have", "had", "with", "as", "at", "by", "from",
         "after", "before", "then", "now", "you", "your", "we", "our", "value", "values"}
_SYN = {"print": {"print", "output", "show", "display", "write"}, "output": {"print", "output", "show", "display"}}
NUMERIC = re.compile(r"-?(?:0x[0-9a-f]+|\d+(?:\.\d+)?)")


def _stem(w):
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def _num_tokens(sentence):
    """Number values in a sentence, with whether each is incidental: [(value, incidental)]."""
    s = sentence.lower()
    code = [(m.start(), m.end()) for m in re.finditer(r"`[^`]*`|\"[^\"]*\"", s)]
    toks = [(m.group(0), m.start()) for m in re.finditer(r"-?0x[0-9a-f]+|-?\d+(?:\.\d+)?|[a-z]+", s.replace("-", " "))]
    out, i = [], 0
    while i < len(toks):
        w, pos = toks[i]
        val, j = None, i
        if NUMERIC.fullmatch(w):
            val, j = w, i + 1
        elif w in _UNITS or w in _TENS:
            n = _TENS.get(w, _UNITS.index(w) if w in _UNITS else 0)
            j = i + 1
            if w in _TENS and j < len(toks) and toks[j][0] in _UNITS[1:10]:
                n += _UNITS.index(toks[j][0])
                j += 1
            if j < len(toks) and toks[j][0] == "hundred":
                n *= 100
                j += 1
                if j < len(toks) and (toks[j][0] in _UNITS or toks[j][0] in _TENS):
                    n += _TENS.get(toks[j][0], _UNITS.index(toks[j][0]) if toks[j][0] in _UNITS else 0)
                    j += 1
            val = str(n)
        if val is None:
            i += 1
            continue
        prev = toks[i - 1][0] if i else ""
        incidental = prev in _INCIDENTAL or any(a <= pos < b for a, b in code)
        out.append((val, incidental))
        i = j
    return out


def _norm_num(v):
    v = v.lower()
    if v.startswith("0x") or v.startswith("-0x"):
        return str(int(v, 16))
    return str(float(v)).rstrip("0").rstrip(".") if "." in v else str(int(v))


def subject_terms(prompt):
    asks = [x for x in text.sentences(prompt) if x.rstrip().endswith("?")] or [prompt]
    words = {_stem(w) for w in re.findall(r"[a-z]+", asks[-1].lower()) if w not in _STOP and len(w) > 1}
    for w in list(words):
        words |= _SYN.get(w, set())
    return words


def answer_parts(lesson, fact_id):
    """[{"kind": "words", "phrase": [...]} | {"kind": "number", "value": "66"}] from the answer fact's lines."""
    out = []
    for ln in lesson.fact(fact_id)["value"].split("\n"):
        ln = ln.strip()
        if not ln:
            continue
        if NUMERIC.fullmatch(ln.lower()):
            out.append({"kind": "number", "value": _norm_num(ln)})
        else:
            out.append({"kind": "words", "phrase": re.findall(r"[a-z0-9']+", ln.lower())})
    return out


def answer_words(lesson, fact_id):
    return [" ".join(p["phrase"]) if p["kind"] == "words" else p["value"] for p in answer_parts(lesson, fact_id)]


def leaks_in(line, parts, subject):
    """The answer parts a displayed line states, by the leak rule above."""
    hits = []
    for sent in text.sentences(line) or [line]:
        words = re.findall(r"[a-z0-9']+", sent.lower())
        about = bool({_stem(w) for w in words} & subject)
        nums = _num_tokens(sent)
        for p in parts:
            if p["kind"] == "words":
                if p["phrase"] and _count_seq(words, p["phrase"]):
                    hits.append(" ".join(p["phrase"]))
            elif about and any(_norm_num(v) == p["value"] for v, inc in nums if not inc):
                hits.append(p["value"])
    return sorted(set(hits))


def leak_gate(lesson, timing, out_dir):
    """No answer in narration/captions or the transcript before the answer cue, nor in any chapter title."""
    leaks, qs = [], []
    caps = parse_vtt(out_dir / "captions.vtt")
    chaps = parse_vtt(out_dir / "chapters.vtt")
    tx_lines = [ln for ln in (out_dir / "transcript.txt").read_text().split("\n") if ln.strip()]
    for sc in timing["scenes"]:
        if not sc.get("question"):
            continue
        ans_scene = next(s for s in timing["scenes"] if s["start"] > sc["start"])
        answer_at = ans_scene["reveal"]  # the answer cue: the first reveal after the question
        parts = answer_parts(lesson, sc["question"]["answer_fact"])
        subject = subject_terms(sc["question"]["prompt"])
        qs.append({"scene": sc["id"], "answer_cue": answer_at, "answer": parts, "subject": sorted(subject)})
        for c in caps:
            if c["start"] < answer_at - 0.01:
                hit = leaks_in(c["text"], parts, subject)
                if hit:
                    leaks.append({"where": "captions", "cue": c["id"], "answer": hit})
        for c in timing["cues"]:
            if c["start"] < answer_at - 0.01:
                hit = leaks_in(c["text"], parts, subject)
                if hit:
                    leaks.append({"where": "narration", "cue": c["id"], "answer": hit})
        for c in chaps:
            hit = leaks_in(c["text"], parts, subject)
            if hit:
                leaks.append({"where": "chapters", "title": c["text"], "answer": hit})
        pre = [c["text"] for c in timing["cues"] if c["start"] < answer_at - 0.01]
        for line in pre:
            if line not in tx_lines:
                leaks.append({"where": "transcript", "problem": "pre-answer line missing", "line": line})
        # the transcript up to the answer cue: its lines in order until the first post-answer narration line
        post = {c["text"] for c in timing["cues"] if c["start"] >= answer_at - 0.01}
        for line in tx_lines:
            if line in post:
                break
            hit = leaks_in(re.sub(r"^\[[\d:.]+\] ", "", line), parts, subject)
            if hit:
                leaks.append({"where": "transcript", "line": line, "answer": hit})
    return {"id": "video.no-answer-leak", "medium": "video", "status": "failed" if leaks else ("passed" if qs else "not-run"),
            "measured": {"questions": qs, "leaks": leaks, "rule": "words answers as phrases anywhere; numeric answers "
                         "only as the value in a sentence about the question's subject, not in code or line numbers"},
            "reason": "answer stated before its cue" if leaks else ("" if qs else "no question in the storyboard")}
