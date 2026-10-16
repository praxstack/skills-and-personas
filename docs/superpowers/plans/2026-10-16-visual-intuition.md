# Visual intuition skill implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Revise the existing general teaching skill to deliver complete visual explanations that build concrete intuition, with optional directory-scoped continuity.

**Architecture:** Preserve the embedded engine and public wrapper. Change teaching policy and routing together; add a single optional continuity record through existing secure state APIs. Reuse rendering facilities and globally installed symlink consumers.

**Tech Stack:** Python 3.13, existing locked fsrs, Node 22, existing static renderer and visual lab.

**Spec:** docs/teach-pro-max/review-2026-10-16/DESIGN-v1.md. Evaluation uses separately approved and frozen EVALUATION-CONTRACT-v2.md; v1 numeric gates remain unchanged.

## Global Constraints

- Start only after independent evaluator, hidden bank, rubric, configuration and baseline are frozen. Candidate workers never inspect hidden evaluation materials.
- Preserve original baseline 286a98fc67486fa91bb19f34a9c0be347f5db029 and installed source. Original and currently accepted versions are identical.
- Each candidate run is capped at 120 minutes elapsed from the first candidate edit through evaluation, with at most 36 primary hidden target runs plus four secondary public smoke runs.
- No paid API purchase, subscription change, unapproved dependency service or automatic publication.
- No human-learning superiority claim. No deployment until acceptance and review pass.
- Existing learner schemas, evidence, IDs, hashes, scheduler, journals, filesystem protections and historical receipts are protected.
- General teaching skill, not a new app or a neural-network-specific lesson generator.
- Preserve prax-teach-v2 identity and teach-pro-max wrapper. Product changes only in the exact paths below. No dependency or rendering-framework changes.
- Teaching, medium, persistence and practice are separate choices. No compulsory quiz; no inferred mastery from coverage.

### Task 1: Align teaching instructions, visual guidance and routing

**Files:** Prefix P = `skills/teach-pro-max/references/prax-teach-v2/`.
- Modify `skills/teach-pro-max/SKILL.md`, `P/SKILL.md`.
- Modify `P/references/MODE-CONTRACT.md`, `TEACHING-PROTOCOL.md`, `VISUALIZATION-ROUTER.md`, `LEGACY-VISUALIZATION-ROUTER.md`, `ARTIFACT-CONTRACT.md`, `VISUAL-RUNTIME.md`.
- Modify `P/scripts/praxteach/routing.py`.
- Modify `P/tests/test_core_cli.py`, `P/tests/test_skill_contract.py` solely for explicitly versioned policy changes; preserve other assertions.
- Create `P/tests/test_visual_intuition_policy_v1.py`, `P/fixtures/routing-cases-visual-intuition-v1.json`.
- Regenerate `.html` companions for changed Markdown within P, and only those companions.
- Create `docs/teach-pro-max/review-2026-10-16/POLICY-TEST-CHANGES.md` to identify superseded assertions and preserved protections.

**Interfaces:** Keep route_request(request, answer_now=False, demote=False, explicit_mode=None) public behavior/shape compatible; unqualified teaching selects lesson. Explicit quick/direct/concise remains quick; ordinary tasks keep action=ordinary_task and mode=null; course remains explicit sequence intent, never implied consent. Continuity operations arrive in Task 2; describe policy without inventing commands before then.

- [ ] Read DESIGN-v1 in full and implement its teaching/visual requirements. Use complete bounded visual explanation first, optional one intuition check, targeted confusion repair, on-demand references, meaningful controls, truthful unavailable/essential medium handling, static equivalent, no fixed scene quota. Preserve quiz-only answer-leakage rules.
- [ ] Add public versioned policy/routing tests before change; run to observe expected failure. Include 'Teach me fractions' lesson, 'Explain this in one sentence' quick, ordinary coding task action=ordinary_task and mode=null, explicit course course, answer_now quick, requested quiz protections, visual explanation retrieval=false.
Concrete routing assertions for the new test module:
```python
assert route_request("Teach me fractions")["mode"] == "lesson"
assert route_request("Explain fractions in one sentence")["mode"] == "quick"
assert route_request("Fix this Python function")["action"] == "ordinary_task"
assert route_request("Teach me fractions", answer_now=True)["mode"] == "quick"
assert route_request("Teach me fractions", explicit_mode="course")["mode"] == "course"
```

- [ ] Change only conflicting old assertions and name each in POLICY-TEST-CHANGES.md; do not call old receipts current. Preserve historical fixture files unchanged.
- [ ] Regenerate only named Markdown companions with `npm exec --yes --package=node@22 -- node scripts/render_markdown.mjs --trusted-root . <relative-md>` from P.
- [ ] Run `.venv/bin/python -m unittest tests.test_visual_intuition_policy_v1 tests.test_core_cli tests.test_skill_contract tests.test_visual_routing tests.test_visual_verification -v`, and render checks for changed companions. Save logs outside P.
- [ ] Self-review, commit named files and report exact tests and any unresolved conflict.

### Task 2: Add consented directory continuity

**Files:** Prefix P as above.
- Create `P/scripts/praxteach/continuity.py`, `P/schemas/continuity.schema.json`.
- Modify only narrow hooks in `P/scripts/praxteach/cli.py`, `state.py`, `export.py`; optional schema hook in `P/scripts/validate_workspace.py` if required by its existing schema dispatcher.
- Create `P/tests/test_continuity_cli.py`, `P/tests/test_continuity_security.py`.
- Modify `P/tests/test_schema_validator_parity.py` for additive independent schema cases only.
- Modify `P/references/LEARNER-STATE.md`, `OPERATIONS.md`, `SOURCES-AND-PRIVACY.md` and regenerate their HTML companions where present.
- Modify `docs/teach-pro-max/USAGE-GUIDE.md` and regenerate its HTML companion.

**Interfaces:** New optional `state/continuity.json`, schema_version 1, revision integer, extension consent status, user-stated preferences, covered_topics, last_lesson, agent_summary, next_topic. Implement CLI `continuity-show` (inspection), `continuity-resume` (active base+extension consent), `continuity-grant --consent --expected-revision`, `continuity-update --data <JSON file> --expected-revision`, `continuity-withdraw --expected-revision`, and `continuity-reset --expected-revision --preferences-only|--all --dry-run|--confirm`. Expected revision 0 represents absent record; real records start 1. Revisions increment under lock, stale update fails. Full reset deletes record and grant; preference-only reset preserves grant and evidence. Any more exact implementation choices must be documented in schema and operations together.

- [ ] Read DESIGN-v1 continuity/security requirements and public implementation map at `.superpowers/sdd/2026-10-16-subscription-evaluation/product-implementation-map.md`. Reuse workspace_lock, secure_workspace, read_json, atomic_write_json, anchored unlink. Do not change existing IO, scheduler or evidence transaction code.
- [ ] Add failing tests for absent legacy record, explicit grant, base/extension withdrawal, regrant, inspect/export/reset after withdrawal, unknown fields/types/bounds, stale revision, concurrent updates, symlink/hardlink/world-readable state, corrupt optional record and sibling lessons surviving delete.
- [ ] Implement bounded optional record with exact fields and independent version. Allowed preference keys: teaching_style, delivery, medium, detail, language, accessibility. Each preference has value and provenance='user-stated'. Covered topics are exposure only, never evidence. Agent summary explicitly labeled agent-authored. Reject unknown keys, booleans as integer revisions, oversized strings/lists, malformed JSON. No transcript or inferred traits. Keep next_topic learner-requested only.
- [ ] Use existing locked state validation with active consent for grant/update/resume. Inspect/export/delete can use require_active=False. Optional-file absence only may return null; malformed or unsafe file must fail. Prevent circular imports with a narrow loader/validator free of state imports and local operational imports.
- [ ] Add valid optional record to show/export. Entire workspace deletion naturally includes it; preserve sibling lessons. New consented initialization uses `<learning-dir>/.prax-teach` without precreating it. Do not change old init default schema. Teach explicit separate continuity grant after base init. Never persist refusal just to suppress prompts.
- [ ] Document independent lesson saving at `<learning-dir>/lessons`, explicit save-nothing, active consent resume and no silent old-workspace migration. Check all documented CLI examples against `--help` and a throwaway workspace.
- [ ] Run focused continuity and protected state/export/security/CLI/schema suites, then Python discovery once. Capture actual output and classify historical policy receipts separately; never suppress a protected regression.
- [ ] Regenerate named companions, self-review, commit only owned paths and report tests.

### Task 3: Freeze candidate, verify delivery and prepare reversible promotion

**Files:**
- Create `docs/teach-pro-max/review-2026-10-16/CANDIDATE-RESULTS.md`.
- Modify `skills/teach-pro-max/references/ENGINE-MANIFEST.json` only after applicable source checks pass.
- Modify `skills/teach-pro-max/references/prax-teach-v2/STATUS.md`, `STATUS.html`, `STATUS.json` only if needed to state old receipts are historical; never rewrite historical receipts.
- Receipts, generated public example lessons, screenshots, sealed grading and rollback links remain external to skill source.

**Interfaces:** Consume reviewed Task 1/2 commits. Produce immutable candidate source hash, deterministic test logs, actual delivery inspection, independent paired scores and rollback manifest. Candidate source is frozen before model comparisons. No post-evaluation source edits presented as evaluated bytes.

- [ ] Run all applicable Python and JavaScript checks with supported locked runtimes; preserve historical-only failures as explicit limitations rather than green claims.
- [ ] Run actual static and interactive/animation public examples and inspect artifacts in browser, including representative model states, keyboard, reduced-motion and fallback. Keep exact source/artifact hashes and scope of observations. Never call structure tests browser inspection.
- [ ] Freeze candidate package; independent evaluator runs approved hidden 36-run matrix and secondary four smoke cases. Compare both original and currently accepted baseline. Grade all repetitions with frozen criteria and retain outputs.
- [ ] Apply unchanged thresholds and protected gates. If failure/budget expiry, preserve installed baseline and report incomplete or rejected candidate. No automatic second candidate on exposed tests.
- [ ] After passing, generate current distribution hashes and version the accepted bytes; record exact previous installed symlink targets. Use canonical `.agents` links, expose consumers by symlink, and verify installed paths and fresh-session smoke. Keep original checkout for rollback. No remote push.
