---
name: constellation-team
description: 'Coordinate a cross-functional star-team workflow (Product Manager, Principal Engineer, Backend, Frontend, QA/Security, DevOps) with mandatory architecture and code-review checkpoints. Use when a request needs end-to-end product delivery, multi-role collaboration, or explicit role-based outputs, or when the user asks for "star team", "cross-functional", "full lifecycle", "multi-role" planning, or product delivery spanning PM + architecture + backend + frontend + QA + DevOps.'
---

# Constellation Team

**Audience:** Agents coordinating multi-role product delivery.
**Goal:** Drive a cross-functional workflow through Product Manager, Principal Engineer, Backend, Frontend, QA/Security, and DevOps roles with enforced architecture and code-review checkpoints.

Read `references/methodology.md` for the underlying methodology (roles, checkpoints, guardrails). Read the per-role references on demand.

## Operating principles

- Act as a coordinator and keep each role scoped to its responsibilities.
- Enforce the two checkpoints: architecture approval before implementation, and code review before deployment.
- Separate outputs by role; keep them actionable and complete.
- Ask for missing requirements and state assumptions explicitly.
- Do not claim to have run tests or commands unless you did.
- Avoid hard numbers unless provided; label estimates and list assumptions.

## Workflow

1. **Product Manager** — define the WHAT and WHY (problem, users, success metrics, acceptance criteria).
2. **Principal Engineer** — define the HOW (architecture, tech selection, trade-offs) and approve design (**Checkpoint 1**).
3. **Backend and Frontend** — outline implementation plans, API contracts, data flow, UI/UX approach.
4. **QA/Security** — define test strategy, security review, quality gates.
5. **Principal Engineer** — verify code-review readiness and approve for release (**Checkpoint 2**).
6. **DevOps/SRE** — define deployment, observability, and rollback plan.

## Output format

Produce sections in this order. If a role is not needed, write "Not applicable" and explain why.

- Product Manager
- Principal Engineer — Checkpoint 1
- Backend
- Frontend
- QA/Security
- Principal Engineer — Checkpoint 2
- DevOps/SRE
- Next Step

## Role references

Load per-role detail on demand. Do not preload all references.

- `references/methodology.md` — distilled methodology overview.
- `references/product-manager.md` — PM role brief, outputs, templates.
- `references/principal-engineer.md` — architecture + code-review checkpoints.
- `references/backend-system-design.md` — API contracts, data model, reliability.
- `references/frontend-uiux.md` — UI structure, UX flows, accessibility, performance.
- `references/qa-security.md` — test strategy, security risks, quality gates.
- `references/devops-sre.md` — CI/CD, observability, incident response, rollback.
- `references/related-skills.md` — related skills and when to invoke them.

## Anti-Patterns

- **NEVER** skip Checkpoint 1 because the PM said the spec is urgent — uncaught architecture issues compound into rewrites that cost 10x the checkpoint time.
- **NEVER** let a single role draft the PRD without product + engineering alignment at the end — specs written in isolation fail validation in Checkpoint 1 and force a rewind.
- **NEVER** merge cross-role work without the QA/Security role touching it, even for "trivial" changes. "Trivial" changes are where the bypassed control decays.
- **NEVER** accept a design from the frontend-uiux-designer role without verifying accessibility considerations — post-hoc a11y retrofits are 5–10x harder than designing with contrast, focus, and semantics from the start.
- **NEVER** pull in the DevOps/SRE role only at deployment — infrastructure constraints (cold-start budgets, egress cost, region pinning) must shape architecture in Checkpoint 1, not surface as a blocker at the end.
- **NEVER** run two roles' outputs in parallel when the later role depends on the earlier role's decisions — parallelism here creates rework, not speed.

## Choosing the right frontend peer skill

Within this constellation workflow, three frontend-adjacent skills are distinct. Pick one — do not combine.

| Skill | Invoke when | Role in the constellation |
|---|---|---|
| `frontend-uiux-designer` | Cross-functional delivery needs UX flows, UI structure, a11y, and visual direction together | Default for the Frontend role in this workflow |
| `frontend-pe` | Greenfield, design-led product where aesthetic direction is load-bearing | Replaces the Frontend role when the brand/design bar is the primary constraint |
| `ultrathink-frontend` | Deep, multi-pass analysis of a specific frontend surface | Invoked *inside* the Frontend role for a particular decision, not as a replacement |
| `frontend-design-excellence` | Pure taste / design-commitment review pass | Invoked *after* the Frontend role's output as a polish critique |

## Related skills

- Use `backend-pe` for deep backend architecture and operations reasoning.
- If the user invokes ULTRATHINK or SUPERMODE protocols, apply them within the relevant role sections.
