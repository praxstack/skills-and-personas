# WP1 review: router and teaching protocol

Commits reviewed: `7530137` and `03ca5a3` (committed diff, read with `git show`, not the working tree).
I didn't read holdout/ or plan/proposed/.
Reviewer: independent review agent, 2026-10-18.

## Verdict

**Request changes.** No P0. Three P1s.

The router does better than I expected on natural, positively phrased requests. My 60 fresh prompts scored
58/60 (details below). It breaks in one predictable place: **negation**. "I don't want a video" builds a
video, and "dont ask me questions" starts a quiz. Negation is how Prax pushes back. D20.7 exists because
he turned a prediction question down, so this is the case that matters most.

The protocol checker catches structural breaks well: turn order, the stop rule, evidence consent,
layer order, exam fields. But the two things AC-1.6 names that need judgement, "exactly one hint" and
"classify the attempt", are taken on the tutor's word. A tutor that gives three hints or calls a
misconception correct still passes.

Tests at `03ca5a3` pass in a clean worktree: `test_route` 8/8, `test_protocol_transcripts` 2/2
(the automatic ones; I didn't run the agent tests), `test_skill_budget` 1/1.

## Fresh-prompt generalisation

Set: `reviews/wp1-fresh-prompts.jsonl`, 60 prompts I wrote. None are copies of the dev set. 30 use no
workspace. 30 use a predict-first workspace: I ran them against Prax's real C workspace (read-only),
and the `predict` fixture gave the same intent, mode and media on all 30. Each row has `expect` (my
first label), an optional `accept` (other outcomes a good tutor could defend) and `tutor` (what a good
tutor does). Everything ran through the CLI: `ptk route "<req>" --workspace <dir> --json`.

| Scoring | Result |
|---|---|
| Lenient (accept lists allowed) | **58/60** |
| quick and explain counted as the same outcome (both answer in chat, no build) | 56/60 |
| Strict (my first label only) | 54/60 |

The two misses:

| id | request | got | should be |
|---|---|---|---|
| r009 | render the video again, the audio is out of sync | teach, lesson, [video], build | ordinary task (re-render an existing build) |
| r020 | can you make an animation where i can drag the slider and see the bits flip for a signed char | lesson [explorer, video] | lesson [explorer] (dragging a slider is an explorer; "animation" here describes it) |

The two judgement calls, which passed only because I allowed them:

- r024 "flashcards + a short video on operator precedence, also quiz me after" routes to `quiz` with
  media [cards, video]. The learner asked for the build first and the quiz after. Under quiz, the
  first turn is Q1, not the build.
- r051 "let me ask you some follow up questions about pointers to pointers, answer in layers" in the
  predict-first workspace routes to `predict-first`. That matches the spec (AC-1.3 only exempts answer
  now, just explain and full course), but here the learner is the one asking. See P2-5.

r006 "write a function that reverses a linked list and make a video of it running" counts as a pass
(lesson, [video]). But the coding half of the request disappears from the route. See P2-6.

### Adversarial probe: 40 more requests aimed at regex weak spots

The 60 above are natural requests, and most use words the table knows. To test brittleness I also
ran 40 requests built to hit negation, topic words and verb position. These are not in the JSONL.
26 of 40 misrouted:

| class | examples (route got) |
|---|---|
| negated medium is built | "I don't want a video, just explain pointers" (lesson, video); "no video please, explain recursion" (lesson, video); "teach me pointers, not as a video" (lesson, video); "quiz me, no cards" (quiz, cards built) |
| refusing questions starts a quiz | "dont ask me questions, what does static do" (quiz, in both workspaces); "explain without the quiz thing" (quiz) |
| natural override missed in the contract workspace | "give me the answer directly" (predict-first); "I just want the explanation, no back and forth" (predict-first); "no need to ask me, show me the video on pointers" (predict-first) |
| topic word read as a medium | "teach me about video codecs", "explain how mp4 compression works", "teach me how to animate in CSS", "how to make a video in python" (all video builds); "explain how to shuffle a deck of cards in C" (cards); "explain the interactive mode of gdb" (explorer); "how do images get stored in memory", "what is the figure of merit" (still) |
| task not recognised | "the explainer video you made had wrong numbers, fix it" (lesson build); "check my code for bugs", "make it faster", "test the parser" (explain); "do not explain, just fix it" (quick) |
| other | "can you predict how long the build takes" (predict-first); "I watched a video on pointers but I'm still confused" (video build); "show me a visual of malloc" (explain, no still) |

The negation, refusal and override rows above should all become dev-set rows.

## Findings

### P1-1. Negated media are still built, and SKILL.md tells the agent not to second-guess the route

Confidence: high (reproduced through the CLI).

- `package/prax-teach/ptk/route.py:63-71` `detect_media` adds every medium whose word appears. Only
  narration has a negation guard (`route_rules.json:99-101`). Video (`:72-88`), explorer
  (`:104-118`), cards (`:129-143`) and still (`:144-167`) have none.
- `route_rules.json:356-359` `with_media` then turns an explicit "just explain" into a lesson build.
  So "I don't want a video, just explain pointers" gives `mode: lesson, media: [video], build_needed: true`.
- `package/prax-teach/SKILL.md:22` says: "Don't re-decide." An agent that follows SKILL.md exactly
  will announce and run a two-minute video build the learner just said no to.

Fix: add a `negated` macro, roughly
`\b(?:no|not|without|don'?t (?:want|need)|skip|minus)\b(?:\s+\S+){0,3}?\s+`, and put
`<<negated>><medium word>` in the `unless` list of every medium rule. Better still, strip negated
spans from the text before media detection, the same way `detect_media` already strips matched
spans. Add the four negated-medium probes above to the dev set. Then soften SKILL.md:22 to: "If the
route plainly contradicts the learner's words (a medium they refused, a task they asked you to do),
follow the words and say so in one line."

### P1-2. "Don't ask me questions" routes to quiz, and natural override phrasing misses D20.7

Confidence: high.

- The `attempt` stage sits above the workspace contract (`route_rules.json:341-349`). Its quiz rule
  (`:280` `\bquiz(?:zes)?\b`, `:284` `\bask me (?:\w+ )?(?:questions|problems)\b`) has no `unless`.
  So any request that mentions "quiz" or "ask me questions" becomes a quiz, even when it is a refusal.
- The refusal rule `no-questions` (`:237-241`) needs an exact apostrophe (`(?:don't|do not) (?:ask|quiz|test) me`)
  and the exact phrasing `without (?:asking|questions|quizzing|a quiz)`. "dont ask me questions"
  (Prax's usual spelling, see r057) and "without the quiz thing" both fall through to the quiz rule.
- `answer-now` (`:212-227`) misses "give me the answer directly", "I just want the explanation, no
  back and forth" and "no need to ask me". In the predict-first workspace all three get a prediction
  question. That is the exact situation D20.7 was written to stop.

Fix: make the apostrophe optional everywhere (`don'?t`, `dont`, `do not`). Give every `attempt` rule
`unless: ["<<NEG_ASK>>"]`, where NEG_ASK covers `(?:no|don'?t|do not|without|skip|stop|no need to)\b[^.]{0,25}\b(?:ask|quiz|question|predict)`.
Widen `answer-now` to cover `answer directly`, `the answer directly`, `no back and forth` and
`no need to ask`. Add these as `override` dev rows run against the `predict` fixture.

### P1-3. AC-1.6's one-hint and classification checks trust the tutor's own labels

Confidence: high (I ran each case through `protocol.check_transcript` with the slice lesson; all
returned `[]`).

- `package/prax-teach/ptk/protocol.py:101-102` checks `x.get("feedback_items") != 1`. That field is
  written by the tutor itself (`tests/test_protocol_transcripts.py:263-264`). A feedback turn whose
  text lists three corrections, labelled `feedback_items: 1`, passes.
- `protocol.py:99-100,103-106` only checks that the classification is well formed and that the
  misconception id exists. The scripted attempt at `test_protocol_transcripts.py:226` ("The next
  case label stops it.") is plainly `misconception:m.stops`. A tutor that classifies it `correct`
  passes.
- Waiting is half checked. Turn order is enforced by the harness and by `check_common`, and the first
  turn must have `acts == ["question"]` with exactly one `?` (`protocol.py:97-98,149`). But a hint
  inside the opening question ("Hint: a case label does not stop anything, so look for the next
  break. What does it print?") passes. TEACHING.md:40 says "Don't add hints ... while waiting".

So `test_predict_first_flow` checks the shape of the conversation, not AC-1.6 items 2 and 3.

Fix: (a) give each scripted learner turn an `expect_class` (here `misconception:m.stops`) and fail
when the tutor's classification differs. (b) Count feedback items from the text, not the label: in
`text` with code removed, count sentences that contain a correction marker, or require the tutor to
put the single item in a `feedback` string field and check it is one sentence of 40 words or fewer.
(c) Make the first-turn leak check also fail on hint markers (`hint`, `look at`, `notice`,
`remember that`) and on any misconception's correction-claim text from the lesson. Add these three
cases to the `breaks` dict in `test_no_reveal_before_attempt`.

### P2-1. Topic words are read as media

Confidence: high. `route_rules.json:75` `\bvideos?\b`, `:82` `\bmp4\b|\bgifs?\b`, `:76`
`\banimat(?:e|ed|...)`, `:136` `\bcards?\b`, `:108` `\binteractive\b`, `:152-154` figures, pictures,
images. These match the word anywhere. The topic examples in the probe table all trigger a build.
For a C learner, "how do images get stored in memory" and "shuffle a deck of cards in C" are ordinary
requests.

Fix: when a medium word comes right after `about|on|of how|how (?:to|do|does)|mode of|deck of`,
treat it as the topic, not the medium. Or require a request frame for single bare nouns:
`(?:as|in|with|into|make|build|give me|show me|want) (?:a |an |the )?(?:\w+ ){0,2}<medium>`. Keep
the unframed match only for words that only ever mean a medium (`narrated`, `manim`, `3b1b`,
`flashcards`, `anki`).

### P2-2. Tasks that mention "explain", or don't start with the verb, become teaching

Confidence: high. `route_rules.json:33` anchors the code verb at the start of the request (`<<PFX>>`),
and `:35-37` voids it when TEACH matches anywhere. In Prax's workspace, "fix the bug and explain what
was wrong", "run the tests and explain the failure" and "refactor loops.c and explain why it's
better" all route to `predict-first`. The task doesn't get done; the tutor asks a prediction
question instead. "the explainer video you made had wrong numbers, fix it" builds a new lesson.
"check my code for bugs", "make it faster" and "test the parser" aren't recognised as tasks at all.

Fix: when a request has a task verb plus "explain", route `ordinary_task` with an `explain_after: true`
flag (do the task, then explain). Match task verbs at the start of any clause
(`(?:^|[,.;] |\band (?:then )?)`). Add `check`, `test`, `render`, `re-?run` and
`make it (?:faster|work|compile)`.

### P2-3. The question-mark counter fails good transcripts

Confidence: high. `protocol.py:97-98` counts `?` in the raw text. A prediction question about a
ternary in a fenced block ("```c int k = n ? 2 : 3; ``` What does it print?") fails with 2. "Predict
the output of the program for n = 2." fails with 0. Both are good first turns, and the live agent
test will flake on them.

Fix: count on `CODE.sub(" ", text)` and also strip inline code. Accept either one `?` or an
imperative opener (`predict|what|which|trace|work out`).

### P2-4. A partial reveal isn't caught

Confidence: medium. `protocol.py:70` `need = min(2, len(answer_lines))`. For the slice answer
`two / three / done`, "It keeps going into case 3, so three shows up. What is the full output?"
passes. That sentence gives away the fallthrough, which is the whole point of the question.

Fix: also treat as a leak any answer line that differs from what the no-fallthrough misconception
predicts (here `three`), or any single answer line next to a causal phrase. At minimum, add this
case to `breaks`.

### P2-5. "Q&A" as a medium makes a chat Q&A build an artifact

Confidence: high. `route_rules.json:120-128` `m-qa` matches `q&a` anywhere. "lets do a q&a session on
pointers" in the C workspace gives `predict-first, media [qa], build_needed: true`. The learner
wanted to ask questions in chat; nobody asked for an expander page. The declared deviation itself (a
Q&A expander is a medium) is right per AC-1.1. The bug is that "q&a session" and "let me ask you"
also count as media.

Fix: add `unless: ["\\bq&a session\\b|\\blet me ask\\b|\\b(?:answer|take) my questions\\b"]` to `m-qa`,
or require an artifact noun (`expander`, `page`, `cards`, `set`).

On the related deviation, qa-expand losing to the contract (TEACHING.md:101-102): it follows the
spec's letter. But when the learner asks to lead with questions, opening with a prediction is
awkward. Consider moving `qa-expand` into the `attempt` stage, justified the same way as quiz: the
learner is already driving. Or ask Prax. This is a spec question, not a code bug.

### P2-6. Multi-intent requests drop one intent with no signal

Confidence: medium. r006 (write code + video) returns only the lesson. r024 (cards + video, quiz
after) returns quiz, so the first turn is Q1, not the build. The route has no way to say "and then".

Fix: add `also: [...]` to the output (for example `also: ["ordinary_task"]` or `also: ["quiz"]`)
whenever a lower-priority stage also proposed something, plus one SKILL.md line on how to sequence
it. That costs about 60 characters of budget.

### P2-7. Leaving out `--workspace` fails silently

Confidence: medium. `route.py:103` uses `Path.cwd()`. If the host runs `ptk` from the skill
directory or a scratch directory, the contract is `{mode: null, files: []}` and the route quietly
becomes explain-first. SKILL.md:18 does pass `--workspace`, so this is a fallback, which is
acceptable. But nothing flags it.

Fix: when `--workspace` is missing and cwd has none of the three files, add
`"warning": "no workspace contract found in <cwd>; pass --workspace"` to the output.

### P3

1. `route_rules.json:293` `\bpredict(?:ion|ions|ing)?\b` fires on "can you predict how long the build
   takes" (predict-first). Require a learner subject (`let me|i(?:'ll| will)? predict|ask me to predict|prediction (?:question|first)`).
2. `:221` `\bin (?:one|two|three|five|ten|\d+) minutes?\b` turns "teach me pointers in 5 minutes"
   into `quick`. That's defensible, but a short lesson isn't the same as a one-line answer.
3. `with_media` (`:356-359`) turns a quick question about an existing artifact ("in one sentence,
   what does the diagram in the lesson show") into a still build. Skip `with_media` when the medium
   follows `the|this|that|your`.
4. A workspace that only says "Socratic" (the fixture, and Prax's real MISSION.md) maps to
   `predict-first`, not `socratic` (`route_rules.json:352-355` contract_modes). Fine as a
   simplification, but say so in TEACHING.md.
5. `protocol.py:218` socratic has no mode check (`lambda: []`). It isn't required by AC-1.8, but the
   "two unproductive answers, then teach directly" rule (TEACHING.md:55) goes unchecked in every mode.
6. `protocol.py:167` checks that the quiz score has the form `k/n`, not that k matches the
   classifications. A tutor reporting 3/3 for correct, partial, correct passes.
7. `protocol.py:145` checks only the first storyboard question. A lesson with two questions gets half
   a reveal check.
8. `protocol.py:156` checks that `artifacts` is non-empty, not that the paths exist.
9. `workspace.py:20` reads the whole file, then slices to `max_bytes`. Use `open(...).read(max_bytes)`.
10. Nit: the TEACH macro (`route_rules.json:6`) is about 900 characters on one line. Split it into a
    list of named sub-macros so diffs are reviewable.

## Requested review topics

**Rule-table design.** It is still keyword regex, the same family as v2's. It has moved into JSON and
gained an explicit precedence list. That is a real improvement: the rules can be read, tested and
diffed, and `route.py` is now about 115 lines with at most five branches per function. But much of
the complexity has been relocated rather than reduced. The TEACH macro and the `unless` lists carry
the logic that `if` statements used to. Rule order inside each list matters and isn't documented per
rule. The table has no idea of scope (negation, topic versus request, clause boundaries), and that
is where every adversarial miss comes from. The fixes above stay inside the table design; none needs
a model call.

**Precedence.** As implemented: override > attempt > workspace > request (qa-expand) > media > intent
> default. That matches the brief (answer-now > contract > medium > intent), plus the declared
`attempt` stage above the contract. I agree with that stage: quiz, exam-drill and socratic already
make the learner attempt first, so they satisfy the contract. The ordering is right. The problem is
in what each stage matches (P1-2). The stage that outranks the contract has the weakest guards.

**Loader budget (AC-1.9).** SKILL.md is 3,841 characters and the whole of TEACHING.md is 6,962. The
largest `route --json` over the dev set, run against Prax's real C workspace (four evidence lines),
is 1,530. Total about 3,080 tokens of the 4,000 budget. The test measures with a one-line fixture
workspace, so it slightly under-counts the real case, but there is plenty of headroom. The test is
also conservative in one way: it counts all of TEACHING.md, while SKILL.md only asks for the routed
mode's section.

**SKILL.md clarity.** Clear and short. The step list and the mode table are easy for an agent to
follow, and keeping LESSON-MODEL.md until build time is right. Two gaps: "Don't re-decide" (P1-1)
leaves no room for an obvious misroute, and nothing says what to do with a multi-intent request
(P2-6).

**Declared deviations.**

| deviation | verdict |
|---|---|
| `ptk/protocol.py` (not in the spec layout at SPEC.md:86) | Accept. The checker needs a home; it's pure and tested. Add it to the layout. |
| extra route fields `narration`, `rules` | Accept. `rules` is the best debugging aid in the package, and the cost is about 100 characters. |
| `--workspace` defaults to cwd | Accept, with the warning in P2-7. |
| Q&A as a medium | Accept per AC-1.1, but narrow the trigger (P2-5). |
| quiz, exam and socratic keep their mode in a predict-first workspace | Accept, but guard those rules against negation (P1-2). |
| "interactive video" routes to IVE only | Accept. The removal pass in `detect_media` does this cleanly. r020 shows the opposite case ("animation" plus a slider should be an explorer only) isn't handled. |

## Notes on method

- Worktree: `git worktree add --detach .state/review-wp1 03ca5a3`, with
  `PATH=<worktree>/package/prax-teach/bin:$PATH`. Removed after the run.
- Selftests ran with `PTK_STATE` set to a scratch directory, so nothing was written to the shared state.
- The real C workspace was only read, by `ptk route`.

## Disposition (WP1 fix round 1, 2026-10-18)

Implementer's notes. Tests: `ptk selftest -k test_route` 16/16, `-k protocol_trans` 2/2, `-k budget` 1/1.
Agent tests not run.

| finding | status | where |
|---|---|---|
| P1-1 negated media built | fixed. The router reads a `positive` view with every negated span removed (cue plus the rest of its clause, at most six words). A refused medium is never built, and the route goes low confidence. SKILL.md no longer says "Don't re-decide". | `route.py` `views`, `route_rules.json` `negation`; `test_negated_medium_is_never_built` |
| P1-2 refusal starts a quiz, natural overrides missed | fixed. Attempt rules read the positive view. `no-questions`, `answer-now` and `just-explain` now cover `dont`, "without the quiz thing", "answer directly", "no back and forth", "no need to ask", "instead of quizzing me". | `test_refusal_beats_quiz_and_contract` |
| P1-3 checker trusts the tutor's labels | fixed. Classification is graded against the scripted learner's `expect_class` (the harness strips it before the tutor sees the file and passes it as `truth`), or against the question's `answer_key`. An attempt with neither fails. Hints are counted from the text: one `feedback` sentence, and any other non-question sentence over four words fails. The opening question fails on hint markers, on a correction claim from the lesson, and on an answer line that rules out a wrong option. The review's three counterexamples are `breaks` in `test_no_reveal_before_attempt` and each fails for the stated reason. | `protocol.py` `check_classification`, `feedback_unit`, `opening_leaks` |
| P2-1 topic words | fixed with `topic_frames` (about X, how to X, deck of X, X codecs, what is the X, watched a X, my X, the X you made) | `test_topic_words_are_not_media` |
| P2-2 tasks with "explain" | fixed. A task verb plus object at the start of any clause is a task; `explain_after: true` when it also asks why. New verbs: check, test, re-run, make it faster. New intent `rebuild` for repairing or re-rendering an existing build. | `test_tasks_and_rebuilds` |
| P2-3 question-mark counter | fixed (code stripped; an imperative "Predict the output..." counts) | |
| P2-4 partial reveal | fixed (`giveaway_lines`) | `breaks["partial reveal"]` |
| P2-5 Q&A as a medium | trigger narrowed: "q&a session", "let me ask", "answer my questions" build nothing. qa-expand still loses to a predict-first contract (AC-1.3's letter); the route now says so with `confidence: low`. Moving it above the contract is a spec change, so it waits for Prax. | |
| P2-6 multi-intent | `also[]` added: a quiz after the build, or a coding task beside a lesson (low confidence) | `test_confidence` |
| P2-7 missing `--workspace` warning | not done | |
| P3-1 predict | fixed (needs a learner subject or an output object) | |
| P3-3 question about an existing artifact | fixed by the topic frames | |
| P3-4 Socratic counts as predict-first | documented in TEACHING.md | |
| P3-6 quiz score | fixed (k must equal the answers classified correct) | |
| P3-9 workspace read | fixed (reads at most `max_bytes`); workspace negations accept `dont` | `test_workspace_negation_without_apostrophe` |
| P3-2, P3-5, P3-7, P3-8, P3-10 | not done | |

Labels where I differ from the review: r009 ("render the video again") is `intent: rebuild, media: [video],
build_needed: true`, not `ordinary_task` (the reviewer's label is kept as `reviewer_expect`). The 40
adversarial probes were not saved by the review, so a01 to a32 are rebuilt from the probe table and
findings above, with labels implied by the review's verdicts; a33 to a40 are mine, in the same classes
(`source` field on each row). a30 ("lets do a q&a session", predict workspace) expects `predict-first`
and accepts `qa-expand`, per P2-5.

Accuracy (lenient: `expect` or `accept`):

| set | before | after |
|---|---|---|
| original dev rows | 109/109 | 109/109 |
| fresh (reviewer's 60) | 58/60 | 60/60 |
| adversarial, tuning half | 2/20 | 20/20 |
| adversarial, held back (`route-dev-heldback.jsonl`, never tuned on) | 0/20 | 20/20 |
| 20 new probes written after the rules, untuned (not committed) | n/a | 17/20 |

The held-back number overstates generalisation. I wrote and read all 40 probes before writing the
rules, so the held-back half shaped the design even though I never ran or tuned on it. The 17/20 on
probes written after the fix is the more honest number. Its three misses: "forget the video, can you
just explain how free works" (forget isn't a negation cue, video built), "regenerate the flashcards,
two of them are wrong" (flashcards isn't matched as an existing build, so a new lesson), "can you not
ask me to guess this time and just walk me through recursion" in the predict workspace (no override
for "not ask me", stays predict-first).

Loader: 3,542 tokens of 4,000. It is now measured against Prax's real C workspace as well as the fixture.
