# Publication review round 3

Baseline primary: `bbbdf6b59653b81bc1d66a0dc3a098c50660edf5`; reviewed secondary: `18da13c2055c3828b9a17f8189926009cd2d542d`.
The exact final source commit is recorded by the secondary export manifest and
release handoff after this commit. All three new Codex P2 findings reproduce.
The changes preserve governing files, schemas, compatibility engine, limits,
original checks, user state and prior receipts.

| Comment | Reproduction and repair |
| --- | --- |
| 4368035097 | Explanation questions in explicit practice mode had no Show me action; empty or short responses could not reveal teaching or unlock Next. Add the same asked-to-be-shown attempt shape as choice/number: given null, right false, asked true. Explicit reveal saves no explanation response or coverage claims, and subsequent edits are not silently saved as an unaided response. Actual comparison still requires the existing minimum length in practice. Model explanation, hidden main explanation and Next all become available. Previously revealed steps restore without inventing an attempt. |
| 4368035102 | Inherited constructor/toString values became nonnumeric depths and disappeared from map, outline and notes. Use null-prototype dictionaries for lesson lookup, depth cache and map positions. Valid IDs are retained. Unknown dependency names no longer resolve through Object.prototype. Numeric dependency depths, insertion order within layers and existing cycle behavior are covered. Persistence and fixed view/status vocabularies are outside this layout repair. |
| 4368035105 | Direct replacement-string insertion expanded authored dollar replacement tokens. Return the complete fallback from a callback. The exported noscript contents now equal the complete style plus static body byte-for-byte, with $&, prefix, suffix, $$, numeric and named replacement tokens all retained. Escaped code text also survives in an actual JavaScript-disabled browser. |

## Evidence and scope

The focused baseline has 7 failures across 11 controls. The repaired source passes
all 15 focused browser controls on host Chromium 153 with external HTTP blocked.
The separate synthetic lesson and course fixtures use retained first-party seasons
source but do not edit it. Empty/short explicit reveals, actual step navigation,
asked evidence, a normal real response and default full teaching are observed.
A course with constructor, toString and valueOf retains all 3 map nodes, outline
rows and notes cards. No browser flags or isolation rule changed.

`node docs/teach-publish-20261024/review-round-3-controls.mjs` produces
[RED](round-3/browser-red.txt) and [GREEN](round-3/browser-green.txt).
The initial harness incorrectly tried to read the unexposed explained field from
the public test API; its [setup failure](round-3/browser-red-setup.txt) is retained.
The corrected controls inspect existing attempt/report evidence without expanding
the API. A unit harness expected a 39-character string that actually has 40;
correcting that expectation did not change product behavior.

Ordinary portable regressions are added to existing suites: explanation reveal
and layout depth/cycle behavior in test_teacher.py, literal fallback insertion in
bundle_templates.test.mjs. Their focused baseline failures are retained in
[layout RED](round-3/layout-red.txt) and [fallback RED](round-3/fallback-red.txt).

All seven existing portable commands plus their updated ordinary assertions pass;
[exact commands and outputs](round-3/portable-green.json) are recorded. Teacher
vendor verification has 0 problems, wrapper distribution matches 759 files, core
has 74 tests with 2 expected primary fixture skips, discovery has 8 tests, Manim
resolution has 9, safe-course has 9, and the three-module Node selection has 22.
The source repair passes git diff --check; raw test output keeps original whitespace.

These are native teacher repairs, so no vendored hash entry is rewritten. This
work does not establish fresh bounded narrated-media or human-learning results.
The root agent owns those release checks and remote operations. The second public
repository receives exact source blobs and modes with provenance outside the
copied skill trees.
