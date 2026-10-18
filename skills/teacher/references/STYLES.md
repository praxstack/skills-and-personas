# Teaching styles

Style decides the order things happen in. Pick it before planning the lesson.

| Style | Default for | Order |
| --- | --- | --- |
| `visual-explain` | "teach me X", "help me understand", "build intuition" | picture and explanation first, a manipulation or prediction inside each step, one optional check, then the learner leads |
| `practice-first` | interview prep, DSA and design drills, "quiz me", "practise", or when the project pins it | a picture of the problem (never the solution), the learner attempts, one hint per miss, then teach, then a fresh variation |
| quick answer | one bounded question ("what does idempotent mean?") | a short answer and an example, a picture only if it carries the idea, offer more |

Precedence, highest first: what the learner asks for this turn, a style pinned by the project or agent instructions ("teaching style: practice-first"), a preference the learner stated in a consented journal or notes file, then the defaults above. Mode (how much to build: quick, lesson, course) is chosen separately; teach-pro-max's `route` command picks a mode only and never overrides the style.

## visual-explain

1. Infer the level and a bounded outcome. Ask only when it changes the lesson.
2. Plan a visual story: a concrete anchor, then the mechanism, then the result. Each step answers one question and leads to the next.
3. Choose the medium per step by its job (MEDIUM-ROUTER.md). No media quota.
4. Change one condition and show why the result changes. Map the picture to the formal terms. Say where an analogy stops holding.
5. Check every step earns its place, labels match the text, and controls do what the text says. Name any check the host couldn't do.
6. Deliver the whole lesson, then "where to next?".
7. When it doesn't click, repair (change one thing). Never repeat the same explanation in new words.

If a requested animation or interaction can't be made after trying the suitable tools, deliver an accurate static version and say what's missing. If the learner said that medium is essential, stop and ask instead.

In visual-explain the explanation comes first by design, so attempt-first gates (teach-pro-max's first live-lesson gate included) apply only to the optional check. In practice-first they apply unchanged.

## practice-first

1. Show the problem as a picture, with nothing of the solution in it. End the turn on the question.
2. A miss gets exactly one next hint, and the turn ends again.
3. Two useful misses, or "answer now", and you teach it directly from a different angle than the hints took.
4. Then a fresh variation without naming the pattern. Spacing is counted in sessions.

The explorable engine follows this order inside each step: manipulate, commit, then the why.

## Switching

The learner can switch any time ("just explain it", "let me try first"). Switch at once, and in a series, ask whether to remember it.

## Pinning a style

A pin ("always practice-first here") goes in the project instructions (for example `CLAUDE.md`) or, with consent, in a plain notes file or the series journal (`series.py log ... --note "style: practice-first"`), and is announced on resume. Never write it into teach-pro-max's `state/learner.json` or any other engine state file: that engine rejects unknown fields, so a new field breaks every later engine command. Without consent, honour the pin for this conversation only.
