# Whole-course Docker sandbox

Run from the course skill directory. The adapter supports `extract`, `build`,
and `validate` for one course. It does not support catalog generation,
narration, fetching, or publishing. Runtime execution is offline and accepts
only an explicitly supplied, already-local immutable `sha256:…` image ID.

## Explicit image setup

Review both Dockerfiles before building. These setup commands use network
access to obtain Debian packages and the pinned Playwright/Chromium release;
they are never run by the sandbox adapter. Dependency repositories can change,
so a fresh build can produce a different image ID: inspect and review that
result before using it. Do not pass mutable tags to the adapter.

From this skill's directory:

```sh
docker --context colima-teach-security build --pull=false -t teacher-course-base:review-local ../explorable/assets/sandbox
COURSE_IMAGE=$(docker --context colima-teach-security image inspect teacher-course-base:review-local --format '{{.Id}}')
docker --context colima-teach-security build --pull=false --build-arg BASE_IMAGE="$COURSE_IMAGE" -f scripts/Dockerfile.sandbox -t teacher-course-browser:review-local scripts
COURSE_BROWSER_IMAGE=$(docker --context colima-teach-security image inspect teacher-course-browser:review-local --format '{{.Id}}')
```

`BASE_IMAGE` has no default and must name the reviewed immutable local image ID.
The base supplies Node 22, Python 3 and g++; the browser derivative adds
Playwright 1.58.0 and its Chromium 1208 headless shell/system dependencies.
The adapter uses a fixed launcher with one renderer/raster worker and smaller
Node thread pools so the ordinary browser checks fit the fixed 64 PID/thread
budget. This launcher is specific to this reviewed Chromium layout. A different
browser version needs review and another verified image/adapter combination.

The local image IDs used on 2026-10-20 were:

- Base: `sha256:c3adc592ed3413a4e7d4e9496911f317e223efb5d86712a18cb2286231c79a6a`
- Browser: `sha256:f24361b3ee8ca3b348faf3d5b4eee5a217f4fa0618553b0e9f8fce57953c7c9b`

Image IDs are local to a Docker daemon. The explicit context option selects
that daemon without changing the user's default Docker context.

## Run

```sh
python3 scripts/sandbox_course.py extract courses/example -o extracted --image "$COURSE_IMAGE" --docker-context colima-teach-security
python3 scripts/sandbox_course.py build courses/example -o built --image "$COURSE_IMAGE" --docker-context colima-teach-security
python3 scripts/sandbox_course.py validate courses/example -o validated --image "$COURSE_BROWSER_IMAGE" --docker-context colima-teach-security --timeout 180
```

The output's parent must already exist without symlink components. Each output
folder must be new. `extract` produces `course.json`; `build` uses the public
`build_course.py`; `validate` uses public `test_course.py`, including Chromium
interaction checks and visual QA/screenshots. Missing runtime/image/browser
dependencies fail closed. A course that fails its existing checks is rejected.

The separately named consent-aware evaluator v2 was approved and adopted on
2026-10-24 (`bf0bcf9`); full validation selects that canonical version. The old
reload-without-consent failure remains historical evidence. The final playback
source `eaa524e` passed three consecutive original narrated fresh-container runs,
each 22/22 plus lesson/visual QA and zero phase PID-limit events. Both disclosed
independent cases pass later regression; their earlier failures remain retained.
Current delivery and exact scope: `deliverables/teach-resume-20261024/README.md`
in the full checkout. These results do not imply a stable release or activation.

Inputs are descriptor-bound private snapshots. Only the declared lesson/shared
JS, matching lesson MP4/VTT files, and `videos.json` beside the logical course
are copied. Relative local assets supported by that existing snapshot remain
relative. No home, Docker socket, credentials, or writable host output is mounted.
The source snapshots remain owner-only on the host. The container uses the same
non-root numeric UID to read its read-only input/tools mounts.

Bounds are 128 lessons, 128 shared files, 64 MiB aggregate input, 64 MiB output,
1,024 archive entries, 1 MiB logs, 512 MiB memory (no swap), one CPU, 64
PIDs/threads, 256 MiB `/tmp`, 64 MiB `/dev/shm`, 128 file descriptors, and 64 MiB
per file. Wall timeout defaults to 90 seconds and cannot exceed 300 seconds. Both the
host capture loop and trusted container PID 1 enforce that requested limit;
the container timer starts before browser preflight or authored execution and
remains armed through descendant cleanup and packaging.
Paths in returned archives are limited to 16 components and 240 UTF-8 bytes.

A trusted container PID 1 waits for the authored process, kills every remaining
owned process (including detached `setsid` descendants), and reaps all children
before packaging output. A descendant that cannot exit prevents packaging and
hits the external wall timeout. The host bounds both archive/log transfer,
requires clean container exit, rejects traversal/duplicates/links/special files,
then publishes through an exclusive new directory. The container is forcibly
removed on success or a handled failure, including catchable host cancellation
by SIGTERM, SIGHUP, or SIGINT. Those handlers are scoped to `execute()` and
restored afterward. Library execution from a non-main Python thread is rejected
before authored code runs because that thread cannot own signal handlers. A local disk error during publication may leave
a partial new owner-only directory; the adapter reports that condition and does
not delete paths another local process might have replaced.

### Abrupt host termination and recovery

Host SIGKILL cannot run Python cleanup. A disconnected or SIGKILLed client
therefore cannot guarantee container removal or deletion of its private host
snapshots. Container PID 1 still reaches its independent deadline, kills
remaining descendants, and exits with code 124; Linux also terminates processes
in a PID namespace when its init exits. No output is published by the dead host
client. This stops execution while preserving the fixed resource limits.

The stopped container and host temporary directories can remain. For an
invocation you own, inspect the exact UUID name and its read-only bind sources:

```sh
docker --context colima-teach-security inspect OWNED_CONTAINER_NAME --format '{{json .State}} {{json .Mounts}}'
docker --context colima-teach-security rm --force OWNED_CONTAINER_NAME
```

Match the invocation and creation time before removing anything; do not remove
all containers sharing the prefix. The two bind sources identify that run’s
owner-only `~/.teacher-course-*` staging directory. Input capture can also leave
owner-only `teacher-bounded-*` and `teacher-course-*` directories beneath the
host's temporary directory. Remove only the exact directories established to
belong to the interrupted invocation. Normal completion and catchable
cancellation clean these automatically; SIGKILL recovery cannot be automatic.

Published HTML still contains authored JavaScript. Review it before opening on
the host; browser execution during `validate` stays inside Docker.

## Verification

```sh
COURSE_SANDBOX_IMAGE="$COURSE_BROWSER_IMAGE" COURSE_SANDBOX_CONTEXT=colima-teach-security COURSE_SANDBOX_BROWSER=1 python3 -m unittest discover -s scripts -p test_sandbox_course.py -v
```

Without `COURSE_SANDBOX_IMAGE`, Docker integration tests are explicitly skipped.
`COURSE_SANDBOX_BROWSER=1` adds the real browser controls. The focused suite
also exercises malicious host archives, missing runtime/image CLI errors,
create/start/copy failure cleanup, and legitimate/hostile authored courses.

## Fixed causal-exemplar render

`render` adds a fixed offline job for the base-rates candidate: one lesson,
seven film scenes, `base`/`hit`/`falseRate` mathematical contract, still step 5.
It builds the page, bundles static formats, exports nine sampled frames per
scene, exercises the model and controls, and records the unchanged lesson and
visual checker results. Those checker return codes are recorded even on failure;
`render` success is an export result, not a successful `validate` claim.

An optional existing `videos/<lesson-id>.mp4` and adjacent VTT use the same
confined descriptor-bound snapshot as ordinary course builds. Matching
`renderTiming` is JSON data in the captured course manifest; the existing bundle
exporter checks it against video duration, caption cues and source scenes.
There are no extra host paths, commands, mounts or changed resource limits.
Native narration is a separate reviewed-text job outside this mode. The direct
render helpers require `--trust-authored-code` and do not sandbox themselves;
use `sandbox_course.py render` for authored execution inside Docker.

The original browser image lacks `ffprobe`; video bundling fails closed there.
For actual video export, the explicitly authorized media setup derivative adds
Debian `ffmpeg=7:5.1.9-0+deb12u1` (observed package candidate 2026-10-20):

```sh
docker --context colima-teach-security build --pull=false --build-arg BROWSER_IMAGE=sha256:f24361b3ee8ca3b348faf3d5b4eee5a217f4fa0618553b0e9f8fce57953c7c9b -f scripts/Dockerfile.media -t teacher-course-media:review-local scripts
```

The locally built result was
`sha256:96e50ad889f7fb38c3360c76c7908d3a9b6b26ec590b82cc316993d6eeae520f`.
The browser recipe is unchanged. Package dependencies may change on a future
setup; inspect the new immutable result instead of assuming this ID. Runtime
still downloads nothing and retains every existing execution/output bound.

### Runtime revision: reaping and browser lifetime (not playback acceptance)

PID 1 now uses `supervisor_reaping.wait_reaping()` while waiting for both its
browser preflight and the owned job. It reaps adopted exited descendants as
they arrive, assigns the owned child's exact exit/signal status to its `Popen`
object, and nonblockingly drains already-exited orphans after that child exits.
There is one waiter, no SIGCHLD handler and no competing `Popen.wait()` for
those objects. Live descendants remain governed by the existing kill-all and
independent deadline. An unavailable owned status raises instead of assuming
success. Default refusal, output validation and publication rules are unchanged.

The fixed render helper closes the static-inspection context/browser before
launching the interactive-video browser with the original launch configuration.
It records direct `/proc`/cgroup phase samples without diagnostic subprocesses
and captures the live explorer after scrolling it into view. Diagnostics are
still subject to the existing 1 MiB log and output budgets.

Historical reaping-only results eliminated observed orphan zombies but did not
establish reliable playback. A retained earlier sequence passed once and then
failed; an ineffective NetworkServiceInProcess experiment was reverted. Those
failures remain historical evidence. The later approved method and final playback
status are described above. Resource limits, isolation, original render assertions
and deadlines remain unchanged.
