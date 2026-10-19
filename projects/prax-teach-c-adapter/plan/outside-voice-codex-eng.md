1. **Offline setup is incomplete (E1–E3, D19.2).** The download inventory omits Playwright’s browser revision, HyperFrames’ browser, Kokoro’s voice file, and any Docker image. `PLAYWRIGHT_BROWSERS_PATH` doesn’t configure every Chrome launcher. **Fix:** enumerate and pin the complete runtime dependencies; prove a first build succeeds with empty ordinary caches and networking disabled. [Playwright](https://playwright.dev/docs/browsers), [Kokoro](https://github.com/thewh1teagle/kokoro-onnx).

2. **A local npm pin doesn’t disable HyperFrames updates (D17.9, E3).** The environment contract omits `HYPERFRAMES_NO_UPDATE_CHECK=1`. Upstream documents background update behavior. **Fix:** set it explicitly and test that pinned **0.8.169** neither fetches nor modifies its installation. [HyperFrames documentation](https://github.com/heygen-com/hyperframes/blob/main/docs/packages/cli.mdx).

3. **ET1’s network evidence is insufficient.** “MP4 produced, zero denied requests in the render log” cannot distinguish successful isolation from missing denial logging. Docker isolation also doesn’t automatically report attempted requests. **Fix:** require deliberate DNS, HTTPS and child-process canaries to fail observably; specify the actual Docker invocation carrying `--network none`.

4. **Caption synchronization lacks an independent timing oracle (D17.8, E2).** Comparing cue starts with their *planned* times can pass captions and audio that drift together. **Fix:** measure synthesized segment durations before scheduling; compare final-MP4 speech timestamps against VTT starts **and ends**. Include shifted-audio, truncated-speech and wrong-code-token fixtures.

5. **Claims reviews can become stale approvals (D18.1).** Schema validation doesn’t establish that a review covers the current lesson, artifacts, sources or rubric. **Fix:** bind each job and response to an immutable input manifest; invalidate affected reviews after edits. Test replaying a previously passing review against changed content.

6. **The sanitizer test exercises the wrong mechanism (Eng §3).** `printf("%f", a)` should trigger the format-warning gate; it doesn’t demonstrate working runtime sanitizers. **Fix:** separate warning-only, runtime-ASan and runtime-UBSan fixtures. Specify GCC’s diagnostic-only command separately from Clang’s compile/link/run flags. Clean sanitizer output must never mean “no UB.” [Clang UBSan](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html).

7. **The stated CSP conflicts with self-contained interactive HTML (§3).** `default-src 'self' data:` blocks ordinary inline scripts and styles. **Fix:** define explicit script/style hashes and media/font directives; choose and test the delivery mode, including metadata-track loading. Exercise the packaged artifact with CSP enforced. [CSP behavior](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy).

8. **`ptk selftest` cannot independently complete its own claims tests (E3, Eng §3).** A Python CLI cannot invoke unspecified host-subagent facilities merely because `claims-jobs/` exists. **Fix:** define the host orchestration adapter and resume protocol. Distinguish automatic selftests from agent-mediated integration tests; test both on each supported host.

9. **Mutation detection has no adequate false-positive control (D17.5).** A reviewer that rejects almost everything can achieve excellent mutation recall. **Fix:** pair every corruption with a valid control, require a clean-control acceptance threshold, and distinguish schema rejection from detection of the intended semantic error.

10. **“genanki round-trip” names no executable test (T4, Eng §3).** The plan specifies a deck generator, but no reader or actual Anki import. **Fix:** inspect the archive/database, then import into an isolated Anki profile and verify rendered cards, stable note IDs and duplicate-free reimport.

11. **The capture watchdog leaves resource escape paths unspecified (D17.10).** Parent RSS and process-group killing don’t cover descendant memory, detached children or unlimited stdout. **Fix:** prohibit child creation for capture programs unless needed; bound aggregate memory and output, and test cleanup after timeout and watchdog termination.

12. **E10 directly contradicts FREEZE’s write boundary.** It mandates writing `~/.gstack/projects/v2.1/`, while D19.1 requires development writes inside `v2.1/**`. **Fix:** keep the test-plan artifact inside the candidate tree; defer external copies until explicitly authorized.
