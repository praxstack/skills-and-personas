# Acceptance rules: proposal against the frozen rules

Written 2026-10-18 at Prax's request. **Each item is a separate decision.** Canary mode is a separate decision in its own section and is not bundled with acceptance policy.

Frozen rules: `../FREEZE.md` (success definition 1–5, evaluator and holdout, protected checks, stop rule). Proposal: `ACCEPTANCE-PROPOSAL.md`.

| # | Frozen rule (FREEZE.md) | Proposed change | Why | Consequence |
|---|---|---|---|---|
| 1 | The holdout is 32 routing prompts only. | Add 6 unfamiliar end-to-end requests, one per medium. Each must build with every gate `passed`. | Routing can pass while lesson generation fails. | Acceptance would test real lessons, not just routing. The 6 drafts in `proposed/` were written by the agent, so Prax should write or rewrite them, or they aren't truly hidden. |
| 2 | Criterion 4: "measured loudness, synced captions", with no numbers. | −16 ± 1 LUFS; true peak ≤ −1 dBTP; cue start and end within 0.5 s of measured speech; non-code WER ≤ 10% against the derived spoken form; 1080p30, H.264 + AAC, captions and chapters tracks. | Makes "synced" and "measured" pass or fail. | Stricter and objective. The current lessons already meet it. |
| 3 | Criteria 1 and 2: values asserted, every claim reviewed. No reviewer-reliability bar. | Value mutations caught 100%; claim mutations ≥ 90%; **unchanged controls accepted ≥ 95%** (missing from the first proposal); the lesson job accepted; the `%f` regression rejected. | The final run caught 38 of 38 planted errors, yet rejected 7 of 40 valid controls. Catching errors alone doesn't make a reviewer reliable. | Stricter. Today **no lesson passes**: controls ran 8/11, 8/10, 8/10 and 9/9. |
| 4 | Criterion 3: "a world-class look … with measured contrast". | 9 automated aesthetic checks, plus 6 screenshot-reviewed items, plus **Prax's own visual verdict per lesson against the Neuron Atlas reference**, as a required human gate. | Gates passed a course Prax called horrible. Taste can't be automated. | Acceptance waits for Prax's visual sign-off. The reviewer scores are evidence, not acceptance. |
| 5 | Criterion 5: "respects the learner workspace contract (Prax's C workspace: one prediction, wait for the attempt)". | **Rewrite** (see `EVIDENCE-PREDICT-FIRST.md`): a complete visual explanation first, everywhere, including the C workspace. Practice is optional afterwards. Prediction barriers apply only in explicitly requested practice modes (quiz, exam-drill, Socratic, "let me predict"). "Answer now" ends questioning in any mode. | Criterion 5 froze a rule an OpenCode agent wrote into the workspace, not Prax's preference. Prax had turned down a prediction question on the same day. | This is an evaluator change. Holdout rows that are labelled predict-first must be relabelled by Prax. The live session becomes usability feedback, not a predict-first test. |
| 6 | Protected check: one skill entry per host. | Also test install and rollback on 4 hosts in throwaway HOMEs. | Rollback is part of reversibility. | Stricter. Already passing. |
| 7 | Mutable path: `v2.1/**` only. | After acceptance, allow writes to the install path, a user-scope state dir and the `prax-teach-v2` link flip. | Needed only to install. | **Deferred.** Prax has said not to install. No change needed for the repair plan. |
| 8 | Stop rule: "newly passing acceptance check". | Read it as "a newly passing EARS criterion in SPEC.md". | The holdout runs only at acceptance, so it can't measure each round. | Progress gets counted by the candidate's own tests. The risk, seen this run: tests can be weakened to show progress. Mitigation: any test or gate change counts only after an independent review classifies it as a bug fix or a stricter check. |

## Canary mode (separate, provisional)

- **The proposal (§9):** run the full mutation suite only when calibrating, then use one canary per build.
- **Status: provisional, and not proposed for adoption now.** The final run shows why it can't stand in for full verification:
  - all four lessons were `canary-verified`;
  - the full suite then failed all four, with real wording errors and reviewer drift.
- **Allowed use:** a cheap development check while building. Its best status is `canary-verified`, never `verified`.
