# Shared contract for the next Prax Teach work

Status: proposed goal brief. No implementation goal is armed by publishing this file. It does not approve a new iteration budget, install anything, or amend an existing frozen evaluator.

## Product Manager

Build the general teacher the user requested: complete explanations that build intuition across subjects and levels, with useful stills, interactive explorers, layered Q&A, flashcards, narrated video and interactive video. Support a single lesson and a course the learner can resume. Practice is optional unless explicitly requested. Select tools by what they explain, not by tool count.

Use the general engine already in `skills/teacher/` and the compatible `skills/teach-pro-max/` entry. Do not create a fourth teacher or replace it with the C compiler. The C compiler is an optional domain adapter.

## Principal Engineer, checkpoint 1

Read `archive/teach-pro-max-evolution-20261019/README.md` and `REVIEW.md`, then fetch and inspect the current remote teacher before selecting implementation paths. The public remote already contained teacher commit e1d196e74ed88df3f5cdce8a06390331f9862300 when these prompts were drafted. Earlier local-only reviews do not establish the state of that newer code.

Before candidate edits, record the exact baseline commits, current accepted version, artifact inventories, mutable/protected paths, evaluator versions, withheld cases, thresholds, approved iteration budget, two-no-gain stop rule and rollback commands. Freeze evaluator changes in a separate, human-approved governing version. Implementation never edits that version to accommodate failures. Keep receipts outside the bytes they attest to. Reuse the historical baseline and Atlas, and keep old failures visible.

The existing v2.2 budget is exhausted. Approval for a new run must be explicit. Do not infer it from this prompt-drafting/preservation task. Claude's earlier estimate of two repair rounds plus one spare is a proposal, not an authorization. No Codex implementation-round cap was supplied. A missing budget or required governing approval is a blocker to implementation, not permission to invent one.

## Ownership and sequencing

- Codex owns general product integration, `skills/teacher/**`, `skills/teach-pro-max/**`, its new general checks and `deliverables/teach-pro-max/codex/**`.
- Claude owns the restored development source at `projects/prax-teach-c-adapter/**`, its C checks and `deliverables/teach-pro-max/claude/**`. Restore `candidate-source.tar.gz` into a new directory, then move its `prax-teach-v2.2` subtree into that project path without editing the archival payloads. Before coding, capture that import as the C baseline commit.
- Each works in a separate worktree/branch. Neither edits the other's paths. Shared contracts and evaluator changes go through the approved governing version. Codex is the integration owner; Claude hands off a commit, build outputs and receipts. No concurrent builds or setup against shared mutable tool/state directories.
- Installed skill links, the accepted general package, the C study workspace, Drive settings/data, archived snapshots and human-owned policies are protected. Do not install, flip links, upload learner records or change sync configuration.
- Optional host-native agents can review bounded work. Do not require a particular model/API, secretly automate consumer chat as an API, or claim consensus proves truth.

## Common evidence rules

Deliver artifact sources, built files and reproduction commands. Record exact code/lesson/artifact hashes, actual exit codes, failures and skips in each owner's REPORT.md. Outputs must be kept outside skill directories and outside the data whose hashes a receipt describes. A skipped required check is not a pass. Never weaken, skip, remove or edit frozen checks to obtain a pass; propose a separately approved version if a check is wrong.

For factual correctness, bind each claim to its example, assumptions, parameter range and source. Standalone cards and excerpts must retain necessary context. Do not solve scope ambiguity by making every sentence repeat a filename or by removing contrary programs from a review job. Compute quantities where computation is appropriate; use traceable sourced evidence for qualitative subjects. LLM reviews are findings, not proofs.

For visuals, inspect actual renders at 1440 px and 390 px, light and dark where supported. Compare against the preserved Atlas and current accepted output. Use readable mechanism-led layouts, exact technical labels, keyboard-accessible controls, captions/transcript and static fallback. Aesthetic ratings cannot establish truth or user acceptance. Deliver as review-ready and explicitly mark Prax's visual acceptance pending.

Use a verified nonsynced root for test learner data and all explicit fixture roots, not just TMPDIR. Detection overrides do not prevent a sync client from copying files. Deletion claims must distinguish workspace removal, observed aliases and unknown remote copies. Read-only paths must preserve state/metadata after consent withdrawal.

## Principal Engineer, checkpoint 2

At completion, each owner compares the candidate with both original and currently accepted baselines. Run the frozen commands on the final immutable inputs, show output in the transcript, preserve the full raw reports and mark each promised deliverable pass/fail/not-run. No partial suite or canary label substitutes for full required acceptance.

## DevOps/SRE

Commit named paths on the owner's branch. Verify the remote branch SHA after an authorized push. Hand off the exact commit and restoration instructions. Installation, deployment and final visual approval remain separate.

## Stop rule

Use the newly approved finite budget. Stop after two consecutive candidates with no held-out improvement, at the approved cap, or when a required human decision blocks progress. Preserve the current work and report the unmet criteria. Stopping does not mean the goal was achieved; never change the goal to declare completion.
