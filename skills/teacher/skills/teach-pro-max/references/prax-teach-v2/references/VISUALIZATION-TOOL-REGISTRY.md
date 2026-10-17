# Visualization Tool and Agent Resource Registry

This is the human guide to `visualization-tool-registry.json`. Use the lookup helper to load only the relevant entries rather than placing the full registry into every teaching turn.

## Quick Lookup

Resolve `<prax-teach-skill-dir>` from the directory containing `SKILL.md`:

```bash
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py mermaid
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py "math animation"
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py --route structure
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py --route interaction
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py --list
python <prax-teach-skill-dir>/scripts/find_visualization_tool.py --check
```

Use `--json` when another script needs structured output and `--limit` to control disclosure.

## Selection Policy

Choose in this order:

1. Existing working tool in the lesson workspace
2. Verified first-party skill, MCP, plugin, or CLI
3. Official documentation
4. Official source and examples
5. Inspected, pinned community integration
6. Small local adapter built from official documentation

Tool capability and agent capability are independent. Graphviz can be the right renderer even when no Graphviz skill exists; write DOT from the official grammar instead of installing a dubious wrapper.

Before installing a community integration, inspect:

- owner and source repository
- scripts and generated commands
- network egress
- dependency tree and install hooks
- secret and credential handling
- filesystem scope and destructive behavior
- target tool and project-version compatibility
- licence and redistribution terms

Pin a reviewed version or commit, test it in isolation, and compare its output with the direct official renderer.

## Trust Classifications

| Trust | Meaning |
|---|---|
| `official-standard` | Specification maintained by a standards body |
| `first-party-tool-docs` | Official project documentation/source; no agent integration implied |
| `first-party-agent-integration` | Skill, MCP, plugin, or agent surface maintained by the tool owner |
| `local-vetted` | Workflow inspected on the source host; current-host availability is probed at query time |
| `community-unverified` | Requires source, permission, dependency, and compatibility review |

“No first-party integration found” means none was found in official documentation and repositories checked on the registry date. It does not mean the tool is unsupported.

## Route Index

| Learning route | Good starting points |
|---|---|
| Exact structure or labels | SVG, Mermaid, D2 |
| Dense hierarchy or dependency | Graphviz |
| Editable handoff | draw.io, Excalidraw |
| UML and software sequence | PlantUML |
| Consistent architecture views | Structurizr/C4 |
| Mathematical constrained layout | Penrose |
| Declarative quantity | Vega-Lite, Altair |
| Lightweight composed marks | Observable Plot |
| Interactive charts | Apache ECharts, Plotly |
| Scientific static figures | Matplotlib, ggplot2 |
| Fully custom data graphics | D3 |
| Interactive node editor | React Flow |
| Browser graph analysis | Cytoscape.js |
| Large network | Sigma.js |
| Large geospatial layers | deck.gl |
| Browser-native lesson interaction | HTML, CSS, JavaScript, SVG |
| Dense raster interaction | Canvas 2D |
| GPU or 3D spatial system | WebGL, Three.js |
| Mathematical transformation | Manim 0.21.0 |
| General explanatory film | HyperFrames |
| TypeScript generator film | Canvas Commons only after a demonstrated need |
| Seekable HTML video | HyperFrames |
| Interactive vector state machine | Rive, dotLottie |
| Illustrative appearance | OpenAI image generation |
| Sourced photography | Wikimedia Commons, Unsplash |
| Multi-language rendering gateway | Kroki |
| Media encoding/inspection | FFmpeg |

## Verified First-Party Agent Integrations

| Tool | Integration | Registry status |
|---|---|---|
| draw.io | Official local/hosted MCP and Codex plugin | Upstream, not confirmed installed |
| Structurizr | Official remote/self-hosted MCP | Upstream, not confirmed installed |
| HTML/CSS/JavaScript references | Experimental MDN MCP | Not installed |
| Cytoscape Desktop | Experimental official Desktop MCP | Adjacent to Cytoscape.js; not installed |
| Rive | Rive Agent | In-editor only; portable MCP not found |
| dotLottie | Lottie Creator MCP and official motion-design skill | Upstream, not installed |
| Remotion | Official skills and Codex plugin | Upstream, not installed; MCP is deprecated |
| HyperFrames | Official agent skill suite | Probe current host at query time |
| OpenAI image generation | Built-in image-generation tool | Available when exposed by the runtime |

Remote MCPs can transmit lesson content or diagrams. Record the data-egress boundary and prefer local rendering for sensitive material.

## Local Capability Map

These relative hints were present under the source host's agent skill root when
the registry was built. They are provenance, not a promise of current
installation. The query helper probes roots from `PRAX_AGENT_SKILLS_ROOTS` or
the current user's standard agent-skill directories and reports
`available-local` or `unavailable-local` at runtime.

| Capability | Relative skill path | Classification |
|---|---|---|
| SVG engineering | `svg-principal-engineer/SKILL.md` | `local-vetted` |
| Mermaid → editable Excalidraw + exports | `gstack/diagram/SKILL.md` | `local-vetted` |
| Manim production | `manim-video/SKILL.md` | `local-vetted` |
| HyperFrames routing and rendering | `hyperframes/SKILL.md` | `first-party-agent-integration` |
| HyperFrames Three.js adapter | `hyperframes-animation/adapters/three.md` | `local-vetted` |

Do not misroute:

- `dcanvas` is DecisionCanvas, not HTML Canvas.
- `json-canvas` is Obsidian JSON Canvas, not Canvas 2D.
- A contributor `AGENTS.md` is not an agent integration.
- An official project’s desktop MCP may be adjacent to, but not interchangeable with, its browser library.
- A skill visible on disk may not be callable in the current agent runtime.

## Shared Verification Contract

For every selected tool:

1. Preserve editable semantic source.
2. Record exact tool version and render command.
3. Record source/data provenance and licence.
4. Render in the lesson’s actual target environment.
5. Inspect visually and factually.
6. Repair the smallest incorrect region and rerender.
7. Add accessible naming, captions or extended description, and a static fallback.
8. Record the verification date and known limitations.

For charts, also audit scale/domain, units, missingness, uncertainty, sample size, and source. For interaction, test keyboard paths and reset behavior. For video, inspect keyframes and use `ffprobe`. For remote services, document privacy and egress.

## Registry Maintenance

The JSON’s `checked_at` date is a snapshot, not a promise of permanent currency. Before installing, authenticating, or relying on a time-sensitive integration:

- revisit its official documentation
- check deprecation and licence notices
- verify the package owner and current command
- compare the installed version with the lesson project
- update the registry only from primary sources

Notable snapshot caveats:

- Remotion’s MCP is deprecated; use its official skill/plugin.
- Motion Canvas and Remotion remain inspectable historical entries but are
  excluded from default Teach Pro Max routing; use HyperFrames or Manim.
- Sigma.js v4 is alpha; stable work should use v3 documentation unless deliberately testing v4.
- Pin Manim Community 0.21.0 at first use. Modern Manim uses PyAV internally;
  FFmpeg is not a core Manim prerequisite.
- Unsplash Source is discontinued.
- Image-model capabilities and limitations change; verify the current official model page.
