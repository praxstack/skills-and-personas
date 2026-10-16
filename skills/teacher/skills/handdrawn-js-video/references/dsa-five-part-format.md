# The five-part DSA explainer format

This is the format Prax asked for (2026-10-06, Cheapest Flights Within K Stops) and the default for any
"explain this problem / make a video for this LeetCode question" request. `vstate.py init --format dsa-5part`
turns its structure into gate checks, so a script that skips a part cannot advance.

## Contents
- Why this order
- The five parts (plus intro)
- Visualization rules per part
- Checklist the script gate enforces
- Worked example

## Why this order

The viewer is an experienced engineer whose recall is rusty. The failure they described is not "I don't know
Bellman-Ford" but "I don't understand what the problem is asking": what each input means, what the output is,
why each example's answer is what it is. Explaining an algorithm to someone who has not decoded the problem is
wasted. So the film decodes first, shows the obvious-but-slow idea second, then *asks* the questions that lead
to the real idea, so the viewer builds the intuition instead of being handed it. Complexity and code come last,
once the reasoning makes them feel inevitable.

## The five parts (plus intro)

| Ch | Name (must contain) | Length | Job |
|---|---|---|---|
| 0 | Intro | 5 to 10 s | Title, problem number, one sentence on the road map. No algorithm names. |
| 1 | The **problem** | 25 to 35% | Decode every input field (name, type, what one entry means), define every term ("stop"), state the output and the "impossible" value. Then walk **every** example: show the input on the persistent subject, trace the answer, say why it is the answer and why the tempting alternative is not. Vary one parameter to show the answer moves. |
| 2 | **Brute** force | 10 to 15% | The obvious approach, drawn (a recursion tree, a nested loop sweep). Its time and space in O(...). The specific waste that the next part fixes (repeated states, re-scanning). |
| 3 | **Intuition** | 20 to 25% | Three or four questions, each a separate line with `think` 2 to 3 s and a visible countdown; the answer is the next line, drawn. Each question removes one obstacle between brute force and the final idea. |
| 4 | Every **approach** | 15 to 20% | A ladder: every reasonable approach (brute force, memo, BFS, Dijkstra variant, DP / Bellman-Ford...) with time and space, and one sentence of which intuition question moves you up a rung. Mark the interview pick. |
| 5 | C++ **code** and **dry** run | 20 to 25% | Final C++ (compiled and run during the brief), revealed in chunks synced to the lines that explain them, current line highlighted. Then a dry run on example 1 with the state table updating cell by cell. End on a one-line recap of the key insight and complexity. |

Total 4 to 8 minutes for a medium problem (`init` sets min 2, max 8; a warning, not a block, outside it).
When the person asks for a length, set it in the state so the checks follow it:
`vstate.py set min_minutes=3 max_minutes=4`.
When the person asks for "short", keep all five parts and shorten each; never drop the problem decoding.

## Visualization rules per part

- **One persistent subject** carries the whole film: the graph, the array, the grid. It is introduced in chapter
  1 and every later chapter acts on it (brute force paths light up on it, the DP row sits under it, the dry run
  writes onto it). Cutting to a new unrelated diagram each chapter is what makes a film feel like slides.
- Decoding inputs: put the raw input text on screen (`flights = [[0,1,100],...]`) and animate each entry
  flying into its place on the subject. The viewer must see the mapping from text to picture.
- Examples: the route travels along the edges (a moving token, a drawing stroke), running totals tick up, the
  illegal route is shown and then visibly rejected (struck, shaken, greyed), not just mentioned.
- Questions: the question card stays up during the think pause with a ring or bar counting down; the subject
  stays visible behind it so the viewer can reason on it.
- Complexity: write O(...) on screen when it is said; in the ladder, bars or rungs whose size reflects cost.
- Code: monospace, ligatures off (`!=` must not become ≠), syntax colours from the palette, the active line
  highlighted while its explanation plays, and the variables it touches pulsing on the subject.
- Dry run: a table (rounds as rows, nodes as columns) that fills in one cell per beat, with the cell's cause
  (the edge that fired) highlighted on the subject at the same moment.

## Checklist the script gate enforces (`format: dsa-5part`)

- Chapters, in order, whose names contain: problem, brute, intuition, approach, code (or c++ / dry). An intro
  chapter before them is allowed.
- At least 4 lines in the problem chapter.
- At least 2 lines in the intuition chapter with `think` >= 2.0.
- At least 3 captions containing `O(` across brute force and approaches.
- A dry run mentioned in the code chapter.
- The brief's Facts section records that the solution was compiled and run, with the outputs.

Things the gate cannot check, which you check at the visuals and QA attestations: every example of the problem
statement is walked; the tempting wrong answer is shown and rejected; each intuition answer is drawn, not only
spoken; the code on screen is exactly the code that was compiled.

## Worked example

`assets/examples/lc787/` is the full Cheapest Flights Within K Stops film (40 lines, about 6 minutes); `assets/examples/mini/`
is the same structure cut to 14 lines (about 71 s) for smoke tests. Copy their shape, not their words.
