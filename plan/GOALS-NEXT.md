# Next goals: two tracks (2026-10-19)

Context, verified on 2026-10-19:
- `teach-pro-max` → `prax-teach-v2` (installed, general: "Teach across subjects and levels").
- The v2.1/v2.2 candidate narrowed that to "Teach Prax C topics". Its only fact source is compiled C (`ptk/capture/c_runner.py`). It has one lexicon (`c.json`), C17 sources, and four C lessons; even the neuron lesson runs as `neuron.c`.
- The narrowing came from FREEZE.md ("for a C or DSA topic"). Prax had asked for "world class all kind of explainer visualisation".

So the work splits into two tracks that must not collide:
- **Track C** keeps and finishes the C/CS pack.
- **Track G** restores the general skill.

Both goals below are written to be pasted as a `/goal` prompt.

---

## Goal C: finish the C/CS lesson pack (owner: the current Claude session)

```text
/goal Finish Prax Teach's C/CS lesson pack so all four C lessons verify on the full claims suite, with no regression.

Repo: ~/Developer/prax-teach-evaluation-20261016/v2.1, branch candidate/v2.2 (start from tag v2.2-rc1 plus ae9b06f). Read FREEZE-v2.md, spec/SPEC.md v1.4, reviews/v2.2-final-result.md, reviews/v2.2-numeric-wording-audit.md, reviews/v2.2-smoke.md first.

Deliverables (each has a check):
C1. Every claim names its program, or its scene/step context makes the program unambiguous to a reviewer.
    Check: in the full suite, no claims-review rejection cites missing scope.
C2. The 8 P1 sentences in reviews/v2.2-numeric-wording-audit.md are fixed:
    - the cast called an object, in the claim and on the drawn label;
    - the binary64 tie wording and its cause;
    - "GCC" for gcc-16;
    - the neuron IVE answer timestamp;
    - the unscoped cards.
    Check: a fresh independent numeric and wording audit reports 0 P1.
C3. Claims jobs carry the captured clang diagnostics and each explorer's control spec (ranges, steps).
    Check: no rejection says "not in the job".
C4. Explanation-first leftovers:
    - Q&A layers lead with the explanation;
    - IVE explore controls are unlocked in default mode;
    - "teach me X" in the C workspace attaches a still.
    Checks: the lint test, IVE tests and holdout v2 rows H19 and H20 pass.
C5. ReLU pronunciation is fixed through a lexicon spoken form that whisper hears. The accepted-forms list is not widened.
    Check: the neuron video.sync gate passes.
C6. Smoke failures inside the C pack:
    - ive.pause-state works for loops (a revisited line);
    - the ~40-character code width at 390 px is documented and checked by `ptk validate`;
    - VERIFY.md and LESSON-MODEL.md match the gates (live control, figure.explore, `spoken` removed);
    - every failed gate has a non-empty reason.
    Check: smoke E5 (sum loop video) passes every automatic gate.
C7. Design verdicts are re-recorded by a separate screenshot reviewer, not by the implementer.

Acceptance (all must hold on one full-suite build of the 4 lessons):
- each lesson verified: value mutations 100%, claim mutations ≥ 90%, controls ≥ 95%, 3 of 3 lesson reviewers accept;
- independent numeric and wording audit: 0 P1;
- `ptk selftest`: 0 failed; only Anki not-run;
- holdout v2: no row worse than v2.2-rc1;
- the check-change audit finds no weaker check.

Rules:
- A run changes the candidate or the evaluator, never both. Any new or changed check is written failing first, then reviewed independently.
- Never read holdout/ or plan/proposed/.
- Don't touch the still projector's figure kinds, the fact-model schema or anything non-C. Track G owns those.
- Budget: 3 rounds, at most 2 per deliverable. Stop after 2 rounds with no newly passing criterion and report.
- Nothing is installed. Commit in small steps. Tag the result v2.3-c-rc1.
```

---

## Goal G: restore the general skill (owner: a fresh session, or Codex; not the C session)

```text
/goal Make Prax Teach teach any subject again, with the same verified quality bar, by generalising the v2.2 engine instead of the C pack.

Baseline: the installed general v2 (~/.agents/skill-library/prax-teach-v2, "Teach across subjects and levels"). Reference engine: ~/Developer/prax-teach-evaluation-20261016/v2.1 tag v2.3-c-rc1 (or v2.2-rc1 if Track C has not landed). Work on a new branch general/v3 from that tag. Read FREEZE-v2.md, plan/GOALS-NEXT.md, reviews/v2.2-final-result.md and reviews/v2.2-smoke.md first.

Step 0, before any code (evaluator; needs Prax):
G0. Freeze a FREEZE-v3 record for the general track.
    - Hidden test: ≥ 24 routing prompts and ≥ 8 end-to-end requests across at least 6 non-C subjects (maths, physics, biology, history, economics, ML).
    - Prax writes these, or approves ones an independent agent wrote in a separate session. The implementer never reads them; the sha256 is recorded.
    - Prax approves FREEZE-v3.

Deliverables (each has a check):
G1. A fact-source interface with 3 implementations:
    - compiled code (the existing C runner, unchanged);
    - computed values (sandboxed Python, exact arithmetic where it matters);
    - cited sources (stored, hash-bound passages).
    Every displayed value carries its source and has a tamper test.
    Check: tamper tests fail on a changed value for all 3 sources.
G2. Generic figure kinds for any topic shape:
    - labelled diagram;
    - plot or graph drawn to one scale;
    - timeline;
    - table or matrix;
    - process flow.
    Still, explorer, film and IVE all use them, alongside the four C mechanism kinds.
    Check: smoke E1 (struct padding still) no longer crashes, and the 8 end-to-end requests build.
G3. Domain lexicons and pronunciation for maths symbols and units, checked against whisper the same way C is.
G4. Three non-C exemplar lessons in all six media:
    - one maths lesson using computed facts;
    - one science lesson using cited facts;
    - one history or economics lesson using a timeline and cited facts.
G5. SKILL.md, the router and references are subject-neutral. The C pack is one optional pack, not the identity. Explanation first stays the default everywhere.

Acceptance:
- the 3 exemplars verified on the full claims suite: value 100%, claim ≥ 90%, controls ≥ 95%, 3 of 3 lesson reviewers accept;
- the WP10 visual measures pass at 390 and 1440 px in both themes; an independent reviewer gives Looks ≥ 8 and Explanation ≥ 8;
- hidden routing test (G0) ≥ 85% on mode, visual route and medium; end-to-end ≥ 6 of 8 pass every automatic gate;
- the 4 C lessons still pass everything they passed at the starting tag;
- `ptk selftest`: 0 failed;
- an independent check-change audit finds no weaker check;
- Prax's visual verdict on each exemplar is the final gate.

Rules:
- Evaluation changes (FREEZE-v3, the hidden test, new checks) land before implementation, on their own branch, with Prax's approval.
- A run changes the candidate or the evaluator, never both.
- Never read the hidden test.
- Don't edit the C lessons or the C runner except through the new interface.
- Budget: 8 rounds, at most 2 per deliverable. Stop after 2 rounds with no newly passing criterion and report.
- Nothing is installed. Tag the result v3.0-rc1.
```

---

## Order and ownership

1. Track C runs first: 3 rounds, small, on `candidate/v2.2`, tagged `v2.3-c-rc1`.
2. Track G starts from that tag. Its step 0 (FREEZE-v3 and the hidden test) can be prepared in parallel, because it touches no code.

| Track | Owns | Must not touch |
|---|---|---|
| C | `lessons/*`, `ptk/capture/c_runner.py`, `lexicon/c.json`, the IVE pause-state gate, C docs | still figure kinds, the fact-model schema, anything non-C |
| G | the fact-source interface, generic figure kinds, new lexicons, `lessons-general/*`, the subject-neutral SKILL.md and router | C lessons and the C runner, except through the interface |

Prax decides: FREEZE-v3 and its hidden test, the visual verdicts, and installation.
