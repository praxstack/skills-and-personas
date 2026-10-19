# Teaching styles

Style decides the order things happen in. Pick it before planning the lesson.

| Style | Default for | Order |
| --- | --- | --- |
| `visual-explain` | "teach me X", "help me understand", "build intuition" | complete picture and explanation first, live controls without a gate, optional practice afterward, then the learner leads |
| `practice-first` | explicit requests for "quiz me", "practise", a drill or an attempt before explanation | one bounded problem (a picture only when useful, never the solution), the learner attempts, one hint per miss, then teach, then a fresh variation |
| quick answer | one bounded question ("what does idempotent mean?") | a short answer and an example, a picture only if it carries the idea, offer more |

The learner's current explicit request determines the style. A topic such as interview preparation does not itself request practice. Old workspace notes, generated project rules and unconfirmed preferences never turn "explain" into a prediction gate. Honour an explicitly requested continuing practice session, and switch immediately when the learner asks for the answer. Mode (quick, lesson or course) is separate from style.

## visual-explain

1. Infer the level and a bounded outcome. Ask only when it changes the lesson.
2. Plan a visual story: a concrete anchor, then the mechanism, then the result. Each step answers one question and leads to the next.
3. Choose the medium per step by its job (MEDIUM-ROUTER.md). No media quota.
4. Change one condition and show why the result changes. Map the picture to the formal terms. Say where an analogy stops holding.
5. Check every step earns its place, labels match the text, and controls do what the text says. Name any check the host couldn't do.
6. Deliver the whole lesson, then "where to next?".
7. When it doesn't click, repair (change one thing). Never repeat the same explanation in new words.

If a requested animation or interaction can't be made after trying the suitable tools, deliver an accurate static version and say what's missing. If the learner said that medium is essential, stop and ask instead.

In visual-explain there are no answer, navigation or closure gates. Optional checks remain skippable. In practice-first the learner requested an attempt, but can still choose "show me" or exit practice.

## practice-first

Live Q&A practice is a conversation. In a six-format routing interface its primary representation is `qa`; this does not request a Q&A webpage. Do not build a still, deck or page unless the learner requests that artifact or a supporting figure is essential to the problem. A worksheet/flashcard request is a different delivery request.

1. Present one bounded problem. Use a picture only when it carries information the problem needs, with nothing of the solution revealed. End the turn on the question.
2. A miss gets exactly one next hint, and the turn ends again.
3. Two useful misses, or "answer now", and you teach it directly from a different angle than the hints took.
4. Then a fresh variation without naming the pattern. Spacing is counted in sessions.

Request practice with `?practice=1` or `style: "practice-first"` for an explicitly requested practice artifact. Omit the style for complete explanation first. `?practice=0` exits practice. Never infer learning from viewed steps.

## Switching

The learner can switch any time ("just explain it", "let me try first"). Switch at once, and in a series, ask whether to remember it.

## Pinning a style

A pin ("always practice-first here") goes in the project instructions (for example `CLAUDE.md`) or, with consent, in a plain notes file or the series journal (`series.py log ... --note "style: practice-first"`), and is announced on resume. Never write it into teach-pro-max's `state/learner.json` or any other engine state file: that engine rejects unknown fields, so a new field breaks every later engine command. Without consent, honour the pin for this conversation only.
