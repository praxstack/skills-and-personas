# Code Review Report — 38 New Skills

**Review lens:** senior-engineer code-review-expert pass (SOLID-for-skills, D1 knowledge delta, routing clarity, safety, overlap, reference completeness). Linter-class issues already cleared by `_audit/lint-report.json` (0 FAILs); this pass focuses on what a deterministic linter cannot see.

---

## Executive Summary

**Verdict: SHIP WITH FIXES** (do NOT hold; no safety-blocking issues, but 3 skills have broken reference links that will degrade runtime behavior the moment Claude tries to follow them).

- **Shippable today:** 35 of 38 skills. Strong D1 knowledge delta, clean Audience/Goal framing, disciplined anti-pattern sections.
- **Must fix before ship (HIGH):** 3 skills with missing reference files (`svg-logo-designer`, `transcript-pipeline`, `gabriel-petersson-topdown-mentor`).
- **Should fix before ship (MED):** frontend-skill cluster overlap; routing ambiguity between `backend-pe` / `backend-system-design-expert` / `backend-architecture-standards`; `idea-capturer` bloat.
- **Safety:** `mental-health-screening-companion` (renamed from `ai-therapist-mdd-adhd`) is well-designed. 988 crisis routing in description, first-run un-suppressible preamble, explicit non-clinician scoping, crisis-first decision rules. No other skill raises dual-use concerns.

D1 knowledge-delta scan: all 38 skills clear the "would this actually make Claude better" bar. No skills are pure filler/restatement.

---

## Top Issues Ranked by Severity

### HIGH — Must fix before ship

**H1. `svg-logo-designer/SKILL.md` references 3 non-existent files.**
The body mentions `references/design-system.md`, `references/svg-techniques.md`, and `references/discovery-questions.md` (lines 31, 103, 194, 334–336). The `references/` dir is empty. Claude will read the mandatory instruction, try to load the file, fail, and fall back to guessing. Either populate these refs (the source persona had the content) or inline-collapse the references section.

**H2. `transcript-pipeline/SKILL.md` references 7 non-existent files.**
Lines 57, 68, 79, 80, 96, 147, 157 reference `stage1-refine.md`, `stage2-synthesize.md`, `stage3-enhance.md`, `stage4-validate.md`, `tutorial-tech-bar-raiser.md`, `resource-enrichment-authenticated-flow.md`, `colab-notebook-explainer-pipeline.md`. Only `readme.md` and `usage-guide.md` actually exist. Stage references are LOAD-bearing for the pipeline flow — this skill will hang on missing reference instructions.

**H3. `gabriel-petersson-topdown-mentor/SKILL.md` references missing `connection-framework.md`.**
Line 208 calls out `references/connection-framework.md`. It does not exist. The other 6 refs do. Lowest-effort fix: remove the parenthetical reference or stub the file.

### MED — Should fix before ship

**M1. Frontend-skill cluster has 5 overlapping skills — routing ambiguity.**
`frontend-pe`, `frontend-uiux-designer`, `frontend-design-excellence`, `frontend-excellence-standards`, `ultrathink-frontend` all cover similar ground (design commitment, motion, accessibility, library discipline, anti-generic defaults). They serve legitimately different entry-points (super-mode loader, ultrathink trigger, constellation role, standalone), but their descriptions don't clearly disambiguate routing. **Recommended fix:** add "Not for:" clauses to each description pointing at the peer skill, so Claude can route uniquely. Example for `frontend-design-excellence`: "Not for: engineering-first UI tasks (use `ultrathink-frontend`) or super-mode orchestration (use `frontend-excellence-standards`)."

**M2. Backend-design overlap — 3 skills cover consistency/API/data-model decisions.**
`backend-pe` (orchestrator), `backend-system-design-expert` (role-expert), `backend-architecture-standards` (super-mode-loaded). All three have API-style selector tables, consistency-model tables, data-store selector tables. Same ambiguity as M1 and same fix — tighter "Not for" routing hints.

**M3. `idea-capturer/SKILL.md` is 471 lines (within budget but bloated with templates).**
Four full templates (~200 of the 471 lines) belong in `references/` files. The skill has no references/ directory content at all (empty dir on disk). Splitting `references/templates.md` would cut SKILL.md to ~270 lines and give the loader room to skip the templates when not needed.

**M4. `spec-creator/SKILL.md` description has no "Use when" clause.**
Only skill in the set missing this routing hint (desc_len=416). All others include "Use when…". Claude will under-route to this skill.

**M5. `mental-health-screening-companion` Audience line is stale.**
Line 16 still reads "therapeutic conversation practice, simulated intake experience, session-tracking scaffolding" — language from the pre-rename `ai-therapist-mdd-adhd` framing. Minor but matters for scope integrity post-rename; the skill is otherwise correctly scoped as a screening/journaling companion, not a therapist.

### LOW — Polish

**L1. `idea-capturer/SKILL.md` lines 400–417 use `❌` / `✓` glyphs inconsistently with the rest of the skill corpus.** The linter let them pass because they're single-char, not ASCII art, but they are stylistic residue from the source persona. Replace with "Avoid:" / "Prefer:" prose.

**L2. `baron-von-markup/SKILL.md` has emoji in tables (lines 72–75).** These are *demonstrating markdown emoji patterns* — content-appropriate. Keep; flag only for reviewer awareness.

**L3. Empty `references/` directories where none are needed:** `idea-capturer/references/`, `svg-logo-designer/references/` (will be populated in H1 fix), `frontend-pe/references/` has only `methodology.md`. If `references/` stays empty, delete the directory to avoid implying there's more to load.

**L4. `gabriel-petersson-topdown-mentor` uses `→` arrows inside code-fenced blocks (lines 28–30 etc.).** Inside code blocks this passes the ASCII-art policy, but if the skill-corpus policy is "no Unicode arrows anywhere," flag for cleanup.

---

## Per-Skill Verdicts (only skills scoring below B-equivalent)

| Skill | Grade | Issue |
|---|---|---|
| `svg-logo-designer` | C | 3 broken refs (H1). Body quality is otherwise solid. |
| `transcript-pipeline` | C | 7 broken refs (H2). Most critical load-bearing issue in the corpus. |
| `gabriel-petersson-topdown-mentor` | B− | One broken ref (H3); long at 305 lines but justified by 5-mode scope. |
| `idea-capturer` | B− | Bloat + glyph residue. Content is good; needs extraction. |
| `spec-creator` | B− | Missing "Use when" clause will cause under-routing. |

All 33 other skills: B or higher.

---

## Spot Check: References Exist

Verified files exist for `mental-health-screening-companion` (5/5), `ai-therapist-mdd-adhd` superseded → files now under `mental-health-screening-companion`, `obsidian-cli` (3/3), `concept-cartographer`, `baron-von-markup` (3/3), `techtutor` (6/6), `professor-alex-interview` (6/6), `constellation-team` (8/8), `principal-engineer` (3/3), `backend-system-design-expert` (5/5), `devops-sre-engineer` (4/4), `frontend-uiux-designer` (5/5), `product-manager` (5/5), `qa-security-engineer` (4/4). All reference paths validated across 38 skills — 11 broken paths across 3 skills; all others clean.

---

## Safety Review — `mental-health-screening-companion`

Passes every requested bar:

- **988 in description**: yes, with "jurisdiction-matched crisis resources when risk signals appear" (line 3).
- **Non-clinician scope explicit**: description opens with "NOT a therapist, NOT a clinician, NOT a replacement for professional care." Line 10–12 of body mandates an un-suppressible disclaimer preamble on first-session response.
- **C-SSRS triggered without optional consent** (lines 26, 34).
- **Scope guard against mania/psychosis/ED/withdrawal/abuse disclosure** (line 39-40 of body): "provide stabilization and firm referral."
- **International coverage** (references/crisis-protocol.md per batch-F report): UK Samaritans, Canada 9-8-8, Australia Lifeline, India iCall, findahelpline.com.

Remaining nit: line 16 "Audience" still uses old "therapeutic conversation practice / simulated intake" framing inconsistent with the post-rename "screening and journaling companion" positioning. Reframe for internal consistency (M5).

No other skill in the corpus raises dual-use, harm, or privacy concerns worth flagging.

---

## Persona Residue Scan

Deterministic scan of second-person directive patterns (`Your role is`, `Your job`, `Your mission`, `Act as a/an/the`, `You will be`, `Your task is to`, sentences starting with `You `): **zero hits** across all 38 SKILL.md bodies. Batches A–F successfully purged persona framing and replaced with `**Audience:** / **Goal:**` pattern.

---

## Specific Recommended Fixes

| ID | File | Lines | Fix |
|---|---|---|---|
| H1 | `svg-logo-designer/SKILL.md` | 31, 103, 194, 334–336 | Create `references/discovery-questions.md`, `svg-techniques.md`, `design-system.md` from source persona, OR remove reference calls and inline the minimum needed. |
| H2 | `transcript-pipeline/SKILL.md` | 57, 68, 79–80, 96, 147, 157 | Create 7 stage/tutorial/enrichment/colab reference files. Source material exists in pre-compression inventory. |
| H3 | `gabriel-petersson-topdown-mentor/SKILL.md` | 208 | Create `references/connection-framework.md` (the DSA↔System-Design / code-smell↔design-principle map) or drop the parenthetical. |
| M1 | all 5 frontend skills | frontmatter `description:` | Add `Not for: …` clauses that name the peer frontend skill so routing is deterministic. |
| M2 | `backend-pe`, `backend-system-design-expert`, `backend-architecture-standards` | frontmatter | Same fix as M1; each description should name the other two and say when to prefer them. |
| M3 | `idea-capturer/SKILL.md` | 137–320 | Move templates (Quick Capture, Developed Idea, Brainstorming, Synthesis, Project) into `references/templates.md`. Target SKILL.md < 250 lines. |
| M4 | `spec-creator/SKILL.md` | frontmatter | Add explicit `Use when: …` clause to description. |
| M5 | `mental-health-screening-companion/SKILL.md` | 16 | Rewrite Audience to "Users who want structured self-reflection, validated screener scoring for personal tracking, or psychoeducation…" — match the skill rename. |
| L1 | `idea-capturer/SKILL.md` | 400–417 | Replace `❌` / `✓` with "Avoid:" / "Prefer:" prose. |
| L3 | empty refs/ dirs | — | Delete `idea-capturer/references/`, `svg-logo-designer/references/` once H1 lands (or populate), and confirm `frontend-pe/references/` has content. |

---

## Batch-Level Observations

- **Batch A (backend-pe family, 8 skills):** consistent section skeleton across variants is a feature, not boilerplate — reads as coherent product. D1 estimates 14–22 all credible.
- **Batch B (blueprint/concept/constellation + misc, 10 skills):** biggest variance; `transcript-pipeline` and `svg-logo-designer` are the broken-refs skills. Batch recovered from subagent stalls; recovery artifacts show.
- **Batch C (SUPER-MODE split, 7 skills):** clean split but creates the M1/M2 overlap problem with Batch A/B peer skills. Addressable in frontmatter only.
- **Batch D (personas-as-skills, 6 skills):** `chronicle`, `techtutor`, `baron-von-markup`, `professor-alex-interview`, `lecture-alchemist`, `gabriel-petersson-topdown-mentor` — all well-distilled. Gabriel has one broken ref (H3).
- **Batch E1/E2 (6 heavy compressions):** 1285–2926 source lines compressed to 113–175 SKILL.md lines + references. Spot-check of `frontend-uiux-designer` and `product-manager` confirms the compression kept the expert trade-offs and dropped the filler. No overcompression found.
- **Batch F (1 safety-critical skill):** `mental-health-screening-companion` rename is the right call. Safety posture is appropriate for ship.

---

## Final Recommendation

Fix the 3 HIGH issues (≈30 min of work — create 11 reference files or remove dead reference calls). Apply M1/M2 "Not for" clauses (≈20 min). Ship. M3–M5 and L1–L4 can land as follow-up polish PRs without blocking release.

The corpus is in strong shape. Knowledge delta is real (not filler), persona residue is clean, safety-critical skill is well-designed. The fixable issues are concentrated in 3 skills.
