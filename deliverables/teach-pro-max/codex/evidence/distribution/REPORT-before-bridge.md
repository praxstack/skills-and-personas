# Legacy distribution full verification after pinned dependency provisioning

The single authorized full rerun remains **FAILED**. Seven of eight gates pass. This is not a full-verification or core-pass claim.

## Environment changes only

- Installed the existing root and Flint package locks with Node 22.23.3/npm 10.9.9 and `npm ci --ignore-scripts --no-audit --no-fund`: 18 and 183 packages added. Neither lock declares install scripts.
- Created a dedicated isolated Python 3.12.15 runtime at `/private/tmp/prax-teach-v3-runtime/venvs/distribution` using `uv sync --frozen`, installing `fsrs==6.3.1` and locked `typing-extensions==4.16.0`.
- The pinned SkillOpt source remains clean at `e4ea6a6771e797ef820cdd8bfea64c57e0481065`; its adapter imports successfully without installing or invoking provider/API stacks.
- Node 22 and the Python environment were selected only in the verifier subprocess environment. Global defaults were not changed.

## Observed gates

| Gate | Before provisioning | One rerun |
| --- | --- | --- |
| Python tests | 238 run; 30 failures, 46 errors | 238 run; 0 assertion failures, 42 errors — FAIL |
| Node tests | FAIL, missing modules in retained tail | 20 passed, 0 failed, 0 skipped |
| Visualization registry tests | PASS | 12 passed |
| Registry count | PASS | 38 tools valid |
| Exact HTML parity | FAIL, missing modules | 41 Markdown/HTML pairs checked — PASS |
| Package validator | FAIL | PASS |
| Python lint | PASS | PASS |
| Python format | PASS | 58 files already formatted — PASS |

The remaining Python tail contains `FileNotFoundError` for the distribution-local `.venv/bin/python`. The provisioning used an external isolated venv, while frozen `tests/test_scheduler_cli.py:14`, `tests/test_state_contract_hardening.py:16`, and `tests/test_state_scheduler_causality.py:13` explicitly require `ROOT / ".venv" / "bin" / "python"`. This was a provisioning-layout miss, not a source/check repair opportunity. These three modules contain 40 test methods; subtests can contribute additional errors. The verifier discards all but 12 lines of each gate's output, so the retained evidence does not establish the exact cause of every one of the 42 errors. No failing gates were rerun to recover discarded logs.

A future authorized environment-only correction can provide the already-built runtime at that ignored `.venv` path and then run a separately authorized verification. This task did not create that bridge or perform a second full rerun, preserving the explicit one-rerun limit. Full readiness remains blocked until that succeeds.

## Immutability and receipts

The frozen release manifest is identical before provisioning, before rerun and after rerun:
`daacc74ff05f5ac54c6f285fff5f67198ad84a0915314153b2c3be674db4bd72`.

Verifier SHA-256 is unchanged:
`acf53a9345c127012bec3d7460c4dbe11b6513c18e708665611025154fcb2f87`.

Both npm locks, `uv.lock`, and SkillOpt source metadata hashes are unchanged. Only ignored dependency/runtime directories and the verifier-required `evidence/verification/full.json` changed inside/outside the distribution as allowed. No source, tests, schemas, thresholds or framework digests were edited. The current required receipt accurately says failed.

`before-full.json` and `before-full.log` preserve the prior failure before any installation; `after-full.json` and `after-full.log` preserve the one actual rerun. `comparison.json` records statuses and evidence hashes; `provisioning.json` and `run-command.json` record exact versions, pinned lock hashes, command, environment prefixes and timestamps. No commits, pushes, private evaluator cases or model/API calls were made.
