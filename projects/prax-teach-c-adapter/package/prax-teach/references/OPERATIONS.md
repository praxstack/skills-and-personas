# Operations: package, install, rollback, learner state, renderer

Read this when you package or install v2.1, roll it back, touch learner state, or render a Markdown note.

## Package (AC-8.1)

```
ptk package --dry-run       # list and check, write nothing
ptk package [--out DIR]     # default $PTK_STATE/package/prax-teach
```

It copies the shipped files (no `__pycache__`, `node_modules`, `build/`, `.DS_Store`, bytecode or logs),
writes `INSTALL-MANIFEST.json` (sha256 per file and one tree hash; no timestamps, so two builds of the
same source match), and checks: at most 5 MB, no home-directory paths, no SKILL.md below the root. Then
it runs the host discovery check. Exit 1 on any problem. It refuses to write into `~/.agents`,
`~/.claude`, `~/.codex`, `~/.hermes` or `~/.config`.

## Hosts (AC-8.2)

`ptk/package.py` models how each host finds skills:

| Host | Where | How |
|---|---|---|
| Claude Code | `~/.claude/skills`, project `.claude/skills` | one level: `<dir>/<name>/SKILL.md` |
| Codex | `~/.agents/skills`, `~/.codex/skills`, repo `.agents/skills` | recursive, hidden dirs skipped (checked against `codex app-server` 0.163.0, which also stops a few levels deep) |
| Hermes | `~/.hermes/skills` | Hermes's own walker: follows links, prunes caches and support dirs |
| OpenCode | `~/.config/opencode/skills`, `~/.claude/skills`, `~/.agents/skills` and project dirs | recursive, hidden dirs included (the stricter reading; OpenCode isn't installed here) |

`tests/test_hosts.py` builds a throwaway HOME per host under `$PTK_STATE/hosts/<host>/`, laid out like
this Mac (v2 in `~/.agents/skill-library`, `~/.agents/skills/prax-teach-v2` linking to it, each host dir a
mirror), and checks exactly one prax-teach entry from three working directories, before and after the
flip. Real Codex and Hermes are asked too when installed. The real home is only read.

## Install and rollback (AC-8.6, D17.12)

From the CLI (integration pass):

```
ptk install --candidate --dry-run                    # the plan, no writes (real HOME)
ptk install --candidate --home H --flip --learner WS # a throwaway HOME; the real HOME also needs --real-home
ptk rollback --dry-run                               # newest record: link it would restore, events it would lose
ptk rollback --record R                              # restore; prints the lost-event count
```

A real install into `~/.agents` waits for Prax (FREEZE amendment pending), so the CLI refuses the real HOME
without `--real-home`.

```python
from ptk import package
rec = package.install(tree, home, flip=True, learners=[workspace])   # snapshot, migrate, flip
package.rollback(rec["record"])                                      # link back, restore, print lost count
```

`install` copies the tree to `~/.agents/skill-library/prax-teach-v2.1` (side by side, never registered),
snapshots each learner workspace to `$PTK_STATE/snapshots/`, and with `flip=True` migrates it to state
schema 2 and repoints `~/.agents/skills/prax-teach-v2`. The rollback record goes to `$PTK_STATE/rollback/`.
`rollback` points the link back, restores each snapshot byte for byte, and prints how many learner events
recorded since the snapshot are lost. Both refuse the real HOME: the real flip is Prax's step (D19.1).

## Learner state (AC-8.4)

`python -m ptk.state` is v2's consent-first state engine, ported (run it with the core venv's Python;
fsrs 6.3.1 lives there). Every v2 command is kept except `route`, `visual-route` and `visual-verify`.
Exit codes are v2's (3 consent, 4 confirmation, 5 safety, 6 validation, 7 not found).

- Schema 1 workspaces (v2) read unchanged. Schema 2 records can't be added until you migrate.
- `migrate WS --snapshot-to DIR`: snapshot first, then only `learner.json` changes.
- `evidence WS --session --concept --observed --gap --next-action`: independent work only, one next action.
- `grant-navigation WS`, then `navigate WS --session --artifact --action [--position]`: navigation needs
  its own consent and goes to `state/navigation.jsonl`, never with attempts. `revoke-navigation` deletes it.
- `snapshot WS --to DIR`, `rollback WS --snapshot DIR`.

Google Drive (WP11): Drive for desktop backs up `~/Developer` and `~/Study` and hard-links each new file into
`<root>/.tmp.driveupload` while it uploads it. `init` refuses a Drive-backed folder unless the learner adds
`--allow-google-drive` to `--consent` (recorded as `consent.synced_location`). `delete` reports copies it finds
outside the workspace and then says `deleted_with_surviving_copies`. A learner's own file with Drive's extra link
is read with a warning naming Google Drive, because it carries the workspace's learner binding (D22.3). Read-only
commands write nothing, extended attributes included, without active consent. Tests set `PRAX_TEACH_SYNC_ROOTS`
to fixture folders and never look at a real Drive folder.

## Renderer (AC-8.3)

`ptk/node.py::render_markdown(source)` runs `node/render_markdown.mjs` with SOURCE_DATE_EPOCH taken from
the source's sha256. The page is one self-contained HTML file: inline SVG (static, `role="img"`, named),
MathJax SVG for `$...$` and `$$...$$`, `<video controls>` with a captions track (embedded as a data: URI
so it loads from file://), a CSP with hashed style blocks and no scripts, and the sha256 of the source
and of every local asset. Anything it can't render safely is rejected with a reason, never dropped.

## Audit

`npm audit` on `node/package-lock.json` (2026-10-18): 0 advisories. sanitize-html is 2.18.1 (fixes
GHSA-g8qq-57p8-ggw5, which matters now that SVG is allowed), and an `overrides` entry lifts
`@xmldom/xmldom` to 0.9.12 (13 advisories in 0.9.10, pulled in by mathjax-full through
speech-rule-engine; tex2svg never loads it, but the lock no longer carries it).
