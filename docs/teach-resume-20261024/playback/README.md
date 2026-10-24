# Narrated playback: browser pool scheduling

The sandbox now merges Chromium's `BrowserThreadPoolAdjustment:min/2` into
the existing enabled features. Three consecutive fresh-container renders of
the original real narration passed all 22 frozen render checks and both lesson
and visual QA. The controller reports that the independent frozen holdout also
starts actual audio/video with zero PID-limit events, then fails the final
seek/caption assertion because its closing still outlasts its last VTT cue.
That separate caption-tail issue remains open; complete runtime acceptance is
not claimed here. The implementer did not inspect the holdout input.

Only the trusted browser wrapper and its sandbox shim changed. The wrapper
keeps the original browser arguments, preserves unrelated enabled features and
produces exactly one merged `--enable-features` value. Its owned pool parameter
replaces conflicting copies. Audio and GPU stay in their existing processes.

## Mechanism and provenance

The direct CDP identity is HeadlessChrome 145.0.7632.0, revision
`0bbdf2913883391365383b0a5dfe7bf9fd1a5213`. Six relevant public Chromium source
files fetched at that exact revision match the prior research's 145.0.7632.0
tag sources byte for byte. `revision-source/receipts.json` contains their URLs
and SHA-256 values. The browser's desktop foreground ThreadPool has a default
minimum capacity of 16, independently of the one-CPU quota. The existing
feature changes that minimum to two. This is scheduling capacity, not a hard
thread count; blocking compensation can still create more workers.

Source: [Chromium startup_helper.cc at the observed revision](https://raw.githubusercontent.com/chromium/chromium/0bbdf2913883391365383b0a5dfe7bf9fd1a5213/content/browser/startup_helper.cc),
[thread_group_impl.cc](https://raw.githubusercontent.com/chromium/chromium/0bbdf2913883391365383b0a5dfe7bf9fd1a5213/base/task/thread_pool/thread_group_impl.cc).

The paired diagnostic instruments only a disposable copy of the frozen render
executor. It adds per-thread `/proc` names, argv, cgroup limits and passive CDP
media observations inside the already-running inspector. No `docker exec`
adds tasks to the playback container. Original acceptance runs use unchanged
executors without these additions.

| Observation | Initial diagnostic | Matched baseline | Pool candidate |
| --- | ---: | ---: | ---: |
| Outer deadline, seconds | 300 | 180 | 180 |
| Browser threads before play | 26 | 29 | 17 |
| Browser `ThreadPoolForeg` names before play | 12 | 15 | 3 |
| Total tasks before play | 59 | 61 | 50 |
| Sampled tasks with advancing media | failed | failed | 59 |
| Sampled tasks with visible explorer | not reached | not reached | 60 |
| PID-limit events | 3 | 3 | 0 |

Linux truncates thread names. The name counts support the source-backed pool
hypothesis; they do not identify each failed thread request. Samples can miss
short peaks. `paired-summary.json` retains every sampled phase, media events
and the actual-argv comparison. All other arguments match in order after
excluding the variable temporary profile path. The candidate's sole merged
value is `CDPScreenshotNewSurface,BrowserThreadPoolAdjustment:min/2`.

The first diagnostic accidentally used a 300-second outer deadline and failed
within 10.323 seconds, before publication. Its raw receipt is retained. The
corrected paired baseline uses the exact bf0bcf9 adapter and reproduces the
same audio-startup failure in 10.350 seconds. It and all candidate/acceptance
runs use the original 180-second deadline and five-second media waits. No
production cap or timeout changed.

## Real audio evidence

The fixture MP4 hash is
`ae739d97750cc01e43032128f9a13d003ca7533fcc50b251443d526801732d71`.
All runs preserve the original lesson, course timing, video and VTT hashes in
`product-freeze.json`. No synthetic media was substituted.

CDP identifies the real mono 48-kHz Opus track, `FFmpegAudioDecoder`, VP9 and
`VpxVideoDecoder`. A separate seven-thread audio utility appears at startup.
The existing default output mute remains in place; audio decoding continues.
At media time 0.119932 the browser reported 63 decoded audio bytes; at 2.510378
it reported 26,841, with 64 decoded video frames and no media error. Source
silence analysis at -45 dB finds leading silence ending at 1.307625 seconds,
consistent with the original `voiceAt: 1.3` timing. This establishes decoding
past the real narration onset. It is not a subjective listening or learning
assessment. `source-onset.txt` and the diagnostic raw log retain the outputs.
Successful muted runs retain the container's D-Bus and absent ALSA-device
diagnostics in stderr. They have no thread-creation or audio-renderer failure;
the decoding observation is separate from physical output-device availability.

## Commands and receipts

Run the task-local reproducible harness from the repository root. It creates
fresh disposable source bytes in the same execution call as secure capture,
then invokes the real sandbox with the immutable image and explicit context.
Each label must be new. `--diagnostic` is supplemental observation only;
`--baseline` loads the exact bf0bcf9 adapter in scratch.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 docs/teach-resume-20261024/playback/run_playback.py LABEL
PYTHONDONTWRITEBYTECODE=1 python3 docs/teach-resume-20261024/playback/run_playback.py DIAGNOSTIC_LABEL --diagnostic
PYTHONDONTWRITEBYTECODE=1 python3 docs/teach-resume-20261024/playback/run_playback.py BASELINE_LABEL --baseline --diagnostic
```

Image:
`sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f`.
Docker context: `colima-teach-security`; global context remains `default`.
Each container retains 64 tasks, 512 MiB/no swap, one CPU, offline networking,
read-only mounts/root, non-root ownership, dropped capabilities and the
existing publication/lifecycle boundaries.

`runs.json` indexes actual commands, exits, durations and per-phase counts.
Each run directory retains the exact source hashes, stdout/stderr, original
check results, QA status and artifact hashes outside the generated artifacts.
`frozen-identities.json` pins the six unchanged governing files.

The three uninstrumented results are 22/22 plus both QA exits zero in 26.108,
25.835 and 26.768 seconds. No extra attempt was needed. Every sampled phase
reports zero PID-limit events. The unchanged checks include model equivalence,
keyboard operation, all explanation steps, film geometry/captions, static
disclosures, real advancing video, chapter/explorer parameter transfer, speed,
caption toggle, near-end seek, network refusal and page errors.

The affected full course suite passed 39/39 with zero skips in 210.833 seconds:

```sh
env PYTHONDONTWRITEBYTECODE=1 COURSE_SANDBOX_IMAGE=sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f COURSE_SANDBOX_CONTEXT=colima-teach-security COURSE_SANDBOX_BROWSER=1 python3 -m unittest discover -s skills/teacher/skills/course/scripts -p 'test_*.py' -v
```

`course-suite.txt` retains the output. Actual browser validation reports 59/59
lesson interactions, 26/26 consent-v2 checks and lesson/course visual QA. The
deliberate page-error control prevents publication. Host SIGKILL deadline
controls stopped native, detached and browser cases in 8.24, 8.22 and 8.45
seconds; SIGTERM cleanup took 0.31 seconds. Reaping, filesystem, environment,
offline networking, memory, task/log/artifact budgets and output-link controls
passed unchanged. Negative controls emit expected process/memory errors in
their retained output. No course containers remained afterward.

The phase is limited to this pinned runtime and source-backed scheduling
repair. Browser updates need a fresh feature/default audit. The existing
thread caps, isolation policy, original checks and installed release are
unchanged. Screenshots were inspected for the actual visible explorer and
interactive video controls; the automated lesson and visual QA also passed.
