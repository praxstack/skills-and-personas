# Lesson model (prax-teach/lesson@1)

The schema is `schemas/lesson.schema.json`. One file, `lesson.json`, plus `programs/*.c`.

- `programs[]`: C17 sources. `ub: true` programs compile but never run.
- `facts[]`: each displayed value. `select` says where capture reads it (`stdout` line N, whole stdout, or a `platform` key). `expect` is an independent computation from `ptk/expect.py` (`{"fn", "args"}`) or a reviewed literal. Capture fills `value` and `source`; never write them by hand.
- `claims[]`: every teaching sentence. `kind`, `justification`, and at least one `source` (C17 clause with a short quote, or the captured run). List the `facts` a claim states.
- `misconceptions[]`: a wrong belief and the claim that corrects it.
- `trace[]`: states the explorer can show: program, current line, executed path, output facts so far.
- `storyboard[]`: scenes for the video. Each narration line cites claims and may carry a `spoken` respelling. A `question` names the fact that answers it; nothing may state that answer before the next reveal.
- `figure`: the still's layout hints (program, trace states, notes at lines, comparison state, caption claims).
- `mutations.json` (optional, next to lesson.json): planted false claims for the claims-sensitivity gate.
