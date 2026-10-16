# Subscription evaluation v2

This is a restricted authenticated Codex content-inference broker. Shell/read/browser/app/MCP tools are disabled; the exposed apply_patch helper is constrained by CLI read-only mode and an outer filesystem boundary. It retains exact responses, per-turn JSONL, stderr, package copies, artifact hashes and paired configuration. It does not execute teaching tools or prove real learner-state behavior. The controller separately renders and inspects textual Markdown/SVG/HTML outputs and exercises real runtime consent/security tests.

Run from this checkout:

```sh
python3 tools/teaching-evaluation/subscription_runner.py \
  --baseline /absolute/original-package --candidate /absolute/candidate-package \
  --scenario /independent/evaluator/teaching-only.json \
  --output /external/receipts/unique-scenario-run \
  --model gpt-6.1-sol --seconds 600 --repetitions 3
```

Both package roots contain `SKILL.md`. The fixed bundle adds existing `references/MODE-CONTRACT.md`, `TEACHING-PROTOCOL.md`, `VISUALIZATION-ROUTER.md`, `ARTIFACT-CONTRACT.md`, and `LEARNER-STATE.md`. Paired path sets must match. Missing optional reference paths are recorded through their absence; the independent freezer must confirm the intended package roots. Bundle UTF-8 text is capped at 200,000 bytes per arm, with no silent truncation. Other package bytes are copied and hashed for audit, never added to the teaching prompt.

Teaching-only JSON schema (additional properties rejected):

```json
{"id":"public-dummy","turns":["Explain why ice floats in two sentences.","I am confused about density; clarify that connection."]}
```

`id` is a nonempty ASCII alphanumeric/hyphen/underscore identifier. `turns` is a nonempty array of nonempty user strings. The independent evaluator exports only these fields from its sealed bank. Answers, grading criteria and future user turns are never supplied early. Each call sees the fixed teaching bundle and exact prior user/assistant role replay, then one new user turn. This is sequential real inference with explicit role replay, not a persisted native CLI chat session; generated filesystem state is not used as teaching memory.

Output layout: `config.json`, `result.json`, `manifest.json`, and `1-baseline/`, `1-candidate/` through replicate 3. Every arm has `turn-N.stdout.jsonl`, `turn-N.stderr.txt`, `turn-N.response.txt`, `turn-N.json`, `conversation.json`, `workspace/`, and `artifacts.json`. Response and artifact files remain available for independent inspection. Config records binary/version/runner/source/bundle hashes, paired model, deadline and disabled features. Existing output directories are refused. An arm deadline covers all its turns, and timeout kills the process group. Nonzero exit, empty response, tool events or changed package/source bytes make transport fail.

Temporary private `CODEX_HOME` copies only existing `auth.json` (0600), uses no inherited user config/rules or global mutation, and is deleted on normal completion/errors. Abrupt host termination can leave temporary credentials; identify `teach-auth-*` directories and remove them explicitly before reuse. No auth bytes are included in receipts. The broker is trusted with credentials. Shell/read tools are disabled; apply_patch remains advertised but patch writes are rejected by CLI read-only mode. Live JSONL is checked for unexpected tool events, and any attempted helper event fails transport. The outer OS profile additionally denies hidden/source/other-arm file-data reads and outside writes. Private auth-home reads are allowed to the trusted CLI; no general model file-reading tool is exposed. Earlier experimental profiles remain diagnostic receipts; each final arm retains its actual applied sandbox.sb and command.json.

No run is automatically accepted. `result.json` explicitly starts with `scored:false, accepted:false`; hidden eligibility remains false until the independent freezer reviews the measured broker boundary, seals the bank and attests the immutable configuration. `validate_grading` refuses absent independent scoring, absent actual inspection, malformed five-dimensional scores or protected failures. The controller must apply the unchanged full acceptance gates across all six families and three paired repetitions. A smoke with `--repetitions 1` is public only. Never interpret public transport success or an AI score as human-learning evidence.

Tests:

```sh
python3 -m unittest discover -s tools/teaching-evaluation -p 'test_*.py' -v
```

Independent scoring API: import the module and call `aggregate_scores(records, checks)`. `records` contains exactly 36 objects of this form (all six families × replicates 1–3 × both arms):

```json
{"family":"science","replicate":1,"arm":"candidate","independent_grader":true,"inspection_passed":true,"dimensions":[2,2,2,2,2],"protected_failures":[]}
```

`inspection_passed:true` means the output was actually inspected for scoring; it does not substitute for the separate rendered quality gate. Baseline protected failures may be recorded; candidate protected failures block acceptance. `checks` must contain exactly these boolean fields: `protected_public_probes_passed`, `deterministic_regressions_passed`, `rendered_inspection_passed`, `frozen_boundary_review_passed`, `receipts_integrity_passed`, `budget_passed`. Missing checks/grades or invalid scoring fail closed. The caller must independently verify receipts and store its scoring output outside the package. The aggregator returns all family means, overall means/gain, improved-family count, numeric gate status and acceptance. It uses integer totals for the overall score/gain thresholds, avoiding floating point boundary drift. Grades contain no teaching prompts and are never passed to inference.

Snapshot exclusions are identical across arms and recorded in config: `.git`, `.venv`, `node_modules`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`, `.DS_Store`. The trusted CLI runs under the generated outer sandbox.sb; its provider network is allowed. Model shell/read tools are disabled and CLI read-only mode rejects patch writes. The outer boundary denies file data reads under /Users outside the current workspace, private CLI home and executable; /Volumes, /private/tmp, and /private/var outside the private CLI home are denied. All outside writes are denied except /dev. Metadata and system runtime reads remain allowed. The boundary is intended for the documented /Users receipt layout, not arbitrary output volumes.

Initial package imports reject symlinks and hardlinked files. Final source/package verification compares exact content hashes and path sets and still rejects symlinks; a metadata-only link-count increase is recorded in `source-link-diagnostics.json`, not treated as changed content. During setup, all six public source files acquired link count 2 without byte changes; the cause remains unverified. The controller explicitly permitted this pre-freeze distinction. This is not evidence of inode immutability or a guarantee against external hardlink alias creation.
