---
tags: [review, council, apex, autonomous-mode]
date: 2026-05-12
conversations:
  stage1-drafts: 20260512-221927-decide--
verdict: SHIP with targeted fixes (applied)
status: APPLIED
---

# Council Review — apex-autonomous-mode + APEX-CORE.md

**3/3 convergence: SHIP with targeted fixes.** Stage 2+3 were truncated at 120s; Stage 1 drafts from all three members provided enough signal.

## Member verdicts

| Member | Model | Verdict | Key critique |
|---|---|---|---|
| A | Opus 4.7 | Ship with fixes | Replace action-count gates with observable gates; binary self-assessment |
| B | Sonnet 4.6 | Ship with fixes | Add scope challenge step; <7 escalation should go to Tier 2, not Tier 3/5 |
| C | Gemini 2.5 Pro | Ship as-is, note sentinel visibility | Binary rigor metrics over 0-2 scale; HTML comments can be swallowed |

## Unanimous themes

1. **Ship** — design is sound, scope calibration is the killer feature
2. **Observable gates, not action counts** — agents can't predict `<5 actions` at task receipt
3. **Binary self-assessment** — 0-10 or 0-2 invites rationalization; YES/NO is falsifiable
4. **Markdown over XML** — all three confirmed

## Applied fixes

- Section 3 (scope calibration): rewrote thresholds as observable gates (file count, interface change, new deps, security surface). Added explicit challenge step.
- Section 5 (self-assessment): collapsed 0-10 → binary YES/NO per dimension. Changed escalation from "Tier 3 Council OR Tier 5 AcknowledgedSkip" → "Tier 2 Reroute" (Sonnet's correction).
- Section 4 (Recon phase): added "Re-enter from Execute if a bad assumption surfaces mid-task" (Opus's Q4 gap).
- Section 11 (state-machine compat): added visible one-line banner for CLIs that swallow HTML comments (Gemini #2).
- scope-calibration.md: flipped the "never downgrade mid-task" rule to "downgrade is OK, just state it" (Opus's minor point).
- SKILL.md Step 7: aligned self-assessment language with APEX-CORE's binary gate + Tier 2 escalation.

## Dropped (intentional)

- Mandatory `state your classification` pre-execution sentence — covered by the challenge step instead.
- XML-vs-markdown A/B — all three models confirmed markdown is correct, skipped the test.
- External CLI-enforced scope validation — deferred; would defeat the "works without APEX infra" property.

## What could invalidate this ship

- Production telemetry showing scope mis-classification >10% of activations.
- Agents consistently rationalising binary NO → YES without Tier 2 attempt.
- HTML-sentinel invisibility affecting user audit in real consuming CLIs.

## Session artifacts

- `~/.council/sessions/20260512-221927-decide--/` — stage-1 drafts from Opus 4.7, Sonnet 4.6, Gemini.
- stage 2+3 truncated at 120s; 3/3 convergence on stage 1 was sufficient per council CLI skill doc.
