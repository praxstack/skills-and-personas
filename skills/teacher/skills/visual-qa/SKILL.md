---
name: visual-qa
description: Check every teaching page and video before a learner sees it. Pages run in real Chromium at desktop and phone sizes, light and dark, with and without reduced motion, failing on console errors, sideways scroll, low contrast, tiny text, figure text drawn under 11px, small tap targets and missing text alternatives, with screenshots to look at. Videos are checked with ffprobe and ffmpeg for size, frame rate, black or frozen stretches, captions, loudness and peaks, plus a contact sheet. Use after building any explorable, diagram, animation or video.
---

# Visual QA

A visual that's broken on a phone, unreadable in the dark or silent about what it shows teaches nothing. Run these before showing anything, then look at the pictures yourself.

## Pages

```sh
node scripts/check_page.mjs lesson.html --out shots/                         # 6 runs, screenshots in shots/
node scripts/check_page.mjs lesson.html --board chalk                        # the chalkboard variant
node scripts/check_page.mjs lesson.html --eval "window.__explorable.check()" # the lesson's model checks too
node scripts/check_page.mjs https://example.com/page --json
```

Runs desktop (1280x860) and phone (390x844), light and dark colour schemes, and reduced motion. It waits for the pen to finish before measuring. Fails on:

- page or console errors
- sideways scroll
- text contrast under 4.5:1 (3:1 for large text), computed on the real composited background
- text under 12px, and figure text drawn under 11px after viewBox scaling
- buttons, links and inputs under 24x24 or without an accessible name
- images without alt, figures without a title or label, video without captions

Needs Playwright (`npm i playwright`; `PLAYWRIGHT_MODULE` points at an existing install, `CHROMIUM_PATH` at an existing browser).

## Videos

```sh
python3 scripts/check_video.py clip.mp4 --sheet sheet.png [--min-height 720] [--lufs -16]
```

Fails on missing video, odd dimensions, under 720p, under 24 fps, non-yuv420p pixels, black stretches over 1.5 s, frozen stretches over 4 s, no captions (sidecar .vtt/.srt or a subtitle stream), loudness more than 2 LU off target, or a true peak above -1 dBTP. The contact sheet tiles 12 frames from across the clip into one image.

For narrated clips, also check the words:

```sh
python3 scripts/check_speech.py clip.mp4 [--vtt clip.vtt] [--model base.en] [--min-recall 0.85]
```

Whisper (`pip install faster-whisper`) listens to the clip and checks, cue by cue, that the caption's words are heard near that time. Fails under 85% overall or when any cue drops below half: a voice that skips, slurs, mangles a symbol or drifts out of sync.

## Then look

Automated checks catch the measurable problems. They don't catch a label sitting on a line, a figure that says the wrong thing, or a cut-off note. Open the desktop and phone screenshots and the contact sheet and ask:

1. Does the figure show the claim the text makes?
2. Can every label be read without zooming, and does none sit on a line or another label?
3. Is the first thing the eye lands on the thing the lesson is about?
4. On the phone, is the figure still the hero, or has it shrunk to a stamp?

Fix, rebuild, re-run. Report what was checked and what was fixed. Never claim a visual is fine without having looked at it.
