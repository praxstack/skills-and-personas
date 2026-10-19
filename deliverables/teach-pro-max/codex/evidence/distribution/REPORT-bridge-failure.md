# Legacy full distribution verification: environment diagnosis

Current full release remains **BLOCKED / FAILED**. No full-pass or core-as-full claim is made. The unchanged tracked baseline has a passed full receipt; the current runs have not reproduced that acceptance.

## Exact comparison

The tracked HEAD baseline receipt (`tracked-baseline-full.json`) is **passed**. It and every actual run below bind the same release manifest:
`daacc74ff05f5ac54c6f285fff5f67198ad84a0915314153b2c3be674db4bd72`.

Verifier SHA-256 is unchanged:
`acf53a9345c127012bec3d7460c4dbe11b6513c18e708665611025154fcb2f87`.

Both npm locks, `uv.lock`, SkillOpt metadata, source, tests, schemas, thresholds, framework digests and review payloads remain unchanged. This is an environment-layout incompatibility, not evidence of a new product/source regression. We did not edit acceptance machinery to accommodate it.

| Actual run | Python gate | Node gate | Package validator | Overall |
| --- | --- | --- | --- | --- |
| Root's original unprovisioned run | 238 tests; 30 failures, 46 errors | FAIL, missing modules | FAIL | FAIL |
| One authorized dependency-provisioned rerun | 238 tests; 0 assertion failures, 42 errors | 20 passed, 0 skipped | PASS | FAIL |
| Separately authorized temporary-bridge rerun | 238 tests; 1 assertion failure, 0 errors | 20 passed, 0 skipped | FAIL | FAIL |

In both provisioned runs, the visualization registry tests pass 12/12, the registry count validates 38 tools, exact HTML parity checks 41 pairs, lint passes, and 58 Python files are already formatted. The final run has six of eight passing gates; no successful final validator postflight was reached.

## Provisioned environment

Pinned root/Flint locks were installed with Node 22.23.3/npm 10.9.9 and `npm ci --ignore-scripts --no-audit --no-fund`, adding 18/183 packages. Neither lock declares install scripts. Node selection is subprocess-local; global defaults are unchanged.

`uv sync --frozen` under Python 3.12.15 created `/private/tmp/prax-teach-v3-runtime/venvs/distribution` with `fsrs==6.3.1` and locked `typing-extensions==4.16.0`. SkillOpt remains clean at pinned commit `e4ea6a6771e797ef820cdd8bfea64c57e0481065`; its source adapter imports successfully without a provider/API stack.

## Why the remaining gates fail

The first provisioned run exposed frozen scheduler/state tests that explicitly invoke `ROOT/.venv/bin/python`. The external runtime alone did not provide that path.

Root then explicitly authorized a temporary `.venv` symlink to that runtime and one further full run. Before launch, every fixed Python/sandbox/runtime path existed and the exact bridged interpreter imported `fsrs==6.3.1`. The 42 missing-path errors disappeared.

The symlink conflicts with the existing independent-review payload policy. `scripts/review_payload.py:126` rejects a directory symlink before checking the `.venv` exclusion at line 130. A read-only diagnostic with the bridge present produces the exact error `review payload contains a directory symlink: .venv` and dependent stale-review errors. With the bridge absent, only the expected current-failed-receipt status errors remain. The Python tail is a validator failure JSON followed by `FAILED (failures=1)`; source inspection identifies the full-release validation assertion in `tests/test_validator_cli.py:239` as the matching assertion. The verifier retains only 12 output lines, so this attribution is supported by the paired diagnostic and source, not a retained complete Python traceback.

The current validator fails closed because the actual full receipt is failed. We did not rewrite it, substitute the old accepted receipt, relax symlink checks, or update any digest.

## State and next boundary

Every temporary bridge was unlinked safely; the isolated runtime target remains. `.venv/`'s directory-only Git ignore rule does not cover a symlink, so no symlink was retained or committed. Only ignored installed dependencies/runtime caches and the verifier-required full receipt changed. Failed receipts/logs were preserved before each authorized run.

The compatible environment layout for a future authorized run is a **real ignored `.venv` directory** provisioned from the existing frozen `uv.lock`, rather than a symlink. That would satisfy both the fixed test path and the existing no-directory-symlink policy without changing product or checks. It has not been applied or run under this task's exhausted rerun authorization. Current full release acceptance therefore remains blocked.

Evidence: `before-full.*`, `after-full.*`, `before-bridge-full.*`, `final-full.*`, `provisioning.json`, `bridge-probe.json`, `run-command.json`, `final-run-command.json`, paired diagnostic-validator JSON/logs, and `final-comparison.json`. The earlier report is retained as `REPORT-before-bridge.md`. Runtime paths, timestamps and source/evidence hashes distinguish execution history; the frozen verifier's content-derived run ID can repeat across unchanged-source runs.

No commits, pushes, private evaluator cases, model calls or API calls were made.
