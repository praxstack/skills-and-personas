# Reading themes — 25 October 2026

## Spec and global constraints

The user requested five dark and five night themes focused on readability/UI/UX, in the live GATE HTML course and in Teach Pro Max for future HTML lessons. Primary teaching remains HTML. This is a product change, not a governing release-test change. No existing release tests, identity policy, historical receipts, embedded compatibility engine, mathematical source, narrative media or unrelated skill body may be changed. Preserve the accepted baseline main b47380c and course f3966eb. Keep receipts outside the files they hash. No paid services, dependency downloads, learner journal or default storage writes. Stop after two no-gain repairs on the same failure or 120 minutes from 2026-10-25T11:08:00Z. Rollback: existing immutable installed releases and course source commit f3966eb; retain existing exports.

Use the existing isolated main worktree on feature branch feat/reading-themes-20261025. Teacher becomes 1.3.0 and Teach Pro Max 3.1.0 for the new feature; old versions remain intact. Other named local skill editions remain 1.2.0. Embedded Max compatibility distribution is protected. Existing YAML frontmatter and verification gates remain unchanged.

Design: retain the course's book/utility typography. Quiet, solid reading surfaces, strong text, semantic blue/red/green diagram colors, and a compact picker with ten Aa palette cards. Dark themes are lighter charcoal surfaces; night themes are deeper surfaces with warmer text. No decorative animation, CSS inversion of figures or health/learning claims. Main text must have >=7:1 contrast against background and panel, secondary text >=4.5:1, and diagram blue/red/green >=3:1. Do not trade readable text for dimness. Rounded values or foreground colors cannot change mathematical meaning.

## Task 1: Reusable reading-theme capability and skill instructions

Ownership: only skills/teacher/assets/reading-themes/{themes.json,themes.css,themes.js}, skills/teacher/scripts/embed_reading_themes.py, skills/teacher/references/READING-THEMES.md, skills/teacher/scripts/tests/test_reading_themes.py, a focused browser test under skills/teacher/scripts/tests/, skills/teacher/SKILL.md and skills/teach-pro-max/SKILL.md. You are not alone in the codebase; preserve all unrelated edits. No subagents.

Implement a self-contained, dependency-free theme injector. Public Python interface `embed_reading_themes(document: str) -> str`; CLI `python3 scripts/embed_reading_themes.py input.html -o output.html`. Embedded CSS/JS/JSON require no sidecar/network. Idempotently inject marked blocks. Do not automatically execute or inline untrusted SVG/images. The injector is for reviewed authored HTML, not a sanitizer, and must say so. A CSP-blocked host remains blocked; never loosen existing CSP or eval code.

Theme names/IDs: Dark: Graphite/graphite, Slate/slate, Forest/forest, Mocha/mocha, Indigo/indigo. Night: Midnight/midnight, Amber/amber, Ember/ember, Moss/moss, Plum/plum. Add an Original reset, not an eleventh custom palette.

Suggested exact initial palette tokens (bg,panel,ink,muted,accent,border); adjust only when measured contrast fails, recording the reason:
- graphite: #202328,#292d33,#eef0ee,#bdc5cd,#9ecbff,#74818f
- slate: #1d2834,#263340,#edf1f5,#b8c7d6,#9cccf4,#70869c
- forest: #1e2b25,#28372f,#edf1e8,#becdc0,#a9d3ed,#74877b
- mocha: #2b2421,#372e29,#f4ede3,#d3c1b2,#c2d3f3,#938173
- indigo: #242539,#2f3047,#eeedf5,#c5c3db,#b9ccff,#8383a2
- midnight: #0e1219,#161c26,#d5dde6,#a6b3c4,#99bbdf,#627186
- amber: #17130d,#221d14,#e5d4b7,#c5b192,#debf88,#8a785d
- ember: #1b1111,#291b1a,#e8cebf,#c9aaa2,#d9b8a0,#8d706a
- moss: #101811,#19231b,#d6dfcb,#afc0a8,#b9cea6,#6e826b
- plum: #17121d,#221c2b,#ded3e4,#bfb0ca,#c7b7df,#806f8b

Model --blue must remain visibly blue (use #adc7e6 on night palettes), --red coral and --green green, even when the link accent is amber. Map the notebook/course tokens --paper,--paper-2,--card,--ink,--ink-2,--graphite,--graphite-2,--rule,--rule-soft,--line,--muted,--accent,--blue,--red,--green,--*-soft,--on-blue,--focus,--highlight,--grid,--margin,--shadow,--stroke-grain. Disable decorative page grid/margin/chalk grain on custom themes while preserving meaningful plotted geometry. Inline SVG uses inherited tokens. Rendered video pixels keep original colors; say so briefly in the picker. Original restores original theme tokens and board controls. Custom themes replace the old Board control (hide its known title selector only while custom active). Printing uses readable light colors.

Use a compact Reading theme button and native modal dialog named Reading themes, two labelled groups Dark/Night of five native radio cards, Original reset and Done/Close. Cards show Aa and name, proper selected/focus states, >=44px card hit area, visible >=24px native inputs, no horizontal overflow at 390px. ESC closes, focus returns, arrows work, reduced-motion respected. On first load no custom theme is forced. Selection applies live, persists in URL `?theme=<id>`, propagates to same-origin local HTML course links, and survives reload. No cookies, localStorage, sessionStorage or network. URL parameters other than theme and hashes must be preserved. Never change external source links or media data URLs. Apply tokens early to prevent flashes; initializing before the lesson engine must not be undone by board setup. Expose `window.__readingThemes` with read-only palette information/current selection and an apply method for authorized page controls/tests.

Update Teacher visible version to 1.3.0; add Max visible version 3.1.0. Document HTML lessons as the substantive default (honor explicit live tutoring/quick-question requests), include picker guidance and the local embedding command. Correct Max's ordinary host-conversation default to substantive HTML delivery, retaining explicitly requested live Q&A and consent rules. All this is authorized product direction; never edit embedded fallback files or historical evaluator/gate source. Add concise reference documenting themes, limits, typography/contrast, embedding and portable/offline behavior.

Verify meaningful Python injection/idempotence/contrast tests and actual Chromium fixture with every palette, device scheme overrides, URL propagation/reload, default zero storage, keyboard/modal behavior, and mobile bounds. Use already provisioned runtime: `source /Users/prax/.local/share/prax-teach/runtime/v3/env.sh`; Playwright loader is available from canonical Teacher visual-qa/scripts/pw.mjs. No installs. Run existing core teacher/distribution tests when relevant and report exact outcomes. Commit task files, self-review, report status and evidence in this plan's Task 1 report.

## Task 2: Integrate into the live portable HTML course

Ownership: /Users/prax/Developer/GateDA2027/Section 2: Linear Algebra tools/build_embedded_html.py, tools/verify_embedded_html.mjs, a new focused theme browser test, README.md, generated primary HTML and evidence. You are not alone; preserve all unrelated edits. No subagents.

Consume the Task 1 embed_reading_themes(document) interface from the reviewed source worktree until installed; after activation use the canonical installed Teacher helper. Embed the component into course index, all twenty primary lessons, HTML study reference and coverage/practice guide. Keep all source/media bytes and original bundled exports unchanged. Preserve per-lesson standalone/offline behavior and no-JavaScript full reading.

Static SVG figures currently are data-URI images with cached light-theme paint. Convert reviewed authored SVG pictures to inline wide/narrow SVG pairs so theme variables reach them; preserve every coordinate, label, dimension and semantic fill/stroke attribute, removing only cached inline color/fill/stroke declarations that shadow the semantic vars. Preserve font sizes and all meaningful geometry. Reject active SVG (script/foreignObject/external references) rather than injecting arbitrary content. Author input is trusted reviewed course output. Generic theme injector must not acquire implicit active-SVG conversion. Match desktop/mobile variants and accessible titles. Update the image-specific no-JS check to meaningful inline-SVG equivalent; no other previous check is relaxed.

Run full portable delivery checks (existing video/audio bytes, actual playback/captions/chapters/handoff, no default storage, no-JS reading and figures, zero required external resources) after rebuild. Add a focused theme check: all 10 choices on desktop and phone, real computed contrast, inline model/static diagram colors, original reset, URL propagation through another lesson and back home, reload, no storage, keyboard ESC/focus, and theme persistence without enabling progress. Check all twenty sources retain exact models/media and theme component presence. Run existing six-profile visual QA on representative new UI, inspect actual screenshots and dialog at phone/desktop. Open a new Chrome preview rather than overwrite the learner's current page, leaving a usable theme picker available. Commit source changes locally and write evidence outside hashed content.

## Task 3: Review, publish and install

Controller ownership: version catalog/readme release docs, portable public mirror, PRs/review responses/merge/release, exact-source staging and canonical alias activation. Prior user authorization for both public repositories and local/GitHub main merges persists. Do not publish the GATE course, private repositories or local-only third-party bodies. Preserve historical version catalog as history; add a current-version catalog for Teacher 1.3.0 + Max 3.1.0 and other 1.2.0 names. Record source provenance rather than fabricating hashes or telemetry.

After task reviews and final whole-branch review, push PRs to praxstack/skills-and-personas and praxstack/skills, address reviews, require unchanged relevant checks on exact heads, merge and synchronize local main. Build deterministic paired release archives from exact merged source, verify downloaded bytes before public release. Stage immutable new release; repoint existing canonical Teacher/Max and their client aliases, retain rollback. Existing bundled helper aliases should follow new Teacher when their entry bytes are identical. Verify no unrelated binding changed. Genuine CLI install can be checked once; no fabricated installs/counters. skills.sh previews may remain an external cache limitation; report current evidence honestly.
