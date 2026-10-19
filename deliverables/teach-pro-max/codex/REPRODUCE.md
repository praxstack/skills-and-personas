# Prax Teach — reproducible accepted general teacher

Open `index.html` to review the real outputs. Each lesson has a self-contained explorer, editable landscape SVG and PNG, explanation-first Q&A, contextual cards/TSV, actual Kokoro MP4/WebVTT and an interactive video. `static.html` and the explorer's noscript fallback contain the full explanation. Open from `file://`; no server is required. Source lessons are under `lessons/<slug>/source/lesson.lesson.js`.

## Runtime requirements

Python 3.12 with PyYAML, numpy, soundfile, kokoro_onnx and faster-whisper; Node with Playwright/Chromium; ffmpeg/ffprobe; cached Kokoro model/voices and faster-whisper base.en. Provision into an isolated environment. The run reused existing tools/models by APFS copy under `/private/tmp/prax-teach-v3-runtime`; it did not reinstall shared tools or use a paid API. Paths in the raw logs are receipts from this Mac, not portable installation instructions.

Export `PLAYWRIGHT_MODULE` to Playwright's module directory, `CHROMIUM_PATH` to Chromium, `KOKORO_DIR` to the model directory and `NARRATE_CACHE` to a dedicated writable cache. Use `HF_HUB_OFFLINE=1` once the speech model is cached. Run from the repository root with the isolated environment's Python on PATH.

```sh
python3 skills/teacher/skills/explorable/scripts/build.py \
  deliverables/teach-pro-max/codex/lessons/base-rates/source/lesson.lesson.js \
  -o deliverables/teach-pro-max/codex/lessons/base-rates/explorer.html
python3 skills/teacher/skills/explorable/scripts/narrate.py \
  deliverables/teach-pro-max/codex/lessons/base-rates/explorer.html \
  -o deliverables/teach-pro-max/codex/lessons/base-rates/lesson.mp4 \
  --engine kokoro --speed 0.85 --fps 24
node skills/teacher/skills/explorable/scripts/bundle_lesson.mjs \
  deliverables/teach-pro-max/codex/lessons/base-rates/explorer.html \
  --out deliverables/teach-pro-max/codex/lessons/base-rates/bundle \
  --video deliverables/teach-pro-max/codex/lessons/base-rates/lesson.mp4 \
  --timing deliverables/teach-pro-max/codex/lessons/base-rates/lesson.timing.json
```

Use the same commands for `voice-and-focus` and `diffusion`. Bundling requires actual matching narration; it checks MP4 streams/duration and the caption/timing sidecars rather than fabricating a film.

```sh
bash skills/teacher/scripts/tests/run_all.sh
python3 skills/teacher/scripts/vendor.py verify
node deliverables/teach-pro-max/codex/reproduce/check_flow.mjs
node deliverables/teach-pro-max/codex/reproduce/check_exports.mjs
python3 deliverables/teach-pro-max/codex/evidence/independent-content/audit-numbers.py
python3 skills/teacher/skills/course/scripts/build_course.py \
  deliverables/teach-pro-max/codex/course \
  -o deliverables/teach-pro-max/codex/course/site
```

The independent numerical auditor uses its source snapshots and a separate Python Fraction/iterative oracle. Its original defects, source hashes, frames and after-repair evidence remain together. Do not turn those original failures into final failures or erase them.

## Evidence boundaries

The private bank contains 24 routing cases, 8 scoped end-to-end requests across non-C subjects and 16 valid/invalid controls. Only hashes, neutral IDs and redacted results may be published. Its author did not classify its blind controls; a separate reviewer did. The public archived bank is regression data, not hidden evaluation.

ASR establishes approximate words and timing, not voice pleasantness or human prosody. Responsive checks establish stated viewport behavior, not aesthetic approval or learning outcomes. The course's old 20/21 persistence diagnostic remains recorded alongside the new explicit-consent flow; it was not weakened. The exact general source is activated locally; the optional C development adapter is not installed.

The C adapter is independently committed on `candidate/teach-c-adapter-20261019`; its `deliverables/teach-pro-max/claude/CANDIDATE1.md` lists actual failures and method conflicts. Synthetic claims unit tests do not establish four-lesson claims acceptance.

Additional diagnostic history: the first export playback probe read readiness immediately after seeking; it was corrected to await `seeked`, with the original receipt retained. A later caption probe accidentally required exactly 18px rather than the legibility floor of 16px; its original three failures are retained, and the corrected probe checks separation below the player and the minimum readable size. Neither diagnostic is a governing evaluator, and no frozen check or threshold changed.
