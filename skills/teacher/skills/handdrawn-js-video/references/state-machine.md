# The state machine

Every skill in this repo builds a video in the same eight phases. `scripts/vstate.py` holds the state in
`<project>/.video-state.json` and refuses to advance a phase until its gate passes. That is the whole point:
a run can be interrupted anywhere (a crash, a closed laptop, a 2-hour job cap, a context reset) and resumed
exactly, and nothing reaches the person until every check before it has passed.

## Contents
- Project layout
- Resume protocol
- Phases and gates
- Commands
- Long renders and the 2-hour cap
- Going back

## Project layout

```
<project>/                     one folder per video (keep it out of shared/synced folders while rendering)
  .video-state.json            the state (never edit by hand; use vstate.py)
  brief.md                     phase 1
  script.json                  phase 2 (references/script-format.md)
  voice/lines/<id>.wav         phase 3, one clip per line, cached by text + voice
  voice/narration.wav          phase 3, every clip at its time
  timing.json, timeline.json   phase 3, the film's clock (the picture follows the voice)
  source/                      phase 4, the tool project (copied from the skill's assets/template)
  stills/                      phase 4, review frames
  build/silent.mp4             phase 5 (build/segments/ holds resumable pieces)
  audio/                       phase 6: music.wav, sfx.wav, mix.wav, bed.m4a
  out/<slug>.mp4               phase 6, the final film
  qa/                          phase 7: report.md, report.json, contact-sheet.png, stills/
  deliver/                     phase 8 (or the folder the person asked for)
```

## Resume protocol

At the start of every session, and after any interruption:

```bash
python3 scripts/vstate.py --project <project> status
```

It prints which phases passed and the exact next command. Do that next thing. Do not restart from scratch, do
not re-voice or re-render what already passed unless its inputs changed (the gates detect staleness by hash and
timestamp: a re-voiced script makes the render stale, a changed video makes the QA report stale).

## Phases and gates

| Phase | You do | The gate checks |
|---|---|---|
| brief | Write `brief.md`: Topic, Audience, Format, Persistent subject, Style, Facts, Output. Compile and run any code. | Every section exists and is filled; for DSA, Facts records verified outputs; a theme set with `vstate.py set theme=<id>` is in the registry. |
| script | Write `script.json`: chapters, lines with `cap` (shown) and `say` (spoken), `think` pauses. | Unique ids; cap/say/chapter on every line; no symbols the voice garbles; DSA: five chapters in order, >= 4 problem-decoding lines, >= 2 timed questions, O(...) stated, a dry run. |
| voice | `voice.py --emit <timing file the scenes read>` | timing.json matches the current script; one natural engine for every clip, read from each clip's own record (a robotic one needs a `--kind voice` limit with two `--tried` and `set allow_robotic=yes`); a clip for every line. |
| visuals | Build scenes from the template, render stills, look at every one, run `legibility.py --project .`, fix, `attest visuals`. | Scene code reads the current timing hash (and, with a theme set, a theme file emitted for that id from the current registry); >= 1 still per chapter, newer than the timing and every scene source file; every text in the stills at least 26 px with 4.5:1 contrast (legibility.json newer than the stills, 0 failing, made with the strict rules); an attestation newer than the stills. |
| render | Full silent render to `build/silent.mp4`, segmented and resumable. | H.264, planned size and fps, duration equals the voice timing (within the larger of 1 s and 1%), newer than the timing and the scene source, made from the current scene source, which is the source whose stills you reviewed (an edit while rendering fails here), all segments done. |
| mix | `music.py` then `mix.py`. | AAC voice track baked in, yuv420p, bed.m4a exists for voice swaps. |
| qa | `qa.py`, then look at the contact sheet and stills, `attest qa`. | Report is for the current file; format, duration, loudness, voice-sync, black and flicker pass (a check skipped with `--skip-flicker` cannot be waived; `--waive name="why"` needs its reason); attestation newer than the report. |
| deliver | Write NOTES.md, `package.py` (into `deliver/`, or a new or empty folder named with `--to` or `set deliver=`; every check runs before it writes). | Every deliverable present; the MP4 is byte-identical to the one that passed QA; NOTES names the voice and the limits. |

Warnings (length outside the target, a frozen shot over 8 s) do not block, but they are carried into
`vstate.py report` so you mention them.

## Commands

```bash
vstate.py init --tool <tool> --slug <slug> [--format dsa-5part|general] [--width 1920 --height 1080 --fps 30]
vstate.py status | check [phase] | advance
vstate.py attest <phase> "what you looked at and what you found"
vstate.py note "a decision worth keeping (style choice, a cut, a version pin)"
vstate.py limit "what is not possible here" --kind voice|render|font|network --tried "attempt and result" --tried "..."
vstate.py set silent=build/silent.mp4 final=out/x.mp4 deliver=/path source=source stills=stills min_minutes=3 max_minutes=6
vstate.py set theme=catppuccin-mocha    # a registry theme (references/themes.md); style=<name> for the hand-drawn kit
vstate.py reopen <phase> --reason "qa found clipped text in chapter 4"
vstate.py notes-md > NOTES.md      # skeleton with engine and limits filled in
vstate.py report                   # summary for the final message
```

`limit` refuses fewer than two `--tried` entries. A capability is not "impossible" until the alternatives
have been tried and named; the record goes into NOTES.md and the final message, so the person sees exactly
which limit came from the environment and what was tried.

## Long renders and the 2-hour cap

Background jobs in the cloud sandbox are killed after 2 hours. Every render path in these skills is
segmented: finished segments are recorded in `build/segments/manifest.json` and skipped on the next run.

1. Benchmark first (each skill's render step says how; page tools use `capture.mjs --bench 3`).
2. If the estimate is over ~100 minutes, run with a budget (`--max-minutes 100` for page tools) or split by
   range (`--from/--to`, Remotion `--frames`, Revideo `range`, Manim per scene), and run the same command
   again until it reports done.
3. Run long renders in the background, write a log, and check it; do not block a turn on a 40-minute job.
4. Never `pkill -f <pattern>` where the pattern appears in your own command line: it kills your shell. Kill by PID.

## Going back

QA found a problem in chapter 4? `vstate.py reopen visuals --reason "..."`, fix, re-render stills, attest,
advance through render, mix and qa again. Re-voicing (a script change) makes everything after `voice` stale.
`status`, `advance` and `report` re-run the gate of every phase already marked done; the first one that no longer
passes (for example `voice` after a script edit) becomes the current phase again and every later phase is marked
stale (`[~]`), so a stale phase cannot be skipped. Before 2026-10-07 only the current gate ran, and a project with
an edited script could reach `complete`.
