# Task 1 report — subscription evaluation revision

Status: implemented and publicly smoke-tested; ready for independent review and bank/configuration freeze. No hidden scenario, candidate quality run, teaching candidate edit, installed-link change or promotion occurred. All target calls during setup used identical public fixtures in both named arms.

## Delivered

Created the standalone subscription runner/tests/README, EVALUATION-CONTRACT-v2.md and APPROVAL-2026-10-16.md. The runner consumes two package roots plus independent teaching-only id/turns JSON, supplies a fixed hashed normative bundle, preserves real sequential role replay without early future turns, runs independent paired workspaces/auth homes, enforces per-arm deadlines, kills timed-out process groups, retains actual responses/JSONL/artifacts/prompts, and hashes receipts. Missing independent scoring/inspection is refused; a small arithmetic aggregator applies the unchanged 36-record acceptance matrix and numeric gates without subjective grading. All product thresholds, families/repetitions, four secondary smoke scenarios, 120-minute candidate budget, two-candidate stop rule and protected conditions remain as v1.

The existing offline evaluator and its tests were inspected read-only. Safe reusable patterns were its SHA-256 byte helper, package exclusion set, teaching/grading input separation, manifests and fail-closed validation. The new transport uses independent small standard-library implementations of those patterns rather than importing a protected candidate package's evaluator or changing its offline/network behavior. FEASIBILITY.md's four compatibility gaps are addressed by separate transport, actual baseline/candidate arms, retained outputs and independent rubric scoring.

## Actual boundary and measured limits

A strict OS runtime allowlist aborted Codex with exit -6; no success is claimed for it. A narrower OS profile authenticates and denies file-data reads under /Users except the current arm workspace, private CLI home and executable; it also denies /Volumes, /private/tmp and /private/var outside the private CLI home. Outside writes are denied except /dev. Metadata and system runtime reads remain allowed. Final per-arm sandbox.sb and command.json are retained. The documented layout uses /Users receipts.

Shell/read/browser/app/MCP/plugin/hooks/memory/image/delegation feature paths are disabled; no unrelated user config/rules are inherited. Private CODEX_HOME contains only minimum copied existing auth at startup, private modes, and normal cleanup. The trusted CLI must read this auth home. The model initially listed helper names, so absence of calls was not treated as absence of capability. A paired actual shell control proved the enabled arm called a real tool and disclosed a random public sentinel; the disabled arm did neither. An additional forced apply_patch probe revealed it remains exposed and could create a harmless workspace file under workspace-write. Final CLI mode is therefore read-only, combined with the measured outer boundary. A forced patch under the combined configuration was explicitly rejected by the CLI as blocked by read-only sandbox/approval settings; no file was created. Every observed executed tool event makes runner transport fail. We do not claim all helper schemas are absent.

Final direct same-build filesystem probes denied hidden-bank, source and other-arm sentinel reads, symlink escape and outside writes. Public sentinels contained no secrets or hidden scenarios. Live final inference worked under that combined boundary, with all four sequential paired responses retained and no executed tool events. This measures text content/adaptation in tool-unavailable conditions; real rendering, persistence/resume, consent and filesystem runtime behavior require separate controller inspection/CLI integration tests. No fictional artifact/tool claims are allowed. No rendered/human-learning success is claimed here.

During public setup, imported source and copied package files acquired nlink=2 without changed bytes; cause remains unverified. Standard shutil copying was checked independently and produced separate nlink=1 files. We did not infer model access from metadata-only changes. The controller explicitly ruled before freeze to retain initial alias rejection, then compare final exact hashes/path sets and reject symlinks while recording nlink-only changes. source-link-diagnostics.json records before/after. External hardlink alias creation alone therefore does not fail final integrity; inode immutability is not claimed. Two failed diagnostics preserved the earlier stricter final-check errors. Initial alias imports still fail.

## Commands and results

Installed capabilities were measured with `codex --help`, `codex exec --help`, `codex features list` and `codex --version`; complete outputs are retained. CLI is 0.163.0. `gpt-6.1` was rejected as unsupported for ChatGPT authentication; actual successful tests use `gpt-6.1-sol`. No paid API or account changes were made. No unsupported-feature warning appeared; the CLI emitted only its known temporary-helper/PATH warning on ordinary successful runs.

Unit command:

```sh
python3 -m unittest discover -s tools/teaching-evaluation -p 'test_*.py' -v
```

Result: 12 tests passed. Coverage includes paired separation/error retention, grader-data omission, timeout/process-group propagation, output retention/hashing, initial symlink/hardlink rejection, final metadata-only distinction, missing scoring/inspection refusal, tool-event rejection, dependency exclusions and unchanged numeric gates. Fake execution is used only for deterministic failure/timeout paths; public inference results are real CLI calls.

Final authenticated smoke command (exit 0):

```sh
python3 tools/teaching-evaluation/subscription_runner.py \
  --baseline /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/final-frozen-public-package \
  --candidate /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/final-frozen-public-package \
  --scenario /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/public-final-smoke.json \
  --output /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/final-measured-smoke \
  --model gpt-6.1-sol --seconds 150 --repetitions 1
```

This is a public one-replicate two-turn probe, not a hidden candidate evaluation. Both arms use identical public baseline normative content. All four calls exited zero without timeout, had actual nonempty responses, and emitted no tool events. Future turn 2 was absent from both initial prompts. Final manifest/content hashes match, source bytes/path sets match, and runner hash matches the tested source. The result correctly remains scored:false, accepted:false, with hidden eligibility awaiting independent freeze.

Additional live probe commands:

```sh
python3 /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/paired-tool-probe.py
python3 /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/patch-tool-probe.py
python3 /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/patch-readonly-probe.py
python3 /Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/patch-confined-probe.py
```

The direct OS probes used `/usr/bin/sandbox-exec -f <generated-profile> /bin/cat <public-sentinel>` and `/bin/sh -c 'echo public > "$1"' probe <outside-test-file>`; all forbidden reads/writes returned 1/Operation not permitted. Broker work writes were allowed, as required for retained responses. The forced patch diagnostic's output-last-message was deliberately outside its permitted work tree and was denied too; its stdout/stderr retains the model/CLI rejection. Final normal smoke writes its last-message inside the permitted workspace and succeeded.

## Evidence index

All receipts are under `/Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/`:

- `unittest.log`: final 12-test passing output.
- `final-measured-smoke/`: final combined-boundary paired multi-turn run, actual responses, configuration, commands, sandbox profiles, prompts, source-link diagnostics and hashes.
- `final-review.json`: independent local verification of manifest, same runner hash, four exit-zero/no-tool turns, future-turn separation and absence of unsupported warnings/outside model write.
- `final-filesystem-probes/final-build-results.json` and `final-build-sandbox.sb`: current-build denied read/write/symlink probes.
- `paired-tool-probe/`: positive/negative shell control, random public sentinel, exact command/configuration and real events.
- `patch-tool-probe/`, `patch-readonly-probe/`, `patch-confined-probe/`: actual helper discovery and read-only rejection.
- `broker-frozen-probe/`: explicit list/use-tools and public hidden/other-arm sentinel request; no sentinel disclosure or outside write. Tool names were reported, so this alone was not accepted as capability proof.
- `smoke-1` through `smoke-5`, `broker-*`, `confined-final-smoke`, `confined-clean-smoke`: retained failed/superseded public diagnostics; do not call these final acceptance results.
- `source-preservation.json`: protected offline evaluator matches HEAD exactly; SHA-256 `5684a2950e4f05ab273b3b0786d7d1a73f1c02e0a89fa0187d0b3e27cfdabe90`.
- `codex-help.txt`, `codex-exec-help.txt`, `codex-features.txt`: installed capability evidence.

Final runner SHA-256: `dcd2b93eef31ccacdc3500179dc0567c592072c47847539594665964a8d41ed1`.

## Self-review

No original skill/offline evaluator bytes or global configuration were changed. Named paths only are staged. Receipts and temporary credentials are outside the teaching package; no credential bytes were intentionally logged. Both arms use identical transport/path sets/deadlines, separate role histories and output trees, and no cross-arm generated state. Scoring keys are neither accepted by scenario validation nor passed to teaching prompts. The runner does not silently accept missing grades, inspections, complete repetition matrix or nonnumeric checks. Public diagnostics remain public and no outcome implies human learning.

Remaining limits: independent review and bank/config freeze are still required; actual runtime/renderer checks and secondary-host smoke are separate work; CLI helper schemas are not all removable but the measured combined boundary constrains their effects; trusted auth-home reads remain necessary; abrupt host termination can leave private temporary auth requiring cleanup; link-count changes have unknown cause and are diagnostic at final verification. No promotion/held-out quality claim is authorized by this task alone.

## Review fix round 1

Fixed the Important failure-finalization finding. Event decoding now validates JSONL event/item shapes without raising for malformed/truncated/invalid-Unicode or excessively nested JSON. Each turn records `events_parse_error` and fails closed with `no_tool_events:false`; raw stdout/stderr, turn status, conversation, artifact hashes, final failed result and manifest are finalized normally. Valid event streams retain their existing tool checks. No inference retry was added.

Regression uses deterministic timed-out/nonzero execution with truncated JSON, non-object event, malformed item and non-string event type. For both actual runner arms it verifies raw stream retention, explicit decoding diagnostic, timeout/exit failure, conversation/artifact/result files and matching manifest hashes. The existing paired/timeout/gate tests remain passing.

Command: `python3 -m unittest discover -s tools/teaching-evaluation -p 'test_*.py' -v`. Result: 13 tests passed. Exact output: `/Users/prax/Developer/prax-teach-evaluation-20261016/subscription-v2/unittest-fix-round-1.log`.

Current runner SHA-256: `0e54d07a67c1dbe324d30fdb6f3733b46fae2cd3b32ff8b8380a12cb1047e3a0`. Earlier same-build live smoke/probe claims remain scoped to the original reported runner hash `dcd2b93eef31ccacdc3500179dc0567c592072c47847539594665964a8d41ed1`. This patch changes event validation/failure receipt handling only; CLI invocation, sandbox, supplied teaching data and inference transport are unchanged. Per controller instruction no additional authenticated smoke was run. No same-byte live claim is made for this revised hash; independent freeze must bind the revised version explicitly.

Self-review: only runner, focused regression and this appended report changed; transport failure remains non-accepting and no keys/source/global settings were modified.
