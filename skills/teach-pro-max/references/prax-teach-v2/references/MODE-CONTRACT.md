# Mode contract

## Purpose

Route each request to the least costly teaching experience that can achieve the learner’s stated outcome. Persistence, rich artifacts, and long intake are capabilities—not default ceremony.

## Decision sequence

1. Honor an explicit `quick`, `lesson`, `course`, `keep it concise`, `go deeper`, or **Answer now** request.
2. Identify the requested outcome: understand, perform, retain, transfer, or build a course.
3. Choose `quick` for explicit brevity or a direct-answer request.
4. Choose `lesson` for unqualified teaching: complete bounded visual explanation, optional practice.
5. Choose `course` only for explicit sequence or resumption intent; persistence still needs consent.
6. Ask one clarifying question only when a different answer would materially change the route.

## Routing table

| Signal | Route | Notes |
|---|---|---|
| “Teach me X” / “Explain X” | `lesson` | Complete bounded explanation; no mandatory assessment |
| “Explain X in one sentence” | `quick` | Honor explicit brevity |
| “Explain X in five minutes” | `quick` | Respect the timebox; one visual only if it materially helps |
| “Quiz me on X” | `quick` or `lesson` | Quick for a short check; lesson for diagnosis plus remediation |
| “Teach me to do X today” | `lesson` | One observable competency and transfer task |
| “Make me an interactive lesson” | `lesson` | Use host chat plus a complete static Markdown/HTML representation unless an approved interaction runtime is available |
| “Help me learn X over six weeks” | `course` | Confirm mission, horizon, persistence, and review policy |
| “Continue where we stopped” | `course` if state exists | Read state only after resolving the intended workspace |
| “Just give me the answer” | current mode → direct answer | Stop the Socratic loop immediately |
| Ordinary task completion | no trigger | Teach only when requested or clearly the goal |

## Quick mode

### Contract

- Do not initialize a workspace or write durable learner state by default.
- Adapt to the learner within the current conversation.
- Ask at most one high-value diagnostic question when the request is already answerable.
- Prefer: concise explanation → concrete example → optional retrieval/application check.
- Offer a deeper lesson or review prompt; do not pressure the learner into one.

### Allowed outputs

- Chat explanation.
- Small semantic table, exact SVG, Mermaid source, or a host-chat attempt with a complete static representation when it earns its cost.
- A one-off file only when the user requests an artifact.

## Lesson mode

### Contract

- Define one observable outcome.
- Build the complete bounded visual explanation before delivery. Practice, diagnosis and transfer checks are optional unless requested.
- Offer at most one optional intuition check; a skipped check is not evidence.
- Ask once before persisting a session summary or learner evidence.
- If creating a durable lesson, make Markdown canonical and generate its HTML companion.
- Close with evidence observed, uncertainty and an optional next step. Schedule review only when chosen.

### Avoid

- Creating a course tree for one competency.
- Writing a personality-style learner profile.
- Treating a polished artifact as proof of learning.

## Course mode

### Contract

- Offer explicit persistence consent; declining or silence does not block ephemeral course teaching.
- Establish the mission, target independent performance, desired retention horizon, source constraints, and access needs.
- Introduce prerequisites where needed; diagnose first only when requested or material ambiguity requires it.
- Store raw observations separately from inferred concept state.
- Maintain a review queue and use later-session evidence before durable-mastery claims.
- Let learner questions, annotations, errors, and goals change the next lesson.
- Show every material learner-state update at session close.
- After validating active consent, state the actually recovered topic/position and offer exactly one next learner action as a suggestion. Allow continuation, topic change or starting fresh without mandatory assessment.

## Host adapters

Adapters contain no teaching policy. They may map host capabilities, file
locations, tool names, and input/output formats onto the core mode and teaching
contracts, but must not redefine routing, evidence, hinting, mastery, or visual
selection. Describe required capabilities rather than hardcoding one agent
harness when an equivalent native capability can satisfy the contract.

## Persistence consent

Before the first durable learner-state write, explain the resolved `.prax-teach`
location and scope. New-directory consent must explicitly name preferences and
continuity if requested; existing base consent needs a separate extension grant
for those categories. Never persist a refusal to suppress future prompts.
Lesson artifacts in sibling `lessons/` are separate; explain default saving and
honor explicit save-nothing. For base practice tracking, say:

> I can store your goal, practice evidence, misconceptions, and review schedule in `<resolved path>` so later sessions can adapt; you can inspect, correct, export, or delete it. Shall I persist this course?

If the learner declines:

- continue in ephemeral lesson mode;
- do not create learner-state files;
- save lesson artifacts independently in `lessons/` by default and explain this; an explicit save-nothing request forbids durable lesson files too;
- offer a copyable summary if useful.

Consent to lesson files does not automatically grant consent to behavioral analytics or inferred learner state.

## Escalation and demotion

Escalate only when the current outcome cannot be met cleanly:

- `quick` → `lesson`: several dependent steps, practice, or a reusable artifact becomes necessary;
- `lesson` → `course`: the learner requests resumption, a sequence, or review over time.

Before escalation, explain the benefit and added persistence/artifact cost in one sentence.

Demote without resistance when the learner requests speed, an answer, or less ceremony. Preserve already consented state but do not update it unless the learner continues the course.

## Time and cognitive-load budgets

| Mode | Intake budget | Default content budget | Questions per turn |
|---|---:|---:|---:|
| `quick` | 0–1 question | One concept, one example, optional check | Usually 1 |
| `lesson` | 0–1 material clarification | Complete bounded explanation; optional check | 1 at a time |
| `course` | Mission; optional diagnosis | One bounded complete lesson | 1 at a time; compact batches only for setup |

These are defaults, not hard limits. Match the learner’s urgency and expertise.

## Failure routing

| Situation | Response |
|---|---|
| Learner is frustrated | Shorten, change representation, or offer **Answer now**; do not infer low ability |
| Source is missing or disputed | State uncertainty and research before teaching the disputed claim |
| Visual fails | After at most two repair attempts on that path, use an honest static equivalent; pause if the requested medium is essential |
| Durable state is missing | Explain the gap, reconstruct only from learner-confirmed evidence, and avoid invented history |
| Durable state conflicts with current performance | Record contradictory evidence, lower certainty, and offer a retest |
| Learner asks for a high-stakes answer | Give appropriately scoped information, use authoritative sources, and avoid pretending tutoring replaces a professional |

## Trigger examples

Should trigger:

- “Teach me why database indexes speed up some queries.”
- “Help me build intuition for Fourier transforms.”
- “Quiz me on these notes, but don’t give answers away.”
- “Make a short accessible HTML lesson from this paper.”
- “Resume my networking course and review what is due.”

Should not trigger automatically:

- “Add an index to this migration.”
- “Summarize this meeting.”
- “Fix this failing test.”
- “What version of PostgreSQL is installed?”

For adjacent tasks, complete the task unless the user asks to learn from it.
