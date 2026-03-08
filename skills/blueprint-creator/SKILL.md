---
name: blueprint-creator
description: >
  Create exhaustive BLUEPRINT.md files — the implementation bible that expands a SPEC.md into
  maximum granular detail so an AI coding agent can translate it line-by-line into code with zero
  interpretation. This skill REQUIRES a SPEC.md to already exist. Use this skill whenever the user
  wants to create a blueprint, implementation blueprint, detailed spec, "bible" document, or says
  "create the blueprint", "expand the spec", "make it more detailed", "generate BLUEPRINT.md", or
  "I need every detail spelled out." Also trigger when the user has a SPEC.md and wants to go
  deeper before implementation. The Blueprint is the final artifact before code — it takes the
  portable implementation contract (SPEC.md) and fills in every edge case, validation rule, error
  message, sequence, and example so nothing is left to judgment. Works for any software domain.
  If no SPEC.md exists, this skill MUST redirect the user to generate one first using the
  spec-creator skill.
---

# Blueprint Creator

Create exhaustive BLUEPRINT.md files by expanding a SPEC.md into maximum implementation detail.
The SPEC defines the contract. The Blueprint fills every corner of that contract so an AI agent
can translate it directly into code without a single judgment call.

**Pipeline position:** `SPEC.md` → `BLUEPRINT.md` → Code

## Prerequisite: SPEC.md Must Exist

Before doing anything else, verify that a SPEC.md exists. Check in this order:

1. **File in working directory:** Look for `SPEC.md` (or similar: `spec.md`, `SPEC_*.md`) in the
   current project directory or `/mnt/user-data/uploads/`.
2. **Provided in chat:** Check if the user pasted or attached spec content in this conversation.
3. **Referenced by name:** Check if the user mentioned a spec they created previously.

**If SPEC.md is found:** Acknowledge it, summarize its scope in 2-3 sentences, and proceed to
Phase 1.

**If SPEC.md is NOT found:** Stop and tell the user:

> "I need a SPEC.md before I can generate the Blueprint. The Blueprint expands a spec into
> exhaustive detail — without the spec, there's nothing to expand. Would you like me to use the
> spec-creator skill to generate a SPEC.md first? I'll walk you through the brainstorming process,
> and once we have a solid spec, I'll pick up the Blueprint from there."

Do NOT proceed with Blueprint generation without a SPEC.md. This is a hard gate.

## What the Blueprint Adds (The Delta)

The SPEC is a portable implementation contract with enough precision to implement. The Blueprint
is that same contract exploded into exhaustive detail. Here's the concrete delta:

| SPEC Level | Blueprint Level |
|---|---|
| Field has type and default | Field has type, default, exact validation rule, error on invalid, cross-ref to every usage site |
| "Suggested response shape" | Complete canonical example with every field populated, plus variant examples for edge cases |
| Prose description of algorithm | Pseudocode + decision table + sequence diagram + edge case table |
| Named error category | Full error catalog entry: code, message template, trigger condition, recovery, blast radius |
| State transition described in text | State transition table with every trigger × every state combination |
| "Normalize to lowercase" | Exact normalization pipeline: input → step 1 → step 2 → output, with 3+ examples including edge cases |
| Config key with default | Config key with default, validation, dynamic reload behavior, and trace to every behavioral impact |

Read `references/expansion-patterns.md` for the full expansion rulebook.

## Quality Bar

The Blueprint's quality bar is: **Could an AI agent implement every behavior by mechanically
translating Blueprint content into code, without ever needing to make an interpretive decision?**

Read `references/quality-bar.md` for the detailed rubric. Key markers:

- Every validation rule has explicit valid/invalid examples
- Every error has a code, message template, HTTP status (if applicable), and trigger condition
- Every algorithm has both pseudocode AND a decision table for branching
- Every data transformation has input → output examples (minimum 3, including edge cases)
- Every sequence of operations has a numbered step-by-step or diagram
- Every configuration key traces to the exact behaviors it affects
- Cross-references are exhaustive — every entity/field links to everywhere it's used

## Workflow

### Phase 1: SPEC Ingestion and Gap Analysis

After confirming SPEC.md exists:

1. **Read the entire SPEC.** Parse every section, entity, config key, state, error class, and
   algorithm.

2. **Build an expansion inventory.** For each SPEC section, identify what's at "spec level" and
   needs Blueprint-level expansion. Categorize into:
   - **Entities needing validation rules** (fields with types but no validation detail)
   - **Algorithms needing decision tables** (pseudocode with branching)
   - **Integrations needing full examples** ("suggested shapes" → exact canonical examples)
   - **Error classes needing full catalog entries** (named categories → code + message + trigger)
   - **Config keys needing behavioral traces** (key → where it affects behavior)
   - **States needing transition tables** (prose transitions → matrix)
   - **Flows needing sequence diagrams** (described processes → step-by-step)

3. **Present the expansion plan.** Show the user what you found:

   > "I've analyzed the SPEC. It has N sections, M entities, K config keys, and J error classes.
   > Here's my expansion plan: [summary of what needs to be expanded per section]. Before I start,
   > are there areas you want me to go especially deep on, or areas where the spec-level detail is
   > already sufficient?"

### Phase 2: Targeted Brainstorming

Unlike the SPEC brainstorming (which discovers requirements), Blueprint brainstorming fills
granular detail. The questions are specific and operational.

Ask questions **one round at a time**, 3-6 questions per round. Focus on areas where the SPEC
left deliberate flexibility that the Blueprint needs to lock down.

Read `references/brainstorm-patterns.md` for the questioning framework. Common areas:

- **Validation edge cases:** "The SPEC says `poll_interval_ms` is an integer with default 30000.
  What should happen with: zero? Negative? Float? String? Extremely large values?"
- **Error message specifics:** "The SPEC names `missing_workflow_file` as an error class. What
  should the error message say exactly? Should it include the path that was tried?"
- **Sequence ambiguities:** "The SPEC says reconciliation runs before dispatch on every tick.
  If reconciliation itself fails, should the tick continue to dispatch or abort entirely?"
- **Boundary behaviors:** "The SPEC says workspaces are reused. If a workspace exists but is
  corrupted (e.g., missing .git), what happens?"

**When to stop brainstorming:**

Stop when you can fill in every cell of every decision table, every field of every error catalog
entry, and every step of every sequence diagram without inventing anything.

### Phase 3: Drafting the BLUEPRINT.md

Read `references/section-templates.md` for the canonical Blueprint section structure. Then
draft the full document.

**Blueprint Section Structure:**

```
1.  Document Header (references SPEC, scope statement)
2.  System Context (expanded from SPEC system overview)
3.  Entity Catalog (every entity with full field specifications)
      - Per entity: field table with type, required/optional, default, validation,
        normalization, usage cross-references
4.  Configuration Bible (every config key fully specified)
      - Per key: type, default, validation rule, valid/invalid examples,
        dynamic reload behavior, behavioral impact trace
5.  State Transition Matrix (full state × trigger grid)
6.  Sequence Specifications (per major operation)
      - Per sequence: numbered steps, decision points, error branches
7.  Integration Specifications (per external system)
      - Per integration: exact request/response examples, pagination walkthrough,
        error response examples, normalization pipeline with examples
8.  Error Catalog (every error fully specified)
      - Per error: code, message template, trigger condition, recovery action,
        blast radius, operator visibility
9.  Validation Rules Compendium (every validation in one place)
10. Algorithm Detail (expanded pseudocode + decision tables)
11. Edge Case Encyclopedia (organized by subsystem)
12. Cross-Reference Index
13. Implementation Checklist (expanded from SPEC, more granular)
```

**Drafting rules — critical for exhaustive Blueprint quality:**

1. **Every field gets a full specification row.** Not just type and default, but: validation rule,
   what happens on invalid input, normalization steps, and cross-reference to every section that
   reads or writes this field.

2. **Every branching path gets a decision table.** If an algorithm has an `if/else`, it gets a
   table: Condition | Input State | Action | Result State | Side Effects.

3. **Every data transformation gets examples.** Minimum 3 examples: happy path, edge case, and
   error case. Format: `Input → [Step 1] → [Step 2] → Output`.

4. **Every error gets a catalog entry.** Code, message template (with variable slots), HTTP status
   (if applicable), trigger condition (exact), recovery action, blast radius (one item? one
   component? whole system?), operator visibility (how the operator learns about it).

5. **Every sequence gets numbered steps.** No prose descriptions of flows. Step 1, Step 2, Step 3.
   Each step names the actor, the action, the input, and the output. Decision points branch into
   labeled paths.

6. **Every "suggested" or "recommended" shape becomes canonical.** If the SPEC said "suggested
   response shape," the Blueprint provides THE response shape with every field, every type, every
   possible value documented.

7. **Cross-references are exhaustive.** The Entity Catalog links to every section that uses each
   entity. The Config Bible links to every behavior each key affects. The Error Catalog links to
   every operation that can produce each error.

8. **Edge cases are organized by subsystem**, not scattered throughout. A dedicated Edge Case
   Encyclopedia section collects every "what if" scenario the SPEC didn't explicitly cover.

9. **The Implementation Checklist is more granular than the SPEC's.** Where the SPEC says
   "Workspace manager with sanitized per-issue workspaces," the Blueprint says: "Workspace
   sanitization function: input `ABC-123` → output `ABC-123`. Input `feat/my branch` → output
   `feat_my_branch`. Input `../../etc/passwd` → output `______etc_passwd`. Validate: output
   contains only `[A-Za-z0-9._-]`."

**Output format:**

- Default: single monolithic `BLUEPRINT.md` file
- If the draft exceeds ~2500 lines, offer to split into logical files:
  - `BLUEPRINT.md` (core document)
  - `ERROR_CATALOG.md` (full error specifications)
  - `EDGE_CASES.md` (edge case encyclopedia)
  - `SEQUENCES.md` (sequence diagrams and step-by-step flows)
- Always include a cross-reference index regardless of split

### Phase 4: Self-Review

Before presenting the Blueprint, run a self-review. Read
`references/self-review-checklist.md` for the full checklist.

**Self-review process:**

1. **Mechanical translation test.** Pick 3 random sections. For each, ask: "Could I translate
   this into code line-by-line without making ANY interpretive decisions?" If the answer is no,
   the section needs more detail.

2. **Coverage check.** Walk through every SPEC section. Does the Blueprint have a corresponding
   expansion? If a SPEC section was not expanded, was that a conscious decision (explain why) or
   an oversight (fix it)?

3. **Consistency check.** Do entity field names match between Entity Catalog, Config Bible, Error
   Catalog, and Sequence Specifications? Inconsistency here causes implementation bugs.

4. **Example completeness check.** Does every validation rule have valid AND invalid examples?
   Does every transformation have at least 3 examples? Does every error have a trigger scenario?

5. **Produce Review Summary:**
   - SPEC sections covered vs. total
   - Entity fields fully specified vs. total
   - Error catalog entries vs. SPEC error classes
   - Decision tables created
   - Edge cases documented
   - Cross-references built
   - Gaps found and fixed during review
   - Remaining `[TBD]` markers
   - Confidence assessment

## Iteration

When the user requests changes:

- Apply changes surgically — the Blueprint is large, don't regenerate entirely
- If a change affects an entity field, update it in Entity Catalog AND trace through every
  cross-reference to update dependent sections
- If a change adds a new error, add a full catalog entry AND update the relevant sequence's error
  branch AND update the Edge Case Encyclopedia
- Re-run self-review on modified sections
- Present a changelog

## Anti-Patterns to Avoid

- **The copy-paste trap.** The Blueprint is NOT the SPEC with more words. Every section must add
  concrete detail the SPEC didn't have. If you can't identify the delta, the section doesn't
  belong.
- **The novel trap.** Don't write prose where a table suffices. Decision tables, field
  specification tables, and example pipelines are more precise than paragraphs.
- **The completionism trap.** Some SPEC sections (like Problem Statement, Goals/Non-Goals) don't
  need Blueprint expansion — they're already at maximum useful detail. Don't pad them.
- **The tech-stack trap.** The Blueprint is language-agnostic. Don't specify `Zod` or `Pydantic`
  or `JsonSchema`. Specify the validation RULE; let the implementing agent pick the tool.
- **The orphan trap.** Every piece of detail must trace back to a SPEC section. If you're adding
  detail that doesn't correspond to anything in the SPEC, either the SPEC has a gap (flag it) or
  the detail is out of scope.
