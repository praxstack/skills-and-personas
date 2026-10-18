# STYLE: themes, type and the still's visual gates

Source of truth: `ptk/templates/tokens.json`. Projectors ask for a colour by role (`t["note"]`) and for type by role (`svg.role("label", size)`). They never name a hex value or a font family; `tests/test_still.py::test_variants_and_sources` checks `still.py` for both.

## Two themes, one set of roles

- **Light** is the paper theme from WP0. Serif display and body (Source Serif 4), mono labels and code (JetBrains Mono), handwritten notes (Caveat), bordered cards.
- **Dark** is taken from the Neuron Atlas still Prax accepted (D20.1). Navy ground, a sans display and body, mono numbers. Lavender for the path and notes, coral for the correction, mint for output values. Panels sit on the ground with no fill or border, split by thin rules, the way Atlas splits its three panels.

| Role | Used for | Light | Dark | Atlas source |
|---|---|---|---|---|
| ground | page | `#fbfaf4` | `#101828` | ground `#101828` |
| surface | code panel | `#fffefa` | `#172136` | (Atlas has no cards; one step up from ground) |
| ink | primary text, executed code | `#171d29` | `#edf1f7` | ink `#edf1f7` |
| ink_soft | secondary prose, strings | `#3f4656` | `#c8d1df` | |
| label | section labels, provenance | `#596070` | `#aebbd0` | meta `#aebbd0` |
| faint | line and step numbers | `#6b7180` | `#8f9db6` | |
| rule | rules, dividers, card borders | `#857f70` | `#64738e` | `#3d4b62`, raised to reach 3:1 |
| note | path, notes, links, emphasis | `#183a94` | `#c4b5fd` | lavender `#c4b5fd` |
| note_tint | behind note text | `#e6ecfa` | `#262046` | |
| correction | "no break", wrong-belief marks | `#c0392b` | `#ea6a5e` | salmon `#ffaaa0`, darkened (see below) |
| correction_tint | behind correction text | `#fbecea` | `#371a24` | |
| value | captured output values | `#171d29` | `#93e6ce` | mint `#93e6ce` |
| highlight | executed code lines | `#dfe7fb` | `#262f50` | |

The WP0 names (`paper`, `card`, `blue`, `red`, `hl`, ...) still resolve through `aliases`, so the video and IVE projectors keep working until their packages move to role names.

Two Atlas values had to change, both for measured reasons:
- Atlas's lavender and salmon differ by 0.4 L*. A reader who can't tell the hues apart can't tell a note from a correction (V12 asks for 15). The correction moved to coral `#ea6a5e` (16.8 L* from lavender), which still reads as the salmon family.
- Atlas's rule `#3d4b62` is 2.0:1 on its ground. Rules need 3:1, so the dark rule is `#64738e`.

Light keeps its WP0 look. Its note and correction were only 5.7 L* apart, so the blue went a step darker (`#1f48ae` to `#183a94`) and the red a step lighter (`#b3261e` to `#c0392b`). They're now 16.9 L* apart and both still clear 4.5:1.

## Type roles

| Role | Light | Dark |
|---|---|---|
| kicker | mono 600, caps, tracked | sans 700, caps, tracked |
| display | serif 600 | sans 800, ×0.86 |
| body | serif 400 | sans 400, ×0.95 |
| caption | serif italic | sans 400, ×0.95 |
| label | mono 600, caps | sans 600, caps (Atlas's "MULTIPLY / SIGNED TERMS") |
| note | Caveat 600 | sans 600, ×0.8 |
| tag, code, foot | mono | mono |
| value | mono 600 | mono 500 (Atlas's big mono numbers) |

Sizes come from the layout (`LAYOUTS` in `still.py`); a role's `scale` adjusts them per theme.

## Fonts

Bundled OFL fonts only, from `assets/fonts/` (sha256 in `SHA256SUMS`, upstream URL and sha256 in `registry/tools.json`). Each artifact embeds a subset as a `data:` URI. Nothing is fetched at view time.

- **Source Serif 4**, **JetBrains Mono**, **Caveat**: as in WP0.
- **Nunito Sans** (OFL, google/fonts at commit `5571d84`) stands in for Atlas's Avenir Next, which is proprietary. Figtree, Nunito Sans and Mulish were set beside Avenir Next at Atlas's sizes. Nunito Sans was closest in width, x-height and figure shapes; Figtree ran narrow. The bundled file is instanced at `wdth=100 opsz=12 YTLC=500`, keeps the `wght` axis (300 to 900) and is subset to Latin, General Punctuation, arrows, `−` and `≤ ≥ ≠`. 28.7 KB.

Numerals: every `<text>` gets `font-variant-numeric: lining-nums tabular-nums` (`numeric` in tokens.json). Source Serif 4 has old-style figures available, so this matters. The other three draw lining figures by default.

Text measurement for wrapping uses the variable-font instance the browser draws: the requested weight, and `opsz` equal to the font size (Chrome's automatic optical sizing). Without that, small serif lines ran a space wider than measured.

## Math

A claim can hold inline TeX written `\( ... \)`. The still projector sends every formula in one batch to `node/tex2svg.mjs`, which runs MathJax 3.2.2 `tex2svg` (pinned in `node/package.json`, installed under `$PTK_STATE`). Each result goes into the figure as a scaled `<g data-math="mathjax-tex2svg">` of glyph paths, with `data-tex-sha256` and no TeX text. The alt text gets a plain reading (`\frac{3}{3}` becomes `(3)/(3)`). A macro with no plain reading is a model error, not a guess.

## The still's gates (`verify/visual.py`)

Each layout is measured where the viewer page shows it: portrait at 390 × 844, wide at 1440 × 900. The image is never scaled above its natural width. The viewer page itself is also shot at 390 and 1440 in both colour schemes.

| Gate | What it checks | AC |
|---|---|---|
| `visual.still.layout` | no text outside its box or the figure, no overlapping text, nothing under 11 CSS px, viewer page with no horizontal overflow | AC-3.4 |
| `visual.still.key-nodes` | every key node (storyboard `key_nodes`, plus the figure's code, output, note and compare) is present, fully inside the viewport and the figure, and no taller than the screen (D20.3) | AC-3.4 |
| `visual.still.contrast` | rendered text against the filled box under it ≥ 4.5; rules, borders, the path and the pill against one adjacent colour ≥ 3; rendered note vs correction ≥ 15 L* in every variant; the token table below | AC-3.3 |
| `visual.still.ocr` | Tesseract reads every value and number cell; every digit cell passes the lining geometry check (same ink height, tops and bottoms aligned per row); every text element is lining + tabular | AC-3.2 |
| `visual.still.fonts` | only bundled families are used and loaded | AC-3.2 |
| `visual.still.alt-source` | title, a real description, a source link | |
| `visual.still.network` | any request off the machine fails (`OutboundRequest`); PNG export raises it too | AC-3.6 |
| `values.still` | every value equals its fact and its expectation; each `data-state` box shows exactly that state's outputs in order; code lines and line numbers match the source | AC-3.7 |

## Contrast table (computed from tokens.json)

`visual.token_contrast()` prints this; `tests/test_visual.py::test_contrast` checks it.

| Pair | Min | Light | Dark |
|---|---|---|---|
| ink on ground | 4.5 | 16.14 | 15.66 |
| ink on surface | 4.5 | 16.72 | 14.17 |
| ink on highlight | 4.5 | 13.63 | 11.54 |
| ink_soft on ground | 4.5 | 9.04 | 11.53 |
| ink_soft on surface | 4.5 | 9.37 | 10.44 |
| ink_soft on highlight | 4.5 | 7.63 | 8.50 |
| label on ground | 4.5 | 6.03 | 9.14 |
| label on surface | 4.5 | 6.25 | 8.28 |
| faint on ground | 4.5 | 4.67 | 6.48 |
| faint on surface | 4.5 | 4.84 | 5.86 |
| note on ground | 4.5 | 9.69 | 9.61 |
| note on surface | 4.5 | 10.04 | 8.70 |
| note on highlight | 4.5 | 8.19 | 7.09 |
| note on note_tint | 4.5 | 8.56 | 8.26 |
| correction on ground | 4.5 | 5.20 | 5.68 |
| correction on surface | 4.5 | 5.39 | 5.14 |
| correction on correction_tint | 4.5 | 4.74 | 5.03 |
| value on ground | 4.5 | 16.14 | 12.21 |
| value on surface | 4.5 | 16.72 | 11.05 |
| surface on note (badge digits) | 4.5 | 10.04 | 8.70 |
| rule on ground | 3 | 3.81 | 3.71 |
| rule on surface | 3 | 3.95 | 3.35 |
| note (path) on ground | 3 | 9.69 | 9.61 |
| note (path) on surface | 3 | 10.04 | 8.70 |
| correction (pill border) on correction_tint | 3 | 4.74 | 5.03 |

| Separation | Min | Light | Dark |
|---|---|---|---|
| note vs correction, L* | 15 | 16.9 | 16.8 |

## Mechanism, not metrics (D20.5)

The output box sits under the program whose path produced it. The comparison shows its own program and path beside its output, not only the output. A figure that showed a summary with no mechanism would fail review, not a gate.
