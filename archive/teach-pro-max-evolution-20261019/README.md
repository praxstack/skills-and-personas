# Prax Teach evolution checkpoint, 19 October 2026

This archive preserves the general teacher, the C-focused v2.1/v2.2 candidates, reviews and actual lesson outputs before the next integration pass. It does not install or promote a candidate.

## Sources

- `v2.2-source.bundle`: complete 216-commit candidate history with all original branches/tags; final candidate a38becaee4e63b455105c394f825bce0fde420fa.
- `candidate-source.tar.gz`: tracked source, tests, lessons, specifications and reviews at that commit.
- `accepted-general-source.tar.gz`: installed accepted general Prax Teach v2 source, including hidden directories, without dependency/runtime caches.
- `teach-pro-max-source.tar.gz`: local Teach Pro Max snapshot before syncing newer remote work. The original source commit is be26eb8f6ec65932adfec138b2cddbe0a5d64b48.
- `prax-teach-v2-clean-install.zip`: original portable baseline, preserved unchanged.
- `neuron-atlas-production.tar.gz`: Atlas demonstrator, source, stills, narrated film, reports and verification, without `.tools`.
- `reviews-and-research.tar.gz`: council and independent reviews.
- `v2.1-rc1.tar.gz.part*` and `v2.2-final.tar.gz.part*`: complete four-lesson output archives. Parts are ordered by their three-digit suffix and stay below GitHub's per-file limit.
- `REVIEW.md`: latest independent review and proposed division of work.
- `LOCAL-CHECKPOINT.json`: historical local checkpoint inventory. Its full runtime-containing local snapshots are not uploaded; the source-only snapshots above replace them for this publication. Its absolute paths describe the original machine, not required restore paths.

The original lesson-archive SHA256SUMS each includes a stale hash of itself. All other listed payloads matched. `PUBLICATION.json`, stored outside the archived payloads, supplies current outer checksums without rewriting historical evidence.

## Verify and restore

From the repository root:

```sh
python3 archive/teach-pro-max-evolution-20261019/verify.py
python3 archive/teach-pro-max-evolution-20261019/restore.py candidate-source.tar.gz --dest /tmp/prax-candidate-source
python3 archive/teach-pro-max-evolution-20261019/restore.py v2.2-final.tar.gz --dest /tmp/prax-v22-artifacts
```

Restore refuses an existing destination. `v2.2-final` restores the actual stills, explorers, Q&A, cards, narration and films. Restoring source does not download its tools or install a skill. To recover git history, use `git clone archive/teach-pro-max-evolution-20261019/v2.2-source.bundle /tmp/prax-history`.

The remote main branch already contains a newer general engine at `skills/teacher/`, source commit e1d196e74ed88df3f5cdce8a06390331f9862300. Preserve and evaluate it before creating a new implementation. The installed local skills were not changed by this publication.

## Evidence limits

All four v2.2 full claims builds fail. The cited six-request smoke worktree and raw smoke outputs are missing and are not represented as preserved. Downloaded tools/models, dependencies, live learner state, private account configuration and unrelated material are excluded. Earlier evaluation attempts remain in the original local project; this package contains the original portable baseline, complete v2.1/v2.2 source history and the named review/output checkpoints, not every historical scratch directory.
