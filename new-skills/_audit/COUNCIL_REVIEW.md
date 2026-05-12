---
tags: [review, council, ratification]
date: 2026-05-11 / 2026-05-12
status: V1 MITIGATIONS APPLIED → V2 PARTIAL SHIP APPLIED → FINAL CONDITIONAL APPROVE
conversations:
  v1-pre-ship: fbcd1101-7630-40e8-8cd6-adef31fdb054
  v2-re-adjudication: 20e0676d-87bd-4825-a327-689d74176a7a
  final-ship-ratification: 48519d09-9c43-4964-906d-63d66ce32657
---

# llm-council-plus Review History — Canonical Record

This file is the durable repo artifact for every llm-council-plus deliberation that gated a ship decision. Conversation IDs remain as provenance metadata; the verdict text, the conditions, the commits that satisfied them, and the post-fix verification live here in the repo so a third-party reader can reconstruct every decision without access to the council backend.

## V1 — Pre-Ship Review (2026-05-11, conv fbcd1101)

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

### V1 commits that satisfied the mitigations

| Mitigation | Commit | Description |
|---|---|---|
| Decision 1 (ai-therapist rename + hardening) | `1379055` + `23ef218` | Rename to `mental-health-screening-companion`, hardcoded preamble, repo-root SAFETY.md, instrument attribution |
| Decision 2 (router "Not for X" clauses) | `1379055` | `super-mode-core`, `ultrathink-frontend`, `frontend-pe` descriptions gained peer-pointer clauses; `kingmode` already had scoping |
| Decision 3 (collision-safe install, no prefix) | `1379055` | `_audit/install.sh` backup-then-install pattern, 38 colliding skills backed up to `~/.claude/skills/_backup-<timestamp>/` |
| Decision 4 (backend layer disambiguation) | verified already present in the 38-skill manifest | `backend-pe`, `backend-pe-{lang}`, `backend-system-design-expert`, `principal-engineer` descriptions already carried the scope language from authoring |

---

## V2 — Re-Adjudication (2026-05-12, conv 20e0676d)

**Trigger:** post-ship skill-judge + skill-auditor reviews contested the V1 decision to keep all 5 frontend skills. Two independent reviews said the portfolio had real content duplication the "Not for X" clauses didn't fix. Council reconvened.

**Verdict:** PARTIAL SHIP — "moderate fix tonight, defer aggressive collapse to user awake."

### Three contested decisions + council resolution

| Contested decision | Council call |
|---|---|
| A. Frontend 5→2 or 5→3 collapse | **MODERATE** — extract shared rules to canonical reference, keep 5 skills for now. Aggressive collapse is an architectural decision that requires user ratification. |
| B. Merge kingmode + super-mode-core | **MODERATE** — don't merge. Strip mode-routing from super-mode-core (make it a pure internal loader); kingmode becomes sole mode-selection authority. |
| C. Retire backend-architecture-standards + backend-system-design-expert into backend-pe/references/ | **HOLD** — user previously pushed back with substantive reasoning; re-litigating overnight would violate the directive, not honor it. |

### V2 commits that satisfied the council

| Council call | Commit | Description |
|---|---|---|
| A (moderate) | `a1da1c4` | Created `frontend-pe/references/design-rules.md` as canonical source; 5 frontend skills delegate to it |
| A (deferred) | `a1da1c4` | Wrote `_audit/FRONTEND_CONSOLIDATION_MEMO.md` for user adjudication with options A/B/C + recommendation |
| B (moderate) | `a1da1c4` | `super-mode-core` rewritten as pure internal domain-standards loader; "Relationship to kingmode" section makes scope separation explicit; arrows fixed in `4cc4d1a` |
| C (hold) | no commit — deferred | User push-back respected; memo documents the option if user wants to revisit |

Also in V2: Phase 7b judge-rubric fixes on 7 skills (idea-capturer D→B+, -516 lines net across the 7), C-SSRS license hardening (Phase 11), TDD suite (39 tests, Phase 9), internal broken-link scanner (Phase 10), README rewrite (Phase 12).

---

## Final Ship Ratification (2026-05-12, conv 48519d09)

**Request:** strict-loop ship approval on the complete v2 state after all prior reviews resolved.

**Verdict:** `CONDITIONAL APPROVE — apply C1 and C2 in the final commit, then ship.`

### Two conditions the council imposed

**C1 — Session log must record this adjudication as an event, not a foregone conclusion.** SESSION_LOG.md's terminal phase must contain:
- This conversation's ID (48519d09)
- The literal verdict string (`CONDITIONAL APPROVE`)
- The two conditions, verbatim
- Explicit note that the final commit is the artifact satisfying them
- The post-fix gate re-run results (even if identical — the point is legible timestamp ordering)

Rationale: "Without this, a future reviewer sees 'council approved' with no visible evidence that the strict-loop gate actually gated anything, which defeats the purpose of the loop."

**C2 — Persist council verdicts as repo artifacts, not conversation references.** COUNCIL_REVIEW.md (this file) becomes the canonical record for V1, V2, and final-ratification verdicts, with conversation IDs retained only as provenance metadata. Each verdict gets the verdict text, the conditions, and the commit SHAs that satisfied them.

Rationale: "A third party reading the repo alone cannot reconstruct *what* the mitigations were or *why* HOLD flipped to SHIP without access to the conversation backend."

### Meta-caveat the council raised (worth preserving on record)

> "I am reviewing your *description* of the portfolio, not the portfolio itself. I cannot independently verify commit SHAs, test counts, or file contents. This verdict is therefore advisory within your established autonomous-run framework. The final human-accountable decision is yours. If any claim in your summary is inaccurate, this ratification does not carry over to the actual state of the repo."

This caveat is preserved here so a future reader understands the council's ratification is bounded by the accuracy of the summary that was submitted to it. The deterministic tooling (lint, smoke, link scanner, pytest) is the ground-truth evidence that the summary matched reality.

### The single commit that satisfies C1 + C2

C1 and C2 both land in the same commit as the final `frontend-uiux-designer` residue fix from the code-review-expert v2 pass. Splitting C1/C2 into a follow-up commit would itself create an audit-trail seam where the "approved" SHA and the "fully documented" SHA diverge — the exact kind of break the strict-loop requirement is designed to prevent.

### Post-fix verification (required by C1)

Run after the frontend-uiux-designer residue fix:

- `python3 _audit/lint.py` → 38 skills, **0 FAILs, 0 WARNs**
- `bash _audit/install.sh` → 38 installed, 38 backed up to `~/.claude/skills/_backup-20260512-090635/`
- `python3 _audit/smoke_test.py` → **38 tested, 0 FAILs, 0 WARNs**
- `python3 _audit/check_links.py` → **38 skills, 134 files, 134 links, 0 broken**
- `pytest _audit/tests/ -q` → **39/39 passing in 0.46s**

All four quality gates remain green after the fix. No regressions introduced.

---

## Final status

Once the commit satisfying C1 + C2 lands on `origin/main`, the strict-loop ratification requirement is satisfied and the overnight autonomous run is complete.

Deferred-to-user decisions (frontend cluster collapse, backend language-agnostic collapse) are documented in `FRONTEND_CONSOLIDATION_MEMO.md` with specific adjudication options and a recommendation. These remain open for the user when awake.
