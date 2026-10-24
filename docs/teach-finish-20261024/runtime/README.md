# Narrated runtime repair: blocked

Two bounded product allocation candidates were tried and reverted. Three
consecutive fresh-container passes were **not** obtained. This work does not
clear narrated-media acceptance or change the installed v3.0.1 release.

The baseline reproduced `pthread_create: Resource temporarily unavailable`,
PID-limit events and `AUDIO_RENDERER_ERROR` at audio startup. Those observations
identify an active resource-pressure failure; they do not establish every
internal Chromium cause. The final candidate failed despite lower sampled
pre-play tasks, so a sampled task count alone cannot predict transient demand.

| Run | Before play | Max sampled tasks | Last PID-limit events | Result |
| --- | ---: | ---: | ---: | --- |
| Baseline | 61 | 62 | 3 | Playback failure; no output |
| CPU affinity only, first run | 55 | 64 | 1 | 22 original checks and both QA statuses pass |
| CPU affinity only, next run | 61 | 61 | 3 | Playback failure; no output |
| Affinity plus reduced background allocation | 57 | 57 | 1 | Playback failure; no output |

The intermittent pass also logged a thread-creation failure and a PID-limit
event. It is retained as a pass of that invocation, never as reliability proof.
Its lesson checker recorded 58 passed, 0 failed, and both `lesson-status.json`
and `visual-status.json` recorded return code 0. The original advancing-video
check passed. There is no accepted new audio-decoder/onset observation: the
extra diagnostic check in the second experiment was never reached.

## Experiment scope and rollback

The controller approved narrowing inherited CPU affinity to one already-allowed
CPU under the existing one-CPU quota. The helper recorded `[0, 1]` to `[0]` and
failed before authored execution if affinity was unavailable, denied, empty or
unapplied. Its three exploratory unit controls passed. The first run passed;
the next real run failed, so the candidate was not accepted.

The second controller-approved candidate kept affinity, ran Node through an
explicit `--single-threaded` launcher, and added Chromium
`--js-flags=--single-threaded --disable-threaded-animation
--disable-threaded-scrolling`. No process isolation or web-security relaxation
was attempted. Node still used five threads in the measured render process.
An earlier local option probe showed that `--single-threaded` cannot be supplied
through `NODE_OPTIONS`; that unsupported form was corrected before the real
second-candidate run. The second real run failed and its scripted sequence
stopped immediately; runs 2 and 3 were not attempted.

`candidate-1-allocation.patch` preserves the first allocation change.
`candidate-2.patch` preserves the full second experimental source diff,
including exploratory tests and an additional decoder/onset check. These are
unaccepted evidence files, not applied patches. Allocation changes, their
new tests and the added decoder requirement were reverted. The only retained
runtime change is a passive `cpuAllowed` field in existing process diagnostics;
it ran successfully in both failed experiments. Existing render assertions
remain byte-for-byte unchanged.

Both experiments retained 64 tasks, 512 MiB memory/no swap, one CPU, the existing
five-second playback waits, offline execution, source capture, QA and fail-closed
publication. No model, package or API download occurred. No governor, frozen
check, private bank, threshold, historical receipt, installed release or public
ref was changed. Work stopped after two unsuccessful product candidates.

## Evidence and commands

`environment.json` records the immutable media image and explicit Docker
context. `baseline-command.json`, `reproduction-notes.json` and the second
candidate's command JSON retain the invocation details. `run-summary.json`
indexes observed phases; stderr/session logs retain the underlying output.
The session log is subsequent output after the launch's initial affinity line;
that separately returned initial line is retained in `reproduction-notes.json`.

The baseline command used `.runtime-task1/source`; the raw directory was then
moved, at the controller's request, to
`.superpowers/sdd/PLAN/runtime-raw/`. Two intervening attempts were correctly
rejected before container launch because host snapshots had added hardlinks to
scratch inputs. `after-1.stderr.log` retains the exact refusal. Fresh input bytes
were created in the same command as capture for subsequent media runs; input
hashes remained unchanged. These pre-launch rejections are safety results, not
playback results.

`source-sha256.json`, `source-media-probe.json` and the verbatim historical
provenance identify the actual 86-second VP9/Opus narration source. The source
lesson hash is `939b58ec9b72ec9fe4100aa382ed533a418a0adaea44b9fd256a23757dcd20f6`;
the narrated MP4 is
`ae739d97750cc01e43032128f9a13d003ca7533fcc50b251443d526801732d71`.
No synthetic media replaced it. The intermittent pass's 136 output files remain
in `.superpowers/sdd/PLAN/runtime-raw/candidate-1/`;
`affinity-only-pass-artifact-sha256.json` records every file's bytes and SHA-256.
Selected unchanged QA/render receipts are copied here. Logs and hash manifests
are outside the artifact content they attest to.

`final-controls.log` records all 34 current course ordinary/security controls
passing with zero skips in 134.068 seconds, with Docker and real browser
controls enabled after rollback. The command is:

```sh
COURSE_SANDBOX_IMAGE=sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f COURSE_SANDBOX_CONTEXT=colima-teach-security COURSE_SANDBOX_BROWSER=1 python3 -m unittest discover -s skills/teacher/skills/course/scripts -p 'test_*.py' -v
```

`final-renderer-syntax.log` records the exit-zero Node syntax check.
Playback remains blocked and needs a separately bounded investigation; these
controls and the isolated pass do not satisfy the three-run requirement.
