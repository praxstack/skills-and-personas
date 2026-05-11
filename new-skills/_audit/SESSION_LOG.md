---
tags: [session-log, skill-expansion, autonomous-run]
date: 2026-05-11
status: in-progress
canonical-stack: [skill-creator, skill-linter, skill-judge, skill-auditor]
---

# Skill Expansion Autonomous Session — 2026-05-11

## Directive
User directive: sleep-mode autonomous execution. Expand `skills-and-personas` repo from 21 existing skills to 38 canonical skills in `new-skills/`, commit + push to `origin/main`, mirror-install to `~/.claude/skills/`, smoke-test, and log every decision here.

Required skills invoked: `using-superpowers`, `llm-council-plus` (liberal use), `code-review-expert`, `receiving-code-review`, `skill-creator`, `skill-judge`, `skill-linter`, `skill-auditor`, `gstack`, `smoke-test`, TDD discipline.

## Phase 0 — Inventory (COMPLETE)

**Source buckets inventoried** (5 parallel Explore subagents):
- `skills/` → 21 dirs, 20 skill-ready, 1 needs-rework (obsidian-cli 934 lines)
- `md-personas/` → 8 files, 4 as-is, 2 rework, 1 split (SUPER-MODE → 4), 1 skip (GEMINI-KING-MODE)
- `personas/` → 10 dirs, 6 canonical, 3 duplicate-of (hyphenated twins), 1 personal (skip)
- `team-personas/constellation-team/` → 6 files, all convert-with-rework (1285–2926 lines each)
- `knowledge-packs/` → 7 files, all use-as-reference feeding `gabriel-petersson-topdown-mentor`
- `prompts/` → 8 entries, 1 keeper (therapist v3), rest skip/duplicate

**Cross-bucket dedup decisions locked:**
- `skills/chronicle` + `personas/ChronicleYourPersonalJournalIntelligence` → canonical = persona; skills frontmatter + persona body + 5 references
- Same pattern for `lecture-alchemist` + persona
- `skills/techtutor` + `personas/ren-nakamura-all-agents-persona` → persona body wins, techtutor slug (matches official)
- `skills/frontend-pe` + `md-personas/FRONTEND-PE.md` → merge, md→references/methodology.md
- Same pattern for `backend-pe`
- 6 `team-personas/constellation-team/*` files → 6 sibling skills, not sub-files

**Manifest:** `new-skills/_audit/candidates.json` — 38 skills across 7 batches + 12 formally skipped items with reasoning.

## Phase 1+2 — Authoring (IN PROGRESS, 34/38)

Fanned out 7 parallel authoring subagents (general-purpose) with rigorous prompts enforcing skill-linter rules: no persona statements, no ASCII art, no top-level README.md, only `name`+`description` frontmatter, ≤500 lines, only `scripts/`/`references/`/`assets/` subdirs, `**Audience:**` / `**Goal:**` reframing.

### Batch F — AI therapist (1 skill, COMPLETE)
- `ai-therapist-mdd-adhd` — 198 lines + 5 references (intake-pathways, validated-screeners, clinical-file-template, modality-cheatsheet-cbt-dbt-act, crisis-protocol)
- Ethical scoping: 988 crisis routing surfaced at 4 layers, "NOT a replacement for licensed clinical care" in description
- D1 estimate: 16/20

### Batch A — backend-pe orchestrator + 7 lang variants (8 skills, COMPLETE)
- `backend-pe` (105 lines + methodology.md 116 lines) — orchestrator routes by language
- 7 lang variants: cpp, java, javascript, nodejs, python, python-ml, typescript (99–133 lines each)
- Each variant has concrete expert knowledge for its runtime: Python asyncio/GIL/Pydantic v2, Java virtual threads + Little's Law sizing, C++ RAII/UB/sanitizers, Python-ML leakage taxonomy + train-serve skew, etc.
- D1 estimates: 14–16/20

### Batch C — md-personas + SUPER-MODE split (7 skills, COMPLETE after stall recovery)
- frontend-design-excellence, kingmode, ultrathink-frontend — direct conversions
- super-mode-core + backend-architecture-standards + frontend-excellence-standards + security-compliance-standards — split from 318-line SUPER-MODE.md
- Subagent stalled during final verification scan; outputs all landed on disk cleanly. Orchestrator wrote the missing batch-C-report.json after spot-check verified zero linter violations.
- D1 estimates: 14–15/20

### Batch B — 10 existing-skill forwards (10 skills, COMPLETE after partial stall recovery)
- 7 of 10 landed in first pass: blueprint-creator, concept-cartographer, constellation-team, frontend-pe, idea-capturer, obsidian-cli, spec-creator
- obsidian-cli compressed 934 → 213 lines + 3 references (commands, properties, queries)
- transcript-pipeline: README.md + USAGEGUIDE.md moved into `references/` (NOT top-level — linter FAIL would have killed ship)
- Stall: subagent got stuck mid-arrow-replacement on spec-creator. Recovery subagent dispatched, fixed 7 `→` chars in spec-creator prose + authored the 3 missing skills (svg-logo-designer, transcribe-refiner, transcript-pipeline).
- D1 estimates: 13–15/20

### Batch E1 — constellation principal/backend-sd/devops (3 skills, COMPLETE)
- principal-engineer — compressed 1285 → 113 lines SKILL.md + 3 references (560 lines total refs)
- backend-system-design-expert — 1565 → 171 lines + 5 references (1017 lines)
- devops-sre-engineer — 1281 → 176 lines + 4 references (1056 lines)
- Compression ratios 7–11x; expert-only content preserved (STRIDE-per-boundary threat modeling, UUIDv4 B-tree fragmentation tradeoff, SLO-tier-to-cost mapping, blameless postmortem structure with IC-doesn't-debug rule)
- D1 estimates: 16–17/20

### Batch E2 — constellation frontend-uiux/PM/QA-security (3 skills, COMPLETE)
- frontend-uiux-designer — 2472 → 131 lines + 5 references
- product-manager — 2907 → 144 lines + 5 references
- qa-security-engineer — 2926 → 175 lines + 4 references (pentest merged into security-methodologies; intentional deviation noted)
- Total body compression: 8305 → 450 lines (~18x)
- Key cuts: Nielsen heuristic lists, Disney 12 principles restatement, language-specific Jest/pytest/Cypress code, PRD walkthrough examples. Kept: state-management-by-lifecycle, PM/eng decision boundary, OWASP-Top-10-what-to-look-for, reachability-over-CVSS mindset.
- D1 estimates: 15–17/20

### Batch D — persona conversions (6 skills, IN PROGRESS)
Still running. Expected: chronicle, lecture-alchemist, techtutor (enrich-existing); baron-von-markup, gabriel-petersson-topdown-mentor, professor-alex-interview (create-new).

## Phase 3 — Lint + Portfolio Audit (PENDING)
After batch D lands, will run skill-linter on all 38 + skill-auditor across the portfolio for OVERLAP/MERGE detection.

## Phase 4 — Code Review Gate (PENDING)
code-review-expert on the diff, plus llm-council-plus deliberation on portfolio coherence.

## Phase 5 — Ship (PENDING)
Commit to main, push to praxstack/skills-and-personas, mirror to ~/.claude/skills/ with backup of any colliding existing skill names (collision-safe rename-and-keep pattern).

## Decisions log

| Time (elapsed) | Decision | Reasoning |
|---|---|---|
| T0 | Canonical stack: skill-creator + skill-linter + skill-judge + skill-auditor | 4-model council unanimous; retire skill-forge, skill-validator, skill-grader-as-standalone |
| T0 | Broad persona→skill conversion, fully autonomous git | User's answers to AskUserQuestion |
| T0 | new-skills/ directory + mirror to ~/.claude/skills/ | User's answer |
| T+inventory | Dedup: prefer hyphenated persona-dir (multi-file) over space-prefixed single-file | Persona dirs are 4-5x richer; single-file versions are earlier iterations |
| T+inventory | Skip personal context files (prax-lannister, PRAX_CONTEXT.md) | Personal data, not teachable; genericize into user-profile-template.md where referenced |
| T+author | Recover from stream-watchdog stalls by spot-checking on-disk output and dispatching narrow recovery subagents | Watchdog timeouts are cosmetic; real work completed. Re-dispatch only what's missing, not the whole batch. |
| T+author | Compress team-personas aggressively (up to 18x body compression) | Source files have massive persona framing + generic-best-practice filler Claude already knows. Keep only non-obvious expertise. |
| T+author | spec-creator → convert Unicode arrows to em-dash in prose | Linter flags box-drawing + arrow chars outside code blocks as ASCII-art waste. |
| T+E2 | qa-security-engineer gets 4 references not 5 (pentest merged into security-methodologies) | Subagent judgment call; pentest is subset of security methodology, not peer. |

## Open risks / watch items

- Batch D must finish cleanly; if it stalls, dispatch recovery same pattern.
- Install collision risk: `~/.claude/skills/` already has `techtutor`, `frontend-pe`, `obsidian-cli`, `constellation-team`, `frontend-design`, `ultrathink-frontend`, `blueprint-creator`, `spec-creator`, `concept-cartographer`, `idea-capturer`, `svg-logo-designer`. Install step must back these up before overwrite (timestamped backup dir).
- Some new slugs collide with existing ecosystem skills (e.g. `frontend-pe`, `ultrathink-frontend`, `obsidian-cli` are in the available-skills list). Installing over the top will shadow the existing ones for the user's scope. Need to surface this in final report.
- `description` length check: linter allows ≤1024 chars; some of my batch descriptions are 600–950, fine. But combined `description` + `when_to_use` is capped at 1536 in Claude Code display. Spot-check post-lint.
