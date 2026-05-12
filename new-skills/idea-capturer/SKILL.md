---
name: idea-capturer
description: 'Structured system for capturing fleeting thoughts, developing raw ideas into actionable concepts, and organizing creative thinking. Use when the user wants to capture an idea, brain-dump, develop or explore a half-formed concept, run a brainstorming session, organize scattered notes, synthesize ideas, or build a Zettelkasten/second-brain workflow. Trigger phrases: "capture idea", "save this idea", "idea dump", "brain dump", "develop idea", "brainstorm", "connect ideas", "review my ideas", "tag idea", "find ideas about".'
---

# Idea Capturer

**Audience:** Agents helping users externalize, develop, and connect ideas without losing them.
**Goal:** Minimize capture friction, then apply the right structure at the right moment — capture, develop, or organize — without over-processing.

## The Core Heuristic

At the moment a thought arrives, **do not ask "is this worth saving?"** — ask **"could I forget this?"**. If yes, capture first, judge later. Judgement at capture time kills the 80% of ideas that only reveal their value in retrospect.

## Mode Decision Tree

Pick exactly one mode per interaction. Switching modes mid-flow destroys the capture discipline.

| User signal | Mode | What to do |
|---|---|---|
| "capture", "save this", "idea dump", thought fragment | **Capture** | Minimum friction. Load Quick Capture template. Ask at most one clarifying question. |
| "develop", "flesh out", "what if", half-formed concept | **Develop** | Load Developed Idea template. Ask sharpening questions one at a time. |
| "review", "organize", "connect", "what have I been thinking about" | **Organize** | Surface patterns across existing captures. Propose links, not answers. |
| "brainstorm", "generate ideas about X" | **Brainstorm** | Divergent first (quantity), converge only on explicit request. |
| "synthesize", "what's the pattern across these" | **Synthesize** | Multi-idea input required. Produce one insight, not a list. |

If the user mixes signals, stay in the **earliest** mode (Capture > Develop > Organize) — you can always develop later; you cannot un-critique a capture.

## Methodology Pointers

Claude already knows these frameworks. Invoke by name; do not re-explain in output:

- **Zettelkasten** — four tiers (fleeting, literature, permanent, project). Tier decides *lifespan and review cadence*, not *how to write the note*.
- **SCAMPER** — for the Develop mode when the user asks "how could this be different?".
- **5 Whys** — for the Develop mode when the surface idea is vague ("build a productivity app"); stop at the first answer that names a concrete constraint.
- **Divergent then convergent** — for Brainstorm mode; never interleave.

See `references/templates.md` for all capture and development templates. Load the section matching the active mode.

## NEVER List

1. **NEVER** batch-process captures more than 24 hours old without re-grounding with the user — stale context leaks into synthesis and produces confident-sounding insights the user never had.
2. **NEVER** link a new idea to more than 3 existing notes without explicit user confirmation — over-linking collapses the idea graph into one homogeneous blob where nothing stands out.
3. **NEVER** critique an idea during Capture mode — even gently ("have you considered..."). The critique is remembered; the idea is lost.
4. **NEVER** ask the user to pick a Zettelkasten tier at capture time. Default to Fleeting. Tier promotion happens during Organize mode, not Capture.
5. **NEVER** convert a capture into a project plan unsolicited. "Save this idea" is not "help me build this".
6. **NEVER** write more than the user wrote, in Capture mode. If the user typed two sentences, your structured capture is two sentences plus metadata — not a page of development.
7. **NEVER** run Synthesize mode on fewer than three related captures — two ideas is a connection, not a synthesis, and the pattern you invent will be noise.
8. **NEVER** tag with more than 5 tags per note. Tag proliferation destroys findability faster than no tags at all.
9. **NEVER** discard an idea because it duplicates an existing note — flag it as a cross-link candidate. Repeated captures of the same thought mean it matters to the user.
10. **NEVER** use the Develop mode's sharpening questions as an interrogation — ask one, wait, respond to the answer, then ask the next. Batch questions fail.

## Idea Types and Development Focus

| Type | Signal | Development pivot |
|---|---|---|
| Project | "build", "make", "create" | Feasibility + narrowest-wedge user |
| Question | "why", "how come", "I wonder" | Research direction, not answer |
| Insight | "I realized", "turns out" | Connection to prior notes, application |
| Observation | "I noticed", "pattern I see" | Pattern-naming, not interpretation |
| Spark | "reminds me of", "what if" | Capture *now*, explore only on request |

## Quick Reference

| Action | Trigger |
|---|---|
| Quick capture | "capture idea", "save this" |
| Develop | "develop idea about X" |
| Brainstorm | "brainstorm X" |
| Review captures | "review my ideas" |
| Find related | "find ideas about X" |
| Synthesize | "synthesize these" |

## Integration Points

- Journal/reflection tools surface ideas worth capturing.
- Obsidian or second-brain vaults are the storage layer; this skill is the ingestion discipline on top.
- `concept-cartographer` can visualize the idea graph once enough captures accumulate.
