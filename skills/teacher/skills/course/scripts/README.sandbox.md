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

Current limitation: the public course-page checker expects progress persistence
after reload without selecting the engine’s required consent checkbox. The
ordinary seasons lesson passed 59/59 interactions and lesson/course visual QA,
but full `validate` correctly reports `FAIL status survives a reload` and
publishes no output. A wholly successful validation remains unverified pending
a separately approved checker repair. The adapter does not bypass that check.

Inputs are descriptor-bound private snapshots. Only the declared lesson/shared
JS, matching lesson MP4/VTT files, and `videos.json` beside the logical course
are copied. Relative local assets supported by that existing snapshot remain
relative. No home, Docker socket, credentials, or writable host output is mounted.
The source snapshots remain owner-only on the host. The container uses the same
non-root numeric UID to read its read-only input/tools mounts.

Bounds are 128 lessons, 128 shared files, 64 MiB aggregate input, 64 MiB output,
1,024 archive entries, 1 MiB logs, 512 MiB memory (no swap), one CPU, 64
PIDs/threads, 256 MiB `/tmp`, 64 MiB `/dev/shm`, 128 file descriptors, and 64 MiB
per file. Wall timeout defaults to 90 seconds and cannot exceed 300 seconds.
Paths in returned archives are limited to 16 components and 240 UTF-8 bytes.

A trusted container PID 1 waits for the authored process, kills every remaining
owned process (including detached `setsid` descendants), and reaps all children
before packaging output. A descendant that cannot exit prevents packaging and
hits the external wall timeout. The host bounds both archive/log transfer,
requires clean container exit, rejects traversal/duplicates/links/special files,
then publishes through an exclusive new directory. The container is forcibly
removed on success or failure. A local disk error during publication may leave
a partial new owner-only directory; the adapter reports that condition and does
not delete paths another local process might have replaced.

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
