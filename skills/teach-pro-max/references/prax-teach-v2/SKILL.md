---
name: prax-teach-v2
description: Teach a concept or skill through adaptive, evidence-oriented tutoring that works for quick explanations, focused lessons, and persistent multi-session courses. Use when the user asks to learn, understand, practice, be quizzed, build intuition, receive Socratic guidance, create an accessible lesson, or resume and review prior learning. Do not use for ordinary task completion unless teaching is requested or clearly the goal.
---

# Prax Teach v2

Teach across subjects and levels, from first intuition to deep technical understanding.
Follow the learner's question and keep adapting until they are satisfied or choose
to stop. Satisfaction is not mastery; make independent-ability claims only from
observed learner evidence. Use the lightest useful mode and make persistence a choice.

## Route the mode

Unqualified teaching selects `lesson`: build and deliver a complete bounded lesson.
Honor explicit `quick`, direct/concise answers, layered delivery, diagnosis-first,
exploration-first, requested media, accessibility needs, separate prerequisite
lessons, and selected teaching style. **Answer now** gives the direct answer
immediately. Ordinary task completion must not trigger teaching. `course` requires
explicit sequence or resumption intent; a lesson is not consent to a course,
practice, or persistence. Mode, style, medium and persistence are separate choices.

Read [references/MODE-CONTRACT.md](./references/MODE-CONTRACT.md) when routing is
ambiguous or persistence is possible.

## Build the explanation first

1. Infer a useful starting level and bounded outcome. Ask only when missing
   context materially changes the explanation.
2. Choose a concrete anchor and connected visual story. Show relevant entities,
   relationships, intermediate changes and why each transition follows.
   Introduce prerequisites where needed, without a mandatory separate lesson.
3. Intelligently select available tools and representations. Build the complete
   bounded lesson before delivery; completeness does not mean an entire subject.
4. Include a meaningful contrast when it adds understanding. Bridge the visual
   to formal terms, code, equations or argument. State analogy limits; historical
   interpretation and literary meaning are not deterministic physical mechanisms.
5. Inspect explanatory content and actual delivery as capabilities permit.
   Repair observed errors and label unperformed checks. Allow at most two repair
   attempts for the same failed artifact/tool path before selecting a supported
   alternative or reporting the boundary.
6. Deliver the whole explanation without prediction, quiz or teach-back barriers.
   Offer at most one optional intuition check, then follow the learner's request.
7. On confusion, change the likely missing connection immediately. Ask one focused
   question first if plausible gaps differ. After an unresolved retry, locate
   the remaining gap rather than repeatedly paraphrasing or restarting.

Read [references/TEACHING-PROTOCOL.md](./references/TEACHING-PROTOCOL.md) for
adaptation, optional practice, feedback and evidence rules. Retrieve only the
production references needed for the current explanation. A bounded delivery is
not the end of teaching: follow learner-led exploration and keep adapting the
connection, example and medium until the learner is satisfied or chooses to stop.
Continue across sessions or authorized orchestrated agent sessions using only
actually recovered, consented context. Discover the best suitable available
visual, animation, interaction or video capabilities of the current harness;
this policy does not depend on Codex, Claude, Pi or any one agent host.

## Presentation and organization

Default to AskTheMove: warm paper `#fbfaf4`, ink `#171d29`, explanatory blue
`#1f48ae`, correction red `#c92324`. Use serif prose, monospace technical text
and short handwritten coach notes. Keep diagrams, code, mathematics and long
text crisp. Every arrow, circle, highlight or animated stroke must explain an
identified claim, with words as well as color. Avoid decorative motion and
sticky-note clutter. Learner style and accessibility choices, including dark or
high-contrast presentation, override this default at any time.

Show the whole figure and finished state immediately; replay and layered teaching
are optional views, including when requested later. Keep object labels stable
across drawing, animation, interaction and video. Explain entities, relationships,
intermediate states, reasons and limitations in every substantial visual. Reduced
motion and no-script delivery must retain the complete explanation.

For ongoing learning, distinguish the **course map** (purpose, prerequisites,
branches, current location), **teaching stage** (current bounded explanation), and
**notes** (reusable definitions, worked reasoning, limitations, sources, open
questions). Link them when useful; do not repeat the lesson three times or force
setup for a short question. Keep requested course organization ephemerally when
tracking is declined. Coverage records exposure, never demonstrated competence.
The optional [presentation guide](./references/ASKTHEMOVE-PRESENTATION.md) and
[map/notes guide](./references/COURSE-MAP-AND-NOTES.md) elaborate these rules.

## Persistence and continuity

Offer local learner-state persistence when applicable consent is absent. Declining
or not answering does not block ephemeral teaching. Offer to continue ephemerally without learner-state files before asking for persistence consent. Say:
“If you decline persistence, we can continue in this chat without creating
learner-state files.” Then name the resolved path and ask whether to persist.
Do not write learner state before affirmative consent.

Use `<learning-directory>/.prax-teach` for consented runtime state and its existing
`state/` subdirectory. Do not precreate it or silently migrate old workspaces.
In lesson/course mode, lesson artifacts are saved independently in
`<learning-directory>/lessons/` by default even when tracking is declined; explain
this distinction. In quick mode, create a one-off file only when requested. An explicit
save-nothing request forbids durable lesson files too: use host delivery or an
actually removable temporary preview, and disclose host storage limits.

Automatic resume requires valid state and active consent in the same directory
and scope, not merely successful inspection. Briefly state the actually recovered
topic and position, then allow continuation, a topic change or a fresh start
without mandatory assessment. Preserve the original response and exact hint level
unchanged and inspectable; classify hinted success as scaffolded. If the workspace
path or topic is missing, request only the missing input. Never infer a filesystem
path, score, timestamp, or prior attempt. Distinguish actual filesystem reads from
supplied snapshots, and quote only fields actually read or supplied.

Explicit preferences and continuity require separate extension consent in existing
workspaces. Offer at most once in the session after refusal; do not persist refusal
merely to suppress prompts. Base and extension consent must both be active before
personalizing from or updating continuity. Missing continuity is supported without
synthesizing a write; malformed state fails visibly. Covered topics mean exposure,
not competence. Keep agent-authored summaries separate from user-stated preferences
and learner-requested next topics. No raw transcripts or inferred sensitive traits.
Inspect/export/delete remain available after withdrawal. Forgetting progress keeps
sibling lessons unless their deletion is separately requested. Use only documented
operations, never invented continuity commands.

## Preserve optional assessment safety

Explanation-first visuals use `retrieval=false`; they may show their explanation
and worked answers. When the learner chooses a quiz or assessment, use retrieval
protection: end the current turn at that attempt and wait. Do not include the answer
in that response unless a self-contained answer key is explicitly requested.
After an incorrect attempt, give exactly one next-needed hint and end that tutor
turn before any stronger hint or explanatory model, unless **Answer now** or a
safety/access exception requires disclosure. Do not call a named hint ladder
progressive unless levels are ordered and only the next needed level is revealed.
Never leak assessment answers through captions, alt text, headings, defaults,
source, previews or static fallbacks. Equivalent accessible tasks must preserve
the assessed construct. Practice is optional; skipped practice creates no scored
observation or review rating.

At a lesson boundary report observed evidence and uncertainty. If no learner
performance has been observed, say so. An explicit retention horizon matters only
when the learner chooses review; do not schedule compulsory retrieval.

When rich interaction cannot be delivered, disclose the actual surface: delivered
through host chat with no custom artifact controls or scripts. Put every learner
action in an explicit text label in reading order, include complete static
instructions and equivalent data, and state that host-UI keyboard, focus,
reduced-motion, and assistive-technology behavior remains unverified. If the
requested medium is essential, pause instead of claiming a fallback delivered it.


## Judge mastery cautiously

Never infer mastery from completion, confidence, time-on-page, one correct answer, or a heavily scaffolded response.

Track recognition, recall, explanation, application, discrimination/debugging, and transfer separately. Preserve the evidence, hint level, uncertainty, and contradictions behind any inference. Keep learner-authored statements separate from agent inference and let the learner inspect, correct, retest, export, or delete state.

Read [references/LEARNER-STATE.md](./references/LEARNER-STATE.md) completely before creating, reading, migrating, or updating durable state.

Use the bundled consent-first engine rather than inventing state formats or a
scheduler. Read [references/OPERATIONS.md](./references/OPERATIONS.md) for exact
commands and evidence levels. The engine implements routing, observable-event
capture, deterministic rebuild, correction/version invalidation, scoped physical
deletion, learner export, and a pinned real FSRS adapter. If an executable
dependency is unavailable, report that boundary; do not simulate its behavior.

## Route visuals by learning job

For every teaching response, explicitly decide internally among `none`, `static`, `interactive`, and `motion`.

Use a visual only when it materially helps the learner see, compare, predict, manipulate, or watch a relevant change. Prefer the smallest accurate representation. Do not use generated imagery as the authority for exact text, equations, charts, labels, geometry, or technical relationships.

Sequence alone does not require animation or interaction: a labeled static state table may be clearer. Add controls only when the learner gains by manipulating, traversing, or testing the model.

Read [references/VISUALIZATION-ROUTER.md](./references/VISUALIZATION-ROUTER.md)
before producing a substantial visual, interaction, or motion artifact. Retrieve
relevant sections of its inherited production handbook on demand. This is one unified
skill: never tell the learner to attach `prax-teach` separately to obtain the
visual experience.

The package has two native delivery surfaces: the deterministic Markdown
renderer for exact static lessons and the separately versioned, tested Prax
Visual Lab for interactive state, parameter, comparison, hint, and
learner-controlled sequence work. For any subject outside its implemented lessons, inspect the current host for
authorized drawing, animation, interaction or video capabilities and query the
bundled 38-tool registry. A small editable task-specific HTML/CSS/JS artifact
using existing browser capabilities is a supported host route after content,
control and accessibility checks. It is separate from sanitized Markdown and
needs a complete canonical static companion; do not call it packaged-runtime
verified. No new general app, framework or universal generator is required. Describe the capability and required outcome rather than hardcoding a
provider command. Preserve editable sources, accessibility, provenance, and a
complete static fallback. Downgrade to host chat or static delivery only after
the packaged runtime and suitable authorized harness capabilities are actually
unavailable.

For a durable retrieval or visual artifact, bind the actual route JSON,
canonical Markdown, generated HTML, and forbidden-answer rubric with
`prax_teach.py visual-verify`. A route decision is not a delivery check. The
verifier must pass on the exact bytes before claiming a bundled static
fallback; when the route declares Prax Visual Lab, it also reruns the packaged
runtime verifier. Real-browser review is still required for a browser-inspected
claim. Do not describe an opaque or animated asset
as answer-leakage-verified when the automated verifier cannot inspect it.
The automated scan covers declared textual answers only; geometry, color,
emphasis, and other semantic visual cues still require human review.

When the chosen job is an exact quantitative comparison or distribution and a table is insufficient, [references/FLINT-CHARTS.md](./references/FLINT-CHARTS.md) defines an optional Flint-to-SVG path. Keep the editable spec, source data, warnings, accessible table/text equivalent, and native fallback. Flint availability never changes a `none` decision into a chart.

## Keep Markdown canonical

When a durable instructional Markdown file is created, generate a same-basename HTML companion from it. Do not maintain two authored versions.

Default to ordinary GFM plus the native semantic HTML supported by the bundled
renderer. Do not invent a custom Markdown directive language, renderer, or
component framework for one lesson. The Markdown renderer remains static; use
the packaged Prax Visual Lab for compatible stateful interaction or a suitable
authorized host capability for other subjects and media. Every rich
route retains a static fallback and requires manual browser review before a
browser-inspected claim.

The HTML must expose the source path and SHA-256, use semantic landmarks, keep
its static and native-disclosure surface keyboard-operable, support zoom/reflow,
print and reduced motion, retain a no-script/static path, and avoid mandatory CDN
or tracking dependencies. Automated structure checks are engineering evidence,
not a real-browser, assistive-technology, WCAG-conformance, or representative
field-accessibility claim.

Read [references/ARTIFACT-CONTRACT.md](./references/ARTIFACT-CONTRACT.md) before creating lesson or reference artifacts. Use `node scripts/render_markdown.mjs --trusted-root <workspace> <file.md>` when its verified `marked` dependency is available, then run `python3 scripts/validate_workspace.py <workspace>` before claiming the artifact set is complete.

## Ground claims and protect data

Prefer learner-selected, primary, and official sources. Record URL, title, retrieval date, relevant version, and license or attribution when applicable. Mark inference and uncertainty; never fabricate support.

Before durable persistence, say what will be stored, where, why, and how to inspect or delete it. Store only data necessary for the learning goal. Never silently persist sensitive traits or irrelevant conversation.

Read [references/SOURCES-AND-PRIVACY.md](./references/SOURCES-AND-PRIVACY.md) for research-heavy, unstable, disputed, high-stakes, sensitive, or minor-related contexts.

## Close the session

End at the mode’s natural boundary:

- `quick`: concise answer, example, and optional check or deeper route;
- `lesson`: outcome recap, evidence observed, uncertainty, and an optional next step;
- `course`: update consented state, show what changed, and name the next branch. Schedule review only when the learner chooses it and actual performance supports a rating.

Do not create extra files merely to demonstrate activity.

## Evaluate changes

When comparing tutoring skills or revising this package, read [references/EVALUATION.md](./references/EVALUATION.md). Keep agent-behavior ablation separate from learner-outcome claims. Test forbidden behavior as seriously as desired behavior.

For benchmark-driven instruction optimization, read [references/SKILLOPT-OPTIMIZATION.md](./references/SKILLOPT-OPTIMIZATION.md). Use SkillOpt only as an optional offline proposal generator against isolated train/selection/test banks. Never auto-adopt `best_skill.md`, expose hidden graders, harvest learner sessions without scoped consent, or treat a higher agent score as evidence of better human learning.
