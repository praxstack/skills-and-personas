# Skills and Personas

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
| `skills/` | Original skills — superseded by `new-skills/` but preserved for reference and as the source material for several `new-skills/` entries |
| `personas/` | Multi-file persona packs (system prompts + domain knowledge + examples + platform configs) |
| `md-personas/` | Single-file Markdown persona prompts |
| `team-personas/constellation-team/` | Six role-based team skills (principal, backend-system-design, frontend-uiux, devops-sre, product, QA-security) |
| `knowledge-packs/` | Reference material (ATLAS / Gabriel Petersson learning mentor knowledge packs) |
| `prompts/` | Agent-builder prompts, AI-therapist prompt versions (superseded by mental-health-screening-companion), memory-bank templates |
| `.claude/agents/` | Claude Code subagents for the constellation-team workflow |
| `.clinerules/` | Cline rules and workflows |
| `opencode-setup/` | OpenCode configuration |
| `SAFETY.md` | Mental-health content scope, crisis resources, instrument attribution |

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
