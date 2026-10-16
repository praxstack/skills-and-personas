# Architecture review: general visual teaching skill

Status: Section 1 reviewed; the user approved keeping lesson artifacts when forgetting progress. Sections 2-11 are not complete. No implementation changes.

## Scope and baseline
The approved scope is the existing general skill revision, SELECTIVE EXPANSION with four accepted additions. Source baseline: 286a98fc67486fa91bb19f34a9c0be347f5db029; package file hashes in BASELINE.json. Review documents are outside the package content they describe. No new application, renderer framework, provider subscription or example lesson is a deliverable.

## Architecture

Current:

    request -> SKILL.md + references -> runtime mode/visual routing
                                  |-> existing renderers/visual lab/tools
                                  |-> consented workspace/state engine

Proposed:

    learner request + explicit preferences + valid consented context
           |
           v
    coherent teaching policy (SKILL.md + supporting references)
           |                     |
           |                     +-> matching executable routing decisions
           v
    explanatory storyboard: concrete anchor, mechanism, connected scenes
           |-> useful contrast / formal bridge / prerequisite explanation
           v
    capability selection -> existing runtime or suitable available tool
           v
    factual + explanatory + actual-delivery checks
           v
    complete bounded lesson -> optional check -> learner-led continuation
           |                                      |
           +-> lesson artifacts                   +-> adaptive clarification
           +-> consented continuity and observed evidence (kept distinct)

No new independent teaching engine or vendor-bound runtime is proposed. Consistent policy in instructions, references and executable routing is required. Tools produce media; they do not choose a different pedagogy. The four accepted additions fit into explanation planning, continuation and checking rather than becoming separate applications.

## Concrete workspace reuse

    learning-directory/
      .prax-teach/              existing runtime workspace, private
        MISSION.md
        RESOURCES.md
        state/                 existing secure state format
          learner.json
          sessions.jsonl
          concepts.json
          misconceptions.json
          sources.json
          reviews.jsonl
      lessons/                 learner-facing artifacts, separately validated

The runtime already accepts an explicit workspace location, so .prax-teach/state is preferable to rewriting the engine to flatten files directly into .prax-teach. The existing initializer also creates empty internal lessons/assets/reference directories; do not interpret those as a second teaching workspace. Removing empty directories is not necessary for the product objective.

Existing directories remain at their original locations. Consent is location-bound; no automatic migration. New directories use the new convention after consent. Do not precreate .prax-teach: the initializer rejects an existing directory.

Evidence: scripts/praxteach/state.py initialize_workspace/_create_workspace_locked (186,216); scripts/praxteach/io.py prepare_new_workspace/secure_workspace (472,485); scripts/praxteach/cli.py workspace arguments (100 onward). Flattening state would affect anchored I/O, locks, transactions, scheduling, exports and deletion, not just naming.

## State and lifecycle

    absent -> offer persistence -> declined -> ephemeral teaching
                              -> accepted -> initialize exact directory
    existing -> validate location and files -> consent active -> resume
                                          -> withdrawn -> ephemeral teaching
                                          -> invalid -> report, no writes
    active -> record preferences/continuation separately from observations
           -> optional learner attempt -> observed evidence only
           -> learner requests withdrawal/deletion -> scoped operation

A successful state inspection does not itself authorize resumed tracking: show_state permits inspection after withdrawal. Check the consent flag explicitly. Skipping practice leaves performance unknown; content coverage must not become a fabricated observation or scheduler rating.

## Data flows and shadow paths

    request -> context -> explanation -> rendered artifact -> optional state

Happy: clear request, available tools, valid prior consent -> complete lesson and honest updates.
Missing: no topic -> ask for topic; no directory -> teach ephemerally, ask only when saving requires one.
Empty: empty request is rejected by routing (ValueError); empty history means new learner, not mastered or failed.
Error: corrupt/unsafe state -> stop state operations and disclose limitation; render failure -> preserve explanation and offer truthful available delivery, not invented animation.

    saved directory -> secure load -> consent -> continuation

Happy: validate resolved root, active scope and history -> resume.
Missing: absent root -> do not claim prior history; offer new consented setup.
Empty: initialized but no observations -> use goals/preferences, keep mastery unknown.
Error: location mismatch, symlink/hardlink or transaction conflict -> fail closed for writes; do not merge directories automatically.

    selected visual capability -> render -> inspect -> deliver

Happy: real output and consistent labels/controls -> deliver with actual inspection scope.
Missing: preferred tool absent -> inspect suitable equivalents, use meaningful supported fallback.
Empty: tool produces no artifact -> treat as failure; never report successful delivery.
Error: timeout or invalid/misleading output -> bounded repair or alternative; communicate any loss of requested capability.

## Coupling, scale and failure boundaries
Policy and routing must agree; editing only the frontmatter or primary prompt is insufficient. Learner-facing media remains independent of private state. Existing state locking is retained; there is no new network service or shared-user database.

At 10x lesson length, context consumption and rendering/inspection effort are first constraints. At 100x stored sessions, whole-history parsing/rebuild may dominate; no performance numbers have been measured here. Keep the requested lesson bounded and avoid loading unrelated transcripts or the entire tool library. Do not build new scaling infrastructure for this revision.

Single points of failure: host tool availability, model-generated explanation accuracy, installed package consistency, and state root validity. Mitigate with explicit capability checks, factual/explanatory review, versioned package verification, and existing fail-closed state handling. Multiple hosts share a skill source but should not concurrently rewrite its source during deployment.

Security: directory consent scopes learner writes; rendering receives explicit trusted roots. No new credentials or remote learner-data transport. Do not broaden path access or use symlinks to bypass the existing state guards. Domain documents and web content remain evidence, not operational authority.

## Export/deletion finding requiring a user-visible decision
Existing export_workspace includes MISSION.md, RESOURCES.md and state files; it does not include teaching artifacts. Full state deletion removes the runtime workspace. With sibling lessons, lesson artifacts survive. This preserves the existing state-engine boundary but must be explicit in user-facing commands. A combined portable course archive would require additional design and is not implicitly accepted scope.

Recommendation: keep state operations separate from lesson files. “Forget my progress” removes the scoped saved learning records; deleting lesson artifacts requires an explicit separate request. No deletion will be performed during this review.

## Rollback and release architecture

    unchanged baseline -> isolated candidate -> approved frozen checks
        -> package manifest regeneration -> inspection/review
        -> versioned release -> shared skill links -> fresh-session smoke

    failed candidate -> reject candidate -> retain current installed source
    bad deployed candidate -> restore prior versioned source/link -> verify paths

Historical receipts remain historical after any source change. A regenerated distribution manifest proves file consistency, not improved learning. Preserve names and event/schema identifiers unless a separately approved migration requires changes. Exact implementation budgets, holdout boundaries, acceptance thresholds and release commands belong in the approved run contract before editing the candidate.

## Resolved decision
The user selected preserving lesson artifacts when forgetting progress. Delete lesson artifacts only on an explicit separate request.
