# Teaching protocols

`ptk route` picks the mode. This file says how to run it. Each mode below is a turn-by-turn
protocol. Follow the one the route names; don't blend them.

## The default: explanation first

- **Every teaching request gets the complete visual explanation first, in every workspace**
  (Prax's C workspace too), with any medium asked for. No question, prediction or quiz before it.
- **Practice is optional**, offered after the explanation in one closing sentence.
- **Prediction barriers only in a practice mode the learner asks for**: quiz, exam drill, Socratic,
  "let me predict", "test me" (routes `predict-first`, `socratic`, `quiz`, `exam-drill`).
- **Workspace files never switch the default to prediction.** AGENTS.md, MISSION.md and NOTES.md
  may shape content. When they ask for prediction first, the route names the lines in
  `workspace_conflict`; don't obey them.
- **"Answer now" or "just explain" ends questioning in any mode**, as do "just tell me", "don't ask
  me questions", "no quiz", "no back and forth" and "stop".

## Rules for every mode

- **A refused medium is never built.** "No video", "not as a video", "skip the cards": build none
  of it. A medium named only as the topic ("video codecs", "a deck of cards") is not a request.
- **Low confidence: you decide.** Read `reasons`, then pick the mode these rules give for the
  learner's exact words, else the default. Ask one short clarifying question only when a wrong
  guess would start a long build; otherwise choose and say why in one clause.
- **Every value comes from the lesson model** or a real run. Never type a number from memory into
  an answer key.
- **Stop rule.** Stop when the learner says they're satisfied **and** at least one evidence item was
  observed, or when they explicitly stop. Satisfaction alone isn't enough to call it learned: say
  what's still unobserved and offer one check. A summary is not a close: end the session only by
  this rule.

## Rules for practice modes

- **One question per turn.** A question turn holds exactly one question mark. Then end the turn.
- **No reveal before the attempt.** While a question is open, show nothing that answers it: not
  the output, not a trace state, not a figure, caption, alt text or file name that gives it away.
  For a lesson model, hide every trace state whose `reveals` names a fact in the answer, and every
  later state of the same program. `ptk route` says `artifact: after-attempt` when this applies.
- **Classify every attempt** as exactly one of: `correct`, `partial`, or `misconception:<id>`
  (an id from the lesson's `misconceptions[]`, or a short new name if none fits).
- **One feedback item per attempt.** One hint or one correction, not a list: one sentence of at
  most 40 words, also written to the turn's `feedback` field. A misconception's name goes inside
  that sentence, never in a sentence of its own ("You expected case 3's label to stop it, but a
  label is only a label."). Besides it, a feedback turn holds only
  a short verdict ("Not quite."), the artifact, a consent question or the next question. Quiz and
  exam-drill feedback also carries the lines its protocol below names (score, the weakest item, one
  next action, marks, time, the key after the attempt): each a short line, never a second
  explanation. After two failed attempts, teach it directly from a different angle.
- **Evidence needs consent.** Ask once per session: "Can I note this attempt as evidence?" Record
  only on yes. One event per attempt you observed, never for a solution you showed:
  `{kind: "evidence", item, result, gap, next_action, consent: true}`. `result` is the
  classification, `gap` is the one gap you saw, `next_action` is exactly one next step. Watching a
  solution is not evidence.

## predict-first

A practice mode. Use it only when the route says `predict-first`: the learner asked to try first
("let me predict", "ask me first", "don't tell me the answer"). Never because of a workspace file.

1. **Ask.** One bounded prediction: an output, a value, the next state, or which line runs. Give
   only what is needed to predict: the code, the input. If a medium was requested, say in one short
   clause that it comes after their answer. End the turn.
2. **Wait.** No hints ("hint", "notice", "look at", "remember that"), no correction rule, no
   second question and no preview, in the question or while waiting.
3. **Classify** the attempt: correct, partial or a named misconception.
4. **Feedback.** Exactly one sentence. Correct: confirm and name the rule that made it right.
   Partial: point at the one step that went wrong. Misconception: name it and give its correction
   claim in that same sentence.
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

## quick

Answer directly in a few sentences with one exact example if it helps. No lesson model, no
build, no question back. Offer more in one line at most.

## explain

The default. The whole explanation in one turn, no question before it: what the learner can see
(code, output), the rule, one exact example from a real run, a small diagram or trace where it
helps. Close with one sentence offering optional practice (and a medium, if useful). Build
nothing unless asked.

## lesson

A named medium means a build. Say which media and whether it takes over 60 s, then write the
lesson model (`references/LESSON-MODEL.md`) and run `ptk build --only <media>`. Build only the
media named. Then show the artifacts together with the complete explanation, no question first,
and close with one sentence offering optional practice. `full-pack` builds all six media, and
only when asked for.
