# Orchestration decision v1

19 October 2026. Owner: Codex, integration/orchestration. This is the final recommended direction for the next run, not an assertion that the run or its budgets have been approved. It resolves conflicts between the two goal plans. It changes no existing frozen evaluator, implementation or installation.

Read [COUNTERS-RESOLUTION.md](COUNTERS-RESOLUTION.md) for verified factual corrections. Additional reviews are leads; they do not automatically change this plan or approve its budgets.

## Decision

Improve the general teacher already in `skills/teacher/` and reconcile the compatible `teach-pro-max` entry. Keep the v2.2 C compiler as an optional adapter. Do not build the general teacher by extending the C-only schema, and do not add another competing teacher.

C repairs and general integration may proceed in parallel after their governing contract and finite budgets are approved. The general track does not wait for C acceptance and does not branch from the C release tag. C acceptance gates integration of that adapter, not progress on the general teacher. The additional reviews do not change this ownership or sequencing.

## Verified preservation and baselines

- Remote `main`: f54d334ae709df48983638a250bf9b6a910fa245. The existing teacher code is inherited from e1d196e74ed88df3f5cdce8a06390331f9862300; the later two main commits add the earlier design documents and ignore rules.
- General archive/goals: `archive/prax-teach-handoff-20261019`, including the real lesson outputs, Atlas, source bundle and accepted general-source snapshot.
- Evaluation source: `prax-teach-eval/v2.1-main` = 1a1eb968; `prax-teach-eval/eval-freeze-v2` = a32698da; `prax-teach-eval/v2.2-candidate` = 025d1604. The latter adds GOALS-NEXT.md after a38beca, with no intervening product changes in the reviewed plan commit.
- Other saved work: `candidate/media-routing-20261018` = f4485c46 and `feat/visual-intuition` = 410ee17e. Saved does not mean reviewed or accepted; do not merge these blindly.
- Milestones `prax-teach-v2.1-rc1`, `prax-teach-freeze-v2` and `prax-teach-v2.2-rc1` exist remotely.

Both preservation efforts are useful. Claude pushed navigable evaluation history and the other sessions' commits. Codex also pushed selected actual output archives and source snapshots. The smoke worktree was deleted, but its sibling archive/v2.2-smoke preserves all six sources/reports and 83/83 recorded artifacts; the earlier missing-evidence statement is retracted. The archive README explains retained content and exclusions. Publicly disclosed old test prompts are regression cases, not a new hidden test.

## Product Manager: keep and change from Claude's proposal

Keep the bounded C repair goal, source-grounded facts, independently checked explanations, domain pronunciation, real rendered examples, fresh unseen evaluation and user visual approval.

Change these parts:

1. Reject C-first as a dependency for general work. Both are independently useful and own separate paths.
2. Reject v2.2 as the required general architecture. Start from the existing general teacher; reuse C capture only through a small optional adapter boundary.
3. Do not mandate a new Python execution backend or exactly five new figure classes before proving a need. Reuse working diagrams, calculations, sourced prose and renderers already in the general teacher. Add only missing capabilities needed for an actual artifact.
4. Do not turn historical or linguistic claims into numeric facts. Keep source/context, interpretation and uncertainty appropriate to the subject.
5. Do not use an 85% routing score or 6/8 end-to-end success to call a release ready. Scores are diagnostics. Every case declared release-critical must pass its complete applicable checks; other misses remain explicit limitations. Never shrink that required set after results.
6. Do not require Prax to hand-write a large test bank. An independent evaluator can author fresh cases under the approved policy, seal them before implementation and report only results to implementers.
7. Three-reviewer agreement is evidence, not truth. Calibrate discrimination using independently adjudicated valid and invalid material, not merely unchanged material containing known errors.

## Principal Engineer, checkpoint 1: work allocation

### Codex, general teacher and integration

Own `skills/teacher/**`, compatible `skills/teach-pro-max/**`, general acceptance evidence and `deliverables/teach-pro-max/codex/**`. Read current remote source and existing test commands before selecting any replacement.

First milestone is one fresh qualitative non-programming lesson, through the normal authoring path, with six requested artifact types, complete explanation first, optional practice, course continuation/resume and usable tool-light/static fallback. Do not count the existing seasons example as fresh transfer evidence. Do not add a hardcoded path for this topic.

Once that milestone works, complete three fresh non-C exemplar lessons, each in the six named formats: one calculation/math topic, one science/process topic, and one qualitative history/language topic. The first qualitative milestone counts as one of the three. This adopts Claude's proposed coverage while staging it, rather than stopping after the earlier one-example pilot. Existing components can satisfy this without a new universal compiler.

Keep Claude's proposed independent bank of at least 24 routing requests and 8 scoped end-to-end requests across at least 6 non-C subjects. Include qualitative subjects. Each end-to-end request asks for the medium its explanatory job needs, not necessarily six formats per request. Keep new case bodies outside the public repository and its archives/releases/bundles, in private evaluator-owned storage; publish only the digest, version and redacted results. Seal the cases before candidate work and have the independent evaluator retain them. Scores are diagnostics; all cases designated release-critical must pass, and that designation cannot change after results.

Resolve the current teacher's contradictory 'question before answer', project-pinned practice and explanation-first instructions across actual chat and artifact paths. Native host teaching must remain possible without the C compiler, paid APIs or subagents. No single public-name change is assumed; keep compatible invocations and document one teaching authority.

### Claude, C adapter

Own restored `projects/prax-teach-c-adapter/**` and `deliverables/teach-pro-max/claude/**`. Repair the four lessons, structured claim context, diagnostic/control evidence, C-engine consent/deletion/fixture issues, default practice leftovers, ReLU audio and the actual struct/loop reproducers.

Claude may fix the C still renderer's generic code-trace fallback needed by the struct reproducer. That does not give it ownership of the general teacher's schema or general figure system. This resolves GOALS-NEXT.md's conflict where the C smoke failure depended on a renderer owned by G.

Hand off exact committed source, built artifacts, raw reports, limitations and the adapter interface. No changes to general-teacher files or shared evaluator rules. Tagging a result does not promote or install it.

### Codex, integration responsibility

Agree the smallest adapter input/output contract before integration. Treat C output as an optional capability. Merge only reviewed compatible changes into an isolated integration branch; preserve both writers' commits. Do not make the general release depend on accepting a known-broken adapter, and do not call the adapter verified while its full suite fails.

## QA/Security: fixed acceptance

### General candidate

- The full default explanation is available without an answer, forced Reveal step, locked controls or evidence requirement. Explicit practice still works and can be skipped or stopped.
- One new qualitative non-code lesson supplies editable still/PNG, explorer, Q&A, cards, narrated video with captions/transcript and interactive video. A continuation lesson/course map resumes correctly with synthetic explicit consent, and teaching continues ephemerally without consent.
- Actual 1440 px/390 px renders, supported light/dark views, keyboard interactions, state transitions, captions and audio are inspected. Static fallback is complete; the rich path actually runs instead of silently becoming static.
- Run `python3 skills/teacher/scripts/tests/test_teacher.py`, `bash skills/teacher/scripts/tests/run_all.sh` and the teach-pro-max distribution verifier in its documented directory. Preserve output and explicitly reject an ALL PASSED label that skipped required browser/video checks.
- All three fresh non-C exemplars deliver the six formats and pass their fixed applicable correctness, interaction/media and source checks. All frozen release-critical transfer cases pass; preserve scores for the 24-route/8-request/6-subject bank separately. New independent checks are approved/frozen before implementation. No hardcoded benchmark/topic fixes.
- One separate reviewer examines actual content and artifacts. Known P0/P1 correctness and blocked-default-flow defects are resolved. User visual acceptance remains separately pending until Prax actually gives it.

### C candidate

- Four full-suite builds verified with existing value/claim/control thresholds and 3/3 lesson job acceptance. Preserve all control jobs in the frozen denominator; adjudicate content defects/false rejections/disagreement separately. Any new scoring or control-eligibility rule needs a separately approved evaluator version before the C run.
- Selftest has zero failures; Anki import is the explicit approved not-run. Required live jobs are completed and scored, not merely queued.
- Independent numeric/wording/rendered audit has no remaining P0/P1 correctness finding. Claim justifications and standalone material are in scope.
- Struct still and loop video reproducers pass applicable automatic checks, with actual output and raw reports retained. Do not silently infer a new lesson's claims acceptance from automatic gates.
- The restored layout/sync checks remain intact. Correct actual ReLU spoken content instead of broadening accepted forms.
- Nonsynced fixture roots, read-path/withdrawal behavior and honest local-deletion scope are checked without touching real Drive data.

### Shared integration

Receipts bind exact commits, lesson hashes and output inventories. Preserve raw evidence, including failures, outside the content it attests to. Compare original and currently accepted baselines. Run the relevant frozen regression set on the integrated candidate; installation is a separate user decision. No aggregate score overrides a failed required case.

## Principal Engineer, checkpoint 2: budgets and stop conditions

Recommended caps, taken from Claude's proposal rather than treated as already approved:

- C: the prior proposal is at most 3 implementation rounds. Claude now proposes 4; neither is approved. Do not drop privacy to force the smaller estimate. A verified nonsynced test/state root is required before any tests.
- General: at most 8 implementation rounds, with a review of the first non-code milestone before expanding scope.
- Both: at most two consecutive no-gain candidates. Stop at either limit, retain the candidate and report unmet criteria. Resuming a session does not reset counts. Initial inventory and the final read-only verification are identified separately; repeated repair builds cannot be hidden as review work.

Use this one no-gain definition in both tracks:

A round is one completed implementation candidate followed by an independent run of the frozen acceptance matrix. Gain means at least one previously failing release-required criterion passes on the evaluator's withheld cases, with no protected regression against the original or current accepted baseline. The evaluator reports criterion IDs/statuses and bounded findings, not withheld prompts; it records every use of the bank. A unit-test count, changed evaluator, screenshot-only opinion or known-case fix alone is not gain. Before implementation, the governing-only freeze records the exact criteria, withheld cases, runner, owner and evaluation schedule for each track. If those are not ready, prepare them without starting candidate work. Two consecutive rounds without gain stop the track; progress counters never reset on resume.

The old v2.2 budget is exhausted. A new finite budget and the versioned governing changes need explicit human approval under the existing identity-preservation contract. Prepare the exact governing-only change before candidate edits; do not alternate evaluator edits and implementation to manufacture progress. A claimed progress improvement is judged against the fixed required criteria, not a moving test count.

## DevOps/SRE: operating rules

Separate worktrees, branches, output paths and mutable tool/state roots. Never run setup against tools another build is using. Keep archived source/evidence and installed links unchanged. No Drive changes, API purchases, broad uploads, forced pushes or unrelated edits. Commit only owned paths and verify authorized pushes by remote SHA.

## Final direction to send Claude

Keep Goal C with the amendments above. Do not start Goal G by generalising the C engine. Codex owns the existing general teacher and integration, in parallel with C repair once the new freeze/budgets are approved. Preserve the scoped C renderer fix so the struct reproducer does not depend on general work. Hand off source/artifacts/evidence; do not install or declare world-class quality from reviewer scores.
