# Fresh installation and build trial

The clean-prefix trial passed after one model-cache provisioning repair. Product source `0d20ff7` and all 2,342 archived source files are unchanged. The trial used the published downloads with matching SHA256 hashes, a fresh Python environment, a fresh Playwright installation and a freshly downloaded Chromium. Existing model weights and the system Python/Node/ffmpeg executables were explicit prerequisites. This was the same macOS arm64 machine, not a clean VM or a cross-platform trial.

## What ran

- Nine installer operations exercised dry-run, linking, repeat install, copy, both uninstall modes, preservation of a foreign folder and project-prefix reinstall. Default discovery exposed one teacher entry. No active host skills were replaced.
- Vendor verification: zero problems.
- Three explorer sources rebuilt, plus a two-lesson course.
- One language lesson received freshly generated Kokoro narration, a real MP4 and all six artifact exports. No narrator clips from the earlier candidate were reused. Recovery reused only clips generated during this same trial.
- Flow/consent/resume: 65/65, against the three fresh explorers and fresh course.
- Export/browser checks: 173/173. This mixed check used the fresh language bundle and the two downloaded published bundles; it is not three new video renders.
- The unchanged framework regression completed with 59/59 practice browser checks, responsive checks and a real animation MP4. The standalone fast run recorded 63 passes and 3 skips out of 66. The missing repository-only lint dependency was supplied from the exact pack commit, and its original test passed separately. The other two skips are the documented downstream-site-only tests. No assertion changed.
- Fresh narration: 57.58 seconds, 24 fps, 1280x720, -16.7 LUFS, -2.7 dB true peak; speech alignment 82/82 caption words, zero weak cues. The actual still and video contact sheet were opened and inspected.

## Failures kept on record

The first narration attempt passed picture and level checks, then failed speech verification because my cache copy preserved a nested link outside the copied cache. The isolated ASR model was missing. I materialized that single blob from the local model source, verified matching SHA256 and reran the unchanged narrator. The failed clip remains under `outputs/voice-and-focus/first-attempt/` in the downloadable evidence ZIP.

The first recovery wrapper also stopped with an undefined variable before invoking the product. Its NameError log is retained. This was a trial harness error, not a lesson defect.

The source archive intentionally excludes a repository-level linter. Its original standalone test reported the omission rather than pretending it ran. The exact same-commit lint implementation was supplied as a separate trial dependency; the original test then passed. It was not added to or changed inside the candidate skill.

## What this does not close

The runtime's new WAV probe reports `audio content omitted because you do not support audio input`. Four required actual listening verdicts remain NOT_RUN, so frozen general evaluation is still 52/56 and release readiness is false. Prax's approval of viewed visuals is recorded; it does not establish an unheard recording's quality. The private listening page is supplied separately and is not in this public archive.

The optional C adapter is unchanged and unaccepted. Its OCR failure, protected-check conflicts and unrun full claims reviews remain in its existing report. No governing rule, candidate source, private bank, real learner records or active skill links changed in this trial.

## Reproduction

`run-trial.py` and `retry-trial.py` preserve the executed build/test commands. `runtime-requirements.txt`, `runtime-freeze.txt` and `runtime-versions.json` identify the runtime. The raw logs and JSON receipts preserve failed and successful attempts separately. Download the original source and review archives from the existing v3 prerelease, compare their hashes, extract them into `source/` and `review/`, and provision the documented runtime before running the script in a new `/private/tmp/prax-teach-clean-install-*` prefix. The scripts are receipts for this host's pinned runtime layout, not an automatic cross-platform installer.
