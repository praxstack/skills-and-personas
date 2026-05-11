# Architecture Review Process — Output Templates

**When to load this file:** Load when producing a written review response (architecture design review, code review, or technology-decision document). Contains the structured output templates and the STRIDE threat-modeling checklist.

---

## Architecture Review Response Template

```markdown
## Architecture Review: [Feature/Component Name]

**Reviewer:** [name]
**Date:** YYYY-MM-DD
**Verdict:** APPROVED | APPROVED WITH CONDITIONS | NEEDS REVISION | REJECTED

### Summary
[1-2 paragraphs: what the design does, headline decision, key rationale.]

### Per-dimension evaluation

| Dimension | Score | Key finding |
|---|---|---|
| Functional correctness | Excellent/Adequate/Needs Work | ... |
| Scalability | ... | ... |
| Performance | ... | ... |
| Security | ... | ... |
| Reliability | ... | ... |
| Maintainability | ... | ... |
| System integration | ... | ... |
| Cost | ... | ... |

### Required changes

**Critical (must fix):**
1. [issue] — [why] — [suggested direction]

**Important (should fix):**
1. ...

**Suggestions (optional):**
1. ...

### Conditions for approval (if APPROVED WITH CONDITIONS)
- [ ] Condition 1 — verifiable at PR time.
- [ ] Condition 2 — verifiable at PR time.

### Next steps
- For engineer: [action items]
- For reviewer: [follow-up items, if any]

### References
- Linked ADRs, design patterns, prior decisions.
```

---

## Code Review Response Template

```markdown
## Code Review: [PR title or #num]

**Reviewer:** [name]
**Date:** YYYY-MM-DD
**Verdict:** APPROVED | APPROVED WITH MINOR CHANGES | CHANGES REQUESTED | REJECTED

### Summary
[1-2 paragraphs.]

### Checklist

- [ ] Architecture adherence
- [ ] Code quality
- [ ] Performance
- [ ] Security
- [ ] Testing
- [ ] Documentation
- [ ] Observability

### Blocking issues

**[Issue title]**
- Severity: Critical
- Location: `path/file.ts:123-130`
- Problem: [why this is wrong]
- Suggested fix: [concrete replacement]
- Reasoning: [why fix is better]

### Non-blocking feedback
- ...

### Positive notes (optional, short)
- [a pattern worth reinforcing in the team]

### Approval conditions (if APPROVED WITH MINOR CHANGES)
- [ ] Fix N
- [ ] Fix N
Once addressed, merge is authorized without re-review.
```

---

## Technology Decision Document Template

```markdown
## Technology Decision: [Name]

**Author:** [name]
**Date:** YYYY-MM-DD
**Decision:** APPROVED | REJECTED | NEEDS MORE RESEARCH

### Context
- Problem statement.
- Current state.
- Proposed technology.

### Evaluation (1-10 each)

| Dimension | Score | Notes |
|---|---|---|
| Technical fit | | |
| Team expertise | | |
| Ecosystem maturity | | |
| Operational complexity | | |
| Cost | | |
| Risk | | |

**Weighted total:** ___ / 100

### Decision rationale
[Why this verdict.]

### Alternatives considered
1. [Alt 1] — pros/cons, why not chosen.
2. [Alt 2] — pros/cons.

### Trade-offs accepted
- [Trade-off] — [why acceptable]

### Rollout plan (if approved)
- Phase 1: PoC on non-critical path.
- Phase 2: Team enablement.
- Phase 3: Pilot project.
- Phase 4: Gradual adoption.

### Review cadence
- Re-evaluate on: [date, 6-12 mo out].
- Success criteria: [how we'll know this was right].
```

---

## STRIDE threat-modeling checklist (for Checkpoint 1 security dimension)

For every trust boundary, ask:

- **Spoofing** — how do we authenticate the actor? MFA for privileged? Key rotation?
- **Tampering** — data integrity at rest and in transit? Signed payloads? Immutable audit log?
- **Repudiation** — can a user deny an action? Audit trail with non-repudiation?
- **Information disclosure** — encryption at rest / in transit? PII masked in logs? Error messages leak internals?
- **Denial of service** — rate limiting? Resource quotas? Backpressure? Payload size limits?
- **Elevation of privilege** — least privilege enforced? Authorization checked at every resource? Horizontal + vertical privilege checks?

If any STRIDE category is "didn't consider", the threat model is incomplete.

---

## Architecture anti-patterns (flag for rejection)

- **God service** — one service with too many responsibilities; violates single responsibility.
- **Tight coupling** — direct dependencies between layers that should be isolated.
- **Premature optimization** — optimizing before measuring; adds complexity without proven need.
- **Over-engineering** — building for hypothetical future needs, unnecessary abstraction layers.
- **Under-engineering** — no thought for scale/security/reliability; "quick and dirty" without rigor.
- **Database as integration layer** — multiple services sharing tables; coupling at the schema level, nearly impossible to evolve.
- **Distributed monolith** — microservices with synchronous call chains; pay microservice cost without getting independence.
- **Ignoring CAP** — expecting strong consistency in a distributed system without considering partitions.
- **No error handling** — design assumes happy path; no graceful degradation.
- **Security as afterthought** — added late in development; threat model not considered at design time.
- **Shared mutable state without synchronization** — race conditions waiting to happen.
- **No idempotency** on retryable operations — duplicate effects under normal network conditions.

---

## Technical-debt classification

| Type | Definition | Repayment policy |
|---|---|---|
| Intentional | Accepted shortcut for time-to-market, documented in ADR with pay-off date | Pay off by documented date; block next feature in area if overdue |
| Unintentional | Discovered bad design or bit-rot | Triage by blast radius; prioritize in normal backlog |
| Bit-rot | Dependencies aging, patterns aging | Dedicated quarterly upgrade cycle |

Default allocation: 20% of sprint capacity to debt reduction. If skipped for >2 sprints, next sprint is 40%.
