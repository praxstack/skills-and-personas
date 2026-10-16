# Visual intuition v1 policy test changes

The approved revision makes complete bounded explanation the unqualified teaching
default. Practice and continuity are separate choices. Historical fixtures and
receipts are unchanged and certify only their original bytes and policy.

## Superseded assertions

- `test_live_lesson_gate_requires_turn_boundary_and_complete_close` is renamed
  `test_visual_intuition_v1_optional_assessment_and_honest_close`. Its attempt,
  progressive-hint, honest-evidence and retention language remains checked;
  new assertions scope attempt gates to learner-chosen assessment and require
  complete explanation without mandatory prediction/quiz/teach-back barriers.
- `test_resume_gate_preserves_scaffold_metadata_and_retests` is renamed
  `test_resume_preserves_scaffold_metadata_without_mandatory_retest`. Only the
  mandatory fresh unassisted prompt assertion is replaced with absence of a
  mandatory assessment. Exact responses, hint levels, scaffold labels and no
  invented history remain required.
- `test_post_error_hint_turn_precedes_substantive_feedback` is renamed
  `test_chosen_assessment_post_error_hint_precedes_substantive_feedback`, adding
  assessment scope. Its one-hint return boundary remains checked.

No historical routing fixture assertion required replacement. `test_core_cli`
adds default-lesson and sentence-override checks. The new versioned fixture and
`test_visual_intuition_policy_v1` cover default lesson, brevity, ordinary coding,
Answer now, explicit course consent and explanation-vs-quiz visual retrieval.

## Preserved protections

No consent, filesystem, hashing, evidence, scheduling, export, deletion,
correction or factual-honesty assertion is removed. Quiz leakage checks remain
active across source, alternatives and rendered surfaces. Structural visual
checks are not browser inspection or evidence of human learning. No old receipt
is presented as current evidence for this revision.
