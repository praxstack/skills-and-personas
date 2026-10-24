# Current portfolio diagnostics, 2026-10-20

This continuation repairs tooling and reporting. It does not close the duplicate
identity, whole-portfolio lint, or link-cleanliness recommendations.

## Delivered

- Both legacy scripts with former-home roots (`check_links.py` and
  `fix_lint_issues.py`) now derive their root from their checkout location.
- `scripts/portfolio_audit.py` inventories both top-level skill collections,
  reports duplicate frontmatter names and entrypoint hashes, and runs existing
  lint and link diagnostics without replacing historical `_audit/*.json` files.
  It writes JSON to stdout. `--check` exits nonzero for outstanding findings;
  report mode exits nonzero for collection errors or an empty inventory.
- `scripts/portfolio_test.py` checks missing links, divergent duplicate
  preservation, malformed metadata, missing collections, report/check exit
  semantics and portable legacy roots.
- `.github/workflows/portfolio.yml` tests those diagnostics, publishes the current
  counts and duplicate paths in the job summary, and retains the full JSON as an
  artifact. This is explicitly a diagnostics job, not a clean-portfolio gate.
- `SECURITY.md` now includes executable tooling, installation, runtime resources,
  generated artifacts, uploads and private state. It gives the concrete GitHub
  private-advisory path without claiming that reporting has been enabled.

## Local evidence

Using Python 3.13 and PyYAML 6.0.3:

```sh
python scripts/portfolio_test.py -v
python scripts/portfolio_audit.py > /tmp/portfolio-current.json
python scripts/portfolio_audit.py --check > /tmp/portfolio-check.json
```

The five diagnostic regression tests passed. Report generation succeeded and
returned `passed: false`; strict checking exited 1. Current observations:

| Observation | Count |
|---|---:|
| Top-level entries | 129 |
| Unique identity names | 116 |
| Duplicate identity names | 13 |
| Legacy lint failures | 28 |
| Heuristic link findings | 136 |
| Collection errors | 0 |
| `allowed-tools` declarations | 0 |

All 13 duplicate pairs have different entrypoint content: backend-pe,
blueprint-creator, chronicle, concept-cartographer, constellation-team,
frontend-pe, idea-capturer, lecture-alchemist, obsidian-cli, spec-creator,
svg-logo-designer, transcribe-refiner, and transcript-pipeline. Each pair spans
`skills/` and `new-skills/`. No pair was deleted, renamed or merged.

The existing `_audit` pytest suite returned **37 passed, 2 failed**. Its two
integration failures concern existing long entrypoints/top-level README files
in autonomous-orchestrion and orchestrion-universal-agent-router, and the agents
subdirectory in techtutor. The test invokes the old report writer; its generated
historical report change was restored afterward. Historical reports are unchanged.
The workflow YAML parsed locally; remote Actions execution has not occurred.

## Remaining boundaries

The 136 link findings use the existing heuristic scanner and need triage before
being treated as broken user-facing links. It scans entrypoints and recursive
references, not every repository document. The inventory excludes nested skill
identities and packaged archives; identical entrypoint hashes would not prove
identical skill directories. Duplicate consolidation requires comparing the
actual divergent guidance and choosing an explicit migration strategy.

A clean portfolio gate still fails. Archive freshness, dependency lock coverage,
continuous secret scanning, installation pinning, capability enforcement and
artifact isolation remain separate work. No blanket `allowed-tools` metadata was
added, and metadata would not enforce a sandbox. Private vulnerability reporting
availability was not verified. Existing frozen evaluations, release archives and
historical evidence were not changed.
