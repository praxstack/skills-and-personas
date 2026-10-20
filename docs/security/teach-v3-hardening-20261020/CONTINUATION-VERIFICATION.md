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

## Addendum through `7777702`

The preceding snapshot remains historical. Enrichment process isolation and the demonstrated packaging defects listed there now have reviewed candidate repairs. Final visual work, broad review and release verification remain pending.

The explicit enrichment runner (`444f20d`) uses a standalone-built immutable image `sha256:6bae2ca9852061ba0abebef8b07f9f3ea96a799c9f7ef4d31f0a6f135ae5ea6c`. Its author ran 50 sandbox controls and 21 transport/budget controls. The controller independently reran all 50 sandbox controls, with no skips, in 38.495 seconds. Independent review also passed 18 host controls and three real browser/container controls. Resource ceilings and authenticated-header scope are documented in the runner README; direct host imports remain unsandboxed, and no personal provider authentication or kernel-enforced public-only egress is claimed.

That review found a P2 in test cleanup: shared-prefix timing could select a concurrent job. Revision `7777702` binds the fixture to an identity and mounts selected before launch and removes only its inspected immutable container ID. The author and independent reviewer each passed three actual-container controls after the revision, including unrelated-job survival under SIGTERM and SIGKILL. Independent review time was 15.328 seconds. Both runtime copies remain identical. These focused revision results do not pretend the earlier full-suite run occurred after the revision.

Portfolio repair `0801771` restored 19 runtime/setup/test files, repaired nine local links and six description syntax defects, corrected the techtutor name, and retained the idea-lineage distinction while removing a nonexistent document pointer. Independent review passed five packaging tests, including synthetic transcript ingestion and handoff. The copied suite passed 39 tests and skipped 33 opt-in/dependency-dependent cases. See PORTFOLIO-REPAIR.md for the retained whitespace caveat and remaining 14 duplicates, 20 lint failures and 126 link findings. No divergent skill was silently deleted.

Remote candidate `1839ad37e1be28af9d01015e872704abb1384ff3` was verified after push. Its four security/diagnostic CI checks passed. CodeRabbit's green status explicitly skipped draft review; Macroscope was skipped. Neither is claimed as a substantive independent review. This addendum records local results through `7777702`; remote verification is limited to the exact hash stated. Installed snapshots and frozen evaluators remain unchanged.
