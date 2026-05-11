# Self-Review Checklist: Blueprint

Run this checklist against the drafted Blueprint BEFORE presenting it to the user.

## Pass 1: Mechanical Translation Test

Pick 3 random sections (one from Entity Catalog, one from Error Catalog, one from Sequences).
For each, attempt a mental line-by-line translation into code:

- [ ] Can you write the data class/struct from the entity specification without ANY decisions?
- [ ] Can you write the error constructor from the error catalog entry without ANY decisions?
- [ ] Can you write the function body from the sequence steps without ANY decisions?

If any answer is no, that section needs more detail. Common gaps:
- Missing validation rule → you'd have to decide what's valid
- Missing error message template → you'd have to write the message
- Missing step in sequence → you'd have to decide what happens between steps

## Pass 2: SPEC Coverage Check

For every section in the SPEC:

- [ ] Is there a corresponding Blueprint expansion?
- [ ] If not expanded, is it explicitly marked "Carried from SPEC — no expansion required"?
- [ ] Are there SPEC sections that were accidentally skipped?

Count:
- SPEC sections total: ___
- Blueprint expansions: ___
- Carried without expansion: ___
- Unaccounted: ___ (these are gaps — fix them)

## Pass 3: Table Completeness

### Entity Catalog
For every entity:
- [ ] All fields have a row in the specification table
- [ ] Every row has: Type, Required/Optional, Default, Validation, Normalization
- [ ] Fields with complex validation have a dedicated detail block with examples
- [ ] Cross-reference table exists mapping fields to reader/writer sections

### Error Catalog
For every error:
- [ ] Has: Code, Message template, Variables, Trigger condition, Recovery, Blast radius,
  Operator visibility, Retryable flag, SPEC reference
- [ ] Message template contains variable slots (not hardcoded values)
- [ ] Trigger condition is exact (not "when something fails")

### Config Bible
For every config key:
- [ ] Has: Type, Required/Optional, Default, Source, Validation table, Dynamic reload,
  Behavioral impact, Interaction effects
- [ ] Validation table has at least 3 valid and 3 invalid examples
- [ ] Behavioral impact lists specific section references

### State Transition Matrix
- [ ] Every state appears as "Current State" in at least one row
- [ ] Every state appears as "Next State" in at least one row (or is explicitly initial/terminal)
- [ ] Every trigger that the SPEC mentions appears in the matrix
- [ ] Illegal transitions section exists
- [ ] Guard conditions are explicit (not just "if eligible" but what eligible means)

### Decision Tables
For every algorithm with branching:
- [ ] Every input combination has a row
- [ ] No empty cells
- [ ] Edge cases at decision boundaries have explicit rows

## Pass 4: Cross-Reference Integrity

- [ ] Entity → Sections index exists
- [ ] Config → Behavioral Impact index exists
- [ ] Error → Producer × Handler index exists
- [ ] Every cross-reference points to a section that actually exists
- [ ] No dangling references (section referenced but doesn't exist)

## Pass 5: Example Coverage

For every:
- Validation rule: at least 1 valid + 1 invalid example? [ ]
- Normalization pipeline: at least 3 examples (normal, edge, error)? [ ]
- Data transformation: at least 3 examples? [ ]
- API request/response: at least success + error example? [ ]
- Edge case table: at least 5 scenarios per subsystem? [ ]

## Pass 6: Consistency Check

- [ ] Entity field names are identical across Entity Catalog, Config Bible, Error Catalog,
  and Sequences (no `poll_interval` in one place and `polling_interval` in another)
- [ ] Error codes are identical across Error Catalog, Sequences, and Validation Compendium
- [ ] State names are identical across State Matrix, Sequences, and Error Catalog
- [ ] Section cross-references use the correct section numbers

## Pass 7: Orphan Detection

- [ ] No Blueprint detail that doesn't trace back to a SPEC section (orphaned detail means
  either the SPEC has a gap or the Blueprint is out of scope)
- [ ] No validation rule without a corresponding error (if validation can fail, where's the error?)
- [ ] No error without a trigger (if an error exists, what produces it?)
- [ ] No state without a transition (if a state exists, how do you get in and out?)
- [ ] No config key without behavioral impact (if a key doesn't affect behavior, why does it exist?)

## Review Summary Template

```markdown
## Self-Review Summary

**SPEC coverage:** {N}/{M} sections expanded, {K} carried without expansion
**Entities:** {N} entities, {M} total fields fully specified
**Config keys:** {N} keys fully specified with validation tables
**Errors:** {N} error catalog entries
**State transitions:** {N} rows in transition matrix, {M} illegal transitions documented
**Decision tables:** {N} created
**Sequences:** {N} fully specified with numbered steps
**Edge cases:** {N} documented across {M} subsystems
**Cross-references:** {Entity index: ✓/✗}, {Config index: ✓/✗}, {Error index: ✓/✗}
**Examples:** {N} total examples across all sections

**Gaps found and fixed during review:** {N}
  - {Description of each fix}

**Remaining [TBD] markers:** {N}
  - {Each TBD with what user input is needed}

**Confidence:** {Ready for implementation / Needs user input on N items}
```
