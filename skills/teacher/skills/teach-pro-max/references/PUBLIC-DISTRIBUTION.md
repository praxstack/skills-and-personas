# Teach Pro Max public distribution

## Contents

1. [Architecture](#architecture)
2. [Naming and compatibility](#naming-and-compatibility)
3. [Evidence boundary](#evidence-boundary)
4. [Current visual-unification status](#current-visual-unification-status)
5. [Modification policy](#modification-policy)
6. [Repository documentation](#repository-documentation)

## Architecture

`teach-pro-max` is a public alias and portable policy layer around an embedded,
content-manifested `prax-teach-v2` engine.

```text
teach-pro-max/
├── SKILL.md                         public entrypoint
├── agents/openai.yaml               Codex UI metadata
├── scripts/verify_distribution.py   embedded-source verifier
└── references/
    ├── PUBLIC-DISTRIBUTION.md        this boundary
    ├── ENGINE-MANIFEST.json          file hashes and source commit
    └── prax-teach-v2/                complete embedded engine
```

The wrapper adds portable capability-adaptive execution, first-class visual
production, and explicit no-API, quota, authorization, and evidence rules. The
embedded engine remains the normative detailed teaching, state, visualization,
evaluation, and operations implementation. It includes the full inherited
Prax-Teach visualization handbook, portable 38-tool registry, and packaged Prax
Visual Lab; no second teaching skill is required for the visual route.

## Naming and compatibility

Use `teach-pro-max` for discovery and invocation. Preserve `prax-teach-v2` as an
internal lineage, persisted-schema, study-arm, package, and receipt identifier.

Do not bulk-replace the internal identifier. Content-addressed event IDs,
fixtures, schema namespaces, study allocation receipts, archive paths, and
immutable reviews depend on exact bytes. A cosmetic rewrite can silently break
integrity and migration behavior.

If a future release adopts new public identifiers internally, implement an
explicit versioned migration that preserves the original value alongside the
new value and proves round-trip, correction, deletion, and replay behavior.

## Evidence boundary

The embedded historical evidence is retained because it is part of the source
candidate and supports reproducible inspection. It applies only to the exact
embedded engine bytes and the limitations named in its `STATUS.md`.

It does not demonstrate:

- that wrapper policy was present during the historical evaluations;
- that the wrapper itself has an immutable release receipt;
- field accessibility conformance;
- better immediate or delayed human learning;
- generalization to every agent harness or model.

The repository-level documentation archive preserves the broader research,
failed attempts, upgrade plan, tracker, and original release archives without
injecting them into the wrapper's default context.

## Current visual-unification status

The source working-tree candidate fixes the product-level visualization route,
includes the packaged Prax Visual Lab, and adds the executable practical loop.
Focused routing, contract, runtime, renderer, registry, and Markdown/HTML gates
pass. Fresh forward-behavior attempt 21 passes 8/8 against 20 exact-byte
bindings, including the runnable practical trace. Older forward receipts remain
historical. Browser inspection passes on five named package pages, including
Prax Visual Lab. Three independent reviews and exact full verification pass for
the frozen embedded payload. Two clean-HEAD archives were byte-identical, and
the global installed copy matches this distribution manifest. This is the newly
reviewed engineering release; delayed human-learning and external-harness
claims remain outside the evidence boundary.

## Modification policy

Before modifying embedded files:

1. run `python3 scripts/verify_distribution.py` and preserve its output;
2. read the embedded `STATUS.md`, `references/OPERATIONS.md`, and relevant
   contract completely;
3. treat every existing receipt as historical after the first byte changes;
4. update `ENGINE-MANIFEST.json` only after focused and full gates pass;
5. record source, tests, review, hashes, known limitations, and rollback;
6. never use a wrapper rename to bypass the embedded release gate.

## Repository documentation

When working from the source repository, see:

```text
docs/teach-pro-max/README.md
docs/teach-pro-max/research/
docs/teach-pro-max/historical/
docs/teach-pro-max/releases/
docs/teach-pro-max/SOURCE-MANIFEST.json
```

These paths are publication documentation, not required runtime dependencies.
