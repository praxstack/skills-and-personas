# Section Templates: Canonical BLUEPRINT.md Structure

This document defines the canonical section structure for a Blueprint. Unlike the SPEC (which is
organized by system architecture), the Blueprint is organized by artifact type — all entities
together, all errors together, all sequences together. This makes it easier for an implementing
agent to find everything about one aspect without jumping between sections.

## Header

```markdown
# [System Name] Implementation Blueprint

Status: Draft v1
Derived from: SPEC.md v[N] ([link or path])
Purpose: Exhaustive implementation detail for [System Name]. Every validation rule, error message,
edge case, and sequence is fully specified. An AI coding agent should be able to implement the
system by mechanically translating this document into code.

## Notation

- **Required field:** Must be present; absence is a validation error
- **Optional field:** May be absent; default value applies when absent
- **Cross-ref:** Section references use [§N.M] notation
- **[TBD]:** Detail pending user input — cannot implement until resolved
```

---

## Section 1: Document Scope

Brief section (5-10 lines). What this Blueprint covers, what it doesn't, and its relationship
to the SPEC.

```markdown
## 1. Document Scope

This Blueprint expands SPEC.md into exhaustive implementation detail for [System Name].

**Covered:** Every entity field, every config key, every error, every state transition, every
sequence, and every edge case needed to implement a conforming [System Name].

**Not covered:** [Anything intentionally omitted — e.g., deployment, infrastructure, monitoring
dashboards beyond what the SPEC requires]

**Relationship to SPEC:** This Blueprint is a strict expansion of the SPEC. It adds granular
detail but does not change any SPEC-level decision. If the Blueprint and SPEC appear to conflict,
the SPEC takes precedence and the Blueprint should be corrected.

**Sections carried from SPEC without expansion:**
- Problem Statement (SPEC §1)
- Goals and Non-Goals (SPEC §2)
- [Other sections that don't need expansion]
```

---

## Section 2: System Context

Carried from SPEC with minimal expansion. Add only if the SPEC's system overview needs
clarifying detail for implementation.

---

## Section 3: Entity Catalog

The heart of the Blueprint. Every entity, every field, fully specified.

```markdown
## 3. Entity Catalog

### 3.1 [Entity Name]

[One-line description from SPEC]

SPEC reference: §4.1.N

| Field | Type | Req/Opt | Default | Validation | Normalization | Notes |
|---|---|---|---|---|---|---|
| `id` | string | required | — | Non-empty | None | Stable tracker-internal ID |
| `identifier` | string | required | — | Non-empty, matches `[A-Za-z0-9._-]+` after sanitization | None | Human-readable ticket key |
| `title` | string | required | — | Non-empty | None | |
| `description` | string or null | optional | null | — | None | |
| `priority` | integer or null | optional | null | If present: positive integer; non-integer coerces to null | Non-integer → null | Lower = higher priority |
| `labels` | list of strings | optional | [] | — | Each label → trim → lowercase | |
| ... | ... | ... | ... | ... | ... | ... |

#### Field Details (where the table isn't enough)

**`priority` normalization:**
```
Input        → Output   Rationale
────────────────────────────────────
1            → 1        Valid integer
4            → 4        Valid integer
0            → 0        Valid (but sorts after 1-4)
null         → null     Missing priority
"high"       → null     Non-integer string → null
3.5          → null     Float → null (do not truncate)
-1           → -1       Negative is unusual but not invalid per schema
```

**`blocked_by` derivation:**
```
Source: Issue relations where relation.type == "blocks" (inverse)
For each such relation:
  blocker = {
    id: relation.issue.id or null,
    identifier: relation.issue.identifier or null,
    state: relation.issue.state.name or null
  }
If no blocking relations exist: blocked_by = []
```

#### Cross-References

| Field | Read by | Written by |
|---|---|---|
| `id` | §5 (Orchestrator state keys), §7.2 (Reconciliation) | §7.1 (Tracker fetch) |
| `state` | §5.2 (Dispatch eligibility), §5.5 (Reconciliation) | §7.1 (Tracker fetch), §5.5 (State refresh) |
| ... | ... | ... |
```

---

## Section 4: Configuration Bible

Every config key, fully specified.

```markdown
## 4. Configuration Bible

### 4.1 Config Key: `tracker.kind`

SPEC reference: §5.3.1, §6.4

| Attribute | Value |
|---|---|
| Type | string |
| Required | Yes (for dispatch) |
| Default | None |
| Supported values | `"linear"` |
| Source | YAML front matter: `tracker.kind` |
| Dynamic reload | Yes — affects future dispatches |

**Validation:**
| Input | Valid? | Behavior |
|---|---|---|
| `"linear"` | Yes | Use Linear adapter |
| `"Linear"` | No | Validation error (case-sensitive) |
| `"github"` | No | `unsupported_tracker_kind` error |
| `""` | No | Treated as missing → validation error |
| `null` / absent | No | Dispatch preflight fails |

**Behavioral impact:**
- Determines which tracker adapter is used for all issue operations [§7]
- Controls which config keys are required (e.g., `tracker.project_slug` required when kind=linear)

---

### 4.2 Config Key: `tracker.api_key`
...
```

---

## Section 5: State Transition Matrix

Full state × trigger grid.

```markdown
## 5. State Transition Matrix

### 5.1 Issue Orchestration States

SPEC reference: §7.1

| Current State | Trigger | Guard | Action | Next State | Side Effects |
|---|---|---|---|---|---|
| ... | ... | ... | ... | ... | ... |

### 5.2 Run Attempt Lifecycle

SPEC reference: §7.2

| Current Phase | Trigger | Next Phase | Error Handling |
|---|---|---|---|
| PreparingWorkspace | workspace ready | BuildingPrompt | workspace_error → Failed |
| BuildingPrompt | prompt rendered | LaunchingAgentProcess | template_error → Failed |
| ... | ... | ... | ... |

### 5.3 Illegal Transitions

| From | To | Why Illegal | How Prevented |
|---|---|---|---|
| ... | ... | ... | ... |
```

---

## Section 6: Sequence Specifications

Numbered step-by-step for every major operation.

```markdown
## 6. Sequence Specifications

### 6.1 Sequence: Service Startup

SPEC reference: §16.1

Actors: CLI, Orchestrator, WorkflowLoader, Tracker, WorkspaceManager
Trigger: CLI invocation
Preconditions: Host environment has required executables and credentials

Steps:
1. [CLI] Parse arguments (optional workflow path, optional --port)
   ...

### 6.2 Sequence: Poll Tick
...

### 6.3 Sequence: Worker Run Attempt
...

### 6.4 Sequence: App-Server Session Handshake
...
```

---

## Section 7: Integration Specifications

Per external system, with exact request/response examples.

```markdown
## 7. Integration Specifications

### 7.1 Linear: fetch_candidate_issues

SPEC reference: §11.1, §11.2

#### Request
...

#### Response (Success)
...

#### Response (Error cases)
...

#### Normalization Pipeline
...
```

---

## Section 8: Error Catalog

Every error, fully specified.

```markdown
## 8. Error Catalog

### 8.1 Configuration Errors

#### MISSING_WORKFLOW_FILE
| Attribute | Value |
|---|---|
| Code | `missing_workflow_file` |
| Message | `Workflow file not found: {path}` |
| Variables | `path` (string): the resolved file path that was tried |
| Trigger | Workflow loader cannot read file at resolved path |
| Recovery | Startup: fail. Reload: keep last known good. Per-tick: skip dispatch. |
| Blast radius | System-wide — no dispatch possible |
| Operator visibility | ERROR log + startup failure exit code |
| Retryable | Yes (on next tick or reload, if file appears) |
| SPEC reference | §5.5 |

#### WORKFLOW_PARSE_ERROR
...

### 8.2 Tracker Errors
...

### 8.3 Agent Session Errors
...
```

---

## Section 9: Validation Rules Compendium

All validation rules in one place, organized by when they run.

```markdown
## 9. Validation Rules Compendium

### 9.1 Startup Validation
| Rule | Field/Condition | On Failure |
|---|---|---|
| Workflow file loadable | File exists at path | Fail startup |
| tracker.kind present | Non-empty string | Fail startup |
| ... | ... | ... |

### 9.2 Per-Tick Dispatch Validation
...

### 9.3 Per-Field Validation (Config)
...

### 9.4 Per-Field Validation (Domain Entities)
...
```

---

## Section 10: Algorithm Detail

Expanded pseudocode + decision tables.

---

## Section 11: Edge Case Encyclopedia

Organized by subsystem.

```markdown
## 11. Edge Case Encyclopedia

### 11.1 Workspace Edge Cases

| Scenario | Input State | Expected Behavior | Rationale |
|---|---|---|---|
| Workspace dir exists but is a file | Path exists as regular file | Replace or fail per implementation | SPEC §9.2 |
| Workspace dir exists but is a symlink | Symlink at path | Resolve and validate containment | Safety invariant |
| ... | ... | ... | ... |

### 11.2 Concurrency Edge Cases
...

### 11.3 Timing Edge Cases
...
```

---

## Section 12: Cross-Reference Index

```markdown
## 12. Cross-Reference Index

### Entity → Sections

| Entity | Defined in | Used in |
|---|---|---|
| Issue | §3.1 | §4 (config), §5 (states), §6.2 (sequences), §7 (integration), §8 (errors) |
| ... | ... | ... |

### Config Key → Behavioral Impact

| Config Key | Sections Affected |
|---|---|
| `polling.interval_ms` | §6.2 (tick scheduling), §5.1 (state: poll interval update) |
| ... | ... |

### Error → Producer × Handler

| Error Code | Produced By | Handled In |
|---|---|---|
| `missing_workflow_file` | §6.1 (startup), §6.2 (per-tick) | §8.1, §9.1, §9.2 |
| ... | ... | ... |
```

---

## Section 13: Implementation Checklist

More granular than the SPEC's checklist. Each item traces to a Blueprint section.

```markdown
## 13. Implementation Checklist

### 13.1 Core Conformance

- [ ] Entity: Issue — all fields typed and validated per §3.1
- [ ] Entity: Issue — `priority` normalization handles all cases in §3.1 table
- [ ] Entity: Issue — `labels` normalized to lowercase per §3.1
- [ ] Config: `tracker.kind` validated case-sensitively per §4.1
- [ ] Config: all $VAR resolution handles empty-string-as-missing per §4.2
- [ ] State: all transitions in §5.1 matrix implemented
- [ ] State: all illegal transitions in §5.3 are prevented
- [ ] Error: all §8 catalog entries produce correct codes and messages
- [ ] Sequence: startup (§6.1) follows exact step order
- [ ] ...

### 13.2 Extension Conformance
...

### 13.3 Pre-Production Validation
...
```
