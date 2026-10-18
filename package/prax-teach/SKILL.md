---
name: prax-teach
description: Compile a C lesson into verified explainers (still, narrated video, interactive video) from one lesson model. Every number comes from a sandboxed real run; every sentence maps to a reviewed claim. Use when Prax asks to be taught a C topic in a named medium.
---

# Prax Teach v2.1 (WP0 slice)

Status: development candidate. Loaded by direct path; not registered with any host.

## Before you teach

1. Read the learner workspace contract first (AGENTS.md, MISSION.md, NOTES.md). If it says predict first, ask one bounded prediction and wait for the attempt before showing any artifact.
2. A quick question gets a direct answer. No lesson, no build.

## Build a lesson in a named medium

`ptk` lives in `bin/` next to this file. Put that directory on PATH.

1. Write `lessons/<slug>/lesson.json` and `programs/*.c` following `references/LESSON-MODEL.md`. Every displayed value is a fact with an independent `expect`; every sentence is a claim with a justification and a source (cite the C17 clause).
2. `ptk validate <lesson>`. Fix errors at the JSON pointer it prints (at most two repairs per error).
3. Tell the learner the build takes about 2 minutes, then run `ptk build <lesson> --only still,video,ive` (only the media asked for).
4. Act on the exit code:

| Exit | Meaning | Do next |
|---|---|---|
| 0 | verified | deliver the artifacts |
| 1 | a gate failed | read `ptk report`, repair at most twice, then report |
| 2 | host problem | name the tool and `ptk host setup` |
| 3 | model error | fix lesson.json at the pointer |
| 4 | claims-pending | run every job in `build/claims-jobs/` as a separate subagent (see `references/HOST-ADAPTERS.md`), then `ptk claims check <lesson>` |
| 5 | incomplete | report which gate did not run and why; never call it verified |
| 6 | degraded | deliver, naming the fallback |

5. Deliver `build/still/*.png`, `build/video/lesson.mp4` (+ captions and chapters), and `build/ive/index.html`. Quote the status from `ptk report <lesson>`.

## Rules

- Never type a value or a sentence into an artifact by hand. Change the model and rebuild.
- Never report a gate as passed that did not run.
- First-time machine setup: `ptk host setup` lists every download; `ptk host setup --yes` fetches into `$PTK_STATE` only.
