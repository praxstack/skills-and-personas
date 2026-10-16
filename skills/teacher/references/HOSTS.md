# Hosts

The teacher is a folder of Markdown, Python, Node scripts and static assets. Any agent host that can read a skill folder and run commands can use all of it.

## Install

```sh
./install.sh                              # every host set up on this machine (its config folder exists)
./install.sh --targets claude,codex,pi    # chosen hosts
./install.sh --with-subskills             # also expose explorable, manim-video, etc. by name
./install.sh --dir ./.claude/skills       # project level
./install.sh --copy                       # for hosts that don't follow symlinks
./install.sh --uninstall
npx skills add praxstack/skills-and-personas --skill teacher
```

Skill folders by host, as used by this repo's installers (check your host's docs if one has moved):

| Target | Folder |
| --- | --- |
| claude | `~/.claude/skills` (project: `.claude/skills`) |
| codex | `~/.codex/skills` |
| agents (shared) | `~/.agents/skills` |
| pi | `~/.pi/agent/skills` |
| opencode | `~/.config/opencode/skills` (project: `.opencode/skills`) |
| gemini | `~/.gemini/skills` |
| hermes | `~/.hermes/skills` |
| cursor | `~/.cursor/skills` |
| cline, kilocode, copilot | `~/.cline/skills`, `~/.kilocode/skills`, `~/.copilot/skills` |

A host without skill support can still use it: point the agent at `SKILL.md` ("read teacher/SKILL.md and follow it").

## What each piece needs

| Piece | Needs |
| --- | --- |
| building explorables, animations, explained pages | Python 3.9+ |
| diagrams from Mermaid, D2 and friends | a local CLI, or network access to Kroki |
| lesson tests, page QA, MP4 export | Node 18+, Playwright with a Chromium |
| video QA, GIF export | ffmpeg and ffprobe |
| narrated video | see `skills/explainer-video` (voice, music, engines) |
| the journal | Python 3 |

`python3 scripts/find_tool.py --inventory --net` reports all of it.

## Showing the learner what you made

| Host can... | Do |
| --- | --- |
| publish a page (Claude artifacts) | build with `--fragment`, publish, give the link |
| show a canvas (ChatGPT, Codex) | paste the single-file HTML |
| send or attach files | send the HTML, MP4 or PNG |
| only write files | write them where the learner can open them and say exactly which file to open |
| only print text | describe the figure in words, give the source, and offer to build it when they're somewhere with a browser |

Built pages are single files with fonts inlined: they open from disk, offline, with no server.
