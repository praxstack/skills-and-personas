# Fresh mechanism demonstrations

Two new first-party editable lessons were built/exported through the candidate canonical teacher. Authoring follows its complete SKILL.md and explorable/visual-qa guidance. Sources were reviewed/trusted before browser execution. No learner journal, provider API, package/model download or installed-release write occurred.

- `examples/teach-visual-candidate/merge-sort-stability/`: original identities, sorted contiguous halves, head comparison and output-prefix tracing; left/right tie-rule control supplies a concrete sorted-but-unstable counterexample. Model tests check stable identity order, ascending keys, no lost/duplicated identities and every emitted-prefix cursor sum.
- `examples/teach-visual-candidate/momentum/`: signed, common-scale momentum contributions within a named two-cart system, their sum and the equal final total. Four mass/velocity controls vary the shared velocity of an idealized sticking collision. All 1,296 slider-grid combinations satisfy momentum conservation and nonincreasing kinetic energy; known-case, cancellation and equal-velocity limits also pass. Collision timing/trajectory is intentionally not simulated.

Both explorers explain first, expose controls immediately, have one optional practice check after teaching, and default persistence off. The canonical exporter also produced complete JavaScript-free static lessons, responsive desktop/mobile editable SVG figures, still SVG/PNG, optional Q&A/cards, provenance and manifests. Bundles stay offline; citations are optional outbound reference links. Medium choice: tracing and counterfactual parameter changes benefit from controls; static figures preserve complete explanation. No neural narration or narrated video was produced, and no listening/playback acceptance is claimed. The built-in silent scrubbable Film is an optional view of the same model, not a narrated-media substitute. Task 1's playback failure remains outside this work.

## Verification and inspection

Commands use `source /Users/prax/.local/share/prax-teach/runtime/v3/env.sh`.

```
python3 skills/teacher/scripts/find_tool.py --inventory
python3 skills/teacher/skills/explorable/scripts/build.py <source> -o <lesson>/explorer.html
node skills/teacher/skills/explorable/scripts/test_lesson.mjs <lesson>/explorer.html
node skills/teacher/skills/visual-qa/scripts/check_page.mjs <lesson>/explorer.html --out <plan>/task-3-evidence/<name>-shots --eval 'window.__explorable.check()' --all-steps
node skills/teacher/skills/explorable/scripts/bundle_lesson.mjs <lesson>/explorer.html --out <lesson>/bundle
node docs/teach-finish-20261024/quality/verify-offline.mjs
```

Browser regression: merge 44/44, momentum 45/45. Visual QA: all six desktop/phone, light/dark/reduced-motion configurations clean for each, with all-step captures. The focused offline check operates a genuine range control at both widths, verifies actual parameter updates/model checks, captures figures, checks no external requests and no stored state, and loads both static companions with JavaScript disabled. Static figures use external local SVG `<picture>` resources, not inline SVG; the verification was corrected to inspect that actual format. No engine/evaluator was changed.

Raw screenshots/logs remain at `.superpowers/sdd/PLAN/task-3-evidence/`. Personally opened and inspected: merge-shots/desktop-light-step-3.png, merge-shots/phone-light-step-4.png, momentum-shots/desktop-light.png, momentum-shots/phone-light-step-3.png; plus focused `inspection/merge-sort-stability-390.png`, `inspection/momentum-390.png`, `inspection/installed-v3.0.1-merge-1280.png`, and `inspection/original-accepted-merge-390.png`. Labels, identity sequences, signed directions, shared zero, equal-total bars and mobile reflow were readable and consistent with the claims. Static mobile captures are also in inspection/ for controller review. Screenshots are raw project evidence, not skill-distribution content.

## Original / installed comparison

The **same new merge source** was built using the original accepted engine at `/Users/prax/.local/share/prax-teach/releases/v3-0d20ff7/teacher/skills/explorable/scripts/build.py` and installed v3.0.1 at `/Users/prax/.local/share/prax-teach/releases/v3.0.1-33cfd55/teacher/skills/explorable/scripts/build.py`. Destinations are `task-3-evidence/original-accepted-merge.html` and `installed-v3.0.1-merge.html`, outside installed directories. Installed regression is 44/44; focused original/installed checks pass at desktop and phone with identical identity ordering and readable figure layout. Candidate, original and installed remain consistent with the accepted figure-led paper/semantic-color direction; no measured quality or human-learning improvement is inferred. These fresh authored demonstrations are not a holdout.

Verified authoritative provenance: Princeton Algorithms Merge and Mergesort documentation, and OpenStax University Physics 9.4 Types of Collisions, browsed during this task. Model values come from executable arithmetic; hypothetical examples and closed-system assumptions are stated on every exported format.

Artifact SHA-256 values are in ARTIFACTS.sha256, outside the content whose bytes they attest to. This is source/render compatibility evidence, not release acceptance. Current portfolio findings and proposals are separate in ../portfolio/PROPOSAL.md.
