# Bounded wrapper integration review

**Conclusion: the previously identified general/embedded authority conflicts are resolved at source `0d20ff7722910d12256240af0897070255cfc4f3`.** No new broken paths were found. One pre-existing bare-path ambiguity remains as a non-blocking clarity note below. The authored video fallback colors exceed the requested strict 4.5:1 threshold.

This is a read-only source and focused stylesheet/path review, not a governing change, private evaluation, full regression rerun or acceptance of every teaching outcome. Only this public report and its receipts were written.

## Authority and behavior

| Previously conflicting instruction | Current evidence | Result |
| --- | --- | --- |
| Embedded router/Visual Lab imposed on general teaching | `skills/teach-pro-max/SKILL.md:20–22,107` names sibling teacher as general authority and restricts embedded routing/registry/Visual Lab to explicit compatibility operations. This agrees with `skills/teacher/SKILL.md:57–95`. | Resolved |
| HyperFrames/Manim mandate and blanket specialist-engine bans | Wrapper `:115` follows the sibling narration/export path or suitable specialist engine; embedded versions/restrictions apply only to explicit compatibility work. Teacher `:68,75,95,159` retains its general routes. | Resolved |
| Durable generated lessons forced through the embedded renderer | Wrapper `:185` now selects sibling teacher's local build/export tools and scopes the preserved renderer to compatibility operations. | Resolved |
| Ordinary requested practice forced into embedded engine gates | Wrapper `:83` now follows the sibling teacher's explicitly requested practice style; `:48,119–124` retain explanation first unless practice is requested. This agrees with teacher `:30–33` and `references/STYLES.md:25–36`. | Resolved |
| Retrieval-leak rule could hide explanation-first static answers | Wrapper `:132` limits the leak restriction to unrevealed practice questions and explicitly retains explanations/answers in complete static fallbacks. Teacher artifact exports `:19–21` agree. | Resolved |
| Legacy PUBLIC-DISTRIBUTION called embedded teaching normative | The legacy document is unchanged. Wrapper `:22` now explicitly scopes its authority to the legacy component/explicit compatibility operations and keeps general teaching under the sibling teacher. Under that approved entry scope, its component-specific authority does not override the general base. | Resolved by scope; legacy bytes preserved |
| Closure could imply an assessment barrier | Wrapper `:250` explicitly honors “done” without an assessment barrier and separates observed evidence from unknown mastery. | Consistent |

The wrapper's “single complete teaching skill” phrasing at `:104–105` is an invocation/attachment promise in this context: `:107` explicitly says the sibling implementation is resolved directly. It no longer implies an independent competing teaching authority.

## Paths

All **16 relative Markdown links** in the two reviewed entry files resolve. The corrected teacher `:95` paths for `skills/explorable/scripts/build.py`, `skills/explorable/scripts/narrate.py` and `skills/explorable/scripts/bundle_lesson.mjs` exist relative to the teacher root. This was an existence/link check; these commands were not rerun during this audit.

Remaining clarity note: wrapper `:102` retains the bare code path `references/ARTIFACT-EXPORTS.md`. It exists relative to the sibling teacher named in that sentence, but not relative to the wrapper directory. It predates this commit and introduces no new broken Markdown link. An explicit `../teacher/references/ARTIFACT-EXPORTS.md` link would remove the relative-root ambiguity if a later wording cleanup is desired. No source edit was made here.

## Video fallback contrast

The actual exported stylesheet from `bundle_templates.mjs:6` sets the native video background to `#10181c`, text to `#f7f8f2`, and its fallback link rule to `#a5ead6`. Existing provisioned Chromium was used at **1440/390 px, light/dark**. All four combinations preserve these values:

| Authored fallback | Background | Contrast | Threshold |
| --- | --- | --- | --- |
| Text `#f7f8f2` | `#10181c` | **16.81:1** | 4.5:1 — PASS |
| Link `#a5ead6` | `#10181c` | **13.12:1** | 4.5:1 — PASS |

Method detail: video container background/text were read from computed styles. This video-capable browser does not render or compute styles for the native fallback child, so its matching **actual CSSOM `video a` rule** supplies the link color. Relative-luminance ratios were then calculated from those observed/declarative colors. This verifies the authored fallback palette; it does not certify native playback controls, rendering in a video-unsupported browser, arbitrary host overrides, field WCAG or every generated lesson. Earlier attempts to treat that unrendered child as a normal computed element returned empty styles; no contrast pass was inferred from those empty values.

## Source binding and limits

All four inspected files match the requested commit byte-for-byte. SHA-256 values:

| File | SHA-256 |
| --- | --- |
| `skills/teach-pro-max/SKILL.md` | `c14299670afc208e88210a2e6f91bb592020f65f6a45cad8dbb5e90702036685` |
| `skills/teacher/SKILL.md` | `3ac34e75072c1e18d82e395a7331807582eaa09319f47ba6534b60f879d83ed5` |
| `skills/teach-pro-max/references/PUBLIC-DISTRIBUTION.md` | `9f5bba47603130d3a79779a8fa1484a79c90af8377354a50485aa769a8d3c90e` |
| `skills/teacher/skills/explorable/scripts/bundle_templates.mjs` | `64e873c22fef0cac4ffa8c7c0c86e65b7e11d987d5b35c25fb86cc61be6df623` |

`source-and-paths.json` records the commit, hashes, link/path observations and retained ambiguity. `fallback-contrast.json` records each viewport/theme observation and the calculation method.

The preserved legacy document's standalone historical/global-installation statements were not revalidated as current deployment claims. The explicit entry scope is the reviewed integration boundary. No evaluator/private case, model CLI, provider/API, dependency installation, product edit, commit or push was used. This review does not replace final rendered artifact checks, user aesthetic acceptance or evidence of human learning.
