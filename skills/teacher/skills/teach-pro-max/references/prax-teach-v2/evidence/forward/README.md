# Forward behavior evidence

This directory preserves the public fresh-context behavior checks required by
AC-23. These checks show whether representative outputs follow the frozen
behavior and artifact-policy rubric. They do **not** establish held-out quality,
candidate superiority, field accessibility, or human learning outcomes.

## Attempt history

| Attempt | Result | Disposition |
|---|---:|---|
| 1 | 5/8 passed | Retained under `attempts/attempt-1/`; the lesson, course-consent, and resume cases failed. |
| 2 | Unscored | Retained under `attempts/attempt-2-driver-draft/`; disqualified because the driver named desired closing behavior. |
| 3 | Reported 8/8, now ineligible | The complete output corpus was not archived; `attempts/attempt-3/MISSING-EVIDENCE.md` forbids using it as current release evidence. |
| 4 | 6/8 passed | Retained under `attempts/attempt-4/`; progressive post-error hinting and resume-state fidelity failed. |
| 5 | Composite 8/8, release-ineligible | Retained under `attempts/attempt-5-composite/`; only the two attempt-4 failures were rerun, so it did not satisfy the all-case fix-and-rerun gate. |
| 6 | Stopped after 5 cases | Retained under `attempts/attempt-6/`; the accessibility response omitted the explicit host-UI limitation and no-custom-control boundary. |
| 7 | 8/8, later invalidated | Retained under `attempts/attempt-7/`; it passed, then source changes made its exact bindings stale. |
| 8 | Unscored | Retained under `attempts/attempt-8-driver-context/`; stopped after seven cases because the runner prompt confused the read-only package with the learner workspace. |
| 9 | 8/8, later invalidated | Retained under `attempts/attempt-9/`; it passed, then final visual, isolation, scheduler, and routing remediation changed its bound source bytes. |
| 10 | 8/8, later invalidated | Retained under `attempts/attempt-10/`; practical-learning and visual-runtime changes made its source bindings stale. |
| 11 | Reported 8/8, rejected | Retained under `attempts/attempt-11/`; frozen-spec review found no bound execution and an incomplete project-takeover prohibition. |
| 12 | 7/8, rejected | Retained under `attempts/attempt-12/`; the lesson omitted an explicit retrieval horizon, and review exposed two routing defects. |
| 13 | 7/8, rejected | Retained under `attempts/attempt-13/`; routing was corrected, but the lesson still called its horizon unspecified. |
| 14 | Reported 8/8, rejected | Retained under `attempts/attempt-14/`; frozen-spec review found transfer before explicit learner explanation, so the passing receipt overstated the bound sequence. |
| 15 | 8/8, later invalidated | Retained under `attempts/attempt-15/`; it passed, then final runtime security remediation changed the bound routing source. |
| 16 | 8/8, later invalidated | Retained under `attempts/attempt-16/`; it passed, then the runtime contracts tree was added to the bound routing source. |
| 17 | 8/8, later invalidated | Retained under `attempts/attempt-17/`; it passed, then direct-model, canonical-route, and consent-source changes altered bound bytes. |
| 18 | 7/8, rejected | Retained under `attempts/attempt-18/`; the course response omitted the required explicit ephemeral alternative, so no passing receipt was written. |
| 19 | 8/8, later invalidated | Retained under `attempts/attempt-19/`; it passed, then final routing security and lesson-capability binding changed the bound source. |
| 20 | 8/8, later invalidated | Retained under `attempts/attempt-20/`; formatter-only normalization changed the bound routing source. |
| 21 | 8/8 passed | Current release-eligible run; all eight cases were regenerated from the final source and independently scored. |

The frozen rubric is `../../evals/forward-behavior.json`. An eligible run binds
the rubric, its own byte-final run manifest, seven teaching sources, the supplied
synthetic resume context, eight distinct fresh task identities, every output
byte, and two replayable execution files. The independent reviewer recomputed
all 20 declared bindings, replayed the execution fixture, and recorded item-level
judgments for every required and forbidden behavior.

## Multi-turn lesson integrity

The lesson case used one fresh `fork_turns:none` tutor. It received the candidate
skill, the learner request, and only natural learner replies; it did not receive
the rubric, prior outputs, or desired closing instructions. The exact transcript
contains five tutor and five learner turns: one initial error, one next-needed
hint followed by a turn boundary, a scaffolded repair, and an unseen unassisted
transfer. The transfer answer first appears in the learner attempt. The closing
evidence statement separates scaffolded from unassisted performance, leaves
delayed recall untested, and names a provisional one-week horizon with a
48-hour re-test.

## Practical executable-learning case

The practical case completes predict, run, inspect, modify, debug, explain, and
transfer against one replayable two-parameter Python model. Its six tutor and
six learner turns contain three exact command/output replays, separate runtime
evidence from learner performance, preserve a
complete script-free transcript, and require no optional dependency or second
teaching skill.

## Claim boundary

Attempt 21 is current release-eligible engineering evidence for its exact bound
bytes. It cannot satisfy EG-01 provider ablation, EG-02 measured SkillOpt
gain, EG-03 representative accessibility field evidence, EG-04 immediate human
benefit, EG-05 delayed retention and transfer, or EG-06 generalization.
