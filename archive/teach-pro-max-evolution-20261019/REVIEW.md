# Independent v2.2 review and integration handoff

Reviewed 19 October 2026. Candidate HEAD: a38becaee4e63b455105c394f825bce0fde420fa. This is an audit and proposed allocation of work, not approval of a new implementation budget or a change to frozen evaluation. No product code, installed skill links, evaluator, Drive settings or Drive data were changed.

## Answer

The work belongs to the Prax Teach / Teach Pro Max evolution, but there is no installed skill named prax-reach-promax. The exact general entry is teach-pro-max. It currently resolves to a different implementation from installed prax-teach-v2. Claude's v2.2 remains a separate, uninstalled C/DSA candidate.

The concern about C focus is confirmed by current files, not inferred from the user's account. FREEZE-v2.md calls the objective unchanged but explicitly limits it to C and DSA. Its authoring schema requires C programs and only permits language c. This is a scope/specification problem. It is not evidence that Claude is inherently incapable of general teaching or that model replacement alone would improve the product.

The narrowing is reversible. Preserve useful C work as an optional domain adapter; recover the general teacher from the accepted general contract rather than rewriting everything.

## Preservation

- Current candidate repository is clean and fully committed at a38beca. Tags v2.1-rc1, freeze-v2 and v2.2-rc1 exist.
- v2.2-source.bundle contains all candidate source history, branches and tags; git bundle verify passed.
- v2.1-rc1 and v2.2-final lesson archives remain intact. Every payload listed in their SHA256SUMS matches. Each manifest incorrectly includes a stale hash of itself; historical manifests were not modified.
- PRESERVATION.json is an external, independently generated inventory of archived files and source bundle. It avoids the self-hash problem and records the source commits.
- installed-general-v2.tar.gz preserves the currently installed general prax-teach-v2, including hidden files. This directory is untracked in its surrounding skill-library repository; it was saved explicitly rather than quietly committed into that unrelated repository.
- teach-pro-max-current.tar.gz preserves the currently installed wrapper and embedded implementation. Its scoped source is already committed and clean at be26eb8f6ec65932adfec138b2cddbe0a5d64b48.
- Reinstallable 4.4 GB .state tool/model caches were not duplicated. The source, committed reviews and four archived lesson outputs are preserved. Do not call missing smoke-test outputs preserved: the cited .state/wt/smoke worktree no longer exists and raw smoke reports were not found by this audit.

## Which skill is which

| Entry | Actual target and behavior |
|---|---|
| teach-pro-max | /Users/prax/Developer/skills-and-personas-recovery-20261016/skills/teach-pro-max; general topics/course/host routing, but wrapper and embedded old engine retain prediction-first behavior |
| prax-teach-v2 | /Users/prax/.agents/skill-library/prax-teach-v2; general, explanation-first, optional practice, course map and host-adaptive visualization |
| prax-teach | /Users/prax/.agents/plugins/agent-stack/skills/prax-teach; separate general teaching-workspace skill |
| Claude v2.2 candidate | /Users/prax/Developer/prax-teach-evaluation-20261016/v2.1/package/prax-teach; uninstalled C-oriented compiler and teaching protocol |

These are parallel branches of behavior, not one automatically synchronized engine. Changing a label or installing v2.2 over the general engine would not integrate them.

## Independently supported progress

- All four canonical lesson hashes and package hash match final receipts. All 214 artifact hashes match. Main reports match archived final reports.
- Full claims receipts support 41/41 planted errors caught (16 value, 25 claim), 0/41 controls accepted and 12/12 lesson-review rejections. All four lessons fail full acceptance.
- Earlier Track A control acceptance of 1/41 and final 0/41 are different runs, not a contradiction.
- Saved selftest supports 287 passed / 2 failed / 1 not-run before two check restorations. There is no fresh complete post-restoration suite pass. Neuron additionally fails the restored ReLU sync check.
- Both live tutor flows have raw passing receipts. The IVE now has practice=false by default, and optional Q&A practice follows the explanations.
- The new one-byte and factorial stills were directly inspected: landscape, mechanism-led, substantially better than the old tall pages. All four integer bytes and eight double bytes are drawn; factorial returns flow upward. Preserve these assets.
- The two identified weakened checks were restored in ae9b06f. This supports those corrections, not automatic approval of every gate change.

## Important remaining defects

### 1. Generality remains blocked

FREEZE-v2.md:9-11 limits the objective to C/DSA. package/prax-teach/SKILL.md:3 and its authoring steps require C/C17. schemas/lesson.schema.json:8-20,38-60 requires programs, only allows c, and explicitly says other subjects still obtain values from C runs. LESSON-MODEL.md:86-89 starts from a small C program. The explorer dispatch still falls back to a switch-specific implementation. Course language maps toward a full media pack rather than a general sequence/resume system.

The six smoke requests are also programming requests. Even perfect results would not demonstrate biology, history, language or another non-code teaching domain.

### 2. Installed general engines disagree

The accepted installed prax-teach-v2 .engine/SKILL.md:8-43 delivers complete explanations first. teach-pro-max makes its own older embedded SKILL normative; that copy:43-47 ends the first turn after prediction/diagnosis. The wrapper repeats prediction at SKILL.md:83-86.

The proper repair is versioned reconciliation of the general engine and wrapper, with distribution verification and rollback, not swapping a C compiler into the general slot.

### 3. Review reliability is still unmeasured

Rejecting every flawed lesson/control can be correct. It does not establish discrimination between good and bad content. The mutation catch code checks rejection of planted text, not whether the mutation uniquely caused rejection. With all controls rejected, 41/41 cannot establish calibrated error detection on otherwise valid material.

Verdict agreement is real; item disagreements remain switch 1, byte 4, factorial 6, neuron 8. Use independently adjudicated valid controls and source-grounded negative cases. Do not equate three agreeing reviewers with truth.

### 4. Actual wording failures remain

The independent review records eight P1 findings, including cast-as-object wording, an incorrect causal explanation of binary64 rounding and unscoped program claims. These are not eight wrong numeric outputs. The audit independently reproduced the binary64 tie and counterfactual behavior, supporting that conceptual error.

A blanket requirement to prefix every sentence with a filename would damage explanatory prose. Bind claims structurally to their program, view, example or parameter range; make standalone cards and excerpts self-contained. Review jobs must preserve that context and carry necessary diagnostics/control specifications. Arbitrarily excluding variant programs to obtain passes is not a remedy.

### 5. Privacy claims remain broader than implementation

ptk/selftest.py:55-57 disables sync detection with PRAX_TEACH_SYNC_ROOTS='', but host.py still puts fixtures beneath repo .state. That is not filesystem isolation from a real sync client.

The sync notice says copies go to Google within seconds; evidence previously established staging, not upload timing or completed remote retention. Deletion still returns all_state_deleted in some paths when no staging match is found, although copies/remote objects remain unknown. Normal CLI withdrawn reads improved, but direct API metadata defaults, lock timing and transaction recovery remain exceptions.

Keep creation consent separate from local deletion. Use a genuinely nonsynced fixture root, and describe the local deletion boundary honestly. No Drive settings/data should be changed during this repair.

### 6. Explanation-first still has a close-rule contradiction

Current references/TEACHING.md:28-31, under all modes, still requires an observed evidence item before satisfied learners can close normally. It should allow satisfaction/stop without claiming measured mastery. The latest report itself lists remaining locked IVE explore controls and other flow issues; the passing tutor transcripts do not cover every artifact path.

### 7. Smoke evidence and usability are incomplete

The 4/6 smoke result is recorded in reviews/v2.2-smoke.md, but its cited worktree/build reports are absent. It is a reported result, not a raw result independently revalidated in this audit. The report nonetheless identifies credible concrete failures: plain struct still projection crashes and loop state matching fails. It also documents conflicting optional schema fields, undocumented width limits, contradictory Q&A routing and mandatory storyboard overhead for cards.

Preserve fresh smoke outputs and their receipts next time. Do not rerun now solely to replace missing evidence under an exhausted budget.

## Recommended ownership

Codex: own product scope, integration, canonical general contract, wrapper reconciliation, capability/adapter boundary, non-code transfer example, and final evidence reconciliation.

Claude: retain bounded C-domain ownership: fix C claims and their scope, compiler diagnostics, mathematical explanations, C-specific still/loop defects, and add source-grounded regression examples. Keep changes in an isolated candidate with named files and no evaluator edits or installed-link changes.

Independent review: inspect integrated artifacts and code after convergence, using fixed inputs. Review can use available authorized agents without making a particular model a correctness authority.

Do not run both writers against the same lesson JSON, shared tool install or output directory. One integration owner merges and builds the accepted candidate. No message was sent to the separate Claude session by this audit.

## Smallest proposed next milestone

A reviewable general teaching vertical slice, preserving the existing renderer rather than replacing it:
1. Version the corrected general contract and acceptance before candidate work, carrying the original baseline/rollback and explicit budget/stop rule.
2. Reconcile teach-pro-max with the accepted explanation-first engine; retain quick/lesson/course, optional state, host-native fallback and learner-led exploration.
3. Treat C capture as an optional evidence adapter; support a lesson from sourced prose/diagrams or calculation without mandatory C scaffolding.
4. Deliver one non-code visual lesson through that same path, with accessible static fallback and optional practice. Use the existing C exemplar for regression.
5. Repair the scoped C and consent defects without weakening acceptance. Preserve reports and exact built artifacts.
6. One final fixed evaluation and visual comparison; report limitations. No claim of model superiority before the artifacts demonstrate it.

This is a proposal only. No new implementation rounds were started and no frozen evaluator was changed. The user has authorized review, preservation and a possible division/takeover; this audit makes that takeover concrete without assuming an unlimited new budget.

## Evidence paths

Candidate: FREEZE-v2.md; package/prax-teach/SKILL.md; schemas/lesson.schema.json; references/LESSON-MODEL.md; references/TEACHING.md; project/explorer.py; templates/ive/ive.js; state/io.py; state/sync.py; selftest.py.

Receipts: reviews/v2.2-final-claims/*/build-report.json; reviews/v2.2-numeric-wording-audit.md; reviews/v2.2-five-lens.md; reviews/v2.2-final-result.md; reviews/v2.2-smoke.md; .state/selftest/auto-20261019T084718Z-19642-61d4b8d5.json; live receipts agent-20261019T091410Z-41846-1cdd45b6 and agent-20261019T091457Z-42176-3c7350f4.

Limits: source/receipt/hash review, two current still images and targeted binary64 calculations. Not a fresh full media build, audio listening test or complete rerun of all tests. Approval interpretation is recorded in FREEZE-v2 but the underlying 'implement it then' exchange was not independently recovered here; no unsupported allegation of unauthorized work is made.
