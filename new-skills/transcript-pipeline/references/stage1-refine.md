# Stage 1 — Refine Raw Captions

## When to load this file

Load at the start of Stage 1: when raw auto-generated captions arrive from Zoom, YouTube, Teams, Google Meet, Otter.ai, or similar. Stage 1 output feeds Stage 2 (synthesize).

## Input contract

- Raw caption file: `.txt`, `.vtt`, `.srt`, or pasted text
- May contain timestamps, speaker tags, filler words, false starts, duplicate lines, ASR errors
- May be multi-speaker or single-speaker
- Expected length: 10 minutes to 4 hours of lecture/meeting content

## Output contract

A cleaned, speaker-attributed, paragraph-structured transcript:

```
# [Inferred title or provided title]
# Source: [filename]
# Duration: [if known]

## [Section header if clear topic shift, otherwise continuous]

**[Speaker A]:** <clean paragraph preserving technical content, code, URLs, numbers exactly as stated>

**[Speaker A]:** <next paragraph; keep paragraphs 2-6 sentences>

**[Speaker B]:** ...
```

## Refinement rules

- **Preserve technical content verbatim.** Code snippets, numbers, URLs, library names, jargon — never paraphrase these. If unsure, mark as `[unclear: ...]`.
- **Strip filler.** "um", "uh", "like", "you know", "right?", "so basically" — remove unless the filler carries meaning ("so" as a logical connective stays).
- **Merge false starts.** "We were, we were, we're going to" → "We're going to".
- **Fix obvious ASR errors.** "cash flow" → "cache flow" when context is caching. Only fix when near-certain; preserve uncertainty with `[sic]` or `[unclear: ...]` otherwise.
- **Attribute speakers.** If the source has speaker labels, use them. If not, infer from content shifts or leave as "Speaker 1 / Speaker 2".
- **Normalize casing and punctuation.** Auto-captions are often all-lowercase with no punctuation. Add sentence case + periods / commas / question marks as needed.
- **Paragraph boundaries on topic shift, speaker change, or natural pauses (>3 sec in timestamps).** Target 2-6 sentences per paragraph.
- **Section headers for major topic shifts** when the lecture structure is clear.

## Domain-aware cleanup

Different source domains need different refinement intensity:

| Source | Typical issues | Priority fixes |
|---|---|---|
| Technical lecture (DSA / systems / ML) | ASR errors on jargon, code misreads | Preserve code verbatim, flag `[unclear]` aggressively on terms |
| Business meeting | Overlap, cross-talk, acronyms | Attribute speakers, expand first-use acronyms |
| Podcast | Long monologues, guests talking over hosts | Break into paragraphs, preserve narrative flow |
| Interview | Q&A alternation | Clear Q vs A marking; preserve interviewee nuance |
| Tutorial / screencast | On-screen content not transcribed | Add `[on screen: ...]` where context demands |

## Coverage verification

After refinement, run a coverage check before moving to Stage 2:

- Word count of refined output should be 85-100% of input (lower = aggressive paraphrasing happened)
- Every numeric value from input appears in output (spot check 5-10 numbers)
- Every URL from input appears in output
- Every code block is preserved or explicitly marked `[code on screen: ...]`

If coverage fails, redo Stage 1 with less aggressive filler-stripping.

## Hand-off to Stage 2

Stage 2 expects:
- Clean paragraph-structured markdown
- Speaker-attributed if applicable
- All technical content preserved
- An inferred or provided section structure

Output goes to `stage1-refined.md` in the working directory.
