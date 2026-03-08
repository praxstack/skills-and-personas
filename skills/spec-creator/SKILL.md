---
name: spec-creator
description: >
  Create production-grade SPEC.md files — portable implementation contracts that any AI coding agent
  can build from without follow-up questions. Use this skill whenever the user wants to write a spec,
  specification, technical spec, implementation contract, SPEC.md, or service specification for any
  software task. Also trigger when the user says "spec out", "write a spec for", "create a spec",
  "define the contract for", or describes a system they want built and needs a thorough specification
  before implementation. This skill works for backend services, full-stack apps, CLI tools, SDKs,
  developer tools, and any domain. It produces specs at the level of a principal-engineer-authored
  portable implementation contract — not a PRD, not an HLD, but the artifact that sits between
  architecture and code.
---

# Spec Creator

Create implementation-grade SPEC.md files through structured brainstorming, then drafting, then
self-review. The output is a single monolithic Markdown specification that an AI coding agent can
implement without asking clarifying questions.

## Quality Bar

The target quality level is a **portable implementation contract** — the kind of document a
principal engineer writes so any competent engineer (or AI agent) in any language can build a
conforming implementation. Read `references/quality-bar.md` for the full quality rubric before
starting any spec.

Key quality markers (internalize these, don't just check them off):

- Every entity field has a type, default value (if applicable), and validation rule
- Every error has a named category and explicit recovery behavior
- Every state transition has explicit triggers and outcomes
- Every boundary says what is in scope AND what is out of scope
- Reference algorithms are provided in language-agnostic pseudocode for complex logic
- Configuration has a cheat-sheet section for quick agent consumption
- The test/validation matrix maps back to spec sections
- Forward compatibility is addressed (e.g., "unknown keys should be ignored")
- The spec is self-contained: an agent reading only this file can implement the system

## Workflow

The spec creation process has 4 phases. Follow them in order.

### Phase 1: Intake and Calibration

When the user provides their input (anything from a one-liner to a detailed brain-dump):

1. **Parse what's already been said.** Extract every concrete decision, constraint, technology
   choice, boundary, entity, and opinion from the user's input.

2. **Classify input depth:**
   - **Sparse** (1-3 sentences, just an idea): The user needs heavy discovery. Start with
     foundational questions about problem, users, scope.
   - **Medium** (a paragraph or two with some decisions made): The user has direction. Focus on
     filling architectural and domain-model gaps.
   - **Rich** (detailed brain-dump with technology choices, entity sketches, constraints): The user
     has thought deeply. Focus on edge cases, failure modes, and contract boundaries.

3. **Acknowledge what you understood.** Before asking questions, write a short summary (3-5
   sentences) of what you extracted from their input. This lets the user correct misunderstandings
   early. Frame it as: "Here's what I'm taking as given from what you've described: [summary]. Now
   let me ask about the gaps."

### Phase 2: Brainstorming Rounds

Ask questions **one round at a time**. Each round should have 3-6 questions, grouped by a coherent
theme. Do NOT dump all questions at once. Wait for the user's answers before proceeding.

Continue rounds until all 10 knowledge domains are sufficiently covered for the task's complexity.
Not every domain applies to every task — use judgment. But never skip a domain without consciously
deciding it's irrelevant.

Read `references/brainstorm-domains.md` for the full questioning framework. Here is the summary:

**The 10 Knowledge Domains:**

1. **Problem & Scope** — What problem? Who benefits? What's the boundary?
2. **Architecture & Components** — What are the pieces? How do they connect?
3. **Domain Model** — What are the core entities, their fields, relationships?
4. **Configuration & Inputs** — What's configurable? Defaults? Validation?
5. **State & Lifecycle** — What states exist? What triggers transitions?
6. **Integration Contracts** — External systems, protocols, API shapes?
7. **Failure & Recovery** — What breaks? How does the system recover?
8. **Security & Safety** — Trust boundaries? Invariants? Secrets?
9. **Observability** — Logs, metrics, debugging? What does an operator need?
10. **Testing & Validation** — How do you prove correctness?

**Questioning strategy by input depth:**

- **Sparse input:** Start with Domain 1 (Problem & Scope) and Domain 2 (Architecture). These
  unlock everything else. Expect 5-8 rounds total.
- **Medium input:** Start with whichever domain has the biggest gaps. Expect 3-5 rounds.
- **Rich input:** Jump straight to edge cases — Domains 7 (Failure), 8 (Security), and 10
  (Testing) are usually the least-specified even in detailed brain-dumps. Expect 2-4 rounds.

**Rules for good brainstorming questions:**

- Ask about decisions, not preferences. "What happens when the webhook delivery fails after 3
  retries?" not "How do you feel about retry strategies?"
- Offer concrete options when the decision space is bounded. "Should failed jobs be retried with
  exponential backoff (recommended), fixed delay, or not retried?" — this accelerates the user.
- Flag when you're making an assumption. "I'm assuming WebSocket for real-time updates — push back
  if you prefer SSE or polling."
- Ask about what should NOT happen. Non-goals and anti-patterns are as valuable as goals.
- Ask about the consumer agent's needs. "Will the implementing agent need to handle graceful
  shutdown, or is hard-kill acceptable?"

**When to stop brainstorming:**

Stop when you can mentally draft every section header AND fill in the first paragraph of each
section without guessing. If you find yourself thinking "I'd have to make something up for the
failure recovery section," you need another round.

### Phase 3: Drafting the SPEC.md

Read `references/section-templates.md` for the canonical section structure and what belongs in each
section. Then draft the full spec.

**Section Structure (adapt to the task — not every section applies to every system):**

```
1.  Problem Statement
2.  Goals and Non-Goals
3.  System Overview (components, layers, external deps)
4.  Core Domain Model (entities, fields, types, normalization)
5.  [Domain-Specific Contract] (e.g., Workflow Spec, API Spec, Protocol Spec)
6.  Configuration Specification (schema, defaults, resolution, dynamic reload)
7.  State Machine / Lifecycle (states, transitions, triggers)
8.  Core Algorithms (scheduling, routing, processing — pseudocode)
9.  [Integration Contracts] (per external system)
10. [Subsystem Contracts] (per major internal subsystem)
11. Prompt/Context Assembly (if AI-related)
12. Logging, Status, and Observability
13. Failure Model and Recovery Strategy
14. Security and Operational Safety
15. Reference Algorithms (language-agnostic pseudocode)
16. Test and Validation Matrix
17. Implementation Checklist (Definition of Done)
```

**Drafting rules — these are critical for agent-consumable specs:**

1. **Every field needs a type.** Not "the timeout setting" but
   "`turn_timeout_ms` (integer) — Default: `3600000` (1 hour)".

2. **Every default needs a value.** If something is optional, say what happens when it's absent.
   Never "defaults to a reasonable value" — always "defaults to `30000`".

3. **Every error needs a name and a recovery.** Not "handle errors gracefully" but
   "`workspace_creation_failed` — Fail the current run attempt. Orchestrator will retry with
   exponential backoff."

4. **Every boundary needs both sides.** "Symphony IS a scheduler/runner. Symphony is NOT a ticket
   writer." Agents take unstated scope as license to expand.

5. **Use pseudocode for complex logic.** Any algorithm with branching, loops, or sequencing gets a
   pseudocode block. Use `function name(params):` style, not any specific language.

6. **Include a config cheat sheet.** A flat list of every config key, its type, and its default.
   Agents parse this faster than hunting through nested sections.

7. **Include "Important boundary" and "Important nuance" callouts.** These prevent the most common
   misimplementation. Place them inline where the misunderstanding would occur.

8. **State validation profiles in the test matrix.** "Core Conformance" (must-pass), "Extension
   Conformance" (if-you-ship-it-test-it), "Integration Profile" (needs real credentials).

9. **End with a Definition of Done checklist.** This is the literal implementation punch-list.
   Group by conformance profile.

10. **Write for the agent, not for a human skimming.** Be explicit, repetitive where it aids
    clarity, and never ambiguous. Agents don't infer intent — they follow contracts. Intentional
    redundancy (like a config cheat sheet that restates what's in the config section) is a feature,
    not a bug.

**Output format:**

- Default: single monolithic `SPEC.md` file
- If the draft exceeds ~2000 lines, offer to split into logical files:
  - `SPEC.md` (core spec)
  - `DOMAIN_MODEL.md` (entities, fields, normalization)
  - `TEST_MATRIX.md` (validation matrix + implementation checklist)
- Create the file(s) in `/home/claude/` during drafting, then copy to `/mnt/user-data/outputs/`
  when presenting.

### Phase 4: Self-Review

Before presenting the spec to the user, run a self-review against the quality bar. Read
`references/self-review-checklist.md` for the full checklist.

**Self-review process:**

1. Walk through every section and ask: "Could an AI coding agent implement this section without
   asking me a single clarifying question?" If no, fix it.

2. Check for these common spec failures:
   - **Vague defaults:** Any "reasonable", "appropriate", "as needed" → replace with concrete value
   - **Missing error handling:** Any operation without a failure path → add one
   - **Implicit state transitions:** Any state change without an explicit trigger → add the trigger
   - **Unbounded behavior:** Any loop, retry, or timeout without a cap → add the cap
   - **Unclear boundaries:** Any component without explicit in-scope/out-of-scope → add them
   - **Missing types:** Any field without a type annotation → add the type
   - **Hand-wavy sections:** Any section that says "implementation-defined" without documenting what
     the implementation must decide → enumerate the decisions

3. Produce a **Review Summary** (shown to user alongside the spec):
   - Number of sections
   - Total line count
   - Gaps found and fixed during self-review
   - Any remaining `[TBD]` markers with explanation of what's needed
   - Confidence assessment: "Ready for implementation" / "Needs user input on N items"

4. If the spec exceeds ~2000 lines, proactively offer to split it.

## Iteration

After presenting the spec, the user may request changes. When iterating:

- Apply changes surgically — don't regenerate the entire spec for a localized fix
- If the user's feedback reveals a gap in your understanding, you may need another brainstorming
  round before editing
- Re-run the self-review checklist on modified sections
- Track iteration count and present a changelog summary

## Anti-Patterns to Avoid

- **The PRD trap:** Don't write user stories, acceptance criteria, or business justification. This
  is an implementation contract, not a product requirements doc.
- **The HLD trap:** Don't stop at boxes-and-arrows. Every component needs its internal contract.
- **The design doc trap:** Don't include alternatives-considered or decision rationale (unless the
  user explicitly wants ADRs). The spec is the decision.
- **The tutorial trap:** Don't explain concepts. Assume the reader (an AI agent) knows programming,
  distributed systems, and common patterns. Explain domain-specific decisions.
- **The over-prescription trap:** Don't specify implementation language, framework, or library
  unless the user explicitly chose them. Keep the spec portable.
- **The under-specification trap:** Don't say "handle errors appropriately" or "use standard
  practices." Every behavior must be explicit enough to implement without judgment calls.
