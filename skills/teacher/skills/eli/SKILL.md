---
name: eli
description: Explain any topic in a detailed, interactive, visual HTML explainer for a mature reader making a decision. Use when the user asks for an "eli" page, a decision-grade visual breakdown, or to regenerate an explainer with more depth. Extends /eli5 with evidence labels, tradeoffs, risks, costs, install commands, and interactive filtering and selection. Offline-safe, no CDN, no API keys, no telemetry.
---

# eli

Version: 1.2.0 (locally maintained edition).

Explain logically and interactively. Produce a self-contained HTML page that
helps a mature reader decide, not just understand. `/eli5` stays the
dead-simple picture mode. This skill adds depth, evidence, and control.

## Sources this skill builds on

Delegate by skill name. Do not restate their rules here.

- Prose quality: load `/unslop`. It must always apply to the page copy and to
  this skill's own text. It isn't bundled here. If it isn't installed, say so
  once and run the plain-language self-check below instead.
- Visualization and evidence discipline: load `/teach-pro-max`. Take its
  honest-claims boundary. Report what was observed. Name remaining
  uncertainty. Never infer mastery from completion.
- Claim sourcing: load `/deep-research`. Every claim gets a source or an
  explicit label. Separate fact from inference. Flag single-source claims as
  unverified.

## Artifact contract

One self-contained HTML file. No build step, no network requests at view
time, no CDN fonts or scripts, no analytics. System font stacks only. The
file must render correctly from `file://`.

### Interactivity ladder

Native HTML first. JavaScript only enhances.

1. `<details>`/`<summary>` carries per-item depth. It works with JS off.
   That is the static fallback and it is required, not optional.
2. Enhanced controls behind small vanilla JS: search filter, category
   chips, per-item selection checkboxes, a sticky selection bar that
   renders the exact install commands, and a copy button.
3. No persistence by default. Selection lives in page state and dies with
   the reload. Durable state requires the user's explicit consent and a
   stated storage location.

### Content contract

Every item on the page carries the decision fields. An item missing a
field is incomplete, not minimalist.

- What it is. One concrete sentence, mechanism named.
- Why you care. Tied to the reader's actual stack, not generic benefits.
- Tradeoffs and risks. Including overlap with things the reader already
  runs, maintenance staleness, trust level, and cost drivers.
- Verdict tier. Install now, consider, or skip. With a one-line reason.
- Install command. Exact and runnable, or the reason none exists.
- Evidence badge on every factual claim: verified (checked this session,
  with the method), unverified (single source or vendor-claimed), or
  unavailable (say so plainly).

### Modes

Pick the lightest mode that serves the decision.

| Mode | Deliverable |
|---|---|
| `quick` | One screen, hero claim, three supporting cards |
| `matrix` | Full item set, filters, tiers, selection bar. The default for "help me choose" |
| `compare` | Two to four items head to head on the decision fields |

## Process

1. Gather facts with real lookups (registry, docs, logs, files). Never
   fill decision fields from memory.
2. Write the page. Apply unslop to every sentence. Short declarative
   sentences, active voice, sentence case headings, straight quotes, no
   em dashes, no mid-sentence colons. Without unslop, reread every sentence
   against this self-check before delivering: Is it plain words a newcomer
   knows, or is each term defined where it first appears? Does it say one
   thing, with a concrete subject and verb? Can a filler word, hedge or
   stacked adjective go? Is any claim vaguer than the facts gathered in
   step 1? Fix each sentence that fails.
3. Validate. Open the file. Check that details expand with JS disabled,
   filters work with JS on, commands copy cleanly, and no field is empty.
4. Deliver. State the file path, what is interactive, and what remains
   uncertain. Do not create extra files beyond the one artifact.

## Closing

Report the artifact path, the decision tiers chosen and why, and the
top uncertainty a skeptic would probe next. Keep it under ten lines.
