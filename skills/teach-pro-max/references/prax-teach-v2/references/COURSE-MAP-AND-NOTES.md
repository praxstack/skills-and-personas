# Course map and reusable notes

Organize ongoing learning without building an app. In chat, use short linked or
labeled sections. In a saved lesson/course, a small structure can be enough:

```text
lessons/map.md                 # purpose, prerequisites, branches, current location
lessons/0001-ratios.md         # current complete explanation
lessons/notes.md               # reusable definitions, reasoning, limits, questions
```

Every saved Markdown document receives its generated same-basename HTML companion.
File names are examples, not a required schema. A short question needs no map,
notes file or course directory. Do not copy the same lesson into three documents.

The map answers what the learner is exploring, what supports it, where they are
and which branches are available next. Change the path as curiosity changes.
“Covered” means exposure; only actual learner performance supports competence.

The stage teaches the current bounded question fully, with linked prerequisites
where helpful. Keep the whole figure and finished state available even when the
learner requests replay or a layered explanation. Notes preserve reusable
definitions, worked reasoning, assumptions, limitations, source links and open
learner questions. Link to exact lesson sections or visuals instead of repeating
them. Mark tutor inference separately from learner-authored statements.

Tracking and artifact saving are independent. Optional consented runtime state
belongs in the existing per-directory `.prax-teach/state`, never a custom notes
schema. In lesson/course mode, explain default artifact saving in `lessons/` even
when tracking is declined; in quick mode, files require an artifact request.
Declining tracking keeps a requested course map and sequence ephemeral rather
than demoting the course. Save-nothing forbids durable map, notes and lesson files
as well as state. Use host delivery or an actually removable temporary preview,
and explain any host storage limits. Do not invent recovered progress.
