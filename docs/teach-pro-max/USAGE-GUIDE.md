# Teacher and Teach Pro Max: installation and use

`teacher` is a general, visual, explanation-first teaching skill. `teach-pro-max` preserves a compatible invocation and delegates ordinary teaching to the sibling teacher. The development C adapter is not required or included as an accepted component.

## Install with the Skills CLI

A working Node.js/npm installation and GitHub access are needed for this command:

```bash
npx skills add praxstack/skills-and-personas --skill teacher
```

For both names, install both skills together:

```bash
npx skills add praxstack/skills-and-personas --skill teacher teach-pro-max
```

Installing `teach-pro-max` alone is supported: it uses its bundled compatibility engine when the sibling teacher is absent. Installing both selects the general teacher.

Select your agent interactively, or target a project-local Codex install explicitly:

```bash
npx skills add praxstack/skills-and-personas \
  --skill teacher teach-pro-max --agent codex --yes
```

Use `--global` only if you want a user-wide install. `--copy` makes physical copies instead of the CLI's normal canonical links. Inspect available names without installing:

```bash
npx skills add praxstack/skills-and-personas --list
```

Your agent can read the new guidance on its next turn. If a host caches its skill list, start a fresh session.

## Download without an installer

Download the complete source ZIP from the repository's GitHub Releases. Extract the whole archive, including hidden supporting directories. It contains both `skills/teacher` and `skills/teach-pro-max`, their bundled references/scripts/templates and license notices. Read `START-HERE.md` and this guide.

For a host that accepts an explicit instruction file, point it at `skills/teacher/SKILL.md`. For local folder installation, the teacher's own installer supports an explicit destination:

```bash
bash skills/teacher/install.sh --dir /path/to/your-agent/skills
```

That installer exposes the standalone `teacher`. The Skills CLI command above is the simplest way to expose both compatible names. Do not copy only SKILL.md: the scripts, fonts, templates, engine files and bundled references are part of the skill.

## Rendering prerequisites

Skill installation provides the instructions and source. Generating media additionally requires tools available to the agent:

| Work | Prerequisites |
| --- | --- |
| Build an explorer or course | Python; Python 3.12 was tested |
| Browser checks and six-format export | Node.js, Playwright and Chromium |
| Video encoding and checks | ffmpeg and ffprobe |
| Local neural narration | The pinned Python requirements below, Kokoro ONNX model/voice files, and a cached speech-recognition model for checking |

The [tested Python requirements](../../deliverables/teach-pro-max/codex/evidence/clean-install-20261019/runtime-requirements.txt) and [reproduction guide](../../deliverables/teach-pro-max/codex/REPRODUCE.md) record the actual environment. Set up dependencies/models in a dedicated environment, not a shared environment used by concurrent builds. Model downloads and dependency installation belong to setup; lessons can then run offline. Models and virtual environments are not included in the source ZIP, and installation does not buy API credits or silently start a paid service.

The source contains optional integrations and other rendering engines. Their presence is not evidence that every engine is installed or tested on your machine. Run the teacher's `scripts/find_tool.py --inventory` for local capabilities and follow `references/HOSTS.md` and `references/ARTIFACT-EXPORTS.md`.

## Ask for a lesson

Examples:

- `Use teacher to explain neurons and deep learning. Start with intuition and a mechanism diagram.`
- `Make an interactive explorer for Bayes' theorem, with assumptions and edge cases.`
- `Explain passive voice with a still, Q&A expander and narrated video.`
- `Use teach-pro-max to build a course on history. Explain first; offer practice afterward.`

Use `$teacher` or `$teach-pro-max` where your host supports dollar skill references. Other hosts may use slash commands or natural-language selection. The Skills CLI installs skills; it is not itself the tutor.

The normal order is a complete explanation followed by optional practice. Explicitly request quizzes or prediction-first practice when you want them. Viewing or finishing an artifact is not proof of understanding. A learner journal is written only with explicit consent; the disclosure covers storage and the limits of deletion when backup/sync software can retain copies.

## Review the evidence

The original general baseline is `0d20ff7722910d12256240af0897070255cfc4f3`. Its fixed routing set reported 24/24; the eight-subject evaluation reported 52/56 automated criteria plus four human listening approvals. The v3.0.1 source adds separately tested security and packaging fixes; it does not rerun or improve that frozen score. Controls are separately 8/8 valid accepted and 8/8 intended invalid propositions identified. See [the accepted report](../../deliverables/teach-pro-max/codex/evidence/private-evaluation/candidate4-accepted-redacted-report.json).

[Real lesson downloads](https://github.com/praxstack/skills-and-personas/releases) include three non-C exemplars in six formats and a connected course. The private evaluation prompts remain private. Historical receipts preserve failures and the original 52/56 result before listening acceptance; baseline end-to-end improvement and superior human learning were not established. The optional C adapter's development status does not block general teaching.

Untrusted executable examples can use the [bundled Docker checker](../../skills/teacher/skills/explorable/references/SANDBOX.md). It requires explicit setup and fails closed when unavailable. Reviewed course builds copy descriptor-checked inputs into private snapshots before extraction, rendering or testing.
