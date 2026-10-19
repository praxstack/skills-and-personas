# Public history cleanup plan

Status: review only; no branch deletion or history rewrite performed
Date: 2026-10-20

## Confirmed public refs

- `origin/prax-teach-eval/eval-freeze-v2`
- `origin/prax-teach-eval/v2.1-main`
- `origin/prax-teach-eval/v2.2-candidate`

These refs expose the old holdout routing prompts. They are no longer hidden
and must not be reused as a private acceptance set.

- `origin/archive/prax-teach-handoff-20261019`
- `origin/candidate/teach-c-adapter-20261019`
- `origin/candidate/teach-general-20261019`

These refs retain large Prax Teach archives, local-path evidence, or both. The
archive and candidate refs also keep roughly 481 MB of historical tar payloads
reachable. Current `main` contained the unrelated `deliverables/teach-pro-max/
codex/codex-cli/` folder; the hardening candidate removes it from the current
tree, but old Git objects remain public.

The broad text scan found many local absolute paths in historical evidence.
No secret scanner finding lands in the hardening candidate's changed files.
The prior bounded scan and the current Gitleaks pass did not establish a live
key or token. This does not make the exposed holdout or personal-path material
appropriate for a public branch.

## Proposed cleanup

1. Save an offline bundle of every ref and tag, plus SHA-256 hashes, outside the
   public repository.
2. Create a new private hidden-test bank. Publish only its version and digest.
3. Delete the three `prax-teach-eval/*` refs and the obsolete archive/candidate
   refs after comparing them with the offline bundle.
4. Decide whether public removal requires a full history rewrite. Branch
   deletion removes ordinary discovery but cannot recall existing clones,
   forks, caches, or downloaded release assets.
5. If a rewrite is approved, freeze pushes, publish an exact path/object list,
   run `git filter-repo` in a disposable mirror, verify every retained tag and
   release, force-push once, and ask GitHub Support to purge cached sensitive
   objects where applicable.
6. Re-clone normally and with `--mirror`; prove that removed paths and large
   objects are unreachable before reopening pushes.

Steps 3 through 5 are destructive external operations. They need a separate
approval against the exact ref and path list.
