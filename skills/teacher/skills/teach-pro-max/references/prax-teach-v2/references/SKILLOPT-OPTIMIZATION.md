# Optional SkillOpt optimization

_Verified upstream snapshot: 2026-08-04. This integration is off by default and is not installed by this package._

## Purpose

Use [Microsoft SkillOpt](https://github.com/microsoft/SkillOpt) as an **offline proposal generator** for measurable instruction changes. Do not let it rewrite a live installed teaching skill, update learner state, or replace learner-outcome evaluation.

SkillOpt treats one Markdown skill document as trainable text. A frozen target agent performs scored tasks; a separate optimizer proposes bounded edits; a selection split gates candidates; the best accepted document is emitted as `best_skill.md`. The authors report strong benchmark results across tested models and harnesses, but those results are an arXiv preprint's own evaluation rather than an independent replication. [Paper](https://arxiv.org/abs/2605.23904)

## Verified upstream boundary

| Item | Current verified fact | Consequence here |
|---|---|---|
| Release | PyPI `skillopt` 0.2.0; Python 3.10+; alpha; MIT | Pin the reviewed release or a specific source commit |
| Commands | `skillopt-train`, `skillopt-eval`, `skillopt-sleep` | Keep execution outside the runtime tutor |
| Artifact | One trained Markdown document, normally `best_skill.md` | Optimize only `SKILL.md`; keep package references frozen |
| Gate | Candidate must strictly improve the repeatedly queried selection score in the paper-style path | Add repeated trials and an external hard-safety gate |
| Custom task | A benchmark adapter supplies train/selection/test data, scored rollouts, and saved trajectories | A Prax Teach adapter is required before real training |
| Cost | The paper reports roughly 20.8M–213.8M training tokens for showcased benchmarks | Begin with a budgeted smoke pilot, not a broad run |
| Portability | Multiple backends and selected transfer settings were tested | Re-test every target model and harness; do not promise zero lock-in |

Primary references: [installation](https://microsoft.github.io/SkillOpt/docs/guide/installation.html), [configuration](https://microsoft.github.io/SkillOpt/docs/guide/configuration.html), [skill document](https://microsoft.github.io/SkillOpt/docs/guide/skill-document.html), [custom benchmark guide](https://microsoft.github.io/SkillOpt/docs/guide/new-benchmark.html), and [method](https://arxiv.org/html/2605.23904#S3).

The documentation tracks `main`, while PyPI 0.2.0 omits repository benchmark configs, plugin shells, materializers, and tests. Features present only on `main` require a reviewed commit pin rather than an unversioned checkout.

Check availability without changing the environment:

```bash
python3 scripts/check_optional_integrations.py --json
```

## Architecture

```text
frozen package + public development cases
                 |
                 v
     isolated Prax Teach benchmark adapter
                 |
       train rollouts and reflection
                 |
                 v
        candidate best_skill.md
                 |
       +---------+------------------+
       |                            |
       v                            v
hidden critical guardrails   repeated selection score
       |                            |
       +-------------+--------------+
                     v
          staged diff for human review
                     |
       package clone + HTML regeneration
                     |
       untouched test + cross-model check
                     |
                     v
             candidate release only
```

The optimizer never owns the installed package. Promotion remains a separate, reviewable release action.

## Trainable and protected surfaces

SkillOpt optimizes a single text file, while Prax Teach is a multi-file package. Use this boundary:

### Trainable proposal surface

- mode-routing wording and order;
- teaching-loop phrasing and compression rules;
- when references should be loaded;
- hint, feedback, and transfer instructions;
- concise routing language that affects observed agent behavior.

### Protected package surface

- all files below `references/` and `scripts/` during an optimization run;
- the `name` field and package-relative links;
- **Answer now** and the live retrieval turn boundary;
- no silent persistence and correctable evidence-based learner state;
- no premature answer leakage, fabricated sources, or false mastery;
- Markdown-as-canonical, accessibility, privacy, and claim-boundary contracts.

Enforce the protected surface with hidden hard graders and deterministic package checks. Do not expose their exact prompts, answers, or judge instructions to the target workspace.

For each rollout, clone the complete package into a fresh isolated workspace, replace only the cloned `SKILL.md` with the proposed text, and leave the frozen references and scripts beside it. This preserves relative links while allowing SkillOpt to train one document.

## Benchmark contract

Maintain five banks:

| Bank | Visible to optimizer? | Use |
|---|---:|---|
| Public train | Yes | Reflection, failure analysis, and rapid iteration |
| Public `valid_seen` selection | Yes | Upstream-compatible optimizer iteration |
| External hidden `valid_unseen` | No | Repeated pre-test hard gating through trusted isolation |
| Test | No | One final evaluation after the candidate is frozen |
| OOD / transfer | No | Different target model, harness, topic, and surface form |

The bundled `references/eval-cases.json` and `evals/evals.json` files are public and discoverable. Treat them as development material, never held-out proof.

Each custom SkillOpt rollout must emit the upstream-required `id`, `hard`, and `soft` values and persist `predictions/<id>/conversation.json` for reflection. Keep reference answers, rubrics, graders, and test fixtures outside every target-agent workspace. [Benchmark adapter contract](https://microsoft.github.io/SkillOpt/docs/guide/new-benchmark.html)

## Non-compensatory scoring

Use a lexicographic gate:

1. **Integrity:** reject on any critical answer leakage, silent persistence, fabricated source/state, false mastery, accessibility loss, hidden-grader exposure, or destructive action.
2. **Behavior:** require a repeated paired improvement larger than measured rollout/judge noise on the frozen selection set.
3. **Regression:** require non-inferiority for quick, no-visual, **Answer now**, no-persistence, and accessibility strata.
4. **Efficiency:** among otherwise passing candidates, prefer lower latency, tokens, cost, and instruction length.

A scalar mean must never compensate for a critical tutoring failure. SkillOpt's internal score gate is necessary but not sufficient.

## Conservative pilot

Start with:

- patch mode rather than full-document rewrite;
- edit budget `1`;
- one or two epochs;
- fixed target, optimizer, configuration fingerprint, permissions, and tool set;
- full selection-set evaluation;
- repeated paired trials with deterministic checks before judge scoring;
- no test-set access during tuning;
- slow update disabled for the first pilot;
- externally enforced token, time, and monetary budgets.

These are local safety-first pilot choices, not the paper defaults. Record the difference.

## Adoption runbook

1. Freeze and fingerprint the current candidate package.
2. Pin SkillOpt by release or source commit in a sibling experiment environment.
3. Build the `prax_teach` benchmark adapter and hidden split banks.
4. Verify the adapter with no-provider or minimal smoke tasks.
5. Train only within the predeclared budget.
6. Quarantine `best_skill.md`; do not copy it into an installed skill. The
   bundled `stage_proposal.py` validates exact fields and byte bindings only:
   its score JSON is self-attested, so its receipt is never evidence-eligible
   or adoption-eligible. A trusted isolated evaluator must independently rerun
   the proposal before a human decision.
7. Review the diff for generalization, contradictions, bloat, and protected-contract changes.
8. Put the approved proposal into a cloned candidate package.
9. Regenerate `SKILL.html`, run `validate_workspace.py`, and repeat forward tests.
10. Open the untouched test once; then run at least one different model or harness.
11. Package a new candidate only after human approval.

Record the SkillOpt version/commit, dependency lock, model identifiers, sampling settings, split hashes, run seeds, costs, accepted/rejected edits, and complete grader fingerprint.

## SkillOpt-Sleep boundary

SkillOpt-Sleep can harvest supported coding-agent sessions and stage an update. Its Codex integration defaults to a no-provider `mock` backend; provider-backed runs send transcript-derived tasks or excerpts to the selected provider, and upstream warns that pattern-based redaction cannot guarantee secret-free prompts. [Codex integration](https://github.com/microsoft/SkillOpt/tree/main/plugins/codex) and [data boundary](https://github.com/microsoft/SkillOpt/blob/main/docs/sleep/README.md)

For Prax Teach:

- do not harvest learner sessions by default;
- require explicit, scoped consent before reading archives;
- export, inspect, redact, and mark a reviewed task file before any real backend;
- exclude learner state, sensitive content, source documents, and hidden assessments unless separately authorized;
- keep `--auto-adopt` off;
- prefer benchmark-driven training before transcript-driven optimization.

## Claim boundary

SkillOpt may show that a revised instruction document scores better on an agent benchmark. It cannot establish that people learn, retain, or transfer better. Delayed learner outcomes remain a separate study governed by [EVALUATION.md](./EVALUATION.md).
