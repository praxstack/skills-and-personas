# Supplemental behavior observations, 2026-10-24

This is an additive behavior audit. The frozen course checker remains unchanged
and continues to fail. The separately named `check-course-consent-v2.proposed.mjs`
is **UNAPPROVED**, version `course-consent/v2`; it cannot certify this run.

## Observed page behavior

`observed-v3/observations.json` records 34/34 supplemental observations after the
report-correctness repair described below. The earlier
`observed-v2/observations.json` records 31/31 supplemental observations in real
Chromium 153.0.8010.12. The fixture is the reviewed, first-party
`skills/teacher/skills/explorable/assets/examples/seasons.lesson.js`. Only its
synthetic course manifest and temporary browser state were created. No real
learner journal was created. Temporary course, bundles and browser contexts were
removed after the run; their exact generated HTML hashes are in the receipt.

| Exercised path | Actual observation |
| --- | --- |
| Course, consent declined | Done changes session progress; localStorage and sessionStorage remain empty; reload resets Done. |
| Course, affirmative consent | Consent and Done are stored; reload restores Done and the checked consent box. |
| Course, withdrawal | Unchecking removes progress and consent keys; reload starts at zero. |
| Explorer, default | All five authored explanations and answer explanations precede closed optional checks; Next and final satisfaction work without an answer. |
| Explorer, declined | Synthetic note and viewed steps write no local/session storage; reload clears note and location. |
| Explorer, affirmative consent | Synthetic note, step location and consent survive reload. |
| Explorer, withdrawal | Progress and consent keys disappear; reload clears note and location. |
| Explicit `?practice=1` | Next initially waits for an attempt; Show me reveals the answer immediately and unlocks Next. |
| Exit requested practice | The visible explanation link switches to `?practice=0` and restores open navigation. |
| JavaScript disabled | Bundled explorer displays the full static five-step lesson; its static link works offline. |
| Offline | All audit contexts had `offline:true` and HTTP(S) interception; no HTTP(S) requests or page errors were observed. |

`explanation-first.png` shows the complete first explanation, unchecked consent,
closed optional practice and enabled Next. `static-fallback.png` records the
JavaScript-disabled page. The explanation screenshot was visually inspected.

These are page observations, not evidence of universal live-chat adherence.
No prompted model sessions, explain-back question kind, blocked-storage browser,
other browsers, persistent browser profile, cross-device backup erasure,
narrated playback or human learning were tested. Storage snapshots cover
localStorage/sessionStorage, not every browser persistence API. Withdrawing
consent clears stored state; current in-memory state can remain until reload.
The page calls the immediate-answer control “Show me”; no literal “Answer now”
button or chat instruction was exercised.

## Report-correctness repair after independent review

Independent review found a product defect in the retained v2 receipt: its
closure report claimed five answers were “right first time” although all
attempt arrays were empty. The original audit checked closure availability,
not the accuracy of its claims, and missed this defect. The initial conclusion
that no product defect was demonstrated was incorrect.

`explorable.js` now includes an answer outcome only when there is at least one
recorded attempt. Empty question/alternate arrays produce no outcome line;
actual alternate explanations remain reportable without inventing correctness.
Correct first tries and prior misses retain their existing reports.

The strengthened real-browser v3 receipt records a five-step unanswered closure
with **no correctness claims**, an actual correct first try, and an actual
wrong-then-correct answer reported as one miss. `fix-round-1/` retains the raw
focused unit-test failure before the repair (3 passed, 2 failed), passing output
after the repair (5/5 passed), and browser output (34/34 observations passed).
The source-byte hashes and corrected reports are in the v3 JSON receipt. V1/v2
receipts remain unchanged and should not be interpreted as report-correctness
evidence. The frozen checker still fails its same historical reload assertion;
the proposed checker remains unapproved.

## Frozen checker comparison and proposed decision

The frozen `skills/teacher/skills/course/scripts/check_course_page.mjs` has SHA256
`6668f5a3b7b74ef9019416151a112a2c723003bfd9ae57c78d18092baa19a109`.
It clicks Done, never selects storage consent, reloads, then requires Done to
survive. The actual diagnostic output is:

```text
FAIL status survives a reload
course page: 18 passed, 1 failed
```

The unapproved proposal retains its existing map, keyboard, quiz, video-offer,
outline, notes and error assertions. Before the main Done interaction it adds a
declined-consent Done/reload branch, then explicitly checks `#cs-remember` before
the original Done interaction. Its reload assertion now explicitly concerns
consented state. A withdrawal/reload branch checks removal of this course's
keys. Its import path changes only because the proposal lives here.

The proposal executed diagnostically with `course page: 26 passed, 0 failed`.
This demonstrates the proposed consent distinction on this fixture. It does
not authorize replacing the historical checker, alter its governing status,
or grant acceptance. A human decision must separately approve and version any
governing evaluator change. Keep refused-consent nonpersistence as a positive
requirement; making the product persist without consent would violate it.

## Reproduce

After reviewing the repository seasons fixture, run from the repository root:

```sh
source /Users/prax/.local/share/prax-teach/runtime/v3/env.sh
node docs/teach-finish-20261024/behavior/audit-behavior-v1.mjs --trust-repository-fixture --out /tmp/teach-behavior-new-evidence
```

The output directory must not exist. Only the reviewed repository fixture is
accepted; this tool is not a sandbox for learner-authored JavaScript. It builds
with the first-party builder's explicit trust flag, exports the static bundle,
uses isolated contexts, then invokes both checkers as diagnostics. It neither
changes Docker context nor modifies media-container limits.

`observed-v1` is retained as the first audit attempt: 29/31 observations passed.
Two harness mistakes caused its failures: an assertion expected an internal
closure key instead of the actual visible report label; the proposal's notice
preceded its shebang. Both were corrected. A preceding import-depth mistake
prevented startup and generated no receipt. These were audit-tool errors,
not the later report-correctness defect. The initial implementation made no
product repair; independent review then identified the defect repaired above.
