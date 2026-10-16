# The video skills, by the numbers (16:9 data clip)

## Topic
What the repository's video skills share and how fast each drawing kit renders, told as a short data clip whose
every number comes from two CSV files, so a revised measurement changes the bars, the counters and the narration.

## Audience
Someone choosing a kit for their first film.

## Format
general, 16:9 (1920x1080), about 50 s. Chapters: The kits, Speed, Checks. The narration is written in
script.template.json and filled from the data by motion_fill.py.

## Persistent subject
The render-speed bar chart (one bar per kit), which stays for three lines while the fastest and the slowest kit
are lit in turn. Around it: counters (kits, frames, gates, themes, contrast) that count up from the data.

## Style
motion-video "paper" look (light, warm): terracotta accent, Fraunces headlines, Inter body and numbers.
Brand "Claude video skills", tag "By the numbers".

## Facts
- data/render-speed.csv: frames per second per render worker at 1080p on a CPU, from the README's "Pick a
  tool" table (a shared 4-CPU sandbox; ranges are entered at their midpoint and the CSV says so). Motion,
  this kit, is entered under load like the others (~5.5 per worker with two renders sharing 4 CPUs); one worker
  on a quiet machine does 11.7.
- data/facts.csv: 8 gates (vstate.py PHASES), 30 themes (themes.json), 4.5:1 minimum contrast
  (legibility.py), 10,800 frames in a 6-minute film at 30 fps.

## Output
1920x1080 at 30 fps, H.264 + AAC, -16 LUFS. Deliver to explainers/motion/.
