# Legacy distribution full verification: passed

The final **full** verifier exited **0**. All eight gates and the final package-validator postflight passed. This reproduces engineering acceptance of the unchanged legacy distribution; it does not establish human learning outcomes or overall v3 acceptance.

| Full gate | Observed result |
| --- | --- |
| Python tests | 238 run — OK |
| Node tests | 20 passed, 0 failed, 0 skipped |
| Visualization registry tests | 12 passed |
| Registry count | 38 tools valid |
| Exact HTML parity | 41 Markdown/HTML pairs checked |
| Package validator | PASS |
| Python lint | PASS |
| Python format | 58 files already formatted |
| Final validator postflight | PASS |

Trusted macOS sandbox tests were required; no verifier policy failures were recorded. The canonical required `evidence/verification/full.json`, `real-venv-full.json` and captured `real-venv-full.log` have identical bytes and report passed.

## Environment repair, no product or gate edits

The final environment uses Node **22.23.3**, npm **10.9.9**, Python **3.12.15**, frozen `fsrs==6.3.1` and `typing-extensions==4.16.0`. Root and Flint dependencies were installed from their existing locks with `npm ci --ignore-scripts --no-audit --no-fund`; no lock declares install scripts. Node selection is local to the verifier subprocess, leaving global defaults unchanged.

The runtime expected by frozen tests is now a **real, Git-ignored `.venv` directory**, created with `uv sync --frozen` from the existing lock. It is not a symlink. Its exact interpreter/version and FSRS import were probed before the final run. `scripts/review_payload.py . --check` passed before launch with payload SHA-256 `7cf9995e3ff84bca35acf55d2e24fbc756628299d90d7de61a920da071255df6`.

SkillOpt's source remains clean at the exact pinned commit `e4ea6a6771e797ef820cdd8bfea64c57e0481065`. Its adapter was exercised without provider/API calls. No global tool or shared renderer runtime was reinstalled.

## Immutable baseline comparison

The tracked accepted baseline full receipt is passed. It and all actual runs use the exact same release manifest:
`daacc74ff05f5ac54c6f285fff5f67198ad84a0915314153b2c3be674db4bd72`.

Verifier SHA-256 is unchanged:
`acf53a9345c127012bec3d7460c4dbe11b6513c18e708665611025154fcb2f87`.

Both npm locks, `uv.lock`, SkillOpt metadata, source, tests, schemas, thresholds, framework digests and independent-review payloads were preserved. The only distribution changes are ignored installed dependencies/runtime files and the required generated full receipt. No validator, digest or governing gate was rewritten.

## Preserved failure history

The original unprovisioned run had missing modules, unsupported default runtime versions and no FSRS. The first provisioned run used an external venv but exposed 42 errors because frozen tests require `.venv/bin/python`. A separately authorized temporary bridge removed those errors but triggered the existing no-directory-symlink review-payload policy, leaving one validator assertion failure. Paired read-only diagnostics isolated that cause. Every symlink was removed safely.

Root then authorized the correct real-directory environment and one final run after complete preflights. That run passed. These earlier failures were environment/setup failures on unchanged source, not a product regression. They were not deleted or replaced with the old accepted receipt.

Evidence is retained as `before-full.*`, `after-full.*`, `before-bridge-full.*`, `final-full.*` (the bridge-induced failure), `before-real-venv-full.*`, and the successful `real-venv-full.*`. The previous blocked reports remain in `REPORT-before-bridge.md` and `REPORT-bridge-failure.md`; `final-comparison-bridge-failure.json` preserves that stage's comparison. The current outcome is in `final-comparison.json`. `real-venv-preflight.json` and `real-venv-run-command.json` record the actual environment, command and timestamps.

The frozen verifier's content-derived run ID repeats for unchanged-source runs; preserved commands, timestamps, dependencies and evidence hashes distinguish execution history. No commits, pushes, private evaluator cases or model/API calls were made.
