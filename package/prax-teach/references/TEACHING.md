# Teaching protocols

`ptk route` picks the mode. This file says how to run it. Each mode below is a turn-by-turn
protocol. Follow the one the route names; don't blend them.

## Rules for every mode

- **The workspace contract wins over these defaults.** If the learner's AGENTS.md, MISSION.md or
  NOTES.md sets a teaching style, `ptk route` already applied it. Don't argue with the route.
- **Explicit requests win over the contract.** "Answer now", "just explain", "just tell me" and
  "build the full course" end any questioning at once (D20.7). So does "stop".
- **One question per turn.** A question turn holds exactly one question mark. Then end the turn.
- **No reveal before the attempt.** While a question is open, show nothing that answers it: not
  the output, not a trace state, not a figure, caption, alt text or file name that gives it away.
  For a lesson model, hide every trace state whose `reveals` names a fact in the answer, and every
  later state of the same program. `ptk route` says `artifact: after-attempt` when this applies.
- **Classify every attempt** as exactly one of: `correct`, `partial`, or `misconception:<id>`
  (an id from the lesson's `misconceptions[]`, or a short new name if none fits).
- **One feedback item per attempt.** One hint or one correction, not a list. If the learner has
  failed twice, teach it directly from a different angle (worked example, picture, smaller case).
- **Evidence needs consent.** Ask once per session: "Can I note this attempt as evidence?" Record
  only on yes. One event per attempt you observed, never for a solution you showed:
  `{kind: "evidence", item, result, gap, next_action, consent: true}`. `result` is the
  classification, `gap` is the one gap you saw, `next_action` is exactly one next step. Watching a
  solution is not evidence.
- **Stop rule.** Stop when the learner says they're satisfied **and** at least one evidence item was
  observed, or when they explicitly stop. Satisfaction alone isn't enough to call it learned: say
  what's still unobserved and offer one check. A summary is not a close: end the session only by
  this rule.
- **Every value comes from the lesson model** or a real run. Never type a number from memory into
  an answer key.

## predict-first

Use when the route says `predict-first` (workspace contract, or the learner asked to try first).

1. **Ask.** One bounded prediction: an output, a value, the next state, or which line runs. Give
   only what is needed to predict: the code, the input. If a medium was requested, say in one short
   clause that it comes after their answer. End the turn.
2. **Wait.** Don't add hints, a second question or a preview while waiting.
3. **Classify** the attempt: correct, partial or a named misconception.
4. **Feedback.** Exactly one item. Correct: confirm and name the rule that made it right.
   Partial: point at the one step that went wrong. Misconception: name it and give its correction
   claim.
5. **Show the artifact** now: the requested medium, or the trace with every state unlocked.
   If nothing was requested, show the real run's output.
6. **Evidence.** Ask consent (once per session) and record one event.
7. **Next.** Offer one small fresh variation, or stop by the stop rule.

## socratic

1. Ask one guiding question. Order questions from observation ("what do you see?") to rule
   ("what decides that?") to prediction ("so what happens if?"). End the turn.
2. Each answer gets one short reply and the next question, never a lecture.
3. After two unproductive answers, teach the step directly from a new angle, then resume.
4. Classify, record evidence and stop as above.

## quiz

1. Say how many questions (3 to 5 unless asked) and ask **question 1 only**. Keep the answer key
   out of the text. End the turn.
2. After each answer: classify, one feedback item, then the next question in the same turn.
3. Never show a later question's answer, and never reveal an answer before it's attempted.
   "Skip" counts as an attempt with result `skipped`.
4. After the last answer: the score (`k/n`), the one weakest item and one next action. Ask consent
   and record one evidence event per answered question. Then offer another round; close only by
   the stop rule, repeating the score in the close.

## exam-drill

Timed GATE practice. Formats: **MCQ** (four options, one correct; +1 or +2 marks, wrong answers
lose 1/3 or 2/3), **MSQ** (one or more correct, no negative marks) and **NAT** (numeric answer
typed in, a stated range or tolerance, no negative marks).

1. First turn: state the format, the number of questions, the marks and the time limit per
   question (about 1.5 min per mark). Then ask question 1 only. End the turn.
2. MCQ and MSQ show options labelled A to D. NAT says the unit and the precision.
3. After each answer: classify, give the marks earned, the time taken against the limit, and one
   feedback item (the trap, or the fastest method). Then the next question.
4. A timeout is an attempt with result `timeout`. Reveal the key only after the attempt or the
   timeout.
5. After the last question: total marks, accuracy, time per question, the weakest topic and one
   next action. Record one evidence event per question, with consent. Close only by the stop
   rule, repeating the total in the close.

Every key must be computed (a real run or `ptk/expect.py`) or come from a cited source.

## qa-expand

Layered answers. The learner leads.

1. Give the **layer 1** answer in two or three sentences. Then list the deeper layers they can
   open by name, for example: *why*, *example*, *edge case*, *standard*, *misconception*.
   End the turn.
2. Open **one layer per request**, in the order asked, each a short paragraph. Don't open
   layers that weren't asked for. Name what's still closed.
3. A layer may end with one optional check question. A wrong answer gets one feedback item.
4. If a Q&A expander artifact was requested, its layers are the same layers, built by
   `ptk build --only qa`.

In a predict-first workspace the route gives `predict-first` instead: ask first, then answer
in layers.

## quick

Answer directly in a few sentences with one exact example if it helps. No lesson model, no
build, no question back. Offer more in one line at most.

## explain

A chat explanation. Start from what the learner can see (code, output), then the rule, then one
exact example from a real run. Use short segments and stop between them for "go on" if the
explanation is long. Offer a medium in one line; build nothing unless asked.

## lesson

A named medium means a build. Say which media and whether it takes over 60 s, then write the
lesson model (`references/LESSON-MODEL.md`) and run `ptk build --only <media>`. Build only the
media named. If the route's mode is `predict-first`, the build can run while you wait for the
attempt, but show nothing from it until the learner has answered. `full-pack` builds all six
media, and only when asked for.
