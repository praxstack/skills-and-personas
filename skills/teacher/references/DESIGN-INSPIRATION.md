# Design inspiration

Patterns a teacher can borrow from learning products when it builds lessons, visuals and course pages.
Each product was checked on 2026-10-16. "Seen" means confirmed on the live page or by driving it in a browser; "inferred" means read from link labels or marketing copy only.
The teacher's own defaults (lesson-notebook look, explorable flow) already use several of these; the last sections say which.

## Brilliant (brilliant.org)

Interactive maths, science and CS lessons with an AI tutor named Koji. Seen on the page: the tutor "never just gives you the answer", it "asks guiding questions, sketches on your screen, gives hints", offers "alternative explanations", checks mastery with "regular assessments" and builds targeted practice from the gaps. Sessions are short ("the quiet 20 minutes before dinner"). The page shows no streaks or leagues today.

- Hold the answer back. Ask a guiding question or give a hint first; the explanation comes after the learner commits.
- Sketch on the learner's picture, not beside it: marks go on the figure they're already looking at.
- Keep "explain it another way" one tap away.
- Build the next practice from what was missed, not from a fixed list.
- Pace by mastery: speed up when they're ready, slow down when they're not.

## Educative (educative.io)

Text-first technical courses. Seen: an "interactive, text-based approach" instead of video, "in-browser quizzes, challenges, and projects" with "no setup, no config", real-time AI feedback on code, AI mock interviews, and an AI tutor that helps "without giving away answers". Courses sit in structured paths with hours and last-updated dates. Inferred, not on the page: the separate outline, lesson and notes panes (the marketing page doesn't show the course reader).

- Text you can skim beats video you must sit through, for technical material. Keep video for what text can't show.
- Put the playground inside the lesson. Running code, or moving the model, is part of reading.
- Separate the course outline, the lesson and the learner's notes so each can be used on its own.
- Show the size of a course up front (hours, steps) and when it was last updated.

## Matt Pocock's teach skill (github.com/mattpocock/skills, productivity/teach)

An agent skill that keeps a teaching workspace: `MISSION.md`, `reference/`, `RESOURCES.md`, `learning-records/`, `lessons/` (short, self-contained HTML), `assets/` (reusable components, a shared stylesheet first) and `NOTES.md`. Seen, quoted from its SKILL.md:

- "Never trust your parametric knowledge." Teach from primary sources.
- "Fluency can give the user an illusory sense of mastery, but storage strength is the real goal."
- "For acquiring knowledge, difficulty is the enemy." But "For skill acquisition, difficulty is the tool."
- "Confirm with the user before changing the mission." The mission grounds every lesson.
- "Reuse is the default, not the exception."
- "Each lesson should contain a reminder to ask followup questions to the agent."

What to take: a mission the learner owns, lessons as small HTML files built on shared assets, compressed reference sheets, and the knowledge-versus-skill split (make understanding easy, make practice effortful).

## fanout.sh

Technical learning across AI research, system design and ML maths. Inferred from its navigation: roadmaps, "Interactive AI and System Design Labs", a "Mathematical Notation Library", a paper decoder, "AI Research Papers Explained Daily", a "Knowledge Topography" view and "Study With Me" sessions.

- Give dense subjects a notation reference: every symbol, what it means, where it appears.
- Decode primary sources (papers) rather than replacing them.
- Show the whole subject as a map the learner can see themselves on.
- Labs next to theory: the lab is where the idea gets used.

## Nibble (nibble-app.com)

General-knowledge microlearning, 35+ topics. Seen: sessions "from 3 to 10 minutes", lessons you read and tap through with questions "along the way", plus games, video and audio episodes, and chats with historical figures. You "Match the format to your time".

- Ask small questions inside the reading, not only at the end.
- Offer the same lesson in more than one format and let the learner pick by the time they have.
- Make stopping anywhere safe: progress is kept.

## Imprint (imprintapp.com)

Visual summaries of important ideas from books, courses and experts. Seen: "the world's most important knowledge, visualized", "elegant visuals that clarify key ideas", and saving key ideas to review later. Lesson length and review scheduling weren't on the page.

- One clear visual per key idea, made to be remembered.
- Let the learner save the ideas that mattered to them, and bring those back later.

## SystemDR video (youtube.com/watch?v=EP3DvnIkybo)

Title from YouTube's oEmbed: "Cortex Curriculum: Hands-On AI System Design Course", by SystemDR (Scalable System Design). The page itself wasn't fetched and its contents weren't watched, so only the framing is known: a hands-on, build-it curriculum for AI system design.

- For systems topics, teach by building a small working system, then stressing it.

## AlgoCamp (algocamp.io)

Seen: a training platform for backend and AI engineers ("Forging the next generation of backend engineering leaders"): a 6-month project-driven AI engineering programme, a 16-week live Spring Boot cohort, and a system design course covering low-level and high-level design. The page shows no detail on algorithm teaching.

- Cohorts and projects: learning anchored to building something real over weeks.
- Treat low-level and high-level design as one ladder, not two subjects.

## AlgoMaster (algomaster.io)

Interview prep by pattern. Seen: "Master Patterns, Not Just Problems", 60+ coding patterns over 600+ problems, 20+ system design patterns, explanations paired with animations, chapters you can mark done or star to revisit, audio playback, highlighting, inline notes, quizzes with instant feedback, code run against tests, and an AI mock interviewer.

- Teach the pattern, then vary the problem until the learner recognizes it unprompted.
- Let the learner star what they want to revisit and highlight or annotate the text itself.
- Pair every algorithm explanation with an animation of its state.

## roadmap.sh, inference engineering (roadmap.sh/inference-engineering)

Seen by driving the page in Chromium: a large node graph (about 180 topic nodes, from Neural Networks and GPU Architecture to Speculative Decoding and Disaggregation). Clicking a node opens a drawer with a short description, status buttons "Learning", "Done" and "Skip", "Learn with AI" actions ("Quick Explain", "Teach Me", "Quiz me") and typed free resources (Article, Video). A banner counts others tracking progress; "Personalize" and an AI Tutor tab sit above the map.

- Show the whole subject as a map first; let the learner jump to any node.
- Three honest statuses per node: learning, done, skip. Skip is a legitimate choice.
- Per node, offer depth on demand: a quick explanation, a full lesson, or a quiz.
- Type the resources (article, video, paper) so the learner can choose by format.

## Wondering (wondering.app)

Any topic as a course of "3-minute lessons". Seen: each lesson available as narrated video, podcast-style audio or text with diagrams; a "global review" that pulls questions from all courses, scheduled with FSRS; personalization from goals and background; an AI tutor for follow-ups and simpler explanations; streaks, XP and streak freezes; a "Canvas" for exploring ideas in parallel.

- One review queue across every subject, scheduled before forgetting.
- The same lesson as video, audio or text.
- Every lesson ends by opening the next question.

## DeepLearning.AI courses (deeplearning.ai/courses)

Seen on the catalog: 107 short courses, 13 courses and 11 professional certificates; each listing shows its total length (from about 36 minutes to over 127 hours), a Beginner or Intermediate level, and instructors, often built with an industry partner. Whether lessons pair video with notebooks wasn't shown on the catalog page.

- Label length and level on every course so learners can choose honestly.
- Short courses for one skill, longer certificates for a field.
- Teach with the people who build the tools.

## Patterns to adopt

### Interaction and visuals

1. Manipulate, commit, then explain. Hold the answer back until the learner has predicted or tried. (Brilliant; already the explorable's step flow.)
2. Draw the explanation on the learner's picture, live. (Brilliant's sketching; the lesson-notebook pen.)
3. "Explain it another way" is always one tap away, and each try changes one thing. (Brilliant; the explorable's "Still confused?")
4. Pair every process or algorithm with an animation of its state. (AlgoMaster; concept-animation.)
5. Put the playground inside the lesson: sliders, runnable code, a lab. (Educative, fanout; explorables.)
6. One clear, memorable visual per key idea. (Imprint; explain-diagram's claim-first stills.)

### Course structure

7. Keep the outline, the lesson, the learner's notes and practice in separate places. (Educative pattern as Prax described it, AlgoMaster's notes; the explorable's contents, lesson, margin and Notes view.)
8. A mission or goal the learner owns, changed only with their say-so. (Matt Pocock; `series.py init --goal`.)
9. Lessons as small, self-contained HTML files built on shared assets. (Matt Pocock; the bundler and lesson-notebook.)
10. Compressed reference sheets: notation, glossary, the key formulas. (Matt Pocock, fanout's notation library.)
11. Offer each lesson in more than one format: interactive, film, transcript, audio. (Nibble, Wondering; explorable film and transcript.)
12. Label every course with its length, level and last update. (Educative, DeepLearning.AI.)

### Pacing and retention

13. Short steps, safe to stop anywhere, progress kept. (Nibble, Wondering.)
14. Small questions inside the reading, not only at the end. (Nibble.)
15. One review queue across all subjects, scheduled before forgetting. (Wondering's FSRS; `series.py resume` lists due recall across threads.)
16. Make understanding easy and practice effortful. (Matt Pocock's knowledge-versus-skill split.)
17. Build the next practice from what was missed. (Brilliant; the explorable report feeds the next session.)

### Roadmaps and depth

18. Show the whole subject as a map, with the learner's place on it. (roadmap.sh, fanout.)
19. Per node: learning, done or skip, plus depth on demand (quick explain, teach me, quiz me). (roadmap.sh; maps to the depth ladder and `series.py` thread states.)
20. Teach patterns, then vary problems until the pattern is recognized unprompted. (AlgoMaster.)

## What not to copy

- Streak pressure. Streaks and streak freezes reward showing up, not understanding. If anything is counted, count ideas the learner can explain.
- XP and leagues for clicks. Points for finishing a lesson teach finishing lessons.
- Paywalled resources in the middle of a lesson, or ads beside it.
- "Mastery" from a quiz score. Fluency feels like mastery; storage strength shows up later, in an unaided answer next session.
- Infinite feeds of tiny lessons with no map, so the learner never sees where they are.
- Personalization that only changes tone. Personalize the example, the representation and the next step.

## Sources

| Source | Checked | How |
| --- | --- | --- |
| https://brilliant.org/ | 2026-10-16 | fetched directly |
| https://www.educative.io/ | 2026-10-16 | fetched directly (marketing page; course reader not visible) |
| https://raw.githubusercontent.com/mattpocock/skills/main/skills/productivity/teach/SKILL.md | 2026-10-16 | fetched directly |
| https://fanout.sh/ | 2026-10-16 | fetched directly (navigation only, so patterns are inferred) |
| https://nibble-app.com/ | 2026-10-16 | fetched directly |
| https://www.imprintapp.com/ | 2026-10-16 | fetched directly |
| https://www.youtube.com/watch?v=EP3DvnIkybo | 2026-10-16 | title and channel via YouTube oEmbed; not watched |
| https://www.algocamp.io/ | 2026-10-16 | fetched directly |
| https://algomaster.io/ | 2026-10-16 | fetched directly |
| https://roadmap.sh/inference-engineering | 2026-10-16 | driven in Chromium: node list read, a node drawer opened |
| https://wondering.app/ | 2026-10-16 | fetched directly |
| https://www.deeplearning.ai/courses | 2026-10-16 | fetched directly |
