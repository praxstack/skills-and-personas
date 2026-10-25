# Reading-theme verification

Teacher 1.3.0 and Teach Pro Max 3.1.0 make HTML the default for substantive lessons and add a portable reading-theme helper to Teacher. The full paired installation exposes the new build path. Max's preserved standalone compatibility engine remains usable and does not contain this new helper.

The picker offers five dark palettes, Graphite, Slate, Forest, Mocha and Indigo, and five night palettes, Midnight, Amber, Ember, Moss and Plum. Original restores the page's previous presentation. Selection follows local HTML course links through a URL parameter, with no theme-owned browser storage, cookies or network requests. Video and image pixels retain their original colors; inline SVG uses the page palette.

## Executed checks

The capability and fixtures were checked at source commits `69a471b` and the standards-mode correction `65637d2`. Existing test sources and release gates were preserved.

- Seven Python tests passed, covering injection, byte-idempotence, in-place output, document/CSP/charset preservation, palette structure, token coverage and nine prolog/doctype cases.
- Real Chromium checked all ten palettes under both device color schemes, direct offline files, reload, URL/query/hash preservation, local and dynamic link propagation, inline SVG colors with unchanged path geometry, typography, native radio arrows, modal focus containment, Escape/Done focus return, reduced motion and 390px layout. Existing CSP blocking remained effective.
- Measured minimum text contrast was 7.465:1 against page and panel colors. Border contrast was at least 3.275:1; semantic diagram colors against their soft fills were at least 4.829:1. Initial palette values did not need adjustment.
- All ten desktop views and a phone view were inspected. Representative captures are below.
- Existing Teacher core tests passed, 74 tests with two optional site-fixture skips in the provisioned runtime. The unchanged distribution verifier matched all 759 embedded compatibility files. These checks do not hash or certify the entire new wrapper; release source manifests bind those bytes separately.

Run from the repository with provisioned Playwright/Chromium and the usual visual-QA environment:

```sh
python3 skills/teacher/scripts/tests/test_reading_themes.py -v
node skills/teacher/scripts/tests/test_reading_themes_browser.mjs /path/to/evidence
python3 skills/teacher/scripts/tests/test_teacher.py -v
python3 skills/teach-pro-max/scripts/verify_distribution.py
```

## Representative views

[Graphite desktop](images/graphite-desktop.png), [Amber desktop](images/amber-desktop.png), [Plum phone](images/plum-mobile.png).

## Scope

The helper is for reviewed authored HTML, not untrusted-content sanitization. It preserves CSP rather than weakening a blocking host policy. Hard-coded third-party styles and rendered media do not automatically adopt these colors. Course-specific integration and artifact checks belong with each generated course. Contrast and browser checks do not establish universal accessibility, subjective comfort or improved human learning.
