# Local rollback repair receipt

Date: 2026-10-20
Scope: local operation; the active v3 installation was not changed

The pre-v3 `teach-pro-max` tree was extracted from Git commit
`f54d334ae709df48983638a250bf9b6a910fa245` into the local Prax Teach releases
area. It contains 804 regular files and no symlinks. The snapshot tree digest
is `5f49514d402db4fc8bb82ba1c7244dd3fdbd54dec10cd5e68288eb677c064a47`.

The activation manifest now restores that read-only snapshot instead of the
mutable repository checkout. Its original manifest was retained beside it as
`manifest.before-rollback-repair.json`.

Verification:

- the snapshot root has mode `0555` and no descendant is owner-writable;
- the snapshot `SKILL.md` SHA-256 matches the same file at commit `f54d334`;
- the rollback script's dry run accepts every current pointer;
- the active `teach-pro-max` pointer still resolves to the v3 release.
