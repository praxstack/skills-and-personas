# Tool discovery

Hosts differ wildly: one has a browser, Manim and an Excalidraw MCP; another has only a shell and Python. Find out, don't assume.

## Probe once per session

```sh
python3 scripts/find_tool.py --inventory --net                         # prerequisite and reachability evidence
python3 scripts/find_tool.py --job cause --job change                  # ranked for this idea
python3 scripts/find_tool.py --job structure --medium still --offline  # nothing that needs a network
python3 scripts/find_tool.py --job story --have mcp:hyperframes --json
```

- Probes: binaries on PATH, Python modules, Node packages (from the working folder, the teacher folder, `PLAYWRIGHT_MODULE`, global npm), network hosts with `--net`, and host tools you name with `--have` or `TEACHER_HOST_TOOLS=mcp:excalidraw,mcp:artifact`.
- The script can't see your host's tool list. Look at it yourself and pass what matters: an Excalidraw or HyperFrames MCP, an image generator, artifact publishing, a canvas.
- `--offline` filters inventory as well as ranked results and suppresses network requests even when combined with `--net`.
- `available` remains a boolean. `status` and `evidence` distinguish detected local prerequisites, declared host tools, bundled instructions, direct SVG authoring, unknown dependencies, and reachable HTTP hosts. None proves a successful render. Missing or unverified requirements remain in `missing`.
- CDN libraries without local probes remain unknown by default. `--net` checks HTTP reachability only; even a reachable host does not establish that a package is installed or can run. No dependencies are downloaded or installed.
- Declare host-only capabilities by registry id, for example `--have canvas --have browser-voice`, or use `TEACHER_HOST_TOOLS`. These are caller declarations, not measured runtime checks.
- Manim inventory is structural by default: CLI and interpreter file candidates are evidence only, with `available: false` and `status: unknown`. It does not read the lesson's source configuration, launch project/source interpreters, or import workspace Manim code.
- After explicitly deciding to trust the workspace and its Python environments, use `--trusted-runtime-probe` to check Manim imports. This executes selected local runtimes and their startup/import code, including project/source venvs and workspace modules. It reads `.video-state.json` to find a configured source directory. This is unsandboxed execution, not a trust check.
- The trusted probe uses the same resolver as `render_manim.py`: `MANIM_PYTHON`, project/source venvs, current Python, then a verified absolute Python shebang from the resolved Manim CLI. The renderer also retains its higher-priority `--python` override. Shell/env launchers are unsupported. Success establishes interpreter compatibility, not version, rendering dependencies, scene correctness, or output.
- `--offline` still suppresses discovery HTTP probes when combined with `--trusted-runtime-probe`; it is not a network sandbox for code you choose to execute. No registry shell commands or installers are executed.

```sh
# Only after trusting this workspace and its runtimes:
python3 scripts/find_tool.py --inventory --trusted-runtime-probe --offline
```
- Bundled skill paths are checked for file presence, including instruction-only lesson-notebook assets. Presence is not build or browser verification.
- Ranking: jobs matched, medium matched, available prerequisites or declarations, notebook-native, bundled.

## The registry

`assets/registry.json` holds 45 entries: the bundled skills, third-party libraries and CLIs, voices, QA tools and host surfaces. Each has `jobs`, `media`, `how` (a skill path, command, pinned CDN URL, MCP or note), `probe`, `offline`, `notebook` (how to get the lesson-notebook look) and, where one exists, `ref`, the id of the entry in `skills/teach-pro-max/references/prax-teach-v2/references/visualization-tool-registry.json`, which holds the official docs, install pins and verification steps.

CDN URLs are pinned to exact versions on hosts that Claude artifacts allow (cdnjs, jsDelivr `/npm/`, unpkg). They were checked to resolve on 2026-10-16.

## When the best tool is missing

1. Say what it would have added ("Manim would let the equation morph term by term").
2. Offer to install it if the host allows installs and the learner wants it. Pin versions from the teach-pro-max registry.
3. Otherwise take the next ranked tool and say what was traded away.
4. The floor is always available: hand-written SVG in the lesson-notebook style, built with `explorable` or `concept-animation`. Both need only Python to build and a browser to view.

## Searching beyond the registry

When the subject needs something the registry lacks (a chemistry structure viewer, a music notation renderer, a circuit simulator), search for it, then hold it to the same bar:

- maintained, with official docs and a licence you can name
- runs in this host, or as a pinned CDN script
- you can verify its output (render it, screenshot it, check it with `visual-qa`)

Add it to `registry.json` with a probe, so the next session finds it too.

## Host surfaces

- **Claude artifacts**: publish a built page with `--fragment`. Single file, CDN allowlist only, no downloads, no `window.print`. Mermaid renders natively there.
- **ChatGPT and Codex canvas**: paste the single-file HTML; it runs as-is.
- **Excalidraw MCP**: a live whiteboard sketch the learner can edit.
- **HyperFrames MCP**: a hosted video project with cloud render, when the learner wants something shareable. Local HTML compositions use the bundled `hyperframes-video` skill.
- **No browser at all**: build the file, tell the learner where it is and how to open it, and describe what they should see.
