# Colab Notebook / Explainer Pipeline

## When to load this file

Load when the transcript source is a Jupyter / Colab notebook walkthrough (code + narration) or when the output target is a hands-on explainer notebook the learner can execute.

## Purpose

Notebook content has a different shape from lecture content: interleaved code, output, and narration. The notebook pipeline preserves executable structure while adding transcript-pipeline-style synthesis and enhancement.

## Input variants

1. **Notebook + voiceover transcript** — the instructor walked through a notebook and the transcript captures both what was said and what was run
2. **Notebook only** — the instructor ran the notebook; any narration is embedded in markdown cells or inferred from the code
3. **Narration only, no notebook** — the instructor described a notebook but didn't share the `.ipynb`; synthesize a notebook from the transcript

## Output contract

An executable `.ipynb` (or equivalent markdown with code fences) that:
- Preserves every code cell the instructor ran, in order
- Preserves every output the instructor showed (or marks `[output: described, not captured]`)
- Adds markdown cells with narration extracted from transcript
- Adds explanatory markdown cells for concepts the transcript glossed
- Includes a setup cell (imports, data loading) runnable from a clean environment
- Is idempotent when re-run

## Cell-level processing

For each code cell:

- **Preserve verbatim.** Code is canonical.
- **Annotate with narration.** If the transcript has a paragraph of explanation for this cell, add it as a markdown cell immediately before the code cell.
- **Add output comments** when the output is numerical or textual and short — inline as a comment after the code.
- **Flag missing outputs** when the instructor showed a plot or table that wasn't captured — add a markdown note `> **Output described in transcript:** ...`.

For each transcript paragraph:

- **Match to a code cell** if it's explaining that cell specifically.
- **Promote to a markdown cell** if it's conceptual, between code.
- **Extract definitions** into a glossary cell at the top.
- **Extract "remember this"** emphases into callout cells.

## Enhancement for learners

Beyond preservation, add:

- **Setup cell** — all imports, data download/load, random seed. Runnable from scratch.
- **Sanity-check cell** — verify setup succeeded (data shape, library versions).
- **Exercise cells** — ~3-5 cells at the end with "try this" prompts and hidden solutions.
- **Cross-refs** — markdown links to related notebooks or documentation.
- **Resource requirements** — GPU / memory / time estimates at the top.

## Technical accuracy checks

- Every code cell parses in the stated language.
- Every import resolves against the installed environment.
- Runs top-to-bottom on a clean kernel.
- No `!pip install` without explicit call-out in the setup cell.
- No hardcoded file paths the learner can't replicate.
- Random seeds set for reproducibility where relevant.

## Narration → markdown cell patterns

| Transcript shape | Markdown cell shape |
|---|---|
| "First we're going to load the data..." | `## Loading the data\n\nWe start by reading the CSV into a DataFrame...` |
| "Here's the key insight:" | `> **Key insight:** ...` |
| "A common mistake is..." | `> **Common pitfall:** ...` |
| "Why this works:" | `### Why this works\n\n...` |
| "Let's look at the result:" | (drop; output cell shows the result) |

## Executable vs explainer modes

**Executable mode:** the notebook runs. Priority = correctness, reproducibility, minimal commentary.

**Explainer mode:** the notebook teaches. Priority = narration depth, gap-filling, exercises.

Choose based on the user's stated goal:
- "I want to run this myself" → executable
- "I want to study this" → explainer
- Both → executable with added explainer cells at end

## Coverage verification

- Every code cell from the source is present in output
- Every transcript paragraph is either a markdown cell or explicitly dropped with reason
- Every output is preserved or marked `[output: described, not captured]`
- Setup cell runs on a clean environment
- Final cell leaves the notebook in a clean state (no open file handles, no hung processes)

## Hand-off

The final notebook goes to the user with:
- The `.ipynb` file
- A short markdown summary of what the notebook covers and how to run it
- Environment requirements (Python version, libraries, GPU if needed)
- Expected runtime
