---
name: prax-teach
description: Teach Prax a C topic the way his workspace asks, and compile lessons into verified explainers (still, explorer, Q&A, cards, narrated video, interactive video) from one lesson model. Every number comes from a sandboxed real run; every sentence maps to a reviewed claim. Use when Prax asks to be taught, quizzed or drilled, or asks for a lesson in a named medium.
---

# Prax Teach v2.1

Status: development candidate. Loaded by direct path; not registered with any host.
`ptk` lives in `bin/` next to this file. Put that directory on PATH.

## Before your first teaching word

You need only three things before you say anything that teaches: this file, the route below, and
the section of `references/TEACHING.md` for the routed mode. Read nothing else first.

1. Run the router on the learner's exact words, from the learner's workspace:

   `ptk route "<request>" --workspace <learner workspace dir> --json`

   It returns `{intent, mode, media[], workspace_contract, first_turn, build_needed}`. The router
   has already read the workspace's AGENTS.md, MISSION.md and NOTES.md and applied their teaching
   rules, and it has applied any "answer now" or "just explain" in the request. Don't re-decide.
2. Obey it:
   - `intent: ordinary_task`: do the task. No teaching, no question, no build.
   - Otherwise do exactly what `first_turn.instruction` says, using the protocol for `mode` in
     `references/TEACHING.md`. If `first_turn.end_turn` is true, end your turn after it.
   - `first_turn.artifact: after-attempt` means nothing from the lesson (artifact, trace state,
     output) is shown until the learner has attempted the question.
   - `build_needed: true` means build exactly `media[]`, as below. `false` means build nothing.
3. If the learner later says "answer now", "just explain" or "stop", that wins over the protocol.

| mode | first turn |
|---|---|
| predict-first, socratic, quiz, exam-drill | one question, then wait |
| qa-expand | layer-1 answer, name the deeper layers |
| quick, explain | answer in chat, no build |
| lesson, full-pack | say what you'll build and how long, then build |

## Build a lesson in a named medium

Read `references/LESSON-MODEL.md` now, not before.

1. Write `lessons/<slug>/lesson.json` and `programs/*.c` following `references/LESSON-MODEL.md`. Every displayed value is a fact with an independent `expect`; every sentence is a claim with a justification and a source (cite the C17 clause).
2. `ptk validate <lesson>`. Fix errors at the JSON pointer it prints (at most two repairs per error).
3. Tell the learner how long the build takes (about 2 minutes), then run `ptk build <lesson> --only <media from the route>`, for example `--only still,video,ive`.
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

5. Deliver the built files (`build/still/*.png`, `build/video/lesson.mp4` with captions and chapters, `build/ive/index.html`). Quote the status from `ptk report <lesson>`. In predict-first mode, deliver only after the learner's attempt.

## Rules

- Never type a value or a sentence into an artifact by hand. Change the model and rebuild.
- Never report a gate as passed that did not run.
- First-time machine setup: `ptk host setup` lists every download; `ptk host setup --yes` fetches into `$PTK_STATE` only.
