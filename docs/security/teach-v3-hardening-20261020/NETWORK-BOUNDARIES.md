# Optional engine setup and network boundaries

The default paths below no longer acquire missing packages/models or select an
online speech fallback automatically. `TEACHER_ALLOW_NETWORK=1` is an explicit
per-invocation opt-in for setup and online speech; it is not an operating-system
network sandbox. Install dependencies and model assets during a separate setup
invocation, then omit the variable for ordinary cached operation.

## Changed paths

| Surface | Default behavior | Explicit online behavior |
|---|---|---|
| Eleven video `pydeps.py` copies | Import installed modules; missing dependencies fail with setup instructions before pip | Allows the existing package installer and environment fallback |
| Eleven video `voice.py` copies | Verified Kokoro/Piper caches work; missing/invalid assets fail before download; auto tries Kokoro then Piper | Allows model downloads and EdgeTTS in the fallback order |
| Eleven `edge_voice_swap.py` copies | Stops before importing EdgeTTS or accessing project artifacts | Allows sending narration to Microsoft speech services |
| Explorable `narrate.py` Kokoro | Checks local model SHA-256; missing/invalid assets fail before download | Allows existing digest-checked model acquisition |
| Explorable Chatterbox | Sets Hugging Face and Transformers offline state before model loading, including already-imported HF constants | Allows the dependency's normal acquisition behavior, subject to its own environment settings |
| Visual QA Whisper | Passes `local_files_only=True`; cache misses explain setup | Passes `local_files_only=False` |
| Remotion renderer | Missing npm dependencies or absent local browser fail before acquisition; cached browser paths work | Allows npm setup and Remotion browser acquisition |
| Learner Python panel | An unchecked consent control blocks worker creation | Learner explicitly allows the Pyodide/jsDelivr runtime download before Run |

The eleven video copies are explainer-video, gsap-video, handdrawn-js-video,
hyperframes-video, manim-video, motion-canvas-video, motion-video, remotion-video,
revideo-video, theatrejs-video, and threejs-video. Each retains its standalone
helper files. No frozen embedded runtime was changed.

Pyodide consent is per panel/page and can be unchecked. Its low-level
`runPython` API remains unchanged, so callers outside the panel must supply
their own user authorization. The CDN loader has its existing integrity pin;
this change does not add integrity coverage to every transitive runtime file.
An internet connection may still be needed after consent even when some files
are browser-cached.

## Evidence and limits

`python3 skills/teacher/scripts/tests/test_network_policy.py -v` passed eleven
behavioral tests. They enumerate all eleven copies, exercise denied installer,
model downloader and service paths, verify local Kokoro/Piper fixture assets,
exercise explicit mocked acquisition and EdgeTTS synthesis, check preimported
HF offline state and Whisper loader arguments, and execute the JavaScript
learner control against a denied worker constructor. A subprocess harness also
checks Remotion missing-package/browser denial, cached executable selection,
and explicit setup using local npm/npx stand-ins. No personal narration was
sent to a service and no production model was downloaded by these tests.

The initial unchanged teacher-suite run identified vendor-receipt drift for
the eleven changed video copies. The documented `scripts/vendor.py record`
workflow now records those local changes; each note preserves the prior tree
SHA-256, and upstream source commits remain unchanged. `vendor.py verify`
reports zero problems. These are product provenance receipts, not changes to
the evaluator or acceptance thresholds. The final unchanged teacher suite
passes: 71 tests run, four skipped, zero failures.

Known remaining boundaries:

- Remotion receives an explicit local browser executable when offline. Automatic
  discovery scans `/opt/pw-browsers` and project/source `node_modules/.remotion`
  caches; another cache layout requires `--browser` or
  `REMOTION_BROWSER_EXECUTABLE`. npm/npx acquisition guards do not prevent
  arbitrary project JavaScript or browser page requests from using network.
- Browser/rendered lesson assets, optional engines and third-party imported
  packages have not received a complete network audit. Host execution can use
  network independently of these setup guards.
- Diagram rendering retains its existing `--allow-network` Kroki opt-in; that is
  a separate control from the environment variable above.
- The Kokoro unpinned-model override remains an explicit pre-existing override;
  Piper retains its existing upstream MD5 checks. These changes do not upgrade
  model authenticity guarantees or constrain setup downloads by total size/time.
- Setting HF offline state persists for that Python process. A fresh invocation
  is the supported way to switch from cached runtime to opted-in online setup.
  Direct dependency behavior outside Hugging Face is not intercepted.
- Historical packaged archives and the frozen teach-pro-max embedded runtime
  retain their recorded behavior until a separately authorized release updates
  them. Current source changes are not installation/deployment evidence.
