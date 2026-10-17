# Environment notes

These skills were built and tested in a Claude Code cloud sandbox (Linux, 4 CPUs, 15 GB RAM, no GPU) on
2026-10-06. Most of it applies to a laptop too; the differences are listed at the end. Verify a path before
relying on it: environments change.

## Contents
- Check the machine first
- Tools and paths that worked
- Network
- Fonts
- Speed table
- Long jobs
- Shell gotchas
- On a laptop instead

## Check the machine first

```bash
nproc; free -g; df -h .; ffmpeg -version | head -1; node --version; python3 --version
ls /opt/pw-browsers 2>/dev/null; fc-list | grep -iE "inter|dejavu|jetbrains" | head
```

Write what you found into the brief's Output section (resolution, fps, expected render time). If `df` shows 0
available, the session's disk allowance is spent: delete `node_modules`, `media/`, old segments and draft renders.

## Tools and paths that worked

| Need | What worked |
|---|---|
| Browser for page/WebGL tools | `/opt/pw-browsers/chromium` (full Chromium); headless shell `/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell` (Remotion, HyperFrames want this one) |
| Playwright | each template that renders with `capture.mjs` pins `playwright-core` 1.56.1 (installed by its `npm ci`); `capture.mjs` also finds a global install (`npm root -g`, here `/opt/node22/lib/node_modules/playwright`); never run `playwright install` here |
| Puppeteer-based tools (Revideo) | `PUPPETEER_SKIP_DOWNLOAD=1` at install, `executablePath: '/opt/pw-browsers/chromium'`, `args: ['--no-sandbox']` |
| Node | v22 (`/opt/node22`); Node 22 strips TypeScript types, so plain-data `.ts` files can be imported by node scripts |
| Python | 3.13; `python3 -m pip install` works through the proxy. Kokoro (`kokoro-onnx` 0.6.1) needs Python 3.10 to 3.13: on 3.14 or 3.9, make a venv with 3.12 or 3.13 first |
| ffmpeg | 6.1 with libx264, libass (subtitles), ebur128, loudnorm, blackdetect, freezedetect |
| Manim system deps | `apt-get update && apt-get install -y libpango1.0-dev libcairo2-dev pkg-config` then `pip install manim` (a venv avoids clashes). No LaTeX: use `Text`/`MarkupText`, build superscripts by hand |
| Voice | Kokoro offline (references/voice-and-audio.md) |

## Network

- Works: npm registry, PyPI, GitHub release downloads, raw.githubusercontent.com.
- Blocked (checked 2026-10-07): huggingface.co (so the piper voice download fails), Google Fonts (TLS fails),
  Microsoft edge-tts speech endpoint, openaipublic.azureedge.net, download.pytorch.org. Others may be blocked; if a download
  fails, read the proxy's status (`curl -sS "$HTTPS_PROXY/__agentproxy/status"` in Claude Code cloud) before
  concluding anything, and record what you tried.

## Fonts

- Installed system fonts: Inter, Inter Display, DejaVu Sans / Sans Mono (full glyphs including arrows and ∞).
- Anything else: `npm i @fontsource/<font>` and load the woff2 locally (CSS `@font-face`, `FontFace` in JS,
  esbuild `--loader:.woff2=dataurl`). Wait for fonts before the first frame (`await document.fonts.ready`, or
  `document.fonts.load('48px "JetBrains Mono"')`), or the first frames render in a fallback font.
- JetBrains Mono / Fira Code ligatures turn `!=`, `<=`, `++` into single glyphs. Turn them off everywhere code is
  shown: CSS `font-feature-settings: "calt" 0, "liga" 0`; `FontFace(..., {featureSettings: '"calt" 0, "liga" 0'})`;
  Motion Canvas `letterSpacing={0.01}`; plain canvas: draw one glyph at a time.
- Space Grotesk digits are hard to read (1 looks like a flag); use Inter or JetBrains Mono for numbers.

## Speed table (1080p30, 4 CPUs, measured on the LC 787 films)

| Tool | Measured | Per minute of film |
|---|---|---|
| Hand-drawn canvas (4 workers, `capture.mjs`) | 5:50 film in ~6 min | ~1 min |
| Revideo (4 workers) | 5 min film in ~11 min | ~2.2 min |
| HyperFrames (draft quality) | 5 min film in ~13 min | ~2.6 min |
| Manim CE (scenes in parallel) | 6:19 film in ~15 min; LC 70 skill test, 3:57 film in 5 min (2 workers, quiet) | 1.3 to 2.4 min |
| Remotion (`--concurrency=4`) | 7.4 min film in ~25 min | ~3.4 min |
| Motion Canvas (editor Render button, bake-off) | ~7k frames in ~27 min | ~7 min; the skill's headless page benched ~10 frames/s per worker |
| GSAP page via `capture.mjs` | LC 739 skill test, 3:30 film in 8 min (2 workers) | ~2.3 min |
| Three.js + Theatre.js, SwiftShader WebGL, shadows + bloom | ~1.25 fps | ~24 min (5.5 min film ≈ 2 h 15 m) |

Per-worker speeds measured while building the skills (1080p, often under heavy load, so rough): hand-drawn 5 to 8,
GSAP ~7, Motion Canvas ~10, Remotion 4 to 6, HyperFrames ~4, Manim ~3.4, Theatre.js 2 to 4, Three.js 0.6 (1.3 at
720p). On a quiet machine they can be 3x higher (Manim measured 11 to 14 in the LC 70 test). Load matters more
than the tool: check `uptime` first, and benchmark before the full render; each skill says how.

## Long jobs

- Background jobs in the Claude Code cloud sandbox are killed at 2 hours. Every render path here is segmented
  and resumable; run with a budget under 100 minutes and re-run the same command until it reports done.
- Run renders in the background with a log file, and check the log; do not hold a turn open on a long render.
- Keep the project on local disk while rendering (`/home/...` or the scratchpad), not on a synced/shared mount:
  thousands of small frame writes to a network folder are slow and can collide with other writers. Copy the
  deliverables to the shared folder at the end (`package.py --to`).

## Shell gotchas

- `pkill -f <pattern>` kills your own shell when the pattern appears in your command line (it matches the
  `bash -c "... pkill -f vite ..."` process). Kill by PID: `kill $(cat server.pid)` or `pgrep -f '^node .*vite'`.
- Killing ffmpeg broadly can take down a dev server that spawned it (Motion Canvas). Kill the specific PID.
- Vite dev servers stay running after a render; stop them so the next run can bind the port.

## On a laptop instead

- Use the local Chrome/Chromium: drop `--browser-executable`/`executablePath` overrides, or point them at the
  installed browser. `npx playwright install chromium` is fine on a laptop.
- edge-tts usually works, so `voice.py --engine edge-tts --voice en-IN-NeerjaNeural` is an option directly; Kokoro
  remains the default because it is offline and deterministic.
- A GPU makes WebGL (Three.js/Theatre.js) renders 20 to 50x faster; launch Chromium with `--use-gl=angle`
  (or the platform default) instead of the SwiftShader flags (`capture.mjs` uses SwiftShader only with `--webgl`).
- macOS: `brew install ffmpeg pango cairo pkg-config` for Manim.
