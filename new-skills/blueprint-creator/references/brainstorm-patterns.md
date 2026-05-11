# Brainstorm Patterns: Targeted Questioning for Blueprint Expansion

Blueprint brainstorming is fundamentally different from SPEC brainstorming. SPEC brainstorming
discovers requirements ("what are we building?"). Blueprint brainstorming fills granular detail
("what exactly happens when X meets Y?").

## Questioning Strategy

The SPEC already answers the big questions. Blueprint questions target:

1. **Validation boundaries** — What are the exact edges of valid input?
2. **Error specifics** — What exactly should the error message say?
3. **Sequence ambiguities** — In exactly what order do these steps happen?
4. **Combinatorial blind spots** — What happens when condition A AND condition B are both true?
5. **Degradation behavior** — When something partially fails, what's the exact state of the system?

## Question Categories

### Category 1: Validation Boundary Questions

For every field in the domain model that accepts external input, ask about boundaries.

**Template:**
"The SPEC says `{field}` is a `{type}` with default `{default}`. I need to lock down the
validation. What should happen with: {boundary_list}?"

**Common boundary lists by type:**

- **Integer fields:** zero, negative, extremely large (MAX_INT), float, string, null, empty string
- **String fields:** empty string, whitespace only, extremely long (10KB), unicode/emoji,
  newlines, null, control characters
- **Path fields:** relative paths, absolute paths, `~`, `..`, symlinks, paths with spaces,
  non-existent paths, paths to files (not dirs), permission-denied paths
- **List fields:** empty list, single item, duplicates in list, extremely long list, null items
  in list, mixed types in list
- **Enum fields:** unknown value, wrong case, with whitespace, null
- **Duration/timeout fields:** zero, negative, sub-millisecond, extremely large (days), float

**Example:**
"The SPEC says `hooks.timeout_ms` is an integer, default 60000, and non-positive values fall back
to default. I want to confirm: does 'non-positive' mean ≤ 0 (zero AND negative both fall back)?
What about string '60000' — coerce to integer or validation error? What about float 60000.5?"

### Category 2: Error Message Questions

For every named error class, ask about the message content.

**Template:**
"The SPEC names `{error_class}` as an error. For the Blueprint I need: What should the error
message include? Should it contain the value that caused the error? The path/key where it
occurred? A suggestion for how to fix it?"

**Example:**
"The SPEC says `workflow_parse_error` is an error class. Should the message include the line
number where YAML parsing failed? Should it include a snippet of the malformed content? Or just
'Failed to parse WORKFLOW.md: {reason}'?"

### Category 3: Sequence Ordering Questions

For any process described as multiple steps, ask about ordering constraints.

**Template:**
"The SPEC describes {process} as: Step A, then Step B, then Step C. I need to clarify:
- Must A fully complete before B starts, or can they overlap?
- If B fails, is A's output rolled back?
- If the process is interrupted between B and C, what's the system state?"

**Example:**
"In the workspace creation sequence: directory creation → `after_create` hook → workspace returned.
If the hook fails, the SPEC says creation fails. Should the directory be deleted (rollback) or left
in place? If left in place, will the next attempt see it as 'existing' and skip `after_create`?"

### Category 4: Combination Questions

For any two conditions that can be simultaneously true, ask what wins.

**Template:**
"What happens when {condition A} and {condition B} occur at the same time? Which takes precedence?"

**Example:**
"What happens if a WORKFLOW.md reload changes `active_states` at the exact same time a
reconciliation tick is checking issue states against the old `active_states`? Does reconciliation
use the old or new states? Is there a consistency window?"

### Category 5: Degradation Questions

For any partial failure scenario, ask about the exact resulting state.

**Template:**
"If {operation} partially completes — specifically, {step N} succeeds but {step N+1} fails — what
is the exact state of: {component A}, {component B}, {the user-facing behavior}?"

**Example:**
"If the app-server subprocess starts successfully but the `initialize` handshake times out — is the
subprocess killed immediately? Is the workspace left in the 'running' state? Does the orchestrator
see this as a normal or abnormal worker exit?"

## Adaptive Questioning by SPEC Quality

### When the SPEC is very thorough (like Symphony)

Focus on:
- Error message exact wording (the SPEC names errors but not their messages)
- Validation boundary values (the SPEC defines types but not all edges)
- Cross-operational combinations (the SPEC documents each operation but not their intersections)
- Recovery partial states (the SPEC says "retry" but not what state the system is in mid-recovery)

Expect: 1-3 rounds.

### When the SPEC has intentional flexibility

Look for phrases like "implementation-defined", "may", "recommended". These are Blueprint expansion
points. Ask the user to lock down each one.

**Template:**
"The SPEC says `{behavior}` is implementation-defined. For the Blueprint I need a concrete choice.
Here are the options I see: {Option A}, {Option B}, {Option C}. Which should the Blueprint specify?"

Expect: 2-4 rounds.

### When the SPEC is minimal

Every section likely needs expansion questions. Work through the expansion patterns
(see `expansion-patterns.md`) systematically, one pattern per round.

Expect: 4-6 rounds.

## When to Stop

Stop when you can fill in every cell of these artifacts without inventing anything:

- [ ] Every field specification row has all columns filled
- [ ] Every error catalog entry has all fields
- [ ] Every decision table cell has a concrete action
- [ ] Every sequence step has an error branch
- [ ] Every config key has valid AND invalid examples

If you're guessing to fill any cell, ask one more round targeting that gap.
