"""AC-10.5 (SPEC v1.4 WP10): narration pace, hedges, repeats, the "unsigned char" reading, and values on
screen when they are spoken.

  pace        per narration line, words per minute <= 170, measured from the final audio. The MP4's track is
              resampled to 16 kHz mono and silencedetect (-40 dB, 0.12 s) finds the silences. The line's window
              runs between the midpoints of the gaps to its neighbours (the planned timeline only separates lines;
              the last window ends where the audio track ends);
              speech starts where the first silence in the window ends and stops where the last one begins, so
              pauses inside a line count. Words are the TTS input (the spoken form): whitespace tokens, hyphenated
              parts counted apart, numbers counted as read aloud ("66" is 2, "1.5" is 3). The whisper word span
              and the planned-timeline rate are reported beside it, never gated.
  hedges      no phrase from HEDGES in a narration sentence, unless the closed allowlist exempts it: only "on this
              machine", only in a sentence that is a sentence of one of the line's claims, only when that claim
              lists the phrase in "needs_hedge" (a lesson schema field the claims job shows to reviewers) and cites
              a platform fact.
  repeats     no sentence (ptk.text.sentences, lowercased, spacing and end punctuation ignored) appears twice
              in a lesson's narration.
  unsigned char  for every line whose text says "unsigned char": the TTS input never reads "unsigned car" (the
              built `spoken` form and the current lexicon's transform), and whisper hears "unsigned char" in that
              line's window as often as the text says it.
  lexicon     every lexicon token the narration uses: the TTS input equals the current lexicon's transform of the
              text, and whisper hears each code token in one of its accepted forms as often as the line says it.
  values      a number in a narration line that equals a captured value (any number in a fact's captured value;
              line, case, step and scene numbers excepted) is on screen within 0.5 s after it is spoken, drawn by an
              element whose data-fact or data-m names a captured fact holding that number, or in the code listing
              when the number is a literal of the program source ("stores 66" and int a = 66;). A spoken number that
              is neither a captured value nor a source literal fails. The spoken time is whisper's time for that word when
              whisper wrote it as digits, else its position in the line's measured speech span.
"""
import json
import re
import shutil

import _b0
from ptk import host, text, tts
from ptk.verify import media

MAX_WPM = 170.0
HEDGES = ("in this lesson's drawing", "on this machine", "basically", "it's worth noting", "as you can see", "simply")
VALUE_SLACK = 0.5
INCIDENTAL = {"line", "lines", "column", "columns", "step", "steps", "scene", "scenes", "chapter", "page", "case", "cases"}
NUM_RE = re.compile(r"(?<![\w.])[-+−]?(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?)(?![\w]|\.\d)")


# ---------------------------------------------------------------- pace

def windows(cues, duration):
    out = []
    for i, c in enumerate(cues):
        lo = 0.0 if i == 0 else (cues[i - 1]["end"] + c["start"]) / 2
        hi = duration if i == len(cues) - 1 else (c["end"] + cues[i + 1]["start"]) / 2
        out.append((lo, hi))
    return out


def speech_span(lo, hi, spans):
    """(onset, offset) of the sound inside [lo, hi] given silence spans, or None when the window is silent."""
    on, off = lo, hi
    for s, e in spans:
        if s <= on < e:
            on = e
    for s, e in sorted(spans, reverse=True):
        if s < off <= e:
            off = s
    return (on, off) if off > on else None


def pace_rows(cues, starts, ends, duration, words=None):
    spans = media.silence_spans(starts, ends)
    rows = []
    for c, (lo, hi) in zip(cues, windows(cues, duration)):
        said = c.get("spoken") or tts.apply_lexicon(c["text"])
        n = _b0.spoken_word_count(said)
        sp = speech_span(lo, hi, spans)
        row = {"cue": c["id"], "words": n, "words_unexpanded": len(said.split()), "window": [round(lo, 3), round(hi, 3)],
               "planned_wpm": round(n / max(c["end"] - c["start"], 1e-6) * 60, 1)}
        if not sp:
            row["error"] = "no speech found in the window"
        else:
            row.update({"speech": [round(sp[0], 3), round(sp[1], 3)], "seconds": round(sp[1] - sp[0], 3),
                        "wpm": round(n / (sp[1] - sp[0]) * 60, 1),
                        "wpm_unexpanded_info": round(row["words_unexpanded"] / (sp[1] - sp[0]) * 60, 1)})
        if words is not None:
            ws = [w for w in words if lo <= (w["start"] + w["end"]) / 2 < hi]
            row["whisper_words"] = len(ws)
            if len(ws) >= 2 and ws[-1]["end"] > ws[0]["start"]:
                row["whisper_wpm"] = round(n / (ws[-1]["end"] - ws[0]["start"]) * 60, 1)
        rows.append(row)
    return rows


def pace_problems(rows):
    out = []
    for r in rows:
        if r.get("error"):
            out.append({"kind": "no-speech", "cue": r["cue"]})
        elif r["wpm"] > MAX_WPM:
            out.append({"kind": "too-fast", "cue": r["cue"], "wpm": r["wpm"], "words": r["words"], "seconds": r["seconds"]})
    return out


# ---------------------------------------------------------------- hedges, repeats, pronunciation

def _hedge_re(ph):
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(w) for w in ph.split()) + r"(?!\w)", re.I)


HEDGE_ALLOWED = {"on this machine"}  # the only phrase a claim may ask for, and only for a platform fact


def _plain(s):
    return s.replace("\u2019", "'")


def hedge_exempt(ph, sentence, cue, claims, facts):
    """A hedge in one narration sentence is allowed only when that sentence is a sentence of one of the line's
    claims, that claim lists the phrase in needs_hedge, the phrase is on the closed allowlist, and the claim cites
    a platform fact (select.stream == "platform")."""
    if ph not in HEDGE_ALLOWED:
        return False
    key = _sent_key(_plain(sentence))
    for cid in cue.get("claims", []):
        cl = claims.get(cid) or {}
        if ph not in {h.lower() for h in cl.get("needs_hedge", [])}:
            continue
        if not any(((facts.get(f) or {}).get("select") or {}).get("stream") == "platform" for f in cl.get("facts", [])):
            continue
        if any(_sent_key(_plain(x)) == key and _hedge_re(ph).search(_plain(x)) for x in text.sentences(cl.get("text", ""))):
            return True
    return False


def hedge_problems(cues, claims, facts=None):
    out = []
    for c in cues:
        for sent in text.sentences(c["text"]):
            for ph in HEDGES:
                if _hedge_re(ph).search(_plain(sent)) and not hedge_exempt(ph, sent, c, claims, facts or {}):
                    out.append({"kind": "hedge", "cue": c["id"], "phrase": ph, "text": sent[:120]})
    return out


def _sent_key(s):
    return re.sub(r"[\s.!?]+$", "", re.sub(r"\s+", " ", s.strip().lower()))


def repeat_problems(cues):
    seen, out = {}, []
    for c in cues:
        for s in text.sentences(c["text"]):
            k = _sent_key(s)
            if k in seen:
                out.append({"kind": "repeated-sentence", "cues": [seen[k], c["id"]], "sentence": s[:120]})
            else:
                seen[k] = c["id"]
    return out


UC = re.compile(r"\bunsigned\s+char\b", re.I)
UCAR = re.compile(r"\bunsigned\s+car\b", re.I)


def _count_seq(words, seq):
    return sum(1 for i in range(len(words) - len(seq) + 1) if words[i:i + len(seq)] == seq)


def unsigned_char_problems(cues, heard_by_cue):
    """heard_by_cue: {cue id: whisper words (text.norm_words) in that line's window}, or None to skip whisper."""
    out, rows = [], []
    for c in cues:
        n = len(UC.findall(c["text"]))
        if not n:
            continue
        spoken, current = c.get("spoken") or "", tts.apply_lexicon(c["text"])
        heard = (heard_by_cue or {}).get(c["id"], [])
        got = _count_seq(heard, ["unsigned", "char"])
        rows.append({"cue": c["id"], "said": n, "spoken": spoken, "current_lexicon": current, "heard_ok": got,
                     "heard": " ".join(heard)})
        if UCAR.search(spoken):
            out.append({"kind": "tts-input-says-car", "cue": c["id"], "spoken": spoken[:120]})
        if UCAR.search(current):
            out.append({"kind": "lexicon-says-car", "cue": c["id"], "current": current[:120]})
        if heard_by_cue is not None and got < n:
            out.append({"kind": "heard-wrong", "cue": c["id"], "said": n, "heard_ok": got,
                        "heard": " ".join(heard)[:160]})
    return out, rows


def lexicon_problems(cues, heard_by_cue):
    """Every lexicon token the narration uses: the TTS input is the current lexicon's transform of the text, and
    whisper hears each code token in one of its accepted forms as often as the line says it."""
    out = []
    for c in cues:
        want = tts.apply_lexicon(c["text"])
        if (c.get("spoken") or "") != want:
            out.append({"kind": "lexicon-not-applied", "cue": c["id"], "spoken": (c.get("spoken") or "")[:120], "lexicon": want[:120]})
        if heard_by_cue is not None:
            for m in media.mispronounced(c["text"], heard_by_cue.get(c["id"], [])):
                out.append({"kind": "lexicon-heard-wrong", "cue": c["id"], **m})
    return out


# ---------------------------------------------------------------- values on screen

def norm_val(s):
    return s.replace("−", "-").lstrip("+").lower()


def value_tokens(v):
    """Normalised numbers in a captured value: the whole line when it is a number, and each number in it."""
    out = set()
    for line in (v or "").split("\n"):
        if NUM_RE.fullmatch(line.strip()):
            out.add(norm_val(line.strip()))
        out |= {norm_val(x) for x in NUM_RE.findall(line)}
    return out


def captured_values(data, capture_dir):
    """{fact id: its normalised numbers} for every captured fact."""
    vals, _drift = _b0.captured_facts(data, capture_dir)
    return {fid: value_tokens(v) for fid, v in vals.items() if v is not None}


def spoken_values(cue, values, literals=frozenset()):
    """([(token, index of its word, word count)] for numbers in the written line that are captured values,
    [numbers that are neither captured values nor source literals]). Line, case, step and scene numbers skip."""
    t = cue["text"]
    words = t.split()
    out, stray = [], []
    pool = set().union(*values.values()) if values else set()
    for m in NUM_RE.finditer(t):
        before = t[:m.start()].split()
        if before and before[-1].lower().strip("(,") in INCIDENTAL:
            continue
        v = norm_val(m.group(0))
        if v in pool:
            out.append((m.group(0), len(before), max(1, len(words))))
        elif v not in literals:
            stray.append(m.group(0))
    return out, stray


def screen_values(m, values):
    """Normalised numbers on screen: (drawn by an element bound to a captured fact that holds the number, drawn in
    the code listing). Unbound text, line numbers, step badges and the chapter count never count."""
    out, code = set(), set()
    for it in m.get("items", []):
        if it["k"] != "text" or it.get("o", 1) < 0.5:
            continue
        if it.get("label") in ("line-number", "output-step", "chapter-count"):
            continue
        nums = {norm_val(x) for x in NUM_RE.findall(it["t"])}
        if it.get("key") == "code" or it.get("srcline"):
            code |= nums
        elif it.get("fact") in values:
            out |= nums & values[it["fact"]]
    return out, code


def source_literals(sources):
    return {norm_val(x) for src in sources for x in NUM_RE.findall(src)}


def value_samples(cues, rows, words, values):
    samples, wants = [], []
    for c, r in zip(cues, rows):
        if not r.get("speech"):
            continue
        ws = [w for w in words if r["window"][0] <= (w["start"] + w["end"]) / 2 < r["window"][1]]
        used = set()
        for tok, idx, total in spoken_values(c, values)[0]:
            hit = next((i for i, w in enumerate(ws) if i not in used and norm_val(w["text"].strip(".,;:!?")) == norm_val(tok)), None)
            if hit is not None:
                used.add(hit)
                t, how = ws[hit]["start"], "whisper"
            else:
                on, off = r["speech"]
                t, how = on + (off - on) * idx / total, "position"
            at = min(t + VALUE_SLACK, r["window"][1] - 0.01)
            label = f"{c['id']}:{tok}@{at:.3f}"
            samples.append((label, at))
            wants.append({"label": label, "cue": c["id"], "value": tok, "spoken_at": round(t, 3), "how": how})
    return samples, wants


def value_problems(wants, frames, values, literals=frozenset()):
    """A spoken value must be drawn by an element bound (data-fact or data-m) to a captured fact that holds it; a
    value that is a literal in the program source ("stores 66" for int a = 66;) may be seen in the code listing
    instead."""
    out = []
    for w in wants:
        m = frames.get(w["label"]) or {}
        if m.get("error"):
            out.append({"kind": "frame-probe-failed", **w, "error": m["error"]})
            continue
        v = norm_val(w["value"])
        shown, in_code = screen_values(m, values)
        if v not in shown and not (v in literals and v in in_code):
            out.append({"kind": "value-not-on-screen", **w})
    return out


def stray_problems(cues, values, literals):
    out = []
    for c in cues:
        stray = spoken_values(c, values, literals)[1]
        if stray:
            out.append({"kind": "uncaptured-number", "cue": c["id"], "numbers": stray, "text": c["text"][:120]})
    return out


# ---------------------------------------------------------------- fixtures

def _tone_wav(path, parts):
    """parts: [("tone"|"gap", seconds)] concatenated into a 16 kHz mono WAV."""
    args, labels = [], []
    for i, (kind, d) in enumerate(parts):
        src = f"sine=frequency=220:sample_rate=16000:duration={d}" if kind == "tone" else \
              f"anullsrc=r=16000:cl=mono,atrim=duration={d}"
        args += ["-f", "lavfi", "-i", src]
        labels.append(f"[{i}:a]")
    flt = "".join(labels) + f"concat=n={len(parts)}:v=0:a=1[a]"
    host.run([host.which("ffmpeg"), "-v", "error", "-y", *args, "-filter_complex", flt, "-map", "[a]", "-ac", "1",
              "-ar", "16000", str(path)], check=True, timeout=120)


def test_fixture_pace_from_audio():
    """Synthetic audio: a 5-word line over 2.5 s of sound (120 wpm) passes; a 10-word line squeezed into 2.0 s
    (300 wpm) fails, although the planned timeline gives it 4 s (150 wpm), so the plan cannot hide it."""
    tmp = host.make_tmp("b0-pace-")
    try:
        wav = tmp / "fx.wav"
        _tone_wav(wav, [("gap", 0.5), ("tone", 2.5), ("gap", 1.0), ("tone", 2.0), ("gap", 0.5)])
        cues = [{"id": "a", "text": "one two three four five", "spoken": "one two three four five", "start": 0.5, "end": 3.0},
                {"id": "b", "text": "w " * 10, "spoken": "a b c d e f g h i j", "start": 3.5, "end": 7.5}]
        starts, ends = media.silences(wav)
        rows = pace_rows(cues, starts, ends, 6.5)
        probs = pace_problems(rows)
        assert [p["cue"] for p in probs] == ["b"], (rows, probs)
        assert abs(rows[0]["wpm"] - 120) < 6 and rows[1]["wpm"] > 280 and rows[1]["planned_wpm"] <= 170, rows
        return rows
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_fixture_word_count():
    """Numbers count as read aloud and hyphenated respellings count each part."""
    got = {s: _b0.spoken_word_count(s) for s in ("66", "1.5", "-0.4", "4294967295", "print-f does", "0 1 0 0")}
    assert got == {"66": 2, "1.5": 3, "-0.4": 4, "4294967295": 16, "print-f does": 3, "0 1 0 0": 4}, got
    return got


def test_fixture_hedges_and_repeats():
    """Hedges are caught unless the closed allowlist exempts them: "on this machine" in the very sentence of a claim
    that cites a platform fact and asks for it. A verbatim repeat is caught; clean lines pass."""
    facts = {"f.size": {"select": {"stream": "platform", "key": "sizeof.int"}}, "f.out": {"select": {"stream": "stdout"}}}
    claims = {"c.size": {"text": "On this machine int is 4 bytes.", "facts": ["f.size"], "needs_hedge": ["on this machine"]},
              "c.bits": {"text": "On this machine the bits differ.", "facts": ["f.out"], "needs_hedge": ["on this machine"]},
              "c.easy": {"text": "It simply prints 66.", "facts": ["f.out"], "needs_hedge": ["simply"]},
              "c.x": {"text": "a is 66.", "facts": ["f.out"]}}
    bad = [{"id": "s1", "text": "As you can see, a is 66. On this machine int is 4 bytes.", "claims": ["c.x"]},
           {"id": "s2", "text": "On this machine int is 4 bytes.", "claims": ["c.size"]},
           {"id": "s3", "text": "It simply prints 66. As you can see, a is 66.", "claims": ["c.easy"]},
           {"id": "s4", "text": "On this machine the bits differ.", "claims": ["c.bits"]},
           {"id": "s5", "text": "On this machine, int holds 4 bytes.", "claims": ["c.size"]}]
    h = hedge_problems(bad, claims, facts)
    assert sorted((p["cue"], p["phrase"]) for p in h) == [
        ("s1", "as you can see"), ("s1", "on this machine"), ("s3", "as you can see"), ("s3", "simply"),
        ("s4", "on this machine"), ("s5", "on this machine")], h
    r = repeat_problems(bad)
    assert [(p["cues"], p["sentence"]) for p in r] == [(["s1", "s2"], "On this machine int is 4 bytes."),
                                                      (["s1", "s3"], "As you can see, a is 66.")], r
    good = [{"id": "g1", "text": "The program stores 66 in a.", "claims": ["c.x"]},
            {"id": "g2", "text": "Then it prints 66 four ways.", "claims": ["c.x"]}]
    assert not hedge_problems(good, claims, facts) and not repeat_problems(good)
    return {"hedges": len(h), "repeats": len(r)}


def test_needs_hedge_in_schema_and_claims_job():
    """needs_hedge is a schema field with a closed list, and the claims job shows it to the reviewers."""
    import copy
    from ptk import model
    from ptk.verify import claims as claims_gate
    slug = "one-byte-four-views"
    if not (_b0.lesson_dir(slug) / "lesson.json").is_file():
        raise _b0.NotRun("needs a lesson to copy")
    base = _b0.load(slug)
    data = copy.deepcopy(base.data)
    cl = next(c for c in data["claims"] if "on this machine" in c["text"].lower())
    cl["needs_hedge"] = ["on this machine"]
    assert not model.schema_errors(data), model.schema_errors(data)[:2]
    body = claims_gate._job_body(model.Lesson(base.path, data), [])
    assert next(c for c in body["claims"] if c["id"] == cl["id"]).get("needs_hedge") == ["on this machine"]
    cl["needs_hedge"] = ["simply"]
    assert model.schema_errors(data), "a phrase outside the closed list must be a schema error"
    return cl["id"]


def test_fixture_lexicon_tokens():
    """A line whose TTS input is not the lexicon's transform, or whose code token whisper did not hear in an
    accepted form, fails; the lexicon's own reading heard correctly passes."""
    line = "printf prints 66."
    good = [{"id": "l1", "text": line, "spoken": tts.apply_lexicon(line)}]
    assert not lexicon_problems(good, {"l1": text.norm_words("print f prints 66")})
    bad = [{"id": "l1", "text": line, "spoken": "printf prints 66."}]
    kinds = {p["kind"] for p in lexicon_problems(bad, {"l1": text.norm_words("printing prints 66")})}
    assert kinds == {"lexicon-not-applied", "lexicon-heard-wrong"}, kinds
    return sorted(kinds)


def test_fixture_unsigned_char():
    """"unsigned car" in the TTS input or in what whisper heard fails; "unsigned char" in both passes."""
    line = "%c converts the int 66 to unsigned char and writes that character."
    bad = [{"id": "c1", "text": line, "spoken": "percent c converts the int 66 to unsigned car and writes that character."}]
    probs, _ = unsigned_char_problems(bad, {"c1": text.norm_words("percent c converts the int 66 to unsigned car")})
    kinds = {p["kind"] for p in probs}
    assert {"tts-input-says-car", "heard-wrong"} <= kinds, probs
    good = [{"id": "c1", "text": line, "spoken": "percent c converts the int 66 to unsigned char and writes that character."}]
    probs, _ = unsigned_char_problems(good, {"c1": text.norm_words("percent c converts the int 66 to unsigned char and")})
    assert not [p for p in probs if p["kind"] != "lexicon-says-car"], probs
    return sorted(kinds)


def test_fixture_values_on_screen():
    """A spoken value drawn by an element bound to a fact that holds it passes. Drawn only in the code listing,
    faded out, drawn as unbound text, or bound to a fact that does not hold it, it fails. A number that is
    neither captured nor a source literal is flagged."""
    vals = {"f.z": {"0.6"}, "f.t1": {"1.2"}, "f.d": {"66"}}
    cue = {"id": "s", "text": "z prints as 0.6 on line 13, a is 66 and the double is 66.0.", "start": 0.0, "end": 3.0}
    sv, stray = spoken_values(cue, vals)
    assert [v[0] for v in sv] == ["0.6", "66"] and stray == ["66.0"], (sv, stray)
    wants = [{"label": k, "value": v} for k, v in (("a", "0.6"), ("b", "66"), ("c", "66"), ("d", "1.2"), ("e", "66"), ("f", "66"))]
    item = lambda t, **k: {"k": "text", "t": t, "o": k.get("o", 1), "key": k.get("key"), "label": None, "fact": k.get("fact")}
    frames = {"a": {"items": [item("z = 0.6", fact="f.z")]}, "b": {"items": [item("int a = 66;", key="code")]},
              "c": {"items": [item("66", o=0.1, fact="f.d")]}, "d": {"items": [item("+1.2", fact="f.t1")]},
              "e": {"items": [item("66")]}, "f": {"items": [item("66", fact="f.z")]}}
    probs = value_problems(wants, frames, vals)
    assert [p["label"] for p in probs] == ["b", "c", "e", "f"], probs
    # the code-only 66 passes when 66 is a literal of the program source, and 66.0 is no longer stray if it is one
    assert [p["label"] for p in value_problems(wants, frames, vals, source_literals(["int a = 66;"]))] == ["c", "e", "f"]
    assert not stray_problems([cue], vals, source_literals(["double d = 66.0;"]))
    return [p["label"] for p in probs]


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "video/lesson.mp4", "video/timing.json", "video/composition", "capture")
    lesson = _b0.load(slug)
    timing = json.loads((b / "video" / "timing.json").read_text())
    cues = timing["cues"]
    claims = {c["id"]: c for c in lesson.data.get("claims", [])}
    work = host.make_tmp(f"b0-narr-{slug}-")
    try:
        words, winfo = media.whisper_words(b / "video" / "lesson.mp4", work)
        starts, ends = media.silences(work / "speech-16k.wav")
        audio_end = float(media.probe(work / "speech-16k.wav")["format"]["duration"])
    finally:
        shutil.rmtree(work, ignore_errors=True)
    # the last line's window ends where the audio ends (the film may run on silently after it)
    duration = min(timing.get("duration") or cues[-1]["end"] + 1, audio_end)
    rows = pace_rows(cues, starts, ends, duration, words)
    heard = {}
    for c, (lo, hi) in zip(cues, windows(cues, duration)):
        heard[c["id"]] = [x for w in words if lo <= (w["start"] + w["end"]) / 2 < hi for x in text.norm_words(w["text"])]
    pron, pron_rows = unsigned_char_problems(cues, heard)
    values = captured_values(lesson.data, b / "capture")
    samples, wants = value_samples(cues, rows, words, values)
    frames = _b0.probe_video(b / "video", timing, samples, f"narr-{slug}", lesson.sha256()) if samples else {}
    literals = source_literals(lesson.program_source(p["id"]) for p in lesson.data["programs"])
    facts = {f["id"]: f for f in lesson.data.get("facts", [])}
    probs = (pace_problems(rows) + hedge_problems(cues, claims, facts) + repeat_problems(cues) + pron
             + lexicon_problems(cues, heard) + value_problems(wants, frames, values, literals)
             + stray_problems(cues, values, literals))
    wpm = [r["wpm"] for r in rows if "wpm" in r]
    summary = {"cues": len(cues), "max_wpm": max(wpm, default=None),
               "max_wpm_unexpanded_info": max((r.get("wpm_unexpanded_info", 0) for r in rows), default=None), "median_wpm": sorted(wpm)[len(wpm) // 2] if wpm else None,
               "cues_over_170": sum(1 for w in wpm if w > MAX_WPM),
               "hedges": sum(1 for p in probs if p["kind"] == "hedge"),
               "repeats": sum(1 for p in probs if p["kind"] == "repeated-sentence"),
               "unsigned_char_lines": len(pron_rows), "unsigned_char_problems": len(pron),
               "lexicon_problems": sum(1 for p in probs if p["kind"] in ("lexicon-not-applied", "lexicon-heard-wrong")),
               "values_checked": len(wants), "values_missing": sum(1 for p in probs if p["kind"] == "value-not-on-screen"),
               "uncaptured_numbers": [n for p in probs if p["kind"] == "uncaptured-number" for n in p["numbers"]]}
    rec = _b0.record(f"ac10.5-{slug}", {"lesson": slug, "summary": summary, "pace": rows, "unsigned_char": pron_rows,
                                        "values": wants, "whisper": winfo, "problems": probs})
    assert not probs, json.dumps({"summary": summary, "problems": sorted({p["kind"] for p in probs}),
                                  "fast": [f"{p['cue']} {p['wpm']}" for p in probs if p["kind"] == "too-fast"][:8],
                                  "record": rec})
    return {"summary": summary, "record": rec}


_b0.lesson_tests(globals(), "AC-10.5 narration", _lesson)
