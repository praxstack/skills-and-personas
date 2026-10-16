# Prax Teach v2: visual intuition revision

Status: DRAFT FOR APPROVAL. This document specifies a revision of the existing general teaching skill. It is not an implementation or a new lesson. Review mode: SELECTIVE EXPANSION. Baseline commit: 286a98fc67486fa91bb19f34a9c0be347f5db029. Accepted user decisions are recorded in DECISIONS.md; research and limitations are in RESEARCH.md.

## Outcome and boundaries

The skill should turn an unfamiliar idea into an accurate, concrete mental model through connected visual explanation, across subjects, learners and supported hosts. The learner should be able to see the relevant relationships and why the conclusion follows. Actual ability remains unknown until the learner provides evidence; no compulsory assessment is required to receive teaching.

Keep the existing skill identity, engine, visualization capabilities and consent safeguards. The user-approved public experience changes substantially: visual explanation comes first, complete delivery is the default, and practice is optional. Neither a new application nor an artificial-neuron lesson is the deliverable. That topic is one public development example only.

## 1. Teaching policy

Request overrides take precedence: concise/direct answer, layered delivery, diagnosis-first, exploration-first, a requested medium, accessibility needs, separate prerequisite lessons, or a selected teaching style. Ordinary task completion must not trigger a lesson.

For an unqualified teaching request:
1. Infer a useful starting level and bounded outcome from the request. Ask only when missing context materially changes the explanation.
2. Offer local state persistence when no applicable consent exists; declining or not answering does not block ephemeral teaching. No learner-state writes without affirmative consent. Lesson artifacts are saved in lessons/ by default even when tracking is declined; explain the distinction. An explicit save-nothing request forbids durable lesson files too: use host delivery or a temporary preview only if it can actually be removed, and disclose host storage limits rather than promising erasure. Existing active consent permits automatic resume within the same directory and scope. Briefly state the actually recovered topic/position, then let the learner continue, change topics or start fresh without a mandatory assessment.
3. Plan a concrete anchor and connected visual story. Expose relevant entities, relationships, intermediate changes and why each transition follows. Introduce prerequisites where they are needed.
4. Intelligently select representations and tools; build the complete bounded lesson before delivery. Completeness does not mean an entire subject or an unbounded course in one artifact.
5. When it adds understanding, include a meaningful contrasting case and connect the visual to formal terms, code, equations or argument. Do not pad the lesson with a contrast that serves no purpose. State where analogies stop being accurate. Historical interpretation or literary meaning must not be falsely presented as a deterministic physical mechanism.
6. Inspect the explanatory content and actual delivery as capabilities permit. Repair observed errors; label unperformed checks honestly.
7. Deliver the whole explanation without mandatory prediction, quiz or teach-back barriers. Offer at most one optional intuition check, then follow the learner's next request.
8. On confusion, change a likely missing connection immediately; ask one focused question first when plausible gaps differ. If a retry does not resolve confusion, locate the remaining gap rather than repeatedly paraphrasing or restarting.

The teaching sequence is configurable, not a fixed learner classification. Remember explicit preferences only with consent. Temporary adaptation is not a durable trait inference.

## 2. Visual explanation contract

Each scene must answer a relevant question and explain its relationship to adjacent scenes. Require enough context to interpret it, accurate labels, and a clear account of what changes or what relationship matters. Use consistent identities, units and notation across views. A scene may be static; a complete story may combine several media.

Select diagrams for structure/relationships, plots for quantities, animation for meaningful transformation/timing, and interaction for an interpretable change in modeled conditions. Use native model/harness capabilities and available specialist tools. The registry is a reference, not an unconditional mandate to use a particular vendor or build interactive content first.

A control must do something that helps explain the subject and expose its effect. Provide meaningful pause/replay/step controls for animations where applicable, a complete static equivalent, keyboard access and reduced-motion behavior. Do not encode essential meaning by color alone. Exact quantitative or technical relationships need deterministic representations rather than image-generation guesses.

No decorative media quota or universal fixed scene count. Do not add a new scene language or rendering framework. Reuse the packaged lab and renderers where they fit; use another available suitable capability where it serves the explanation better. Required inaccessible or unavailable tools must not silently become fabricated output.

Default delivery is complete. Explicit layered delivery changes the sequence, not the factual standard. If requested rich media cannot be produced after appropriate alternatives, disclose the limitation and deliver an accurate static explanation; if the requested medium is essential, pause instead. A fallback never counts as delivering the missing medium.

## 3. Directory state and continuity

    learning-directory/
      .prax-teach/
        MISSION.md
        RESOURCES.md
        state/                 existing private runtime state
          learner.json         existing consent/goal record
          sessions.jsonl       actual learning evidence only
          ...                  existing projections and reviews
          continuity.json      proposed optional, versioned record
      lessons/                 learner-facing explanatory artifacts

Use .prax-teach as the existing runtime workspace. Retain its state/ subdirectory rather than rewriting secure I/O, locks and transaction semantics. Empty internal artifact directories made by the initializer are harmless; removing them is not a requirement. Do not precreate the workspace before the consented initializer.

Existing state locations and schema/event identifiers remain unchanged. Do not relocate or silently migrate a learner's directory. Automatic resume requires valid state and active consent; successful show_state inspection alone is insufficient because inspection is allowed after withdrawal.

### Continuity record

The runtime currently rejects extra fields in learner.json. Add a separate optional continuity record and bounded CLI operations using existing anchored reads/writes and workspace locks. It is not another evidence database.

Proposed contents: independent schema version; explicit preference key/value records with user-stated provenance; bounded covered-topic list; last lesson identifier and learner-visible position; concise agent-authored continuation summary explicitly labeled as such; learner-requested next topic when present. Keep generated summaries separate from verbatim learner statements. Do not store raw transcripts, sensitive traits, keys, diagnoses or inferred learning styles.

Existing broad persistence consent does not silently authorize new categories: new-directory consent names preferences and continuity explicitly. Existing-directory users are offered this additional scope before continuity writes; offer at most once in the current session after a refusal. Do not persist a refusal without permission merely to suppress future prompts. Represent that grant as explicit versioned extension consent in the continuity record. Base active consent and extension consent must both be present for reads used to personalize teaching or updates; explicit inspect/export/delete controls remain available after withdrawal. No absent record is synthesized as a write during resume. Extension-only withdrawal keeps inspect/export/delete available but stops personalizing from or updating continuity content. A reset deleting the whole continuity record also deletes its extension grant, so future writes require a new grant. A preference-only reset clears the selected preferences while retaining the explicitly granted scope. Regrant requires affirmative consent and active base consent; do not silently re-enable base persistence.

No optional practice means no scored observation and no review rating. Covered topics mean exposed material, not demonstrated competence. A changed preference must not rewrite historical evidence. Validate bounded field sizes and accepted preference keys; reject malformed input and unknown fields. Missing continuity is supported for legacy workspaces; malformed continuity is an error, not silently treated as absent.

Export and inspect include the optional record when present and valid. Full state deletion removes it. Preference/continuity-specific reset must preserve learning evidence unless the user explicitly asks to forget all progress. Forget-progress preserves sibling lessons; removing lessons requires a separate explicit request. Exports remain learner-state exports, not an implied complete course archive.

## 4. Policy and runtime alignment

Revise the primary skill, mode contract, teaching protocol, visualization router and applicable inherited handbook rules together. The public teach-pro-max wrapper must not reintroduce old behavior. Preserve the prax-teach-v2 identifier and teach-pro-max alias.

Update executable request routing so unqualified teaching requests select the complete-lesson policy, while explicit brevity and ordinary-task boundaries remain intact. Mode, teaching style, output medium and persistence are separate decisions. Do not equate a lesson with compulsory practice or consent to long-term storage.

Existing retrieval-answer protection remains required when the user chooses a quiz/assessment. Explanation-first content is not a failed retrieval task. Route it with retrieval disabled; the existing visual verifier already accepts that distinction. Do not disable checks globally or expose actual assessment answers in accessibility text or source files.

Prefer a narrow continuity module over expanding the large state.py for unrelated policy. Add only the hooks needed for consent, inspection, export and deletion. Avoid changes to existing event hashing, projections, scheduler algorithms, secure locks or transaction recovery.

## 5. Failure and recovery design

See ERROR-REVIEW.md for the observed exception map. Existing ConsentRequired, ConfirmationRequired, SafetyError, ValidationError and StateNotFound remain visible; OSError/UnicodeError do not become silent success. Cleanup catches that close descriptors and re-raise are intentional.

    request -> validate -> plan -> render -> inspect -> deliver
       |          |          |        |         |
    missing    invalid    missing  tool error  bad semantics
       |          |          |        |         |
    ask topic   explain   use valid alternative / bounded repair
                         essential medium unavailable -> pause
                         otherwise -> honest static equivalent

    state root -> secure load -> active consent -> continuation/evidence
       |             |              |
    absent        unsafe/corrupt   withdrawn
       |             |              |
    offer setup   no writes       ephemeral teaching

No unbounded retries. During lesson production, at most two repair attempts for the same failed artifact/tool path before selecting a supported alternative or reporting the boundary. This is a runtime default, not a limit on learner-requested clarification. No success or learning claim is inferred from a tool exit code alone.

## 6. Security and data flow

No new remote service, account, telemetry or credentials. State remains directory-scoped and private. Never send saved learner records to an external visualization provider merely because it is available. Pass the minimum concept/model data required for the authorized visual. Treat web pages, source documents and imported files as untrusted evidence, not instructions to alter host settings or consent.

Continuity uses existing no-symlink/no-hardlink, private-mode and descriptor-anchoring defenses. The new optional file needs the same validations as existing state files, including export and deletion paths. On concurrent updates, validate the prior revision under the lock and reject stale updates rather than overwrite a newer preference. Atomic replacement prevents partial JSON writes. No multi-file continuity transaction is needed because it does not change evidence files.

A new directory requires affirmative consent. An empty existing directory is not permission to initialize over it. Corrupt state is preserved for diagnosis. Logging records operation and sanitized error, not private response contents or tokens.

## 7. Verification design

Separate five questions: package integrity, runtime correctness, agent policy adherence, explanatory visual quality, and actual human learning. Only the first four are in this engineering revision. No claim that people learn better or remember longer without separate learner evidence.

Protect existing consent, withdrawal, correction, export, deletion, path containment, event hashing and factual honesty behavior. Keep tests for those protections unchanged except where a separately approved additive schema case genuinely requires new fixtures. Historical attempt-first policy tests are incompatible with the approved direction: preserve their history, identify them explicitly and introduce versioned new-policy tests. Do not relabel their prior results as evidence for the revision.

    runtime changes -> unit + CLI integration/security regression
    instruction changes -> fresh-context baseline/candidate behavior comparisons
    visual behavior -> render/control inspection on actual representative artifacts
    host portability -> real available-host smoke checks, not universal claims

Public development examples include the beginner neuron-to-LLM journey, a physical mechanism, a mathematical relationship, a historical interpretation and a language concept. Use novice/expert, concise, no-consent, resume, reduced-motion and tool-limited conditions. Test that the same skill generalizes without embedding a neural-network-specific lesson generator.

The proposed scoring matrix, protected invariants, six unseen scenario families, paired-run count, acceptance thresholds, supported-runtime requirements and stop rules are specified in EVALUATION-CONTRACT-v1.md. Approve and freeze that document before candidate edits. The evaluator setup is a separate phase; candidate workers cannot modify or inspect its sealed bank. Human-learning superiority remains outside scope.

## 8. Performance and inspection

First constraints are model context, media generation time and browser inspection, not server throughput. No measured p99 exists and none is invented. Read the short policy first and retrieve relevant production guidance on demand; avoid mandatory complete ingestion of unrelated tool handbooks for every visual.

Complete delivery means a bounded learning objective with navigable scenes, not simultaneous autoplay or a huge monolithic display. Reuse content only when its source/version and visual model remain valid. Expensive or unavailable external capabilities must not prevent ordinary direct answers. No new cache service, background daemon or dashboard is justified.

Record tool/version, artifact hashes and actual inspection scope alongside generated outputs when artifacts are requested. Do not create files solely to demonstrate activity. Inspection should expose broken labels, impossible states, empty outputs and controls whose numeric/model effect disagrees with the explanation.

## 9. Deployment and rollback

    approved spec + separately frozen evaluator
      -> isolated candidate checkout
      -> focused checks -> full applicable checks -> independent review
      -> regenerate current manifests -> version candidate and retain baseline
      -> update shared installed source/links -> fresh-session probes

    failure before promotion -> retain installed baseline
    regression after promotion -> restore previous source/link targets
                              -> validate manifest and host paths

Never edit the active installed source during development: all recovered clients currently resolve to shared files. Use a separate worktree/checkout and keep original dirty work untouched. Persist the exact previous symlink targets before promotion. Do not migrate learner state as a release side effect. Historical evidence and archives are immutable. Regenerated manifests certify bytes, not educational efficacy.

Proposed implementation bounds: at most two candidate revisions, 120 minutes elapsed from the first candidate edit through evaluation per approved run, no paid API purchase or new subscription, and stop after two no-gain candidates or any budget limit. Pause for a revised human-approved run contract if work cannot fit; do not lower acceptance gates. Exact evaluator and mutable-path lists are frozen before the candidate run.

## 10. Review coverage and implementation tasks

| Section | Finding / conclusion | Required work |
|---|---|---|
| Architecture | Reuse runtime under .prax-teach; policy and runtime must agree | T1, T2 |
| Errors | Typed errors already fail visibly; new continuity/media boundaries need explicit handling | T3, T4 |
| Security | Optional state file must retain existing containment and consent defenses | T3 |
| Data/interaction | Skipped checks cannot become mastery; stale continuity updates must not overwrite newer state | T3, T5 |
| Code quality | Old behavior is repeated in several normative references; state.py is already large | T1, narrow T3 module |
| Tests | Old attempt-first gates conflict; separate new policy and protected regressions | T5 |
| Performance | Full-handbook reads and unbounded generation risk delay/context overload | T1, T4 |
| Observability | Route selection is not proof of rendered correctness or human understanding | T4, T5 |
| Deployment | Shared symlink sources make in-place editing immediately affect multiple clients | T6 |
| Long-term | Stable identity and versioned additive continuity avoid unnecessary migrations | T3, T6 |
| Design/UX | Complete delivery must retain navigation, pacing and static/access alternatives | T4, T5 |

- T1: Align teaching policy and all normative references with accepted behavior; remove conflicting mandatory gates from explanation-first mode only.
- T2: Update request routing and public wrapper consistency; keep ordinary-task and explicit brevity behavior.
- T3: Implement optional versioned continuity with consent, safe CLI updates, stale-write protection, inspect/export/reset/delete integration, and legacy absence support.
- T4: Update visual production and checking guidance for purposeful scenes, contrast, formal bridges, clarification and honest fallback. Reuse existing rendering facilities.
- T5: Freeze new evaluation contract separately; add focused tests, retain protected regressions, and run fresh-context comparison and representative actual-delivery checks.
- T6: Validate package, retain historical receipts, update current manifests only after gates pass, version candidate, then deploy reversibly and smoke-check installed paths.

## Not in scope

New application, cloud backend, account system, subscriptions, universal media framework, automatic course migration, complete-course export, neural-network lesson as a product deliverable, optimizer loop, changing human-owned identity policy, or claims of superior human learning. No additional feature proposals remain pending.

## What already exists and future direction

Reuse consented state and journal recovery, scheduler, renderer, visual lab, capability registry, export/deletion controls, artifact validation and package verification. The revision changes how these serve teaching; it does not rebuild them.

Current: inspectable tutoring with mandatory attempt-first gates. Revision: a general visual-intuition skill with optional practice and truthful continuity. Longer-term ideal: reliable cross-host, cross-subject teaching with separately gathered learner-outcome evidence. This release does not claim that ideal has been demonstrated.

## GSTACK REVIEW REPORT

| Review | Runs | Status | Findings |
|---|---:|---|---|
| CEO review | 1 | Awaiting approval | Four accepted expansions; lifecycle decisions resolved; concrete design and evaluation contract ready |
| Independent design review | 2 | No remaining design blockers | Seven initial concerns resolved in the proposal; no implementation or learner-outcome claim |
| Engineering execution | 0 | Not started | Installed baseline unchanged |

VERDICT: Design proposal only; not cleared for implementation or deployment.

**UNRESOLVED DECISIONS:**
- Approve DESIGN-v1.md and EVALUATION-CONTRACT-v1.md; then freeze the independent evaluator setup before candidate implementation.
