# C adapter candidate 1 — not accepted or installed

Source commit: `4a834ac`. Import baseline: `988e691`; governing freeze: `b7bb239`.

The source addresses the eight P1 wording sites, supplies program context on standalone rule/misconception cards, gives Q&A its complete core explanation before optional detail/questions, permits satisfaction to close teaching without an attempt, unlocks IVE controls by default, uses the actual answer-bearing cue for practice timing, and narrows sync/deletion receipts to what local evidence establishes. Interrupted deletion explicitly reports that outside copies were not rechecked. The legacy deletion enum is retained for frozen compatibility, with `deletion_scope=workspace-local` and `remote_deletion=not_verified`.

The loop fix counts occurrences of executed edges instead of treating repeated edges as a set. The generic still fallback draws captured observations and source-linked explanatory notes when no domain panel exists; it no longer crashes or invents an unrelated panel. This fallback remains below acceptance because OCR fails.

No protected verifier, schema, rubric, threshold, freeze, installed link, or original test changed. Two new diagnostic unit tests cover repeat-edge planning and answer-bearing cue selection. ReLU changes only spoken realization and its pronunciation-cache version; every accepted `heard` list is unchanged. A context pause prevents the activation name merging into the following verb.

## Observed local results

- Fresh sandboxed capture: all 101 facts match the original values across all 20 programs; compile-only programs remain unexecuted. `candidate1-numeric.json`.
- Original focused regressions: privacy 5/5, QA 3/3, routing 18/18, frame-state 8/8, spoken-form 5/5, lint 6/6, cards 3 passed plus existing Anki not-run, claims infrastructure 14/14, recovery 1/1. The claims infrastructure tests use isolated synthetic unit-test records; they are not lesson acceptance reviews.
- New diagnostic tests: 2/2.
- Preserved loop composition with identical fixed narration durations: baseline has 2 frame/cue mismatches among 36 pauses; candidate has 0/36. The frozen frame checker is unchanged. This is a composition probe, not a full regenerated loop MP4 acceptance result.
- QA opened at 1440/390 px in light/dark and with JavaScript disabled: complete core explanation precedes the first question, has zero controls, and has no horizontal overflow. Previews: `/private/tmp/prax-teach-c-v3-audit/qa-preview-*.png`.
- Actual switch video/IVE build: all automatic gates passed; claims pending.
- Actual neuron video/IVE build: `video.sync` passed with unchanged accepted forms, including the new ReLU realization. Actual answer cue is 85.633 seconds. `ive.predict-gated` failed for the fixed observation horizon described below.
- Actual struct still build: crash eliminated; all automatic still gates except OCR pass. OCR confuses literal mixed stdout such as `i` and `1`. No OCR exemption was introduced.

These are local construction-time diagnostics. Exact-commit independent full-suite acceptance, all four real claims builds and reviews, independent numeric/wording/rendered audit, screenshot design verdicts, and human visual acceptance remain pending. The full selftest was not run. Raw attempts, including earlier failures and missing-browser attempts, are retained under `candidate1-selftest-receipts/`; the latest result per focused group is in `candidate1-selftests.json`.

## Remaining failures and governing conflicts

1. **BLOCKED: reviewer job context.** Captured clang diagnostics and explorer ranges/steps are omitted by protected `ptk/verify/claims.py`. No payload/schema workaround or counterprogram removal was applied. A separate governing version is required to repair this formatter.
2. **BLOCKED: default IVE locking assertion.** The frozen `test_no_leak_before_answer` requires live controls locked in default mode. The authorized product unlocks them. Its actual failure has `hits=[]`, `locked=false`: no answer leakage was observed. Reinstating the barrier would violate the product request; changing the assertion would violate this candidate freeze.
3. **BLOCKED: neuron observation horizon.** Frozen `ive.predict-gated` observes about 8 seconds after the question and requires reaching `answer_at`. Truthful answer time is 85.633 s; observed default playback reaches about 62.2 s, remains unpaused, and stays in film mode. Do not mislabel the earlier Add scene as the answer to satisfy this check.
4. **BLOCKED: automatic still attachment for plain teaching.** Frozen public routing cases require explain routes to have `media=[]` and `build_needed=false`, including "teach me pointers". A temporary default-still change failed eight groups and was removed; the unchanged route now passes 18/18. Do not change expected labels inside a candidate.
5. **FAIL: struct OCR.** The fallback is executable and its layout passes, but the literal captured text fails OCR. It is not release-ready.
6. **NOT_RUN: full loop MP4 and full-suite acceptance.** The preserved loop's focused before/after comparison passes; its actual MP4 layout, complete automatic gate suite and real claims still need independent execution. Factorial/one-byte IVE builds were not regenerated, so the all-lessons live-control test is not-run.

## Isolation and reproduction

Only synthetic data was written, outside Developer/Study, with `PRAX_TEACH_SYNC_ROOTS=''`. Provisioned tools/models were APFS-copied from `/private/tmp/prax-teach-v3-runtime` into `/private/tmp/prax-teach-c-v3-state`; separate temporary lesson copies and caches live there or under `/private/tmp/prax-teach-c-v3-*`. No setup, shared reinstall, Claude CLI, API request, skill install or live claims reviewer was invoked.

The stock routing test was initially run before its conditional real-workspace path was noticed. It can inspect `~/Study/.../01-C` if that workspace exists. No manual learner/staging inspection occurred, and no subsequent diagnostic used that path. `run-isolated-checks.py` now replaces only fixture locations in memory and leaves all assertions intact. Its results are diagnostics, not a substitute for independent acceptance.

Example:

```sh
PTK_STATE=/private/tmp/prax-teach-c-v3-state /private/tmp/prax-teach-c-v3-state/venvs/core/bin/python -B deliverables/teach-pro-max/claude/run-isolated-checks.py --lesson-copy /private/tmp/prax-teach-c-v3-lessons/switch-fallthrough -k test_route.py
```

Receipts are outside the source product tree. `candidate1-integrity.json` records its commit/tree. Nothing is installed or accepted, and no candidate count or stop rule is reset.
