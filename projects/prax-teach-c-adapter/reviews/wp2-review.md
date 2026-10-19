# WP2 review: lesson model and capture

Scope: commit `75a31ad` (the only `wp2:` commit), 23 files, +1967/-174. I read the committed diff with `git show` and a clean `git worktree` at `75a31ad` (`.state/review-wp2`, removed afterwards), because other agents are editing the live tree. I did not read `holdout/` or `plan/proposed/`. Spec: `spec/SPEC.md` v1.1 (AC-2.1..2.8, §5.2-§5.4). Decisions: `plan/CEO-PLAN.md` D17.4, D17.5, D17.10, E19, E24.

## Verdict

**Request changes.** The work is careful and most of it is good: the security tests have real controls, the AC-2.8 lint plants each way of reaching capture code and proves the lint catches it, and validation reports every dangling reference with a pointer. But two things the commit claims don't hold against a hostile or sloppy lesson program. The UB guard (D17.4, AC-2.3) can be switched off from inside the C source, and the new compile-mode read restriction can be bypassed with a symlink. Both are small fixes.

## What I ran

| Run | Result |
|---|---|
| `ptk selftest -k test_model / test_capture / test_security / test_lint` on the clean worktree | all pass (2 needed a `PTK_STATE` under `$HOME` with hyperframes, see P3-6) |
| My probe: `format_warning.c` plus `#pragma clang diagnostic ignored "-Wformat"`, through `capture_lesson` | **captured** `"0.000000"`, clang diagnostics empty |
| Same program with a GNU line marker `# 1 "fake.h" 3` instead of the pragma | **captured** `"0.000000"` |
| `INT_MAX + 1` inside `__attribute__((no_sanitize("undefined")))` | **captured** `"-2147483648"`, sanitizers `"no finding"` |
| `programs/hello.c` replaced by a symlink to a file outside every allowed dir | `CompileError`, and the file's bytes are in `stderr` |
| `#embed` of a 1.6 GB file under `/System/Volumes/Preboot/Cryptexes/OS/System/Library/dyld/`, compile profile, my own 1.5 GB watchdog | clang passed 1.5 GB RSS in 3.4 s and was still growing |
| `#include "/dev/zero"` and `#embed "/dev/urandom"` in compile mode | harmless: clang returns at once or refuses device files |
| platform fact with `key: "sizeof.int128"` | validates, then capture raises a bare `KeyError` |
| stdout fact selecting line 3 of a 1-line program, `ptk build` | exit 3, `ModelReferenceError`, expected value not shown |
| `CCC_OVERRIDE_OPTIONS="x-fsanitize=undefined,address" clang ... -###` | the sanitizer flags are gone from the cc1 line |

Side effect to know about: my first selftest runs used the shared `PTK_STATE`, so `.state/selftest-auto.json` in the live tree now holds my `-k test_lint` subset. Any full `ptk selftest` rewrites it.

## Counts

| Severity | Count |
|---|---|
| P0 | 0 |
| P1 | 2 |
| P2 | 6 |
| P3 | 9 |

## P1

### P1-1 The UB guard can be turned off from inside the program (confidence 10/10)

`package/prax-teach/ptk/capture/c_runner.py:124`

```python
if "warning:" in warnings and not ub_covered(lesson, program):
```

The guard trusts clang's warning output, and the lesson source controls that output. I captured the exact `%f` regression that motivated D17.4 and D17.5 three ways, and each one got through as a clean fact:

- `#pragma clang diagnostic ignored "-Wformat"` (or `-Weverything`, or `_Pragma(...)`, or `#pragma GCC diagnostic`);
- a GNU line marker `# 1 "fake.h" 3`, which makes clang treat the rest of the file as a system header and drop its warnings;
- `__attribute__((no_sanitize("undefined")))` (or `"address"`) on the function with the UB, so UBSan never instruments it and the report says `"no finding"`.

The program is agent-written. The realistic path isn't even malice: an agent hits `SanitizerFinding`, adds the pragma it sees in `tests/fixtures/capture/embed.c.in`, re-runs, and the repair loop in `LESSON-MODEL.md` succeeds. The test fixture itself teaches the bypass (`#pragma clang diagnostic ignored "-Wc23-extensions"`).

Fix: reject these at `ptk validate` and again in `capture_program` before compiling, with a pointer to `/programs/i/path`. Strip comments and string literals, then refuse `#pragma clang diagnostic`, `#pragma GCC diagnostic`, `_Pragma`, `#pragma clang system_header`, `#line`, GNU line markers (`^\s*#\s*[0-9]`), `#embed` (the lesson std is C17), `no_sanitize`, `disable_sanitizer_instrumentation`, and definitions of `__asan_default_options`, `__ubsan_default_options`, `__asan_on_error` and `__sanitizer_set_death_callback`. Add one fixture per form to `test_capture.py`, each asserting `SanitizerFinding` or a model error, with `format_warning.c` as the control.

### P1-2 A symlinked program file walks around the compile read restriction (confidence 10/10)

`package/prax-teach/ptk/capture/c_runner.py:120`

```python
shutil.copyfile(lesson.dir / program["path"], src)
```

The schema pattern `^programs/[A-Za-z0-9_.-]+\.c$` blocks `..`, but `copyfile` follows symlinks, and it runs in the unsandboxed Python process. Point `programs/p1.c` at any file the user can read and capture copies it into the temp dir, where the compile profile happily reads it. If it isn't valid C, clang quotes it line by line in the error. `CompileError` carries that `stderr`, the CLI prints it, and `build._fail` writes it into `build/build-report.json` next to the lesson. My probe got the whole secret token back. If the target happens to be valid C, it gets compiled and its source becomes the lesson's code figure.

The commit message and the profile comment both say compile mode can read file contents "only from the temp dir and the toolchain". With this bypass that isn't true.

Fix: before the copy, refuse if `(lesson.dir / path).is_symlink()` or if its `resolve()` isn't inside `lesson.dir.resolve() / "programs"`. Better still, open with `O_NOFOLLOW` and copy from the fd. Do the same check in `model.reference_errors` (it already stats the file at `model.py:188`) so `ptk validate` reports it with a pointer. Add a test that symlinks a secret and asserts the token appears in neither the error nor the report.

## P2

### P2-1 Compile has no memory or output cap (confidence 9/10)

`package/prax-teach/ptk/capture/c_runner.py:79`

```python
return host.run(sb, cwd=tmp, timeout=timeout, env=host.child_env({"TMPDIR": f"{Path(tmp).resolve()}/"}))
```

The compiler runs on attacker-controlled input with a 120 s timeout and nothing else. `#embed` of a large readable system file (the dyld cache pieces under `/System/Volumes/Preboot/Cryptexes/...` are allowed and up to 1.6 GB) took clang past 1.5 GB in 3.4 s and kept climbing. At that rate 120 s is enough to push a 24 GB Mac into heavy swap. `host.run` also reads stderr with no cap, so a source that expands into millions of warnings lands entirely in Python memory before `[-4000:]` is applied. E24 asks for memory capped across the process group in capture. The compile step is part of capture.

Fix: run compiles through `host.run_limited` with an RSS cap (2 GB is plenty for a lesson program), the same 1 MB output cap, and a shorter timeout (30 s). Banning `#embed` (P1-1) removes the cheapest trigger, but the cap is still needed. Add a test with a deliberately heavy compile and a low cap, plus the survivor check from `test_cleanup_after_kill`.

### P2-2 The compiler inherits the caller's whole environment (confidence 8/10)

`package/prax-teach/ptk/capture/c_runner.py:79` with `host.child_env` (`host.py:73`).

`child_env` copies `os.environ` minus a list of API keys. clang honours `CCC_OVERRIDE_OPTIONS`, and with `x-fsanitize=undefined,address` the sanitizers silently vanish from the cc1 line. I checked that with `-###`. Capture still writes the full flag list into every fact's `source.cmd`, so the provenance would claim sanitizers that never ran. `CPATH`, `C_INCLUDE_PATH`, `SDKROOT` and `DEVELOPER_DIR` change what gets compiled too. `PATH` also picks which `clang` and `gcc-16` run (`host.which`), and `toolchain_params` builds the read allowlist from wherever `gcc-16` resolves.

Fix: give compiles an allowlist env like `host.program_env`: `PATH=/usr/bin:/bin`, `TMPDIR`, `HOME`, `LANG=C`, `LC_ALL=C`, plus `DEVELOPER_DIR` and `SDKROOT` taken from `xcode-select -p` / `xcrun --show-sdk-path`. Pin the clang and gcc-16 paths through `host.registry()` or `ptk host probe` rather than `PATH`. Add a test that sets `CCC_OVERRIDE_OPTIONS` and still gets the ASan fixture blocked.

### P2-3 Too few output lines should be `ExpectationMismatch`, not a model error (declared deviation; confidence 7/10)

`package/prax-teach/ptk/capture/c_runner.py:176-178`

```python
raise errors.ModelReferenceError(f"fact {fact['id']} selects stdout line {sel['line']} but "
```

The model is valid: the fact names a real program and a legal line number. What differs is the run. AC-2.7 says that when capture differs from expect the build fails with `ExpectationMismatch` showing both. Today `ptk build` exits 3 and never shows what was expected, so the repair loop in `LESSON-MODEL.md` sends the agent to edit the model ("fix exactly what each pointer names") when the program is what changed. I don't accept this deviation.

Fix: in `capture_lesson`, record a missing line as `value: null` with a `missing` reason. Let `values.check_expectations` report `{"fact", "captured": null, "expected": ..., "reason": "program printed 1 line"}` and raise `ExpectationMismatch` (exit 1). `ptk capture` alone can keep exiting 0, or exit 1, as long as it names the line.

### P2-4 A bad platform sub-key crashes capture instead of exiting 3 (confidence 10/10)

`package/prax-teach/ptk/model.py:202` checks only the first segment:

```python
if f["select"]["stream"] == "platform" and f["select"]["key"].split(".")[0] not in PLATFORM_KEYS:
```

So `sizeof.int128` validates, and then `c_runner.py:167-168` (`val = val[k]`) raises a bare `KeyError`. `ptk capture` prints a Python traceback. `ptk build` records it as `internal` with exit 1. `captured.x` would raise `TypeError` the same way. §5.4 says a model error exits 3 with a pointer.

Fix: validate the full dotted path against a fixed shape (`sizeof.<one of the probe's types>`, `compilers.clang|gcc-16`, the scalar keys) and report `/facts/i/select/key`. In `select`, turn a lookup failure into `ModelReferenceError` with the same pointer. Add the case to `test_validation_errors`.

### P2-5 `sizeof_from_platform` checks the capture against itself (confidence 9/10)

`package/prax-teach/ptk/expect.py:49-50` with `ptk/verify/values.py:17-19`

```python
def sizeof_from_platform(platform, ctype):
    return str(platform["sizeof"][ctype])
```

The platform dict it reads is the one the capture probe just wrote, and the fact reads the same key from the same dict. The expectation can never disagree with the capture, so D17.5's "independent" expectation is a tautology for every sizeof fact, and the mutation suite can't catch a corrupted platform value. `PLATFORM_FUNCTIONS` makes this pattern official and easy to extend. The lint proves import independence well. Data independence is the gap.

Fix: compute it from something that isn't clang's probe, for example `ctypes.sizeof(ctypes.c_int)` (Python's own build ABI), with a fixed name-to-ctype table. That means adding `ctypes` to `EXPECT_ALLOWED_IMPORTS`. Or drop the function and require `{"value", "reviewed": true}` for platform facts, as the happy test already does for `char_signed`.

### P2-6 Expectation args run unbounded at validate time (confidence 8/10)

`package/prax-teach/ptk/model.py:142-145`

```python
try:
    fn(*args)
except (TypeError, ValueError, KeyError, IndexError, AttributeError) as e:
```

`_expect_problem` calls the expect function with whatever the lesson says. `bits(1, 10**10)` allocates `1 << 10**10` (about 1.25 GB) and can end in `MemoryError`, which isn't caught, so `ptk validate` crashes instead of exiting 3. `printf_f(1, 10**9)` builds a gigabyte string. `factorial(200000)` burns seconds before `str()` hits the int-digits limit. `switch_line(..., line=0)` returns the last line through index `-1` and doesn't fail at all.

Fix: bound the arguments in each function (width ≤ 128, precision ≤ 30, n ≤ 1000, line ≥ 1) and raise `ValueError` outside the bounds. Add `OverflowError` and `MemoryError` to the caught tuple as a backstop.

## P3

1. **The compile profile can still write anywhere under `/private/var/folders`** (`sandbox.sb:49`). Now that `TMPDIR` points into the temp dir, xcrun's cache is probably the only writer left there. Narrow it to the same `xcrun_db` regex used for reads, plus the per-user `C/` clang cache if a test proves it's needed. Confidence 6/10.
2. **`GCCROOT` comes from wherever `gcc-16` resolves** (`c_runner.py:67-69`). On Homebrew that's the whole `Cellar`, which is fine. A non-Homebrew install at `~/.local/bin/gcc-16` would make `~/.local` readable, and one at `~/bin/gcc-16` would open all of `$HOME`. Refuse a `GCCROOT` that is `$HOME` or contains it, or allow only the gcc, gmp, mpfr, isl, libmpc and zstd kegs. Confidence 8/10.
3. **The hard-coded Xcode plist and `xcrun_db` regex** (`sandbox.sb:78-81`): I accept this declared deviation. Neither holds secrets, and the regex only matches temp dirs the user already owns. Anchor the regex end (`xcrun_db[^/]*$`) so it can't match a sibling directory with a longer name.
4. **`ptk capture` never checks expectations** (declared deviation). I accept it as spec-compliant, since AC-2.7 assigns the check to the build. Still, put a non-fatal `expect` comparison in the capture JSON, so an agent iterating with `capture` sees mismatches before a full build.
5. **`printf_c` and `ascii` don't match C for bytes 128-255** (`expect.py:38-46`). C writes one raw byte, which the runner decodes with `errors="replace"` into U+FFFD, but `chr(200)` is `È`. That's a false mismatch, not a false pass. Either reject codes above 127 or model the replacement.
6. **`test_compile_cannot_embed_outside_files` assumes `PTK_STATE` lives under `$HOME`** (`tests/test_security.py:257`) and fails anywhere else, for example a CI box with state in `/tmp`. Make the secret dir with `tempfile.mkdtemp(dir=Path.home())` and clean it up, so the test proves the point on any install.
7. **The `ptk new` scaffold pre-asserts review** (`model.py:342`, `"expect": {"value": "hello", "reviewed": True}`). That teaches agents to type `reviewed: true` without a review. Make the value `"TODO: hello"` so the placeholder check lists it, or use `{"fn": ...}`.
8. **`ub_covered` exists twice**: `c_runner.py:52-55` and `model.py:192-193`. Keep one helper (the model may import it, since nothing forbids model → capture) so the two can't drift.
9. **Trace `vars` and the new `frames[].vars` are display strings with no fact or expect behind them** (schema `$defs/state`). Nothing projects them yet, but once WP4 does, they skip D17.5's values gate. Either make them fact refs or add a validation rule before WP4 lands.

## Focus questions, answered

- **Sandbox escapes.** `MODE=run` held up against everything I tried. Fork and `posix_spawn` are denied, mach lookups are denied, reads are limited to the temp dir and system libraries, and the env is an allowlist. Its tests prove denial with an unsandboxed control. The escapes are all around compile: P1-1 (the guard), P1-2 (symlink, outside the sandbox), P2-1 (resources), P2-2 (environment). `__has_include` of a file in `$HOME` turns into an `Operation not permitted` fatal error, so it leaks whether the file exists. That's one bit, visible only in an error, so I didn't count it.
- **Do the tests prove behaviour?** Mostly yes. The security tests each pair the sandboxed denial with an unsandboxed success. The ub test uses a never-terminating fixture, so a wrongful run would fail on its own. The nondeterminism fixture prints the pid. The embed test has a control compile. The missing tests are adversarial ones: pragma and attribute bypasses, symlinks, heavy compiles, and a hostile environment.
- **expect.py independence.** Import independence is proven well: AST allowlist, planted violations, and a fresh-interpreter `sys.modules` check. Data independence is broken for sizeof (P2-5).
- **Exit codes vs §5.4.** `validate` 3, sandbox missing 2, sanitizer, compile and run failures 1, `new` errors 3: all correct. Wrong: a bad platform sub-key (traceback, P2-4) and too few lines (3 instead of 1, P2-3).
- **Declared deviations.** Added schema fields: fine, every new object is closed (watch P3-9). TODO markers: good. Hard-coded plist and `xcrun_db`: fine (P3-3). Expect check only in build: fine (P3-4). Too few lines as exit 3: fix it (P2-3).
- **Broad excepts and the subprocess boundary.** No new broad except. `test_no_broad_except` and `test_subprocess_boundary` pass. Every new subprocess call goes through `host.run`.

## Disposition (WP2 fix round 1)

Fixed: P1-1, P1-2, P2-1, P2-2, P2-3, P2-4, P2-5. Tests are named in the `wp2 fix:` commit messages. Deferred:

- **P2-6** (unbounded expect args at validate): not in this round's scope. It crashes `ptk validate` on a hostile literal but can't produce a wrong fact. It goes with the next expect.py pass.
- **P3-1** (compile writes anywhere under `/private/var/folders`): TMPDIR now points into the temp dir and compiles are capped. Narrowing the profile needs a proof run of what xcrun still writes there.
- **P3-2** (GCCROOT from wherever gcc-16 resolves): partly closed, since gcc-16 is now pinned to `/opt/homebrew/bin` or `/usr/local/bin` before PATH. The keg allowlist is left for the sandbox-profile pass.
- **P3-3** (anchor the `xcrun_db` regex): accepted deviation, one-character profile change. It belongs with P3-1 so the profile is proven once.
- **P3-4** (non-fatal expect check in `ptk capture` output): a nice-to-have. The build already shows mismatches, and too-few-lines now raises ExpectationMismatch from capture itself.
- **P3-5** (`printf_c`/`ascii` above 127): a false mismatch, never a false pass. It goes with P2-6.
- **P3-6** (embed test assumes `$HOME`): mostly done. The rewritten test no longer asserts `$HOME`, and the secret only has to sit outside the compile read allowlist. No secret is written outside v2.1/.
- **P3-7** (`ptk new` scaffold pre-asserts review): it changes `test_new_scaffold`'s placeholder contract. Left for the scaffold owner.
- **P3-8** (`ub_covered` twice): left alone to keep this diff on the P1s. The new override rule lives in one helper (`guard.allowed_constructs`).
- **P3-9** (trace `vars` with no fact behind them): belongs to WP4's projection work. It needs a rule before WP4 projects `vars`.

Residual, not a guard switch-off: calling `printf` through a function pointer hides `-Wformat`, and UBSan doesn't check varargs types. It's a limit of static warnings, recorded here for the E19 caveat.
