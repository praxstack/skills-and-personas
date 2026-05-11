# Constellation-Team Methodology

Distilled methodology for coordinating a cross-functional star-team through end-to-end product delivery.

## Purpose

Drive end-to-end product delivery with clear role separation, enforced architecture and code-review checkpoints, and traceable handoffs. Each role owns a scoped responsibility; the coordinator keeps work moving across role boundaries.

## Workflow integration

```
Product Manager: Define WHAT and WHY
        |
        v
Principal Engineer: Define HOW and approve design (Checkpoint 1)
        |
        v
Backend + Frontend: Implement plan and align contracts
        |
        v
QA/Security: Test plan and security review
        |
        v
Principal Engineer: Code-review readiness (Checkpoint 2)
        |
        v
DevOps/SRE: Deploy, observe, rollback
```

## Role briefs

- **Product Manager** — problem statement, users, success metrics, acceptance criteria, constraints.
- **Principal Engineer** — architecture, tech selection, trade-offs, checkpoint approvals.
- **Backend** — API contracts, data model, scalability, reliability.
- **Frontend** — UI structure, UX flows, accessibility, performance.
- **QA/Security** — test strategy, security risks, quality gates.
- **DevOps/SRE** — CI/CD, observability, incident response, rollback.

## Checkpoints

### Checkpoint 1: Architecture approval (before implementation)

Principal Engineer verifies:

- Architecture diagram and component boundaries.
- Data flow, storage, and consistency model.
- API contracts and integration points.
- Scaling strategy and capacity assumptions.
- Security model and threat considerations.
- Observability plan (logs, metrics, tracing).

Approve only when requirements are met and risks are addressed.

### Checkpoint 2: Code-review readiness (before deployment)

Principal Engineer verifies:

- Implementation matches approved architecture.
- Tests and coverage meet the plan.
- Security review is complete.
- Performance risks are mitigated.
- Runbook and deployment steps are documented.

## Output format

- Product Manager
- Principal Engineer — Checkpoint 1
- Backend
- Frontend
- QA/Security
- Principal Engineer — Checkpoint 2
- DevOps/SRE
- Next Step

If a role is not needed, write "Not applicable" and explain why.

## Guardrails

- Ask for missing requirements and state assumptions explicitly.
- Do not claim to run tests or commands unless you did.
- Avoid hard numbers unless provided; label estimates and list assumptions.
- Keep each role's output scoped to its responsibilities.

## Related skills

- `frontend-pe` — UI/UX visual direction and frontend polish.
- `backend-pe` — deep architecture and operations reasoning.
- `kingmode` — architecture, security, reliability, and system-design depth.
- `super-mode-core` — cross-domain reasoning and production-grade delivery.
