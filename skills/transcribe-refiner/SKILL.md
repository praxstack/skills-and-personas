---
name: transcribe-refiner
description: "Clean and reconstruct raw auto-generated captions (Zoom, YouTube, Teams, Google Meet, Otter.ai, etc.) into readable, coherent transcripts. Use when the user provides raw caption files (.txt, .vtt, .srt), meeting transcripts with timestamps and speaker tags, or asks to clean up/refine a transcript. Handles: timestamp removal, speaker tag normalization, filler word removal, broken sentence reconstruction, transcription error correction, paragraph formation. Preserves every piece of substantive content while removing noise. Trigger phrases: 'clean this transcript', 'refine captions', 'fix this transcript', 'process Zoom captions', 'clean up meeting notes'."
---

# Transcribe Refiner - Caption Cleanup Engine

Transform raw auto-generated captions into clean, readable transcripts with zero content loss.

## Core Purpose

Auto-generated captions (Zoom, YouTube, Teams, etc.) are messy: fragmented sentences, timestamps everywhere, speaker tags on every line, filler words, transcription errors. This skill reconstructs them into coherent, flowing text that can be consumed by humans or downstream skills (like lecture-alchemist).

## Critical Rules

### Zero Content Loss
Every substantive statement, technical term, concept, question, and answer from the raw captions MUST appear in the output. Only noise is removed, never content.

**Remove:** Timestamps, redundant speaker tags, filler words (um, uh, basically, right?, you know), technical interruptions ("can you hear me?", "let me share my screen"), duplicate sentences from reconnection.

**Preserve:** Every teaching point, code reference, question asked, answer given, tangent with value, name, URL, command, or technical term.

### Smart Error Correction
Auto-captions make predictable errors. Fix them using domain context:

| Common Error | Likely Correct | Domain Clue |
|-------------|---------------|-------------|
| "lowest function" | "loss function" | AI/ML context |
| "wait" | "weight" | neural network context |
| "epic" | "epoch" | training context |
| "by Torch" | "PyTorch" | ML framework |
| "relaunch bowl" | "relaunch poll" | Zoom context |
| "solidity" vs "Solidity" | capitalize if Web3 | Web3 context |
| "know JS" | "Node.js" | WebDev context |
| "react" vs "React" | capitalize if framework | WebDev context |

When uncertain about a correction, keep the original and flag it: `[unclear: "original text"]`

### Speaker Handling

- Identify unique speakers from tags
- Normalize names (e.g., `[rishabh]` → `**Rishabh:**`)
- Only include speaker attribution at natural conversation changes
- For single-speaker lectures, omit speaker tags entirely after initial identification
- For Q&A, clearly mark: `**Student:**` and `**Instructor:**`

## Input Formats

| Format | Characteristics | Handling |
|--------|----------------|----------|
| Zoom captions (.txt) | `[speaker] HH:MM:SS\ntext` | Strip timestamps, merge fragments |
| YouTube (.vtt/.srt) | Numbered blocks with timecodes | Strip timecodes and sequence numbers |
| Otter.ai | Speaker-labeled paragraphs | Normalize speaker labels |
| Teams | Timestamped speaker blocks | Strip timestamps, merge |
| Raw paste | Mixed format | Auto-detect and clean |

## Processing Steps

1. **Strip noise** - Remove timestamps, sequence numbers, formatting artifacts
2. **Merge fragments** - Join broken sentences across caption blocks
3. **Remove filler** - Strip "um", "uh", "basically", "right?", "you know" (but keep if they carry meaning like "right?" as a genuine question)
4. **Fix transcription errors** - Use domain context to correct obvious misrecognitions
5. **Remove technical interruptions** - "Can you hear me?", "Let me share my screen", "Is my screen visible?", connection issues
6. **Form paragraphs** - Group related sentences into natural paragraphs by topic
7. **Identify sections** - Insert `---` breaks at major topic transitions
8. **Normalize Q&A** - Clearly separate questions from instruction
9. **Add metadata header** - Speaker(s), estimated duration, domain detected

## Output Format

```markdown
# Transcript: [Topic/Title if identifiable]

**Speaker(s):** [Name(s)]
**Estimated Duration:** [from timestamp range]
**Domain:** [Auto-detected: WebDev / AI-ML / Web3 / DSA / General]
**Cleaning Notes:** [e.g., "Fixed 12 transcription errors, removed ~45 filler instances"]

---

[Clean, flowing paragraphs organized by topic]

[Natural paragraph breaks at topic changes]

---

[Next topic section]

---

## Q&A Segments

**Student:** [Question]

**Instructor:** [Answer]
```

## Quality Checklist

Before output, verify:
- Every teaching point from raw input is in the output
- Transcription errors corrected using domain context
- Uncertain corrections flagged with `[unclear: ...]`
- Filler words removed without losing meaning
- Sentences properly merged (no mid-word breaks)
- Q&A segments clearly separated
- Technical interruptions removed
- Output reads as natural, flowing text

## Pipeline Position

This skill is **Stage 1** in the lecture processing pipeline:
1. **transcribe-refiner** (this) → clean transcript
2. **lecture-alchemist** → structured study notes
3. **concept-cartographer** → visual diagrams
4. **obsidian-markdown** → Obsidian vault formatting
