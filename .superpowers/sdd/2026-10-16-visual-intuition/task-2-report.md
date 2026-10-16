# Task 2: consented directory continuity

Status: implemented; focused checks pass. Supported-runtime discovery: 258 tests, 256 passed and 2 historical-binding failures. No deployment, evaluator change or historical receipt promotion is included.

## Scope and implementation

Read the exact Task2 brief, the plan's Global Constraints, DESIGN-v1 and the public implementation map. Started after Task1 commit `39f21f0`; obeyed the requested pause before source edits. Only Task2 paths are staged. No hidden evaluation materials, frozen contract/plan, existing learner schema, scheduler, IO, event identifiers/hashes or evidence transaction machinery were edited.

Added an independent optional `state/continuity.json` schema v1, not fields in `learner.json`. The small module validates exact fields, allowed preference keys, user-stated / agent-authored / learner-requested provenance, bounded strings/lists, exact integer revisions, and content-only partial updates. It exposes inspect/resume, explicit grant, update, withdrawal and dry-run/confirmed preference or full reset CLI operations.

Grant/update/resume validate active base consent; update and personalization also require the extension grant. Legacy absence returns null without writes. Inspection/export/reset/withdrawal remain available after base or extension withdrawal. Preference reset preserves consent status, continuation and learning evidence; full continuity reset removes record and grant using the existing descriptor-relative unlink helper. Full workspace deletion still preserves sibling lessons.

Every operation validates the prior record and expected revision under existing `workspace_lock`. Narrow state validation, show and export hooks include optional continuity and reject unsafe/corrupt state. The loader/validator have no state imports; operations import state locally to avoid cycles. Existing generic anchored file reads checked type/link/containment but did not check optional-file private modes. New security tests caught that gap; continuity locally reuses existing anchored destination/parent checks plus private single-link validation. No IO implementation changes were made.

Schema and Operations jointly document every added choice: exact shapes/bounds; omitted content fields survive while supplied fields replace whole fields; null clears nullable slots; input JSON cap 262144 bytes; revision ceiling; absent reset behavior; preference reset clears all preferences; revision restarts after full reset, so cached revisions must be discarded across reset. Semantic truth of a provenance label remains the caller's responsibility; runtime validates structure, not whether a learner actually requested a string.

Updated Learner State, Operations, Sources/Privacy and public Usage Guide, including `.prax-teach` consented initialization without precreation, independent sibling lessons, explicit save-nothing, separate extension grant, active-consent resume without forced quiz, no silent migration, and no remote learner-record disclosure. Regenerated only their four HTML companions.

## Test commands and actual results

Commands from P (`skills/teach-pro-max/references/prax-teach-v2`) unless specified otherwise. Logs are outside the package, at the named `/tmp/` paths. Python is 3.13.15. Node22 is supplied through `npm exec --yes --package=node@22 --` for renders and the corrected discovery run.

| Command | Result | Output |
|---|---|---|
| `.venv/bin/python -m unittest discover -s tests -p 'test_continuity_cli.py' -v` before implementation | Expected red: 5 failures, unknown continuity CLI commands | `/tmp/task2-red.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_continuity*.py' -v` | 10 passed | `/tmp/task2-continuity-final.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_state*.py' -v` | 43 passed | `/tmp/task2-state.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_core_cli.py' -v` | 12 passed | `/tmp/task2-core.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_export*.py' -v` | 5 passed | `/tmp/task2-export.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_private_paths.py' -v` | 9 passed | `/tmp/task2-private.log` |
| `.venv/bin/python -m unittest discover -s tests -p 'test_schema_validator_parity.py' -v` | 4 passed, including independent additive continuity cases | `/tmp/task2-schema.log` |
| `SKILLOPT_SOURCE=/Users/prax/Developer/prax-teach-evaluation-20261016/dependencies/SkillOpt-v0.2.0 PRAX_RUN_MACOS_SANDBOX_TESTS=1 .venv/bin/python -m unittest discover -s tests -p 'test_skillopt_adapter.py' -v` | 15 passed | `/tmp/task2-skillopt.log` |
| `.venv/bin/python /tmp/task2-smoke.py` | 21 new documented CLI/help checks passed in throwaway directory; update JSON read directly from Operations example | `/tmp/task2-cli-smoke.json` |
| `ruff check` on new continuity module and two new test files | Passed | Tool output |
| `git diff --check` | Passed | Tool output |

Focused tests cover legacy absence/no synthesized write, grant/refusal, update, extension and base withdrawal, regrant, inspect/export/reset after withdrawal, unknown fields/types/provenance/bounds, malformed input/stored JSON, exact integer revisions, stale and concurrent writes, symlinks/hardlinks/world-readable files across controls, and sibling lesson preservation. Existing protected state/export/private-path tests were unchanged.

Initial full discovery used the shell's Node26 and omitted `SKILLOPT_SOURCE`: `PRAX_RUN_MACOS_SANDBOX_TESTS=1 .venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v`. Actual result: 243 tests in 181.230s; 2 failures and 1 setup error. This is retained as a diagnostic result, not claimed as a supported-runtime pass. Log `/tmp/task2-discovery.log`:

- `test_skillopt_adapter.SkillOptAdapterTest.setUpClass`: asserted pinned SkillOpt source was required; corrected by the separate 15-test pinned run above and by the corrected full command below.
- `test_validator_cli.ValidatorCliTest.test_full_validation_accepts_the_release_status_ledger`, line239: expected validator exit0, got1. Reported historical release/review/forward/inspection/provenance digest bindings stale after source changes. It also correctly reported `json_schemas: 11`. Old receipt bytes were not rewritten to pass it.
- `test_validator_cli.ValidatorCliTest.test_portability_adapted_legacy_assets_are_explicitly_bound`, line106: expected no provenance errors, got `evidence/provenance/legacy-assets.json: assets[5] target digest mismatch: references/LEGACY-VISUALIZATION-ROUTER.md` (Task1 policy source versus old provenance receipt).

The release-ledger test also contains a later `json_schemas == 10` assertion. A genuinely additive independent schema makes 11. That test file is outside Task2's allowed paths, so the assertion remains unchanged and needs explicit additive test-path authorization if the full release gate is to become current later. No protected assertion was suppressed.

Corrected full supported-runtime command (needed because the first run used the wrong Node runtime):

```sh
SKILLOPT_SOURCE=/Users/prax/Developer/prax-teach-evaluation-20261016/dependencies/SkillOpt-v0.2.0 \
PRAX_RUN_MACOS_SANDBOX_TESTS=1 \
npm exec --yes --package=node@22 -- \
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

Output `/tmp/task2-discovery-node22.log`: **258 tests in 110.438s, 2 failures, no errors or skips** (256 passed). Node22 verified as v22.23.3. The two failures are precisely the same release-ledger and legacy-provenance assertions listed above; no continuity/state/export/security test failed. This is not a green full-release claim.

After corrected discovery, restored the historical runtime receipt again to the exact SHA256 given below and verified no `evidence/` or `historical/` diff. No existing old schemas were changed.

## Generated companions

Used `SOURCE_DATE_EPOCH=2026-10-16T17:34:54Z npm exec --yes --package=node@22 -- node scripts/render_markdown.mjs --trusted-root . <source>` followed by the same command with `--check` for `references/LEARNER-STATE.md`, `OPERATIONS.md`, `SOURCES-AND-PRIVACY.md`. For public Usage Guide, invoked the same renderer from repository root with trusted root `.` and source `docs/teach-pro-max/USAGE-GUIDE.md`.

Actual result: four regenerations and four exact parity checks passed, log `/tmp/task2-render.log`. Earlier standalone checks used the renderer's default current timestamp and therefore reported generated-at drift; rerendering and checking with the same fixed timestamp resolved that without changing the renderer. Rendering/structure checks do not claim browser inspection or human-learning outcomes.

## Self-review and protected receipts

Reviewed narrow hooks and lifecycle/security behavior. No scheduler/event/projection algorithm changes, no dependency/network service additions, no copied skill trees and no research/aesthetic files staged. Optional continuity corruption remains an error, including export/deletion, rather than being silently discarded. Revision conflicts never overwrite newer content in ordinary concurrent operations; full-reset revision restart is explicitly documented.

A transient diff in historical `evidence/zero-api-visual-runtime/verification.json` was observed during the first discovery. It changed only routing byte-count/hash bindings. Restored exact HEAD bytes after the test run and verified SHA256 `42d5826f23ed4462a79a363f27ab8c2ab9721c1f93d1c9ac10a1b11c1a2fe959`. Its source was not established; inspected visual tests use temporary outputs. No historical receipt changes are part of this task. After the final discovery, repeated exact-byte restoration and verified no evidence/historical diff before committing.

No installation, release-manifest regeneration, acceptance-evaluator claim, browser-delivery claim, or learning-superiority claim is made by this implementation report.
