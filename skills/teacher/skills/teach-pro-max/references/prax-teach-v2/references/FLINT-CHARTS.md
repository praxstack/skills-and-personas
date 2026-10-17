# Optional Flint charts

_Verified upstream snapshot: 2026-08-04. This integration is off by default and is not installed by this package._

## Purpose

Use [Microsoft Flint](https://github.com/microsoft/flint-chart) as an optional compiler for exact quantitative charts after the visualization router has already decided that a chart materially helps learning.

Flint is a semantics-driven intermediate language: the author supplies data, field meanings, chart type, and encodings; the compiler produces a backend-native specification. Version 0.4.1 is declared by the current npm package manifests, requires Node 18+, and is MIT licensed. [Core package](https://github.com/microsoft/flint-chart/blob/main/packages/flint-js/package.json) and [MCP package](https://github.com/microsoft/flint-chart/blob/main/packages/flint-mcp/package.json)

Flint does **not** replace the Prax Teach visual router, data preparation, accessibility contract, source verification, or browser acceptance tests.

## Route

```text
none | static | interactive | motion
                 |
          static chart-worthy job?
                 |
       +---------+----------+
       |                    |
      no                   yes
       |                    |
native representation   table sufficient?
                            |
                    +-------+-------+
                    |               |
                   yes             no
                    |               |
              semantic table   Flint available,
                               pinned, and permitted?
                                    |
                              +-----+-----+
                              |           |
                             yes         no
                              |           |
                        Flint -> SVG   native SVG/table
```

Use Flint initially only for `static` quantity, distribution, time-series, and exact-comparison jobs. Do not route process diagrams, architecture, hierarchy, geometry, equations, illustrations, simulations, or motion through it merely because it is available.

## Verified upstream surface

| Path | Output | Appropriate use here |
|---|---|---|
| `assembleVegaLite` | Vega-Lite specification | Default portable compiler target |
| `assembleECharts` | ECharts options | Specialized static render when verified |
| `assembleChartjs` | Chart.js configuration | Existing Chart.js hosts |
| `assemblePlotly` | Plotly data/layout | Optional application integration |
| `assembleExcel` | Office.js chart artifact | Explicit Excel export only |
| MCP `validate_chart` | Validation result | Authoring-time spec check |
| MCP `compile_chart` | Backend-native JSON plus warnings | Inspection and controlled customization |
| MCP `render_chart` | PNG/SVG for supported backends | Build-time static artifact |
| MCP `create_chart_view` | Host-specific live editor | Authoring preview, not the durable lesson |

See the upstream [README](https://github.com/microsoft/flint-chart/blob/main/README.md), [API reference](https://github.com/microsoft/flint-chart/blob/main/docs/api-reference.md), and [MCP guide](https://github.com/microsoft/flint-chart/blob/main/packages/flint-mcp/README.md).

The released Python package is not available; the Python port is a source preview. Use the JavaScript/TypeScript library or MCP server for a released path.

Check availability without changing the environment:

```bash
python3 scripts/check_optional_integrations.py --json
```

## Authoring contract

1. Inspect the actual values, units, missingness, category counts, totals, and outliers.
2. Transform joins, pivots, derived fields, filtering, time buckets, and complex aggregation before Flint.
3. Decide whether a semantic table already communicates the comparison more clearly.
4. Author a `ChartAssemblyInput` with exact field names and the most specific valid semantic types.
5. Validate the Flint spec.
6. Compile and inspect all warnings.
7. Render a static SVG where possible.
8. Compare the rendered marks, axes, domains, labels, and retained categories with the source data.
9. Add the accessible figure wrapper, text summary, and data table.
10. Preserve the editable spec, prepared data, render manifest, and version pin.

Flint is a chart compiler, not a data-wrangling system. Never invent an unsupported transform or silently change the data to make a template fit.

## Minimal semantic spec

```json
{
  "data": { "values": "host-binds-reviewed-rows" },
  "semantic_types": {
    "review_day": "Day",
    "recall_rate": "Percentage",
    "condition": "Category"
  },
  "chart_spec": {
    "chartType": "Line Chart",
    "encodings": {
      "x": { "field": "review_day" },
      "y": { "field": "recall_rate" },
      "color": { "field": "condition" }
    },
    "baseSize": { "width": 640, "height": 360 }
  }
}
```

The string in `data.values` above is documentation shorthand, not executable Flint input. A host must bind reviewed row objects or a permitted local data file. Do not reserialize a large dataset through an agent response.

## Durable artifact set

```text
chart.source.flint.json      # original reviewed ChartAssemblyInput
chart.data.json              # separately editable prepared exact rows
chart.semantic-spec.json     # separately editable semantics and encodings
chart.svg                    # preferred static delivery
chart.vega-lite.json         # inspected backend-native specification
chart.table.html             # complete semantic data/table alternative
manifest.json                # versions, hashes, backend, warnings and limits
lesson.md                    # canonical lesson and data-table alternative
lesson.html                  # generated companion
```

The render manifest records separate hashes for source, prepared data, semantic
spec and output so an edit cannot hide inside a combined input hash. It records
the normalized CLI with path placeholders, the exact pinned render-module APIs
and options, a `SOURCE_DATE_EPOCH`-derived non-null generation time, and an
explicit non-empty limitations list. It also
states `network_isolation_verified: false` unless external tracing actually
measured the process; rejecting remote references is not itself proof of
network isolation. A representative shape is:

```json
{
  "flint_version": "pinned-version",
  "backend": "vegalite",
  "format": "svg",
  "data_sha256": "sha256-of-prepared-data",
  "spec_sha256": "sha256-of-flint-spec",
  "output_sha256": "sha256-of-rendered-output",
  "warnings": [],
  "generated_at": "SOURCE_DATE_EPOCH-derived ISO-8601 timestamp",
  "invocation": {"api": [], "cli": []},
  "known_limitations": ["explicit reviewed limitation"]
}
```

Use real hashes and versions in delivered artifacts. Never copy the illustrative values above as provenance.

## Dependency and build policy

- Pin and lock the tested package version; do not use floating `npx -y` in deterministic builds.
- Install only after user authorization and in the project environment, not globally.
- Prefer programmatic build-time rendering with a local dependency.
- Keep essential lesson HTML free of mandatory runtime CDN requests.
- If Flint is absent, unsupported, or fails validation, fall back to a semantic table or verified native SVG.
- Treat any backend warning about filtering, truncation, invalid types, or unsupported templates as a build failure until reviewed.
- Publish only beneath an explicit trusted root. Existing or dangling symlink output leaves and any symlinked ancestor are rejected, and the directory lineage is revalidated at publication.

The upstream MCP can read inline rows or local JSON/CSV/TSV files. Remote URL fetching is disabled, but local-file references are allowed by default. Start the MCP with local-file references disabled unless a narrowly scoped file is needed; otherwise bind reviewed rows inline. [Flint authoring skill](https://github.com/microsoft/flint-chart/blob/main/agent-skills/flint-chart-author/SKILL.md)

## Accessibility wrapper

The reviewed upstream README, API, MCP documentation, and bundled authoring skill do not document WCAG conformance, automatic alternative text, screen-reader navigation, or data-table equivalents. Treat raw Flint output as a visual artifact that still needs an accessible host.

Every delivered chart must include:

- `<figure>` and a useful `<figcaption>`;
- concise alt text for the chart's purpose, without dumping every value;
- a nearby extended description or complete semantic data table;
- units, sample size, missingness, uncertainty, assumptions, and source provenance when material;
- patterns, direct labels, or redundant encodings so color is not the only cue;
- readable contrast, text size, focus behavior, zoom/reflow, print, and reduced-motion checks;
- a static/no-script path with the same essential meaning.

Do not claim that a Flint-generated chart is accessible merely because it is SVG.

## Retrieval and assessment safety

A chart can reveal an assessed answer through labels, annotations, scale domains, highlighted marks, captions, alternatives, or the default interactive state. When prediction or retrieval is the learning task:

1. show neutral source data or an incomplete representation first;
2. end the live turn for the learner's prediction;
3. reveal the explanatory chart only after the attempt;
4. keep pre-attempt alt text and tables neutral;
5. offer an equivalent accessible response task when neutral alternatives would invalidate the assessment.

## Acceptance gate

Reject the chart when:

- a table is clearer;
- data provenance or transformation cannot be verified;
- semantic types, units, axes, baselines, domains, or category retention are wrong;
- warnings are ignored;
- accessibility alternatives are missing;
- essential meaning requires a remote runtime dependency;
- the chart leaks a retrieval answer;
- the source spec, prepared data, render manifest, and output cannot be reproduced.

Flint improves chart authoring reliability; it does not by itself prove that the chart improves learning. Test representation appropriateness and transfer separately.
