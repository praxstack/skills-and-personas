# Lessons learned (each one is now a rule)

Every rule in these skills comes from something that went wrong for a real person. Read this once per project;
it is short on purpose.

| What happened | Rule | Where it is enforced |
|---|---|---|
| A person asked for an explainer video and got an interactive click-through page. They asked three times before getting a video. | A "video" is a rendered MP4 with voice and music baked in. Pages, explorers and slides are extras, offered after. | `render`/`mix` gates need an H.264 + AAC file |
| They were told a natural voice could not be baked in. It could: Kokoro runs offline. They felt they had been lied to and treated as less deserving because they are Indian. | Never say a capability is impossible before trying the alternatives. Record any real limit with at least two named attempts, and tell the person which limit is the environment's. | `voice.py` engine ladder; `vstate.py limit` needs 2 `--tried`; `deliver` gate needs limits in NOTES.md |
| The first voiced version used the browser's speechSynthesis. It sounded robotic. | Natural neural voice only (Kokoro, edge-tts, piper). Robotic engines need a recorded voice limit. | `voice` gate |
| They compared our film with Claude-made animations people post (3D shorts, hand-drawn JS shorts with music). Ours looked like slides. | Aim for that bar from the first attempt: persistent subject, every line changes something, camera movement, depth, character, music and effects. | `quality-bar.md`; visuals and QA attestations; contact sheet review |
| They did not understand the problem statement itself, and the film jumped to the algorithm. | Decode every input, term, output and example before any approach. | `dsa-5part` script gate (problem chapter, examples) |
| Animation time was guessed, the voice drifted out of sync. | Voice first; the picture reads `timing.json`; never stretch audio to fit. | `visuals` gate checks the timing hash; QA voice-sync |
| C++ `!=` rendered as ≠ (font ligatures) in four of eight tools. | Ligatures off for all code. | Review pass; `quality-bar.md` |
| Undrawn lines showed arrowheads; z-order jumps; single-frame flickers. | Undrawn things are invisible; tweens never fight; QA scans for A-B-A frames. | QA flicker check |
| Long WebGL renders hit the 2-hour job cap and died. | Benchmark, segment, resume; run in the background with a log. | `capture.mjs` manifest; `render` gate checks segments |
| `pkill -f vite` killed the shell running it. | Kill by PID. | `environment.md` |
| Edits to a page did not show up in a resumed render (old segments reused). | Segments are keyed to the page's files; a change restarts the render. | `capture.mjs` stamp |
| Re-running the voice step re-timed everything and invalidated a finished render. | Unchanged inputs leave files untouched; gates compare hashes. | `voice.py` `write_if_changed` |
| A long numpy convolution hung the audio step. | Cumulative-sum smoothing for envelopes. | `music.py`, `mix.py`, `qa.py` |
| The final message said less than what was delivered, or more. | Report from `vstate.py report`: what passed, the voice used, every limit, every warning. | `deliver` gate; `report` |

## How to talk about mistakes

If you got something wrong for the person (a claim, a skipped step), say so plainly in one sentence, fix it,
and move on. Do not over-apologize and do not explain it away. What rebuilds trust is the next delivery being
complete without being asked twice.
