"""AC-0.3: whisper-cli word timestamps on the proof MP4 (converted to 16 kHz mono WAV)."""
import json

from _util import V21
from selftest_support import NotRun
from ptk import host
from ptk.verify import media

PROOF = V21.parent / "clean-install-20261018" / "review-20261018" / "proof" / "video"


def test_whisper_timestamps_on_fixture():
    mp4 = PROOF / "renders" / "one-byte-four-views.mp4"
    timings = PROOF / "assets" / "timings.json"
    if not mp4.exists():
        raise NotRun(f"proof MP4 missing at {mp4}")
    work = host.make_tmp("whisper-test-")
    words, info = media.whisper_words(mp4, work)
    assert (work / "speech-16k.wav").exists()
    wav = host.run([host.which("ffprobe"), "-v", "error", "-show_entries", "stream=sample_rate,channels", "-of", "json",
                    work / "speech-16k.wav"], check=True).stdout
    st = json.loads(wav)["streams"][0]
    assert st["sample_rate"] == "16000" and st["channels"] == 1, st
    assert len(words) >= 100, len(words)
    starts = [w["start"] for w in words]
    assert all(b >= a - 0.25 for a, b in zip(starts, starts[1:])), "word times go backwards"
    dur = float(json.loads(host.run([host.which("ffprobe"), "-v", "error", "-show_entries", "format=duration", "-of",
                                     "json", mp4], check=True).stdout)["format"]["duration"])
    assert 0 <= starts[0] and words[-1]["end"] <= dur + 0.5
    # every proof cue start has a heard word within 0.5 s (the proof's own measured timings)
    cues = json.loads(timings.read_text())["cues"]
    misses = [c["id"] for c in cues if not any(abs(w["start"] - c["start"]) <= 0.5 for w in words)]
    assert len(misses) <= 1, f"cue starts with no word within 0.5 s: {misses}"
    return {"words": len(words), "first": words[:3], "cue_start_misses": misses, "model": info["model"]}


# ---------------------------------------------------------------- AC-5.4 media thresholds

def _built():
    from _util import SLICE
    vdir = SLICE / "build" / "video"
    if not (vdir / "lesson.mp4").exists() or not (vdir / "timing.json").exists():
        raise NotRun(f"no built video at {vdir}; run `ptk build lessons/switch-fallthrough --only video,ive`")
    return vdir, json.loads((vdir / "timing.json").read_text())


def test_media_thresholds():
    """The built MP4 passes every AC-5.4 check; each out-of-range fixture fails the check it breaks."""
    vdir, timing = _built()
    gate = media.media_gate(vdir / "lesson.mp4", vdir, timing)
    assert gate["status"] == "passed", gate["reason"]
    m = gate["measured"]
    info = media.probe(vdir / "lesson.mp4")
    loud = {k: m[k] for k in ("integrated_lufs", "true_peak_dbtp", "lra_lu")}
    caps, chaps = media.parse_vtt(vdir / "captions.vtt"), media.parse_vtt(vdir / "chapters.vtt")
    assert all(media.media_checks(info, loud, caps, chaps, timing).values())

    def video_stream(**kw):
        d = json.loads(json.dumps(info))
        next(s for s in d["streams"] if s["codec_type"] == "video").update(kw)
        return d

    def audio_stream(**kw):
        d = json.loads(json.dumps(info))
        next(s for s in d["streams"] if s["codec_type"] == "audio").update(kw)
        return d

    no_subs = json.loads(json.dumps(info))
    no_subs["streams"] = [s for s in no_subs["streams"] if s["codec_type"] != "subtitle"]
    fixtures = {
        "loud -13 LUFS": (info, {**loud, "integrated_lufs": -13.0}, caps, chaps, "loudness_in_range"),
        "quiet -18.5 LUFS": (info, {**loud, "integrated_lufs": -18.5}, caps, chaps, "loudness_in_range"),
        "true peak -0.4 dBTP": (info, {**loud, "true_peak_dbtp": -0.4}, caps, chaps, "true_peak_ok"),
        "1280x720": (video_stream(width=1280, height=720), loud, caps, chaps, "video_h264_1920x1080"),
        "hevc": (video_stream(codec_name="hevc"), loud, caps, chaps, "video_h264_1920x1080"),
        "25 fps": (video_stream(r_frame_rate="25/1"), loud, caps, chaps, "video_30fps"),
        "mp3 audio": (audio_stream(codec_name="mp3"), loud, caps, chaps, "audio_aac"),
        "no caption track": (no_subs, loud, caps, chaps, "captions_track_in_mp4"),
        "no captions.vtt": (info, loud, [], chaps, "captions_vtt"),
        "no chapters.vtt": (info, loud, caps, [], "chapters_vtt"),
        "no chapters in mp4": ({**info, "chapters": []}, loud, caps, chaps, "chapters_in_mp4"),
        "audio 2 s short": (audio_stream(duration=str(float(m["audio"]["duration"]) - 2)), loud, caps, chaps,
                            "av_duration_match"),
    }
    caught = {}
    for name, (i, lo, c, ch, check) in fixtures.items():
        res = media.media_checks(i, lo, c, ch, timing)
        failed = sorted(k for k, ok in res.items() if not ok)
        assert failed == [check], f"{name}: failed {failed}, expected only {check}"
        caught[name] = check
    # one real out-of-range file through the whole gate: 1280x720, 25 fps, a full-scale sine (about -3 LUFS, true peak near 0 dBTP)
    work = host.make_tmp("media-fixture-")
    bad = work / "bad.mp4"
    host.run([host.which("ffmpeg"), "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=1280x720:r=25:d=3",
              "-f", "lavfi", "-i", "aevalsrc=0.98*sin(2*PI*440*t):s=48000:d=3", "-c:v", "libx264",
              "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", bad], check=True, timeout=120)
    g = media.media_gate(bad, work, timing)
    assert g["status"] == "failed", g
    for check in ("video_h264_1920x1080", "video_30fps", "loudness_in_range", "true_peak_ok", "captions_vtt"):
        assert not g["measured"]["checks"][check], (check, g["measured"])
    return {"measured": {k: m[k] for k in ("integrated_lufs", "true_peak_dbtp", "lra_lu", "duration")},
            "video": m["video"], "fixtures_failing": caught, "real_fixture": g["reason"]}


# ---------------------------------------------------------------- AC-5.5 sync gate

def test_sync_gate():
    """Whisper on the final MP4: every cue's speech starts and ends within 0.5 s of the cue, and the
    non-code WER is at most 10%; every code token is heard as its lexicon form."""
    vdir, timing = _built()
    g = media.sync_gate(vdir / "lesson.mp4", vdir, timing, host.make_tmp("sync-built-"))
    assert g["status"] == "passed", g["reason"]
    m = g["measured"]
    assert m["max_abs_start_delta"] <= media.SYNC_TOL and m["max_abs_end_delta"] <= media.SYNC_TOL
    assert m["non_code_wer"] <= media.WER_MAX and not m["mispronounced"]
    return {k: m[k] for k in ("max_abs_start_delta", "max_abs_end_delta", "non_code_wer", "ref_words", "hyp_words")}


def test_sync_fixtures_fail():
    """E17: the control passes; shifted audio, truncated speech and a mispronounced code token each fail,
    for their own reason."""
    import _sync_fixtures as fx
    from ptk import tts
    if not tts.kokoro_available():
        raise NotRun("Kokoro missing: the fixtures are built from Kokoro segments")
    out = {}
    for kind in ("control", "shifted", "truncated", "mispronounced"):
        work = host.make_tmp(f"sync-{kind}-")
        wav, timing = fx.build(kind, work)
        g = media.sync_gate(wav, work, timing, work / "sync")
        m = g["measured"]
        out[kind] = {"status": g["status"], "reason": g["reason"], "max_start": m["max_abs_start_delta"],
                     "max_end": m["max_abs_end_delta"], "wer": m["non_code_wer"],
                     "mispronounced": [b["tokens"][0]["token"] for b in m["mispronounced"]]}
    assert out["control"]["status"] == "passed", out["control"]
    assert out["shifted"]["status"] == "failed" and "out of sync" in out["shifted"]["reason"], out["shifted"]
    assert out["shifted"]["max_start"] > media.SYNC_TOL, out["shifted"]
    assert out["truncated"]["status"] == "failed" and "sc3.1" in out["truncated"]["reason"], out["truncated"]
    assert out["mispronounced"]["status"] == "failed" and out["mispronounced"]["mispronounced"] == ["n"], \
        out["mispronounced"]
    assert "out of sync" not in out["mispronounced"]["reason"], out["mispronounced"]
    return out


def test_refine_ignores_stretched_last_token():
    """WP9: before a long pause whisper stretches the last token over the silence (factorial's question line:
    "on." from 31.74 to 35.50). The speech still stops at the first silence after the token's start, so the
    offset is the silence edge at 31.95, not one after the stretched end. A normal last word keeps the old rule."""
    from ptk.verify import media
    words = [{"text": "go", "start": 31.5, "end": 34.65}, {"text": "on.", "start": 31.74, "end": 35.5}]
    on, off = media.refine(words, starts=[31.95, 35.61], ends=[29.2])
    assert off == 31.95, off
    normal = [{"text": "go", "start": 31.5, "end": 31.7}, {"text": "on.", "start": 31.74, "end": 31.9}]
    assert media.refine(normal, starts=[31.95, 35.61], ends=[29.2])[1] == 31.95
    late = [{"text": "on.", "start": 33.0, "end": 33.3}]  # a genuinely late word still ends late
    assert media.refine(late, starts=[31.95, 33.4], ends=[32.9])[1] == 33.4
    # one second of stretch before a scene gap (one-byte sc7.2: "run." 79.74 to 80.72, silence from 79.89)
    run = [{"text": "never", "start": 79.48, "end": 80.03}, {"text": "run.", "start": 79.74, "end": 80.72}]
    assert media.refine(run, starts=[78.85, 79.89, 81.36], ends=[79.19])[1] == 79.89
    # a pause inside the stretched token is not its end (neuron sc5.1: "is" ... pause ... "0.6.", silence at 60.28)
    six = [{"text": "is", "start": 58.7, "end": 59.37}, {"text": "0.6.", "start": 59.02, "end": 61.0}]
    assert media.refine(six, starts=[57.87, 59.34, 60.28, 63.76], ends=[55.28])[1] == 60.28
    return {"stretched_offset": off}


def test_refine_stretch_needs_a_silence_holding_the_token_end():
    """Round-17 Codex 6: the long-token rule may only move the offset back to a silence that contains the token's
    end (that is what a stretch over a pause looks like). Codex's counterexample: token [1, 4], a short pause
    [2, 2.2] inside it, the speech resumes and stops at 4.05, cue ends at 2. The old rule measured 2 (a false pass);
    now no silence holds 4, so the later boundary 4.05 stands and the cue fails by about 2 s."""
    from ptk.verify import media
    late = [{"text": "word", "start": 1.0, "end": 4.0}]
    on, off = media.refine(late, starts=[2.0, 4.05], ends=[2.2, 5.0])
    assert off == 4.05, off
    assert abs(off - 2.0) > media.SYNC_TOL, "the hanging caption must fail the sync tolerance"
    # the hanging-caption direction (round-17 P3-4): a caption that ends before a real stretch over a pause is
    # measured at the pause start, so a cue that ends after the pause fails by the pause length
    hang = [{"text": "on.", "start": 31.74, "end": 35.5}]
    on, off = media.refine(hang, starts=[31.95, 35.61], ends=[35.45, 36.0])
    assert off == 31.95 and abs(off - 35.5) > media.SYNC_TOL, off
    # a silence that ends well before the token's end is a pause inside the word, not its end
    inner = [{"text": "0.6.", "start": 59.02, "end": 61.0}]
    assert media.refine(inner, starts=[59.34, 60.28], ends=[59.5, 61.05])[1] == 60.28
    assert media.refine(inner, starts=[59.34, 61.2], ends=[59.5, 61.6])[1] == 61.2, "no silence holds 61.0"
    return {"counterexample_offset": 4.05}


def test_whisper_word_never_ends_after_the_audio():
    """B5, measured on the factorial film: whisper.cpp gave the last token of the last 30 s window the window's end
    (112.2 s) as its end, 3.5 s past the end of the audio (108.67 s), so no silence could hold it and the sync gate
    put the speech end at 112.2 against a cue that ends at 107.07. A word cannot end after the audio does: the end is
    clamped to the audio's duration, and the trailing silence then holds the stretched token as usual."""
    words = [{"text": "frame", "start": 106.26, "end": 110.5}, {"text": "above.", "start": 106.72, "end": 112.2}]
    starts, ends = [104.771875, 107.0225], [105.12025, 108.666688]
    clamped = media.clamp_to_audio(words, 108.666688)
    assert [w["end"] for w in clamped] == [108.667, 108.667] and [w["start"] for w in clamped] == [106.26, 106.72]
    assert media.refine(words, starts, ends)[1] == 112.2, "unclamped, the end lands past the audio"
    assert media.refine(clamped, starts, ends)[1] == 107.022
    # a token inside the audio is untouched
    assert media.clamp_to_audio([{"text": "a", "start": 1.0, "end": 1.4}], 5.0) == [{"text": "a", "start": 1.0, "end": 1.4}]
    return clamped
