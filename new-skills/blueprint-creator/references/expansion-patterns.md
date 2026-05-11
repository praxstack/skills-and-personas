# Expansion Patterns: How to Expand Each SPEC Section Type

This document defines the mechanical expansion rules for converting SPEC-level content into
Blueprint-level content. For each type of SPEC content, there is a specific expansion pattern.

## Pattern 1: Field Definition → Full Field Specification

**Trigger:** SPEC defines an entity field with type, default, and semantic meaning.

**Expansion:**

```
Field: {field_name}
  Type: {type}
  Required/Optional: {required | optional}
  Default: {value} (when: {condition for default to apply})
  Validation:
    - {Rule 1}
    - {Rule 2}
  Valid examples: {example_1}, {example_2}, {example_3}
  Invalid examples: {example_1}, {example_2}, {example_3}
  On invalid:
    - At startup: {behavior}
    - At runtime: {behavior}
    - On reload: {behavior}
  Normalization: {steps, if any}
  Behavioral impact: {what changes when this field's value changes}
  Cross-references:
    - Read by: {Section X.Y (description)}
    - Written by: {Section X.Y (description)}
    - Validated in: {Section X.Y (description)}
```

**What to ask the user if unclear:**
- What are the boundary values? (min, max, zero, empty)
- What's the coercion behavior? (string "30000" → integer 30000?)
- Are there interaction effects with other fields?

---

## Pattern 2: Named Error → Error Catalog Entry

**Trigger:** SPEC names an error category with a recovery strategy.

**Expansion:**

```
Error: {ERROR_CODE}
  Code: "{error_code_string}"
  Message template: "{message with {variable} slots}"
  Variables:
    - {var_name}: {type} ({description})
  Trigger condition: {Exact condition, not vague}
  Recovery:
    - {Specific recovery action}
    - {Fallback if recovery fails}
  Blast radius: {What's affected — one item? one tick? whole system?}
  Operator visibility: {How operator sees this — log level, structured fields}
  Retryable: {yes/no}
  Cross-references:
    - Produced by: {Section X.Y}
    - Handled in: {Section X.Y}
```

**What to ask the user if unclear:**
- Should error messages include contextual data? (e.g., the file path that was missing)
- Are there sub-categories within this error class?
- What log level should this be? (debug, info, warn, error)

---

## Pattern 3: Algorithm (Pseudocode) → Algorithm + Decision Table

**Trigger:** SPEC provides pseudocode with branching logic.

**Expansion:** Keep the pseudocode AND add a decision table that maps every input combination to
an outcome.

```
### Algorithm: {name}

#### Pseudocode
{Keep the original SPEC pseudocode, possibly refined}

#### Decision Table

| {Input 1} | {Input 2} | {Condition} | Action | Result | Side Effects |
|---|---|---|---|---|---|
| {value} | {value} | {condition} | {action} | {result} | {effects} |
| ... | ... | ... | ... | ... | ... |

#### Edge Cases

| Scenario | Input State | Expected Behavior | Rationale |
|---|---|---|---|
| {scenario} | {state} | {behavior} | {why} |
```

**What to ask the user if unclear:**
- What happens in the "else" branch? (Never leave a catch-all undocumented)
- Are there ordering sensitivities? (Does step A need to complete before step B starts?)
- What's the worst case? (Maximum iterations, maximum concurrent operations)

---

## Pattern 4: State Machine → State Transition Matrix

**Trigger:** SPEC describes states and transitions in prose or pseudocode.

**Expansion:** Create a full matrix: every state × every possible trigger = action + result state.

```
### State Transition Matrix

| Current State | Trigger | Guard Condition | Action | Next State | Notes |
|---|---|---|---|---|---|
| Unclaimed | poll_tick + eligible | slots available | dispatch | Claimed → Running | |
| Running | worker_exit_normal | — | schedule continuation retry | RetryQueued | attempt=1, delay=1s |
| Running | worker_exit_abnormal | — | schedule backoff retry | RetryQueued | delay=10s×2^(attempt-1) |
| Running | reconcile_terminal | — | stop + cleanup workspace | Released | |
| Running | reconcile_non_active | — | stop (no cleanup) | Released | |
| Running | stall_timeout | elapsed > stall_timeout_ms | kill + schedule retry | RetryQueued | |
| RetryQueued | timer_fired + eligible | slots available | dispatch | Running | |
| RetryQueued | timer_fired + not_found | — | release claim | Released | |
| RetryQueued | timer_fired + no_slots | — | requeue | RetryQueued | attempt+1 |
| ... | ... | ... | ... | ... | ... |

### Illegal Transitions (Must Never Happen)

| From | To | Why Illegal |
|---|---|---|
| Released | Running | Cannot dispatch without going through Unclaimed → Claimed first |
| ... | ... | ... |
```

**What to ask the user if unclear:**
- Are there any transitions that should be impossible? (Illegal transitions are as important
  as legal ones)
- Can the same trigger have different effects depending on timing?
- Are there transient states that exist briefly during transitions?

---

## Pattern 5: "Suggested Shape" → Canonical Shape

**Trigger:** SPEC provides a "suggested" or "recommended" JSON/data shape.

**Expansion:** Make it THE canonical shape. Document every field.

```
### Canonical Response: GET /api/v1/state

Every field is required in the response unless marked (optional).

{
  "generated_at": "2026-02-24T20:15:30Z",
    // Type: ISO-8601 UTC timestamp string
    // Always present. Timestamp of snapshot generation.

  "counts": {
    "running": 2,
      // Type: non-negative integer
      // Count of entries in the running array below.
    "retrying": 1
      // Type: non-negative integer
      // Count of entries in the retrying array below.
  },

  "running": [
    {
      "issue_id": "abc123",
        // Type: string
        // Tracker-internal stable ID. Matches domain model Issue.id.
      "issue_identifier": "MT-649",
        // Type: string
        // Human-readable key. Matches domain model Issue.identifier.
      ...
    }
  ],
  ...
}

### Variant Examples

**Empty state (service just started, no work dispatched):**
{response with all arrays empty, counts at 0}

**Saturated state (all slots full, retries queued):**
{response showing max concurrency reached}

**Error state (tracker unreachable):**
{response showing running entries still present, last error fields populated}
```

---

## Pattern 6: Integration Contract → Full Request/Response Specification

**Trigger:** SPEC defines required operations for an external system.

**Expansion:** Document exact request and response shapes for each operation, including error
responses.

```
### Operation: fetch_candidate_issues

#### Request
  Transport: HTTP POST
  Endpoint: {tracker.endpoint}
  Headers:
    - Authorization: {tracker.api_key}
    - Content-Type: application/json
  Body:
    {Exact GraphQL query with variable definitions}
  Variables:
    - projectSlug: {tracker.project_slug}
    - states: {tracker.active_states}
    - after: {pagination cursor, null for first page}

#### Successful Response (200)
  {Exact response shape with every field documented}

#### Pagination
  Step 1: Send initial request with after=null
  Step 2: Check response.data.issues.pageInfo.hasNextPage
  Step 3: If true, send next request with after=response.data.issues.pageInfo.endCursor
  Step 4: Repeat until hasNextPage=false
  Step 5: Concatenate all response.data.issues.nodes arrays
  Note: Page order must be preserved across pages

#### Error Responses
  401: {meaning, handling}
  403: {meaning, handling}
  429: {meaning, handling}
  500: {meaning, handling}
  Network timeout: {handling}
  Malformed response: {handling}

#### Normalization Pipeline
  Raw API node → normalized Issue entity

  Step 1: Extract fields (map API field names to domain model field names)
  Step 2: Normalize labels to lowercase
  Step 3: Derive blocked_by from inverse relations where type == "blocks"
  Step 4: Parse timestamps from ISO-8601
  Step 5: Coerce priority to integer (non-integer → null)

  Example:
    API node: {raw shape}
    → After Step 1: {intermediate}
    → After Step 5: {final normalized Issue}
```

---

## Pattern 7: Config Key → Config Bible Entry

**Trigger:** SPEC defines a config key with type and default.

**Expansion:**

```
### Config: {key.path}

Type: {type}
Default: {value}
Source: {where it comes from — YAML front matter key path}
Resolution: {precedence — e.g., "CLI override > YAML value > environment via $VAR > default"}

Validation:
  - {Rule 1}
  - {Rule 2}
  Valid: {examples}
  Invalid: {examples}
  On invalid at startup: {behavior}
  On invalid at reload: {behavior}

Dynamic reload: {yes/no}
  If yes: Takes effect {when — next tick, next dispatch, next run launch}
  If no: Requires restart

Behavioral impact:
  - {Behavior 1 that changes when this value changes} (Section X.Y)
  - {Behavior 2} (Section X.Y)

Interaction effects:
  - {Other config keys this interacts with, if any}
```

---

## Pattern 8: Prose Process → Numbered Sequence Specification

**Trigger:** SPEC describes a multi-step process in paragraph form.

**Expansion:**

```
### Sequence: {Process Name}

Actors: {who participates}
Trigger: {what initiates this sequence}
Preconditions: {what must be true before starting}

Steps:

1. [{Actor}] {Action verb} {what}
   Input: {what this step receives}
   Output: {what this step produces}
   → On success: Continue to Step 2
   → On failure: {exact error handling — go to Step Xa, retry, abort}

2. [{Actor}] {Action verb} {what}
   Input: {from Step 1 output}
   Output: {produced}
   Decision point:
     → If {condition A}: Continue to Step 3
     → If {condition B}: Go to Step 2a
     → If {condition C}: Go to Step 2b

2a. [{Actor}] {Handle condition B}
   ...

3. [{Actor}] {Action verb} {what}
   ...

Final states:
  - Success: {what the system looks like after successful completion}
  - Failure (Step 1): {system state}
  - Failure (Step 2): {system state}
  - Timeout: {system state}
```

---

## Expansion Priority

When expanding a SPEC into a Blueprint, prioritize in this order:

1. **Entity fields and validation** — This is the foundation. Get the types right first.
2. **Error catalog** — Agents waste the most time guessing error handling. Lock it down early.
3. **State transitions** — The matrix catches cases the prose misses.
4. **Integration contracts** — External system details are the highest risk for drift.
5. **Algorithms and decision tables** — Complex logic needs the most precision.
6. **Config traceability** — Connect every knob to every behavior it affects.
7. **Sequence specifications** — Formalize the flows.
8. **Edge cases** — Collect the remaining "what ifs."
9. **Cross-reference index** — Build this last since it references everything above.

---

## Sections That Usually Don't Need Expansion

Not every SPEC section benefits from Blueprint-level expansion:

- **Problem Statement** — Already at maximum useful detail in the SPEC. Carry forward as-is.
- **Goals and Non-Goals** — Same. No expansion needed.
- **Abstraction Layers** — Architectural guidance. Carry forward.
- **Security posture guidance** — Blueprint may add specific validation examples, but the posture
  description itself doesn't expand.

When carrying forward without expansion, note: "Carried from SPEC Section N — no Blueprint
expansion required."
