# Prax Teach v3 governing freeze

Status: governing stage complete; candidate implementation is a separate run.
Authorization: Prax's 19 October request, "Please follow your recommendation and implement it. Let's finish this ... Do not lower the technical or quality standards." This accepts the architecture and finite caps proposed in DELEGATION.md. It does not authorize installation, changes to identity-preservation policy, archive history rewrites, or touching real learner/Drive data.

## Product and baselines

The objective remains a reusable general visual teacher across subjects: complete explanation first, optional practice, mathematically/factually correct mechanism-led stills, explorers, layered Q&A, cards, narrated video and interactive video; resumable course plus complete static fallback. Human learning outcomes and world's-best claims require evidence beyond automated tests.

General original source e1d196e74ed88df3f5cdce8a06390331f9862300; current preserved source a064610f4cbe3bf32915a9fd570f8872433df4dd. Tree inventories are in BASELINES.json. Existing accepted Prax Teach v2 and Atlas snapshots remain immutable archive comparators. No new candidate is accepted or installed by this freeze.

C import baseline 988e6914599821bccb9d2d0cb1faff19118ac33e, exact source a38becaee4e63b455105c394f825bce0fde420fa, restored-check commit ae9b06fa151e2df75842fb9a0b4d77ac1ee0c84d, public tag commit 2493c45c075c9db9ec0b7b7e44cdc9220f3de1e1. Optional adapter only; failure of its acceptance blocks C integration, not general work.

## Mutable and protected paths

General candidate branch candidate/teach-general-20261019: skills/teacher product code/instructions, compatible skills/teach-pro-max product instructions, deliverables/teach-pro-max/codex and supporting reproduction scripts. C branch candidate/teach-c-adapter-20261019: projects/prax-teach-c-adapter product code/instructions/lessons, deliverables/teach-pro-max/claude and adapter documentation. Codex integrates. No shared mutable tool root or overlapping writers.

Protected: this freeze, original/current/archived baselines, evaluator private files and checksums, original tests except the governing change explicitly below, all C verify/** and thresholds, schemas/reviewer rubric, installed links, real study/learner/Drive data, human policies and unrelated files. Candidate unit tests may add diagnostic coverage but cannot replace acceptance or weaken an existing test. If a frozen checker is wrong, stop that criterion and propose a separate governing version; do not repair the checker inside a candidate run.

One governing test change: explorable/scripts/test_lesson.mjs now explicitly requests ?practice=1 and opts into progress persistence when the new consent checkbox exists. Every original question, lock, answer, film, model and persistence assertion remains. These assertions test requested practice; the independent v3 default-flow checks require ungated complete explanation. This avoids imposing practice-first as the default. No other existing gate changes.

## Fixed evaluation

Private evaluator general-v3.1-20261019, owner independent evaluator agent, /Users/prax/.local/state/teach-pro-max-evaluator/v3-20261019. Implementers do not open case bodies. Sealed hashes are in BASELINES.json. Previously public holdouts are regression cases only.

24 critical routing cases R01-R24, 8 scoped non-C end-to-end cases E01-E08 across 8 subjects, 56 critical E2E subcriteria AUTHOR/FACT/EXPLAIN/UI/MEDIA/FALLBACK/CONSENT, and 16 fixed valid/invalid controls. All critical cases must pass; 85% routing is a diagnostic, not release acceptance. Controls retain >=95% valid acceptance, 100% planted value errors / >=90% planted claim errors; for eight controls in each group these thresholds require all eight. Preserve all denominators, target-ID and paired-control results; no post-hoc exclusions. No unresolved P0/P1 correctness or blocked-default-flow defects.

Use actual authored artifacts, native routing and real media. Source-only capability inspection cannot pass E2E. Missing/failed required checks are NOT_RUN/FAIL and block readiness. Evaluator receipts preserve exact commits and input/output hashes outside the content they attest to. LLM agreement is not truth or user visual approval.

Three fresh non-C exemplars, one qualitative, one calculation, one science, each in all six formats, through one generic authoring path; first qualitative lesson is the staged milestone. No topic-specific renderer path. Course continuation/resume is verified with synthetic explicit consent and an ephemeral no-consent path. Complete static fallback is opened with JavaScript disabled. Inspect actual 1440 px and 390 px, supported light/dark, keyboard, controls, chapter state, video/captions/transcript and audio. Compare actual output with Atlas and current baseline. Independent looks/explanation review target >=8, with Prax's visual acceptance separately pending. No score certifies world-class quality.

Existing regression commands: teacher/scripts/tests/test_teacher.py; teacher/scripts/tests/run_all.sh with required Playwright/Chromium/ffmpeg provisioned; teacher/scripts/vendor.py verify; teach-pro-max/references/prax-teach-v2/scripts/verify.py --level full. Preserve skipped diagnostics; ALL PASSED after a required skip is not accepted. The two site-only course tests are not applicable outside their downstream site; exercise the new standalone course directly. Provision required YAML, browser, voice and speech dependencies rather than silently skipping them.

C acceptance remains four full claims builds with 3/3 real lesson jobs, existing value/claim/control thresholds, zero selftest failures except the explicit existing Anki-import not-run, independent numeric/wording/rendered audit with zero P0/P1, actual struct and loop reproducer passes, unchanged ReLU pronunciation check, and privacy/consent/deletion checks. Do not substitute fabricated accepting reviews. A checker/source-access/provider failure remains a limitation, not a pass.

## Execution, budgets and stop

General at most 8 completed implementation candidates; C at most 4. Evaluate each completed candidate independently against the frozen matrix and both original/current accepted baselines. Count every use of private cases. Gain means a previously failing critical criterion passes without a protected regression. Stop at the cap or after two consecutive no-gain candidates. No reset on resume, no masking repair builds as review, no gate edits to keep going. Governing preparation/import and final no-change verification are recorded separately. At completion retain PASS/FAIL/NOT_RUN per criterion; stopping is not success.

Use copied runtime tools/models at /private/tmp/prax-teach-v3-runtime, separate per-track caches and explicit synthetic fixture roots outside Developer/Study. ISOLATION.json records a two-second hardlink probe with link count 1 before/after; this is observed local evidence, not proof about all remote copies. No shared setup/reinstall. Do not scan/delete real Drive staging. Teaching goes offline after provisioning; no paid API fallback or automatic Claude quota use.

Installation, public archive migration/history rewriting and user aesthetic acceptance remain separate decisions. Commit named paths and verify authorized pushes. Roll back by returning to the named baseline branches/commits; never reset a user's worktree. Keep failed candidates and receipts.
