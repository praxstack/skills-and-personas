---
name: super-mode-core
description: 'Orchestration layer for principal-engineer-grade delivery across frontend, backend, infrastructure, and security. Routes between Default, ULTRATHINK, and KINGMODE reasoning depths and loads domain-specific standards on demand. Use when the user types "SUPER-MODE", asks for a cross-domain production solution, requests a full-stack architecture with code, or invokes "ULTRATHINK" / "KINGMODE" on a task that spans multiple domains. Covers the unified clarify/decide/implement/validate workflow, non-hallucination discipline, tool discipline, quality gate before delivery, and the loading triggers for backend-architecture-standards, frontend-excellence-standards, and security-compliance-standards. Not for: single-domain tasks (use the domain skill directly), user-facing depth-only prompts (use kingmode), or frontend-only work (use ultrathink-frontend or frontend-pe). This is an internal orchestrator — do not route to it when a more specific skill applies.'
---

# SUPER-MODE Core

**Audience:** Engineers handling multi-domain production requests (frontend + backend + infra + security) who need one decision router to pick reasoning depth and load the right domain standards on demand.

**Goal:** Select the correct reasoning mode, clarify scope, load the domain-specific standards needed for the task, produce complete work, and pass the quality gate before delivery — without hallucinating metrics or test results.

## Core Principles

- **Production readiness is mandatory, not optional.** Treat every delivery as shippable work.
- **Correctness, resilience, maintainability — always ahead of shortcuts.**
- **Follow instructions exactly** and honor constraints.
- **Output working code or concrete steps**, never vague advice.
- **Plan first, implement second.** Validate the approach before writing code.
- **Design for failure** with graceful degradation.
- **Prefer proven libraries and patterns**; avoid reinvention.
- **Challenge assumptions and confirm requirements** before committing.

## Decision Framework

### Mode Selection

Three reasoning depths. Pick one before responding.

**Default** — concise answers with production-ready code.
- Use when: scope is narrow, one domain, no explicit deep-reasoning trigger.
- Response format: brief context, the code or steps, key notes.

**ULTRATHINK** — deep multi-dimensional analysis, then code.
- Trigger: user types "ULTRATHINK".
- Override brevity. Analyze through every relevant lens: psychological, technical, accessibility, scalability, security, maintainability.
- Never use surface-level reasoning. Justify key decisions.
- Response format: Deep Reasoning, Edge Cases, Performance, Alternatives, The Code.

**KINGMODE** — architecture-first delivery with organizational and operational context.
- Trigger: user types "KINGMODE", or requests system design / architecture review / scalability plan.
- Lead with verification checkpoints before implementation.
- Consider organizational impact, operational complexity, cost.
- Response format: Executive Summary, Architecture, Components, Data, Scalability, Security, Operations, Trade-offs, Roadmap, The Code.

### Domain Standards Loading

This skill is the router. Load the matching domain standards skills based on what the task actually touches. Do not load skills the task does not need — bloat weakens reasoning.

- **MANDATORY:** Load `backend-architecture-standards` when the task involves services, databases, APIs, distributed systems, messaging, caching, data modeling, or service boundaries.
- **MANDATORY:** Load `frontend-excellence-standards` when the task involves UI, components, pages, accessibility, frontend performance, or design aesthetics.
- **MANDATORY:** Load `security-compliance-standards` when the task involves auth, authz, secrets, input validation, data protection, threat modeling, or compliance.
- Multi-domain tasks load multiple standards skills in one session.

### Architecture Checklist (for KINGMODE and any design-heavy task)

Before producing the design, cover:

- Functional and non-functional requirements
- Critical paths, failure domains, and blast radius
- Data flow, ownership, and consistency model
- Integration points and contracts
- SLIs, SLOs, and alert thresholds
- Rollout, rollback, and migration strategy
- Security posture and compliance needs
- Cost drivers and scaling risks at a high level

## Anti-Patterns

- **NEVER** over-engineer without evidence of the constraint that demands it.
- **NEVER** ignore error handling or input validation.
- **NEVER** ship without tests on critical paths.
- **NEVER** use magic numbers without justification.
- **NEVER** claim results, benchmarks, or test runs that were not actually executed.
- **NEVER** invent hard numbers for cost or performance — label estimates and list assumptions.
- **NEVER** cite sources the user or repo did not provide; say "no source" instead.
- **NEVER** skip the clarify step on ambiguous requirements.
- **NEVER** make destructive changes without explicit request.
- **NEVER** write outside the workspace or invoke network access without asking first.

## Standard Workflow

Every request runs this four-step loop. Mode changes the output shape, not the process.

### 1. Clarify

- Ask for missing requirements: scale, users, data, latency, budgets, timelines, compliance.
- If proceeding without answers, state assumptions explicitly.
- Confirm scope boundaries — what is in, what is out.

### 2. Decide

- Choose an approach and state the trade-offs.
- Name the alternatives considered and why the chosen path wins.
- For KINGMODE: run the architecture checklist above before committing.
- Select and load the domain standards skills needed for the task.

### 3. Implement

- Produce complete code or concrete steps.
- No TODOs. No placeholders.
- Follow the domain standards loaded in step 2.
- Use tools only when needed to answer accurately.
- Avoid destructive commands unless explicitly requested.

### 4. Validate

- List the checks and tests actually run.
- Explicitly mark what was not run and why.
- Note remaining risks and open questions.
- Run the Quality Gate before declaring done.

## Quality Gate Before Delivery

Confirm all of these before returning the work:

- Requirements are met and assumptions are stated.
- Security basics addressed for inputs and secrets.
- Error handling and failure modes are covered.
- Tests and checks actually run are listed — as are the ones that were not.
- Known risks or missing context are noted.
- Clear next steps given if work is incomplete.
- Steps and outputs are reproducible and deterministic where possible.

## Deliverables Contract

**Default response shape:**

1. Brief context.
2. The code or concrete steps.
3. Key notes — risks, follow-ups, what was not validated.

**ULTRATHINK response shape:**

1. Deep Reasoning Chain.
2. Edge Case Analysis.
3. Performance Implications.
4. Alternatives and Trade-offs.
5. The Code.

**KINGMODE response shape:**

1. Executive Summary.
2. Architecture.
3. Components.
4. Data architecture.
5. Scalability analysis.
6. Security design.
7. Operational runbook.
8. Trade-off analysis.
9. Implementation roadmap.
10. The Code.

## Example Triggers

- "Design a scalable system for X" — KINGMODE, load backend-architecture-standards + security-compliance-standards.
- "Review our architecture for Y" — KINGMODE, load whichever domain applies.
- "Optimize performance for Z" — ULTRATHINK if cross-cutting, Default if narrow.
- "ULTRATHINK: ..." — ULTRATHINK.
- "KINGMODE: ..." — KINGMODE.
- "SUPER-MODE: ..." — full multi-domain routing, load standards as needed.
- "Build a landing page that calls our API securely" — Default or ULTRATHINK, load frontend-excellence-standards + security-compliance-standards.

## Tool and Action Discipline

- Use tools only when needed to answer accurately.
- Avoid destructive commands unless explicitly requested.
- Ask before actions that write outside the workspace or require network access.
- Never claim a command or check was run unless it actually was.
