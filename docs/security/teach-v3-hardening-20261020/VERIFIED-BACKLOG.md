# Verified backlog

Evidence was checked against public revision `dc6a498`; statuses below distinguish source defects from evidence semantics and external cleanup.

## Source and packaging defects to repair

| ID | Priority | Status | Problem |
|---|---:|---|---|
| SEC-001 | P1 | fixed in candidate; focused exploit and control tests pass | Public video upload accepted unconfined lesson paths and followed links. |
| SEC-002 | P1 | fixed in candidate; static sink removed | Skillpack health actions reached shell `eval`. |
| SEC-003 | P1 | default path fixed; portable hostile-code sandbox still open | Routine lesson validation executed authored JS, Python, and C/C++ on the host. |
| SEC-004 | P1 | fixed in candidate; exact-host tests pass | Domainless cookie dictionaries could be sent to arbitrary resource hosts. |
| SEC-005 | P2 | mitigated; DNS-rebinding-resistant transport still open | Resource enrichment permitted private-network and metadata requests and unchecked redirects. |
| SEC-006 | P2 | fixed in candidate; mutable commands removed | Installer examples executed mutable branches, `@latest`, and raw `main` content. |
| SEC-007 | P2 | fixed in candidate; link tests pass | Journal operations followed workspace links and used predictable replacement paths. |
| SEC-008 | P2 | fixed for traversal and links; concurrent swap hardening remains | Course manifest paths and narration identifiers could escape their roots. |
| SEC-009 | P2 | fixed in candidate; byte and artifact budget tests pass | Remote bodies and browser captures lacked transfer and artifact budgets. |
| SEC-010 | P3 | fixed in candidate; mode tests pass | Journal privacy depended on the ambient umask. |
| SEC-011 | P3 | fixed in candidate; scheme and CSP tests pass | Generated citation links accepted active URL schemes. |
| REL-002 | P1 | fixed in candidate | A nested teach-pro-max copy diverged and defaulted some topics to practice-first. |
| REL-003 | P1 | fixed in candidate; 759-file verifier passes | The published teach-pro-max integrity verifier failed on `evidence/verification/full.json`. |
| REL-004 | P1 | fixed in candidate; isolated standalone install passes | A single-skill teach-pro-max install lacked the sibling teacher it required. |
| PED-001 | P1 | fixed in candidate | Subject and series references still prescribed practice/recall before explanation. |
| DIST-001 | P2 | fixed in candidate | Teaching deliverables contained unrelated Codex CLI configuration and rollback material. |
| DOC-001 | P2 | fixed in candidate; network fallback now opt-in | Diagram rendering sent source to Kroki by default without a clear explicit network choice. |
| DOC-002 | P3 | partly fixed | Counts, README paths, and tool inventory text contain stale values and local absolute paths. |

## Evidence/reporting corrections, not product certification failures

| ID | Status | Required action |
|---|---|---|
| EVID-001 | substantiated | Report `52/56` automated and four human-listening judgments separately; do not rewrite the frozen report. |
| EVID-002 | substantiated | Mark hard-coded review fields as assertions rather than observed results; replace them in a future evaluator version only with explicit approval. |
| EVID-003 | substantiated | Add errata that activation approval provenance was ambiguous. |
| EVID-004 | substantiated | Describe the one-case routing gain and lack of baseline E2E measurement accurately. |

The learner later explicitly stated that all four clips were heard and sounded good. That supports four human listening judgments, but it does not turn them into automated measurements or justify editing the frozen evaluator.

## Operational or destructive work kept outside this patch

| ID | Status | Required action |
|---|---|---|
| REL-001 | fixed operationally | The local rollback manifest now points to a read-only snapshot from commit `f54d334`; the active v3 links were not changed and the rollback dry run passes. |
| PRIV-001 | credible and partly reproduced | Public side branches contain private/local artifacts and large archives. Prepare exact branch/object inventory; deletion or history rewrite requires a separate destructive-action decision. |

## Skill-system gaps

- One sandbox contract for all lesson code execution.
- One safe-fetch library for URL schemes, DNS/IP policy, redirect revalidation, credentials, and byte budgets.
- One safe-path/private-file library for containment, link rejection, descriptor binding, and modes.
- Reproducible release generation so aliases, manifests, ZIPs, source, and skills.sh instructions cannot drift.
- CI for lint, duplicate-name detection, distribution integrity, safe archives, focused security regressions, and clean standalone installs.
- A declared rule that the canonical teacher's explanation-first, safety, and privacy policy overrides bundled specialist defaults.
- Honest capability metadata: offline core versus opt-in downloads, network-required renderers, and unavailable tools.
- License inventory for vendored media skills and immutable upstream provenance.
