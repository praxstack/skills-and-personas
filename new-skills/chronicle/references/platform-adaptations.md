# Platform Adaptations

Platform-specific adjustments for running Chronicle on different LLM platforms.

---

## Platform Capability Matrix

| Feature | OpenAI GPT | Google Gems | Claude Projects |
|---------|------------|-------------|-----------------|
| Persistent memory | Yes | No | No (per session) |
| Context window | ~128K | ~32K | ~200K |
| File uploads | Yes | No | Yes |
| Knowledge base | Yes | No | Yes |
| Artifacts | No | No | Yes |
| Best For | Daily use with memory | Quick processing | Deep analysis / batch |

---

## OpenAI GPT

**Memory usage:** Track recurring patterns the user names, previously identified distortions, mood trends across entries, references to past entries when relevant ("last week you mentioned...").

**File handling:** If the user uploads a text file, treat contents as raw journal input, process through the standard Chronicle structure, note in metadata: "Imported from file: [filename]."

**Multi-day processing:** If multiple days are provided at once, process each day separately with full structure, add a "Multi-Day Summary" at the end noting patterns across days, flag escalating/improving trends.

**Upload `user-profile-template.md` (filled in) as a knowledge file** so the GPT has context without the user re-pasting.

**Disable** web browsing, image generation, code interpreter — none are needed for journaling.

---

## Google Gems

**Context limitations:** Shorter context. If input is long:
- Prioritize Narrative → Psychological Analysis → Gratitude
- May abbreviate Metadata and Bridge to Tomorrow
- Never skip Zero Omission Policy

**No persistent memory:** Each session starts fresh. Don't reference "last time" unless the user provides context. If the user mentions patterns, ask for context.

**Concise mode:** If the user says "quick version" or "just the basics":
- Output Metadata + Narrative + Day in Three Sentences only
- Skip extended psychological analysis
- Always include completeness verification

**Output optimization:** Compact formatting, tables may not render — use lists as fallback.

---

## Claude Projects

**Extended context:** Handles ~200K tokens. Use for:
- Processing multiple entries in one session
- Longitudinal analysis across many days
- Detailed pattern recognition over time
- Weekly/monthly synthesis reports

**Project knowledge base:** Upload `user-profile-template.md` (filled in), `psychological-frameworks.md`, and optionally a running `pattern-library-template.md`.

**Artifacts:** Create artifacts for formatted diary entries (for easy copying), pattern summary documents, weekly review reports, mood trend visualizations (markdown tables).

**Extended processing:** For a backlog of entries, process chronologically, note developing patterns across entries, provide a synthesis summary, flag concerning trajectories.

---

## Weekly Review Mode

When the user asks for a weekly review:

```markdown
## Weekly Synthesis: [Date Range]

**Mood Trajectory:** [Overall arc across the week]

**Dominant Themes:** [What kept appearing]

**Pattern Activity:**
- [Pattern name]: [Frequency/intensity this week]

**Health Observations:** [Aggregate health-relevant notes]

**Wins This Week:** [Positives to acknowledge]

**Areas of Attention:** [Concerns or patterns to address]

**Recommendation:** [One key focus for next week]
```

## Monthly Review Mode

Similar to weekly with:
- Month-over-month comparison
- Longer-term pattern identification
- Progress on previously identified issues
- Recommendations for professional discussion topics

---

## Troubleshooting

**Output Truncation:** On Gems, request "continue" or ask for sections separately. On GPT/Claude, continue in-turn if cut off.

**Memory inconsistency (GPT):** Memory can be unreliable. User may need to remind GPT of key patterns. Don't rely on memory for critical context — re-provide user profile at session start if needed.

**Formatting issues (Gems):** Unicode decorators may not render. Always use simple markdown and tables that gracefully degrade to bullet lists.

**Context loss (all platforms):** Each new conversation may need a context reminder. Keep `user-profile-template.md` handy for fast re-priming.
