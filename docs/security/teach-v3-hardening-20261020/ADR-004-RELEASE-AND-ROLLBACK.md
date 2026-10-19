# ADR-004: immutable releases and rollback targets

Status: accepted for this repair branch
Date: 2026-10-20

## Context

The active v3 installation lives in an immutable release directory, but its
rollback manifest points the previous `teach-pro-max` link at a mutable Git
working tree. That working tree advanced after activation, so rollback would
restore v3-era bytes instead of the actual pre-activation version. The public
release also let source, ZIPs, aliases, and integrity manifests drift.

## Decision

- Every activation copies both the new version and every restorable previous
  version into content-addressed or commit-addressed release directories.
- Rollback manifests point only to those immutable snapshots or record
  `missing`; they never point to a branch checkout.
- Release generation produces aliases, ZIPs, hashes, manifests, and install
  instructions from one staged tree, then verifies a clean standalone install.
- Historical release evidence is immutable. Corrections are additive errata.

## Consequences

- Rollback remains valid after repositories move or advance.
- Releases need a staging and verification step before activation.
- A repaired rollback manifest is an operational fix and is verified
  separately from this source branch.
