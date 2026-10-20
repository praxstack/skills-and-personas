# Continuation candidate handoff

Product source: `6f4304691f5a08b6d0d544abaf70b3cee467cd64`.
This is an unaccepted v3.0.2 candidate, not a stable release or an installation.
The installed v3.0.1 snapshot remains unchanged.

## Reviewed repairs

The continuation adds aggregate resource budgets, explicit course/enrichment
container boundaries, bounded child-process cleanup, optional-download guards,
portable portfolio diagnostics and repaired transcript packaging. Earlier
receipts in CONTINUATION-VERIFICATION.md retain their exact revision limits.

Independent final reviews also confirmed:

- Manim inventory does not execute workspace interpreters by default. Explicit
  trusted probing shares interpreter resolution with the renderer; 22 focused
  controls and vendor verification passed.
- Redirect response bodies are discarded before Requests can drain them outside
  the budget. The original 2 MiB bypass reproduction now consumes zero redirect
  bytes and charges the two-byte final response. Both runtime copies passed
  26 transport/budget controls; same-origin cookie/manual-redirect controls
  passed for 301, 302, 303, 307 and 308.
- The course supervisor preserves the owned child's failure/signal status while
  reaping adopted exits. Independent review passed ten focused lifecycle controls.
- New CI uses explicit Bash failure propagation, rejects missing required
  runtime controls and consumes actual lesson/visual status receipts. Archive
  assembly rejects unmanifested source files. These are product regression
  checks, not replacements for frozen evaluators.

The controller's core run at `26eb50f` passed 67 tests and skipped four optional
tests. Five transcript packaging controls passed in the prepared Requests
environment; the first system-Python attempt failed because Requests was absent.
No source or assertion was changed to conceal that environment failure.

Remote [CI run 39468515529](https://github.com/praxstack/skills-and-personas/actions/runs/39468515529)
passed both jobs on the exact product commit. Downloaded host provenance confirms
that commit, ARM64 Ubuntu, Python 3.11.17 and Node 22.23.3. The required runner
executed 132 controls with zero skips, including two real browser callback
controls, 21 course tests and 51 tests in the enrichment sandbox suite. Three fresh
synthetic-media containers each passed 22 existing render checks and both QA
statuses. These synthetic fixtures do not clear the separate local narrated-media
repeatability failure. The controller read the downloaded logs rather than
inferring these results from a green status alone.

The parallel pull-request [CI run 39468522046](https://github.com/praxstack/skills-and-personas/actions/runs/39468522046)
failed at the same product head. Security and required controls passed, but the
second fresh synthetic-media container failed. Its downloaded log shows
`pthread_create: Resource temporarily unavailable`, three PID-limit events,
`AUDIO_RENDERER_ERROR`, and a playback timeout. The sandbox failed closed without
publishing output. This reproduces the resource-pressure failure remotely:
synthetic-media CI is **not reliably passing**, despite the successful run above.
No retries, limit increases or weaker assertions were used to erase this result.

## Local deliverables

These artifacts were built locally from the exact product commit above.
They have not been uploaded as a public release or sent to Dot.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| Current source and demo | 26,327,700 | `39a43e9a7619797af736ecc2ff965b13eb9f27f7e2b7fe1ecb3a58c95e7f69ff` |
| Complete historical-inclusive handoff | 668,852,120 | `2d2cde881421ddb9f3ce91468694517f79585d337361a15a49ddc24ec7d88059` |

Source archives repeated byte-identically. Temporary combined and standalone
installation checks passed, including 22 subskills, vendor verification and the
759-file embedded verifier. Both video encodings fully decoded. Archive CRCs and
every member hash were checked; the controller separately matched both final ZIP
hashes. The older 644,145,442-byte handoff retained its original hash.

The handoff includes current committed source, the six-format demo, both video
encodings, seven narration clips and explicitly staged historical artifacts.
The demo comes from an identified earlier observed-pass run; it is not a fresh
render of the final runtime. Its later failed repetitions are retained alongside
the positive evidence. External engines and runtime weights are not bundled.
Private test banks, credentials and raw agent-session logs are excluded.

## Still open

1. **Narrated playback reliability:** three consecutive fresh-container passes
   were not achieved within the unchanged 64-task/512-MiB limits. The reaping fix
   helps but does not close this failure. The ineffective launch experiment was
   reverted. Synthetic CI media cannot substitute for this narrated-artifact
   requirement. The parallel remote synthetic-media run also failed at its
   second container with thread exhaustion and an audio renderer error.
2. **Course consent checker:** the frozen checker expects persistence without
   storage consent. Its separately versioned correction still requires the
   human-owned governing-change decision. Product privacy was not weakened.
3. **Release acceptance:** the above blockers and human visual acceptance remain
   separate from successful packaging and the single successful CI run.
4. **Broader portfolio/history work:** divergent identities, remaining lint/link
   debt, portfolio-wide capability/library adoption and destructive public
   history cleanup have not been silently declared complete.

No merge, stable publication, live installation, public-history rewrite or
governing-evaluator change is represented by this handoff.
