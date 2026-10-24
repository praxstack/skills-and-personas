# Scoped portfolio and public-history decisions

Read-only inventory on 2026-10-24; no identities, refs, old receipts or installed releases changed.

Current `python3 scripts/portfolio_audit.py` collected 129 top-level entries / 115 names, 14 duplicate names, 20 lint failures, 126 heuristic link findings, zero collection errors. Its `passed` is false. This is current collection evidence, not a clean-portfolio claim. The audit excludes nested identities and archives; duplicate-tree-inventory.json expands the 14 reported pairs to full per-file SHA-256 manifests.

Of the 126 link findings, 122 originate in the embedded historical engine/reference or frozen attempt snapshots. They must retain their original bytes and receive contextual notes rather than repairs that falsify receipts. The four active-document findings were inspected: eiirp explicitly refers to an **upstream** script; teach-pro-max names two paths relative to its **resolved embedded engine**, where those files exist; PUBLIC-DISTRIBUTION.md has stale architecture wording and an unqualified OPERATIONS reference whose actual embedded file exists. Thus this set does not prove four missing runtime dependencies. Exact per-finding decisions are in link-triage.json. The active public-distribution documentation should be updated in a separate authorized documentation change, preserving the historical source snapshots.

One actual currently observable dependency problem is the unrelated transcript-pipeline regression import of `requests`: 9/10 portfolio tests pass; the tenth fails with ModuleNotFoundError. The provisioned teacher environment has the same result. A single `uv run --offline --with requests==2.34.2 --with pyyaml==6.0.3 ...` retry finds no cached requests distribution. No download or unrelated repair was performed.

## Lossless identity migration proposal

All 14 duplicate pairs are divergent. Their names are backend-pe, blueprint-creator, chronicle, concept-cartographer, constellation-team, frontend-pe, idea-capturer, lecture-alchemist, obsidian-cli, spec-creator, svg-logo-designer, techtutor, transcribe-refiner and transcript-pipeline. Neither directory wins by location or recency alone.

Prax (or an explicitly appointed domain maintainer) should approve each pair independently. Before any change, freeze both trees using the provided manifests, review behavioral differences, select a canonical future invocation, and record a versioned mapping from each old collection-qualified identity to that invocation. Keep original lineage, content hashes and schemas. Retain both old invocations as explicit aliases or preserved variants until round-trip/replay and rollback checks pass. A cosmetic name deduplication is insufficient. No acceptance criteria or rename were imposed by this inventory.

## Exact public-history review inventory

public-refs.tsv contains every head/tag and peeled tag observed using `git ls-remote --heads --tags origin` (17 heads; 6 tags plus peeled records). public-history-review-objects.tsv lists 765 reachable object/path pairs matching historical, evidence, release, private-evaluation or holdout path classes across the advertised tips; this is a **review inventory**, not a finding that each object is sensitive or should be removed. Exact hashes permit a human to make a scoped decision without altering evidence. Repository visibility was not independently checked; “public” here means remotely advertised refs. GitHub PR refs, release assets, forks, caches and external clones require a separately authorized provider inventory.

Proposed decision order: preserve immutable release/freeze tags and signed/hashed receipts; identify specific accidentally public private material, if any, by content review; approve an exact object/path/ref removal list; capture an offline backup and ownership mapping; then design the smallest history migration and updated provenance. Candidate/archive branches need separate retain/archive/delete decisions. Do not rewrite all history merely because 765 historical paths are reachable. No destructive action is authorized by this proposal, and none was executed.
