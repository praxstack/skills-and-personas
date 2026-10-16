# Subscription evaluation implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Make the approved baseline-versus-candidate teaching evaluation run with existing subscription authentication before any teaching-skill edits.

**Architecture:** Add a separately versioned subscription runner beside the existing evaluator, reusing applicable validation/hash helpers. Preserve the existing offline evaluator and receipts. Keep model-visible teaching inputs separate from independent grading inputs, allow inference network access, and restrict filesystem/tool access with a measured boundary.

**Tech Stack:** Existing Python 3.13, Codex CLI, macOS sandbox, unittest.

**Spec:** docs/teach-pro-max/review-2026-10-16/DESIGN-v1.md and EVALUATION-CONTRACT-v1.md in that directory; user explicitly approved revising the incompatible evaluator and requested implementation.

## Global Constraints

- No teaching candidate edits during evaluator setup. No installed-link changes.
- Preserve the original design, original contract, historical evidence and offline evaluator bytes.
- Preserve all original scoring thresholds, six families, three paired repetitions, 36 target-run maximum, four secondary smoke scenarios, and 120-minute candidate budget.
- No paid API purchase, subscription change, new remote service, or publication.
- No exposed tokens, private learner data, or unrelated project files in prompts/logs.
- Receipts live outside the package they attest to. Hidden inputs live outside candidate workspaces.
- No security or evaluation-strength claims unsupported by actual probes.

### Task 1: Implement subscription-compatible evaluation

**Files:**
- Create: `tools/teaching-evaluation/subscription_runner.py`
- Create: `tools/teaching-evaluation/test_subscription_runner.py`
- Create: `tools/teaching-evaluation/README.md`
- Create: `docs/teach-pro-max/review-2026-10-16/EVALUATION-CONTRACT-v2.md`
- Create: `docs/teach-pro-max/review-2026-10-16/APPROVAL-2026-10-16.md`
- Read only: `skills/teach-pro-max/references/prax-teach-v2/scripts/evaluate.py` and its tests.
- External receipts: `/Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/`.

**Interfaces:** Consume baseline/candidate package roots and one scenario supplied by an independent evaluator. Produce separate arm/replicate transcripts, artifact trees, config/version/hash receipts, and grader-ready outputs without answer keys. Document exact runnable CLI and JSON formats. The frozen runner must support real multi-turn boundaries, paired configuration and deadline enforcement. Model tools cannot read the hidden bank or the other arm. Grading is independent and uses the approved 5-dimension rubric, not term matching. Never expose grading keys to teaching calls.

- [ ] Read the old evaluator and external FEASIBILITY.md. Identify helpers that can be reused without weakening the offline mode.
- [ ] Write v2 as a versioned amendment reflecting the user's approval: authenticated inference may use network; require direct comparison of original skill and candidate; retain outputs for independent inspection; rubric scoring replaces term matching. Record exact isolation and known limits. Preserve all product and numeric gates.
- [ ] Implement the smallest runner that uses the installed authenticated Codex CLI with a restricted filesystem and no unrelated MCP/tool configuration. A temporary CODEX_HOME may carry minimum necessary auth, private permissions and explicit cleanup, never token logs. Do not change global configuration. Do not invent CLI flags: inspect installed help/config capabilities.
- [ ] Add unittest cases for paired arm separation, grader-data omission, failure/timeout propagation, output retention/hashing, path escape rejection, and refusal to accept missing inspection/scoring. Use fake subprocess only for deterministic error paths.
- [ ] Run `python3 -m unittest discover -s tools/teaching-evaluation -p 'test_*.py' -v` and retain output.
- [ ] Run an actual authenticated public smoke request and adversarial filesystem probes. Explicitly prove hidden/source/other-arm/outside-write boundaries or report precisely what cannot be guaranteed. No hidden scenarios yet. Preserve actual generated response and harmless test artifacts in external receipts.
- [ ] Self-review, stage only named files, commit. Report the exact commands, tested boundaries and remaining blockers. Do not run candidate evaluations or change skill files.
