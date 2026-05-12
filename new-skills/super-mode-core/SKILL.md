---
name: super-mode-core
description: 'Internal loader for principal-engineer domain standards across backend, frontend, and security. Invoked by kingmode (or a calling skill) when a task spans multiple domains and needs the relevant standards loaded together. Does NOT make user-facing mode decisions — that is kingmode''s job. Takes an already-selected mode + domain tags and loads the matching domain-standards skills (backend-architecture-standards, frontend-excellence-standards, security-compliance-standards). Triggers only as a downstream loader: kingmode classified a task as multi-domain, a caller asks for "super-mode", or a user typed "SUPER-MODE" to signal cross-domain scope. Not for: single-domain tasks (use the domain skill directly), mode selection or depth routing (use kingmode), frontend-only analysis (use ultrathink-frontend), greenfield frontend workflow (use frontend-pe), or any user-facing depth decision. Pure loader — no mode routing, no user-facing output.'
---

# SUPER-MODE Core — Domain-Standards Loader

**Audience:** Other skills (primarily `kingmode`) that need multi-domain standards loaded for a cross-cutting task. Occasionally invoked directly by a user typing `SUPER-MODE` to signal cross-domain scope.

**Goal:** Detect which domains a task touches, load the matching domain-standards skills, and hand control back to the caller. This skill does NOT choose reasoning depth, does NOT run workflows, does NOT produce output — it's a loader and nothing else.

## Relationship to kingmode

The two skills used to overlap on mode routing. After the 2026-05-12 council re-adjudication (conversation `20e0676d-87bd-4825-a327-689d74176a7a`), that duplication is removed:

- **kingmode** is the sole source of mode selection (Default / ULTRATHINK / KINGMODE). User-facing depth decisions live there.
- **super-mode-core** (this skill) is a pure internal loader. It assumes a mode has already been chosen and loads the cross-cutting domain standards for the task.

If you (as a caller) need mode selection, invoke `kingmode` first, then super-mode-core. If you only need one domain, load that domain's standards skill directly — don't route through super-mode-core.

## Domain-Tag Detection Table

When invoked, classify the task by which domains it touches. Load the corresponding standards skills. Multi-domain tasks load multiple.

| Task touches | Load |
|---|---|
| Services, databases, APIs, distributed systems, messaging, caching, data modeling, service boundaries | **MANDATORY:** `backend-architecture-standards` |
| UI, components, pages, accessibility, frontend performance, design aesthetics, motion, typography, color | **MANDATORY:** `frontend-excellence-standards` |
| Authentication, authorization, secrets, input validation, data protection, threat modeling, encryption, compliance (GDPR/SOC2/PCI/HIPAA) | **MANDATORY:** `security-compliance-standards` |
| Language-specific backend implementation (Python asyncio, Java concurrency, C++ RAII, Node.js event loop, TypeScript types, Python-ML training) | Load the matching `backend-pe-{language}` skill in addition to the standards |
| Pure taste / aesthetic commitment (reject AI slop, bold aesthetic direction) | `frontend-design-excellence` |
| Cross-functional UI/UX role (product + design + frontend together) | `frontend-uiux-designer` |
| Deep frontend analysis / review (ULTRATHINK mode applied to frontend) | `ultrathink-frontend` |

## Loader Rules

- **Load only what the task needs.** Loading irrelevant standards bloats context and weakens reasoning.
- **Load once per session.** If a standards skill is already in context, don't reload it.
- **Defer to the caller's mode.** Whatever mode kingmode chose (Default / ULTRATHINK / KINGMODE) remains authoritative. super-mode-core does not override it.
- **Return control after loading.** This skill does not produce final output — it hands back to the caller (kingmode, or the user directly if they typed SUPER-MODE).

## When to NOT route here

- User types "ULTRATHINK" or "KINGMODE" alone → that's mode selection; route to `kingmode`.
- Task is single-domain (e.g., "write a Python FastAPI endpoint") → load the domain skill directly (`backend-pe-python` in this case). Skipping super-mode-core saves a context load.
- Task is a narrow prototype or a one-file refactor → the domain skill is enough; no need for the standards layer.

## Anti-Patterns

- **NEVER** make user-facing mode decisions here. That's kingmode's job. If a caller hasn't picked a mode, route back to kingmode.
- **NEVER** load all three standards skills by default. Detect the domain and load only what applies.
- **NEVER** produce final user-facing output from this skill. It's a loader; the caller produces output.
- **NEVER** override the caller's selected mode. If the caller is in Default mode, don't escalate to KINGMODE because the task looks complex — that's the caller's call.
- **NEVER** duplicate mode-routing logic that belongs in kingmode. If you find yourself writing a Default/ULTRATHINK/KINGMODE decision tree here, that's the signal to delete it and delegate to kingmode.

## Deliverables Contract

When invoked, this skill's "output" is a loader report, not user-facing content:

```
Loaded for [task description]:
- backend-architecture-standards (because [domain tag])
- security-compliance-standards (because [domain tag])

Control returned to [caller: kingmode / user].
```

That's it. The actual response to the user comes from the caller skill using the loaded standards.

## Example invocations

- kingmode (in KINGMODE mode) classifies "design a payment processing system" as backend + security multi-domain → invokes super-mode-core → super-mode-core loads `backend-architecture-standards` + `security-compliance-standards` + `backend-pe-python` (or whichever language) → control returns to kingmode for the KINGMODE-shaped output.
- User types `SUPER-MODE: design a dashboard with secure auth` → super-mode-core classifies as frontend + backend + security multi-domain → loads all three standards → invokes kingmode (if the user implied depth) or lets the domain skills drive otherwise.
- User asks "write a Python FastAPI endpoint" → super-mode-core is NOT the right skill; route directly to `backend-pe-python`.
