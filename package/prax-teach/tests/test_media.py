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
