# Teach Pro Max publication archive

This directory preserves the complete design, evaluation, implementation-status,
upgrade-planning, and historical-evidence trail behind the public
[`teach-pro-max`](../../skills/teach-pro-max/SKILL.md) skill.

## Directory map

| Path | Contents | Install status |
|---|---|---|
| `../../skills/teach-pro-max/` | Public wrapper plus the complete byte-preserved engine, distribution verifier, and manifest | Installed by the skills CLI |
| `USAGE-GUIDE.md` and `USAGE-GUIDE.html` | Canonical invocation, installation, visualization, evidence, privacy, and persona deployment guide | Documentation only |
| `../../personas/teach-pro-max-agent-persona/` | OpenClaw-, Hermes-, Codex-, and Gemini-adaptable persona bundle | Copy selectively after reviewing existing workspace identity |
| `research/` | Reports 01–10 in canonical Markdown with HTML companions, tracker JSON, browser index, and the site renderer | Documentation only |
| `historical/evidence/` | Original forward attempts, integration receipts, reviews, provenance, and verification artifacts | Historical evidence only |
| `historical/STATUS.*` | Original candidate's release-status statement in Markdown, HTML, and JSON | Historical snapshot only |
| `releases/` | All original candidate archives plus immutable release archives and sibling receipts | Historical source packages |
| `SOURCE-MANIFEST.json` | File-level source/destination/hash ledger for this publication | Provenance |

## Naming decision

The discoverable wrapper is named `teach-pro-max`. The embedded engine keeps its
original `prax-teach-v2` identifiers and bytes because its event hashes, schema
namespaces, study arms, fixtures, tests, and receipts are content-addressed.
The research dossier likewise keeps its original filenames and wording where
changing them would falsify history.

## Evidence decision

Historical receipts remain byte-preserved and therefore continue to describe
only the embedded `prax-teach-v2` engine bytes. A second documentation copy is
kept under `historical/` for audit browsing. The receipts do not cover the new
wrapper and must not be presented as a current immutable `teach-pro-max`
release or as human-learning evidence.

## Install

```bash
npx skills add praxstack/skills-and-personas --skill teach-pro-max
```

Direct source:

```text
https://github.com/praxstack/skills-and-personas/tree/main/skills/teach-pro-max
```

Expected skills.sh page after registry ingestion:

```text
https://skills.sh/praxstack/skills-and-personas/teach-pro-max
```

## Read in order

1. `USAGE-GUIDE.md` (or its self-contained `USAGE-GUIDE.html` companion)
2. `research/06-teach-prax-teach-v2-comparison.md`
3. `research/07-prax-teach-v2-implementation-status.md`
4. `research/08-zero-api-visual-runtime-upgrade-plan.md`
5. `research/09-zero-api-visual-runtime-tracker.md`
6. `research/10-zero-api-autonomous-goal.md`

The upgrade plan is a plan, not a claim that the future interactive visual
runtime or external learner-evidence gates are complete.

## Evolution checkpoint and next goals

The [19 October checkpoint](../../archive/teach-pro-max-evolution-20261019/README.md) preserves source history, the accepted general engine, Atlas, reviews and v2.1/v2.2 lesson outputs. The [coordinated goal briefs](goals-20261019/README.md) split general-teacher integration from C-adapter repair. Both are review material; neither changes the installed skill or approves a new implementation budget.
