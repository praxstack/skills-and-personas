---
tags: [decision-memo, awaiting-user-adjudication, frontend-cluster]
date: 2026-05-12
status: DEFERRED TO USER
prior-reviews: [council fbcd1101, judge 2026-05-12, auditor 2026-05-12, council re-adjudication 20e0676d]
---

# Frontend Cluster Consolidation — Decision Memo

## Why this is in front of you

Three post-ship reviews have now weighed in on the frontend cluster (5 skills). Two reviews (judge + auditor) think it has meaningful duplication. The council (twice) has been reluctant to autonomously collapse skill count. The second council run **explicitly deferred this call to you** because retiring skills is an architectural decision, not janitorial work.

You're the tiebreaker. The council has already authorized and applied the "moderate fix" (extract duplicated content to a canonical reference, keep 5 skills). This memo is about the bigger question: should the count drop from 5, and to what?

## The cluster today (post-moderate-fix)

| Skill | Lines | Purpose | Distinct from peers? |
|---|---|---|---|
| `frontend-pe` | ~90 | Design-led implementation workflow for greenfield UI (stack: Next.js/React 19/Tailwind/Framer Motion). Navigation pattern references/methodology.md. | Yes — workflow, not principles |
| `frontend-uiux-designer` | ~130 | Cross-functional role within constellation-team workflow; UI + UX design + accessibility + research. Has 5 references. | Yes — team-role axis, not taste axis |
| `frontend-design-excellence` | ~85 | Pure taste / aesthetic commitment — reject AI slop, bold direction. Mindset pattern. | Partial — overlaps with excellence-standards |
| `frontend-excellence-standards` | ~135 | Loaded by super-mode-core for frontend-heavy work. Standards checklist. | Partial — overlaps with design-excellence |
| `ultrathink-frontend` | ~170 | Two-mode (default + deep analysis). Library discipline + anti-generic aesthetic + full multi-dim lens. | Partial — duplicates mode-routing concern with kingmode AND design concerns with design-excellence |

## What the reviews said

**skill-judge (rubric D1-D8, /120):**
- frontend-pe: 97 (B)
- frontend-uiux-designer: 103 (B)
- frontend-design-excellence: 103 (B)
- frontend-excellence-standards: 97 (B)
- ultrathink-frontend: 95 (C)
- Diagnosis: "Four skills repeat banned-fonts / purple-gradient-on-white / UI-library-discipline / 'every element justified' content." Recommended: "consolidate to 2 maximum — one for design-commitment (Mindset pattern ~50 lines), one for cross-functional UI/UX role."

**skill-auditor (portfolio scan):**
- "The 'Not for X' clauses do NOT substantively disambiguate."
- "frontend-excellence-standards and frontend-design-excellence are ~95% duplicates."
- "ultrathink-frontend could be a mode flag inside frontend-pe."
- Recommendation: "Collapse 5 to 2." Potential savings ~300 lines.

**Council (re-adjudication, conv 20e0676d):**
- Rejected "5 to 2" as too aggressive
- Considered "5 to 3" via creating a `frontend-craft-standards` skill by merging design-excellence + excellence-standards + ultrathink-frontend. Technically defensible. Explicitly: "This is an architectural decision, not janitorial work." **Deferred to you.**
- Applied moderate fix (extract shared rules to canonical ref) autonomously.

## Three options (and my recommendation)

### Option A: Keep 5 — do nothing further

**Why it's reasonable:** The moderate fix already shipped — duplicated prose now points at a canonical reference instead of owning the content. The five skills serve genuinely distinct activation patterns (workflow, constellation role, taste, standards, depth-mode). Skill triggering is heuristic; having more specific skills improves routing precision even if their bodies overlap.

**Why it's not:** Two independent reviews called the duplication out after the "Not for" fix. The duplication exists at the *design* level, not just the content level — three of five skills exist primarily to say "be intentional about frontend design" in slightly different ways.

### Option B: Collapse to 3 (Council's 5-to-3 proposal)

**New structure:**
- `frontend-pe` (greenfield workflow) — unchanged
- `frontend-uiux-designer` (cross-functional role) — unchanged
- **NEW `frontend-craft-standards`** — absorbs design-excellence + excellence-standards + ultrathink-frontend. Covers: aesthetic commitment, library discipline, typography/color/motion, WCAG, performance, and ULTRATHINK deep-analysis mode as an internal switch.

**Why it's good:** Eliminates the ~95% duplicate-content finding. Keeps the two distinct axes that survived review (workflow, team-role). Creates one strong "frontend craft" skill that owns all the principal-engineer-grade standards in one place.

**Cost:**
- ~4-6 hours of careful authoring
- 3 skills retired, 1 new skill created (`frontend-craft-standards`)
- Users who already invoked `/ultrathink-frontend`, `/frontend-design-excellence`, `/frontend-excellence-standards` will need to adjust to `/frontend-craft-standards`
- Super-mode-core reference needs to retarget

**Risk:** The ULTRATHINK mode concept was a user-facing mental model (kingmode + ultrathink-frontend both expose it). Folding it into a "standards" skill loses the cognitive shorthand. Mitigation: keep the mode concept alive inside frontend-craft-standards as an internal switch.

### Option C: Collapse to 2 (judge's stronger recommendation)

**New structure:**
- `frontend-craft` (Mindset pattern, ~50 lines) — the distinctive-aesthetic discipline, reject AI slop, bold commitment
- `frontend-uiux-designer` — cross-functional role in constellation

And remove frontend-pe + excellence-standards + ultrathink-frontend entirely, folding their workflow + standards into the surviving two.

**Why it's good:** Most aggressive de-duplication. Two skills, two clear axes (taste + team-role).

**Cost:** Significant content authoring. Loses the Navigation-pattern `frontend-pe` (which the judge scored B+ on pattern fit). Loses ULTRATHINK mode entirely.

**Risk:** Over-corrects. frontend-pe is genuinely a workflow skill (opening step, stack opinion, motion strategy), not a "standards" skill. Collapsing it loses real signal.

## My recommendation

**Go with Option B (5 to 3).** It:
- Addresses both reviewers' duplication finding
- Preserves the two clearly distinct axes (workflow, constellation role)
- Creates a canonical home for frontend standards that `super-mode-core` can load cleanly
- Costs ~4-6 hours (not a rewrite; content already exists across 3 skills)
- Does not destroy genuinely useful skills (frontend-pe workflow, frontend-uiux-designer role)

If you disagree and want Option C (5 to 2), the additional 30-60 min of work is folding frontend-pe's workflow content into frontend-uiux-designer. Recoverable.

If you want Option A (keep 5), note that the moderate fix is already live; the cluster is 85% better than it was pre-review. You're just accepting that there are 5 frontend skills on purpose.

## What I need from you

One of: `[A: keep 5]` / `[B: collapse 5 to 3 with frontend-craft-standards]` / `[C: collapse 5 to 2 with frontend-craft]` / `[D: some other framing you want to propose]`.

Once you pick, the work is ~30 min (A), 4-6h (B), or 6-8h (C). All reversible via git.

## Supporting artifacts

- Full judge rubric: `_audit/judge-report.md` (deep analysis section for each frontend skill)
- Full auditor scan: `_audit/auditor-report.md` (cluster section)
- Council re-adjudication full text: conversation `20e0676d-87bd-4825-a327-689d74176a7a` in llm-council-plus
- Prior council (kept 5 with "Not for" clauses): conversation `fbcd1101-7630-40e8-8cd6-adef31fdb054`
