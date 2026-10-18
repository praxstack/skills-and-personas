"""AC-5.2: batched Kokoro TTS with lexicon respellings, full-input cache keys, and fallbacks."""
import json
import uuid
import wave

from selftest_support import NotRun
from _util import SLICE
from ptk import build, host, model, tts
from ptk.project import video


def _silence(path, seconds=0.3, rate=24000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\0\0" * int(seconds * rate))


class _FakeKokoro:
    """Stands in for host.run when it starts the Kokoro process: records each call, writes silence."""

    def __init__(self):
        self.calls, self.jobs = 0, []
        self.real = host.run

    def __call__(self, cmd, **kw):
        if not str(cmd[1]).endswith("tts_kokoro.py"):
            return self.real(cmd, **kw)
        self.calls += 1
        job = json.loads(open(cmd[2]).read())
        self.jobs.append(job)
        for s in job["segments"]:
            _silence(s["out"])
        return host.Result(cmd=cmd, code=0, stdout=json.dumps({"loads": 1}), stderr="", seconds=0.0)


def _segments(n=2):
    nonce = uuid.uuid4().hex[:8]
    return [{"id": f"t{i}", "spoken": f"cache probe {nonce} number {i}."} for i in range(n)]


def test_cache_key_covers_every_input():
    """D17.9: the key changes when any effective input changes, and only then."""
    base = {"engine": "kokoro-onnx", "engine_version": "0.6.1", "model_sha256": "a" * 64, "voices_sha256": "b" * 64,
            "voice": "af_heart", "speed": 1.0, "lang": "en-us"}
    k0 = tts.cache_key("hello", base, "2")
    assert k0 == tts.cache_key("hello", dict(base), "2"), "the key is not stable"
    changed = {"text": tts.cache_key("hello!", base, "2"), "lexicon_version": tts.cache_key("hello", base, "3")}
    for field, val in (("engine", "say"), ("engine_version", "0.6.2"), ("model_sha256", "c" * 64),
                       ("voices_sha256", "d" * 64), ("voice", "af_bella"), ("speed", 1.1), ("lang", "en-gb")):
        changed[field] = tts.cache_key("hello", {**base, field: val}, "2")
    same = [f for f, k in changed.items() if k == k0]
    assert not same, f"changing {same} keeps the cache key"
    assert len(set(changed.values())) == len(changed)
    return {"fields": sorted(changed)}


def test_cache_misses_when_any_input_changes():
    """End to end through synthesize(): a repeat hits the cache; each changed input misses it."""
    if not tts.kokoro_available():
        raise NotRun("Kokoro model or venv missing")
    fake = _FakeKokoro()
    saved = (host.run, tts.VOICE, tts.SPEED, tts.lexicon, tts.kokoro_version, tts._file_sha)
    segs = _segments()
    made = []
    host.run = fake
    try:
        def synth():
            r = tts.synthesize(segs, host.make_tmp("tts-cache-"), force_engine="kokoro")
            made.extend(s["wav"] for s in r["segments"])
            return r["synthesised_now"]

        assert synth() == 2 and synth() == 0, "a repeat with the same inputs missed the cache"
        misses = {}
        lex = tts.lexicon()
        for name, patch, undo in (
                ("voice", lambda: setattr(tts, "VOICE", "af_bella"), lambda: setattr(tts, "VOICE", saved[1])),
                ("speed", lambda: setattr(tts, "SPEED", 1.05), lambda: setattr(tts, "SPEED", saved[2])),
                ("lexicon_version", lambda: setattr(tts, "lexicon", lambda: {**lex, "version": "x"}),
                 lambda: setattr(tts, "lexicon", saved[3])),
                ("engine_version", lambda: setattr(tts, "kokoro_version", lambda: "9.9.9"),
                 lambda: setattr(tts, "kokoro_version", saved[4])),
                ("model_sha256", lambda: setattr(tts, "_file_sha", lambda p: "f" * 64),
                 lambda: setattr(tts, "_file_sha", saved[5]))):
            patch()
            try:
                misses[name] = synth()
            finally:
                undo()
        segs[0]["spoken"] += " changed"
        misses["text"] = synth()
        assert misses == {"voice": 2, "speed": 2, "lexicon_version": 2, "engine_version": 2, "model_sha256": 2,
                          "text": 1}, misses
        assert fake.calls == 7, f"expected one Kokoro process per uncached batch, saw {fake.calls}"
        return {"misses": misses, "kokoro_processes": fake.calls}
    finally:
        host.run, tts.VOICE, tts.SPEED, tts.lexicon, tts.kokoro_version, tts._file_sha = saved
        for w in set(made):
            w.unlink(missing_ok=True)


def test_batch_one_process():
    """Every uncached segment is synthesised by ONE kokoro-onnx process that loads the model once."""
    if not tts.kokoro_available():
        raise NotRun("Kokoro model or venv missing")
    starts = []
    real = host.run

    def counting(cmd, **kw):
        starts.append([str(c) for c in cmd])
        return real(cmd, **kw)

    segs = _segments(3)
    host.run = counting
    try:
        r = tts.synthesize(segs, host.make_tmp("tts-batch-"), force_engine="kokoro")
    finally:
        host.run = real
    try:
        kokoro = [c for c in starts if c[-2].endswith("tts_kokoro.py")]
        assert len(kokoro) == 1, f"{len(kokoro)} Kokoro processes for 3 segments"
        assert r["process_count"] == 1 and r["model_loads"] == 1 and r["synthesised_now"] == 3, r
        durs = [tts.probe_duration(s["wav"]) for s in r["segments"]]
        assert all(d > 0.5 for d in durs), durs
        return {"processes": len(kokoro), "model_loads": r["model_loads"], "seconds": durs}
    finally:
        for s in r["segments"]:
            s["wav"].unlink(missing_ok=True)


def test_lexicon_applied():
    """Code tokens are respelled whole-word before synthesis, and the Kokoro job carries the respelling."""
    assert tts.apply_lexicon("puts(n); printf and input") == "put-s(en); print-f and input"
    assert tts.apply_lexicon("a \\n b") == "a newline b"
    lesson = model.load(SLICE)
    segs = {s["id"]: s for s in video.segments_of(lesson)}
    assert segs["sc1.0"]["said"].startswith("The program sets n to two"), segs["sc1.0"]
    assert " en " in segs["sc1.0"]["spoken"] and " n " not in segs["sc1.0"]["spoken"], segs["sc1.0"]["spoken"]
    if not tts.kokoro_available():
        return {"kokoro_job": "not checked (no Kokoro)"}
    fake = _FakeKokoro()
    host.run = fake
    made = []
    try:
        nonce = uuid.uuid4().hex[:8]
        r = tts.synthesize([{"id": "x", "spoken": tts.apply_lexicon(f"puts prints {nonce}")}],
                           host.make_tmp("tts-lex-"), force_engine="kokoro")
        made = [s["wav"] for s in r["segments"]]
    finally:
        host.run = fake.real
        for w in made:
            w.unlink(missing_ok=True)
    sent = fake.jobs[0]["segments"][0]["text"]
    assert sent.startswith("put-s prints"), sent
    assert r["cache_inputs"]["lexicon_version"] == tts.lexicon()["version"]
    return {"sent_to_kokoro": sent}


def test_fallback_degraded():
    """Without Kokoro: `hyperframes tts` when the pinned CLI and the Kokoro venv exist, else `say`.
    Either fallback marks the result degraded, and a degraded build whose claims pass is `degraded`."""
    if not host.which("say", required=False):
        raise NotRun("macOS say missing")
    saved = (tts.kokoro_available, tts._hyperframes_tts_available)
    tts.kokoro_available = lambda: False
    tts._hyperframes_tts_available = lambda: False
    made = []
    try:
        r = tts.synthesize(_segments(1), host.make_tmp("tts-say-"))
        made = [s["wav"] for s in r["segments"]]
        assert r["degraded"] and r["engine"].startswith("macOS say"), r
        assert tts.probe_duration(made[0]) > 0.5
        # hyperframes tts comes before say when it can run
        tts._hyperframes_tts_available = lambda: True
        calls = []
        real = tts._hyperframes
        tts._hyperframes = lambda todo, out_dir, inputs: (calls.append(len(todo)), [_silence(s["wav"]) for s in todo], 0)[2]
        saved_inputs = tts.engine_inputs
        tts.engine_inputs = lambda engine: {**saved_inputs("say"), "engine": engine, "engine_version": "test"}
        try:
            r2 = tts.synthesize(_segments(1), host.make_tmp("tts-hf-"))
            made += [s["wav"] for s in r2["segments"]]
        finally:
            tts._hyperframes = real
            tts.engine_inputs = saved_inputs
        assert calls == [1] and r2["degraded"] and "hyperframes" in r2["engine"], r2
    finally:
        tts.kokoro_available, tts._hyperframes_tts_available = saved
        for w in made:
            w.unlink(missing_ok=True)
    gates = [{"id": "values.expect", "status": "passed"}, {"id": "claims.review", "status": "passed"}]
    assert build.final_status(gates, degraded=True) == "degraded"
    return {"say": r["engine"], "hyperframes": r2["engine"]}
