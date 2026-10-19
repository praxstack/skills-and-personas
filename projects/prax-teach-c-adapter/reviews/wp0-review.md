# WP0 review: Prax Teach v2.1

Scope: `git diff 5e48978..HEAD` for `package/prax-teach/**` and `lessons/switch-fallthrough/**`.
Read against `spec/SPEC.md` (AC-0.1 to AC-0.5, §5) and `plan/CEO-PLAN.md` (D17 to D19, E0 to E25).
I did not read `holdout/` or `plan/proposed/`, and I didn't edit or rebuild anything.

## What I checked myself

- `ptk selftest`: 8/8 passed, exit 0 (setup inventory, env contract, three lint tests, whisper, render isolation, entry by direct path).
- `ptk report lessons/switch-fallthrough`: `verified`, exit 0, 24 gates, all passed, none not-run.
- The capture `run` profile, probed with two small C programs under the real `sandbox.sb` with `MODE=run`:
  - `posix_spawn` is blocked (EPERM);
  - writing to `$HOME` is denied;
  - reading `~/.zshrc` works;
  - mach lookups of `com.apple.coreservices.launchservicesd`, `com.apple.lsd.open`, `com.apple.nsurlsessiond`, `com.apple.pasteboard.1` and `com.apple.coreservices.appleevents` all succeed.
- Frames pulled from `build/video/lesson.mp4` at 3, 30 and 44 s, plus the wide light still, compared with `ive/states.vtt`.

The implementer's numbers hold up: the five ACs pass their tests as written, and the report really is 24/24. The problems are in what some of those tests and gates actually prove.

## Counts

| Severity | Count |
|---|---|
| P0 | 0 |
| P1 | 4 |
| P2 | 9 |
| P3 | 12 |

## Verdict

Fix first. None of the four P1s is a big change, and the slice itself is well built. But two of them can make `ptk` tell an agent "deliver this" when the claims were never reviewed or the build crashed. One is a pause-state bug that the IVE gate can't see by design. The fourth leaves the capture sandbox reachable over mach IPC. Fix those four, then ship WP0. The P2s can ride along with WP2, WP5 and WP7, where their ACs live.

---

## P1

### P1-1. A degraded build skips the claims review and exits 6 ("deliver")

- **Confidence:** 9/10
- **Where:** `ptk/build.py:66-76`

```python
    if "not-run" in st:
        return "incomplete"
    if degraded:
        return "degraded"
    if "pending" in st:
        return "claims-pending"
```

**Why it matters.** `degraded` is checked before `pending`. When TTS falls back to `hyperframes tts` or `say`, `build()` lands on `degraded` while `claims.review` is still `pending`, and the exit is 6. SKILL.md and D19.5 tell the agent to "deliver, naming the fallback" on 6. So a fallback build ships with no claims review at all. D18.1 defines degraded as "all gates passed but a fallback was used", and a pending gate hasn't passed.

**Fix.** Put `pending` before `degraded` in `final_status`. `claims_check` already carries `fallbacks` into the final status, so a reviewed fallback build still ends `degraded`. Add a unit test: degraded=True plus a pending gate must give `claims-pending`.

### P1-2. A crashed build leaves the previous "verified" report in place, and the crash exits 1

- **Confidence:** 8/10
- **Where:** `ptk/build.py:125-138`, `ptk/cli.py:116-122`

```python
    except errors.PtkError as e:
        ...
        save(lesson, rep)
        raise
```

**Why it matters.** The report is written only at the end, or on a `PtkError`. Any other exception escapes as a Python traceback, and Python exits 1, which is the same code as "a gate failed". A few ways that happens:

- an unknown `expect.fn` raises `KeyError` at `expect.py:94-96`, because the schema only checks the name's pattern;
- the loudness regex returns None and raises `AttributeError` at `media.py:36`;
- a malformed cue payload raises `JSONDecodeError` at `values.py:93` or `claims.py:128`.

SKILL.md says that on exit 1 the agent should "read `ptk report`". That report is the last successful build's, which says `verified`, exit 0. This is exactly the "never report a half-built lesson as done" case that D19.5 exists to prevent.

**Fix.**
1. Write a `status: "draft"` report (or delete the old one) at the very start of `build()`.
2. In `cli.main`, map any non-`PtkError` to a distinct internal-error exit that isn't 1 (or wrap it as a `PtkError` subclass with exit 2), and record it in the report.
3. Validate `expect.fn` against `expect.FUNCTIONS` in `model.reference_errors`, so it fails at validate time with a JSON pointer.

### P1-3. In the recap, the IVE explorer and the video frame show different states for about 5 s, and the pause gate can't see it

- **Confidence:** 8/10
- **Where:** `ptk/project/video.py:171-173`, `ptk/project/ive.py:43-65`, `ptk/verify/visual.py:319-325`

```python
    if prev["program"] != cur["program"]:
        prev = {"program": cur["program"], "line": cur["path"][0] if cur["path"] else cur["line"], "path": [],
                "output": [], "vars": cur["vars"]}
```

**Why it matters.** sc7 (Recap, state s3) follows sc6 (state s4, program p2). Because the program changes, the projector resets `prev` to "line 4, no output". From 42.63 s to the reveal at 48.07 s, the video shows `fallthrough.c` at line 4 with an empty output box (see the 44 s frame). Over the same window, `states.vtt` cue m10 says state s4: `with_break.c`, output `two, done`.

A learner who pauses during the first recap sentence sees one program in the frame and another in the explorer. That breaks D18.2's "the last state already shown on screen".

`ive.pause-state` passes because it compares the page to `cue_list`, and `cue_list` comes from the same `timing` rather than from what the composition draws. It's a self-referential check. sc6 has the same reset for 0.37 s.

**Fix.**
1. Make one function own "what is on screen at time t" (prev state, current state, reveal and settle), and have both `scene_html` and `ive.cues` call it.
2. For a scene whose state was already shown earlier (a recap), don't replay: set `prev = cur`.
3. Add a gate that checks the frame: seek the composition (or the MP4) at each cue midpoint and compare the highlighted line and the output-box text (the OCR path already exists) with the cue's state.

### P1-4. The capture `run` profile is `allow default`, so lesson programs can reach LaunchServices, nsurlsessiond, Apple Events and the pasteboard

- **Confidence:** 6/10 (I confirmed the services are reachable; I didn't run a full escape, because that would launch apps on this Mac)
- **Where:** `ptk/capture/sandbox.sb:16-20` and `47-51`

```scheme
(version 1)
(allow default)

;; ---------- network ----------
(deny network*)
```

**Why it matters.** Network, writes and fork are denied, and `posix_spawn` is blocked too, which is good. But everything else is allowed. From inside `MODE=run` I could look up:

- `com.apple.lsd.open` and `launchservicesd`: open a `.command` file written to TMP, and Terminal runs it outside the sandbox;
- `com.apple.coreservices.appleevents`: script another app;
- `com.apple.nsurlsessiond`: a daemon that makes network requests for its callers;
- `com.apple.pasteboard.1`: read the clipboard.

Reads are also unrestricted (`~/.zshrc` opened fine). Whatever a program reads can then land in stdout, which becomes a captured fact and goes into artifacts.

D17.10 says capture "denies network and file writes outside its temp dir", and a daemon making requests on the program's behalf is a network path. There's also no WP0 test of the `run` mode at all: the only canaries test `render`.

**Fix.**
1. Make `MODE=run` deny-default:
   - `(deny default)`;
   - `(allow process-exec (literal EXE))`;
   - `(allow file-read*)` limited to `/usr/lib`, `/System`, `/private/var/db/dyld`, the dyld cache and TMP;
   - `(allow file-write* (subpath TMP))`;
   - only the `mach-lookup` names ASan and UBSan actually need (find them by running the sanitizer fixtures under `(deny default)` with `(debug deny)`).
2. Add `tests/test_security.py` now rather than in WP2: from MODE=run, assert that connect, write outside TMP, fork, `posix_spawn`, a read of `$HOME`, and `bootstrap_look_up` of `lsd.open`, `nsurlsessiond` and `pasteboard.1` all fail.

---

## P2

### P2-1. Setup writes outside `$PTK_STATE`, and the font-hash check approves itself

- **Confidence:** 9/10
- **Where:** `ptk/host.py:340-343`, `474-492`; `tests/test_host.py:36-38`; `tests/fixtures/write-jail.sb:7-8`

```python
def _write_font_sums():
    lines = [f"{sha256_file(p)}  {p.name}" for p in sorted(FONTS_DIR.iterdir())
             if p.is_file() and p.name != "SHA256SUMS"]
    (FONTS_DIR / "SHA256SUMS").write_text("\n".join(lines) + "\n")
```

**Why it matters.**
- AC-0.1 says "no writes outside `$PTK_STATE`". Setup rewrites `package/prax-teach/assets/fonts/*`, and the write jail allows that dir plus all of `/private/var/folders`.
- The test then checks each woff2 hash against the SHA256SUMS that setup just generated from those same files. That proves nothing about pinning.
- The fonts are already committed, so setup doesn't need to touch the package.

**Fix.**
1. Commit SHA256SUMS as the pin. Setup verifies the committed woff2 files against it and never writes into the package.
2. If re-subsetting is ever needed, write to `$PTK_STATE/fonts`.
3. Drop the `FONTS` and `/private/var/folders` allowances from the jail, or justify them, and note the spec tension between §5.1 and AC-0.1.

### P2-2. The sensitivity gate is easy to pass

- **Confidence:** 8/10
- **Where:** `lessons/switch-fallthrough/mutations.json`, `ptk/verify/claims.py:262-292`, `references/CLAIMS-RUBRIC.md` (rule 6)

```json
{"claim": "c.labels", "kind": "false-mechanism",
 "text": "Each case label acts as an implicit break, so the switch stops before it runs the statements under the next label."}
```

**Why it matters.**
- There's one mutation, and it restates the lesson's own misconception `m.stops`, which ships in the job. Rubric rule 6 says to reject anything that restates a misconception, and the source quote for `c.labels` says the opposite. The reviewer's reason literally cites "misconception m.stops".
- The private map (`build/claims-private.json`) and `mutations.json` sit on disk next to the jobs. A subagent with file tools can read them; only HOST-ADAPTERS.md asks it not to.
- "Every round rejected the planted claim" is a weak signal at n=1.

**Fix.**
1. For WP0, add at least three mutations that are *not* in `misconceptions[]`: a wrong clause citation, an overgeneralised "always", and a swapped value in narration.
2. Keep the private map outside the lesson tree (`$PTK_STATE/claims-private/<lesson>.json`).
3. Write mutation and control jobs to a staging dir the reviewer is pointed at, with nothing else in it.

### P2-3. Claim mapping accepts fragments, so dropping a "not" still maps

- **Confidence:** 7/10
- **Where:** `ptk/verify/claims.py:166`, `174`, `184`

```python
    return re.fullmatch(pat, t, flags=re.I | re.S) is not None or t.lower() in tpl.lower()
...
        if ref in claims and t in _norm(claims[ref]["text"]):
```

**Why it matters.**
- Any substring of a claim maps to that claim. "It does not stop execution." truncated to "stop execution." still maps to `c.labels`.
- Any substring of any chrome template counts as chrome.
- Template placeholders become `.+`, so a chrome string with `{lines}` accepts any teaching text in that slot.

AC-7.3 wants every teaching sentence mapped to a claim. A gate that passes on fragments only partly enforces that. The reviewer subagent may still catch it, but the mapping gate is meant to be the mechanical floor.

**Fix.**
- Require whole-sentence equality: the artifact sentence must equal one of `text.sentences(claim.text)`.
- Drop the `t in tpl` fallback.
- Type each placeholder (`{lines}` matches `fact` values only) and verify those values.

### P2-4. The alt text's output sentence is tagged as facts but never compared with them

- **Confidence:** 7/10
- **Where:** `ptk/verify/claims.py:93-98`, `ptk/verify/values.py:40-48`

```python
                    if _chrome_match("alt_output", sent):
                        # the alt text's output sentence states captured values: tag it with those facts
                        raw.append(("fact", ",".join(shown), sent, svg.name))
```

**Why it matters.** "Output of programs/fallthrough.c: two, three, done." is a teaching surface for screen-reader users.

- `map_item("fact")` only checks that the fact ids exist.
- `values.check_svg` only reads elements that carry `data-fact`, and `<desc>` has none.

It's correct today because the still projector builds it from the facts, which is correct by construction, not by gate.

**Fix.** In the values gate, parse the `alt_output` sentence back into its values and compare them with `text.display(fact)` and the `expect`, in order.

### P2-5. The answer-leak gates can't see digits or multi-word answers, and the transcript check doesn't look for leaks

- **Confidence:** 8/10
- **Where:** `ptk/verify/media.py:202-229`, `ptk/verify/visual.py:250`

```python
                hit = words & set(re.findall(r"[a-z']+", c["text"].lower()))
...
        for line in pre:
            if line not in tx:
                leaks.append({"where": "transcript", "problem": "pre-answer line missing", "line": line})
```

**Why it matters.**
- The answer words are whole lines of the fact value, while the text is split into runs of letters. An answer like `2`, `x = 2` or `0x42` can never match, and neither can any line with a space in it. The switch lesson passes only because its answers are single lowercase words.
- The transcript part checks that pre-answer lines are *present*. It never scans the transcript for answer words.

AC-5.7 and M20 name the transcript explicitly. WP9's "one byte, four views" exemplar has numeric answers, so it would pass this gate blind.

**Fix.**
1. Tokenise both sides the same way (`text.norm_words`, digits included).
2. Match multi-token answers as phrases.
3. Scan the transcript up to the answer cue's scene for answer tokens.
4. Add a fixture with a numeric answer that must fail.

### P2-6. AC-0.5's evidence is true by construction

- **Confidence:** 7/10
- **Where:** `ptk/build.py:41-44`, `tests/test_slice.py` (`test_entry_by_direct_path`)

```python
    return {"skill_md": str(skill), "skill_md_sha256": ..., "ptk": str(host.PKG / "bin" / "ptk"),
            "registration": "none (direct path, D19.3)"}
```

**Why it matters.** `build.py` always writes this constant, whoever ran the build and however they got there. The test then asserts that constant, plus "SKILL.md mentions some commands" and "no host dir holds the candidate". None of that shows the slice was produced *by loading SKILL.md*. A build run straight from the CLI would pass the same way.

**Fix.** Keep the evidence AC-0.5 actually needs: the transcript of a fresh agent session that got only the fixed request and the SKILL.md path. Store it (or its hash and location) under `reviews/` or `.state/`, and have the test check that it exists and names the same lesson sha256 as the report. Label the `entry` field as "build invoked via bin/ptk", which is all it can show.

### P2-7. The video wastes space, has no control-flow arrow, and the recap resets

- **Confidence:** 9/10 (I checked frames and the composition source)
- **Where:** `ptk/project/video.py:163-164`, `194-200`, `236-246`, `171-173`

```python
LINE_H = 46
CODE_TOP = 250
...
    tl.to(q('#hl'), {{ y: {hl_to + 24}, duration: 0.45, ease: 'power2.inOut' }}, R);
```

Checked against the orchestrator's frame review:

- **Empty bottom: partly confirmed.** The code card ends at about y=944 of 1080, so the bottom 13% is empty across the full width. The right column ends near y=800, so about 26% is empty there. "About 25%" is right for the right column and generous for the left. The cause is fixed values: `LINE_H` 46, `CODE_TOP` 250, a fixed 620 px side column, and nothing sized to fit 1080.
- **No arrow: confirmed.** The still draws the path rail with arcs and arrowheads (`still.py:199-210`: the 5→8 jump and the 12→16 exit), plus "enters here", "no break" and "skipped" tags. The video draws only a `#hl` bar that slides from line to line, and dots. The jump into case 2 and the run straight past the `case 3:` label, which are the whole idea of the lesson, never appear in motion.
- **Recap reset: confirmed.** See P1-3. The 44 s frame shows line 4 highlighted and an empty OUTPUT box under "Recap".

**What the projector should do.**
1. Move the rail geometry (dots, straight runs, jump arcs, the "no break" badge position) out of `still.py` into one shared module that both projectors call. The still and the video then draw the same picture.
2. In each scene, draw the new path segment at `reveal` with a stroke-dashoffset tween:
   - sc3 draws the 5→8 jump arc and its arrowhead;
   - sc4 draws the straight run from 9 through 10 to 11, crossing the `case 3:` label, with a "no break" badge pulsing on line 10;
   - sc5 draws the 12→16 exit arc;
   - sc6 shows `with_break.c` with its own 10→16 exit arc.
   Keep the highlight bar as a secondary cue, not the main motion.
3. Recap: show the settled full path with all its arcs and the full output (`two`, `three`, `done`), with no replay. Optionally add a small side-by-side output card for `with_break.c`, which also fills the empty band.
4. Size the layout to the frame: compute `LINE_H` from `(1080 - CODE_TOP - bottom margin) / n_lines`, make the side column the same height as the code card, and let the note fill the space below the output card. Add an AC-5.6 style snapshot check that fails when more than about 12% of the frame height is empty below the lowest element.

### P2-8. The hyperframes check treats a missing count as zero

- **Confidence:** 6/10
- **Where:** `ptk/build.py:180-182`

```python
        clean = hf.get("ok") and all((c["errors"] or 0) == 0 and (c["warnings"] or 0) == 0 for c in counts.values())
```

**Why it matters.** If a HyperFrames update renames `errorCount`, or drops one of the five sections, then `None or 0` passes. If all five sections go missing, `counts` is empty, `all([])` is true, and `ok: true` alone passes the gate. AC-5.1 needs "0 errors and 0 warnings", so a missing count isn't zero.

**Fix.** Require all five sections, and require each count to be an int. A missing section or count fails the gate with a reason.

### P2-9. A claims job costs about 115k tokens; fine for WP0, too much for WP7

- **Confidence:** 7/10
- **Where:** `ptk/verify/claims.py:228-244`

**Why it matters.** Each job is about 50 KB: 160 artifact texts, most of them chrome, line numbers or code that the rubric doesn't need. AC-7.1 allows 12 mutations plus controls, so about 25 jobs, or roughly 3M tokens per lesson.

**Fix.** Send the reviewer only claim-bearing texts (`claim`, `narration`, `alt`, `question`, `trace`). List the others by count and hash in the manifest so they stay bound. I accept the deviation for WP0, but trim the jobs before WP7.

---

## P3

### P3-1. gcc-16's exit code is ignored, and its warnings never surface

- **Where:** `ptk/capture/c_runner.py:63-68`

```python
    res = host.run(host.sandboxed([gcc, *GCC_FLAGS, ...], "compile", tmp=tmp, proj=tmp), cwd=tmp, timeout=120)
    return res.stderr.strip()
```

A gcc error is swallowed as a string. gcc's `-Wimplicit-fallthrough` warning on lines 7 and 9 is the lesson's own topic, but it only appears in the claims job. Record `res.code`, and fail on a non-zero code. Consider a claim citing the warning.

On the declared deviation: I accept `-c` instead of `-fsyntax-only`. It runs more of the compiler and still never runs the object.

### P3-2. The render profile can write all of `$PTK_STATE` and `/private/var/folders`

- **Where:** `ptk/capture/sandbox.sb:39-45`

The render process can rewrite the pinned toolchain (venvs, `tools/node`, browsers) and other apps' per-user caches. Narrow it to `$PTK_STATE/home`, `$PTK_STATE/tmp` and the project.

### P3-3. Secrets are stripped by a denylist

- **Where:** `ptk/host.py:33-36`, `74`

Anything not listed (`MEM0_API_KEY`, `XAI_API_KEY` and so on) reaches every child, including the sandboxed program, whose stdout becomes facts. Use an allowlist env for `run_limited` and `MODE=run`.

### P3-4. The setup inventory is overwritten on rerun

- **Where:** `ptk/host.py:335`, `390-394`

This is a declared deviation. On a rerun every item says `present`, and the venv's `packages_installed_now` is empty, so the original fetch provenance is lost. I accept it for WP0. Keep the first-fetch record, or append runs.

### P3-5. The AC-0.3 fixture lives outside the repo

- **Where:** `tests/test_media.py:9`

```python
PROOF = V21.parent / "clean-install-20261018" / "review-20261018" / "proof" / "video"
```

On any other checkout this test is `not-run`, and selftest then exits 5. Copy a short clip into `tests/fixtures`, or pin its sha256 and say where to get it.

### P3-6. Hard-coded platform

- **Where:** `ptk/host.py:434`, `registry/tools.json:18,50`

`chrome-headless-shell-mac-arm64` is baked in. There are no `/Users/` strings in the package, which is good. Claims jobs carry absolute `rubric_path` and `review_path`, but they live only in the ignored `build/`, so that's fine.

### P3-7. Duplicate "body of main" logic

- **Where:** `video.py:142-147`, `ive.py:35-36`, and the still

There are three copies, with a magic default of `4`. The still starts at line 3 and the video and IVE start at line 4, so the same program shows different line ranges across media. Answer-word extraction is also duplicated (`media.py:202-203`, `visual.py:277`). Use one helper for each.

### P3-8. Dead code

- **Where:** `ptk/verify/claims.py:73-75`

`_merge` returns its input and is never called. Delete it.

### P3-9. The lint tests are shallow

- **Where:** `tests/test_lint.py:30`, `41`; `ptk/selftest.py:16-17`

- The subprocess check only matches import lines. `import os, subprocess` passes, and so does `importlib.import_module("subprocess")`.
- The broad-except check misses tuples that contain `Exception`.
- `EXPECTED_FAILURES` is close to a broad except: it lists ten classes, including `RuntimeError` and `OSError`.

Walk the AST for `Call` nodes that resolve to `subprocess.*` or `os.exec*`/`os.spawn*`. Treat tuple handlers too.

### P3-10. The IVE fonts gate is weaker than the still's

- **Where:** `ptk/verify/visual.py:363-364`

```python
    fams -= {"monospace", "serif", "cursive", "Georgia"}
```

It subtracts Georgia and doesn't check `loadedFaces`, so a page rendering in Georgia would pass. Check the loaded faces, as `still_gates` does.

### P3-11. The RSS watchdog spawns `ps` 50 times a second

- **Where:** `ptk/host.py:158-166`, `217`

It's fine for 5 s runs, but heavy and racy. Sample every 100 ms, or use `proc_pidinfo` through `psutil` if it goes into the core venv.

### P3-12. Small items

- `claims_check` doesn't confirm that the artifact hashes in `rep["artifacts"]` still match before it calls the build verified (`build.py:220-243`).
- A `.DS_Store` is committed in the diff.
- Update the spec and `references/LESSON-MODEL.md` for the schema additions `select`, `figure` and `diagnostics`, which is a declared deviation. I accept it, but the spec §5.2 sample no longer matches.

---

## Declared deviations: my calls

| Deviation | Call |
|---|---|
| gcc-16 with `-c`, not `-fsyntax-only` | Accept. Check the exit code (P3-1). |
| Sync uses whisper plus ffmpeg silencedetect | Accept for now. The silence edges come from the final MP4's own audio, and the cue time isn't used to choose them, so this doesn't bias toward passing. WP5 still needs the E17 fixtures (shifted audio, truncated speech, a mispronounced token) before AC-5.5 can close. |
| Answer cue at visible start | Accept. It's earlier than the spoken answer, so it's the safe side for leaks. |
| Schema gained `select`, `figure`, `diagnostics` | Accept. Update the spec (P3-12). |
| AC-6.3 vs AC-6.4 noscript conflict | Accept the resolution (the leak check runs on the JS page). Better still, put the post-answer part of the noscript transcript inside a `<details>` "Show the answer", and record the amendment in the spec. |
| Setup inventory overwritten on rerun | Accept for WP0 (P3-4). |
| About 115k tokens per claims job | Accept for WP0, but trim before WP7 (P2-9). |
