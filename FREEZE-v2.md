# Freeze record v2: Prax Teach v2.2 repair run

Written 2026-10-19, before any v2.2 implementation. It replaces `FREEZE.md` (v1, kept unchanged) for the v2.2 run. Changing anything here needs Prax's explicit approval and a v3 of this file.

## Approval

On 2026-10-19 Prax replied to the repair plan (`plan/REPAIR-PLAN.md`) and the acceptance comparison (`plan/ACCEPTANCE-COMPARISON.md`) with "implement it then", and said to leave the Google Drive and backup data alone. This file records that approval as acceptance of the plan with the recommended option on every open item. Each item is listed below so Prax can overturn any one of them.

## Objective (unchanged)

Beautiful, mathematically correct teaching artifacts that build intuition: a still explainer, an interactive explorer, a Q&A expander, flash cards, a narrated video and an interactive video explorer, for C and DSA topics.

## Success definition v2

1. Every displayed value comes from a real compiled run or is computed by code, and an automated assertion fails on tampering. *(Unchanged.)*
2. Every conceptual claim is checked by separate reviewers, and the reviewer is shown to be reliable: value mutations caught 100%, claim mutations caught ≥ 90%, unchanged controls accepted ≥ 95%, and the lesson job accepted by 3 of 3 independent reviewers who judge cited sources from stored excerpts, never from memory. The `%f` cast regression is still rejected. *(Item 3, approved: stricter.)*
3. The look: 9 automated aesthetic checks, the Track B measures in `spec/SPEC.md` WP10, 6 screenshot-reviewed items, and **Prax's own visual verdict per lesson against the Neuron Atlas reference**. Reviewer scores are evidence, never acceptance. *(Item 4, approved.)*
4. Media: −16 ± 1 LUFS integrated, true peak ≤ −1 dBTP, cue start and end within 0.5 s of measured speech, non-code WER ≤ 10% against the derived spoken form, 1080p30 H.264 + AAC with caption and chapter tracks, narration ≤ 170 words per minute per line. *(Item 2, approved; the wpm bound comes from Track B.)*
5. **Teaching behaviour (rewritten, item 5):** a complete visual explanation first, for every teaching request, in every workspace including Prax's C workspace. Practice is optional and offered afterwards. Prediction barriers run only in practice modes the learner explicitly asks for (quiz, exam-drill, Socratic, "let me predict"). "Answer now" ends questioning in any mode. Workspace files never switch the default to prediction; when they ask for it, the route reports the conflict instead of obeying.

## Item-by-item record (ACCEPTANCE-COMPARISON.md)

| # | Decision | Note |
|---|---|---|
| 1 | **Adopted in a weaker form.** The 6 end-to-end requests in `plan/proposed/e2e-requests.jsonl` run at acceptance as a **smoke set**, not as holdout. | The agent wrote them, so they are not hidden. They count only as "builds end to end with every gate passed". A real end-to-end holdout needs requests Prax writes. |
| 2 | Adopted. | Stricter. |
| 3 | Adopted, plus 3-of-3 reviewers on the lesson job. | Stricter. |
| 4 | Adopted. | Prax's verdict is the final visual gate. |
| 5 | Adopted. Holdout relabelled (below). | Evaluator change. |
| 6 | Adopted. | Stricter; already passing. |
| 7 | **Deferred.** No install. | Prax: keep v2.1 as a development candidate, don't install. |
| 8 | Adopted with the mitigation. | Progress counts by newly passing SPEC v1.4 criteria. A changed test or gate counts only after an independent review classifies it as a bug fix or a stricter check. |
| Canary | **Provisional.** | Allowed only as a development check during a round. Never used for acceptance; best status `canary-verified`. |

## Other decisions recorded (D23)

- **D23.1 Learner state in Google-Drive-backed folders:** refuse by default; the learner can opt in explicitly, and the opt-in is recorded with consent. (Recommended option.)
- **D23.2 D22.3 (xattr learner binding) approved together with the A6 privacy fixes:** delete reports surviving copies outside the workspace, the consent text names Google Drive when it backs up the folder, warnings say "Google Drive", not "macOS backup".
- **D23.3 Read-only commands never write** (not even extended attributes) when consent is absent or withdrawn.
- **D23.4 Data already staged in Google Drive:** left alone, per Prax ("leave it").
- **D23.5 IVE explore (check change 6):** stricter reading of AC-6.6. Every IVE needs at least one live control in EXPLORE that changes the shown state; step-through alone no longer passes.
- **D23.6 The C study repo's AGENTS.md and NOTES.md** are protected and stay untouched in this run. ptk reports the conflict when it reads them.
- **D23.7 Anki import** stays `not-run` (Anki is not installed; installing it was not approved).

## Holdout v2

- `holdout/routing-prompts.jsonl` (v1, sha256 `8b9240cc…`) is kept unchanged.
- `holdout/routing-prompts-v2.jsonl` (sha256 `9f99db25…`, both in `holdout/SHA256`) differs only in H19 and H20: "teach me pointers" and "teach me how printf %c works" in the C workspace were labelled `prediction-first`; they are now `lesson / static / still`, the same label a plain "teach me X" gets (H13). H27 (timed GATE practice, explicitly requested) stays `exam-drill`.
- The relabel applies Prax's stated rule mechanically. Prax may still rewrite any row.
- Implementers must not read `holdout/` or `plan/proposed/`. Only the final verification runs them.

## Baselines

- **Original baseline:** v2, ZIP sha256 `c4827533185ad7db90aaf3af25edd97f6cf9d3a8b3e868a1b683ef3ba552205f`, installed at `~/.agents/skill-library/prax-teach-v2` (untouched).
- **Current candidate:** tag `v2.1-rc1` (commit `1a1eb96`). Its lesson builds are archived with checksums at `../archive/v2.1-rc1/` (`SHA256SUMS`, `SOURCE`).
- Every v2.2 result is compared against both v2 and `v2.1-rc1`.

## Branches: evaluation separate from implementation

- `eval/freeze-v2`: this file, holdout v2, SPEC v1.4. Tagged `freeze-v2`. Nothing else.
- `candidate/v2.2`: implementation only, branched from `freeze-v2`. It must not change `FREEZE*.md`, `holdout/**`, `plan/proposed/**` or the acceptance criteria in `spec/SPEC.md`. A check script that implements a SPEC v1.4 measure is candidate code, but it is written and independently reviewed before the work it measures.

## Protected checks (must never regress)

- v2's 22 JS tests and its passing Python tests, or each removal justified in writing.
- One skill entry per host (Claude Code, Codex, Hermes, OpenCode), plus install and rollback in throwaway HOMEs.
- The tamper test: a deliberately wrong figure fails verification.
- No network at teach time.
- Nothing outside `v2.1/**` and `../archive/**` is written. v2, the C study repo and every other skill stay untouched.

## Budget and stop rule

- **Track A (correctness):** at most 5 rounds. **Track B (visual):** at most 5 rounds. At most 2 rounds per deliverable.
- A deliverable with 2 rounds and no newly passing SPEC v1.4 criterion is parked and reported.
- A run changes the candidate or the evaluator, never both. Stalls are reported; gates are never weakened.
- Then one read-only final verification (full claims suite, holdout v2, smoke set, protected checks, independent numeric and wording audits), then Prax's visual acceptance.
