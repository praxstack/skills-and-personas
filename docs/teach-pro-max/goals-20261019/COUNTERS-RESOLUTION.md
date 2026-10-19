# Resolution of the two additional independent reviews

19 October 2026. These reviews are evidence leads, not instructions. They do not change the agreed general-teacher/C-adapter architecture, authorize rounds, or alter frozen evaluation. Only verified factual corrections are applied here.

## Claude counter 1: smoke evidence

Accepted; our earlier missing-evidence statement was wrong. The deleted worktree was not the only copy. The sibling `archive/v2.2-smoke/` contains all six lesson sources, routing outputs and reports. Fresh hash checks verify all six canonical lesson hashes and 83/83 recorded artifacts. Four builds pass their automatic gates and remain claims-pending; struct-padding crashes, and sum-loop-trace fails layout/pause-state checks. See SMOKE-VERIFICATION.json. Rebuild those reproducers after repairs to measure improvement, not to replace missing evidence.

## Counter 2: large archives in Git

Accepted as a storage-design improvement, not an instruction to rewrite history now. An ordinary unfiltered full clone fetches branch history; the archived binary objects add download/storage cost. Single-branch, shallow and filtered clones are exceptions, and wire bytes need not equal file sizes. [Git clone documentation](https://git-scm.com/docs/git-clone).

GitHub Release assets are the preferred proposed home for these immutable checkpoint binaries. [GitHub binary distribution guidance](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github#distributing-large-binaries). Keep manifests, hashes, provenance and fetch/verify instructions in Git. Migrating already-pushed blobs requires more than a new deletion commit. Before any cleanup: preserve current refs locally, upload and verify replacement assets, create the lean metadata version, inspect all remote refs that retain the binary commit, and obtain explicit approval for the exact branch/history rewrite. A release tag must point to a lean commit, otherwise the tag retains the same binary history. Do not rewrite main or unrelated branches, and do not promise erasure from existing public clones/caches. No migration, deletion, LFS conversion, release publication or history rewrite was performed.

## Counter 3: private test bank

Accepted as a necessary clarification. New withheld case bodies stay in an independent evaluator workspace outside the public repository and its archives/releases/bundles. Publish only the bank's digest, version, policy and appropriately redacted results. Local/private storage and evaluator access restrictions are fixed before generation; an instruction not to read public cases does not make them hidden. Previously published cases remain regression cases.

## Counter 4: evaluator ambiguity

Partly accepted, with a code correction to the counter. `mutation_claims.py:164-171` already requires an overall rejection AND rejection of the planted claim ID or a changed-text ID. That proposed ID rule is not new work. It does not establish that the mutation caused rejection when the same target also fails in its unchanged control.

Preserve existing frozen scores and their denominators. Independently audit the final baseline text and classify each control rejection as a content defect, false rejection or unresolved disagreement. Do not remove rejected controls from the denominator, call an unreviewed control valid, or automatically treat a 0-P1 audit as proof. Report paired-control/target outcomes separately. Any new scoring definition, eligibility rule, threshold or rubric change belongs in an independently reviewed, human-approved evaluator version before candidate implementation. Diagnostic adjudication is not permission to change acceptance mid-run.

## Counter 5: C budget

Four rounds are a reasonable alternative estimate, not an established necessity or an approved extension. The prior 3-C/8-general proposal remains a proposal; the counter's 4-C/8-general option is recorded for the budget decision. Privacy is still required and is not silently deferred. A verified nonsynced fixture/state root is a prerequisite for every test run; it cannot wait until the last privacy round. If establishing it requires a candidate code change, that change counts inside the approved budget. No round has been granted or started by this resolution.

## Counter 6: exact C baseline

Accepted. The public annotated tag `prax-teach-v2.2-rc1` peels to commit 2493c45c075c9db9ec0b7b7e44cdc9220f3de1e1. The restored-check commit is ae9b06fa151e2df75842fb9a0b4d77ac1ee0c84d. The chosen source snapshot a38becaee4e63b455105c394f825bce0fde420fa includes those restorations; package/lesson bytes do not differ from ae9b06f. The later goal/counter commits are planning/review records, not a different product baseline. Record all of these in the import receipt.

## The earlier routing/council session

Its useful lesson stands: inspect actual media, separate candidate and governing changes, retain stale-digest defects and do not call a text-only council an empirical audit.

Its branch-status claim is historical. The 15 edits are now committed and pushed as f4485c463f42c876a9e31615fb924598031b277f on `candidate/media-routing-20261018`; that worktree is clean. The commit explicitly says saved as found, not reviewed. Its validator/digest changes are not thereby accepted and must not be merged wholesale.

The original council brief explicitly prohibited tool use and supplied one author's framing. Agreement/rankings do not establish independent factual verification or changed minds. Its proposed timing estimates remain estimates.

That session's lack of media is not the present project's status: the preserved Atlas still, interactive page, narrated MP4 and captions exist, and later C outputs have real receipts. Do not start another redundant generic pilot. Test the selected current general-teacher path on the planned fresh qualitative lesson under the approved next run. Reversible observation is allowed; it does not reset an exhausted implementation budget.

## Current direction

Keep `skills/teacher/` as the general foundation, retain C as an optional adapter, and keep tracks independent. The additional reviews correct evidence and expose decisions; they do not replace the product goal or trigger automatic new work. Storage migration, new evaluator semantics and budgets remain approval items.
