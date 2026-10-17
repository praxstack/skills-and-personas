# Task 2 implementation report

Implemented against method base `1a77b4c4a006b3cbe718c5c80639e0a04db4c80e` after the exclusive candidate start succeeded at `2026-10-17T14:13:40.288050+00:00`. Absolute deadline remains `2026-10-17T20:13:40.288050+00:00`; no clock reset. Installation and acceptance remain parent responsibilities.

## Result

The normative teaching documents now specify general cross-subject tool discovery, complete explanations with immediate whole-figure/finished-state access, consistent objects across media, optional replay/layers, learner style/medium changes, adaptation until satisfaction or chosen stop, and separate mastery evidence. Existing optional assessment protection and two-repair limits remain intact. Conceptual exploration no longer requires a practical performance objective or review horizon. Declining tracking preserves an ephemeral requested course; quick mode creates files only on an artifact request.

Course map, current explanation and reusable notes have separate purposes and optional links. The two focused references elaborate these rules without hiding core requirements. Save-nothing includes map, notes and lesson files. No learner schema, state implementation, historical evidence, sanitizer, publication boundary, method or hidden cases changed.

The renderer consumes `assets/askthemove-teaching.css` and embeds it in standalone output. Template version is `prax-teach-lesson/3.0.0`; parsing/sanitization renderer remains `prax-teach-markdown/2.2.0`. Exact default colors are paper `#fbfaf4`, ink `#171d29`, explanatory blue `#1f48ae` and correction red `#c92324`. Serif prose, monospace technical content and short semantic handwritten notes stay distinct. Quotations remain serif. Native `div role="note"` and the existing `aria-label` support coach notes and explicitly named corrections without changing the sanitizer. Dark, high-contrast, forced-color, reduced-motion and print rules retain complete content.

CSS SHA-256 is `839fa2c5f82278d49fa1591949c5ed44dbdb1974463be8eeb647f3d0a0563c9d`. The actual loaded bytes are bound in `presentation-sha256` metadata and visible page provenance, and deterministic `--check` compares the entire output. Fonts use local fallback families. No font assets, network requirements or package-relative output dependencies were added; exact branded fonts are not promised.

The runtime reference now accurately identifies Python floating point as the implemented browser lesson/binding. A small task-specific host-authored HTML/CSS/JS visual is explicitly supported for another subject after content/control/accessibility checks and real-browser inspection, with a complete canonical static companion. It does not inherit packaged verification and never passes scripts through sanitized Markdown. No app, new framework or universal generator was built.

## Executed checks

Node `22.23.3` via the already cached `npm exec --yes --package=node@22 -- node`:

- Full JS suite: **21 passed**. Includes all existing renderer sanitizer, decoded path, symlink publication, deterministic parity, unsupported attribute/media and Flint tests, plus actual HTML assertions for embedded CSS, exact semantic colors, CSS hash provenance, book/technical/coach voices, dark/contrast/reduced-motion rules, no script/network dependencies and byte parity after moving output with its source.
- Existing Python visual-verification suite: **7 passed** with Node22 on PATH. This exercises route/fallback shape, exact companion verification and existing textual answer/asset protections.
- Exactly **36 frozen current companions** regenerated and byte-checked with `SOURCE_DATE_EPOCH=1785844800`; historical companions were not rewritten. Parent must rerender any companion whose source another task changes later.
- External ratio example includes separate map, lesson and notes, a complete labeled static SVG, coach note and correction. Its actual source/HTML/route/rubric/SVG bytes passed `visual-verify`, then frozen receipt `--check`.
- `git diff --check` passes.

Logs and example: `/Users/prax/Developer/prax-teach-evaluation-20261016/completion-v3/product/presentation/`. Relevant files are `node-tests.log`, `visual-verification-tests.log`, `companions.log`, `example-visual-verification.log`, and `example/lesson.html` with linked map and notes.

A direct `validate_workspace.py` invocation on the standalone example failed because this package-wide validator requires `fixtures/visual-verification/manifest.json`. That attempt is retained in `example-validation.log`; no fixture was fabricated and no validator changed. The dedicated exact-byte visual verifier passed instead. No full package release/held-out acceptance or real-browser/assistive-technology/human-learning claim is made here. Parent owns independent rendered inspection and acceptance.

No known remaining contradictions in the owned mode/presentation instructions after the scoped replacements. No hidden evaluation cases, keys or outputs were inspected.
