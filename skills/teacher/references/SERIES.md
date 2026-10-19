# Series of sessions

One sitting is enough for one idea. A subject (transformers, organic chemistry, the French Revolution, system design) takes a series. The journal lets any host pick up where the last one stopped.

## Consent first

Ask before keeping anything: "Want me to keep a short learning journal in this folder so next time I can pick up where we left off? It's two plain files in `.teacher/`, and you can delete them any time." Only on a yes run `series.py init`. If they say no, teach without it and don't ask again this session.

## Shape of a series

- **Goal**: one sentence the learner agrees with ("implement a transformer from scratch and explain each part").
- **Map**: break the goal into threads, ordered by prerequisite. Draw it as a concept map or roadmap (`explain-diagram`) and show the learner where they are. Each thread names its depth target (L0 to L4).
- **Threads**: one idea each (`attention`, `positional-encoding`). A thread is open, satisfied (the learner said so) or parked.
- **Sessions**: `series.py resume` starts the next one and prints open threads, what's still unclear, which explanations were already tried, and which recall points are due.

## In each session

1. `resume`. Read it before saying anything.
2. Continue the open thread, or start the next one on the map with a complete explanation. Do not turn resumption into a quiz gate.
3. If recall points are due, offer one after the explanation. Put recall first only when the learner explicitly asked for a practice-first session. Record an attempted point with `recall result ID N --right|--wrong [--unaided]`. A miss, or a right answer that needed help, brings the point back next session; it stays due until shown unaided.
4. `log` what you did, what's still unclear, and which explanations were tried. Be specific; the next session depends on it.
5. Add 1 to 3 `recall` points per thread worth keeping: claims they should be able to explain, not trivia.
6. `satisfied` only when the learner says it. `level` when they climb a rung.

## Rules

- Spacing is counted in sessions, not days: due 1, 3 and 6 sessions after it's taught. People don't study on a calendar.
- "Demonstrated" means a right, unaided answer in a later session than the teaching one. Same-session answers don't count.
- The journal never holds grades or judgements about the person, only what was taught, what was unclear, and what was tried.
- The learner can read `JOURNAL.md` any time and delete it all with `series.py forget --yes`.

## Coordinating a long series

For a long course, keep the map in the journal's goal and threads, and build each session's materials when that session starts, not all up front: what the learner needs next depends on what happened last time. Heavy assets (a narrated video for a recap) can be built in the background by another agent while the session goes on (see ORCHESTRATION.md).
