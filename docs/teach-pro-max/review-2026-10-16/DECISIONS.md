# General visual teaching skill: agreed direction

Status: existing-skill revision approach approved by the user; SELECTIVE EXPANSION review mode selected; revised governing specification remains pending.

## Product objective
Improve the general Prax Teach v2 skill so it can teach across learners, subjects, and agent hosts by building concrete intuition through deep, purposeful visual explanation. The deliverable is the reusable skill, not a neural-network lesson or a new application.

## User decisions
- General teaching skill, not a personal tutor or standalone app.
- Highest emphasis on intuition and explanatory visualization; nothing decorative.
- Visual explanation first. Diagnosis-first and exploration-first are configurable alternatives.
- Deliver the complete visual lesson together by default. Layered delivery on request.
- Select static drawings, animation and interaction intelligently by explanatory purpose. Learners can request a different representation afterward.
- Use native model capabilities and available tools. Browser HTML is a delivery surface when useful, not a new product.
- Connected scenes collectively explain the whole story; every scene has an explanatory role.
- Offer one optional intuition check, then let the learner lead. No compulsory quiz or teach-back.
- Offer state persistence when starting a new lesson without existing consent; declining must not block teaching.
- Store state per learning directory in .prax-teach/ and instructional artifacts in lessons/, outside installed skill files.
- Resume automatically within an already-consented directory; announce context briefly and allow topic changes. Re-consent for changed scope.
- Adapt naturally from the request and conversation; respect explicit preferences without fixed learning-style labels.
- Explain necessary prerequisites within the story; separate prerequisite mini-lessons on request.

- Forgetting progress deletes scoped saved learning records while preserving lesson artifacts. Delete lesson artifacts only on an explicit separate request. User selected this lifecycle behavior.

- If suitable tools cannot produce requested animation/interaction, deliver an accurate static fallback with the limitation disclosed; pause instead when the learner explicitly requires that medium. User selected A.

- Declining learner-state persistence still allows lesson artifacts in lessons/ by default, with the distinction disclosed. Explicit save-nothing overrides artifact saving; no learner profile, progress or history is written without consent. User selected A.

## Problems the user wants solved
Explanations sound clear but never click; visuals display the result without explaining why/how; impressive motion or controls teach little; explanations are too shallow.

## Illustrative test case only
Artificial neuron -> multilayer representations -> backpropagation -> attention -> LLMs, assuming basic arithmetic and introducing mathematical prerequisites visually. This is not the product scope or an instruction to build that lesson now. Evaluation must include other domains and expertise levels.

## Confirmed implementation-policy conflicts
- SKILL.md response gates and TEACHING-PROTOCOL.md require an initial attempt and stop before explanation.
- Immediate post-error rule withholds correction until another learner turn.
- Resume currently requests fresh retrieval before advancing, rather than simply resuming with optional practice.
- Visual router says build an interactive lesson first, while new preference chooses medium by concept.
- MODE-CONTRACT.md prioritizes the lightest/quick mode; complete visual teaching needs a distinct default without overriding explicit requests for brevity.
- Existing state evidence must continue separating observed performance from content viewed; optional checks cannot generate invented mastery.

These are document-level findings, not results of a new behavioral experiment.

## Approved implementation approach

Revise the existing skill in place as a versioned candidate, reusing its state and visualization capabilities. User explicitly selected this approach and asked to continue. This is not approval to replace the governing evaluation contract or deploy an unreviewed candidate.

## Reuse candidates
Existing consent/state/event engine, scheduler, visual capability registry, renderer, visual lab, export/deletion operations, factual/accessibility checks. Verify compatibility before reusing; avoid a second state engine or rendering framework.

## Accepted selective expansions

Review mode: SELECTIVE EXPANSION, explicitly selected by the user.

1. **Adaptive make-it-click recovery.** When a likely gap is clear, change the explanation immediately. When several gaps are plausible, ask one focused question first. If confusion persists, locate the remaining disconnect before trying again. Honor requested representations; preserve useful explanation rather than restarting or paraphrasing repeatedly.
2. **Meaningful contrast.** Where useful, change one important condition and explain why the result changes. Use contrasts to expose mechanisms, distinguish concepts, or mark analogy limits. Avoid padding.
3. **Visual-to-formal bridge.** Connect the visual mental model to relevant equations, code, terminology, or argument at the learner's level. Do not force equations into unsuitable subjects.
4. **Pre-delivery explanation check.** Inspect visual purpose, missing causal/logical steps, label consistency, and whether controls/animation produce the described result. Revise observed problems and distinguish rendered inspection from checks unavailable in the current host. This is quality control, not evidence of learner mastery.

All four additions were individually accepted; the user subsequently confirmed the combined scope and directed the detailed review to proceed. No additional product expansion is accepted by implication. These are candidate design requirements, not claims of implementation or validation.

## Review tasks
- [x] Capture current product direction and baseline commit.
- [x] Inspect current teaching policy, visualization router, mode/state/evaluation contracts.
- [x] Complete primary-source research and record limitations.
- [x] Compare 2-3 implementation approaches and obtain user selection: revise the existing skill.
- [x] Select CEO review mode: SELECTIVE EXPANSION.
- [ ] Complete detailed review and resolve remaining design decisions.
- [ ] Present and approve a versioned design and evaluation contract.
- [x] Independently review the draft design: one pass, seven concerns recorded; unresolved decisions remain.
- [ ] Create implementation plan, then make approved changes in isolation.
- [ ] Verify behavior and deployment; report limits without claiming human learning gains.

Visual companion: offer only if a forthcoming visual decision benefits from it; no mockup or lesson is being built during discovery.

## Change control
The installed skill and its historical evaluator remain untouched. New behavior deliberately conflicts with old policy gates, so the new governing specification must be approved and versioned before candidate changes. Old tests failing because the policy changed must not be silently rewritten and cited as independent improvement evidence. Freeze baseline, evaluation inputs, thresholds, protected paths, candidate paths, budgets, stop rule and rollback before implementation. Current work is a read-only product review plus review-document output, not an optimization run.
