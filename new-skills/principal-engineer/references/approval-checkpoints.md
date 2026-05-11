# Approval Checkpoints

**When to load this file:** Load before running Checkpoint 1 (design review) or Checkpoint 2 (code/merge review). Contains the required-artifact intake lists, per-dimension review rubrics, and the decision-outcome decision tree.

---

## Checkpoint 1 — Architecture Design Approval

**Trigger:** before any implementation work begins.

### Required artifacts (reject intake if any are missing)

1. Problem statement — what and why.
2. Solution diagram — high-level architecture, components, data flow.
3. Technology choices — languages, frameworks, services, with justification.
4. Data model — schema, consistency model, growth projection.
5. API contract — endpoints, request/response schemas, auth, versioning.
6. Integration points — how this fits existing systems, coupling analysis.
7. Scalability plan — how it handles 10x users/data/traffic.
8. Security & threat model — STRIDE-level threats + mitigations.
9. Failure modes — what can go wrong, graceful degradation plan.
10. SLO targets — latency p50/p99, availability, throughput.
11. Test strategy — unit, integration, load, security.
12. Rollout & rollback — deployment approach, feature flags, rollback trigger.

If any item is "TBD" or missing, return the intake. Do not partial-review.

### Review rubric — score each dimension

**Functional correctness**
- Solves the stated problem.
- Edge cases addressed (not handwaved).
- Error paths specified, not just happy path.

**Scalability**
- Handles 10x current load without redesign.
- No obvious bottlenecks (single DB, single queue, single region if HA needed).
- Horizontal scaling possible for hot services.
- Caching strategy appropriate to read/write mix.

**Performance**
- Latency targets achievable given dependencies' latencies.
- Algorithmic complexity acceptable.
- Network calls minimized in critical paths.
- DB access optimized (indexes justified, no unbounded scans).

**Security**
- Authentication mechanism specified.
- Authorization model (RBAC/ABAC) at resource level.
- Input validation at every trust boundary.
- Secrets management (no hardcoded, no logged).
- PII handling and data retention.
- Threat model covers STRIDE.

**Reliability**
- Failure modes of each dependency identified.
- Circuit breakers on external calls.
- Retry with exponential backoff + jitter.
- Timeouts configured explicitly (never "default").
- Idempotency for retryable operations.
- No unbounded resource consumption (no unbounded queues, no unbounded loops).

**Maintainability**
- Boundaries align with domain model (bounded contexts).
- Complexity justified (not over- or under-engineered).
- Consistent with existing system patterns.
- Tech debt created is explicit and tracked.

**Observability**
- Structured logs with correlation IDs.
- RED metrics (Rate, Errors, Duration) for every service.
- USE metrics (Utilization, Saturation, Errors) for resources.
- Distributed tracing across service boundaries.
- Health check endpoints for orchestrator.

**Cost**
- Estimated infrastructure cost for expected load.
- Auto-scaling policy to shed cost at low load.
- Data transfer costs considered (cross-AZ, cross-region, egress).

### Decision tree

- All dimensions ≥ Adequate, no Critical issues → **APPROVED**.
- 1-3 Medium issues fixable at code time with verifiable conditions → **APPROVED WITH CONDITIONS** (list each).
- Any High issue, or multiple Medium that compound → **NEEDS REVISION**. Send back with detailed feedback.
- Violates a non-negotiable (shared DB across services, sync chain >2 deep, no threat model, no failure modes) → **REJECTED**. Propose alternative.

Do not mix verdicts. Do not say "approved but fix these critical issues". Approved means approved.

---

## Checkpoint 2 — Code Review Approval

**Trigger:** before any code merges to main/production branch.

### Required PR state (reject PR if any missing)

- Matches approved design from Checkpoint 1 (no unapproved deviations).
- All tests pass in CI.
- Coverage ≥ 80% for new code (or project standard).
- Linter passes with zero errors.
- Security scan (SAST, dependency) passes.
- Docs updated (API, README, inline for complex logic).
- Migration scripts present if schema changed, with rollback plan.

If any are missing → close PR, request resubmit. Do not review.

### Review rubric

**Architecture adherence**
- Matches approved design. Any deviation → back to Checkpoint 1.
- Consistent with established codebase patterns.
- Dependencies point in allowed direction (no inner layer depending on outer).

**Code quality**
- Readable and self-documenting.
- No commented-out code (version control exists).
- No magic numbers — named constants.
- Error handling comprehensive; no empty `catch`, no `catch Exception`, no silent failures.
- DRY where it aids clarity; WET where abstraction would obscure.
- Naming consistent with codebase.

**Performance**
- No obvious O(n²) where O(n) is trivial.
- No N+1 queries (check every loop that calls DB).
- DB queries use indexes (verify with EXPLAIN for non-trivial queries).
- Caching applied at appropriate layer.
- Resources closed (connections, files, streams).

**Security**
- Input validated at every trust boundary.
- Parameterized queries (no string concatenation into SQL).
- Output encoded for context (HTML, JS, shell, LDAP).
- CSRF tokens where applicable.
- No secrets in code, logs, or error messages.
- Authn/authz checks on every protected endpoint.
- Dependency vulnerabilities at zero Critical/High.

**Testing**
- Unit tests for business logic, not just coverage padding.
- Integration tests for critical paths.
- Edge cases tested (empty, null, max size, concurrent, malformed).
- Error paths tested, not just happy path.
- Tests are fast (< 10s for unit suite typical).
- Tests are isolated — no shared mutable state, no external-network dependency.

**Documentation**
- Comments explain "why", not "what".
- Public APIs have schema + examples.
- README updated if user-visible behavior changed.
- Breaking changes have migration guide.

**Observability**
- Logs at right level (INFO for business events, WARN for recoverable, ERROR for alertable).
- Structured logs (JSON) with correlation IDs.
- Metrics for new operations (latency, error rate, throughput).
- No excessive logging (cost + noise).

### Decision tree

- No Critical or High issues → **APPROVED - MERGE AUTHORIZED**.
- Only Low issues, or Medium with tracked follow-up ticket → **APPROVED WITH MINOR CHANGES** (merge after fix, no re-review).
- Any Critical, or >2 High, or deviation from approved design with architectural impact → **CHANGES REQUESTED** (re-review required).
- Implementation fundamentally doesn't match approved design → **REJECTED — back to Checkpoint 1**.

### Post-deployment verification

Within 24h of merge, confirm:
- Smoke tests pass in production.
- Metrics show expected rate/latency/error profile.
- No error-rate spike above baseline.
- SLO compliance maintained.

If any fail → engineer owns rollback decision; principal owns the "is the design still right" decision.

---

## Non-negotiables (auto-reject at either checkpoint)

- No threat model for a system handling user data or money.
- No rollback plan for any production-affecting change.
- No observability for any new service.
- Shared mutable database between services owned by different teams.
- Synchronous call chain >2 services deep.
- Secrets in source control, logs, or error responses.
- `catch (Exception)` / empty catch in business logic.
- Unbounded queues, loops, retries, or caches.
- "We'll add tests later" for money/auth/PII code paths.
