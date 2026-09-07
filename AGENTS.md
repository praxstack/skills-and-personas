# Repository Guidelines

## Project Structure & Module Organization
This repo is a small collection of skills and persona specs.
- `skills/<skill-name>/SKILL.md` holds Skill definitions (YAML front matter with `name` and `description` only).
- `skills/<skill-name>/references/` stores detailed guidance for progressive disclosure.
- `skills/*.skill` are packaged skill archives (zip archives), for example `skills/kingmode.skill`.
- `md-personas/*.md` are portable docs for other LLMs or persona notes (for example, `md-personas/KINGMODE.md`).
- `team-personas/` contains shared team persona material.
- `assets/` stores images and supporting documents.
- `archive/` stores legacy or “to review” material.
Keep skill folders named after the skill (`skill-name/`) and prefer descriptive filenames like `persona-brief.md`.

## Build, Test, and Development Commands
There is no build or runtime step; edits are plain Markdown.
Helpful local commands:
- `rg --files` to list tracked files.
- `rg "keyword"` to search content (for example, `rg "description"`).
- `git diff` to review edits before committing.

## Coding Style & Naming Conventions
- Markdown is the source of truth; keep paragraphs short and use clear headings and bullet lists.
- For skills, keep YAML front matter at the top and include only the required fields (`name`, `description`) unless a specific optional field is needed.
- For personas, follow the existing pattern: an H1 title, numbered sections, and bolded labels.
- Indent nested list items with two spaces.
- No formatter or linter is configured in the repo today.

## Testing Guidelines
No automated tests are present. Validate changes by reading for clarity, consistency, and broken Markdown structure. If you run a Markdown linter locally, ensure it passes before opening a PR.

## Commit & Pull Request Guidelines
- Commit messages in history use an emoji prefix plus a type and short description (example: `:tada: feat : add new persona`).
- Keep commits focused on a single skill or persona update.
- PRs should include a short summary, the rationale for the change, and a list of updated files (for example, `SKILL.md`).

## AI Agent Instructions
- For cross-functional planning, use the Constellation Team workflow and role-labeled output (`md-personas/CONSTELLATION-TEAM.md`).
- For UI/UX tasks, apply frontend-design guidance (`md-personas/FRONTEND-DESIGN.md`).
- For architecture, security, reliability, or deep reasoning, apply kingmode or super-mode (`md-personas/KINGMODE.md`, `md-personas/SUPER-MODE.md`).
- Ask for missing requirements, state assumptions explicitly, and do not claim to run tests or commands unless they were executed.

## Agent skills

### Issue tracker

Issues are tracked as GitHub issues on `praxstack/skills-and-personas` via the `gh` CLI; local markdown tickets under `.scratch/<feature>/` mirror them for offline work. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-role vocabulary (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: one `CONTEXT.md` at the repo root (created lazily) plus `docs/adr/`. See `docs/agents/domain.md`.

### Skill discovery

Use a relevant skill when the task needs its workflow; explicit skill requests take priority. The gstack suite (browse, ship, investigate, retro, and related) is installed host-side under `~/.agents/skills/`; invoke it by name when a task matches. Per-role model mapping for pstack lives globally at `~/.config/pstack/models.md`. For any user-facing prose drafted here, run `stop-slop` or `humanize` over it before shipping.
