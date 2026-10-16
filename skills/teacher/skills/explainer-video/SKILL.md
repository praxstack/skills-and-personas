---
name: explainer-video
description: Make a finished, narrated explainer video (an MP4 with a natural voice, music and animation timed to the voice), for example a LeetCode or DSA problem walkthrough, a concept explainer or an anim video. Use this whenever someone asks for a video, an animated explainer, a 3Blue1Brown-style animation, or a film made with Manim, Motion Canvas, Remotion, Revideo, HyperFrames, GSAP, Three.js, Theatre.js or hand-drawn canvas, or a short Claude Motion-style clip (a Short, Reel or data clip), even if they only say "make a video of this problem". It picks the right tool skill, enforces the rules that stop the usual failures (an interactive page instead of a video, a robotic or missing voice, slide-like visuals), and runs the resumable eight-phase pipeline.
---

# Explainer video (start here)

This skill routes a video request to one of ten tool skills and holds the rules they all share. Each tool skill
runs the same eight-phase state machine (brief, script, voice, visuals, render, mix, QA, deliver) with gates that
refuse to deliver anything unchecked. `$SKILL` is this skill's folder.

## Non-negotiables (and why)

1. **Deliver an MP4 with the voice baked in.** Not an interactive page, not slides, not a silent render. A person
   once asked three times for a video and kept getting click-through pages.
2. **Natural voice, always tried first.** Kokoro-82M runs offline on any CPU (`python3 -m pip install kokoro-onnx
   soundfile`, model files from github.com/thewh1teagle/kokoro-onnx releases, `model-files-v1.0`). Then edge-tts,
   then Piper. Never call a voice, or anything else, impossible before trying the alternatives and naming them.
   A person was once told TTS was impossible when it was not and read it as being treated as less deserving
   because of where they are from. When a limit really comes from the environment, say so plainly, in one sentence.
3. **Voice first, picture follows.** Synthesize every line, lay out the timeline from the real clip lengths, and
   key every animation to those times.
4. **Hit the bar on the first attempt.** The bar is the Claude-made animations people share publicly: one
   persistent subject, every line changes something on screen, eased motion and camera moves, depth and light,
   music ducked under the voice, sound effects on events. `references/quality-bar.md` has the details.
5. **Look before you deliver.** Render stills, open them, fix what is wrong, and write down what you saw.
6. **Coding problems use the five-part format** (`references/dsa-five-part-format.md`): decode the problem and
   every example, brute force, intuition through timed questions, every approach with time and space, final
   C++ with a dry run. Compile and run the code first.

## Pick the tool

If the person named a tool, use it. Otherwise pick by the look they want and say which default you chose:

| Want | Skill |
|---|---|
| Classic math / 3b1b look, "anim video" | `manim-video` |
| Hand-drawn, paper-cut or chalkboard short; fastest render | `handdrawn-js-video` |
| Polished motion graphics in React | `remotion-video` |
| Vector motion and code animation in TypeScript generators | `motion-canvas-video` or `revideo-video` (headless render API, faster here) |
| HTML compositions with a CLI renderer | `hyperframes-video` |
| One HTML page of DOM/SVG motion design | `gsap-video` |
| Short clip like Claude Motion: a Short or Reel (9:16), a data clip from a CSV, block-built shots you can edit | `motion-video` |
| 3D diorama film | `threejs-video` (slow on CPU; fine on a GPU laptop) |
| Keyframed 2.5D motion design you can tweak in a studio | `theatrejs-video` |

No preference and a coding problem: `handdrawn-js-video` (character, speed) or `manim-video` (classic look).

**Looks.** A named palette ("Catppuccin Mocha", "Tokyo Night", "a light Nord one", "pastel") is one of 30 registry
themes that every kit can wear: keep the tool choice above, write the theme id into the brief's Style section and
record it with `vstate.py set theme=<id>` (`references/themes.md` lists the ids and how a kit applies one). A
drawing style (whiteboard, chalkboard, blueprint, paper-craft or risograph, watercolor) means `handdrawn-js-video`,
whose styles combine with any theme. No look named: keep the kit's own palette (`original`).

## Find the pipeline

The tool skills carry the scripts (state machine, voice, music, mix, QA, capture). Use the first that exists:

1. An installed skill: `~/.claude/skills/<tool>-video/` (or the project's `.claude/skills/`).
2. This repository's copy: `$SKILL/../<tool>-video/` when this skill was installed with its siblings.
3. A copy in the current project or a shared folder (search for `<tool>-video/SKILL.md`).
4. The repository: `npx skills add praxstack/claude-video-skills-for-people-who-feel-neglected-by-claude --skill <tool>-video`,
   or `git clone https://github.com/praxstack/claude-video-skills-for-people-who-feel-neglected-by-claude` then
   `./install.sh <tool>-video`.

Then read that skill's SKILL.md and follow it from `vstate.py status`.

## If none of the pipeline is reachable

Do not downgrade the deliverable. Build the same thing by hand, in this order:

1. Write the script as lines with a shown caption and a spoken text (symbols spelled out in the spoken text).
2. Voice each line with Kokoro (`Kokoro(onnx, voices).create(text, voice="af_heart", speed=1.0, lang="en-us")`),
   trim silence, and compute each line's start as the running sum of lead (0.25 s) + clip + pad (0.35 s) +
   think pause.
3. Animate against those start times in any tool, render frames to H.264 at the exact total length.
4. Mix: voice on top, a quiet music bed ducked under it, `loudnorm=I=-16:TP=-1.5:LRA=11`, AAC, `-pix_fmt yuv420p`.
5. Check: ffprobe the result, extract a frame per chapter and look at each, listen-check by comparing a few line
   start times against the plan (`ffmpeg -ss <t> -t 3` on the audio).

## Reference files

`references/quality-bar.md`, `dsa-five-part-format.md`, `script-format.md`, `voice-and-audio.md`,
`state-machine.md`, `themes.md`, `environment.md`, `lessons-learned.md`.
