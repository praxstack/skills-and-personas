---
name: explain-diagram
description: Draw a still figure that proves one claim, how parts connect, how a process flows, or how a subject is mapped out, and frame it with why it works, how it works and a look-for cue. Renders Mermaid, D2, Graphviz, PlantUML, Vega-Lite, BPMN and Excalidraw sources locally by default, with an explicit opt-in Kroki fallback, hand-drawn by default (Mermaid handDrawn, D2 sketch, Kalam labels), or uses hand-written SVG with lesson-notebook ink marks. Use when structure is the idea and nothing needs to move.
---

# Explain diagram

A diagram is an argument. Before drawing, write the one sentence it proves. If you can't, you don't need a diagram yet.

## Pick the form

| The idea is... | Draw | Source |
| --- | --- | --- |
| steps and decisions | flowchart | Mermaid `flowchart` |
| who talks to whom, in order | sequence diagram | Mermaid `sequenceDiagram` or PlantUML |
| parts inside parts | nested boxes | D2 containers |
| a big graph that needs auto layout | network | Graphviz |
| states and transitions | state machine | Mermaid `stateDiagram-v2` |
| how ideas in a subject depend on each other | concept map or roadmap | D2 or Graphviz, left to right by prerequisite |
| numbers to compare | chart | Vega-Lite (`.vl.json`) |
| a precise physical or geometric picture | hand-written SVG | lesson-notebook classes and `ink.js` marks |
| a sketch the learner should edit | Excalidraw | the host's Excalidraw MCP if it has one, or `.excalidraw` via explicitly enabled Kroki |

`python3 ../../scripts/find_tool.py --job structure --medium still --net` says which of these run on this host.

## Render and frame it

```sh
python3 scripts/render.py assets/examples/cache.mmd --page cache.html \
  --claim "A cache answers repeat questions without going back to the origin" \
  --why "The origin is slow and far away. The cache is close and fast." \
  --how "Check the cache first. Only a miss goes to the origin, and its answer is stored." \
  --look-for "only the 'no' branch ever reaches the slow origin" \
  --step "A question comes in." --step "Hit: answer from the cache." --step "Miss: ask, store, reply."
node ../visual-qa/scripts/check_page.mjs cache.html
```

`-o x.svg` writes just the SVG. `--plain` turns off the hand-drawn look. Rendering is local-only by default. `--allow-network` explicitly permits sending the complete diagram source to Kroki when no local renderer is available; `KROKI_URL` selects that service. `--offline` remains as a compatibility spelling for the default. `--page` refuses to run without `--claim`.

## Annotation rules

- Title is the claim, as a sentence, not a topic ("A cache answers repeat questions without the origin", not "Caching").
- Every figure has why, how, and a look-for cue that says where the eye should go first.
- Mark only what the text talks about: circle the bottleneck, arrow the direction of cause, cross out the wrong path. Red for the thing to notice or the mistake, blue for the explanation, graphite for workings.
- Label in the learner's words first. Add the jargon after, next to it.
- Real units and real numbers when they exist (about 1 ms against 120 ms says more than "fast" and "slow").
- Fewer than about 12 boxes. Past that, split it or switch to an explorable that reveals it in steps.
- A walk-through (`--step`) for anything with an order, so it also works read aloud.
