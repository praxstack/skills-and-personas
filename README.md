# Skills and Personas

[![skills.sh](https://skills.sh/b/praxstack/skills-and-personas)](https://skills.sh/praxstack/skills-and-personas)

A curated portfolio of [Agent Skills](https://agentskills.io) for Claude Code, plus the raw personas and knowledge packs they were distilled from.

The canonical, production-ready portfolio lives in `new-skills/` — 38 skills that pass a deterministic linter, a council-reviewed safety gate, and a runtime smoke test. The original source material (personas, md-personas, team-personas, knowledge-packs) is preserved so anyone can see how each skill was derived.

## Portfolio at a glance

- **38 skills** covering backend engineering (orchestrator + 7 language variants), cross-functional team roles (principal, product, QA/security, DevOps, frontend UI/UX, backend system design), multi-mode orchestrators (kingmode, super-mode-core, ultrathink-frontend), design excellence, document production (blueprint-creator, spec-creator, transcript-pipeline, transcribe-refiner), creative (svg-logo-designer, frontend-design-excellence), learning (techtutor, gabriel-petersson-topdown-mentor, lecture-alchemist, professor-alex-interview), personal intelligence (chronicle, idea-capturer, concept-cartographer, baron-von-markup), obsidian automation, and mental-health screening.
- **Every skill** passes the deterministic linter in `new-skills/_audit/lint.py` (frontmatter validity, ≤500 lines, no persona statements, no ASCII art, no top-level README, matching directory names).
- **Every skill** passes the runtime smoke test in `new-skills/_audit/smoke_test.py` (references resolve, YAML parses, persona discipline holds, no missing files).
- **Mental-health content is scoped.** See [SAFETY.md](SAFETY.md) for the mental-health-screening-companion skill scope, 988 + international crisis resources, and instrument attribution (PHQ-9, GAD-7, ASRS v1.1, C-SSRS).

## Repository layout

| Path | What lives here |
|---|---|
| `new-skills/` | **Canonical portfolio** — 38 production-ready skills, each a directory with SKILL.md + references/ |
| `new-skills/_audit/` | Audit trail — inventory, judge rubric scores, lint report, smoke-test report, council review, code-review report, session log, reusable tooling (lint.py, fix_lint_issues.py, smoke_test.py, install.sh, check_links.py, pytest suite) |
| `skills/` | The accepted visual teaching distribution and original skill sources; the separate curated portfolio remains in `new-skills/` |
| `skills/teach-pro-max/` | Public, skills.sh-discoverable adaptive teaching system with runtime tools, schemas, tests, and optional integrations |
| `skills/teacher/` | Standalone visual teacher for any host: picks the medium (hand-drawn diagrams, explorables, animations, narrated video), re-explains on confusion, vendors its video and teaching skills |
| `docs/teach-pro-max/` | Teach Pro Max research dossier, historical evidence, original release archives, and source manifest |
| `personas/teach-pro-max-agent-persona/` | Cross-harness Teach Pro Max identity, user-context, tool, heartbeat, bootstrap, and agent-operation files |
| `personas/` | Multi-file persona packs (system prompts + domain knowledge + examples + platform configs) |
| `md-personas/` | Single-file Markdown persona prompts |
| `team-personas/constellation-team/` | Six role-based team skills (principal, backend-system-design, frontend-uiux, devops-sre, product, QA-security) |
| `knowledge-packs/` | Reference material (ATLAS / Gabriel Petersson learning mentor knowledge packs) |
| `prompts/` | Agent-builder prompts, AI-therapist prompt versions (superseded by mental-health-screening-companion), memory-bank templates |
| `prompts/project-alignment/` | Generic paste prompts: reconstruct any project, install gstack / Superpowers / Matt Pocock / OpenSpec / deep-research, optional report-only QA |
| `prompts/high-end-operator/` | Lifecycle paste-prompt family (Think → Plan → Build → Review → Test → Ship → Reflect). Invokes installed skills; does not copy skill bodies |
| `.claude/agents/` | Claude Code subagents for the constellation-team workflow |
| `.clinerules/` | Cline rules and workflows |
| `opencode-setup/` | OpenCode configuration |
| `SAFETY.md` | Mental-health content scope, crisis resources, instrument attribution |

## Visual teaching: Teacher and Teach Pro Max

`teacher` is the accepted general visual teacher. It gives the complete explanation first, then offers optional practice. It produces mechanism-led stills, interactive explorers, layered Q&A, flashcards, narrated video and interactive video from one sourced lesson model. Courses can resume with explicit consent; a complete static explanation remains available.

Install the standalone teacher:

```bash
npx skills add praxstack/skills-and-personas --skill teacher
```

To retain the `teach-pro-max` invocation, install both entries together. That compatibility entry delegates general teaching to its sibling `teacher`:

```bash
npx skills add praxstack/skills-and-personas --skill teacher teach-pro-max
```

Ask your agent: `Use teacher to explain how a neuron becomes a neural network, with a visual mechanism and an interactive example.` Request the formats you want. Practice and persistent learner records require explicit requests/consent.

- [Teacher source](skills/teacher/SKILL.md) · [compatible entry](skills/teach-pro-max/SKILL.md)
- [Installation, prerequisites and usage](docs/teach-pro-max/USAGE-GUIDE.md)
- [Public downloads](https://github.com/praxstack/skills-and-personas/releases) · [accepted evaluation](deliverables/teach-pro-max/codex/evidence/private-evaluation/candidate4-accepted-redacted-report.json)
- [Teacher on skills.sh](https://skills.sh/praxstack/skills-and-personas/teacher) · [Teach Pro Max on skills.sh](https://skills.sh/praxstack/skills-and-personas/teach-pro-max)

The fixed general evaluation passed 24/24 routing cases and 56/56 end-to-end criteria after the learner accepted all four required recordings. Valid-control acceptance and planted-error detection are separate receipts. These results do not certify human learning gains, every optional renderer, or world-best quality. The development C adapter remains separate and unaccepted.

The complete skill sources and supporting files are public under the repository license, with bundled third-party notices retained. Runtime packages and voice/browser model downloads are separate prerequisites. Historical development archives and failed attempts are preserved; current acceptance does not rewrite them.

## Additional public skills

These portable skills live in `skills/` and can be installed independently:

| Skill | Purpose | Install |
|---|---|---|
| [`superimprove`](skills/superimprove/SKILL.md) | Bounded audit-fix-review-verify loop with non-destructive recovery and honest exit states | `npx skills add praxstack/skills-and-personas --skill superimprove` |
| [`coding-agent-leadership-principles`](skills/coding-agent-leadership-principles/SKILL.md) | Evidence, ownership, scoped authority, and engineering-completion operating floor | `npx skills add praxstack/skills-and-personas --skill coding-agent-leadership-principles` |
| [`cross-agent-handoff`](skills/cross-agent-handoff/SKILL.md) | Privacy-safe, independently verifiable transfers across agents and harnesses | `npx skills add praxstack/skills-and-personas --skill cross-agent-handoff` |

The public `superimprove` edition intentionally rejects destructive reset/clean
recovery, automatic rescue commits, unapproved dependency installation, and
unbounded review loops.

## Install the portfolio locally

```bash
# Clone
git clone https://github.com/praxstack/skills-and-personas.git
cd skills-and-personas

# Install all 38 skills into ~/.claude/skills/ (existing colliding skills auto-backed up)
bash new-skills/_audit/install.sh

# Smoke-test the installed portfolio
python3 new-skills/_audit/smoke_test.py
```

The installer is collision-safe: if you already have a skill in `~/.claude/skills/<name>/`, the installer moves it to `~/.claude/skills/_backup-<timestamp>/` before overwriting. To restore an original, copy it back out of the backup directory.

Alternatively, install individual skills by copying the directory:

```bash
cp -R new-skills/<skill-name> ~/.claude/skills/<skill-name>
```

Then restart Claude Code or let its live-reload pick it up. Trigger skills by their slug (`/skill-name`) or by using terms from their `description`.

## Quality gates (all run locally, reproducible)

```bash
cd new-skills

# Structural linter (0 FAILs required)
python3 _audit/lint.py

# Unit + integration tests for the linter itself (39 tests)
pytest _audit/tests/ -v

# Runtime smoke test on ~/.claude/skills/ installs (requires prior install)
python3 _audit/smoke_test.py

# Broken-link scanner across SKILL.md + references/*.md
python3 _audit/check_links.py
```

## Review process for every skill in `new-skills/`

1. **Inventory and classify** every source file in the repo (skills/, personas/, md-personas/, team-personas/, knowledge-packs/, prompts/)
2. **Judge the source material** — is there real knowledge delta beyond what Claude already knows?
3. **Author** the SKILL.md applying Audience/Goal framing, zero persona statements, anti-pattern discipline, references/ split for anything over 500 lines
4. **Deterministic lint** — name regex, description ≤1024 chars, 500-line cap, no top-level README, no ASCII art in prose, no "You are a..." statements outside code blocks
5. **Automated fixer** for the two most common authoring errors: YAML colon-quoting and Unicode arrow replacement
6. **Runtime smoke test** — YAML parses, references resolve, persona discipline holds
7. **llm-council-plus review** with four Claude models deliberating on architecture, safety, and overlap
8. **code-review-expert pass** — SOLID-equivalents for skills, knowledge-delta check, cross-skill overlap, broken-reference detection
9. **skill-judge rubric** — 8 dimensions, /120, letter grade per skill
10. **skill-auditor portfolio scan** — overlap clusters, verdicts (TRIM / RESTRUCTURE / MERGE / OK)

The full audit trail for the current portfolio is in `new-skills/_audit/` — every report, every decision, every fix.

## Packaging a skill (optional)

To produce a `.skill` archive compatible with ecosystem tooling:

```bash
zip -r new-skills/<skill-name>.skill new-skills/<skill-name>
```

Or regenerate all portable docs + archives via the existing script:

```bash
scripts/build_skills.sh --force-md
```

## Interoperability notes

- **Claude Code** — all 38 skills use the frontmatter extensions Claude Code supports (`description`, optional `allowed-tools`). None rely on `disable-model-invocation`, `user-invocable`, `context: fork`, or other CC-only features unless specifically marked.
- **Other Agent Skill runtimes** — every skill in `new-skills/` conforms to the open agentskills.io specification (lowercase-hyphen names, 64-char max, 1024-char description cap, SKILL.md at directory root).
- **Gemini CLI / Cline / Codex** — see `GEMINI.md`, `.clinerules/`, `AGENTS.md` for tool-specific configuration files preserved from the original repo.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for conventions.

When adding a new skill to `new-skills/`:

1. Create `new-skills/<skill-name>/SKILL.md` with valid YAML frontmatter (`name`, `description`)
2. Run `python3 _audit/lint.py` — must pass with zero FAILs
3. Run `pytest _audit/tests/` — must pass all 39 tests
4. Add per-skill audit notes to `_audit/SESSION_LOG.md` if substantial

## License

MIT for skill content. See [LICENSE](LICENSE).

Screening instruments in `new-skills/mental-health-screening-companion/` retain their original copyrights and attribution requirements — see [SAFETY.md](SAFETY.md) for details.
