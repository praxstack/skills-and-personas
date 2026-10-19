# Tool registry (`registry/tools.json`)

Read this when you pick how to make an artifact, or when `ptk build` stops because a tool is missing.

## What's in it

- **`artifacts`**: for each artifact type (still, explorer, qa, cards, video, ive, tts), the ranked
  alternatives from the approach catalog (report 05, 2026-10-18): 16, 15, 13, 13, 16, 15 and 10 of them.
  Each has a `rank`, the tools it `needs`, whether it is `local`, and `ptk_projector` when ptk can build
  it itself. `fallback_order` lists the ids by rank.
- **`tools`**: one yes/no probe per tool. Kinds: `binary` (on PATH), `state` (a file under `$PTK_STATE`),
  `sandbox`, `app` (a macOS app bundle), `python-module` (importable in a `$PTK_STATE` venv),
  `node-module` (under `$PTK_STATE/tools/node`), `builtin` (ships here), `cloud` (never runnable without
  Prax's permission) and `unsupported-platform`.
- **`catalog`**: v2's 38 visualization tools, ported with corrections. Each has a `disposition`
  (`route`, `alternative`, `backend`, `format`, `handoff-only`, `do-not-route`,
  `requires-human-authored-asset`, `cloud-needs-consent`) and a `corrections` list saying what changed.
- **`downloads`**: everything `ptk host setup` fetches, with source, size and sha256.

## Use it

```
ptk host probe                      # every tool and every artifact type
ptk host probe --artifact video     # one type
```

For each type the probe gives `selected` (the best alternative ptk can build here now), `best_runnable`
(the best one runnable at all, which may need hand work) and, per alternative, `missing` tools.
A probe never fetches or starts anything. Two limits: a `binary` probe for `docker` only finds the CLI,
not a running daemon, and an `app` probe only finds the bundle.

## Corrections to v2's registry (report 03 M11 to M17, report 01 L2)

- Manim is pinned to 0.22.0, the host version, not 0.21.0. No LaTeX here, so `MathTex` fails: use `Text`
  and `Code`, or install Tectonic with Prax's OK.
- HyperFrames is 0.8.169 from `node/package-lock.json`, with its narration commands (`tts`, `transcribe`)
  listed. Never the global CLI and never `npx` latest.
- Remotion and Motion Canvas were `do-not-route` in v2 while report 05 ranks them. They are ranked
  alternatives now; the contradiction is gone.
- FFmpeg is a `backend` and never ranks first. HTML, CSS, JavaScript, Canvas and WebGL are `format`s,
  not tools.
- Rive and dotLottie need a human-made asset. Image generation, Unsplash and Wikimedia need network and
  consent.
- Every docs link is https. Probes check binaries and files, not whether a skill file exists.

## No self-approval

`tests/test_registry.py` pins the expected counts, the top three of each type and the 38 v2 ids by hand,
so editing the registry can't make its own test pass. It also runs the probe with an empty PATH and
checks that every binary-probed tool flips to missing.
