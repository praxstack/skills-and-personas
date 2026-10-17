# Complete the general teacher skill

Status: engineering review complete; final six-hour run budget approved. See APPROVAL-AND-RUN-v3.md. The user authorized autonomous review, all four outcomes, and reuse of the existing engine. No product edit or new candidate clock starts in this review.

## Product and reuse

Keep prax-teach-v2 and its teach-pro-max wrapper. Reuse secure consented continuity, the static renderer, supported rich/host media and canonical skill links. Complete AskTheMove presentation, distinct course map and notes, ordinary-task routing, truthful current verification, actual teaching/render evaluation and accepted installation. Do not build an app, replace the renderer framework or require every short explanation to create a course.

Detailed scope: docs/teach-pro-max/review-2026-10-17/IMPLEMENTATION-SCOPE.md. Independent source review: docs/teach-pro-max/review-2026-10-17/ENGINEERING-REVIEW.md. That report supplies concrete defects, source references and a proposed exact path list.

## Architecture decisions

1. Put required teaching behavior in the existing core/normative documents. Optional detailed presentation references must not hide requirements from the frozen evaluation bundle.
2. Use precise static text/images with the existing safe renderer. Use supported rich/host delivery for animation and interactive controls. Do not loosen static sanitization.
3. Separate building visual artifacts from choosing them. Route selection must be read-only and bounded. Stage builds separately before immutable publication.
4. Preserve historical receipts. Select explicit versioned current evidence bound to exact source bytes. Never select by newest filename or silently accept missing proof. Keep receipts outside the content hash they attest to.
5. Separate evidence-method setup from candidate edits. Review and freeze any changed evidence-selection/gate implementation before the final candidate phase; retain all protected checks and the frozen teaching evaluator. Do not change the candidate and governing method within one run.
6. Preserve the existing documented continuity record-lifetime contract. Add reset/regrant coverage and explicit cancellation/reread instructions. Do not claim numeric revisions prevent stale updates across a full reset and regrant. Do not add a hidden tombstone or schema migration.

## Implementation tasks

- T1: Complete and independently check current-evidence plumbing and read-only visual verification. Preserve original historical package checks. Freeze the resulting governing method before candidate edits.
- T2: Add the requested presentation and course/notes behavior using existing instructions and actual reusable assets. Preserve explicit user overrides, complete static equivalents and save-nothing behavior.
- T3: Repair intent precedence and add public regressions for ordinary editing/deletion, explicit teaching-artifact creation, polite requests and misleading topic words. Preserve explicit API overrides.
- T4: Complete lifecycle documentation/tests, regenerate current companions and manifests, and run protected state/security plus supported-runtime suites. Retain all logs in a durable external directory.
- T5: Independently review final source; resolve substantive findings; freeze exact candidate bytes. Run unchanged paired teaching comparisons, secondary-host checks and actual rendered inspection. Retain every result.
- T6: Install only on acceptance. Record old canonical links, promote atomically, verify consumer links and fresh-session use, and retain rollback.

## Test and failure map

```text
Request
  + explicit override ................ preserve API precedence
  + ordinary edit/delete/write ....... regression tests, no teaching activation
  + teaching material or explanation . lesson/course intent and brevity tests
  + rich visual
      + valid current binding ....... read-only selection; immutable bytes
      + missing/stale/wrong receipt . clear supported fallback, no false claim
      + verifier timeout ............ bounded failure, no indefinite wait
      + concurrent/read-only use .... no build, no modified files

Teaching artifact
  + static .......................... sanitizer/publication checks retained
  + rich ............................ real control-state and browser inspection
  + reduced motion/no scripts ....... complete usable equivalent
  + course/notes .................... separate linked content, no forced folder
  + save nothing .................... no durable lesson or learner-state write

Continuity
  + active base + extension grant ... inspect/resume/update integration
  + declined/withdrawn ............... no personalization; inspect/export/reset work
  + stale same-lifetime revision .... reject without overwrite
  + full reset + explicit regrant ... test documented lifetime boundary
  + malformed/unsafe record ......... fail visibly, preserve state

Release
  source tests + independent review + held-out teaching + rendered inspection
    + all pass ...................... atomic install, fresh-session smoke, rollback
    + any fail or elapsed cap ....... preserve original installation and evidence
```

Failures above need behavioral tests and actual inspection where indicated. Do not substitute existence assertions, self-reported mastery or generated source for those checks. The independent review freshly ran 10 continuity checks and 8 current policy checks. Passing policy checks did not cover the reproduced ordinary-task regressions; add those cases.

## Performance

Remove route-time builds and bound verification subprocesses. Do not weaken state validation or introduce caching without measurement. Keep production references on demand. Use the existing evaluation concurrency of three case processes; do not add retries or repetitions to obtain a pass.

## Work order

Sequential implementation because routing, verification and package binding share modules. Independent read-only review and output grading can run separately when their inputs are fixed. Evidence setup precedes candidate edits; source freeze precedes acceptance evaluation; acceptance precedes installation.

## Not in scope

- New teaching app, persistent service, rendering framework or vendor account. Existing tools support the intended skill.
- Universal claims about every host or every medium. Verify supported delivery and disclose unavailable tools.
- Human-learning superiority or permanent mastery claims. Agent evaluations do not establish either.
- Learner schema migration, scheduler redesign or historical-evidence rewrite. Preserve existing protections and rollback.
- Unrelated dependency upgrades. Recorded dependency risks remain surfaced and must be considered before release.

## Run controls proposed at review

Original and currently accepted baseline remain identical, commit 286a98fc67486fa91bb19f34a9c0be347f5db029. Earlier candidate expired without acceptance. Proposed second and final candidate: four-hour target, six-hour elapsed stop from first candidate edit, unchanged 36 primary runs and four secondary checks, no threshold reductions or paid purchases. Finalize the exact mutable path list from the review, independently sealed inputs and rollback pointer before starting. The six-hour proposal is not approved merely because the user authorized autonomous review.

## GSTACK REVIEW REPORT

| Review | Runs | Status | Findings |
|---|---:|---|---|
| Architecture | 1 | Decisions resolved for plan | Preserve safe renderer; separate build/selection and historical/current evidence |
| Code quality | 1 | Implementation required | Ordinary-task intent precedence; precise reset/regrant lifetime boundary |
| Tests | 1 | Gaps mapped | Missing route regressions, read-only/timeout checks, current evidence and actual teaching/render acceptance |
| Performance | 1 | Implementation required | Route-time rebuild and unbounded subprocess chain |
| Independent source review | 1 | Completed, source not accepted | Five findings; 10 continuity and 8 policy checks passed |

VERDICT: Engineering review complete. Product implementation, evidence-method freeze, candidate freeze and acceptance remain outstanding. No installation authorized by test results yet.

**UNRESOLVED DECISIONS:**
- Resolved by the subsequent user approval: six-hour cap accepted. Keep the original installation until all acceptance checks pass. See docs/teach-pro-max/review-2026-10-17/APPROVAL-AND-RUN-v3.md.
