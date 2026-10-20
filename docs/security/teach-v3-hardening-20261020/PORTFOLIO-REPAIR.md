# Portfolio product repair — 2026-10-20

The new transcript-pipeline entrypoint now has its executable implementation. Nineteen tracked files were copied from the canonical `skills/transcript-pipeline/scripts/` tree at commit `444f20d`, including aggregate resource budgets, transport tests, the sandbox runner, two Dockerfiles, wheel hashes, and sandbox setup documentation. No cache files were copied.

The copies are byte-identical except for three prompt paths in `run_chat_pipeline.py`: `docs/prompts/stages/stage1-refine.md`, `stage2-synthesize.md`, and `stage3-enhance.md` become the corresponding `references/` paths. Both entrypoints and all divergent skill content remain. The copied setup documentation retains canonical command paths; it builds the same reviewed image and is not a second setup recipe.

Ten existing entrypoints received bounded repairs:

- Blueprint creator: five local Markdown links now point to existing top-level reference files.
- Spec creator: four local Markdown links now point to existing top-level reference files.
- Techtutor: the frontmatter name is `techtutor`; the visible persona stays intact.
- Book mirror, draft in voice, eiirp, skill autobench, skillify, soul audit: six discovery-description syntax substitutions preserve meaning. Body instructions and thresholds are unchanged.
- Idea lineage: removed the missing takes-versus-facts document pointer while retaining the full requirement to keep holder-attributed takes separate from the brain owner's hot facts.

## Verification

`python -B -m unittest discover -s scripts -p test_portfolio_repair.py -v`: **5 passed**. This checks every tracked source/setup/test file, executable bits, missing/extra files, and the exact three permitted substitutions. Negative controls reject runtime drift and a different prompt destination. It imports all 11 runtime/library modules and checks `--help` for all 10 CLIs.

The synthetic smoke actually ingests a temporary two-segment transcript, verifies content/noise classification and matching ledger/manifest segment IDs, then runs the guided runner. The runner returns its expected pending-chat code **3**, writes a stage1 handoff pointing to an existing prompt, records completed ingestion and waiting-for-chat status, and preserves the transcript and deterministic ledger. It does not claim completion of chat synthesis or publication.

`python -B -m unittest discover -s new-skills/transcript-pipeline/scripts -p 'test_*.py' -v`: **72 discovered, 39 passed, 33 skipped**. Skips are 32 explicitly opt-in Docker cases and one browser-test module requiring Playwright. No live Docker control, network enrichment, account login or private learner access was used. The Task7 test-fixture ownership review remains a separate follow-up; this copy preserves canonical source pending that correction.

Tests ran in `/tmp/task6-portfolio-venv`, with existing local cached requests dependencies exposed through a temporary `.pth` file. Initial stock-Python import checks failed because requests was absent. Offline wheel installation could not satisfy platform-specific charset-normalizer; no dependencies were downloaded. The final run passed using existing local cache contents. `git diff --check` passed.

## Remaining portfolio debt

The unchanged live audit reports **129 entries, 115 unique names, 14 duplicate names, 20 lint failures, 126 link findings, zero collection errors, passed=false**. Correcting techtutor's declared name exposes the fourteenth real duplicate; no duplicate was hidden, renamed away or deleted.

Remaining lint failures are ten long entrypoints, seven directory-policy findings and three top-level README findings. Link findings fell from 136 to 126 through nine real reference repairs and removal of the missing idea-lineage pointer. The remaining 126 include 115 frozen attempt findings and 11 contextual/historical findings described in the triage. Frozen evidence, scanners, lint rules, evaluators and historical reports were not changed.

Further work requires explicit scope: reconcile duplicate invocation ownership without losing content; consider governed directory/length policy changes separately from product edits; locate the upstream takes-versus-facts document with provenance before restoring a document pointer. Any future canonical runtime edit must update the copy and pass the parity regression.
