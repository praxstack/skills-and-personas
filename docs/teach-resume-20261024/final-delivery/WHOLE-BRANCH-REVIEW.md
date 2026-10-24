# Final whole-branch senior review

Reviewed range: `ef3f5fe52b8191b5c5c168b70687a55718b8f6c1..31b9ced801c703edf4ef5b191d1b416582411830` (46 commits). Product snapshot: `eaa524e`; method adoption: `bf0bcf9`. Read-only review; only this requested report is written. No subagents, source/index/HEAD mutations, suite reruns, installation, release or publication.

## Spec compliance

The product and method implementation follows the approved continuation: visual explanation precedes optional practice; the frequency, stable-merge and momentum exemplars expose mechanisms and state their assumptions. Consent v2 is separately named and selected explicitly, with historical v1 retained. The pool change preserves process/audio isolation, exact browser identity and 64-task/512-MiB/no-swap/one-CPU course limits. Generic caption and chapter repairs preserve native cue data and supplied scene metadata. Transcript output and selected-manifest protections are narrowly described; VENDOR retains upstream provenance while recording local edits.

The final packaging/documentation task has one unresolved delivery-boundary issue below: a shipped regression runner requires files absent from its archive. Current operational documentation also contradicts current approved consent/playback status. These are distinct from the correct current top-level delivery README and retained historical failure receipts.

Fresh independent fixtures were initially tested after source freeze and exposed real defects. The final successful replays are explicitly disclosed-case regressions, not fresh blind post-repair passes. This is a genuine evidence limitation, not a reason to rewrite failures or relax the frozen evaluator.

## Scope and evidence checked

- Read the dispatch first, reviewer instructions, current plan, global constraints and progress ledger, Task 1/2/3 implementation reports and independent reviews, including the additional chapter-precision diagnosis. Read all authored changes in `final-primary-source.diff` and `final-example-source.diff`, recovering truncated output in smaller passes. Repeated voice/pydeps/EdgeTTS hunks across the 11 video engines were checked for exact hunk identity and reviewed through their representative copy. No authored subsystem was excluded.
- Scope includes both workflows; security policy; portfolio audit/link/path repairs; candidate/source/handoff packaging; CI setup and execution; tool discovery/Manim resolution; explicit model/package/network acquisition controls; course sandbox, cancellation and reaping; consent checker adoption; player/caption/chapter/report changes; transcript budgets, HTTP redirect/browser transport, manifest/output confinement, enrichment sandbox; their ordinary and real-boundary tests; and all three authored exemplar sources/reproduction helpers.
- Scanned all **628** full-patch sections. Reconstructed **521** complete added text payloads and compared them with current files: **zero mismatches**. Accounted for **36** binary markers. This checks package/receipt traceability, not the semantic truth of every historical log line.
- Independently verified **22** omitted new-skills mirrors against their primary bytes and recorded hashes; the three distinct new-skills paths remain in the authored review.
- Independently verified the four final `source-eaa524e` ZIPs against `repeat-eaa524e`, archive hashes, every **3,303** member hash/mode, and **1,681** complete-archive files against current source. These identities are correct; identity alone does not establish dependency completeness.
- Independently verified **36** final demo members against `delivery-manifest.json` and all **six** frozen governing source hashes against preservation evidence. Current demo/source directories are versioned separately from preserved d808 snapshots.
- Independently inspected all three final original render check arrays, error/network arrays and 13 runtime phases per run. Results: **22/22**, both QA return codes 0, durations **26.632/26.252/26.250 s**, peaks **59/59/60 tasks**, all PID events `max 0`. Read final immutable-case regression scope and the initial/additional failure records; no blind-success relabeling found.
- Read current UI control receipt and its checker code, plus local suite command records and raw result summaries: teacher71/100 with the two disclosed unrelated fixture skips, transcript33, output10, parity5, wrapper4, code sandbox8, enrichment sandbox51 and browser2. Did not rerun those suites. Task 3's independent report supplies installed1546/five-link preservation and visual screenshot inspection; this reviewer did not independently repeat those live checks.
- One focused unanswered-risk probe only: extracted the exact final source ZIP into a temporary directory and invoked its shipped runner for `scripts/test_render_receipts.py`. It exited1 with `Ran 0 tests` / `NO TESTS RAN`. No existing suite was rerun.

## Strengths

- Isolation is implemented at the actual process/filesystem/transport boundaries, not inferred from skill instructions. Course and enrichment limits have different explicitly documented scopes; the enrichment bridge is not misrepresented as kernel public-only egress.
- Owned-container cleanup uses predetermined identities, preserves concurrent foreign jobs, restores signal handlers, and retains an independent container deadline after host loss. Output publication requires clean exit and bounded validated archives.
- The redirect hook prevents Requests' internal redirect-body drain before manual validation; browser callbacks bind the original cumulative budget across Playwright greenlets. Exhaustion remains sticky rather than becoming successful provider fallback.
- Actual filesystem tests exercise link, hardlink, FIFO and substitution behavior. The caption/chapter fixes have actual-media RED/GREEN evidence, preserve original assertions and do not contain fixture-specific words/times.
- Exact artifact hashes are external, failures and old snapshots remain available, and current top-level claims distinguish decoding/UI evidence from subjective listening and learning.

## Issues

### Critical (must fix)

None found.

### Important (should fix)

1. **The complete archive ships a regression entry point without its required validation dependencies.** `scripts/package_teacher_release.py:12` selects `run_teacher_regressions.py`, but omits `scripts/test_render_receipts.py`, `scripts/test_candidate_packaging.py` and `scripts/test_portfolio_repair.py`, all required at `scripts/run_teacher_regressions.py:21`. The latter suites additionally need `package_teacher_handoff.py`, Git metadata and the omitted `new-skills` mirror. Exact ZIP membership and the temporary extraction probe above confirm this is a recipient-visible failure, not a speculative test gap. The complete skill runtime trees themselves are present. **Fix:** make the supported validation boundary concrete: either supply a complete archive-specific validation path/dependencies, or explicitly identify these utilities as repository-only and require the exact full Git checkout, with an early actionable refusal from the shipped runner instead of discovering missing tests after expensive controls. Do not imply that all repository regressions run from this source ZIP. This need not change any governing acceptance assertions.

### Minor (nonblocking quality corrections)

1. **Current operational status text still describes resolved failures as current.** `skills/teacher/skills/course/SKILL.md:55`, `skills/teacher/skills/course/scripts/README.sandbox.md:55` and `:179`, `skills/teacher/references/MECHANISM-STORYBOARD-EXAMPLE.md:62`, `examples/teach-visual-candidate/base-rates/README.md:40` and `:55`, and `scripts/TEACHER-CANDIDATE.md:3` still say consent approval/validation or the three-run requirement remains unresolved. The actively reusable handoff notice at `scripts/package_teacher_handoff.py:49` hardcodes the same old state into newly assembled handoffs. A recipient can wrongly conclude current validation is broken. Update operational prose or explicitly date its historical subsection, link current approved evidence and retain old attested receipts verbatim. Keep release/activation pending separately.
2. **The reusable release packager asserts this run's successful status for arbitrary revisions.** `scripts/package_teacher_release.py:55` emits approved-v2/three-narrated-pass prose for every `--candidate --revision`. Current archives correspond to verified source, so their measured identity is not invalidated; another revision could receive unsupported results. Use revision-neutral candidate text or explicitly supplied, revision-bound status provenance. Apply the same principle to the handoff helper.
3. **New discovery/resolution controls are absent from ordinary CI selection.** `.github/workflows/teacher-security.yml:17` executes only `test_teacher.py`; `scripts/run_teacher_regressions.py:12` adds only `test_network_policy.py` from the teacher test directory. New `test_find_tool.py` and `test_manim_resolution.py` therefore remain local-only even though their source behavior changed significantly. Add their patterns to the required runner. Local results are already recorded, so this is not a current functionality failure.
4. **Two packaged exemplar README evidence links are unresolved inside the complete source ZIP.** `examples/teach-visual-candidate/merge-sort-stability/README.md:5` and `examples/teach-visual-candidate/momentum/README.md:5` point to `docs/teach-finish-20261024/quality/INSPECTION.md`, which is absent from that ZIP. Include the referenced public receipt or describe the link as requiring the full checkout/provide a resolvable provenance location.

## Deferred-minor triage

- The teacher-extra `downloading kokoro-v1.0.onnx…` message is established as expected mocked test output: `skills/teacher/skills/explorable/scripts/narrate.py:88` prints it, while `skills/teacher/scripts/tests/test_network_policy.py:209` redirects the model directory and URL retrieval to a temporary local `b'fixture'` write. Denied/cached cases assert no transport call. This is not evidence of a real model download or shared-environment mutation. An explanatory receipt note is sufficient; no source repair needed.
- Deliberate negative-control flood/exhaustion output is successful adversarial-test evidence, not unexplained production warnings. Preserve raw output; a concise view is optional.
- Exact copied generated HTML/VTT whitespace is disclosed in `FINAL-COMMIT-NOTE.md`. Preserve attested bytes; do not reformat the demo solely for whitespace cleanliness. Source-only checks have a separate scope.
- The baseline/effective-adapter metadata clarification is additive, and disclosed-case regression labels are appropriate.

## Limitations and assessment

This review does not certify hosted GitHub Actions execution, actual authored Manim scene rendering, subjective audio listening, learner outcomes, universal browser/platform compatibility, private fixture contents, or a fresh blind final post-repair pass. No such completion claim should be added. Installed rollback verification is supported by the independent Task 3 review/preservation receipt rather than repeated here. Current top-level “final review pending” text is a snapshot status to be resolved by the controller's separate actual review receipt, not a defect requiring rewriting the snapshot.

**Ready to merge? With fixes.** The runtime/security changes are coherent and final measured playback/artifact identities are supported. Resolve the shipped validation boundary and correct the current operational/status prose in one bounded follow-up, then review that exact delta and newly versioned packages; do not rerun frozen media acceptance merely for documentation/packaging changes.
