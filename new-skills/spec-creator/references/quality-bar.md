# Quality Bar: What Makes a Symphony-Grade Spec

This document defines the quality rubric for specs produced by the spec-creator skill. The reference
implementation is the Symphony Service Specification — a 2100-line portable implementation contract
for a coding-agent orchestration service.

## The Five Layers of Spec Quality

A Symphony-grade spec operates at five distinct layers. Each layer locks down the next. If any
layer is weak, everything below it becomes ambiguous.

### Layer 1: Intent (WHY)

- **Problem Statement** is concrete and operational, not aspirational. "Solves four operational
  problems: [list]" not "Improves developer productivity."
- **Goals** are verifiable. Each goal can be tested with a yes/no question.
- **Non-Goals** are equally precise. They don't just say "not X" — they explain why X is out of
  scope and where X's responsibility lives instead.
- **Important Boundaries** are called out explicitly. "Symphony IS a scheduler/runner. Ticket
  writes are performed by the coding agent, not Symphony."

### Layer 2: Structure (WHAT)

- **System Overview** names every component with a one-sentence role description.
- **Abstraction Layers** are enumerated (Policy, Configuration, Coordination, Execution,
  Integration, Observability).
- **External Dependencies** are listed with version/protocol expectations.
- **Domain Model** defines every entity with typed fields, not just names.
  - Every field has: name, type, nullability, default (if applicable), and semantic meaning.
  - Normalization rules are explicit ("labels → lowercase strings").
  - Stable identifiers are defined with derivation rules.

### Layer 3: Behavior (HOW)

- **State Machines** enumerate all states with transition triggers and terminal conditions.
- **Lifecycle Phases** are ordered and numbered.
- **Algorithms** are provided in language-agnostic pseudocode for any non-trivial logic.
- **Concurrency rules** are explicit (who owns the lock, how slots are counted).
- **Ordering guarantees** are stated (sort by priority ascending, then oldest first, then
  identifier as tiebreaker).

### Layer 4: Contracts (BOUNDARIES)

- **Configuration** has a flat cheat-sheet with every key, type, and default.
- **Integration contracts** define required operations, query semantics, normalization rules, and
  error categories per external system.
- **Hook contracts** specify execution context (shell, cwd), timeout behavior, and failure
  semantics per hook type.
- **Protocol contracts** define message ordering, handshake sequences, and compatible payload
  shapes.
- **Error handling contracts** map every error class to a named category and recovery behavior.

### Layer 5: Verification (PROVE IT)

- **Test Matrix** maps bullet-for-bullet back to spec sections.
- **Validation Profiles** categorize tests: Core Conformance, Extension Conformance, Real
  Integration.
- **Implementation Checklist** is a literal punch-list grouped by conformance profile.
- **Each checklist item is a behavior**, not a feature name. "Dispatch sort order is priority then
  oldest creation time" not "Implement dispatch sorting."

## Quality Markers Checklist

Use this checklist during self-review. Every item should be true for a conforming spec.

### Precision
- [ ] No field exists without a type annotation
- [ ] No optional field exists without stating what happens when absent
- [ ] No timeout exists without a concrete default value in milliseconds
- [ ] No retry exists without a backoff formula and cap
- [ ] No list/array exists without stating its element type
- [ ] No enum exists without enumerating all values

### Completeness
- [ ] Every component in the system overview has at least one dedicated section
- [ ] Every external dependency has an integration contract section
- [ ] Every configurable value appears in the config cheat sheet
- [ ] Every error class has a named category and recovery behavior
- [ ] Every state in the state machine has at least one entry transition and one exit transition
- [ ] The test matrix covers every section of the spec

### Clarity for AI Agents
- [ ] No "use your judgment" or "handle appropriately" language
- [ ] No "standard practices" references without spelling out which practice
- [ ] No "reasonable default" without a concrete value
- [ ] No "implementation-defined" without listing what must be decided
- [ ] Pseudocode is provided for any algorithm with branching or loops
- [ ] The config cheat sheet is intentionally redundant with config section (agents parse it faster)

### Boundary Discipline
- [ ] Goals section has a matching Non-Goals section
- [ ] Every component has explicit scope boundaries
- [ ] "Important boundary" callouts exist for high-risk misinterpretation areas
- [ ] Forward compatibility is addressed (unknown keys, future extensions)
- [ ] Extension points are documented (what can be added without changing core)

### Structural Integrity
- [ ] Section numbering is consistent and hierarchical
- [ ] Cross-references between sections are by section number
- [ ] No circular dependencies between sections (each section builds on prior ones)
- [ ] The spec can be read linearly from top to bottom
- [ ] The implementation checklist items map to verifiable spec behaviors

## What This Spec Level is NOT

Understanding what the spec is NOT prevents the most common quality failures:

- **Not a PRD.** No user stories, no acceptance criteria, no business metrics, no stakeholder
  analysis. The "user" of this spec is an implementing engineer/agent.
- **Not an HLD.** Not just boxes and arrows. Every component has its internal contract defined.
- **Not an LLD.** Not tied to a specific language, framework, or library (unless explicitly
  chosen). Portable across implementations.
- **Not a design doc.** No alternatives-considered, no decision rationale, no meeting notes. The
  spec IS the decision — it documents what was decided, not the journey.
- **Not a tutorial.** Assumes the reader knows programming, common patterns, and standard
  protocols. Explains domain-specific decisions only.
- **Not a runbook.** Not operational procedures for humans. It's a build contract for implementors.
