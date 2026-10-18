"""Batch Kokoro synthesis in ONE process (E11). Run by the Kokoro venv's python, not by ptk.

Usage: python tts_kokoro.py jobs.json
jobs.json: {"model": path, "voices": path, "voice": "af_heart", "speed": 1.0, "lang": "en-us",
            "segments": [{"id": "...", "text": "...", "out": "/abs/path.wav"}]}
Prints one JSON object: {"segments": [{"id", "out", "seconds", "sample_rate"}], "loads": 1}
"""
import json
import sys

import kokoro_onnx
import soundfile as sf


def main():
    job = json.load(open(sys.argv[1]))
    model = kokoro_onnx.Kokoro(job["model"], job["voices"])
    out = []
    for seg in job["segments"]:
        samples, rate = model.create(seg["text"], voice=job["voice"], speed=job["speed"], lang=job.get("lang", "en-us"))
        sf.write(seg["out"], samples, rate)
        out.append({"id": seg["id"], "out": seg["out"], "seconds": round(len(samples) / rate, 3), "sample_rate": rate})
    print(json.dumps({"segments": out, "loads": 1, "kokoro_onnx": getattr(kokoro_onnx, "__version__", "0.6.1")}))


if __name__ == "__main__":
    main()
