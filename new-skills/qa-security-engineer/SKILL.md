---
name: qa-security-engineer
description: 'Quality assurance plus security engineering for software products. Use when designing test strategy, writing test plans, reviewing code for security, running SAST/DAST, doing penetration tests, managing vulnerabilities, validating compliance (GDPR/SOC2/PCI/HIPAA), responding to incidents, or hardening APIs. Covers test pyramid, unit/integration/E2E, performance/load testing, OWASP Top 10, authentication/authorization review, encryption, secrets hygiene, logging/monitoring, and post-incident forensics. Keywords: QA, testing, test automation, security, SAST, DAST, penetration test, pentest, OWASP, vulnerability, CVE, CVSS, GDPR, SOC2, PCI, HIPAA, compliance, incident response, Cypress, Playwright, k6, Burp, ZAP, Semgrep, Snyk.'
---

# QA / Security Engineer

**Audience:** Engineers responsible for test strategy, security review, and compliance.

**Goal:** Ship software that's tested where it matters and secure by default — without bottlenecking engineering or creating theater.

## Core Responsibilities

- **Design test strategy proportional to risk.** Test pyramid is an ideal, not a mandate; financial/PII-handling code deserves more integration and security tests, pure UI polish deserves less. Not every line needs 100% coverage; boundaries, contracts, and business logic do.
- **Shift left on security.** Security flaws caught in design cost 10x less than caught in production. Architecture review for vulnerabilities, threat-model new features, enforce patterns via lint rules and CI gates — don't rely on manual audits.
- **Advise, don't implement for developers.** Your leverage is in pattern-setting, test harnesses, CI gates, and training. Fixing one engineer's bug doesn't scale; fixing the class of bugs does.
- **Manage vulnerabilities by exploitability, not just CVSS.** A CVSS 9.8 in a library you don't reach is lower risk than a CVSS 5 in your auth path. Context beats score.
- **Own compliance as engineering, not paperwork.** GDPR deletion, SOC2 access logs, PCI scope reduction — these are code and architecture problems, not docs.
- **Make incidents rare and their recovery fast.** Preparation (runbooks, drills, monitoring) matters more than heroic response. Post-incident learnings prevent recurrence.

## Decision Framework

**Test pyramid allocation (starting point, adjust by risk):**
- ~60% unit: business logic, utilities, validators, pure functions. Fast, isolated, run on every save.
- ~30% integration: API endpoints, DB operations, service boundaries with mocks only at the edge. Run on every PR.
- ~10% E2E: critical user flows only (signup, checkout, core value moment). Run on every deploy to staging.

**Shift allocation when:**
- Heavy microservice boundaries — more integration, less unit
- Critical financial/payment flows — more E2E, contract tests between services
- UI-heavy with complex interactions — more component tests (middle of pyramid)
- Data pipelines — property-based tests and golden-output tests dominate

**Coverage is a diagnostic, not a goal.** 95% coverage with bad assertions is worse than 70% with great ones. Look at branch coverage, mutation score (Stryker, PIT), and fault injection.

**When to write what test:**
- Pure function — unit, lots of edge cases
- Validator / business rule — unit + integration with real DB for type/constraint errors
- API endpoint — integration test against app + real DB in docker
- User flow — E2E, but only the "must work or we lose money" ones
- Race condition / ordering — focused concurrency test with controlled clocks
- Performance regression — benchmark with threshold alerts

**Security test prioritization:**
1. Authentication & session management (account takeover is worst-case)
2. Authorization / access control (horizontal + vertical privilege escalation)
3. Injection surfaces (SQL, NoSQL, command, template, LDAP)
4. Secrets handling (leaked logs, client bundles, version control)
5. Input validation at trust boundaries (user — API, external — internal)
6. Dependency vulnerabilities (reachable paths, not total CVE count)
7. Transport + storage encryption
8. Logging / monitoring gaps (can you detect the attack?)

**SAST vs DAST vs IAST vs SCA:**
- **SAST** (Semgrep, SonarQube, CodeQL): reads code, finds patterns. Fast, but lots of false positives. Catches code-pattern issues.
- **DAST** (OWASP ZAP, Burp): scans running app. Finds runtime-visible issues (headers, misconfigs, some injection). Slow; can miss auth'd paths without config.
- **IAST** (Contrast): instruments the running app. Higher accuracy, requires integration.
- **SCA** (Snyk, Dependabot): scans dependencies. Catches known CVEs but not reachability.

All four together catch different things. None catches everything; human review still matters for auth logic and business rules.

**Severity classification (CVSS + context):**
- CRITICAL: remote code execution, auth bypass, data exfiltration at scale — fix in <24h.
- HIGH: stored XSS, privilege escalation, exposed sensitive data — fix in <7d.
- MEDIUM: reflected XSS, missing headers, information disclosure — fix in <30d.
- LOW: best-practice violations, cosmetic — next release.

Override CVSS up if exploit-in-the-wild, down if unreachable code. Document the reasoning.

## Quality Gates / Checkpoints

**Pre-development:**
- Requirements reviewable for testability (can each acceptance criterion be validated?)
- Architecture review for security (threat model, trust boundaries)
- Test plan drafted

**During development:**
- Unit tests written alongside code (not after)
- SAST runs on every commit
- Code review flags security patterns (parameterized queries, output encoding, auth on every endpoint)

**Pre-merge:**
- All tests passing (unit, integration, E2E for touched flows)
- Coverage threshold met (team-defined, typically 70-80% for critical modules)
- SAST clean (or suppressions documented)
- Secrets scanner clean (git-secrets, gitleaks, trufflehog)
- No critical/high vulns in dependencies (Snyk, npm audit)
- Performance regression tests (benchmarks within threshold)

**Pre-deployment:**
- DAST scan on staging
- Performance test against SLO
- Security review for major releases
- Penetration test for significant new attack surface (annually or major releases)

**Post-deployment:**
- Smoke tests in production
- Security monitoring and alerting verified
- Error rates within baseline
- No new vulnerability signals (WAF logs, EDR)

## Anti-Patterns

- **NEVER** concatenate user input into SQL, shell commands, or template strings. Parameterize. Use libraries that do this right (Prisma, SQLAlchemy, pg with `$1` placeholders).
- **NEVER** store passwords with MD5, SHA-1, SHA-256 alone, or reversible encryption. Use bcrypt, scrypt, or Argon2 with appropriate work factor.
- **NEVER** trust the client. Repeat all validation and authorization server-side even if the client does it.
- **NEVER** return secrets, password hashes, internal IDs, or stack traces in API responses. Build explicit response DTOs.
- **NEVER** allow CORS `*` on authenticated endpoints. Whitelist origins.
- **NEVER** disable SSL certificate verification "temporarily." It gets committed and deployed.
- **NEVER** commit secrets. Even in old commits — history is searchable. Use pre-commit hooks (gitleaks) + rotate any leaked secret regardless of exposure length.
- **NEVER** test only the happy path. Attackers test edge cases by definition.
- **NEVER** rely on obscurity. Security through obscurity fails; layer it with real controls at most.
- **NEVER** log PII, passwords, tokens, full credit card numbers. Mask at the logging boundary, not at the caller.
- **NEVER** treat auth'n and auth'z as the same check. Auth'n is "who are you"; auth'z is "what can you do." Both required, separately, on every protected endpoint.
- **NEVER** trust JWTs without verifying signature AND issuer AND audience AND expiration. `none` algorithm attacks still happen.
- **NEVER** allow time-based secrets comparison (leaks via timing). Use constant-time compare.
- **NEVER** ship flaky tests. A test that fails 2% of the time is training engineers to ignore failures.
- **NEVER** suppress SAST findings without a documented rationale and expiry.
- **NEVER** treat "100% coverage" as a quality signal. It's a necessary-but-not-sufficient check.
- **NEVER** declare an incident closed without a retro and follow-ups.

## Standard Workflow

1. **Test strategy design.** Analyze risk (user impact, data sensitivity, regulatory). Allocate test effort accordingly. Document pyramid shape expected.
2. **Test plan per feature.** Scope, risks, test cases at each level, environments, entry/exit criteria.
3. **Automate where it pays.** CI harness, test data management, seed scripts, flaky-test quarantine.
4. **Pair with developers on tests.** Especially for tricky cases (concurrency, auth, data consistency). Not to write them for devs — to set the pattern.
5. **Security review checkpoints:** architecture design, PR review, pre-release.
6. **Vulnerability triage.** Daily intake from SAST/DAST/SCA/reports. Classify, route, track to closure.
7. **Compliance validation.** Map controls to code/infra/process evidence. Automate evidence collection.
8. **Incident preparation.** Runbooks, on-call rotation, tabletop drills, access/tooling readiness.
9. **Incident response.** Detect — contain — eradicate — recover — postmortem — prevent recurrence.
10. **Training & culture.** Lunch-and-learns on OWASP, secure-code workshops, blameless post-mortems. Security is everyone's job.

## Deliverables Contract

**Test plan includes:**
- Scope (in + out)
- Strategy per level (unit/integration/E2E/perf/security)
- Test environments + test data
- Entry criteria (feature complete, env ready)
- Exit criteria (all tests pass, coverage met, no criticals)
- Risks + mitigations
- Schedule

**Security audit report includes:**
- Executive summary (severity counts, overall posture)
- Each finding: severity, CVSS, affected component, PoC, impact, remediation
- Compliance status (OWASP Top 10 pass/fail; relevant frameworks)
- Prioritized remediation plan (immediate / short-term / long-term)

**Vulnerability report includes:**
- ID, title, severity, CVSS
- Affected component + introduction point
- PoC with reproducible steps
- Impact (confidentiality / integrity / availability)
- Remediation (hotfix + permanent fix, with code example)
- Timeline (discovered — fixed — verified)
- References (OWASP, CWE, CVE)

**Incident postmortem includes:**
- Timeline with evidence
- Root cause analysis (use "5 whys" or similar — stop blaming a person)
- Customer impact (scope, duration, severity)
- What went well
- What went poorly
- Action items (owner, date) — NOT "try harder next time"
- Follow-up to verify actions landed

## References

- `references/testing-strategy.md` — pyramid allocation, unit/integration/E2E patterns per language, flaky-test handling, test data, performance testing (k6, Artillery). CONDITIONAL (load when designing tests).
- `references/security-methodologies.md` — OWASP Top 10 detailed, SAST/DAST/IAST/SCA tool matrix, pentest methodology, auth/session/crypto review checklists. MANDATORY for any security review.
- `references/compliance-frameworks.md` — GDPR, SOC2, PCI DSS, HIPAA control mappings and test patterns. CONDITIONAL (load when in scope).
- `references/performance-testing.md` — load/stress/spike/soak test patterns, SLOs, interpreting results, capacity planning. CONDITIONAL (load when validating performance).
