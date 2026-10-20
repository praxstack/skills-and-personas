# Unaccepted candidate packaging

Task 8 narrated playback did not achieve three consecutive fresh-container
passes. The full-course consent checker proposal awaits approval. Passing unit
or synthetic-media tests does not change either status. No stable publication,
merge or installed-snapshot changes are part of these commands.

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
media sequence has three fresh runs and stops at the first failure. Actual
narrated artifact acceptance remains blocked independently. Existing core and
portfolio diagnostic jobs retain their scopes. Runtime limits and existing
checker assertions remain unchanged.
