# The quality bar

The bar is the Claude-made animations people post publicly: the JS-drawn-every-frame shorts, the Python +
Blender 3D render with composed music, and "A Day in the Life of Claude" (a stylised 3D short: one orange
character, warm-to-neon lighting through a day, comic onomatopoeia, a time-stamped lower third per scene,
continuous camera moves, a score under everything). A person compared an earlier explainer of ours to those and
found it far below them. Aim for that bar on the first attempt, because a second attempt costs the person a day
and their trust.

## Contents
- What separates a film from slides
- Style recipes that hit the bar
- Typography and layout
- Motion
- Sound
- Anti-patterns seen in our own renders (and the fix)
- The review pass (what to look at before attesting)

## What separates a film from slides

1. **A persistent subject.** One world (a graph, a city of nodes, a desk, a character) exists across the film
   and is acted upon. Viewers track change; they cannot track replacement.
2. **Every beat changes something.** Each narration line has a visible consequence: a token moves, a number
   ticks, an edge lights, a cell fills. If a line plays over a static frame, either animate something it
   refers to or merge it into a neighbour.
3. **Continuous camera.** Push in on the part being discussed, pull back to show the whole, drift slightly
   during holds (2D tools: scale/translate the stage; 3D: dolly and orbit). Hard cuts only at chapter changes.
4. **Depth and light.** Even in 2D: a soft vignette, a background with texture or gradient, shadows under
   cards, a glow on the active element. Flat white boxes on flat black is the slide look.
5. **Character and texture.** Hand-drawn wobble, paper grain, comic bursts ("POP!", "700!"), a mascot token
   that travels the route. Pick one personality and keep it.
6. **Sound design.** Narration on top, a quiet score underneath that ducks under the voice, small effects on
   events (pop on a node appearing, whoosh on chapter change, tick on a counter, chime on the answer).
7. **Chapter cards and lower thirds.** Each chapter opens with a title card or a lower third in the style
   ("01 · THE PROBLEM", like the reference film's "7:00 AM RISE AND SHINE").
   A card never sits over content: fade the subject, its labels and the caption fully out (0.25-0.3 s)
   after the chapter's last word, then bring the card in; the card leaves before the next chapter's
   content fades back in. Check it with 5 fps frames around every chapter change, not one still.

## Style recipes that hit the bar

Pick one in the brief's Style section and give its tokens (colours, fonts, texture). Mixing them reads as noise.

| Style | Look | Good tools |
|---|---|---|
| Dark editorial | Near-black blue background with grain, one warm accent (amber) and one cool (cyan), Inter Display headlines, JetBrains Mono code, soft glow on the active path | Remotion, Motion Canvas, Revideo, GSAP, HyperFrames, Manim |
| Paper cut | Warm paper texture, cut-out shapes with drop shadows, hand lettering (Caveat Brush, Patrick Hand), slight per-frame wobble | Hand-drawn canvas |
| Blueprint / chalk | Deep blue or slate board, chalk strokes drawn on, handwritten labels | Hand-drawn canvas, Manim |
| Toy diorama 3D | Rounded blocks on a table, warm key light + cool rim light, shallow depth of field feel, comic bursts in screen space | Three.js + Theatre.js |
| 3b1b classic | Black, pastel blues/yellows, LaTeX-free Text, smooth transforms between states | Manim |

## Typography and layout

- 1920x1080 safe area: keep text 96 px from every edge. Captions sit in the bottom 180 px band and never cover
  the subject.
- Sizes at 1080p: headline 72 to 96 px, body 40 to 48 px, captions 38 to 44 px, code 30 to 36 px. Nothing under
  26 px.
- Monospace code with ligatures off. Digits that are easy to read: check every display font's digits at caption
  size (Space Grotesk's 1 looks like a flag; Bangers' 7 reads as 1, so a "700!" burst read "100!"; hand fonts
  like Patrick Hand have a hooked 7). Put numbers that matter in Inter or JetBrains Mono.
- Never let two text blocks overlap, and never let text run off-frame. Long captions wrap to two lines max
  (captions.py splits at 84 characters).
- Contrast at least 4.5:1 for text against its background.
- `scripts/legibility.py --project .` measures every text the OCR finds in the review stills, single digits and
  letters included (size from the glyphs, WCAG contrast from the pixels), and the visuals gate fails until none is
  under 26 px or under 4.5:1. The gate applies 4.5:1 to every text at every size, with no tolerance; it is not the
  WCAG 3:1 large-text exception. Dimmed context (code lines that are not active, past steps) still needs 4.5:1;
  show focus with colour, weight or a highlight bar.

## Motion

- Ease everything (cubic or expo in-out, springs for pops). Linear movement only for constant-speed travel.
- Enter 0.3 to 0.6 s, exit faster than enter. Stagger lists by 60 to 120 ms.
- Hold a result on screen for at least 1 s after it lands before the next change.
- Motion has a source and a destination: when a value moves from the input text to the graph, animate it
  travelling, do not fade one out and the other in.
- No element should pop in at full opacity in a single frame unless the pop is the effect (and then add a scale
  overshoot and a sound).
- Text may pass under 26 px or 4.5:1 only while it moves (a fade, a sweep, a scale-in). `qa.py` samples the
  finished film on a 4 fps grid at any length (it reads every other frame, then the frames next to any failing
  text, which costs about a second per frame read), follows each text that fails the legibility bar from frame to
  frame, and fails the film when one stays under the bar for 0.5 s or more (`qa/moving-text.json` lists each
  run with its time, box and worst size and contrast). Stills only cover the moments you chose; this covers
  the rest, including chapter cards and labels at rest on a gradient.
- The subject is on screen when a chapter's voice starts. Chapter cards play in the chapter's first second
  (`chapter_lead`, script-format.md); bring the subject back as the card leaves, not on the voice. `qa.py`
  warns ("chapter-entry") when the content area at a chapter's first word has under 60% of the detail it has
  one second later.

## Sound

- Natural voice (references/voice-and-audio.md). Robotic voice fails the bar even if the picture is perfect.
- Music around -17 dB under the voice, ducked to about 60% while the voice speaks, thinner during think pauses
  so the pause feels like space to think, swells at chapter starts. `music.py --mood calm|piano|pulse`.
- Integrated loudness -16 LUFS, true peak around -1.5 dBTP and never above -0.5 (mix.py aims for this; qa.py checks it).

## Anti-patterns seen in our own renders (and the fix)

| Seen in | Problem | Fix |
|---|---|---|
| Remotion, Three.js, hand-drawn, Motion Canvas | C++ `!=`, `<=`, `++` rendered as ≠ ≤ ligatures in JetBrains Mono | Turn off `calt`/`liga` (CSS `font-feature-settings`, Motion Canvas `letterSpacing={0.01}`, canvas: draw glyph by glyph) |
| Motion Canvas | Arrowheads and round caps visible on lines that had not been drawn yet (`end={0}`) | Keep undrawn lines at opacity 0 until they start drawing |
| Manim | Elements re-added on top inside AnimationGroup (z-order jumps) | Unpack plain animations into `self.play(...)` |
| First LC 787 attempt | An interactive click-through page instead of a video | Always a rendered MP4 with voice baked in; pages are extras |
| First LC 787 attempt | Browser speechSynthesis voice | Kokoro in the file (references/voice-and-audio.md) |
| Several | Frames where the subject jumps for one frame (A-B-A flicker from a state reset or a mis-keyed tween) | `qa.py` flags it; key tweens with `immediateRender: false`, never set state from outside the timeline |
| Several | Long static holds while the voice talks about something not on screen | One visible change per line |
| Several | Empty frames between scenes (black gaps from scene boundaries) | Cross-fade or carry the subject across; `qa.py` black check |
| Hand-drawn | Visible seams in paper texture tiles | Draw tile strokes wrapped (at ±tile size) |
| Revideo, Theatre.js, hand-drawn | Film grain re-randomized every frame made files 4 to 7x larger (13 to 66 Mbit/s) and slowed encoding, with no visible gain | Keep grain static, or change it every 3 to 4 frames; hold backdrops still between camera moves |
| Remotion, Theatre.js | A "700!" burst in Bangers read "100!" | Check display-font digits; numbers in Inter or JetBrains Mono |
| GSAP (LC 739 test) | Bangers has capitals only, so an "O(n)!" burst read "O(N)!" | Keep case-sensitive text (variable names, O(n)) out of all-caps display fonts |

## The review pass (what to look at before attesting)

The visuals and QA attestations are a promise that a person looked. Open every still (Read the image, PNG or JPEG) and check:

1. Is the subject on screen and readable? Is anything cut off, overlapping, or under the caption band?
2. Does the frame show what the line at that moment is saying?
3. Are code glyphs correct (no ≠ where `!=` should be)?
4. Would this frame look at home next to the reference film's frames? If it looks like a slide, add depth,
   light, motion or character before moving on.
5. On the contact sheet: is there visible variety (camera moves, colour of the active element, cards) across
   the 36 tiles, or do they all look alike?

Write what you looked at and what you changed in the attestation. "Looks good" is not an attestation.
