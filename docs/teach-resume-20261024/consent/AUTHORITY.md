# Governing evaluator: course-consent/v2

Adopted 2026-10-24 in the method-only Task 1 phase, from base `a06cea0`.
The canonical implementation is
`skills/teacher/skills/course/scripts/check_course_page_v2.mjs`.
`test_course.py` deliberately selects v2 by default; the restricted sandbox's
`validate` mode invokes that same executor through its unchanged supervisor.

## Human approval and provenance

The user approved the previously prepared consent-aware proposal in the current
conversation on 2026-10-24. The controller reports that the message begins
“The narrated video sometimes fails to play under the agreed memory and process
limits...”, requests “fix do research dont give up”, repeats the prepared
explanation “Your approval would let us use that corrected test to judge whether
a release is ready.”, and ends with the standalone word “approved”.
No immutable message identifier or exact timestamp is exposed by this API; none
is invented here. The implementation brief is
`.superpowers/sdd/RESUME-20261024/task-1-brief.md`, with binding constraints in
`global-constraints.md` beside it.

Approval covers adopting the separately named `course-consent/v2` method.
It preserves refusal/nonpersistence, affirmative consent/resume and withdrawal.
It does not authorize changing human identity policy, media thresholds, teaching
content, playback implementation or the required release evidence.

## Frozen source identities (SHA256)

| Source | SHA256 |
| --- | --- |
| Historical `check_course_page.mjs` | `6668f5a3b7b74ef9019416151a112a2c723003bfd9ae57c78d18092baa19a109` |
| Approved source proposal `docs/teach-finish-20261024/behavior/check-course-consent-v2.proposed.mjs` | `f9fd595aac5487685df1af61567ae7d8641f6dc068d20dd0ae15ac774a6b96ca` |
| Canonical `check_course_page_v2.mjs` | `b2d29644b699a8e9fd5cb072d1969188b3969354a70bd5be65afbda513541ebc` |

The adopted file differs from the approved proposal only in its authority
comment, usage filename and local Playwright-helper import. All executable
assertions are copied unchanged. Source hashes are separate from test receipts.
The old checker, proposal and all old receipts remain unchanged. Their original
UNAPPROVED notices describe their historical status; this additive record
establishes the later approval and named canonical version.

Task 2 and Task 3 must hold this governing method, holdouts, thresholds and
evidence rules fixed. Any later governing change needs separate human approval
and a new version; later product results cannot rewrite old failures.
