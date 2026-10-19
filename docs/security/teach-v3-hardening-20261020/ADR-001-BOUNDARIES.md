# ADR-001: centralize trust boundaries and keep evaluation frozen

Status: accepted for this repair branch
Date: 2026-10-20

## Context

The scan found repeated copies of the same missing controls: path containment, link handling, URL policy, credential scoping, resource budgets, and untrusted code execution. Claude's release review also found that distribution aliases and bundled references can drift from the canonical teacher. Patching only the reported string at each sink would leave sibling paths open.

## Decision

- Enforce each security invariant at the narrowest shared product boundary.
- Use reusable path, network, and private-file helpers instead of ad hoc checks.
- Keep the private evaluator, frozen policy, and historical evidence unchanged during product repair.
- Add focused ordinary regression tests for the repaired product boundaries; do not use them to rewrite prior acceptance scores.
- Treat `teacher` as the canonical general-teaching source and make compatibility entries explicitly subordinate to it.

## Consequences

- Some unsafe permissive behavior becomes a clear error.
- Product code gains small shared helpers and focused tests.
- Previous acceptance evidence remains historically accurate but does not certify the new candidate.
- A later read-only verification run can compare the candidate with both v3.0.0 and the frozen evaluator.

## Rejected alternatives

- Updating validators and product code in the same run: self-certifying and contrary to the identity-preservation policy.
- Fixing only literal `../` strings or URL prefixes: bypassable through absolute paths, encoded forms, links, redirects, or DNS changes.
- Declaring all lesson code trusted: incompatible with public skill installation and learner-supplied course inputs.
