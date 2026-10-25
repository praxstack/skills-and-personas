# Reading themes

Substantive teaching defaults to a complete HTML lesson. Explicit live tutoring,
live Q&A, quick questions and requested delivery formats take priority. Embed the
picker in reviewed authored HTML lessons and every local HTML course page:

```sh
# From the Teacher skill directory; in-place output is supported.
python3 scripts/embed_reading_themes.py lesson.html -o lesson.html
```

Python callers can import `embed_reading_themes(document: str) -> str` from
`scripts/embed_reading_themes.py`. Repeating it replaces its marked block with
current assets. Output contains its CSS, JavaScript and palette JSON, with no
sidecars, CDN, fonts to fetch or package dependency. Project output belongs in
the learner's project directory, not this skill. The feature is portable across
hosts that can open ordinary HTML and allow its inline CSS and scripts.

## Choosing a palette

**Reading theme** opens a native modal named **Reading themes**. Its labelled
Dark and Night groups contain five native radio cards each:

| Dark | Night |
| --- | --- |
| Graphite (`graphite`) | Midnight (`midnight`) |
| Slate (`slate`) | Amber (`amber`) |
| Forest (`forest`) | Ember (`ember`) |
| Mocha (`mocha`) | Moss (`moss`) |
| Indigo (`indigo`) | Plum (`plum`) |

Cards preview Aa and their name. Select one to apply immediately. Arrow keys
move between native radios; Tab moves through the modal's controls. Original
removes the custom palette and restores authored tokens and Board controls.
Done or Escape closes the modal and returns focus to its button. First load
retains the authored appearance unless the URL names a recognized palette.

Selection uses `?theme=<id>` only. It preserves other query parameters and the
hash, survives reload, and propagates to same-origin `.html`/`.htm` links,
including course links created later. External links, fragment-only links,
downloads and media/data URLs are untouched. Original removes that parameter.
No cookies, localStorage, sessionStorage, telemetry or network calls are used by
this feature. Existing lesson engines can have their own storage behavior.
A restrictive embedded browser can deny URL replacement; colors still change
but persistence then depends on the host permitting URL updates.

## Colors and typography

`assets/reading-themes/themes.json` is the palette source. All ten initial
six-token palettes retain their specified hex values. Tests measure normal
text, muted text and link accents at a minimum 4.5:1 against both page and panel;
control/figure borders reach 3:1. Semantic blue, coral red and green retain their
meaning independently of the link accent. Night blue is `#adc7e6`. Model colors
are therefore still distinguishable on Amber and other warm palettes.

The mapper covers notebook/course paper, panel, card, wash, ink, muted, graphite,
rules/line, accent, semantic colors and soft fills, on-blue text, focus,
highlight, grid, margin, shadow and stroke-grain tokens. Exported note, readable
caption and current-chapter surfaces use the mapped wash, including light print
colors. Inline SVG using these tokens inherits them without changing paths,
coordinates, labels or geometry.
Grid/margin decoration and chalk grain become transparent/disabled. Rendered
video, canvas, raster and externally loaded image pixels keep their original
colors; the picker states this limit. Hard-coded authored colors must be
reviewed and mapped by the author; the injector does not rewrite arbitrary CSS.

Authored fonts, type sizes, spacing, diagrams and media remain intact. Picker
text uses the system font; its cards are at least 44px tall and native inputs
are 24px. At 390px the cards form two columns within the viewport. The feature
has no motion and respects reduced-motion preferences. Print mode replaces
custom colors with readable light colors and hides the picker.

## Trust, CSP and verification

This is an injector for **reviewed authored HTML, not a sanitizer**. Review the
lesson's existing scripts before opening it. It does not execute lesson code
while embedding, fetch resources, inline images/SVG or evaluate code. Existing
CSP directives and charset metadata stay ahead of the injected block. A host
that blocks inline scripts/styles continues to block them; never loosen a CSP
for the picker. Injection follows CSP metadata even if that means it cannot run
before an unusually early authored lesson script.

`window.__readingThemes` exposes frozen `palettes`, a read-only `current` getter
(`null` for Original), and `apply(id)` for authorized lesson controls or tests.
Unknown IDs throw. CSS custom-theme tokens take priority over later Board setup;
reset removes the custom attribute, exposing the current original Board state.
Only the notebook's exact known Board-button title selector is hidden.

Run the scoped tests without installing dependencies:

```sh
python3 scripts/tests/test_reading_themes.py -v
node scripts/tests/test_reading_themes_browser.mjs
```

The browser test uses the provisioned Playwright loader from `skills/visual-qa`.
Inspect the actual delivered page at desktop/mobile sizes, all palettes, system
light/dark settings, keyboard navigation, reload and course navigation. Automated
contrast and bounds checks support these observations; they do not establish
field accessibility conformance or learner outcomes.
