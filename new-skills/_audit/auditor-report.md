# skill-auditor Portfolio Scan — 38 Skills

**Run date:** 2026-05-12
**Scope:** `new-skills/` (project-local)

## Summary Table (sorted by line count desc)

| #  | Name                               | Lines | Desc chars | Refs | Status | Verdict     |
|----|------------------------------------|-------|------------|------|--------|-------------|
| 1  | svg-logo-designer                  | 343   | 842        | 3    | HEAVY  | TRIM        |
| 2  | gabriel-petersson-topdown-mentor   | 305   | 911        | 7    | HEAVY  | RESTRUCTURE |
| 3  | idea-capturer                      | 299   | 527        | 1    | OK     | OK          |
| 4  | concept-cartographer               | 246   | 576        | 0    | OK     | TRIM        |
| 5  | spec-creator                       | 237   | 805        | 4    | OK     | OK          |
| 6  | lecture-alchemist                  | 234   | 779        | 3    | OK     | MERGE (learning cluster) |
| 7  | obsidian-cli                       | 213   | 699        | 3    | OK     | OK          |
| 8  | transcript-pipeline                | 208   | 544        | 9    | OK     | OK          |
| 9  | mental-health-screening-companion  | 206   | 922        | 5    | OK     | OK          |
| 10 | blueprint-creator                  | 193   | 929        | 5    | OK     | OK          |
| 11 | professor-alex-interview           | 187   | 948        | 6    | OK     | OK          |
| 12 | transcribe-refiner                 | 184   | 673        | 0    | OK     | OK          |
| 13 | devops-sre-engineer                | 176   | 628        | 4    | OK     | OK          |
| 14 | qa-security-engineer               | 175   | 736        | 4    | OK     | OK          |
| 15 | techtutor                          | 174   | 822        | 6    | OK     | MERGE (learning cluster) |
| 16 | backend-system-design-expert       | 171   | 569        | 5    | OK     | MERGE → backend-pe or backend-architecture-standards |
| 17 | ultrathink-frontend                | 169   | 935        | 0    | OK     | MERGE → frontend-pe |
| 18 | super-mode-core                    | 168   | 963        | 0    | OK     | MERGE → kingmode |
| 19 | baron-von-markup                   | 164   | 815        | 3    | OK     | OK          |
| 20 | security-compliance-standards      | 151   | 729        | 0    | OK     | OK (internal ref of super-mode) |
| 21 | product-manager                    | 144   | 656        | 5    | OK     | OK          |
| 22 | backend-architecture-standards     | 141   | 693        | 0    | OK     | MERGE with backend-pe (pick one) |
| 23 | frontend-excellence-standards      | 133   | 882        | 0    | OK     | MERGE → frontend-design-excellence |
| 24 | backend-pe-python-ml               | 133   | 839        | 0    | OK     | OK          |
| 25 | frontend-uiux-designer             | 131   | 873        | 5    | OK     | MERGE → frontend-pe (or keep as constellation role) |
| 26 | backend-pe-cpp                     | 122   | 745        | 0    | OK     | OK          |
| 27 | chronicle                          | 119   | 706        | 5    | OK     | OK          |
| 28 | backend-pe-javascript              | 115   | 744        | 0    | OK     | OK (or merge into typescript with mode flag) |
| 29 | principal-engineer                 | 113   | 621        | 3    | OK     | OK          |
| 30 | backend-pe-nodejs                  | 113   | 826        | 0    | OK     | OK          |
| 31 | backend-pe-java                    | 110   | 654        | 0    | OK     | OK          |
| 32 | kingmode                           | 109   | 606        | 0    | OK     | OK          |
| 33 | backend-pe-typescript              | 108   | 704        | 0    | OK     | OK          |
| 34 | backend-pe                         | 105   | 838        | 1    | OK     | OK (keep as orchestrator) |
| 35 | backend-pe-python                  | 99    | 698        | 0    | OK     | OK          |
| 36 | frontend-pe                        | 88    | 845        | 1    | OK     | OK          |
| 37 | frontend-design-excellence         | 87    | 834        | 0    | OK     | MERGE target for frontend-excellence-standards |
| 38 | constellation-team                 | 61    | 480        | 8    | OK     | OK (router) |

## Totals

- **Total skills:** 38
- **Lines across SKILL.md:** 6,234
- **Lines across references/ (all *.md):** 17,818
- **Average SKILL.md lines:** 164
- **Status distribution:** OVER 0 / HEAVY 2 / OK 36
- **`allowed-tools` present:** 0 / 38 (every skill is implicitly granted full toolset)

Notable: no skill approaches the 500-line OVER threshold; the portfolio's bloat problem is **duplication across skills**, not verbosity within one skill. Total portfolio footprint ~24k lines including references.

---

## Deep review — skills flagged TRIM / RESTRUCTURE / MERGE

### TRIM

**svg-logo-designer (343 lines, HEAVY)**
- [CONCISENESS] Lines 8–13 restate the goal three times (audience, goal, core principle). ~5 lines savings.
- [CONCISENESS] Phase 1 discovery (lines 35–60) enumerates 15 questions inline AND references `references/discovery-questions.md`. Pick one location. ~15 lines savings.
- [CONCISENESS] Workflow overview (lines 15–25) is a 9-step numbered list that is then repeated as section headers. ~8 lines savings.
- **Suggested savings:** ~30 lines (9% reduction). Keep the skill; tighten the body.

**concept-cartographer (246 lines, 0 refs)**
- [CONCISENESS] Large inline Mermaid examples that Claude can generate from prompt alone. Move examples to `references/examples.md`.
- [STRUCTURE] 0 references files despite 246 lines — everything is inline. Either split or keep but trim.
- **Suggested savings:** ~60–80 lines by externalising example diagrams to a references file.

### RESTRUCTURE

**gabriel-petersson-topdown-mentor (305 lines, HEAVY)**
- [CONCISENESS] Lines 55–120 contain several extended inline ASCII traces (two-pointer, BFS, tree visualizations). Good pedagogy but ~40 lines could move to `references/visualization-examples.md` — the skill already has 7 reference files.
- [STRUCTURE] Description is 911 chars with deep detail about "5 response modes" and "CodeCrafters stage" — good triggers but overlaps heavily with techtutor's description. Needs either clear scoping or merge.
- [OVERLAP] See Learning cluster below.
- **Suggested savings:** ~40 lines.

### MERGE — see Overlap analysis section for rationale

- **frontend-excellence-standards** → merge into **frontend-design-excellence** (≈95% content overlap, same anti-patterns, same typography rules, same motion-budget rules).
- **ultrathink-frontend** → fold "ULTRATHINK mode" output format into **frontend-pe** as a mode flag.
- **super-mode-core** → merge into **kingmode** (both are 3-mode reasoning-depth routers with the same Default/ULTRATHINK/KINGMODE names).
- **backend-architecture-standards** + **backend-system-design-expert** → collapse into one "backend-architecture" reference OR into `backend-pe/references/architecture.md`. The three cover identical ground (API style, consistency, caching, messaging, reliability).
- **frontend-uiux-designer** → either merge into **frontend-pe** or retain ONLY as the constellation-team role doc (rename to `constellation-role-frontend` if so).
- **lecture-alchemist** ↔ **techtutor** → See learning cluster; lecture-alchemist is a pipeline, techtutor is a conversational tutor; keep both but trim description overlap.

---

## Overlap analysis (per cluster)

### Frontend cluster (5 skills)

**Skills:** frontend-pe, frontend-uiux-designer, frontend-design-excellence, frontend-excellence-standards, ultrathink-frontend

The recently-added "Not for X" clauses help at the margin but **the disambiguation fails** because the core content is 70–95% identical:

| Concern | frontend-pe | frontend-uiux-designer | frontend-design-excellence | frontend-excellence-standards | ultrathink-frontend |
|---|---|---|---|---|---|
| Ban Inter/Roboto/Arial | yes | yes | yes | yes | yes |
| "No purple gradient on white" | — | yes | yes | yes | — |
| Dominant + accent (60/30/10) | — | yes | yes | — | — |
| One hero motion moment | — | yes | yes | yes | — |
| UI library discipline | — | implicit | — | yes | yes (explicit) |
| CSS var palette | yes | yes | yes | yes | — |
| WCAG AA/AAA | — | yes | yes | yes | yes |
| Transform/opacity only | — | yes | yes | yes | — |

**frontend-design-excellence** and **frontend-excellence-standards** are near-duplicates. Same anti-patterns, same core principles, same workflow. The "internal reference loaded by super-mode-core" justification in frontend-excellence-standards is weak — super-mode-core can just point at frontend-design-excellence.

**frontend-pe** and **ultrathink-frontend** differ in framing (workflow vs. analysis modes) but the output specs (hero motion, library discipline, anti-generic) overlap heavily. ULTRATHINK mode could be a flag inside frontend-pe rather than a separate skill.

**frontend-uiux-designer** is positioned as the constellation-team role — that's a legitimate use case, but users invoking frontend work directly will get ambiguous routing between it and frontend-pe.

**Verdict:** collapse to **2 skills** — `frontend-pe` (workflow + aesthetics + ULTRATHINK mode merged in) and optionally `frontend-uiux-designer` retained strictly as the constellation role. ~300 lines saved.

### Backend cluster (10 skills)

**Skills:** backend-pe, backend-architecture-standards, backend-system-design-expert, backend-pe-{python,python-ml,typescript,javascript,nodejs,java,cpp}

Two failure modes here:

1. **Three skills ([backend-pe, backend-architecture-standards, backend-system-design-expert]) cover the same ground — language-agnostic backend architecture.** All three enumerate: API style selector (REST/GraphQL/gRPC), consistency model selector, data-store selector, caching strategy, messaging model, reliability patterns (timeout/retry/circuit-breaker), observability (RED/USE + SLO), anti-patterns (don't share DBs, don't retry without idempotency, etc.). backend-pe is the "orchestrator", backend-architecture-standards is the "internal ref for super-mode", backend-system-design-expert is the "decision-tree skill" — but a user asking to design a backend has no clear basis to pick among them, and the orchestrator doesn't route to the other two. **Consolidate to one** (backend-pe) and keep the decision tables / checkpoints / patterns inside references/.

2. **Seven language variants are actually valuable.** Each surfaces specific failure modes (blocking-in-async for Python, GIL, event-loop lag for Node runtime, UB/RAII for C++, virtual-threads/GC for Java, tsconfig strictness for TS) that a generic backend skill can't meaningfully capture. The variants are lean (99–133 lines each) and cite concrete library/tool defaults by version. **Keep the seven variants.** One possible future consolidation: `backend-pe-javascript` could fold into `backend-pe-typescript` with a "plain-JS mode" flag (low priority — current separation is cleaner).

**Verdict:** merge backend-architecture-standards + backend-system-design-expert into backend-pe (or into a single shared reference file). Keep the 7 language variants. ~250 lines saved.

### Learning cluster (4 skills)

**Skills:** techtutor, gabriel-petersson-topdown-mentor, lecture-alchemist, professor-alex-interview

Entry points differ on paper but converge in practice:

| Skill | Framing | Unique primitive |
|---|---|---|
| techtutor | 6-layer explanation (WHY/HOW/VISUALIZE/CODE/SCALE/CONNECT) | Layered explanation with optional check-ins |
| gabriel-petersson-topdown-mentor | 5-step recursive gap-filling loop + 5 response modes | Recursive drill-down until teach-back passes |
| lecture-alchemist | Transcript → structured notes pipeline | Zero-topic-loss transcript ingestion |
| professor-alex-interview | FAANG/HFT interview mentor with 5-level guided discovery | Solution-mode guardrails + quant/HFT content |

**techtutor vs. gabriel-petersson-topdown-mentor** is the real overlap. Both demand mandatory visualizations, both default to intuition before formalism, both target DSA/system-design for senior engineers. The differences (6-layer vs. 5-step loop) are stylistic. A user typing "explain how HashMap works" could route to either. Triggers overlap ("help me understand", "how does X work", "tutor me on", "drill into", "make this click").

**lecture-alchemist** is distinct — it's a transcript-ingestion pipeline, not a conversational tutor. Overlap with transcript-pipeline (separate skill in portfolio) should be audited later.

**professor-alex-interview** is distinct — specific to FAANG/HFT prep with anti-gaming safeguards and quant content.

**Verdict:** consider merging techtutor and gabriel-petersson-topdown-mentor into one mentor skill with two modes (layered-explanation mode vs. recursive-gap-filling mode). Keep lecture-alchemist and professor-alex-interview. ~200 lines saved if merged.

### Orchestrator cluster (3 skills)

**Skills:** kingmode, super-mode-core, constellation-team

| Skill | Role | Modes / routes | Overlap |
|---|---|---|---|
| kingmode | Reasoning-depth router | Default / ULTRATHINK / KINGMODE | Full overlap with super-mode-core |
| super-mode-core | Multi-domain + depth router, loads domain standards | Default / ULTRATHINK / KINGMODE + loads backend/frontend/security standards | Full overlap with kingmode on depth |
| constellation-team | Role-based delivery workflow | PM → PE → BE → FE → QA → DevOps | No overlap with the depth routers |

**kingmode and super-mode-core are near-duplicates** — same 3 modes with same names, same 4-step workflow (clarify/decide/implement/validate), same anti-hallucination rules, same output formats. Super-mode adds "load these domain standards" routing, which kingmode could absorb in 10 lines.

**constellation-team** is a different axis (multi-role orchestration) — genuinely complementary.

**Verdict:** merge kingmode into super-mode-core (or vice versa). Keep constellation-team. ~100 lines saved.

---

## Portfolio-level recommendations (priority order)

1. **Collapse frontend cluster from 5 → 2 skills.** Merge `frontend-excellence-standards` into `frontend-design-excellence` (near-duplicate). Merge `ultrathink-frontend` into `frontend-pe` as a mode flag. Retain `frontend-uiux-designer` only if the constellation-team integration is load-bearing; otherwise merge into `frontend-pe`. **Savings: ~300 lines + dramatic routing clarity.**

2. **Consolidate backend "architecture" skills (3 → 1).** `backend-architecture-standards` and `backend-system-design-expert` both cover language-agnostic backend architecture identical to what `backend-pe` already summarises. Fold both into `backend-pe/references/architecture-patterns.md` and retire the two standalone skills. **Savings: ~312 lines + a clear single entry point.**

3. **Merge kingmode into super-mode-core (or rename super-mode-core → kingmode).** Identical 3-mode router. **Savings: ~100 lines + zero confusion about which routes a design question.**

4. **Add `allowed-tools:` frontmatter to every skill.** Zero of 38 currently declare it. Most skills need only Read/Edit/Write/Bash/Glob/Grep. Declaring limits surface area, improves runtime enforcement, and is spec-required by the marketplace. **Effort: ~1 line per skill; no line savings but a quality upgrade.**

5. **Trim description fields that creep past 900 chars.** Descriptions over ~700 chars burn context on every invocation and rarely add routing value. Offenders: `professor-alex-interview` (948), `blueprint-creator` (929), `mental-health-screening-companion` (922), `gabriel-petersson-topdown-mentor` (911), `ultrathink-frontend` (935), `super-mode-core` (963). Target: ≤700 chars, focusing on trigger keywords + clear "not for X" disambiguation. **Savings: ~1,500 chars total across descriptions.**

6. **Audit learning cluster (techtutor ↔ gabriel-petersson-topdown-mentor) in a follow-up session with the user.** Merge candidates but this is a taste call; the user may prefer two distinct "voices" (layered explainer vs. Socratic driller). **Savings: ~200 lines IF merged.**

7. **Externalise inline examples in heavy skills.** `svg-logo-designer` (343), `gabriel-petersson-topdown-mentor` (305), `concept-cartographer` (246) carry long inline examples that belong in `references/`. **Savings: ~100 lines total.**

8. **Prune "internal reference" skills that shouldn't be user-invocable.** `backend-architecture-standards`, `frontend-excellence-standards`, and `security-compliance-standards` all say "Loaded by super-mode-core" / "Not for standalone user invocation" in their descriptions — yet they're installed as full skills that will trigger on user prompts. Either (a) move them to `super-mode-core/references/` and dereference, or (b) remove the "internal only" qualifiers and treat them as first-class skills. The current middle state is worst-of-both.

9. **Document a house frontmatter style.** Most descriptions begin with a role sentence then triggers then "Not for: ..." — but four skills (constellation-team, obsidian-cli, transcribe-refiner, idea-capturer) omit "Not for" disambiguation. Add a one-line checklist to new-skill templates.

10. **Consider retiring `concept-cartographer`.** Mermaid diagram generation is well within Claude's default capability — a 246-line skill describing how to generate common diagram types mostly restates what Claude already does. Keep only if the user has evidence the skill fires better routing than the base model.

---

## Top-5 lowest-impact skills (candidates for retirement or downgrade)

1. **frontend-excellence-standards** — ~95% duplicate of `frontend-design-excellence`; description itself says "Not for standalone user invocation." Retire or merge.
2. **backend-architecture-standards** — duplicates `backend-pe` and `backend-system-design-expert`. Retire or merge into backend-pe references.
3. **super-mode-core** — duplicates `kingmode`. Retire one.
4. **concept-cartographer** — 246 lines for Mermaid diagram guidance Claude can do natively; no references, no unique primitive. Retire or compress to <50 lines.
5. **backend-system-design-expert** — overlaps heavily with backend-pe + backend-architecture-standards. Retire or fold into backend-pe.

Collectively retiring/merging these 5 saves roughly **750–900 lines** of SKILL.md plus removes 5 routing ambiguities.
