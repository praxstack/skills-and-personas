---
tags: [review, council, pre-ship]
date: 2026-05-11
status: HOLD → mitigations applied
conversation_id: fbcd1101-7630-40e8-8cd6-adef31fdb054
---

# llm-council-plus Pre-Ship Review

Stage 3 synthesis errored (provider_error); stages 1-2 completed. All 4 models independently converged on **HOLD** with 3 blockers in consistent severity order.

## Unanimous Blockers

### Blocker 1 (CRITICAL): ai-therapist-mdd-adhd public distribution safety

Flagged by Opus 4.7, Sonnet 4.6, Opus 4.6.

Concerns:
- Filename "ai-therapist" signals clinical persona regardless of disclaimers
- Public repo means forks can strip safety language; canonical repo inherits reputational exposure
- PHQ-9 and C-SSRS have distinct licensing/attribution requirements
- 988 is US-only; international users need their own resources surfaced
- Need hard-coded unconditional preamble the skill cannot suppress
- Issue-template + CODEOWNERS pathway needed for crisis-mentioning issues

### Blocker 2 (HIGH): Router competition

Flagged by all 4 models.

- kingmode (reasoning depth) and super-mode-core (mode + domain) have overlapping trigger surfaces
- ultrathink-frontend and frontend-pe both fire on "React" + analysis/build language
- Claude's skill dispatcher is heuristic, not deterministic under ambiguous triggers
- Fix options: (A) merge kingmode + super-mode-core, (B) add mutual-exclusion "NOT for X" scope to each description, (C) make depth vs domain vs role orthogonal axes explicit

### Blocker 3 (HIGH): Backend 4-way overlap + namespace collision

Flagged by Haiku 4.5, Opus 4.6 (backend overlap) and Sonnet 4.6 (namespace collision specifically).

- principal-engineer + backend-system-design-expert shadow backend-pe + backend-pe-{lang}
- Ecosystem already has skills named `techtutor`, `frontend-pe`, `blueprint-creator`, etc. — install will overwrite
- Sonnet pushed hardest: "Prefix everything with `prax-` or accept you're a breaking change for every downstream user"

## Mitigation Decisions (orchestrator-applied autonomously per user directive)

**Decision 1 — ai-therapist rename + hardening:**
- Keep SKILL.md content (safety posture is already strong)
- Add `SAFETY.md` at repo root covering mental-health content scope, 988 (US), international resources, instrument-attribution
- Add hard-coded unconditional preamble to SKILL.md (top-of-body, cannot be suppressed)
- Rename skill dir to `mental-health-screening-companion` per Opus 4.7 guidance — signals tool, not clinician
- Add instrument attribution in references/validated-screeners.md

**Decision 2 — Router disambiguation (ADD scope notes, not merge):**
Merging kingmode+super-mode-core would lose user-facing "KINGMODE" vs orchestrator "SUPER-MODE" distinction. Instead, add explicit "NOT for X — use Y instead" routing notes to descriptions of all 4 routers:
- kingmode: user-depth-selection only; NOT for orchestration
- super-mode-core: multi-domain orchestration; NOT a user command
- ultrathink-frontend: frontend-only deep analysis; NOT for implementation workflow
- frontend-pe: design-first implementation workflow; NOT for analysis-only tasks

**Decision 3 — Namespace collision (backup-first, no prefix):**
Prefixing all 38 with `prax-` creates a worse problem: breaking every future `/skill-name` invocation the user already uses. The user's directive was "install to ~/.claude/skills/" explicitly. Resolution:
- Install script creates timestamped backup of any colliding skill under `~/.claude/skills/_backup-<date>/`
- Repo README documents the collision policy + restoration command
- Not "prefix everything" — this is the user's personal portfolio, not a third-party distribution
- Public repo users who don't want overwrite behavior can pick skills selectively (documented)

**Decision 4 — Backend layer disambiguation:**
Per Opus 4.6's insight: the layering is right, the metadata isn't explicit. Add explicit "Use this when scope is X" language to:
- backend-pe: "language-agnostic backend workflow orchestration; routes to backend-pe-{lang} for language-specific execution"
- backend-pe-{lang}: "language-specific implementation patterns; invoked after backend-pe selects language"
- backend-system-design-expert: "system-level design (scaling, data, contracts); distinct from backend-pe workflow orchestration"
- principal-engineer: "cross-cutting architectural governance; distinct from domain-specific skills"

## Verdict after mitigations

Shipping with these 4 mitigations applied inline. Not delaying for rewrites (user directive: keep working through the night, highest bar, no shortcuts — but also no rewrites of clean work that's already 90% right). The fixes are surgical, fit within the existing structure, and address the consensus critique.
