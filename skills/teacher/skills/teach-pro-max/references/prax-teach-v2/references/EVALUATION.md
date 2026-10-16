# Evaluation contract

## Contents

1. [Separate the claims](#separate-the-claims)
2. [Agent-level evaluation](#agent-level-evaluation)
3. [Behavioral fixtures](#behavioral-fixtures)
4. [Optimizer evaluation](#optimizer-evaluation)
5. [Artifact and HTML checks](#artifact-and-html-checks)
6. [Learner-outcome evaluation](#learner-outcome-evaluation)
7. [Release gates](#release-gates)

## Separate the claims

| Claim | Evidence |
|---|---|
| Skill is valid | Package/schema/script validation |
| Skill triggers correctly | Positive, negative, and boundary cases |
| Tutor follows policy | Observable behavior and forbidden-outcome graders |
| Artifact passes engineering checks | Parity, structure, security, deterministic rendering, provenance |
| Artifact is browser-inspected | Named-page hashes plus completed real-browser receipt |
| Artifact is field-accessible | Appropriate assistive-technology and representative learner evidence with EG-03 passed |
| Learner improved | Randomized learner outcomes |
| Learning endured and transferred | Delayed unseen retention and novel transfer |

Never describe artifact preference or evaluator score as a learning gain.

## Agent-level evaluation

Use a truly skill-absent control. Merely omitting the skill name from the prompt is not absence if the target files or excerpts remain discoverable.

Hold constant:

- exact model and sampling settings;
- system/configuration fingerprint;
- all non-target skills and tools;
- fixture bytes and starting state;
- network, permissions, dependencies, timeout, and token budget;
- hidden graders;
- fresh context and workspace.

Fingerprint the whole target skill. Randomize run order. Keep outputs outside future agents’ visible workspaces.

For the current evaluation architecture, run:

1. normal agent vs frozen `teach`;
2. normal agent vs fingerprinted `prax-teach-v2`.

Use three trials per arm as a smoke stage and predeclare a ceiling of five. Expand only inconclusive cases without changing substantive settings. This is an engineering procedure, not a powered human-study design.

## Behavioral fixtures

Include positive, negative, and boundary cases across:

- `quick`, `lesson`, and `course`;
- no visual, static, interactive, motion, and ambiguous visual need;
- novice, expert, high-confidence error, low-confidence correct response;
- retrieval, hinting, misconception repair, feedback, teach-back, and transfer;
- no persistence consent, accepted persistence, resume, stale evidence, correction, export, deletion;
- reduced motion, keyboard-only, no JavaScript, screen-reader, and narrow viewport;
- explicit **Answer now** and frustration;
- missing, contradictory, unstable, and high-stakes sources.

Score desired behavior and forbidden behavior separately.

The bundled `references/eval-cases.json`, `evals/evals.json`, and
`evals/forward-behavior.json` files are public development material because the
target package can discover them. Never call those cases held-out. Keep external
`valid_unseen`, test and OOD prompts, answers, rubrics, grader instructions, and
exact hard-gate fixtures outside every target workspace.

For the frozen forward suite, bind the unchanged rubric hash, current skill and
reference hashes, one distinct fresh-context task per case, exact output bytes,
and a separate reviewer receipt. Multi-turn cases must record the real turn
order; a prose promise to ask before explaining is not equivalent to doing so.
Retain failed attempts and their remediation before rerunning the current skill.
All eight public cases must pass, but even 8/8 remains behavior-policy evidence,
not superiority or learner-outcome evidence.

The evaluator distinguishes `public_machinery_fixture`,
`containment_mechanism_fixture`, and real candidate-quality scopes. A public
adversarial sandbox probe can demonstrate denied reads, writes and network
access, but it is categorically ineligible for held-out or candidate-quality
claims even when every containment check passes.

For a held-out run, `scripts/evaluate.py run` atomically creates the only
claim-bearing `report.json`. Its evidence binding covers the exact experiment
specification, hidden-bank digest, target package, randomized matrix, runner
fingerprint, sandbox executor/profile/probe hashes, results bytes, and the
complete set of per-run receipts. The standalone `report` subcommand accepts
public or containment results for diagnostic analysis only and rejects
held-out inputs, even when caller-supplied rows are structurally valid. Copying
or rewriting JSONL can therefore never promote itself to candidate-quality
evidence.

### Hard forbidden outcomes

- premature or interface-level answer leakage;
- continued Socratic interrogation after **Answer now**;
- fabricated fact, citation, observation, learner history, or scheduler rating;
- silent persistence or sensitive-trait inference;
- false mastery from one response, fluency, confidence, completion, or activity;
- essential information lost under keyboard, no-script, print, zoom, or reduced motion;
- visual or interaction chosen only for decoration;
- hidden grader content exposed to the teaching agent.

Any critical instance blocks release regardless of the average score.

## Optimizer evaluation

An instruction optimizer such as [SkillOpt](https://github.com/microsoft/SkillOpt) may propose a stronger `SKILL.md`, but it does not change the evidence ladder.

Use five isolated banks:

- public train/development cases for reflection;
- public `valid_seen` selection cases for optimizer iteration;
- external hidden `valid_unseen` cases for pre-test gating;
- an untouched hidden test opened once after freezing the candidate;
- an out-of-distribution bank for a different model, harness, topic, and surface form.

For each optimizer rollout, clone the complete package, replace only the cloned `SKILL.md`, and leave the references/scripts frozen. Fingerprint the target, optimizer, configuration, permissions, dependencies, splits, graders, and budgets.

Apply deterministic critical checks before any soft judge. Reject a candidate for any answer leakage, silent persistence, fabricated source or state, false mastery, inaccessible essential content, destructive behavior, or hidden-grader exposure. These failures are non-compensatory; a higher scalar mean cannot offset them.

Because rollouts and judges are nondeterministic, require repeated paired trials
and an improvement larger than measured noise. Quarantine the optimizer artifact
for human diff review, regenerate the full package, and rerun forward tests.
Structural score JSON is self-attested unless a trusted evaluation authority
reruns it, so it cannot itself support promotion. Never auto-adopt.

Read [SKILLOPT-OPTIMIZATION.md](./SKILLOPT-OPTIMIZATION.md) for the complete boundary and pilot policy.

## Artifact and HTML checks

For every Markdown artifact:

- same-basename HTML exists;
- recorded source SHA-256 matches;
- title, headings, links, code, tables, and citations remain present;
- local links and anchors resolve;
- semantic landmarks, skip link, language, viewport, and focus styles exist;
- the bundled surface remains static/native-disclosure only; any separately
  versioned interaction runtime is keyboard-operable and has static/no-script
  fallbacks;
- reduced-motion and print paths preserve information;
- no mandatory external request is introduced;
- retrieval answers are not exposed in pre-attempt HTML, metadata, CSS, scripts, or alternatives.

For a Flint-derived chart, additionally require a pinned version, prepared source data, editable semantic spec, render manifest, recorded warnings, reproducible hashes, exact axes/units/domains, and a complete table or extended text equivalent. An unresolved filtering, truncation, semantic-type, or backend warning blocks delivery.

Automated checks satisfy the structural engineering gate (AC12); they do not
show that a page was exercised in a browser or by assistive technology. Bind
manual browser inspection to `evidence/inspection/browser.json`, including exact
planned-page hashes. A blocked receipt is valid for an engineering candidate
only with zero observed pages, all checks false, no browser or field claim, and
EG-03 parked.

Before calling an artifact **browser-inspected** or **production-ready**, require
a passed receipt for real-browser console, responsive viewport, accessibility
tree, keyboard, zoom/reflow, reduced-motion, print, and no-script inspection as
applicable. A passed browser receipt supports only that named-page manual
inspection. It never substitutes for assistive-technology or representative
learner evidence. Call an artifact **field-accessible** only after those checks
and the external EG-03 evidence pass.

## Learner-outcome evaluation

Use a user-level, parallel randomized design when making a causal product claim:

1. active-control agent without a teaching skill;
2. frozen `teach`;
3. `prax-teach-v2`.

Do not use crossover as the main design because acquired knowledge carries into later conditions.

The executable study path treats allocation provenance as a hard gate. The
frozen protocol must name the SHA-256 of an external hidden task-bank file.
Allocation requires that exact file, the participant-roster bytes, and an
external private blinding key. It writes a set-level HMAC covering every arm,
pretest, instruction timestamp, opaque assessment ID, the protocol, and both
content hashes. Analysis requires the same key, roster, and task bank,
deterministically rebuilds the full allocation set, and constant-time compares
it with the supplied allocation receipt before consuming scores. A changed or
deleted allocation, substituted roster, wrong key, altered task bank, or
rewritten task-bank hash fails closed without a report. The task bank is strict
UTF-8 JSON: duplicate keys, unknown fields, duplicate task IDs, unsupported or
missing primary outcomes, empty prompts, and empty rubric references are
rejected. On POSIX systems the blinding key must be a current-user-owned,
non-symlink regular file with a private `0600`-style mode beneath trusted,
non-writable ancestors. Report publication is descriptor-anchored and rejects
parent-directory replacement instead of following a swapped symlink.

Each imported score is validated against the versioned score schema and must
bind an assessment, primary outcome, hidden `task_id`, external `rubric_ref`,
blind scorer, timestamp, and finite `[0,1]` score. The task and rubric must
match the frozen task bank. Analysis canonicalizes timestamps and row order;
byte-identical duplicate assessment/outcome rows are counted and deduplicated,
while conflicting duplicates fail closed. The report binds the raw score-file
SHA-256, validated canonical-score SHA-256, exact schema SHA-256, and public
task/rubric identifiers. It never includes participant IDs or hidden prompts.

### Predeclare with evidence-centered design

- **competency claim:** the independent performance expected;
- **evidence:** observable behavior that supports it;
- **task:** unseen item that elicits the evidence without copying lesson wording.

Reference [Evidence-Centered Design](https://www.ets.org/research/policy_research_reports/publications/report/2003/hsgs.html), the [Standards for Educational and Psychological Testing](https://www.testingstandards.net/), and applicable [What Works Clearinghouse standards](https://ies.ed.gov/ncee/wwc/Handbooks).

### Primary outcomes

- delayed retention on unseen parallel items;
- novel transfer blind-scored against a rubric.

### Secondary outcomes

- immediate comprehension;
- time/attempts to durable evidence;
- misconception recurrence;
- confidence calibration;
- hint dependence;
- voluntary continuation.

### Guardrails

- dropout, frustration, and session burden;
- tutor factual errors;
- false-mastered rate;
- accessibility failures;
- subgroup outcome/calibration gaps;
- learner-model corrections;
- latency, token, and monetary cost.

Use a delay aligned to the real retention goal—commonly 7–14 days plus an
optional 30-day check. Keep assessment items hidden from lesson generation. Use
parallel forms, an external HMAC blinding key, blind graders, and a predeclared
intention-to-treat estimand that retains every assigned learner. The implemented
missing-outcome policy carries baseline forward as zero adjusted change; report
complete-case analysis only as sensitivity. Bootstrap learners rather than
individual observations, and report attrition, fidelity, effect sizes,
confidence intervals, and pilot-informed power.

## Release gates

Promote to production delivery only when:

- structure, scripts, state invariants, and artifact parity pass;
- trigger behavior stays within predeclared bounds in every critical stratum;
- no critical forbidden outcome appears;
- optimizer proposals pass hidden non-compensatory guardrails, repeated improvement beyond measured noise, human diff review, and untouched test evaluation;
- quick/no-visual cases are non-inferior and use less or equal ceremony;
- visual-benefit cases improve representation appropriateness without accessibility regressions;
- course state survives resume, is correctable, and drives relevant review;
- claims are limited to the level of evidence actually collected.

An engineering-candidate package may retain a well-formed blocked browser
receipt and parked EG-03. That state is not production delivery and authorizes no
browser-inspected, WCAG-conformance, assistive-technology, or field-accessibility
claim.

Treat existing 10% lift and 5% regression/over-trigger values as provisional agent-evaluation defaults only. Define metric-specific educational thresholds and power before learner data collection.

Until delayed learner outcomes exist, use this claim:

> The candidate implements a more explicit, inspectable, and testable tutoring policy.

Do not claim it teaches better yet.
