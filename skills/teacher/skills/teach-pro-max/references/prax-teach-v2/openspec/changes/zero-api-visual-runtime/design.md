## Context

The candidate already contains the `prax-teach-v2` teaching engine, JSON/JSONL learner-state machinery, Markdown/HTML renderer, visual router, pinned dependencies, and release validator. It does not contain the separately versioned Zero-API Visual Lab described by the canonical plan. The implementation must fit the existing Python/Node repository, preserve the bundled static path, and never turn ChatGPT/Codex subscription access into a programmatic backend.

## Goals / Non-Goals

**Goals:**

- Build the smallest reusable local runtime that can express the three planned laboratories.
- Keep lesson specifications, receipts, manifests, and proof artifacts versioned and inspectable.
- Make no-network, deterministic, accessible, and fallback behavior mechanically testable.
- Produce evidence that is honest about engineering versus external learner outcomes.

**Non-Goals:**

- No embedded model, chatbot, API client, telemetry, cloud storage, or live theorem prover.
- No framework migration or replacement of the existing renderer.
- No automatic global installation or canonical replacement.
- No claim of field accessibility or improved human learning from fixtures.

## Decisions

### Local runtime boundary

Use a project-scoped TypeScript/standards-based Web Components runtime built into a deterministic static artifact. Keep the Python package for state/evidence operations and lesson-domain calculations. The runtime communicates with the host only through learner-controlled JSON receipts.

**Alternatives:** a React application would add a dependency and a second rendering model; a pure Python server would make the packaged offline artifact less portable; embedding host-model calls would violate the no-API boundary.

### Declarative lesson contracts

Represent lesson structure, states, actions, hints, graders, fallback content, and receipt fields in JSON Schema-validated documents. Keep domain calculations in small pure modules and keep UI components domain-neutral.

**Alternatives:** hard-coded lesson pages would be faster for one lesson but would fail the cross-domain reuse requirement; a general plugin framework would add abstraction before a second implementation proves it necessary.

### Static-first accessibility

Generate semantic HTML and a no-script/print route from the same lesson specification. Interactive controls progressively enhance the static sequence, and reduced motion disables animation without hiding meaning.

**Alternatives:** an interaction-only canvas would make keyboard, screen-reader, print, and answer-leakage review harder.

### Exact and structural grading only

Use exact graders for numeric, permutation, and interleaving invariants. Preserve ambiguous prose for host-tutor interpretation instead of inventing a local natural-language judge.

**Alternatives:** an embedded model would violate the zero-API boundary; opaque heuristic scoring would overstate learner evidence.

### One build-time Lean experiment

Pin Lean only for authoring/build verification, export proof states as data, and show a static equivalent. Decide keep/revert from a predeclared value threshold.

**Alternatives:** a live browser theorem prover would expand bundle size, supply-chain surface, and accessibility burden; adding TLA+, Alloy, Dafny, Agda, or F* now would be scope without a named lesson need.

### Evidence ledger and promotion gate

Keep the JSON tracker authoritative, generate Markdown/HTML views, bind evidence to exact bytes, and separate `ENGINEERING_COMPLETE / SCIENTIFIC_EVIDENCE_PENDING` from `UPGRADE_100_PERCENT_VERIFIED`. Human approval remains mandatory for promotion and external study actions.

**Alternatives:** treating a green test suite as proof of learning would contradict the existing claim policy.

## Risks / Trade-offs

- **Interactive/static drift** → build both routes from one lesson spec and test semantic parity.
- **Answer leakage through labels or hidden content** → keep transfer answers out of default markup and scan all generated assets.
- **Browser behavior differs from structure checks** → record browser and assistive-technology evidence separately; never promote automated checks to field claims.
- **Receipts become a second learner database** → keep them local, schema-bound, exportable, deletable, and limited to declared observations.
- **Runtime overfits the first lab** → require the same public components to power all three domain lessons before MVP closure.
- **Lean adds cost without learner value** → retain only when the predeclared experiment earns its threshold; otherwise remove the adapter.
- **Repository payload and generated HTML drift** → use deterministic manifests and fail closed on stale source hashes.

## Migration Plan

1. Freeze the current candidate and add the runtime under a separately versioned directory.
2. Build the floating-point pilot and prove the static fallback before adding other labs.
3. Add Rubik's and lost-update lessons using the same public components.
4. Run the bounded Lean experiment and retain or remove it by evidence.
5. Update tracker views, run independent exact-byte verification, and create a local archive/rollback receipt.
6. Keep the global `teach-pro-max` installation unchanged until a separate promotion approval.

Rollback is removing the runtime directory and its project-scoped dependencies, restoring the previous candidate commit/archive, and leaving the existing static renderer and tutor skill untouched.

## Open Questions

None. The canonical plan already fixes the runtime boundary, lesson domains, fallback, Lean scope, evidence labels, and promotion gates.
