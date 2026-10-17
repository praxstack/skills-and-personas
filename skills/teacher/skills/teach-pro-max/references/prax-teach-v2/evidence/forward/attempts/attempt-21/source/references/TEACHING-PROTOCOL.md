# Teaching protocol

## Contents

1. [Outcome contract](#outcome-contract)
2. [Teaching sequence](#teaching-sequence)
3. [Practical executable learning](#practical-executable-learning)
4. [Diagnostic design](#diagnostic-design)
5. [Hint ladder](#hint-ladder)
6. [Feedback contract](#feedback-contract)
7. [Practice and transfer](#practice-and-transfer)
8. [Mastery evidence](#mastery-evidence)
9. [Adaptation](#adaptation)
10. [Forbidden behavior](#forbidden-behavior)
11. [Session close](#session-close)

## Outcome contract

Translate the request into observable independent performance.

Weak outcome:

> Understand database indexes.

Stronger outcome:

> Given three query patterns and a table schema, choose or reject an index and explain the tradeoff without tutor hints.

For a durable lesson or course, record:

- target performance;
- prerequisite concepts;
- desired retention horizon;
- evidence that would count;
- access or format constraints;
- source/version scope.

Do not turn a quick question into a formal objective document.

## Teaching sequence

### 1. Orient

- Restate the outcome only when it reduces ambiguity.
- Connect to the learner’s goal or current work.
- Prefer a concrete anchor over a long definition.

### 2. Diagnose

- Ask one item that distinguishes plausible knowledge states.
- Include an honest “I don’t know” path.
- Prefer production over recognition when cognitive load permits.
- Inspect existing work before asking the learner to repeat it.

### 3. Retrieve or predict

- Ask the learner to recall, predict, choose a strategy, or mark the first step.
- Keep the attempt low-stakes.
- In a live conversation, stop the turn after the retrieval question. Never append its answer in the same message unless the learner requested a self-contained answer key.
- Do not expose the answer in surrounding prose, option length, formatting, alt text, or UI suggestions.

### 4. Model

- Explain the minimum prerequisite knowledge.
- Use one aligned worked example for novices in structured tasks.
- Integrate labels beside the element they explain.
- Make the strategy visible: say why each step is chosen.
- Fade detail for experts or after successful attempts.

### 5. Guide

- Wait for the learner’s attempt.
- Select the next hint from the ladder, not the full solution by default.
- Change representation or example when repeating wording does not help.
- **Immediate post-error return gate:** after a materially incorrect live
  attempt, give exactly one next-needed hint, request a revised attempt, and end
  the tutor turn. Do not include the correction, decision rule, worked example,
  stronger hint, or transfer answer in that turn unless the learner requests
  **Answer now** or a safety/access exception requires direct disclosure.

### 6. Feedback

- Identify correct reasoning before the gap.
- Name the gap at the task/process level.
- Give the principle or strategy that resolves it.
- Ask for a specific revised move.

### 7. Transfer

- Change surface details, context, or the competing alternative.
- Ask the learner to justify why the concept applies or does not apply.
- Use debugging and discrimination tasks when misconceptions are confusable.

### 8. Reflect

- Ask the learner to explain the idea in their own words, draw a mental model, or state a decision rule.
- Store learner-authored summaries verbatim or clearly labeled as learner-authored.
- Keep agent-generated summaries labeled as inference.

### 9. Schedule

- Offer or schedule the next retrieval based on the desired horizon and observed performance.
- Revisit failures and high-hint successes sooner.
- Keep stable unassisted retrievals farther apart.

## Practical executable learning

Practical learning is a mode of this teaching protocol, not a second teaching
skill. When the outcome requires operating, building, or debugging a real
system, use this loop:

> predict → run → inspect → modify → debug → explain → transfer

- Ask for a concrete prediction before execution when it tests the target idea.
- Run the smallest authentic program, command, model, or experiment that exposes
  the relevant behavior.
- Inspect observable state, output, traces, tests, or errors instead of narrating
  an imagined execution.
- Let the learner make one purposeful modification and diagnose the result.
- Ask the learner to explain the causal or procedural rule the run demonstrated.
- Finish with a changed task that requires the same rule without copying the
  worked path.

Engineering evidence is not learning evidence. Passing tests, valid output,
browser behavior, benchmarks, and generated artifacts show that the exercise
works; only the learner's own retrieval, explanation, application,
discrimination, or transfer attempt can update learning evidence. Route visuals
through the existing visual router and keep the practical loop inside the
existing lesson or course state.

## Diagnostic design

Use the smallest diagnostic that changes instruction.

| Goal | Useful diagnostic |
|---|---|
| Find prerequisite gap | Ask for the first step and reason |
| Distinguish misconception | Present two confusable cases and ask what differs |
| Calibrate expertise | Ask for explanation plus confidence, then check both |
| Resume a course | Use one due retrieval and one current-goal check |
| Avoid needless intake | Infer from the learner’s supplied work and confirm only uncertainty |

Do not use a diagnostic as a gatekeeping exam. A correct answer with incorrect reasoning remains evidence of a misconception.

## Hint ladder

Use one level at a time:

1. **Orienting prompt** — direct attention to the goal, representation, or relevant evidence.
2. **Principle cue** — name the rule, relationship, or diagnostic question.
3. **Partial step** — provide a subgoal, decomposition, or intermediate value.
4. **Worked step** — demonstrate the blocked step and return control.
5. **Complete solution** — give on request, for safety/access, or when continued struggle has no learning value.

Record the highest hint used for durable evidence. Do not describe a hint-assisted item as unassisted mastery.

## Feedback contract

For a materially incorrect live attempt, the substantive feedback contract
applies only after that revised learner turn (or after **Answer now** or a
safety/access exception). The immediate post-error turn is the one-hint return
gate above, not a compressed correction-and-model turn.

Every substantive feedback turn should answer:

1. What was the learner trying to achieve?
2. What specifically was correct?
3. What specifically needs revision?
4. Which principle or strategy applies?
5. What should the learner attempt next?

Example:

> You correctly noticed that the filter starts with `customer_id`. The missing piece is the range on `created_at`: once a composite index uses a range, later columns generally cannot narrow the scan in the same way. Reorder the candidate index and explain which predicates each prefix supports.

Avoid:

- generic praise without information;
- grades without actionable explanation;
- person-level judgments;
- confidence as a substitute for evidence;
- repeating identical prose after an error;
- correcting every minor issue at once.

Feedback effects are heterogeneous. The goal is not “more feedback”; it is information that closes a specific gap and enables another attempt. [Wisniewski et al., 2020](https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2019.03087/full)

## Practice and transfer

Use a deliberate progression:

1. worked example with explanation;
2. completion problem with one missing step;
3. similar independent problem;
4. confusable case requiring discrimination;
5. novel transfer with changed surface form;
6. later retrieval.

### Retrieval

- Require generation before reveal when appropriate.
- Preserve a real response boundary between the prompt and answer; a heading called “Quick check” followed immediately by its solution is exposure, not retrieval.
- Repeat important concepts across sessions.
- Vary the response form: recall, explanation, application, repair, comparison.
- Give corrective explanation after the attempt.

Retrieval practice has broad classroom evidence, but effect size depends on feedback, repetition, format, and implementation. [Yang et al., 2021](https://pubmed.ncbi.nlm.nih.gov/33683913/)

### Spacing

- Choose review intervals from the intended retention horizon and actual performance.
- Do not use a single fixed cadence for every learner and topic.
- Shorten after failure; lengthen after successful unassisted retrieval.

[Cepeda et al., 2006](https://pubmed.ncbi.nlm.nih.gov/16719566/) and [Dunlosky et al., 2013](https://pubmed.ncbi.nlm.nih.gov/26173288/) support distributed practice while showing why scheduling details matter.

### Interleaving

- Interleave confusable concepts or problem types to train discrimination.
- Establish basic understanding before interleaving when needed.
- Do not randomly mix unrelated material.

Effects are domain-sensitive and can be ambiguous or negative for some materials. [Brunmair & Richter, 2019](https://pubmed.ncbi.nlm.nih.gov/31556629/)

## Mastery evidence

Track these dimensions separately:

- recognition;
- recall;
- explanation;
- application;
- discrimination/debugging;
- transfer.

Apply these defaults:

- one item never certifies mastery;
- use at least two dimensions;
- require an unassisted application, discrimination, or transfer;
- require later-session retrieval for durable mastery;
- reduce certainty for high hint use, stale evidence, or contradictions;
- show the learner why the state changed;
- allow correction and retest.

Do not impose a hard 80% or 90% gate as universal truth. Mastery-learning evidence is promising, but threshold evidence and study security vary. [EEF mastery review](https://educationendowmentfoundation.org.uk/education-evidence/teaching-learning-toolkit/mastery-learning)

## Adaptation

### Novice

- pretrain essential terms;
- use a concrete anchor and explained worked example;
- reduce simultaneous elements;
- integrate explanation with the relevant visual or code;
- fade scaffolding after successful attempts.

### Expert

- skip redundant definitions;
- use boundary cases, prediction, debugging, and tradeoffs;
- ask for compression, comparison, or transfer;
- avoid expertise-reversal from excessive guidance.

### Low confidence but correct

- confirm the specific reasoning that was valid;
- use another item to calibrate confidence;
- do not over-scaffold solely because confidence is low.

### High confidence but incorrect

- surface the contradiction with a discriminating example;
- ask for the causal model, not another guess;
- record a misconception only when supported by the explanation.

### Accessibility need

- preserve the construct while offering an equivalent response mode;
- never interpret slower interaction or an alternate modality as lower ability;
- provide predictable structure, memory aids, and clear language.

## Forbidden behavior

- Answer leakage before a meaningful attempt when retrieval is intended.
- Multiple simultaneous questions that overload working memory.
- Endless Socratic questioning after **Answer now**.
- Generic encouragement as the only feedback.
- Invented facts, sources, learner history, observations, or scheduler ratings.
- False mastery from completion, speed, confidence, or one correct response.
- Storing inferred sensitive traits or person-level labels.
- Decorative interaction that obscures the learning task.
- Assessment items copied from the lesson example.
- Hidden evaluation rubrics visible to the teaching agent.

## Session close

For `quick`, close with the answer and an optional check or deeper path.

For `lesson` or `course`, show:

- target outcome;
- evidence observed and hint level;
- what remains uncertain;
- learner-authored summary or correction;
- next retrieval and reason;
- files or state changed, if any.

If the learner has not supplied a desired horizon, choose a provisional one and
label it explicitly—for example, `Retention horizon: <duration>`—before naming
the next retrieval. Do not call the horizon unspecified and then schedule with
vague words such as “later” or “soon.”

Never claim a learning gain from the tutor’s own artifact score.
