# Candidate verification through 97bf5c0

This is an additive receipt for the development branch, not release acceptance.
The installed v3.0.1 snapshot is unchanged. Frozen evaluators and historical
results were not rewritten. Later changes need their own verification.

## Aggregate quotas — f4c31b7

Twenty HTTP/security/job-budget tests passed. Two actual Chrome controls passed,
using a controlled broker response. Independent review reproduced loss of the
job ContextVar across Playwright callback greenlets; explicit callback binding
closed that bypass. A tiny cumulative quota blocked the response and a normal
allowance permitted it. These results do not establish authenticated Canva
access or browser operating-system resource limits.

## Offline setup boundary — 70d604f and 404b1e2

The explicit network opt-in applies to eleven standalone video-helper sets,
model acquisition, speech acquisition, Remotion setup, and learner-triggered
Pyodide loading within the documented scope. Independent review found that
`need()` rejected missing host dependencies before selecting an existing private
Python environment. The revision selects that environment first and forbids
new environment creation offline.

The focused suite passed twelve tests, including sixty-six actual synthetic
private-environment subprocess cases. The preceding helpers failed thirty-three
of the new cases as expected. Independent scoped re-review approved the repair.
The unchanged teacher suite then ran seventy-one tests: sixty-seven passed,
four skipped, zero failures. Vendor verification reported zero problems.

These are controlled runtime checks, not a new live voice-quality assessment.
Third-party executable content can still make network requests unless run in an
actual restricted environment; acquisition flags are not a network sandbox.

## Whole-course execution — 3bcc980 and 97bf5c0

The new explicit Docker adapter successfully extracted and built ordinary
courses, preserved linked course video manifests and local media, and rejected
hostile filesystem/network/process/resource cases. Browser tests exercised
fifty-nine lesson interactions and successful lesson/course visual QA.

The unchanged course-page checker still fails its persistence assertion because
it does not select the required progress-storage consent checkbox. A separate
standalone invocation reproduced eighteen passes and that one failure. The
adapter propagates failure and publishes no output. Successful complete
`validate` remains unverified; a separately versioned consent-aware checker
proposal is pending explicit approval.

Independent review also reproduced a cancellation defect: SIGTERM to the host
adapter left authored code running after its timeout. The revision adds scoped
catchable-signal cleanup and an independent trusted PID 1 deadline. Fourteen
focused tests passed, followed by three final controls after explicit
`--init=false`. The independent reviewer reran three termination controls and
approved the scoped repair. SIGTERM removed the container/snapshots. After host
SIGKILL, native, detached and browser execution stopped at the configured
deadline with exit 124 and no published output.

SIGKILL cannot run host cleanup. Stopped containers and private snapshots can
remain and require recovery using their exact recorded ownership; the guide
states this limitation. The broader initial fourteen-test run had one
cross-test container-name assertion failure. Its corrected owned-container
checks were tested separately; this receipt does not invent a clean rerun of
that entire original suite.

## Packaging and repository operations

At this revision, the embedded distribution verifier passed all 759 hashed
engine files. It does not hash the wrapper content. Vendor verification found
sixteen vendored entries, six copied files, six native entries and zero problems.

GitHub private vulnerability reporting was enabled and a subsequent repository
API read returned `enabled: true`. Candidate source was pushed and its remote
commit verified as `97bf5c00bd5bae1b27898442c20d95a8e47443b8`.
[Draft PR 16](https://github.com/praxstack/skills-and-personas/pull/16) remains a
development review, not an accepted release.

Remaining work includes enrichment process isolation, demonstrated packaging
repairs, improved visual artifacts, final broad review and release verification.
Portfolio diagnostic debt is still reported honestly; its green CI job tests
the diagnostics and does not mean the portfolio passes acceptance.
