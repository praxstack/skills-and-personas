# Prax Visual Lab

The runtime is a separately versioned, zero-dependency ES-module/Web-Component package. Shared components are `prax-state-stepper`, `prax-parameter-lab`, `prax-compare-views`, `prax-hint-engine`, and `prax-receipt-panel`. Lesson specs are declarative JSON; pure domain modules provide exact transitions and structural graders. Every interactive lesson ships a semantic static sequence and print/no-script route.

The three first labs are Python floating point, legal Rubik's moves, and lost-update interleavings. Motion is optional and reduced motion removes transitions. Deliberate learner actions produce local receipts; parameter changes update the comparison and receipt through the shared session rather than an isolated control. No receipt is uploaded automatically. Imported receipts are untrusted input: action identifiers must belong to the lesson and observations and learner-authored evidence must remain objects. The floating-point Python and browser models are checked against one independently specified literal vector file.

The visual router treats this packaged runtime as the default direct delivery
surface only when an `interactive` or learner-controlled `motion` job binds to
an implemented lesson capability. An unbound job falls back to static. For
specialized charting, diagrams, generated imagery, 3D, animation, or video, the
agent selects an authorized equivalent capability from the current harness and
the bundled visualization registry. Static fallback is a resilience and
accessibility requirement, not the default replacement for a working rich
route.

The router promotes the packaged runtime only when its exact source, build,
manifest, tests, JSON contracts, routing policy, and verifier bindings match;
every bound input and ancestor must be a real path rather than a symlink. It
replays the verifier against current bytes and requires the stored receipt to
match that result, so mutable status fields cannot promote a forged runtime.
The network scan must pass, and the receipt must explicitly decline any
human-learning or field-accessibility claim.

Receipt import validates the exact public receipt shape, replays its declared
actions to reconstruct the current lesson state, and synchronizes the stepper,
hint engine, and receipt panel. The JSON schema defines transport shape; runtime
validation additionally enforces that static-fallback state IDs reference real
lesson states.

## Explanation-first use

Use these existing components only when their implemented domain and controls
serve the concept. Build and deliver the complete bounded explanation first;
practice and receipt transfer are optional. Explanation visuals use
`retrieval=false`; chosen quizzes retain answer-leakage protection in every
surface, including source and static alternatives. Controls must expose a
meaningful model effect with consistent identities, notation and units. Inspect
representative states against the explanation, and provide keyboard access,
reduced motion, pause/replay/step when applicable and a complete static equivalent.
There is no fixed scene quota or requirement to use this runtime before another
suitable available capability. Do not create a new rendering framework.

An unbound or unavailable rich route is not fabricated output. Try suitable
authorized alternatives, with at most two repair attempts on the same failed
artifact/tool path. Disclose the missing medium and use an accurate static
explanation unless the requested medium is essential, in which case pause.
Covered material and control receipts do not demonstrate competence; skipped
practice creates no scored observation or review rating.
