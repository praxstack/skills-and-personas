# Scope Calibration — decision tree

APEX-CORE calibrates rigor to task size. This is the most common violation: forcing 10-phase ceremony on a 5-line fix.

## Decision tree

```
Is the ask a single question with a known answer?
  YES -> TINY, answer directly, skip all phases
  NO  -> continue

Is the change < 10 LoC across ≤ 1 file and no new tests?
  YES -> TINY, one primitive cycle, skip phases
  NO  -> continue

Is the change 5-20 actions, 1-3 files, clear spec, no architectural impact?
  YES -> SMALL, Plan -> Execute -> Verify only (3 phases)
  NO  -> continue

Is the change 20-50 actions, multi-file, test changes, potentially breaking?
  YES -> MEDIUM, full 10-phase contract
  NO  -> continue

Is it >50 actions, new feature, architectural impact, or external dependencies added?
  YES -> LARGE, 10-phase + Council review gate at Plan phase
```

## Examples

### TINY — one primitive cycle

- "What does `find -mtime -7` do?" — answer directly.
- "Fix the typo in line 42 of README.md." — read, edit, confirm.
- "Run the test suite and paste the output." — `interact` + report.

### SMALL — Plan -> Execute -> Verify

- "Add a `--verbose` flag to the existing CLI." — 1-3 files, clear spec.
- "Rename this variable across the repo." — ast-grep-replace + test.
- "Add one new endpoint to the existing API." — clear scope.

### MEDIUM — full 10-phase

- "Implement the `ksum query` command per the CEO review plan." — multi-file, new logic, tests, docs.
- "Refactor the error-handling to thread ASI across retries." — crosscuts modules.
- "Add structured logging with correlation IDs." — observability, test changes.

### LARGE — 10-phase + Council

- "Design and implement a multi-model council deliberation pipeline." — new architecture.
- "Migrate from Celery to Arq." — external deps, multi-phase work.
- "Rewrite the auth layer to use JWT refresh tokens." — security-critical.

## Defaults on uncertainty

When the size sits between two classes, default to the SMALLER class. Over-scoping burns trust (phase ceremony on trivial work is a worse sin than skipping a phase on work that deserved it — the latter is visible and correctable, the former is frustrating).

## Scope drift mid-task

If during execution you realize the task is actually one size larger:

1. Emit `self_update` primitive with the scope-change note.
2. Write ASI: "upgrading scope TINY -> SMALL because Y".
3. Re-plan (jump back to Plan phase).
4. Inform the user in the next response.

If you realize the task is actually one size smaller, it is OK to downgrade mid-stream — but state the change explicitly to avoid jarring the user ("realized this is TINY, not SMALL — dropping the Plan phase and proceeding directly"). Note the initial mis-classification in Final Summary for future calibration. The real sin is hiding the downgrade, not doing it.
