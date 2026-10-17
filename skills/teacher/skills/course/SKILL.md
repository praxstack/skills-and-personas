---
name: course
description: Turn a set of lessons into a course with a map of the whole subject (lessons placed by prerequisite, hand-drawn arrows), each lesson offering Quick explain, Teach me (interactive), Watch (film or narrated video), Read and run the code, Quiz me, and a Learning, Done or Skip status; plus an outline and a notes sheet kept apart from the lessons, and a catalog of courses. Use when a subject needs more than one sitting. Builds static pages in the lesson-notebook look and tests every lesson's code, interactions and looks in one command.
---

# Course

One lesson teaches one idea. A course is a map of ideas, so the learner can see the whole subject, where they are, and choose the next step and the medium they want, as often as they like.

## Layout

```
courses/<id>/
  course.json            id, title, subtitle, level, prereqs (other course ids), shared (model scripts), lessons
  <model>.js             optional shared model, loaded before every lesson (window.Something = ...)
  lessons/*.lesson.js    explorables (see ../explorable/SKILL.md)
  lessons/*.anim.js      concept animations (see ../concept-animation/SKILL.md)
  videos/<lesson-id>.mp4 optional narrated videos, with .vtt captions beside them
```

Each `lessons[]` entry: `id`, `file`, `title`, `needs` (ids of lessons it builds on, which place it on the map), `minutes`, `summary` (the plain one- or two-sentence Quick explain).

## Build and test

```sh
python3 scripts/build_course.py courses/segment-tree -o site/segment-tree     # one course
python3 scripts/build_course.py --catalog courses -o site                      # every course plus a catalog page
python3 scripts/test_course.py courses/segment-tree                            # code, interactions and looks of every lesson, then the course page
```

`--fragment` builds pages for hosts that wrap them (Claude artifacts). Pages are single files and work from disk.

## What the course page does

- **Map**: lessons left to right by prerequisite (top to bottom on phones), arrows drawn by the pen. Click a lesson to open its panel.
- **Panel**: Learning / Done / Skip (remembered in the browser), Quick explain, Why it mattered, and the same idea in every medium: Teach me, Watch (the narrated video when there is one, else the lesson's film), Read and run the code, Quiz me, Notes. "Can you say it back?" shows the lesson's explain-back question.
- **Quiz me**: the lesson's questions, answers resolved from its model at build time; try first, then see why. The score is a clue, not a finish line: a miss links back to its step.
- **Outline** and **Notes**: separate views. Notes gather every lesson's margin notes, mix-ups and deeper questions on one sheet for review.

Patterns from roadmap.sh, Educative and Brilliant (see `teacher/references/DESIGN-INSPIRATION.md`).
