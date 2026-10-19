# Teach v3 hardening verification

Date: 2026-10-20
Candidate branch: `fix/teach-v3-security-hardening-20261020`
Product patch: `4e5cd3b`

## Passed

- 71 teacher Python tests passed; 4 environment-specific tests skipped.
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

## Not certified yet

- `SEC-005`: URL, IP, redirect, credential, and size controls are present, but
  Requests and Chromium still resolve DNS when they connect. A hostile DNS
  server could change its answer after validation. A hardened transport must
  pin the checked address or enforce the policy at connection time.
- `SEC-003`: untrusted code no longer executes by default. The explicit trust
  path still runs reviewed code on the host; the repository does not yet ship
  a portable OS sandbox for hostile lessons.
- `SEC-008`: traversal, absolute paths, symlinks, hard links, ownership, and
  suffixes are checked. Course build inputs are not yet descriptor-bound from
  validation through every downstream renderer, so a concurrent file swap is
  still a proof gap.
- Release ZIPs and skills.sh still describe v3.0.0. They should be regenerated
  only after this candidate is accepted; the published tag stays immutable.
- Public side-branch cleanup is planned separately because it deletes refs or
  rewrites history.
