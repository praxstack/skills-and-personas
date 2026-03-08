# Quality Bar: What Makes a Bible-Grade Blueprint

This document defines the quality rubric for BLUEPRINT.md files. The Blueprint sits between the
SPEC (portable contract) and Code (implementation). Its job is to eliminate every interpretive
decision an implementing agent would otherwise have to make.

## The Core Test

For any given section of the Blueprint, ask:

> "Could an AI coding agent translate this section into code by mechanical line-by-line conversion,
> without ever pausing to think 'what should I do here?'"

If the answer is no, the section needs more detail.

## Seven Dimensions of Blueprint Quality

### 1. Validation Exhaustiveness

Every field that accepts input has:
- [ ] Exact type constraint (not just "integer" but "positive integer > 0")
- [ ] At least one valid example
- [ ] At least one invalid example
- [ ] Exact behavior on invalid input (error code, message, recovery)
- [ ] Boundary values documented (min, max, zero, null, empty string)

**SPEC level:** "`poll_interval_ms` (integer) — Default: `30000`"

**Blueprint level:**
```
Field: poll_interval_ms
Type: integer
Default: 30000
Validation:
  - Must be a positive integer (> 0)
  - String integers are coerced: "30000" → 30000
  - Non-numeric strings → validation error
  - Floats → validation error (do not truncate)
  - Null/missing → use default (30000)
  - Zero → validation error
  - Negative → validation error
Valid examples:   1000, 30000, 120000
Invalid examples: 0, -1, "fast", 30.5, null (when required), "", []
On invalid: Emit validation error. At startup: fail startup. On reload: keep last
  known good value, emit operator-visible warning.
Behavioral impact: Controls delay between poll ticks. Change takes effect on next
  scheduled tick without restart.
Cross-references: Section 8.1 (Poll Loop), Section 6.2 (Dynamic Reload)
```

### 2. Example Completeness

Every data transformation, normalization, and processing step has:
- [ ] At minimum 3 examples: happy path, edge case, error case
- [ ] Input → intermediate steps → output format
- [ ] Examples cover boundary conditions

**SPEC level:** "Derive workspace key by replacing characters not in `[A-Za-z0-9._-]` with `_`"

**Blueprint level:**
```
Workspace Key Sanitization Pipeline:

Input                    → Output              Notes
─────────────────────────────────────────────────────────
"ABC-123"                → "ABC-123"           Already clean
"feat/my-branch"         → "feat_my-branch"    Slash replaced
"ABC 123"                → "ABC_123"           Space replaced
"../../etc/passwd"       → "______etc_passwd"  Path traversal neutralized
"hello@world#2"          → "hello_world_2"     Special chars replaced
""                       → ""                  Empty stays empty (caught by later validation)
"a"                      → "a"                 Single char OK
"---"                    → "---"               Dashes are allowed
"A.B_C-D"               → "A.B_C-D"           All allowed chars preserved
"über"                   → "_ber"              Non-ASCII replaced
```

### 3. Decision Table Coverage

Every algorithm with branching has:
- [ ] A decision table mapping every input combination to an outcome
- [ ] No "else" catch-all without documenting what falls into it
- [ ] Edge cases at decision boundaries

**SPEC level:** Pseudocode with if/else branches

**Blueprint level:**
```
Blocker Eligibility Decision Table:

Issue State | Has Blockers | All Blockers Terminal | Eligible?
────────────────────────────────────────────────────────────
Todo        | No           | N/A                   | Yes
Todo        | Yes          | Yes                   | Yes
Todo        | Yes          | No (any non-terminal) | No — skip
Todo        | Yes          | Mixed                 | No — skip (at least one non-terminal)
In Progress | No           | N/A                   | Yes
In Progress | Yes          | Any                   | Yes — blockers only gate Todo
Other Active| Any          | Any                   | Yes — blockers only gate Todo
```

### 4. Error Catalog Completeness

Every named error class has:
- [ ] Unique error code
- [ ] Message template with variable slots
- [ ] Exact trigger condition (not "when something fails" but "when HTTP status != 200")
- [ ] Recovery action
- [ ] Blast radius (affects one item? one component? whole system?)
- [ ] Operator visibility (how the operator learns about this error)

**SPEC level:** "Recommended error categories: `linear_api_request`, `linear_api_status`"

**Blueprint level:**
```
Error: LINEAR_API_STATUS
  Code: "linear_api_status"
  Message: "Linear API returned non-200 status: {status_code} {status_text} for {operation}"
  Trigger: HTTP response from Linear GraphQL endpoint has status code outside 200-299 range
  Variables:
    - status_code: integer (e.g., 401, 403, 429, 500, 502, 503)
    - status_text: string (HTTP reason phrase)
    - operation: string (e.g., "fetch_candidate_issues", "fetch_issue_states")
  Recovery:
    - 401/403: Log auth error, skip dispatch this tick, retry next tick
      (persistent failure suggests credential rotation needed — operator intervention)
    - 429: Log rate limit, skip dispatch this tick, retry next tick
    - 500/502/503: Log server error, skip dispatch this tick, retry next tick
    - Other: Log unexpected status, skip dispatch this tick, retry next tick
  Blast radius: Affects all issue fetching for current tick. Running agents unaffected.
  Operator visibility: Structured log at WARN level with status_code and operation fields.
  Cross-references: Section 11.4 (Error Handling Contract), Section 8.1 (Poll Loop)
```

### 5. Sequence Specification Rigor

Every multi-step operation has:
- [ ] Numbered steps (not prose)
- [ ] Each step names: actor, action, input, output
- [ ] Decision points branch into labeled paths
- [ ] Error branches at every step that can fail
- [ ] Final state clearly identified for each path

**SPEC level:** Pseudocode for `on_tick(state)`

**Blueprint level:**
```
Sequence: Poll Tick

Step 1: [Orchestrator] Execute reconciliation
  Input: current state (running map, retry queue)
  Action: Call reconcile_running_issues(state)
  Output: Updated state
  Error: If reconciliation crashes → log error, continue to Step 2 with unchanged state

Step 2: [Orchestrator] Validate dispatch config
  Input: current workflow config
  Action: Run dispatch preflight validation
  Output: validation_result (ok | error)
  → If error: Go to Step 2a
  → If ok: Go to Step 3

Step 2a: [Orchestrator] Handle validation failure
  Action: Log validation error, notify observers, schedule next tick
  Output: Tick ends. No dispatch attempted.
  Final state: Waiting for next tick.

Step 3: [Orchestrator] Fetch candidate issues
  ...
```

### 6. Cross-Reference Density

- [ ] Every entity field lists every section where it's read or written
- [ ] Every config key lists every behavior it affects
- [ ] Every error lists every operation that can produce it
- [ ] Every state lists every transition that enters or exits it
- [ ] A dedicated Cross-Reference Index section exists

### 7. Config-Behavior Traceability

Every config key has:
- [ ] The exact list of behaviors it changes
- [ ] When changes take effect (immediate, next tick, next run, requires restart)
- [ ] What happens at the boundary values
- [ ] Interaction effects with other config keys (if any)

## Quality Comparison Table

| Aspect | SPEC Level | Blueprint Level |
|---|---|---|
| Field definition | Type + default | Type + default + validation + examples + cross-refs |
| Error handling | Named category + recovery strategy | Full catalog: code + message + trigger + recovery + blast radius |
| Algorithm | Pseudocode | Pseudocode + decision table + sequence diagram |
| Data shape | "Suggested shape" with key fields | Canonical shape with every field, every type, every possible value |
| State machine | States + transitions in prose | Full state × trigger matrix |
| Normalization | Rule description | Rule + 5-10 input→output examples including edge cases |
| Config | Key, type, default | Key, type, default, validation, reload behavior, behavioral impact trace |
| Testing | Test matrix bullets | Test matrix bullets + specific input→expected-output test cases |
