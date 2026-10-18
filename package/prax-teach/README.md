# Prax Teach v2.1

A teaching skill for Prax's C study, plus `ptk`, a small lesson compiler.

It does two jobs:

1. **Teach the way the workspace asks.** `ptk route` reads the request and the learner's AGENTS.md, MISSION.md and NOTES.md. In a predict-first workspace the first turn is one question, and the agent waits for the attempt. An explicit "answer now" or "just explain" wins.
2. **Build verified explainers from one lesson model.** One `lesson.json` with its C programs becomes up to six media: a still, an interactive explorer, a Q&A expander, flash cards, a narrated video and an interactive video explorer (IVE).

Every number on screen comes from a real compiled run in a sandbox, and each one is checked against an independent `expect` function. Every sentence maps to a claim, and a separate reviewer subagent checks the claims.

Status: development candidate. It is loaded by direct path (`SKILL.md` in this folder) and is not registered with any host. v2 stays installed until Prax accepts v2.1.

## Setup

- Put `bin/` on PATH. `bin/ptk` runs `python -m ptk` from this folder, using the core venv when setup has made one.
- State lives in `$PTK_STATE`. If that is unset, ptk uses the dev tree's `.state/`, else `~/.local/share/prax-teach`. Nothing is written anywhere else.
- `ptk host setup` lists every download with its source, size and sha256. `ptk host setup --yes` fetches them into `$PTK_STATE`: two Python venvs, the pinned Node tools (Playwright, HyperFrames 0.8.169), Playwright Chromium, HyperFrames' Chrome, the Kokoro model and voices (about 350 MB), whisper `ggml-base.en` (about 148 MB) and the OFL fonts.
- `ptk host probe` shows which tools and ranked alternatives can run now.
- Every child process gets `HYPERFRAMES_SKIP_SKILLS=1`, `HYPERFRAMES_NO_UPDATE_CHECK=1`, telemetry off and `PLAYWRIGHT_BROWSERS_PATH=$PTK_STATE/browsers`. Only `ptk/node.py` and `ptk/host.py` start external tools.
- macOS only for capture: it needs `sandbox-exec`, clang, ffmpeg, whisper-cli and tesseract.

## Commands

| Command | What it does |
|---|---|
| `ptk route "<request>" [--workspace DIR] [--json]` | intent, mode, media, first turn, build needed, confidence |
| `ptk new <slug> [--dir lessons]` | scaffold `lesson.json` and `programs/` |
| `ptk validate <lesson>` | schema and reference checks, errors as JSON pointers |
| `ptk capture <lesson>` | sandboxed compile and run (twice), facts and platform |
| `ptk build <lesson> [--only a,b] [--calibrate]` | validate, capture, project, run the automatic gates, write the claims jobs |
| `ptk claims check <lesson>` | check the reviews against their manifests and finish the status |
| `ptk report <lesson> [--json]` | print the build report |
| `ptk host probe` / `ptk host setup [--yes]` | see above |
| `ptk package [--dry-run]` | build the install tree (5 MB limit) and run the host discovery check |
| `ptk install --candidate [--dry-run]` | install the tree side by side as `~/.agents/skill-library/prax-teach-v2.1`. `--flip` also snapshots learners and repoints the v2 link. The real HOME needs `--real-home` |
| `ptk rollback [--record R] [--dry-run]` | point the v2 link back and restore the learner snapshots. Prints how many learner events are lost |
| `ptk selftest [-k name]` | the automatic tests |
| `ptk agent-tests [-k name]` | the tests that need reviewer subagents. They write jobs and exit 4 until the reviews exist |

### Build modes

- **`--only a,b`** rebuilds only those media and keeps the others on disk. `--only video` or `--only ive` rebuilds both, because the IVE plays the video. If the lesson is unchanged, the report keeps the other media's gates from the last finished build. If the lesson changed, they are listed under `uncovered_media` instead.
- **Claims jobs.** A normal build writes the lesson job plus one canary: a copy of the job with one planted value or claim error, picked from the lesson's mutations by its hash. `verified` needs the lesson job accepted and the canary caught.
- **`--calibrate`** writes the full suite instead: up to 12 mutation jobs, each with a clean control. Run it when the rubric or the reviewer model changes, and at acceptance. Its thresholds: 100% of value mutations caught, at least 90% of claim mutations caught, at least 95% of controls accepted.

Run each claims job in its own subagent, given only the job file and `ptk/verify/rubric.md`. `references/HOST-ADAPTERS.md` has the command for each host.

## Statuses and exit codes

`draft → valid → captured → projected → claims-pending → verified → packaged`

| Exit | Status | Meaning |
|---|---|---|
| 0 | verified, packaged | every gate passed |
| 1 | failed | a gate failed |
| 2 | failed | host or environment problem (a tool is missing, or a real HOME install without `--real-home`) |
| 3 | failed | lesson model error |
| 4 | claims-pending | the claims jobs are waiting for reviewer subagents |
| 5 | incomplete | a gate did not run |
| 6 | degraded | verified, but a fallback was used (for example `say` instead of Kokoro) |

A gate that did not run is reported as `not-run`, never as passed.

## Where outputs go

Everything goes under `lessons/<slug>/build/`:

- `still/`: wide and portrait SVG plus 2x PNG, light and dark.
- `explorer/index.html`, `qa/index.html`: single HTML files that work from `file://`.
- `cards/`: Markdown and `.apkg`.
- `video/lesson.mp4` with `captions.vtt`, `chapters.vtt` and `transcript.txt`.
- `ive/index.html`: the interactive video explorer, with `states.vtt`.
- `shots/`: the screenshots the gates took.
- `claims-jobs/` and `claims-review/`: the review jobs and the reviews.
- `build-report.json`: every gate, measurement, artifact hash and tool version.

The job roles (lesson, canary, mutation, control) are kept in `$PTK_STATE/claims-private/`, where the reviewer can't see them.

## Learner state

`python -m ptk.state` is v2's consent-first state engine, ported, with schema 2 adding `navigation` and `evidence` events. One change from v2: macOS backup and versioning give new files under `~/Developer` and the C study workspace a second hard link. So a state file with more than one link is now accepted if it is a regular file owned by you, with a warning on stderr. Symlinks, files owned by someone else and non-regular files are still refused. `plan/PROTECTED-MAP.md` in the dev tree records this, including the risk it leaves.

## Honest limits

- **Anki import is not run.** Anki isn't installed here, so `test_cards.py::test_anki_import` reports `not-run`. The `.apkg` contents and stable GUIDs are tested. Re-import into a real Anki is not.
- **The router has known limits.** It is table-driven regex, not a language model. It scores 192/192 on its dev set and 20/20 on 20 held-back probes, but both sets were written by the people tuning it. Unusual phrasings can still misroute; a low-confidence route lists its reasons so the agent can decide. The hidden holdout is only run at acceptance.
- **No Manim backend.** The video projector is renderer-neutral, but only HyperFrames is built. Manim CE is a ranked alternative in the registry, not a working renderer.
- **No LaTeX.** BasicTeX or Typst would be a system install that needs Prax's OK, so Manim `MathTex` is out. Math in stills uses MathJax `tex2svg`.
- **Claims reviews are LLM findings, not proofs.** The canary shows that this reviewer caught one planted error on this build. It does not prove that every claim is true.
- **macOS only.** Capture needs `sandbox-exec`. There is no Linux sandbox yet.
- **Taste is Prax's call.** The gates check contrast, overflow, fonts, numerals and the network. Whether it looks world-class is for Prax to judge against the Neuron Atlas reference.
