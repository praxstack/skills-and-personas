# Unaccepted candidate packaging

The separately named consent-aware evaluator v2 was approved and adopted on
2026-10-24 (`bf0bcf9`); full validation selects that canonical version. The old
reload-without-consent failure remains historical evidence. The final playback
source `eaa524e` passed three consecutive original narrated fresh-container runs,
each 22/22 plus lesson/visual QA and zero phase PID-limit events. Both disclosed
independent cases pass later regression; their earlier failures remain retained.
Current delivery and exact scope: `deliverables/teach-resume-20261024/README.md`
in the full checkout. These results do not imply a stable release or activation.

The source ZIP supports individual included skill build/check commands and the
embedded vendor/distribution verifiers. Full regression orchestration and CI setup
(`run_teacher_regressions.py`, `setup_teacher_ci.sh`, `ci_media_regression.py`)
require the complete exact Git checkout, its Git metadata, test utilities and
new-skills mirror. They are not archive validation commands. The runner and setup
refuse incomplete source archives explicitly before tests or dependency setup.

After review and commit, use a new empty output directory:

```sh
python3 scripts/package_teacher_release.py --candidate --revision "$COMMIT" --version 3.0.2 --output "$NEW_SOURCE"
```

The deterministic Git-object ZIPs include transcript-pipeline separately and
example source in the combined archive. Generated media is not in Git. Repeat
to another directory and compare ZIP hashes. Extract into temporary folders;
run teacher vendor verification and teach-pro-max distribution verification,
then `install.sh --copy --with-subskills --dir <temporary-agent-skills>`.
Also verify teach-pro-max alone with teacher absent. Never target live skills.

To assemble current source+demo and a complete historical-inclusive Dot handoff:

```sh
python3 scripts/package_teacher_handoff.py --source "$NEW_SOURCE" --media "$BUNDLE" --historical "$HISTORICAL" --output "$NEW_HANDOFF" --media-provenance "$EXACT_RUN_AND_SOURCE"
```

Inputs must be regular directory trees; links are rejected. `BUNDLE` is the
completed six-format bundle. Include retained audio/video and receipts under
that staged media tree as needed. `HISTORICAL` is an explicit staged directory
containing the preserved historical ZIP and its original receipts, with every
requested historical artifact inside that ZIP. Do not stage the old extracted
tree or its rebuild script as duplicate payload.
The preserved 644145442-byte historical ZIP is never rebuilt or overwritten.
The helper verifies source hashes, ZIP CRCs and each payload hash, and writes
external receipts. It labels historical content separately from current source.
An output already present is refused. Packaging does not prove delivery to Dot.

The ARM CI job explicitly builds pinned-base course/enrichment/media images,
uses the returned immutable IDs with the default context, installs hash-locked
requests/Playwright wheels, and fails if required controls skip. Its synthetic
media sequence has three fresh runs and stops at the first failure. Revision-specific actual narrated results remain distinct from synthetic CI. Existing core and
portfolio diagnostic jobs retain their scopes. Runtime limits and existing
checker assertions remain unchanged.
