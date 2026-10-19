# Teach v3 hardening verification

Date: 2026-10-20
Implementation branch: `fix/teach-v3-security-hardening-20261020`
Product patch: `4e5cd3b`

## Passed

- 71 teacher Python tests ran: 67 passed and 4 environment-specific tests skipped.
- The browser run passed 59 interaction checks and all 18 paper, chalkboard,
  desktop, phone, and reduced-motion visual runs.
- A 28-second, 1280 by 720 H.264 animation rendered at 24 fps. Video QA found
  no black or frozen spans; its WebVTT captions were present.
- 7 Node security regressions passed for public upload confinement and citation
  handling.
- 3 course path tests and 8 resource-enrichment security tests passed.
- The top-level `teach-pro-max` verifier matched all 759 embedded files.
- An isolated `teach-pro-max` copy with no sibling `teacher` resolved its local
  fallback and passed the same integrity verifier.
- `vendor.py verify` reported 16 vendored skills, 6 copied files, 6 native
  skills, and 0 problems.
- Python compilation, Node syntax checks, and `git diff --check` passed.
- Gitleaks scanned the working tree and reported 29 existing generic patterns;
  none are in a changed or newly added file.

The first browser attempt inside the filesystem sandbox failed because macOS
denied Chromium's Mach rendezvous service. The same frozen suite passed when
rerun outside that sandbox with the installed local Chromium. No dependency was
downloaded for the rerun.

## Continuation verification

The remaining SEC-003, SEC-005 and SEC-008 implementation work is complete:

- 8 real Docker sandbox tests pass: legitimate Python/C++, host-file/env/network
  isolation, infinite JavaScript, outer deadline, memory/process/output budgets,
  missing-image failure. The reviewed ARM64 image ID is
  `sha256:c3adc592ed3413a4e7d4e9496911f317e223efb5d86712a18cb2286231c79a6a`.
- 11 transport regressions pass, including a resolver that changes public to
  private, numeric-address-only connect, mixed DNS answers and proxy rejection.
  A real HTTPS request to example.com returned 200 with TLS checking enabled.
- A real Chromium test passes: brokered public HTML works, a localhost fetch
  fails, WebSocket upstream connections are isolated. Service workers are
  disabled and browser sockets have no usable DNS/proxy route.
- 7 safe-course tests pass, including replacement of the original after snapshot,
  directory replacement after open, output symlink replacement, and video
  manifests beside linked courses.
- The unchanged full browser/video suite passes again: 59 interactions, 18
  visual runs, 673 rendered frames at 24 fps, and video QA with no black/frozen
  spans and captions present. The animation export has no audio; it is not a
  new narration-listening test.
- Fresh read-only bypass review found a linked-course manifest regression and
  a browser credential-origin gap. Both were fixed; final review reported no
  remaining concrete findings. It did not independently rerun Docker/browser.

Initial sandbox tests could not mount macOS private temp folders. Those attack
results were discarded until legitimate controls passed using a private,
VM-accessible staging directory. The first WebSocket browser test deadlocked
in Playwright's synchronous close callback; the corrected local-sink handler
passes. These were product/test integration failures, not accepted passes.

The first Linux CI run exposed a host-wide `RLIMIT_NPROC` conflict: the runner's
other processes shared its UID, so Node could not start. The redundant per-user
limit was removed. The container's cgroup PID limit remains 32; the fork test
now checks that exact kernel limit before attempting process exhaustion.

## Limits and release status

The sandbox is for executable lesson examples. Whole third-party course
rendering still needs a separately restricted environment; no trust gate was
removed. Containers rely on a trusted daemon/image and runtime/kernel security.
Authenticated Canva capture was not tested against a live personal account.
The request broker is covered by deterministic tests and real Chromium controls.

Public side-branch cleanup remains separate because it deletes refs or rewrites
history. The frozen quality evaluator and historical evidence were not changed.
Release packaging verification is recorded with the new release manifest;
v3.0.0 and its historical artifacts remain available for rollback.

## Published and activated

- [PR #15](https://github.com/praxstack/skills-and-personas/pull/15) merged as
  `cf87b5dfa285c34055af6dd0742257c5710d9f3d` after both the security workflow and
  CodeRabbit checks succeeded. The final tested skill trees match source
  revision `33cfd556ed0387c0b4991fcb6d4bb6f2ae912fad`.
- [Final PR security CI](https://github.com/praxstack/skills-and-personas/actions/runs/39332546209)
  passed on Linux; local Docker/Chromium checks passed on Apple Silicon.
- [v3.0.1](https://github.com/praxstack/skills-and-personas/releases/tag/prax-teach-v3.0.1)
  is public, non-draft and non-prerelease, with source ZIP, both standalone ZIPs,
  external manifest and checksums. All three anonymously downloaded ZIPs match
  the locally verified hashes and pass archive integrity checks.
- Both skills.sh pages return HTTP 200 with the expected skill/repository titles.
  This verifies listing availability; indexing is controlled by skills.sh.
- The canonical local skill links now select the versioned v3.0.1 snapshot.
  All 1,546 installed source files match the release ZIPs. Existing Codex,
  Claude, Hermes and Cursor aliases resolve to it. The active sandbox CLI
  successfully ran both Python and C++ against its model.
- The previous v3.0.0 snapshot is retained. A separate local activation manifest
  and rollback script preserve the exact preceding links; rollback dry run passes.
- No test containers remained. The isolated test VM was stopped; the default
  Docker context and broken pre-existing default runtime were preserved.

Public-history removal and broad portfolio redesign remain outside this patch.
No evaluator thresholds or private holdout inputs changed.

## Coverage correction

The broader review is not fully closed. SEC-009 has tested per-resource caps but lacks total-job quotas and browser-process resource ceilings. Whole hostile-course isolation and portfolio recommendations also remain. See [the complete matrix](COVERAGE-MATRIX.md); the existing focused passes do not certify these missing controls.
