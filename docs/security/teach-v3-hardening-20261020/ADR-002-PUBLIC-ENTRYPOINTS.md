# ADR-002: one canonical teacher with a self-contained compatibility fallback

Status: accepted for this repair branch
Date: 2026-10-20

## Context

The skills.sh page for `teach-pro-max` shows a single-skill install command. The published entry points to `../teacher/SKILL.md`, which is absent after that install. A second, older teach-pro-max copy is bundled under `teacher/skills/` and can be installed by `--with-subskills`; its rules diverge and default some learners to practice-first.

## Decision

- Keep `skills/teacher` as the canonical full general teacher.
- Keep the top-level `skills/teach-pro-max` entry for compatibility and discovery.
- When the sibling teacher exists, the wrapper delegates to it.
- When it does not exist, the wrapper uses its embedded engine under the wrapper's explanation-first, privacy, and untrusted-content rules.
- Remove the nested divergent teach-pro-max copy from the teacher bundle and exclude compatibility aliases from subskill installation.

## Consequences

- The exact skills.sh single-entry command yields a working skill.
- Installing teacher subskills cannot shadow the public wrapper with an older policy.
- The compatibility fallback remains heavier than the canonical teacher, but it is already shipped and integrity checked.
- General improvements still belong in `teacher`; the fallback exists for portability, not as a second general-teaching authority.
