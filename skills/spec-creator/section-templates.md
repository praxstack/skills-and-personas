# Section Templates: Canonical SPEC.md Structure

This document defines the canonical section structure for a Symphony-grade SPEC.md. Not every
section applies to every system — adapt to the task. But never omit a section without consciously
deciding it's irrelevant.

## Header and Metadata

```markdown
# [System Name] Service Specification

Status: Draft v1 (language-agnostic)

Purpose: [One sentence describing what this spec defines]
```

---

## Section 1: Problem Statement

**What belongs here:**
- The concrete operational problem this system solves (not aspirational)
- 3-5 specific problems it addresses, as a bulleted list
- Important boundaries — what the system IS and IS NOT
- Trust/safety posture overview if relevant

**Template:**
```markdown
## 1. Problem Statement

[System] is a [type of system] that [primary action].

The service solves [N] operational problems:

- [Problem 1: specific, operational]
- [Problem 2: specific, operational]
- [Problem N: specific, operational]

Important boundary:

- [System] is [what it IS].
- [What it is NOT] is handled by [where that responsibility lives].
```

**Quality check:** Can someone read just this section and understand what to build and what NOT to
build?

---

## Section 2: Goals and Non-Goals

**What belongs here:**
- Goals: verifiable behaviors the system must exhibit
- Non-Goals: explicit exclusions with reasoning

**Template:**
```markdown
## 2. Goals and Non-Goals

### 2.1 Goals

- [Verifiable behavior 1]
- [Verifiable behavior 2]

### 2.2 Non-Goals

- [Excluded capability 1]. ([Why it's excluded or where it lives instead])
- [Excluded capability 2].
```

**Quality check:** Every goal can be tested with a yes/no question. Every non-goal explains why.

---

## Section 3: System Overview

**What belongs here:**
- Main components with one-sentence descriptions
- Abstraction layers
- External dependencies

**Template:**
```markdown
## 3. System Overview

### 3.1 Main Components

1. `Component Name`
   - [One-sentence responsibility]

2. `Component Name`
   - [One-sentence responsibility]

### 3.2 Abstraction Levels

1. `Layer Name` (role)
   - [What lives here]

### 3.3 External Dependencies

- [Dependency 1]: [What it provides, version/protocol expectations]
- [Dependency 2]: [What it provides]
```

---

## Section 4: Core Domain Model

**What belongs here:**
- Every entity with typed fields
- Normalization rules
- Stable identifiers and derivation rules
- Relationships between entities

**Template:**
```markdown
## 4. Core Domain Model

### 4.1 Entities

#### 4.1.1 [Entity Name]

[One-sentence description of what this entity represents]

Fields:

- `field_name` (type, required/optional)
  - [Semantic meaning]
  - [Default if optional]
- `field_name` (type or null)
  - [Semantic meaning]

#### 4.1.2 [Entity Name]
...

### 4.2 Stable Identifiers and Normalization Rules

- `Identifier Name`
  - [Derivation rule or source]
  - [Usage context]
- `Normalized Field`
  - [Normalization rule: trim + lowercase, character replacement, etc.]
```

**Quality check:** Could an agent generate a data class/struct from this section alone?

---

## Section 5+: Domain-Specific Contract Sections

These sections vary by system type. Common patterns:

### For services with configuration files:
```markdown
## N. [Config File] Specification (Repository Contract)

### N.1 File Discovery and Path Resolution
### N.2 File Format
### N.3 Schema
  #### N.3.1 `section` (object)
    - `field` (type) — Default: `value`
### N.4 Validation and Error Surface
```

### For services with APIs:
```markdown
## N. API Specification

### N.1 Endpoints
  #### N.1.1 `METHOD /path`
    - Request: [shape]
    - Response: [shape]
    - Errors: [codes and meanings]
### N.2 Authentication
### N.3 Rate Limiting
### N.4 Versioning
```

### For services with protocols:
```markdown
## N. Protocol Specification

### N.1 Transport
### N.2 Message Format
### N.3 Handshake Sequence
### N.4 Message Types
### N.5 Error Handling
```

---

## Configuration Specification Section

**What belongs here:**
- Source precedence and resolution semantics
- Dynamic reload semantics
- Dispatch/startup validation
- Config cheat sheet (flat, scannable)

**Template:**
```markdown
## N. Configuration Specification

### N.1 Source Precedence and Resolution Semantics

Configuration precedence:

1. [Highest priority source]
2. [Next source]
3. [Defaults]

### N.2 Dynamic Reload Semantics

- [What triggers reload]
- [What changes take effect immediately vs. requiring restart]
- [What happens on invalid reload]

### N.3 Validation

Startup validation:
- [What's checked and when]

Per-operation validation:
- [What's re-validated and when]

### N.4 Config Fields Summary (Cheat Sheet)

- `key.path`: type, default `value`
- `key.path`: type, default `value`
```

**Quality check:** Could an agent implement the entire config layer from just the cheat sheet?

---

## State Machine Section

**Template:**
```markdown
## N. State Machine

### N.1 [Entity] States

1. `State Name`
   - [When the entity is in this state]

2. `State Name`
   - [When the entity is in this state]

### N.2 Lifecycle Phases

1. `Phase Name`
2. `Phase Name`
...

### N.3 Transition Triggers

- `Trigger Name`
  - [What happens: which state transitions occur]

### N.4 Idempotency and Recovery Rules

- [Serialization strategy]
- [Duplicate prevention]
- [Restart recovery approach]
```

---

## Failure Model Section

**Template:**
```markdown
## N. Failure Model and Recovery Strategy

### N.1 Failure Classes

1. `Failure Category`
   - [Specific error 1]
   - [Specific error 2]

### N.2 Recovery Behavior

- [Category] failures:
  - [Recovery strategy]
  - [Impact on other operations]

### N.3 Partial State Recovery (Restart)

After restart:
- [What state is lost]
- [How the system recovers]

### N.4 Operator Intervention Points

- [How operators can influence behavior]
```

---

## Reference Algorithms Section

**Template:**
```markdown
## N. Reference Algorithms (Language-Agnostic)

### N.1 [Algorithm Name]

\```text
function algorithm_name(params):
  step_1
  step_2

  if condition:
    action_a
  else:
    action_b

  for item in collection:
    process(item)

  return result
\```
```

Use `text` code blocks, not a specific language. Use descriptive function/variable names.

---

## Test and Validation Matrix Section

**Template:**
```markdown
## N. Test and Validation Matrix

Validation profiles:

- `Core Conformance`: required for all implementations
- `Extension Conformance`: required only for optional features that are shipped
- `Real Integration Profile`: environment-dependent, recommended before production

### N.1 [Spec Section Name]

- [Specific testable behavior from the spec]
- [Specific testable behavior from the spec]
- If [optional feature] is implemented, [specific testable behavior]
```

**Quality check:** Does every bullet correspond to a specific, verifiable behavior in the spec?

---

## Implementation Checklist Section

**Template:**
```markdown
## N. Implementation Checklist (Definition of Done)

### N.1 Required for Conformance

- [Capability/behavior 1]
- [Capability/behavior 2]

### N.2 Recommended Extensions (Not Required)

- [Optional capability 1]
- TODO: [Future enhancement]

### N.3 Operational Validation Before Production (Recommended)

- [Pre-production check 1]
- [Pre-production check 2]
```
