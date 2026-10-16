# Spec: Practical executable learning in Teach Pro Max

## Problem Statement

Teach Pro Max has strong adaptive tutoring, visual routing, learner-state, and
artifact contracts, but it does not yet name the complete learning sequence for
skills that must be demonstrated through a real executable artifact. Its public
wrapper also rejects Motion Canvas and Remotion while an installed inherited
handbook can still route to them, creating contradictory instructions.

## Solution

Teach Pro Max will remain the single public teaching skill and gain one concise
practical-learning branch. The branch will move a learner through prediction,
execution, inspection, modification, debugging, explanation, and unseen
transfer while keeping engineering success separate from learner evidence.
The visual contract will require one authoritative executable model or an
automated parity check when a browser implementation duplicates it. Current
visual routing policy will be consistent across every normative layer.

## User Stories

1. As a learner, I want to predict what executable work will do before running it, so that I exercise a causal model rather than merely watch output.
2. As a learner, I want to run the smallest authentic artifact, so that practice resembles the skill I ultimately need.
3. As a learner, I want to compare my prediction with observed output, so that discrepancies become useful evidence.
4. As a learner, I want to change one meaningful variable, so that I learn which parts of the system control the result.
5. As a learner, I want to debug a realistic failure, so that success is not limited to the demonstrated path.
6. As a learner, I want to explain why the result changed, so that execution is connected to a reusable mental model.
7. As a learner, I want an unseen transfer task, so that the tutor can distinguish imitation from independent capability.
8. As a learner, I want generated files and passing tests kept separate from claims about my learning, so that progress reports remain honest.
9. As a learner, I want one current next action when I resume an accepted course, so that I can restart without another intake interview.
10. As a visual learner, I want interactive output to use the same authoritative model as the executable lab, so that the picture cannot silently teach different rules.
11. As a visual learner, I want reduced-motion, no-script, keyboard, print, and narrow-screen paths to preserve essential information, so that the lesson remains usable through my access path.
12. As a teaching-skill user, I want one public invocation, so that I do not need to attach legacy teaching skills to recover visualization.
13. As a teaching-skill user, I want Manim and HyperFrames to be the current film routes, so that new work does not drift into deprecated defaults.
14. As a maintainer, I want practical behavior covered at existing public seams, so that implementation refactors do not invalidate the tests.
15. As a maintainer, I want speculative scene schemas and optional runtimes deferred until a lesson consumes them, so that the teaching package does not accumulate unused infrastructure.
16. As a reviewer, I want exact-byte distribution and generated-document checks, so that a release claim binds the code that was actually reviewed.

## Implementation Decisions

- `teach-pro-max` remains the only public teaching skill. The embedded v2 name remains a compatibility and schema identifier.
- Extend the existing teaching protocol rather than creating a new skill, framework, or practical-teaching package.
- The practical branch is: predict, run, inspect, modify, debug, explain, transfer.
- A successful command, test, generated artifact, or visual interaction is engineering evidence. Learner evidence still requires observed learner performance with hint level and transfer status.
- A practical visual uses the authoritative executable model directly or carries an automated parity fixture with independently specified expected states and outputs.
- Current routing uses browser-native HTML/SVG and Prax Visual Lab first, HyperFrames for general film, and Manim 0.21.0 for precision mathematical film.
- Motion Canvas and Remotion remain historical registry entries and are never default routes for new work.
- A scene or execution-trace schema is introduced only when a concrete lesson needs playback, scrubbing, or synchronized multi-surface state.
- Course resumption may expose exactly one next action after persistence consent. Host adapters only read this state; they do not contain independent pedagogy.
- Olli, JSXGraph, Pyodide, MCP Apps, Three.js, and other optional runtimes remain trigger-gated.

## Acceptance Criteria

- **AC1:** WHEN an executable competency is taught, the system SHALL route through prediction, authentic execution, output inspection, meaningful modification, debugging, explanation, and unseen transfer in that order unless the learner requests **Answer now** or an accessibility/safety exception applies.
- **AC2:** WHEN executable output or tests pass, the system SHALL label that result as engineering evidence and SHALL NOT infer learner mastery without observed learner performance.
- **AC3:** WHEN a practical visual duplicates an executable model, the system SHALL require an automated parity fixture against independently specified expected states and outputs.
- **AC4:** WHEN a practical visual can consume the authoritative model directly, the system SHALL prefer that path over duplicate logic.
- **AC5:** WHEN new visual or film work is routed, the system SHALL exclude Motion Canvas and Remotion from default candidates while retaining exact-name historical inspection.
- **AC6:** WHEN Teach Pro Max is invoked for a visual lesson, the system SHALL NOT require a second teaching skill.
- **AC7:** WHEN a course is resumed from consented state, the system SHALL expose exactly one current next action without embedding new pedagogy in a host adapter.
- **AC8:** WHEN no lesson requires playback, scrubbing, or synchronized multi-surface state, the system SHALL NOT create a scene or execution-trace schema.
- **AC9:** WHEN an optional visual runtime has no consumer lesson, the system SHALL NOT install or require it.
- **AC10:** WHEN reduced-motion or no-script delivery is used, the system SHALL preserve essential instructional information.
- **AC11:** WHEN the practical branch is evaluated, the public fixture SHALL test desired behavior and forbidden outcomes through existing protocol/evaluation seams.
- **AC12:** WHEN the package is promoted, generated Markdown/HTML parity, focused behavior tests, the full test suite, distribution integrity, a smoke test, and fresh review receipts SHALL bind the exact promoted bytes.

## Testing Decisions

- Test tutoring policy at the public skill/evaluation fixture seam rather than parsing private implementation helpers.
- Test visual routing through the existing route and registry interfaces, including default exclusion and exact-name historical inspection.
- Test practical-model consistency through an artifact-level parity fixture with known expected values, not by recomputing the same formula in the assertion.
- Reuse the package renderer and distribution verifiers for generated HTML and exact-byte checks.
- Add one public practical-learning fixture covering the complete sequence and one forbidden-outcome set covering project takeover, false mastery, unused dependency installation, and second-skill invocation.
- Run focused tests during each vertical slice and the complete package verification before promotion.

## Out of Scope

- A new teaching skill or renamed embedded schema.
- A universal scene/trace DSL before a playback consumer exists.
- Installing Olli, JSXGraph, Pyodide, MCP Apps, Three.js, Manim, or HyperFrames merely to prove availability.
- Vendoring external teaching sites or visualizers.
- Claiming improved human learning without delayed learner evidence.
- Rewriting historical immutable receipts to make them appear current.

## Further Notes

The Python-for-ML lab is an implementation probe, not the product. Its useful
patterns inform this protocol, while its project-specific scaffolding stays in
that repository. Existing dirty visual-unification work is part of the current
candidate and must be revalidated rather than discarded or silently relabeled.
