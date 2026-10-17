# Default teaching aesthetics: AskTheMove / ChessLab

## Evidence

Inspected local ChessLab commit `7bef53b8e2a2bd23240da1f71bb2607f08cdd3ab`, clean working tree. Source: [site/DESIGN.md](/Users/prax/Developer/ChessLab/site/DESIGN.md), corroborated by `site/public/assets/app.css` and `askthemove/launch/video/askthemove/v2-project/source/brand.css`. No ChessLab files changed.

Exa fetched public [AskTheMove](https://askthemove.online/) text, including the annotated move walkthrough, counterfactual branch and separate evidence/explanation. Direct browser navigation failed with ERR_CONNECTION_REFUSED; this research does not claim a fresh live visual or interaction check.

The source defines a patient coach annotating printed material: Vollkorn for prose, Courier Prime for calculations/technical evidence, Kalam for short coach notes. Warm paper #fbfaf4, ink #171d29, explanatory blue #1f48ae and correction red #c92324. Meaning is also expressed in words. Diagrams stay crisp; coach arrows, circles and marks are drawn. Each mark must correspond to a stated claim. Motion is drawing/writing, not decorative looping; reduced motion shows the finished state. Back/Next/Replay and a counterfactual branch support learner control. These are source-design facts, not independently measured accessibility or learning outcomes.

## Proposed general teacher adaptation

User has requested this aesthetic by default. Treat the following as an implementation brief, not proof it has shipped.

- Default surface: warm whiteboard/notebook with strong contrast, uncluttered explanation and purposeful annotations. Keep optional ruling/margins faint; remove them when they compete with the subject.
- Three visual voices: readable prose, precise mathematics/code/data, brief handwritten coach annotations. Handwriting never replaces long text, equations or code.
- Draw causes before effects. Time an arrow, highlight or change in the model with the sentence explaining it. The learner can inspect the complete diagram immediately; animation never gates access to the whole story.
- Preserve the same objects and labels across static drawing, animation, manipulable model and narrated video. Changes in presentation should not require relearning a visual vocabulary.
- Controls manipulate real explanatory variables. Show the changed input, intermediate mechanism and consequence together, with a reset and meaningful comparison. A slider whose only effect is a cosmetic change does not qualify.
- Video uses the same causal storyboard, with captions, transcript and still/key-state equivalent when supported. Live drawing is a presentation style, not a claim that a human is teaching live.
- Course overview and durable notes remain separate from the teaching stage. Notes include assumptions, definitions, worked reasoning, unanswered questions and useful references rather than only a compressed summary.
- Fit the host: inline drawing when supported; self-contained HTML/SVG or video where supported; readable static sequence or text where richer rendering is unavailable. Report the actual fallback. Never promise every host can render every medium.
- Fonts can fall back to suitable locally available families. Exact assets require portable bundling and license checks. Avoid machine-specific absolute font paths.
- Learner accessibility and requested style override the default. Do not import the site's light-only constraint as a universal teaching restriction.

## Feasibility

The existing repository already demonstrates an implementation vocabulary (SVG paths, seeded pen strokes, text reveals, semantic styles and reusable brand styles for video). It provides a concrete starting point for this skill's generated artifacts. A harness-independent policy can select and explain the style; runtime capabilities determine which artifact can actually be produced and displayed. Best-tool discovery should remain dynamic, rather than hard-coding a vendor as universally best.

## Acceptance examples for a future implementation

A static diagram tells the complete bounded causal story. Its animation reveals the same mechanism without hiding prerequisites. Its interactive version lets a learner change a cause and see all dependent quantities update. Its video narrates the same states with usable pacing. Each has a readable non-animated explanation; tests check correctness and usability, not learner satisfaction by proxy.
