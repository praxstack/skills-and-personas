# Evidence: where predict-first came from

Written 2026-10-18 for Prax's decision 4 ("Identify which rule drifted before asking me to choose"). Read-only investigation. Nothing in the C repo, the v2 install or the v2.1 package was changed. All times are IST. Every commit below carries Prax's git identity, so the agent is named from the session log or the `Co-Authored-By` trailer.

## Short answer

- The predict-first default did not come from Prax. An OpenCode agent (Kai Mori) wrote it into the C workspace on 2026-09-30.
- The drift happened in this Claude session (Claude Opus 5.5), in review finding T1 on 2026-10-18 at about 03:26. T1 said a project file counts as an "explicit" style request. That one sentence turned the agent-written workspace note into a rule that beats the explain-first default.
- FREEZE.md criterion 5 froze it 45 minutes later. Plan, spec, TEACHING.md, the router and the tests all inherit it.
- The failing `test_predict_first_flow` sits downstream. Its cause is a small checker vs TEACHING.md wording clash inside the predict-first protocol. It only blocks the default path because predict-first was made the default.

## 1. What Prax said, in order

| When | Where | Prax's words |
|---|---|---|
| 2026-09-30 14:08 | OpenCode session `ses_f0e893dcbffeROk20cAf1990nR` | "Will you use Socratic learning methods to teach me the things I want to learn?" |
| 2026-09-30 14:11 | same | "You can teach me by visualization method, also using video and creating high animations visually." |
| 2026-09-30 18:19 | same | "Can you please explain to me how a C compiler works? ... Let's demo that." |
| 2026-10-16 21:31 | Codex rollout `01a1456a` | "Highjest focus on intuition thrugh heavy visualisation" |
| 2026-10-16 23:25 | same (Prax confirmed this summary: "yes and record thios") | "Keep exploring with the learner until they are satisfied, rather than treating one lesson or a quiz score as the finish line." |
| 2026-10-18 02:29 | Codex session `01a14ba6` (export line 1882) | "answer now , nuild best visualoisaser based intuiton building based full coirse" (he turned down a prediction question) |
| 2026-10-18 22:37 | this Claude session, decision 4 | "preserve my original teaching preference: complete visual explanation first, with optional practice afterward. Prediction barriers belong in explicitly requested practice modes." |

One honest caveat. On 2026-09-30 Prax did ask for "Socratic learning methods". It was a question to a tutor persona, and the agent's reply kept the exit open: "You can also ask for a direct explanation or full solution." It was never "start every session with a prediction." His later statements are specific, and the 2026-10-18 one is explicit and current. It governs.

The Claude export (`2026-10-18-105839-...txt`) holds no statement from Prax about prediction or quizzes. His requests there are about media: "world class all kind of explainer visualisation still, interactive, videos, TTS".

## 2. The C workspace: who wrote the predict-first lines

- Commit `4890911d`, 2026-09-30 18:11:12, "feat: scaffold C practice and visual study workspace". No co-author trailer.
- Writer: the OpenCode agent `kai-mori`, model `openai/gpt-6.1-sol`, session "Socratic learning and repo initialization" (`ses_f0e893dcbffeROk20cAf1990nR`, OpenCode db). It is the only session that contains the NOTES.md sentence. `progress.txt` in the same commit is that agent's log ("lead | spec | Acceptance contract frozen...").
- Lines it wrote, unchanged since:
  - AGENTS.md:7 "Ask one bounded prediction, trace, code repair, or explanation. Wait for the attempt."
  - NOTES.md:3 "The user requested Socratic teaching, visual explanations, animations, video, and saved lesson files. ... Start the first learning session with one short C output prediction."
  - MISSION.md:5 "learn through Socratic prompts and accurate visual explanations"
  - docs/tutoring.md: "the learner should predict or trace before opening the explanation."
- "Start the first learning session with one short C output prediction" is the agent's plan, not a Prax quote. AGENTS.md:7 even lists "explanation" as one of the allowed moves.

## 3. v2, the accepted baseline: explain-first

- Commit `f9b9212`, 2026-10-16 23:13, "teach with complete visual intuition by default" (source repo `skills-and-personas-recovery-20261016`, written in the Codex sessions above). It added `.engine/SKILL.md:42`: "Deliver the whole explanation without prediction, quiz or teach-back barriers."
- Loader `SKILL.md:12` (accepted package, commit `389f6f9`): "Do not block explanation behind a prediction or quiz unless that teaching style was explicitly requested."
- `.engine/SKILL.md:133`: practice modes keep retrieval protection only "When the learner chooses a quiz or assessment".
- Stale leftovers from older attempts, still in the protected v2 bytes:
  - `.engine/STATUS.md:46` still claims "attempt-before-explanation".
  - `.engine/evals/forward-behavior.json:19` still requires "prediction or attempt before explanation".
- Codex owned the slip at 2026-10-18 03:12: "The clean package explicitly requires explanation-first teaching, so my earlier quiz-first response was an execution error." Its quiz-first turn came from an archived attempt-11 skill ("We'll start here in chat with one small prediction").

## 4. v2.1: the drift chain

All of these were written by Claude Opus 5.5 in session `ff394d66` (this session, started in the C workspace). Each v2.1 commit carries `Co-Authored-By: Claude Opus 5.5`.

| Step | When | Commit | Sentence |
|---|---|---|---|
| **T1 review (the drift)** | 2026-10-18 ~03:26 (file mtime; folder not in git) | none | "Teaching style stated in host or project instruction files (AGENTS.md, CLAUDE.md, MISSION.md, NOTES.md or equivalent) is an explicit style selection. It overrides the explanation-first default without needing `.prax-teach` consent." The premise it fixes: "Prax's first session would likely open with a full explanation of the answer he was supposed to predict." That outcome is exactly what Prax wants. |
| FREEZE criterion 5 | 08:10:37 | `e29321b` "freeze: baseline, evaluator, holdout..." | "teaching behaviour that respects the learner workspace contract (Prax's C workspace: one prediction, wait for the attempt)." It sits under "Success definition", right after "Original objective (Prax's words)". Prax's quoted words there say nothing about prediction. |
| PLAN-INPUT T1 | 08:15:41 | `6fd06f1` (file added) | "The default 'explain first, no quiz' style overrides the learner workspace's contract (one prediction, then wait)". Explain-first is now framed as the bug. |
| CEO plan D4.7, outcome | 08:15:41 | `6fd06f1` | "Router rebuild: ... workspace contract precedence, prediction-first". Outcome 2: "inside his own study loop: a prediction first". Scope: "Workspace contract loader (AGENTS.md, MISSION.md, NOTES.md), which wins over skill defaults." |
| CEO plan D17.6 | 08:18:49 | `53529c6` | "Workspace contract precedence: AGENTS.md, MISSION.md and NOTES.md are read first, and their rules beat skill defaults." |
| SPEC AC-1.3, AC-1.6 | 08:33:07 | `5e48978` | AC-1.3: "When the workspace contains AGENTS.md, MISSION.md or NOTES.md requiring prediction first, `ptk route` shall return `mode=predict-first`... This applies even when a medium is requested". AC-1.6 defines the five-step predict-first protocol. |
| D20.7 | 11:08:29 | `92acff1` "plan/spec v1.1: adopt D20.x" | "'Answer now' beats predict-first (Codex, Prax's own words)." Prax's words were read as an escape hatch, not as his default. AC-1.3 amended with "Unless". |
| TEACHING.md, workspace.py, route_rules.json | 12:01:33 | `7530137` "wp1: rule-table router, workspace contract..." | TEACHING.md:8 "The workspace contract wins over these defaults." workspace.py:8 "When files disagree, predict-first wins". Step 4 "Misconception: name it and give its correction claim." |
| Negation-aware router, checker | 12:42:02 | `eb55c96` | TEACHING.md:10 "A workspace that only says 'Socratic' counts as predict-first." `protocol.feedback_unit` added. |

Router precedence today (`route_rules.json`): `override > attempt > workspace > request > media > intent > default`. `default_mode` is `explain`, but the `workspace` stage fires first in the C repo. The `predict_first` patterns match `predict`, `socratic` and `wait for the attempt`. Run against the C workspace now:

- "teach me pointers" gives `predict-first`, artifact `after-attempt`.
- "explain how switch fallthrough works with a video" gives `predict-first`, even with the word "explain".
- "answer now: explain pointers" gives `quick`.

## 5. The failing test

- `test_protocol_transcripts.py::test_predict_first_flow` (AC-1.6) failed 2 of 2 live runs (`reviews/final-verification.md`, `7ce608f`, 21:13:47).
- Both failures: "a second correction or explanation besides the one feedback item". The tutor followed TEACHING.md step 4 and named the misconception in its own sentence. `feedback_unit` allows only one sentence of feedback plus a verdict, a question or a line of four words or fewer.

**Is it downstream of the drift?** Yes, for whether it matters. No, for the bug itself.

- It blocks acceptance only because predict-first is the default C-workspace path (AC-1.3 sends every C teaching request there, and FREEZE #5 demands it).
- The wording clash between `7530137` and `eb55c96` is real on its own terms. It still needs a fix once predict-first becomes an opt-in practice mode. The fix is small: put the misconception name inside the one feedback sentence in TEACHING.md, or let the checker accept one short naming sentence.

## 6. Corrected rule set

1. Every teaching request starts with a complete visual explanation, in every workspace, including the C repo. At most one optional check comes after it. Practice is offered, never required.
2. Prediction-gated modes (`predict-first`, `socratic`, `quiz`, `exam-drill`) run only when the learner's own request asks for them: "quiz me", "test me", "let me predict", "ask me first", "Socratic", "exam drill", "drill me on".
3. Workspace files do not switch the default to prediction. AGENTS.md, MISSION.md and NOTES.md shape content (C, misconceptions, hint pacing, where to log evidence). A file can make prediction the default only if it says that Prax himself chose it, in words like "Prax asked for predict-first by default". Agent-written teaching notes are context, not an explicit request.
4. Inside a practice mode, retrieval safety stays: one question per turn, no reveal before the attempt, one hint, then teach directly after two misses. "Answer now", "just explain" and "stop" still end the questioning at once.
5. A requested medium is built and shown with the explanation, not held back until after an attempt.

## 7. What would change

Evaluator and governing changes. Each needs Prax's explicit approval and a new FREEZE version, as FREEZE.md and `/Users/prax/AGENTS.md` require:

- **FREEZE.md success criterion 5.** Today it encodes the predict-first contract. Proposed: "teaching behaviour that matches Prax's stated preference: complete visual explanation first, optional practice after; prediction only in an explicitly requested practice mode." Changing it is an evaluator change. It cannot ride along with an implementation round.
- **Holdout labels.** final-verification says "H21's predict-first contract wins the medium label". Any holdout row labelled predict-first because of the C workspace would need relabelling. That is also an evaluator change. I did not open the holdout.
- **ACCEPTANCE-PROPOSAL item 5** ("One live predict-first session with Prax") becomes "one live explain-first session, with one optional practice turn".

Spec and plan (a new spec version):

- SPEC AC-1.3: rewrite as "Workspace prediction or Socratic wording shall not change the mode. Without an explicit practice request, `ptk route` returns `explain` (or a lesson build when a medium is named)." Replace `test_workspace_contract_wins` with `test_workspace_wording_does_not_force_prediction`. Keep `test_answer_now_overrides_contract` for practice modes.
- SPEC AC-1.6: scope to "When the learner explicitly requests predict-first". Fix the feedback-sentence wording so TEACHING.md and the checker agree.
- CEO-PLAN: D4.7, outcome 2 ("a prediction first"), D17.3 predict-first runtime, D17.6 "Workspace contract precedence", Q4/E9 precedence order, D18.6 live predict-first session, the test diagram row "AGENTS.md says predict-first wins".
- EXTERNAL-INPUTS D20.7: reframe. Prax's "answer now" is evidence for the default, not an exception to a predict-first default.

Package (an implementation change after the spec is approved):

- `references/TEACHING.md` lines 8-13 and 49: drop "The workspace contract wins over these defaults" and "A workspace that only says 'Socratic' counts as predict-first".
- `ptk/route_rules.json`: remove the `workspace` precedence stage for mode (or map `contract_modes.predict-first` to `explain`). Keep `attempt` for explicit requests.
- `ptk/workspace.py`: drop "When files disagree, predict-first wins". Keep the reader for content hints.
- `ptk/route.py` precedence comment, `SKILL.md` description ("Teach Prax a C topic the way his workspace asks") and its mode table.
- `tests/test_route.py`, `tests/test_protocol_transcripts.py` (predict-first becomes an opt-in transcript).

Not touched: the v2 baseline is protected. Its stale `STATUS.md:46` and `forward-behavior.json:19` lines should be noted in any v2 errata, not edited.

## 8. What the C workspace AGENTS.md should say (proposal only, not edited)

The drifted source is AGENTS.md:7 with NOTES.md:3, written by Kai Mori in `4890911`. Suggested Teaching section:

> - Start with a complete visual explanation: a concrete C example, its state diagram or trace, and the real compiler output. Then offer one optional practice item.
> - Use prediction, trace or repair questions only when Kai asks for practice ("quiz me", "let me predict", "Socratic", "exam drill"). Then ask one, wait for the attempt, give one hint, and teach directly after two unsuccessful attempts.
> - "Answer now" or "just explain" ends any questioning.

NOTES.md:3 should drop "Start the first learning session with one short C output prediction" and say "Prax prefers a complete visual explanation first; practice on request." MISSION.md:5 "learn through Socratic prompts and accurate visual explanations" should read "learn through accurate visual explanations, with Socratic practice on request." docs/tutoring.md "the learner should predict or trace before opening the explanation" needs the same change. These edits are Prax's call, since the C repo is protected in FREEZE.md.
