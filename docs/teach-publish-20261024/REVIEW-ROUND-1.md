# Publication review round 1

All four Codex P2 findings on `praxstack/skills#1` reproduce in the reviewed source.
The focused baseline has 14 failed assertions across 27 controls. The repaired
source passes 40 controls on host Chromium 153, including additional no-JavaScript
fallback and actual video advancement checks. This is supplemental product
verification; governing evaluators, historical fixtures, limits and receipts are
unchanged. Full bounded narrated regression remains a separate release check.

| Comment | Reproduction and repair |
| --- | --- |
| 4367933981 | Explicit practice displayed `.xp-say` before answering. Hide that explanation while the practice step is unresolved; reveal when the existing question resolution completes. An explicit CSS hidden rule is required because `.xp-say` uses grid. Default explanation remains visible. Correct-answer and Show me paths both reveal it. |
| 4367933993 | JavaScript-off native text tracks had no source under file and HTTP. The track now has a default data:text/vtt source containing the actual encoded VTT. CSP allows data media without permitting network connections. Scripted Blob replacement remains. Browser controls load genuine native cues and advance the retained real video with JavaScript on/off over both transports, without new browser flags. |
| 4367933995 | JSON/static projection dropped js/java/go/rust. Preserve all live keys and the existing javascript alias, render them escaped in static output and its explorer noscript fallback. The live panel also accepts that alias. |
| 4367933998 | Caption/narration text retained entity syntax. Strip markup first, then decode using inert template content. Operators, named/numeric entities, Unicode and paragraph spacing now match displayed text. Escaped markup stays text; a resource-markup control causes no request or execution. Export metadata text extraction also uses inert templates. |

`review-round-1-controls.mjs` builds a separate synthetic lesson from the retained
first-party seasons source. It does not edit that fixture. Initial harness attempts
needed correction for a literal closing script delimiter in generated executable
source and for Playwright text lookup inside noscript; the retained RED/GREEN
receipts use the corrected focused controls. Additional fallback/advancement checks
were added after reproduction, not substituted for the original failing checks.

The requested vendor record helper refuses `explorable` because it is one of the
six native skills, not a vendored entry. No vendor hash or helper rule was bypassed.
`vendor.py verify` still reports 0 problems. Native repair provenance is this Git
commit and this additive review record. Wrapper distribution verification passes
all 759 embedded files; the protected compatibility engine is unchanged.

## Python 3.11 CI repair

The primary CI import failure is separate: three backslash-containing joins inside
an f-string in `enhance_final_notes.py` need Python 3.12 syntax. Python 3.11.15
reproduced that SyntaxError. Hoisting those joins preserves formatting and fixes
both source and new-skills mirror. All 26 non-test modules in the import set now
compile under 3.11.15; all 5 parity/import/CLI tests pass. All 9 guide configurations
produce byte-identical output when comparing the old and repaired module under
Python 3.13.17. CI remains pinned to its original Python version.

The first local 3.11 parity run lacked requests. An offline install found no cached
requests 2.34.2, so a temporary `/tmp/teach-pr1-py311` environment installed that
pinned dependency normally. No permanent environment or dependency rule changed.

## Commands and receipts

- Scoped host environment: source the existing runtime `env.sh` and set
  `PYTHONDONTWRITEBYTECODE=1`; run `node docs/teach-publish-20261024/review-round-1-controls.mjs`.
  [RED](round-1/browser-red.json) / [GREEN](round-1/browser-green.json).
- `node --test skills/teacher/skills/explorable/scripts/bundle_templates.test.mjs skills/teacher/skills/explorable/scripts/report.test.mjs`:
  [16 tests pass](round-1/node-green.txt).
- Python 3.11 source/mirror compile: [baseline SyntaxError](round-1/python311-red.txt).
  `/tmp/teach-pr1-py311/bin/python scripts/test_portfolio_repair.py -v`:
  [5 tests pass](round-1/python311-green.txt).
- Teacher vendor verification: 16 vendored, 6 copied, 6 native, 0 problems.
  Wrapper distribution verification: 759 embedded files match.
- `git diff --check` passes for the repair.

No new subjective listening, learning, authored Manim rendering or sandbox
qualification claim follows from these host controls. The secondary repository
receives exact tracked teacher/wrapper bytes and modes from the resulting primary
commit, with an updated external provenance manifest.

The secondary full core rerun caught the existing Node-only formula-spacing
control needing no DOM. Entity-free text now avoids the decode parser entirely;
entity-containing browser text still uses the inert template. The assertion and
its expected formula spacing are unchanged. Full core and browser controls were
rerun after this integration correction before the final source freeze.
