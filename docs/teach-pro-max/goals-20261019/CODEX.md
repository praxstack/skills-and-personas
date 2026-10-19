# Codex goal: general teacher integration

Read SHARED-CONTRACT.md first. This brief defines a review-ready candidate; it does not claim Prax's final visual acceptance.

## Owned deliverables

1. One documented general teaching authority using the current `skills/teacher/` implementation and compatible `teach-pro-max` invocation. Reconcile conflicting instructions rather than adding another engine. General lesson authoring accepts sourced prose, diagrams or calculations without a mandatory C program, C17 citation or compiler. C/DSA is an optional adapter.
2. Complete explanation-first behavior in chat, ordinary video, interactive video, Q&A and session closure. Questions in headings are fine when the answer is available; default playback/layers/controls never require an attempt. Explicit practice mode still works, can be skipped/exited, and does not leak its answer. Satisfaction ends the session without claiming measured mastery. A workspace note or topic such as interview preparation does not silently override the user's current request.
3. A new qualitative, non-programming teaching example through the normal authoring path, not a hardcoded demo branch. Choose and freeze the topic/source material before implementation; do not reuse the existing seasons demonstration as proof of new transfer. Deliver a sourced editable still plus PNG, a working explorer, Q&A expander, cards, a narrated film with captions/transcript and an interactive video. Reuse one coherent lesson model where appropriate. Never invent numeric or causal certainty for qualitative content.
4. A connected course map with a continuation lesson, next-step navigation and a demonstrated resume through the existing course/series mechanism. Persistence needs explicit synthetic consent; declining it still permits ephemeral teaching. No real learner state is used.
5. Evidence from both a rich host/tool profile and a tool-light/static profile. Ordinary teaching must remain possible without the C compiler, paid APIs or reviewer subagents. The rich profile must actually run its offered interactions/video. Do not satisfy the rich route by silently substituting a static image.
6. A small documented adapter boundary for the C contribution. Establish required inputs/outputs and evidence expectations before Claude integrates; do not rewrite Claude's domain code or merge an adapter whose full claims suite fails.

## Acceptance

- Run `python3 skills/teacher/scripts/tests/test_teacher.py` from the repository root; it exits 0.
- Run `bash skills/teacher/scripts/tests/run_all.sh` with a verified nonsynced TEACHER_TEST_OUT. Preserve all output and generated files. Required browser, interaction and video checks actually run; a script printing ALL PASSED alongside required SKIPPED lines is not acceptance.
- Run `python3 scripts/verify_distribution.py` from `skills/teach-pro-max`; it exits 0 after the legitimate distribution workflow. Never merely rewrite expected hashes to mask a changed or broken package.
- Freeze the new generality, optional-practice, course/resume and fallback checks before implementation, with any governing changes separately approved. The non-code example and the C regression example both pass the relevant approved checks. A separate reviewer inspects real stills, interactions, video frames and audio; no known P0/P1 correctness or blocked-default-flow defect remains.
- `deliverables/teach-pro-max/codex/` contains SOURCES.md, REPRODUCE.md, REPORT.md, PROGRESS.md, the artifact set, raw check outputs and an external hash manifest binding the final commit/artifacts. REPORT.md lists every acceptance row and distinguishes engineering pass, reviewer judgment and pending Prax acceptance.

The tests protect functionality, not the exact initial wording. Add meaningful regressions for the new behavior only under the frozen contract. Don't turn a tool inventory or a test count into the product.

## Stop

Follow SHARED-CONTRACT.md. Do not start implementation without a new approved finite budget and any required governing approval. Preserve ready-to-review design work if blocked. Commit only owned paths, do not install, and do not mark the goal complete with missing artifacts or failed required checks.
