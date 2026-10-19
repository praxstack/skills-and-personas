# Repair plan: Prax Teach v2.2 candidate (proposal; nothing runs until Prax approves)

Goal: beautiful, mathematically correct teaching artifacts that build intuition. Each deliverable says how it improves the artifacts.

## Preservation (before anything)

- **Baseline:** v2 stays installed and untouched (`~/.agents/skill-library/prax-teach-v2`).
- **Current candidate:**
  - tag the current HEAD `v2.1-rc1`;
  - archive its lesson builds and reports under `archive/v2.1-rc1/`;
  - every later result is compared against both v2 and `v2.1-rc1`.
- **Evaluation stays separate from implementation:**
  - evaluator changes live on an `eval/freeze-v2` commit series that Prax approves;
  - implementation runs on `candidate/v2.2`;
  - no run changes both. The old holdout file is kept, and a relabelled holdout is a new file with both hashes recorded.

## Track 0: evaluator decisions (Prax only; no implementation)

From `ACCEPTANCE-COMPARISON.md`: approve, reject or edit items 1–6 and 8 one by one.

- **Item 5** (the teaching rule) needs Prax to relabel the predict-first holdout rows.
- **Canary mode** stays provisional.
- **Tracks A and B start only after Track 0 is settled,** so the targets don't move under the implementation.

## Track A: correctness and verification

| ID | Deliverable | How it improves the artifacts |
|---|---|---|
| A1 | Fix every wording the full claims suite rejected (detail below). | Learners never meet a false or confusing sentence. |
| A2 | Restore the three dropped claims with correct wording (detail below). | Brings back the "how to catch it", formula and recap teaching the drops removed. |
| A3 | Reviewer consistency (detail below). | Verdicts come from the source, not memory, so "verified" means something. |
| A4 | Teaching rule (after Track 0 item 5): explanation-first routing everywhere; quiz, exam-drill and Socratic opt-in; the checker counts the misconception-naming sentence correctly. | Matches Prax's preference: understanding first, practice by choice. |
| A5 | Outstanding checks (detail below). | No gate stays unaudited. Interaction stays real. |
| A6 | Learner-state privacy (detail below). | Learner data stays where the learner thinks it is. |

**A1 wording fixes:**
- factorial: "Three frames deep" against the four frames shown;
- factorial: t.213 "choose before the answer plays" appears in the transcript;
- neuron: the c.mul quote is cut without marking it, and the trailing-zero rule is missing;
- one-byte: c.samebits is too broad;
- switch: t.245;
- the Annex F citation is weak.

**A2 restored claims:**
- switch c.warn: "gcc-16 -Wimplicit-fallthrough warns when a case with statements falls into the next case; it stays silent when the next case only breaks", verified by a compiled run;
- neuron c.kformula: bounded to the slider range, with b's range right;
- one-byte c.recap: "the value 66 stays the same; the type and the bits change".

**A3 reviewer consistency:**
- every cited source paragraph (C17/N2176 clauses, *Deep Learning* §6.3.1) is stored with the lesson and hashed, so reviewers read the actual text and don't quote from memory;
- the rubric states how transcript and context sentences are judged;
- the lesson job is reviewed by 3 independent reviewers. Any disagreement is surfaced, and the claim is fixed or the rubric clarified.

**A5 outstanding checks:**
- audit the round-18 factorial-chip overlap exemption and give it a probe;
- decide AC-6.6 for panel lessons (proposed: every IVE needs a live control, since every explorer now has one; stricter);
- Anki import stays `not-run` unless Prax approves installing Anki.

**A6 learner-state privacy:**
- by default, refuse to create learner state inside a Google-Drive-backed folder unless the learner opts in;
- `delete` reports any surviving copy outside the workspace (such as `.tmp.driveupload`);
- the consent text names Google Drive;
- read-only commands never write xattrs after consent is withdrawn;
- warning text says "Google Drive", not "macOS backup".

**Fixed acceptance criteria for Track A** (all must hold on a full-suite build):
1. All four lessons `verified`: value mutations 100%, claim mutations ≥ 90%, controls ≥ 95%, lesson job accepted.
2. 3 of 3 reviewers agree on each lesson job.
3. A numeric audit and a wording audit, both by an independent agent, find no false or misleading statement.
4. `ptk selftest`: 0 failed. Live transcript tests pass for every mode. Every `not-run` is listed with an approved reason.
5. A6 behaviour is covered by tests, including a delete test in a Drive-backed probe folder.

**Rounds:**
- Estimate: 4 (A1+A2, A3, A4, A5+A6), plus 1 spare.
- Stop rule: at most 2 rounds per deliverable. A deliverable with 2 rounds of no newly passing criterion is parked and reported. The track stops at 5 rounds, whatever happens.

## Track B: visual quality

| ID | Deliverable | How it improves the artifacts |
|---|---|---|
| B1 | True landscape stills (detail below). | The figure carries the idea at a glance. |
| B2 | Clearer mechanism diagrams (detail below). | Each lesson shows the mechanism, not just code. |
| B3 | Video typography and layout (detail below). | Readable at a glance. The mechanism dominates. |
| B4 | Captions that change with state (detail below). | Text and picture always tell the same story. |
| B5 | Narration (detail below). | Calm, clear and direct. Code tokens are said correctly. |

**B1 true landscape stills:**
- width ≥ 1.5 × height;
- one figure-led composition per lesson, like Atlas;
- no code block or hashes on the still; provenance moves to the caption, alt text and metadata;
- a portrait variant for phones.

**B2 mechanism diagrams:**
- switch gets a real path figure (from its explorer);
- factorial gets a stack column with return values flowing up, replacing the arc tangle;
- one-byte draws all 4 bytes of `a` with the low byte highlighted, plus the double's 8 bytes;
- neuron stays as the reference.

**B3 video typography and layout:**
- output text at least as large as its code line;
- teaching text ≥ 28 px at 1080p;
- the mechanism figure takes ≥ 55% of the frame;
- no empty region over 20% of the frame;
- on phones, the IVE puts the figure above the fold.

**B4 changing captions:**
- every explorer sentence is bound to live state (the neuron slider caption) and checked after each control step;
- the `z = 1.11022e-16` case is explained (rounding in binary64).

**B5 narration:**
- ≤ 170 wpm per line, measured from the audio;
- a lint list of hedges ("in this lesson's drawing", "on this machine") outside claims that need them;
- no verbatim repeats;
- pronunciation fixed ("unsigned char");
- values appear when spoken.

**Fixed acceptance criteria for Track B:**
1. The automated measures above pass for all four lessons in both themes at 390 and 1440 px. Each measure is a stricter check, added before implementation and reviewed.
2. An independent five-lens reviewer gives every lesson Looks ≥ 8 and Explanation ≥ 8. These are reviewer judgments.
3. **Prax's visual verdict per lesson, against Atlas, is the final gate.**

**Rounds:**
- Estimate: 4 (B1+B2, B2 finish, B3+B4, B5), plus 1 spare.
- Stop rule: same as Track A. The track stops at 5 rounds.

## Order and concurrency

1. **Track 0 first:** Prax's decisions.
2. **A1 and A2 next.** They change lesson text, and the rest depends on stable text.
3. **Then A3–A6 and Track B in parallel.** Each owns separate files:
   - A: `verify/**`, `route*`, `protocol.py`, `state/**`, lesson claims;
   - B: projectors, templates, lexicon, lesson figure and storyboard fields.
4. **Final:** a read-only verification (full suite, holdout under the approved FREEZE v2, protected checks), then Prax's visual acceptance.
