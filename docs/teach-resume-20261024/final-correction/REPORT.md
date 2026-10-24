# Combined final review correction

Read final-fix-brief.md first and the completed full final-review.md before
source commit. Controller explicitly confirmed the full authored review was
complete before dispatch. No subagents or sibling PLAN reads. Source commit
`e97fe5b` follows `31b9ced`; no runtime, governing, installed, private input or old
artifact bytes were changed. No Docker or narration suite was rerun.

## Corrections

Chose the reviewer's explicit full-checkout validation boundary. The shipped
runner now checks for Git metadata, required repository test/handoff utilities
and the new-skills mirror before any discovery or suite execution. An extracted
archive gets a clear actionable refusal rather than missing suites or zero-test
output after expensive work. CI setup also refuses before dependency/platform
setup. Combined START-HERE and setup/candidate docs explicitly identify those
utilities as complete exact Git checkout only. Individual skill checks and
embedded vendor/distribution verifiers keep their supported scope. No acceptance
assertion or required suite was weakened or silently skipped.

Ordinary core workflow and required runner now select test_find_tool.py and
test_manim_resolution.py. Current course SKILL/sandbox/MECHANISM/example/candidate
prose describes approved consent v2 and the actual eaa524e three-run results;
old failures remain explicitly historical. Generic source/handoff notices now
require evidence for the named revision and cannot attach this run's success to
an arbitrary requested revision. Generic manifest scope likewise makes no
approval claim. The public historical INSPECTION.md is included in the combined
source archive, resolving both merge-sort and momentum README links.

## Exact commands and outputs

All ran from this current worktree, with PYTHONDONTWRITEBYTECODE=1 for tests.
Complete outputs are committed in docs/teach-resume-20261024/final-correction/.
Cached Headroom Python3.13.17 only; no package/environment changes.

```sh
/Users/prax/.local/share/uv/tools/headroom-ai/bin/python -m unittest discover -s skills/teacher/scripts/tests -p test_find_tool.py -v
/Users/prax/.local/share/uv/tools/headroom-ai/bin/python -W error::ResourceWarning -m unittest discover -s skills/teacher/scripts/tests -p test_manim_resolution.py -v
/Users/prax/.local/share/uv/tools/headroom-ai/bin/python scripts/run_teacher_regressions.py skills/teacher/scripts/tests test_find_tool.py
/Users/prax/.local/share/uv/tools/headroom-ai/bin/python scripts/run_teacher_regressions.py skills/teacher/scripts/tests test_manim_resolution.py
/Users/prax/.local/share/uv/tools/headroom-ai/bin/python -m unittest discover -s scripts -p test_candidate_packaging.py -v
python3 skills/teacher/scripts/vendor.py verify
bash -n scripts/setup_teacher_ci.sh
git diff --cached --check
```

All exit 0. Discovery8 and Manim9 pass directly and through the ordinary required
runner, zero skips. Packaging's comprehensive repeat/member/handoff control1/1
passes in33.668s. Vendor16 vendored/6 copied/6 native, zero problems; changed course
and mechanism docs are native public docs, so no vendored tree identity changed.
Mocked Kokoro download stdout is explained by the completed review: URL retrieval
is patched to a temporary local fixture; no real model download or shared mutation.

New committed-source build commands (both exit0):

```sh
python3 scripts/package_teacher_release.py --revision e97fe5b --version 3.0.2 --candidate --output deliverables/teach-resume-20261024/source-e97fe5b
python3 scripts/package_teacher_release.py --revision e97fe5b --version 3.0.2 --candidate --output deliverables/teach-resume-20261024/repeat-e97fe5b
```

Each of the four archives and external sidecars is byte-identical across builds.
An independent Python zipfile pass compares every member's SHA256 and stored mode
against the external manifest and exact e97fe5b Git blobs/modes, with only generated
START/CANDIDATE notices treated as generated members. Public INSPECTION dependency
is present. Existing private banks/sessions/models/caches remain outside selection;
public synthetic schema fixtures are unchanged. Full stdout/manifest and independent
comparison summary are external receipts in final-correction/.

Actual complete archive extraction into a temporary directory then ran:

```sh
python3 scripts/run_teacher_regressions.py scripts test_render_receipts.py
bash scripts/setup_teacher_ci.sh
```

First exits1 with no stdout:
“Full regression validation requires the complete exact Git checkout, including
Git metadata, test utilities and the new-skills mirror. Source archives are
unsupported; no tests were run.” Second exits2 with no stdout and the corresponding
CI-setup/full-checkout message ending “no setup was run.” Neither emits Ran0 tests,
discovers tests, provisions dependencies or performs Docker work. Complete command
arrays/return codes/stdout/stderr are in archive-refusal-controls.json.

## Preservation and final source/package scope

Rehashed all six governing files, final template6a978340...,1546 installed files,
five resolved links and all36 final demo members: unchanged. Existing d808/eaa
archives and demo files are untouched. `preservation.json` records the scope.
Current status HTML and README point to source-e97fe5b packages while retaining
explicit runtime eaa524e/demo-eaa524e provenance. They explain full-checkout-only
regression/setup boundaries and preserve earlier snapshots. Runtime passes and
screenshots remain their already-reviewed original source scopes; no fresh blind,
subjective audio or learner outcome claim is added.

Source-only and shell syntax checks pass. Exact generated historical demo whitespace
remains untouched as previously documented. Whole-branch correction review is the
controller's next step. No push, merge, installation, publication or activation.

Independent archive comparison completed successfully: all3305 members across four
archives match recorded SHA256/mode and selected exact Git objects. All repeat
archive/sidecar bytes match. Actual extracted runner/setup refusal controls pass.
