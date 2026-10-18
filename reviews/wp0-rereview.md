# WP0 re-review: fix round 1

Scope: commits `315efc3..f8468be` (8 commits, 26 files). I read the committed range only, through `git show` and a `git archive f8468be` copy in a scratch dir, because other agents are editing the working tree. I did not read `holdout/` or `plan/proposed/`, did not rebuild video, and changed nothing in the repo except this file.

## What I ran

All against the archived `f8468be` tree, with `PTK_STATE` pointed at the real `.state` (no pytest in the core venv, so I called the test functions directly):

| Test | Result |
|---|---|
| `test_build::test_pending_claims_beat_degraded` | pass |
| `test_build::test_degraded_only_after_claims_pass` | pass |
| `test_build::test_unknown_expect_fn_leaves_failed_report` | pass (build exit 3, report `failed`) |
| `test_build::test_internal_crash_leaves_failed_report` | pass (report `failed`, `KeyError`, exit 1) |
| `test_build::test_hyperframes_check_missing_count_fails` | pass |
| `test_security::test_run_profile_denies_escapes` | pass (all 10 probes denied inside, allowed outside) |
| `test_values::test_alt_output_sentence_is_value_checked` | pass |
| `test_frame_state::test_explorer_matches_frame_at_every_pause` | pass (33 pauses, 13 old-rule mismatches) |
| `test_lint` (3 tests) | pass |

Extra probes I wrote myself:

- `frames.probe` at 5 more points inside the sc6 transition, to see what the frame shows there (P1-A below).
- A C probe under the committed `sandbox.sb` `MODE=run`: `open()` of a file outside TMP, `link()` of it into TMP, and `rename()` out of TMP. All three were denied.
- A C program that uses `#embed` on a file outside TMP, compiled under `MODE=compile` and run under `MODE=run` (P2-A below).

## The four P1s

| P1 | Fixed? | Does the new test fail without the fix? |
|---|---|---|
| P1-1 degraded vs pending | Yes. `final_status` checks `pending` before `degraded` (`build.py:91-94`), and `claims_check` still reaches `degraded` once reviews pass. | Yes. With the old order, `final_status(..., degraded=True)` returns `degraded`, and both orderings in the test assert `claims-pending`. |
| P1-2 stale report on crash | Yes. A `draft` report is written atomically before any work (`build.py:107`). A `finally` records any non-`PtkError` as `failed` (`build.py:156-162`). `expect.fn` is checked at validate time (`model.py`). A SIGKILL now leaves `draft`, which `claims check` refuses. | Yes. Both crash tests seed a stale `verified` report. Under the old code the `KeyError` escapes before `save`, so `ptk report` still says `verified`. The unknown-fn test also asserts exit 3 with a JSON pointer, which needs the `model.py` change. |
| P1-3 recap explorer/frame mismatch | The recap is fixed. A program-change transition still mismatches, for longer than before (P1-A). | Partly. The recap assertion and the old-cue-rule check do fail without the fix, so the gate isn't self-referential any more. But nothing tests a program change, and `compare_pauses` excuses that case by design. |
| P1-4 loose run sandbox | Yes for `MODE=run`. Deny-default, no mach-lookup, reads limited to TMP, the runtime and system libs. Env is an allowlist (`host.program_env`). | Yes. Under the old `allow default` profile, the mach lookups and `read-home` succeed and the test lists them as leaks. Each denial has a control run outside the sandbox, so it really is the sandbox doing it. |

No new broad excepts. The `finally` records the failure and re-raises, it doesn't swallow anything. No new subprocess calls outside `host.py`: `sanitizer_runtime_dir` uses `host.run`, and `frames.py` goes through `visual.shoot`. No presence-only gates: the new gates compare values and fail on missing data. A probe job that fails gives `frame_state: None`, which counts as a mismatch, and `hf_check_clean` fails on a missing count.

## Counts

| Severity | Count |
|---|---|
| P0 | 0 |
| P1 | 1 |
| P2 | 1 |
| P3 | 5 |

## Verdict

Needs another fix, but a small one. P1-1, P1-2 and P1-4 are done properly, with tests that bite. P1-3 is fixed for the recap, but the same class of bug (frame shows one program, explorer shows the other) is still there at the start of sc6, and the new gate is written to let it through. Fix P1-A and WP0 is clean. P2-A can ride with WP2, where capture hardening lives.

---

## P1

### P1-A. A program change shows `with_break.c` in the frame and `fallthrough.c` in the explorer for 2 to 3 s, and the pause gate excuses it

- **Confidence:** 8/10 (reproduced with `frames.probe` on the committed composition)
- **Where:** `ptk/project/video.py:125-126`, `134-135`; `ptk/project/ive.py:54-56`; `ptk/verify/frames.py:222-223`

```python
            in_tween = c["kind"] in ("transition", "answer") and row["frame_state"] == "moving"
            if row["explorer_state"] != row["expected_state"] or not (in_tween or row["frame_state"] == row["explorer_state"]):
```

**What happens.** For a program change, `plan_screen` sets `reveal = start`, so sc6 draws the whole `with_break.c` path from its first frame. Meanwhile `ive.cues` gives that window a `transition` cue whose state is `before`, which is s3 from `fallthrough.c`.

With 2 s narration segments, cue m9 runs from 24.47 to 26.43 s. With longer segments (3.5 s), it runs from 36.53 to 39.37 s. At every probe point in that window, the frame shows program p2 at lines 4, 5, 8, 9, 11 and 17, and the explorer shows p1 with output `two, three, done`:

```
m9 transition sc6 24.517 explorer s3 p1 | frame moving p2 4 [] []
sc6 extra      25.450               | frame moving p2 9 [4, 5, 8] []
m9 transition sc6 26.383 explorer s3 p1 | frame moving p2 17 [4, 5, 8, 9, 10, 17] ['f.p2.l1']
```

A learner who pauses in the first seconds of "With break" sees one program in the video and another in the explorer. That's the P1-3 failure, and sc6 was named in the original finding (0.37 s then, about 2 to 3 s now). It also breaks the invariant the code claims for itself: "the frame never shows a program the explorer does not" (`video.py:125-126`). And it breaks D18.2's "the last state already shown on screen", since no part of s3 is on screen once sc6 starts.

**Why the gate misses it.** `compare_pauses` accepts any `moving` frame during a transition or answer cue without comparing anything. `shown` is defined as the first settled frame, so the last pause point (`end - 0.05`) is always still moving. In practice, the frame is never checked during transition cues at all.

**Fix.**
1. In `compare_pauses`, a moving frame must still match the explorer's program. Better still, its drawn path must lie between `before.path` and `state.path`. With that change the gate fails on sc6 as it stands, which is the point.
2. Then fix the behaviour. Two options:
   - Simplest: treat a program change like the recap. Show the new state settled at the scene start (`before = sid`, `shown = start`). sc6 doesn't follow a question, so nothing leaks.
   - If the drawing should stay: hold the old program on screen until the scene's last narration segment, as same-program scenes do. Then cut to the new code and give the explorer the target state for that window. That's only allowed when the cue isn't an answer cue.
3. Add a program-change case to `test_frame_state.py`. Assert that no pause point has `frame.program != explorer program`.

---

## P2

### P2-A. Compile mode still reads anything, so `#embed` gets around the run profile's read limits

- **Confidence:** 8/10 (reproduced with the committed profile and `/usr/bin/clang`, Apple clang 21, which is what `host.which("clang")` resolves to)
- **Where:** `ptk/capture/sandbox.sb:21-22`, `44-48`; `ptk/capture/c_runner.py:96`

```scheme
(version 1)
(allow default)
```

**What happens.** P1-4 limited what the *running* program can read. But the compiler runs under `MODE=compile`, which is still `allow default` for reads. C23 `#embed` (and `#include` of a well-formed file) pulls any file the user can read into the binary, and the program prints it at run time. I tested this program:

```c
#pragma clang diagnostic ignored "-Wc23-extensions"
static const char s[] = {
#embed "/abs/path/outside/secret.txt"
, 0};
int main(void){ fputs(s, stdout); return 0; }
```

- clang with `CLANG_FLAGS` exits 0 with no warnings, so the warning block at `c_runner.py:96` doesn't fire.
- gcc-16 exits 0 too. Its only output is a non-blocking `-Wunknown-pragmas` warning, which is recorded as a diagnostic.
- Under `MODE=run` the program printed the file's contents.

So an agent-authored lesson program (say, after a prompt injection) can still turn `~/.ssh/*` or a `.env` into stdout. Stdout becomes a captured fact, then the artifacts, then the claims jobs. This was the read-to-fact path in the original P1-4, just moved to compile time. There's no network path, so it's P2, not P1.

**Fix.**
1. Make compile mode deny reads outside the toolchain:
   - deny `file-read*` under `/Users` and `/private/var/folders`;
   - re-allow TMP, the clang and gcc install trees, the SDK and `/opt/homebrew`.
2. In `model.validate`, reject `#embed`, and any `#include` with an absolute path or `..`, as a cheap second layer.
3. Add `embed-outside` to `test_security.py`. It must fail to compile, or fail validation.

---

## P3

### P3-A. An internal crash still exits 1, the same code as "a gate failed"

- **Confidence:** 7/10
- **Where:** `ptk/build.py:160-162`, `ptk/cli.py:118-122`

The report now tells the truth (`failed`, `internal: true`), so the original harm is gone. But it records `exit: 1`, and the process dies with a traceback and exit 1. An agent that branches on the exit code alone can't tell a ptk bug from a lesson defect. Map non-`PtkError` exceptions in `cli.main` to their own code (or to 2), and record that code in the report.

### P3-B. The frame's program comes from a data attribute, not from what is drawn

- **Confidence:** 6/10
- **Where:** `ptk/verify/frames.py:48`

```js
  return { t, program: root.dataset.program, line,
```

Line, path and output are all derived from what is drawn. The program isn't: `root.dataset.program` is metadata written by the same projector. A composition that drew the wrong code under the right `data-program` would pass. Derive it from the `.file` label text, or compare the code rows' text with the program source.

### P3-C. The frame probe takes scene offsets from `timing`, not from the rendered composition

- **Confidence:** 5/10
- **Where:** `ptk/verify/frames.py:144-147`, `video.py` `host_html` (`data-start`)

`probe` maps video time to scene-local time with `timing["scenes"][i]["start"]`. The root composition is built from the same numbers. If `host_html` rounding (`:g`) or a HyperFrames offset rule ever diverged from `timing`, the MP4 would differ from what the gate checks. Read `data-start` back from the generated `composition/index.html`. Or OCR the file label and output box from two or three MP4 frames per scene (the OCR path exists).

### P3-D. `sysctl-read` is wide open in run mode

- **Confidence:** 6/10
- **Where:** `ptk/capture/sandbox.sb:78`

The program can read `kern.hostname`, `kern.osversion`, `kern.boottime`, `hw.model` and so on, and print them as facts. That's host fingerprinting in shipped artifacts. It's low risk, but the rest of the profile is tight. Allow only the names ASan needs, with `(sysctl-name ...)` or `(sysctl-name-prefix "hw.")`, found the same way the file reads were bisected.

### P3-E. The alt-output parser splits values on ", "

- **Confidence:** 6/10
- **Where:** `ptk/verify/values.py` `_alt_output` (`shown = m["lines"].split(", ")`)

A captured value that contains ", " (for example `a, b` printed on one line) gets split in two and reported as "wrong number of values", a false failure. Build the expected sentence from the facts with the same template and compare whole strings, or join the facts and compare.

---

## Sandbox profile, as a security reviewer

`MODE=run` is now in good shape:

- deny-default;
- exec limited to the one binary;
- no mach-lookup, so no LaunchServices, Apple Events, pasteboard, nsurlsessiond or other XPC services;
- no network, including unix sockets;
- no fork or `posix_spawn`;
- writes only in the per-program TMP;
- hard links and renames out of TMP are denied (I probed both);
- stdin is `/dev/null`;
- the env is an allowlist;
- `-D` params are passed as values, not spliced into SBPL source, so a hostile program id can't inject rules;
- each program gets its own TMP subdir, and ptk writes nothing into it after the runs, so a symlink planted on the first run has nothing to redirect.

The remaining escapes are:

- compile-time reads (P2-A);
- the wide `sysctl-read` (P3-D);
- the render profile, which is still `allow default` with STATE writes. That's P3-2 from the first review, deferred.

## Deferred items (from PROGRESS.md)

P2-2, P2-3, P2-5, P2-6 (evidence), P2-9, P3-2, P3-4, P3-5, P3-6 and P3-9 are listed as deferred. I didn't re-review them. The deferral matches what the first review said could ride with later WPs.
