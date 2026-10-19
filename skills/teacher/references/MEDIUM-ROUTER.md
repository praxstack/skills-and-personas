# Medium router

Pick the medium by the job the idea needs, then the tool by what the host can run. Every visual must explain something. Pretty isn't a job.

## Honor the requested delivery

Explicit requests take priority over a default medium. Live oral or chat practice stays as a live dialogue, one exchange at a time. Do not turn it into flashcards just because it is practice. Cards require a request for a deck/cards; a layered Q&A page requires a request for a reference artifact. Video, still, interactive explorer and course requests retain those forms when the host can produce them.

## Four questions

1. **What's the claim?** Write the sentence the visual proves. No sentence, no visual.
2. **Is the point a structure, a change, or a cause?**
   - Structure (parts, connections, a map): a still.
   - Change the learner should watch: an animation.
   - Cause and effect the learner should discover: an explorable.
   - A story arc to rewatch later: a narrated video.
3. **What would the learner do with it?** Look once, look closely, drive it, or rewatch it. Driving needs interaction; rewatching needs a video.
4. **What's the cheapest medium that carries it?** Text, then a sketch, then a still, then an animation, then an explorable, then a video. Step up only when the cheaper one loses something that matters.

## Job to medium

| Job (`find_tool.py --job`) | First choice | Step up to |
| --- | --- | --- |
| structure | explained still (D2, Mermaid, hand SVG) | explorable that reveals parts in steps |
| process | step-through diagram with a numbered walk | concept animation, or an explorable that runs it |
| change | concept animation | explorable where the learner drives the change |
| cause | explorable with one slider per cause | explorable plus film |
| quantity | honest chart (Vega-Lite, Plot, D3) | interactive chart with a "what if" control |
| space | hand SVG with a clear viewpoint | Three.js scene, orbitable |
| math | worked equation beside a picture | Manim transformation, explorable with the formula live |
| code | code panel with the line that matters marked | explorable whose figure is driven by the real code, or a Motion Canvas walk |
| story | a short captioned animation | narrated explainer video |
| map | concept map, prerequisites left to right | roadmap with depth per node |
| timeline | annotated timeline still | scrubbable timeline animation |
| sound | a waveform or notation still | audio examples with the picture synced |
| real | a real photo with labels (record its licence) | short footage |

## Every visual carries four things

- **Claim**: the sentence it proves, as its title or caption.
- **Why**: the reason it's true.
- **How**: the mechanism, step by step, tied to marks on the picture.
- **Look for**: where the eye should go first ("the yellow patch stretches as the noon sun drops").

And an honest text alternative that says what the figure shows right now, with its numbers.

## Don't make a visual when

- the idea is a definition or a single fact
- the learner asked for a quick answer
- the picture would only restate the words
- you can't get the numbers right (say so instead and describe it)

## When the requested medium isn't possible here

Try the suitable tools (`find_tool.py`), then deliver the best honest substitute (a still in place of an animation, a scrubbable HTML player in place of an MP4) and say what's missing and why. If the learner said that medium was essential, stop and ask before substituting.
