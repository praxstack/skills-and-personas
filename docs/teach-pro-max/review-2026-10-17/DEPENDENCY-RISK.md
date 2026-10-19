# Dependency release risk — 2026-10-17

Assessment: the existing local teacher/renderer release is not blocked by a demonstrated new dependency regression. It has disclosed baseline dependency risk, and must not be described as audit-clean. This conclusion is limited to the supported static renderer and local Flint adapter, with their current safety boundaries intact. It does not approve exposing Flint's MCP HTTP server, using SDK OAuth against untrusted servers, or relaxing sanitizer rules.

## Reproducible evidence

`P` means `skills/teach-pro-max/references/prax-teach-v2`. Raw evidence is outside the candidate at `/Users/prax/Developer/prax-teach-evaluation-20261016/completion-v3/dependency-risk/`.

- Ran `npm audit --json --package-lock-only --ignore-scripts` in `P` and `P/integrations/flint`, against the existing pinned locks. Both returned exit 1 because advisories were found. No install, update, audit fix, dependency or source edit was performed.
- Root: **3 affected packages: 2 high, 1 moderate, 0 critical**. Flint: **6 affected packages: 1 critical, 2 high, 3 moderate**. These are package counts; several packages have multiple advisories. Full advisory lists and ranges are in `root-audit.json` and `flint-audit.json`.
- Both lockfiles remained unchanged before/after audit and are byte-identical to original accepted baseline `286a98fc67486fa91bb19f34a9c0be347f5db029`. Hashes and comparisons are in `audit-provenance.json`.
- Existing focused suites `tests/render_markdown.test.mjs` and `tests/flint_adapter.test.mjs`: **20/20 passed**, no skips, on cached Node **22.23.3**; see `boundary-tests.log`. The audit itself used system npm/Node 26; the safety/runtime checks used Node 22, consistent with `P/package.json`.
- Direct advisory-shaped SVG SMIL and inline-style probes both returned exit 2 and published no HTML; see `reachability-smoke.json` and probe logs.
- A real inline-data Vega-Lite fixture rendered successfully through the local Flint adapter. Its `NODE_DEBUG=esm` trace contains none of the six affected Flint package names; see `flint-esm-trace.log`. This is supporting module-load evidence for that execution, not a syscall/network isolation trace or proof about every optional backend.

## Root renderer: exact vulnerable paths and exposure

All three are production dependency entries; calling them development-only would be incorrect.

| Locked path | Advisory impact | Actual boundary and finding |
| --- | --- | --- |
| `sanitize-html@2.17.6` | [SVG SMIL stored XSS](https://github.com/advisories/GHSA-g8qq-57p8-ggw5); fixed 2.17.7 | The advisory requires permitting SVG animation and its URI-list attributes. `P/scripts/render_markdown.mjs:12–39` permits neither SVG nor `animate`/`set` nor the relevant attributes. Its preflight rejects unsupported input before sanitizing, and the direct SMIL probe was rejected. The vulnerable configuration is not exposed by the supported renderer. |
| `sanitize-html@2.17.6 → postcss@8.5.25 → nanoid@3.3.17` | [Zero-size custom generator infinite loop](https://github.com/advisories/GHSA-2v37-7h3g-55p8); fixed 3.3.18 | Installed PostCSS `lib/input.js:3,80` uses `nanoid/non-secure` with fixed `nanoid(6)`, not an attacker-controlled zero-size custom generator. Renderer admits no `style` attributes. No affected call path was found. |
| `sanitize-html@2.17.6 → postcss@8.5.25 → source-map-js@1.2.1` | [Indexed source-map offset denial of service](https://github.com/advisories/GHSA-68fv-2mgg-jv7q); fixed 1.2.2 | Renderer admits neither inline style nor style tags. Even sanitize-html's style parser uses PostCSS `{ map: false }` (`node_modules/sanitize-html/index.js:505`). No path accepting hostile indexed source maps was found in this renderer. |

The trusted publication root protects output paths; it does not make lesson text trustworthy. Hostile Markdown/HTML still crosses a sanitizer boundary, so retaining strict HTML/URL/image checks is essential. The passing suites include hostile HTML, URL, image and publication-path checks. These results address these advisories, not every possible sanitizer defect.

## Flint: exact vulnerable paths and exposure

Every row begins with `flint-chart-mcp@0.4.1 → @modelcontextprotocol/sdk@1.30.0` under `P/integrations/flint/node_modules/`.

| Continuation of locked path | Highest audit severity and impact | Supported local adapter reachability |
| --- | --- | --- |
| SDK itself | High: [OAuth credentials sent to server-selected authorization server](https://github.com/advisories/GHSA-6qxp-vccf-f47h) | No OAuth client, auth provider or remote MCP connection. Advisory explicitly excludes SDK servers and stdio clients. |
| `ajv@8.20.0 → fast-uri@3.1.5` | High: host/scheme/authority normalization ambiguity and SSRF policy bypass; six advisories | Local render entry does not import SDK/AJV. No fast-uri-based URL authorization/fetch path found. Full advisory IDs/ranges are in audit JSON. |
| `hono@4.13.0` | Moderate: static-generation path traversal, body-parser exhaustion, query interpretation, JSX boundary XSS | No Hono routing, static generation or JSX boundary functions in local adapter. |
| `express-rate-limit@8.6.2 → ip-address@10.4.0` | Moderate: IPv6 trust classification/subnet mistakes and oversized diagnostic denial of service | No IP allowlist, rate limiter or Address6 parsing in local adapter. |
| `express@5.2.1 → proxy-addr@2.0.7` | Critical: [spoofable client IP with particular IPv4-mapped IPv6 trust subnets](https://github.com/advisories/GHSA-jqcg-44mw-7w3h) | Local adapter starts no Express server and configures no trusted proxy subnet. A critical installed package does not establish the advisory's exploit preconditions here. |
| `express@5.2.1 → qs@6.15.3`; also `express → body-parser@2.3.0 → qs` | Moderate: array-limit bypass/attacker-controlled `isBuffer` denial of service | No request-body/query parser in local adapter. |

`P/integrations/flint/render_flint.mjs:16–21` imports the package's `flint-chart-mcp/render` export, distinct from its server/CLI export. The installed render module imports Flint and Node file/path helpers, with dynamic imports for rendering backends; it does not import SDK/Express/Hono. The package's HTTP/stdio CLI is present on disk but is not this entry point.

The adapter is a local process accepting bounded JSON, requires inline `data.values`, rejects nested reference keys and remote/file reference strings, and passes `disableFileReference: true` to Flint validation, assembly and rendering (`render_flint.mjs:105–128,219–225,659–672`). This limits hostile input reachability; it is not an operating-system sandbox. Network isolation remains explicitly unproven. The dependency-free `runtime/prax-visual-lab/package.json` does not import these packages into delivered offline lessons.

## Existing gates and follow-up

The frozen completion scope requires preserving sanitizer/publication/security checks and passing unchanged runtime/rendered/held-out/review gates before installation. `P/scripts/verify.py:371–414` enumerates executable gates and records dependency lock fingerprints; it contains no npm-audit-zero gate. This review adds no threshold and grants no exception to a failing protected check. Identical baseline locks plus the inspected execution paths establish no new critical dependency regression from this candidate. Remaining release gates belong to the completion run and are not certified by this report.

Treat these as disclosed residual risks for the existing supported local use. Reassess before enabling HTTP/OAuth, accepting references or arbitrary schemas, changing renderer HTML rules, or changing the affected dependency graph. Do not label the whole Flint package safe merely because the local rendering entry point bypasses its server dependencies.

A separate scoped dependency maintenance change can update sanitize-html (audit proposes 2.18.1), nanoid to at least 3.3.18 and source-map-js to at least 1.2.2; refresh compatible Flint transitive locks to patched SDK (at least 1.31.0), fast-uri (3.1.8), Hono (at least 4.13.7), proxy-addr (2.0.8), qs (6.16.0) and ip-address outside its current advisory ranges. Verify actual published compatible versions and the whole resulting audit then. Re-run current renderer/publication, Flint deterministic-output, native artifact and exact-source evidence checks, and regenerate bindings for the changed lock bytes. No such repair or gate change occurred in this assessment.
