# Brainstorming Domains: Structured Questioning Framework

This document defines the 10 knowledge domains that must be explored during brainstorming to
produce a Symphony-grade spec. Each domain includes purpose, key questions, and signals that
indicate the domain is sufficiently covered.

## How to Use This Framework

- Ask questions **one round at a time**, 3-6 questions per round, grouped by theme.
- Not every domain applies to every task. Skip domains consciously, not accidentally.
- Adapt question depth to input richness. Don't ask foundational questions when the user has
  already provided detailed architecture.
- Track which domains are covered. At the end of each round, mentally check off domains.
- Stop when you can draft every section header AND its first paragraph without guessing.

---

## Domain 1: Problem & Scope

**Purpose:** Establish why this system exists, who it serves, and where it ends.

**Key questions:**

- What specific problem does this system solve? (Operational, not aspirational)
- Who are the direct consumers? (Users, other services, AI agents, operators)
- What are the 3-5 most important things this system MUST do?
- What are 3-5 things that are explicitly NOT this system's job?
- Is this a greenfield build or does it replace/extend something existing?
- What is the "minimum viable spec" — the smallest system that solves the core problem?
- Are there hard constraints (performance budgets, compliance, platform restrictions)?

**Sufficiency signal:** You can write the Problem Statement, Goals, and Non-Goals sections without
inventing anything.

---

## Domain 2: Architecture & Components

**Purpose:** Identify the building blocks and how they connect.

**Key questions:**

- What are the major components/modules of this system?
- What is each component's single-sentence responsibility?
- What are the abstraction layers? (Policy, Config, Core Logic, Execution, Integration,
  Observability)
- What are the external dependencies? (APIs, databases, filesystems, third-party services)
- What communication patterns exist between components? (Sync calls, events, queues, shared state)
- Which components are required vs. optional/pluggable?
- Is there a single authority for mutable state, or is state distributed?

**Sufficiency signal:** You can draw the system overview with component names, layer assignments,
and dependency arrows.

---

## Domain 3: Domain Model

**Purpose:** Define the core entities, their shapes, and how they relate.

**Key questions:**

- What are the 3-7 core entities this system operates on?
- For each entity: what are its fields, types, and which are required vs. optional?
- What are the stable identifiers? How are they derived or assigned?
- Are there normalization rules? (Case folding, character sanitization, timestamp parsing)
- What are the relationships between entities? (One-to-many, references, derived fields)
- Are there computed/derived fields? What are their derivation rules?
- What does "the same entity" mean? (Equality semantics, deduplication rules)

**Sufficiency signal:** You can write a typed entity definition for each core entity with all
fields, types, defaults, and normalization rules.

---

## Domain 4: Configuration & Inputs

**Purpose:** Define what's configurable, how configuration is loaded, and what the defaults are.

**Key questions:**

- What runtime values are configurable? List every one you can think of.
- For each: what's the type, default value, and validation rule?
- Where does configuration come from? (File, environment, CLI args, API)
- What's the precedence when multiple sources conflict?
- Are there environment variable indirection patterns? (e.g., `$VAR_NAME` in config files)
- Does configuration support dynamic reload without restart?
- What happens when configuration is invalid? (Fail startup? Use last known good? Degrade?)
- Is there path expansion needed? (`~`, env vars, relative paths)

**Sufficiency signal:** You can write a flat config cheat sheet with every key, type, default, and
source.

---

## Domain 5: State & Lifecycle

**Purpose:** Map the state machines, transitions, and lifecycle phases.

**Key questions:**

- What are the possible states of the primary entity? (Not external states — internal orchestration
  states)
- What triggers each state transition? Be specific: "poll tick", "worker exit", "timer fired"
- Are there lifecycle phases within a single operation? (e.g., Preparing → Building → Launching →
  Streaming → Finishing)
- What are the terminal states and how does the system reach them?
- Is there a distinction between "completed" and "released" states?
- Can the same entity go through the lifecycle multiple times? (Retries, continuations)
- What idempotency guarantees exist? Can duplicate transitions cause harm?

**Sufficiency signal:** You can enumerate all states, draw all transitions with labeled triggers,
and identify all terminal states.

---

## Domain 6: Integration Contracts

**Purpose:** Define the interface with every external system.

**Key questions:**

- For each external system:
  - What operations does this system require from it? (List them as function signatures)
  - What's the transport? (HTTP, GraphQL, gRPC, stdio, filesystem)
  - What authentication is needed?
  - What's the request/response shape? (At least key fields)
  - What normalization must happen on responses?
  - What are the pagination, timeout, and retry semantics?
- Are there protocol handshakes or session establishment sequences?
- What happens when the external system is unavailable?
- Are there compatibility concerns across versions of the external system?

**Sufficiency signal:** You can write the integration contract section for each external system
including operations, query semantics, normalization rules, and error categories.

---

## Domain 7: Failure & Recovery

**Purpose:** Map every failure class to a named category and recovery strategy.

**Key questions:**

- What are the categories of things that can go wrong? (Config, workspace, network, external
  service, internal logic, resource exhaustion)
- For each failure category:
  - What specific errors can occur?
  - Is the failure transient or permanent?
  - What's the recovery strategy? (Retry, skip, degrade, fail fast, alert)
  - Does recovery require human intervention?
- What happens on process restart? What state survives? What's lost?
- Is there a retry mechanism? What's the backoff formula and cap?
- What's the "blast radius" of each failure? (Affects one item, one component, whole system)
- Are there circuit breakers or rate limiters?

**Sufficiency signal:** You can write the failure model section with named error categories,
recovery behaviors, and restart semantics.

---

## Domain 8: Security & Safety

**Purpose:** Define trust boundaries, invariants, and secret handling.

**Key questions:**

- What's the trust model? (Fully trusted environment? Multi-tenant? Untrusted input?)
- What safety invariants must never be violated? (e.g., "agent runs only in its workspace")
- How are secrets handled? (Environment vars, secret stores, never logged)
- Are there filesystem safety constraints? (Path containment, sanitization)
- Are there operations that could be destructive if misapplied?
- Is there user/operator input that could be malicious? (Prompt injection, path traversal)
- What hardening measures should implementations consider?
- Should the spec mandate security posture or let implementations choose and document?

**Sufficiency signal:** You can write the security section with trust boundaries, mandatory
invariants, and a hardening guidance list.

---

## Domain 9: Observability

**Purpose:** Define what operators need to see and how.

**Key questions:**

- What structured log fields are required on every log entry?
- What events must be logged? (Startup, dispatch, completion, failure, retry)
- Are there metrics that should be tracked? (Counters, gauges, histograms)
- Is there a runtime status/snapshot interface? What does it return?
- Is there a human-readable dashboard? What does it show?
- Should log sink failures crash the system or be absorbed?
- Is there token/resource accounting? How are totals calculated?
- What debugging information should be available without a debugger?

**Sufficiency signal:** You can write the observability section with log field requirements,
snapshot schema, and metric definitions.

---

## Domain 10: Testing & Validation

**Purpose:** Define how to prove an implementation is conforming.

**Key questions:**

- What are the validation profiles? (Core Conformance, Extension, Integration)
- For each spec section: what specific behaviors should be tested?
- Are there environment-dependent tests that need credentials or network access?
- What's the boundary between unit-testable and integration-testable behaviors?
- Are there invariants that should be continuously validated at runtime?
- What does "definition of done" look like for an implementation?

**Sufficiency signal:** You can write a test matrix where every bullet maps to a specific spec
behavior, and an implementation checklist with every required capability.

---

## Adaptive Questioning Strategy

### Sparse Input (1-3 sentences)
**Round 1:** Problem & Scope (Domain 1) — establish what we're building
**Round 2:** Architecture & Components (Domain 2) — identify the pieces
**Round 3:** Domain Model (Domain 3) + Configuration (Domain 4) — shape the data
**Round 4:** State & Lifecycle (Domain 5) + Integration (Domain 6) — define behavior
**Round 5:** Failure & Recovery (Domain 7) + Security (Domain 8) — handle the bad paths
**Round 6:** Observability (Domain 9) + Testing (Domain 10) — prove it works
**Round 7+:** Follow-up on gaps discovered in prior rounds

### Medium Input (a paragraph or two)
Start with whichever domain has the biggest gap. Likely order:
**Round 1:** Domain Model + State/Lifecycle (these are rarely in initial descriptions)
**Round 2:** Configuration + Integration Contracts
**Round 3:** Failure + Security + Observability
**Round 4+:** Targeted follow-ups

### Rich Input (detailed brain-dump)
**Round 1:** Edge cases in Failure (Domain 7) + Security (Domain 8) — almost always underspecified
**Round 2:** Testing (Domain 10) + any gaps from parsing the brain-dump
**Round 3+:** Targeted follow-ups if any domain is still weak

---

## Ending Brainstorming

Before declaring brainstorming complete, do a mental walkthrough:

1. Can I write the Problem Statement without guessing? ✓/✗
2. Can I list every component and its responsibility? ✓/✗
3. Can I define every entity with typed fields? ✓/✗
4. Can I list every config key with its type and default? ✓/✗
5. Can I draw the state machine with all transitions? ✓/✗
6. Can I write the integration contract for each external system? ✓/✗
7. Can I name every error category and its recovery? ✓/✗
8. Can I state the safety invariants? ✓/✗
9. Can I define the structured log fields? ✓/✗
10. Can I write the test matrix? ✓/✗

If any answer is ✗, ask one more round of targeted questions for that domain.

When ready, tell the user: "I have enough to draft a comprehensive spec. I'll write it now and
include a self-review. Ready to proceed?"
