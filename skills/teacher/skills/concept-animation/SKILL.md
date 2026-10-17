---
name: concept-animation
description: Make a short, scrubbable, captioned animation of one idea changing, driven by a model so every frame shows real numbers, then export it frame-exact to MP4, GIF and WebVTT captions with Playwright and ffmpeg. Use when the insight is in the change itself (a weight growing, a curve shifting, a process running) and the learner should watch rather than drive. Hand-drawn lesson-notebook look by default. For full narrated videos hand the clip to explainer-video; for learner-driven change use explorable.
---

# Concept animation

An animation earns its place when the change is the point. Watching a sum slide along a sigmoid teaches something that two still frames don't.

## Make one

```sh
python3 scripts/build.py assets/examples/neuron.anim.js -o neuron.html          # scrubbable player, one file
node scripts/export.mjs neuron.html --out neuron.mp4 --gif neuron.gif --poster poster.png
python3 ../visual-qa/scripts/check_video.py neuron.mp4 --sheet sheet.png  # then look at the sheet
```

The export seeks the timeline frame by frame (30 fps by default, 1280x720), so there's no screen recording and no dropped frames. Captions are burned in and also written as `neuron.vtt`. `--no-captions` leaves them out of the picture.

## The animation file

```js
window.ANIMATION = {
  id, title, kicker, subtitle, viewBox: "0 0 960 540",
  params: { w1: 0, b: 0 },
  model: (p) => ({ s: ..., y: ... }),
  keys: [
    { at: 0, say: "Two inputs come in." },
    { at: 3.5, set: { w1: 0.8 }, say: "Each is multiplied by a weight." },
  ],
  duration: 28, transition: 1.2,
  draw(g, s, p, kit) { /* kit.el, kit.mark(paths, { progress }), kit.hand, kit.since(i), kit.key, kit.u */ },
};
```

- Between keys, numeric params ease from one key's values to the next over `transition` seconds.
- `kit.since(i)` is how far key i's change has played (0 to 1). Use it to draw a mark part-way, `kit.mark(paths, { progress: kit.since(3) })`, or to reveal a panel. Everything is a function of time, which is what makes `seek()` and the export exact.
- One caption per key, said in the book's plain voice. A key without `say` keeps the last caption.

## Rules

- One transformation per clip, 10 to 40 seconds. Longer means it wants to be an explorable or a narrated video.
- Hold still long enough to read: at least 2.5 seconds between a caption and the next change.
- Show cause before effect: the thing that changes moves first, then what it changes.
- Label the numbers the learner should track, in the machine voice, from the model.
- Reduced motion: the player steps key to key instead of tweening.
- Check the contact sheet and at least the poster frame by eye before sharing.

## Other engines

When the idea needs something this player can't do, use the bundled video skills, which share the same discipline: `manim-video` for equations and proofs, `motion-canvas-video` for code walkthroughs, `threejs-video` for 3D, `handdrawn-js-video` for whiteboard narration. `explainer-video` routes between them and adds voice, music and QA.
