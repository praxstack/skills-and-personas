# Self-Review Checklist

Run this checklist against the drafted spec BEFORE presenting it to the user. Fix issues in-place
during review. Track what you found and fixed for the Review Summary.

## Pass 1: Agent-Readiness Scan

Walk through every section and ask: "Could an AI coding agent implement this section without asking
me a single clarifying question?"

For each section, check:

- [ ] **No vague defaults.** Search for: "reasonable", "appropriate", "as needed", "standard",
  "typical", "sufficient". Replace each with a concrete value.
- [ ] **No missing error handling.** Every operation that can fail has a named error and recovery
  behavior.
- [ ] **No implicit state transitions.** Every state change has an explicit trigger.
- [ ] **No unbounded behavior.** Every loop has a termination condition. Every retry has a cap.
  Every timeout has a value.
- [ ] **No unclear boundaries.** Every component knows what's its job and what isn't.
- [ ] **No untyped fields.** Every field in the domain model has a type annotation.
- [ ] **No hand-wavy sections.** "Implementation-defined" is only used when the implementation
  MUST make a decision, and the spec lists what decisions must be made.

## Pass 2: Structural Integrity

- [ ] **Section numbering is consistent.** No gaps, no duplicates, proper hierarchy.
- [ ] **Cross-references are by section number.** "As defined in Section 4.1.1" not "as defined
  above."
- [ ] **No circular dependencies.** Each section builds on sections that come before it.
- [ ] **Config cheat sheet exists** and matches the configuration section. Every key appears in both
  places.
- [ ] **Test matrix exists** and has at least one bullet per major spec section.
- [ ] **Implementation checklist exists** and is grouped by conformance profile.

## Pass 3: Completeness Check

For each component in the System Overview:
- [ ] Does it have a dedicated section or subsection?
- [ ] Are its inputs, outputs, and error modes defined?

For each entity in the Domain Model:
- [ ] Are all fields typed?
- [ ] Are required vs. optional fields marked?
- [ ] Are defaults specified for optional fields?
- [ ] Are normalization rules stated?

For each external dependency:
- [ ] Is there an integration contract section?
- [ ] Are required operations listed?
- [ ] Are error categories defined?
- [ ] Are timeout and retry semantics specified?

For each state in the state machine:
- [ ] Is there at least one way to enter this state?
- [ ] Is there at least one way to exit this state (or it's explicitly terminal)?
- [ ] Are transition triggers explicitly named?

## Pass 4: Common Failure Patterns

These are the most frequent spec defects. Check each one:

1. **The "it depends" trap.** Search for phrases that defer decisions without bounding them. Every
   "it depends" needs to become either a concrete rule or an explicit list of what the implementor
   must decide.

2. **The missing negative path.** For every success path, check: what happens on failure? What
   happens on timeout? What happens on invalid input? What happens on partial completion?

3. **The config-behavior gap.** For every configurable value, check: is there spec text that
   describes what behavior changes when this value changes? A config key without behavioral impact
   is dead configuration.

4. **The test-spec gap.** For every test matrix bullet, check: can you find the corresponding spec
   text? If a test bullet doesn't trace back to spec text, either the spec is missing something or
   the test is testing phantom behavior.

5. **The "at startup" gap.** What happens when the system starts? Is there a startup sequence? Does
   it validate before running? Does it clean up stale state? Many specs define steady-state behavior
   but forget the cold-start path.

6. **The "on shutdown" gap.** What happens when the system stops? Are in-flight operations drained
   or killed? Is state persisted? Many specs forget graceful shutdown entirely.

7. **The concurrency gap.** If multiple things can happen simultaneously, who wins? Is there a
   single authority for mutable state? Are race conditions addressed?

## Pass 5: Tone and Style

- [ ] **No tutorial tone.** The spec doesn't explain what a state machine is or how retries work
  in general. It defines THIS system's specific state machine and retry behavior.
- [ ] **No marketing language.** No "powerful", "flexible", "elegant", "seamless". Just facts.
- [ ] **No ambiguous pronouns.** "It" and "this" always have an unambiguous antecedent. When in
  doubt, use the full name.
- [ ] **Consistent terminology.** The same concept uses the same term throughout. No switching
  between "task" and "job" and "work item" for the same thing.
- [ ] **Imperative mood for requirements.** "The orchestrator validates config before dispatch" not
  "The orchestrator should validate config before dispatch."

## Review Summary Template

After completing all passes, write a Review Summary:

```markdown
## Self-Review Summary

**Sections:** [N]
**Total lines:** [N]
**Gaps found and fixed:** [N]
  - [Brief description of each fix]
**Remaining [TBD] markers:** [N]
  - [Each TBD with explanation of what user input is needed]
**Confidence:** [Ready for implementation / Needs user input on N items]
```

Present this summary to the user alongside the spec.
