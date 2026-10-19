# Prax Teach v2.1: the lesson compiler, specification

Version 1.4, 2026-10-19. Source of truth for /implement-from-spec.

Changelog v1.4 (Prax approved the repair plan on 2026-10-19; `../FREEZE-v2.md`): explanation first everywhere. Amended AC-1.3, AC-1.6, AC-1.7, AC-6.6 (stricter, D23.5), AC-7.1 and AC-7.5 (3 reviewers on the lesson job). New: AC-1.10, AC-6.8, AC-7.7, AC-7.8, AC-7.9, WP10 (visual quality) and WP11 (learner-state privacy). Implementers of v2.2 must not change acceptance criteria.

Changelog v1.3: D21.1 withdrawn (D22.1), proposal §9 pending Prax. AC-7.1 and AC-7.5 are back to the v1.1 text: a normal `ptk build` writes the full suite. `ptk build --canary` stays as an explicit cheaper mode whose best status is `canary-verified`, never `verified`.

Changelog v1.2 (withdrawn by v1.3; orchestrator decision D21.1, cost; integration pass round 15): AC-7.1 amended. A normal `ptk build` writes the lesson claims job plus one canary mutation job; the full mutation suite with controls moves to `ptk build --calibrate`, run on a rubric or reviewer-model change and at acceptance. AC-7.5 is measured in calibration mode. This is a governing change made by the orchestrator, not yet approved by Prax (FREEZE stop rule).

Changelog v1.1: adds D20.x from three independent sessions (`../plan/EXTERNAL-INPUTS.md`). Amended: AC-1.3, AC-3.4, AC-4.2, AC-5.6, AC-6.2. New: AC-4.6, AC-4.7, AC-4.8, AC-6.6, AC-6.7, AC-9.4 (P1), and the STYLE dark theme taken from the accepted Neuron Atlas reference.

Derived from:
- `../plan/CEO-PLAN.md`, decisions D1–D19 and E0–E25 (where they conflict, the later decision wins);
- `../FREEZE.md` (frozen goals, baseline, holdout, stop rule);
- `../plan/ACCEPTANCE-PROPOSAL.md` (pending Prax);
- `../plan/TEST-PLAN.md`.

Implementers must not read `../holdout/` or `../plan/proposed/`.

## 1. Problem statement

Prax is learning C, then C++, DSA and GATE CS, for GATE 2027. He wants explanations in the medium he asks for: a still, an interactive explorer, a Q&A expander, flash cards, a narrated video or an interactive video. They have to look world-class and be technically exact.

The installed v2 skill can't do this:
- It routes "make a narrated video" to text.
- It has no narration or video path.
- It ships wrong figures with "passed" receipts.
- It overrides his workspace's predict-first contract.

The review found 114 issues, 9 of them critical. Today's hand-built proofs show the Mac can do all of it. They also show that checking values alone still lets a false teaching claim through.

## 2. Goals (measurable)

1. **G1. Every medium.** Each of the six artifact types builds from one lesson model for a C topic, and the build report shows every gate `passed` with none `not-run`.
2. **G2. No wrong numbers or claims reach the learner.** Measured with the real gates on each lesson:
   - 100% of value mutations caught;
   - at least 90% of claim mutations caught;
   - at least 95% of clean controls accepted;
   - the `%f` "same bits" regression rejected.
3. **G3. World-class look, checked.**
   - The 9 automated aesthetics items pass: contrast, lining numerals by OCR, no overflow at 390 and 1440 px, light and dark, portrait, bundled fonts, no network, alt text, source link.
   - The 6 screenshot-reviewed items have written verdicts.
4. **G4. Broadcast-grade narration.**
   - −16 ± 1 LUFS, true peak ≤ −1 dBTP.
   - Caption starts and ends within 0.5 s of measured speech.
   - Non-code WER ≤ 10%.
5. **G5. It teaches the way his workspace asks.** In a predict-first workspace, the first turn is one question and the agent waits. The scripted transcript tests pass.

## 3. Non-goals

- **Claims about human learning outcomes.** Not measurable here (FREEZE).
- **Cloud TTS, cloud rendering, paid services, HyperFrames `publish`.** Not permitted without Prax.
- **Running the learner's own code in explorers.** Deferred to TODOS (D4.12): it needs its own threat model.
- **Topic packs for C++, DSA and GATE.** Phase 2 (D4.16).
- **Manim `MathTex`, and the BasicTeX or Typst installs.** System installs need Prax's OK (D4.15). Math uses MathJax `tex2svg`.
- **Linux capture.** macOS `sandbox-exec` only in v2.1 (E5).
- **Editing v2's accepted bytes.** v2 stays installed until v2.1 is accepted.

## 4. Users and stories

**Prax, the learner**
1. As a learner, I want "teach me X as a narrated video" to produce a narrated, captioned video, so that I can learn by watching.
2. As a learner, I want to pause a video and play with the exact state on screen, so that I can test my understanding at that moment.
3. As a learner in my C workspace, I want the tutor to ask me one prediction and wait, so that I think before I see the answer.
4. As a learner, I want every number to come from a real run, with a link to that run, so that I can trust what I see.
5. As a learner, I want cards built from the same facts, so that review matches what I was taught.
6. As a learner, I want quick questions answered directly with no build, so that small questions stay fast.

**The host agent** (Claude Code, Codex, Hermes, OpenCode)
1. As the agent, I want a router command that tells me mode, medium and first turn, so that I don't guess from keywords.
2. As the agent, I want clear exit codes and next steps (D19.5), so that I never report a half-built lesson as done.
3. As the agent, I want claims-review jobs I can run in a subagent, so that claim checking works without API keys.

**Prax, the maintainer**
1. As the maintainer, I want v2.1 installable side by side and reversible with one link flip, so that trying it costs nothing.
2. As the maintainer, I want a build report that records every gate, measurement and tool version, so that I can audit any lesson later.

## 5. Architecture

### 5.1 Repository layout

```
v2.1/
  package/prax-teach/            # the installable skill (the only thing that ships)
    SKILL.md                     # loader, <= 4k tokens to first teaching word (AC-1.9)
    references/                  # TEACHING.md, LESSON-MODEL.md, PROJECTORS.md, VERIFY.md,
                                 # MEDIA.md, STYLE.md, HOST-ADAPTERS.md, REGISTRY.md
    schemas/lesson.schema.json, claims-review.schema.json, build-report.schema.json
    bin/ptk                      # sh shim -> python -m ptk
    ptk/                         # Python 3.10-3.13 package
      cli.py route.py route_rules.json workspace.py model.py expect.py text.py errors.py
      host.py node.py tts.py
      capture/c_runner.py capture/sandbox.sb
      project/{still,explorer,qa,cards,video,ive}.py
      verify/{values,mutation,visual,media,claims}.py
      state/                     # ported v2 consent engine + schema v2 migration
      templates/{chrome.json, svg/, html/, ive/, video/}
    node/                        # render_markdown.mjs (ported), shoot.mjs (Playwright), package.json + lock
    assets/fonts/                # OFL: Source Serif 4, JetBrains Mono, Caveat (+ LICENSE, sha256)
    lexicon/c.json               # pronunciation lexicon for code tokens
    registry/tools.json          # ported + corrected registry with ranked alternatives (D17.13)
    tests/                       # all tests named below
  lessons/                       # development lessons (exemplars), not shipped
  .state/                        # $PTK_STATE during development (git-ignored)
```

### 5.2 Lesson model (`schemas/lesson.schema.json`, JSON Schema 2020-12)

```
{
  "schema": "prax-teach/lesson@1",
  "id": "one-byte-four-views", "title": "...", "topic": "...", "language": "c",
  "platform": { "captured": true, "sizeof": {...}, "char_signed": true, "endianness": "little",
                "libc": "...", "compilers": {"clang": "...", "gcc-16": "..."} },
  "programs": [ { "id": "p1", "path": "programs/p1.c", "std": "c17",
                  "ub": false, "run": true } ],
  "facts": [ { "id": "f.d", "program": "p1", "kind": "stdout-line|value|derived",
               "value": "66",
               "expect": { "fn": "printf_d", "args": [66] }      // or {"value": ..., "reviewed": true}
               "source": { "compiler": "clang 21.0.0", "cmd": "...", "stdout_sha256": "..." } } ],
  "claims": [ { "id": "c.cast", "text": "...", "kind": "definition|mechanism|rule|caveat|undefined-behaviour|implementation-defined|framing",
                "justification": "...", "sources": [ {"title","url","clause"} ], "facts": ["f.f"] } ],
  "misconceptions": [ { "id": "m.samebits", "statement": "printf reinterprets the same bits for %f",
                        "correction": "c.cast" } ],
  "trace": [ { "id": "s0", "label": "...", "state": { ... }, "reveals": ["f.d"] } ],
  "storyboard": [ { "id": "sc1", "title": "...", "state": "s0",
                    "narration": [ { "text": "...", "claims": ["c.x"], "spoken": "optional respelling" } ],
                    "question": { "prompt": "...", "answer_fact": "f.c" } } ],
  "requested_media": ["still","explorer","qa","cards","video","ive"]
}
```

Rules:
- Every artifact sentence comes from `claims[].text`, `narration[].text` (which cites claims), or `templates/chrome.json`.
- `expect.fn` names a pure function in `ptk/expect.py` (bits, hex, printf_d/u/f/c, ascii, sizeof_from_platform, sum, factorial_frames, …). That module never imports capture code.

### 5.3 Build state machine (`ptk/model.py` holds this diagram inline)

```
draft ─validate─▶ valid ─capture─▶ captured ─project─▶ projected ─verify─▶ claims-pending ─claims check─▶ verified ─package─▶ packaged
  any failure ─▶ failed (exit 1/2/3)    a gate not-run ─▶ incomplete (5)    a fallback used ─▶ degraded (6)
```

### 5.4 CLI contract (`ptk`)

| Command | Purpose |
|---|---|
| `ptk route "<request>" [--workspace DIR] --json` | `{intent, mode, media[], workspace_contract, first_turn, build_needed}` |
| `ptk new <slug> [--dir lessons]` | scaffold `lesson.json` and `programs/` |
| `ptk validate <lesson>` | schema plus reference checks, with JSON-pointer errors |
| `ptk capture <lesson>` | sandboxed compile and run; writes facts and platform |
| `ptk build <lesson> [--only a,b]` | validate, capture, project, run the automatic gates; writes `claims-jobs/` |
| `ptk claims check <lesson>` | validate the reviews against the manifests and finish the status |
| `ptk report <lesson> [--json]` | print the build report |
| `ptk host probe` | which tools and alternatives are runnable now (D17.13) |
| `ptk host setup [--yes]` | lists every download with size, source and sha256, then fetches only with `--yes` |
| `ptk selftest` | all automatic tests |
| `ptk agent-tests` | agent-mediated suite: writes jobs, exits 4 |
| `ptk package [--dry-run]` | build the install tree, plus the discovery check |

**Exit codes** (D19.5):

| Code | Meaning |
|---|---|
| 0 | verified or packaged |
| 1 | a gate failed |
| 2 | host or environment problem |
| 3 | model error |
| 4 | claims-pending |
| 5 | incomplete |
| 6 | degraded |

### 5.5 Environment contract (`ptk/node.py`, `ptk/host.py`)

Every child process gets:
- `HYPERFRAMES_SKIP_SKILLS=1`
- `HYPERFRAMES_NO_UPDATE_CHECK=1`
- HyperFrames telemetry off
- `PLAYWRIGHT_BROWSERS_PATH=$PTK_STATE/browsers`
- `SOURCE_DATE_EPOCH` (taken from the lesson's sha256)

Only these two modules call `subprocess` for external tools.

## 6. Requirements and acceptance criteria (EARS)

Each criterion has an ID and a named test. A work package closes only when all its P0 criteria pass. Stop rule (FREEZE plus D19.4): a round counts as progress when a new AC starts passing. Two rounds in a row with no progress parks the package.

### WP0: Vertical slice and spikes (P0; blocks everything)

Development request (fixed): "Teach me how a switch statement with a missing break falls through, as a still, a narrated video and an interactive video."

- **AC-0.1** When `ptk host setup --yes` runs, ptk shall fetch and pin:
  - Playwright Chromium;
  - HyperFrames 0.8.169 (local npm, under `$PTK_STATE/tools`) and its Chrome;
  - the Kokoro model and voices;
  - `ggml-base.en.bin`;

  recording each sha256, and making no writes outside `$PTK_STATE`. *Test:* `tests/test_host.py::test_setup_inventory_and_paths`.
- **AC-0.2** When `hyperframes render` runs under `capture/sandbox.sb`'s render profile, the DNS, HTTPS and child-connect canaries shall all fail visibly, and the render shall succeed. If Chrome can't start under the profile, ptk shall use `docker run --rm --network none` with the pinned image and the same canaries (E1, E16). *Test:* `tests/test_render_isolation.py::test_canaries_fail_render_succeeds`.
- **AC-0.3** When `whisper-cli` runs on the proof MP4 (converted to 16 kHz mono WAV), ptk shall produce word timestamps. *Test:* `tests/test_media.py::test_whisper_timestamps_on_fixture`.
- **AC-0.4** When the slice lesson builds with `--only still,video,ive` and its claims jobs are reviewed, the report shall be `verified`, with no `not-run` gate. *Test:* `tests/test_slice.py::test_switch_fallthrough_slice` (agent-tests suite).
- **AC-0.5** The slice shall be produced by loading `package/prax-teach/SKILL.md` by direct path, with `ptk` on PATH, and no host registration (D19.3). *Test:* `tests/test_slice.py::test_entry_by_direct_path`.

### WP1: Router and teaching protocol (P0)

- **AC-1.1** When a request names a medium (video, narrated, voice over, animate, interactive video, explorer, cards, Q&A), `ptk route` shall return that medium. *Test:* `tests/test_route.py::test_medium_words` (dev set of 60 or more, including the M1 and M2 cases).
- **AC-1.2** When the request is an ordinary task (fix, rename, write tests), `ptk route` shall return `intent=ordinary_task` and no teaching. *Test:* `test_route.py::test_ordinary_tasks`.
- **AC-1.3** When a teaching request arrives, `ptk route` shall return an explanation-first lesson whose first turn is the complete explanation (with the requested or default medium), never a question, whatever the workspace's AGENTS.md, MISSION.md or NOTES.md say. When those files ask for prediction first, the route shall carry a `workspace_conflict` note naming the file and line, and shall not obey it. A prediction-first turn happens only when the request explicitly asks for a practice mode (quiz, exam-drill, Socratic, "let me predict", "test me"). "Answer now" or "just explain" ends questioning in any mode. *Tests:* `test_route.py::test_explanation_first_in_every_workspace`, `::test_workspace_conflict_reported`, `::test_practice_only_when_asked`, `::test_answer_now_overrides_practice`.
- **AC-1.4** When the request asks for a direct or quick answer, `ptk route` shall return `mode=quick, build_needed=false`. *Test:* `test_route.py::test_quick_no_build`.
- **AC-1.5** The router shall be table-driven (`route_rules.json`), and no function in `route.py` shall have more than 5 branches. *Test:* `test_route.py::test_rule_table_and_complexity`.
- **AC-1.6** When a learner explicitly asks for a practice mode, the protocol shall:
  1. ask one question and end the turn;
  2. classify the attempt as correct, partial or a named misconception;
  3. give exactly one hint or feedback item;
  4. show the artifact;
  5. record one evidence event (with consent).

  When no practice mode was asked for, the protocol shall deliver the complete explanation first, then offer optional practice in one closing sentence, with no question before the explanation. *Tests:* `tests/test_protocol_transcripts.py::test_practice_mode_flow`, `::test_explanation_first_flow` (agent-tests).
- **AC-1.7** In a practice mode, if a trace or storyboard state would reveal the answer to an open question, then the protocol shall hide it until the attempt (T3). *Test:* `test_protocol_transcripts.py::test_no_reveal_before_attempt`.
- **AC-1.8** Modes `quiz`, `exam-drill` (timed GATE MCQ/NAT) and `qa-expand` shall each have a protocol in `references/TEACHING.md` and one transcript test each. *Test:* `test_protocol_transcripts.py::test_modes`.
- **AC-1.10** `references/TEACHING.md`, `SKILL.md` and `ptk/route_rules.json` shall state the explanation-first rule of AC-1.3 and contain no instruction that makes prediction the default. *Test:* `tests/test_lint.py::test_no_predict_first_default`.
- **AC-1.9** The loader path (`SKILL.md`, plus whatever it requires before the first teaching word) shall be at most 4,000 tokens, measured with a fixed tokenizer approximation (characters/4). *Test:* `tests/test_skill_budget.py::test_loader_budget`.

### WP2: Lesson model and capture (P0)

- **AC-2.1** `ptk validate` shall reject schema violations and dangling references (claim → fact, storyboard → state, narration → claim) with JSON-pointer messages, exit 3. *Test:* `tests/test_model.py::test_validation_errors`.
- **AC-2.2** When `ptk capture` runs, ptk shall:
  - compile each program with clang (`-std=c17 -Wall -Wextra -Wformat=2 -fsanitize=undefined,address`) under the capture sandbox;
  - run it twice;
  - store stdout facts with sha256;
  - capture platform facts.

  gcc-16 shall compile for diagnostics only. *Test:* `tests/test_capture.py::test_happy_capture`.
- **AC-2.3** If a compiler warning, ASan or UBSan finding occurs and no claim of kind `undefined-behaviour` covers the program, then capture shall fail with `SanitizerFinding`. Programs marked `ub: true` shall compile but never run. *Tests:* `test_capture.py::test_format_warning_fixture`, `::test_asan_fixture`, `::test_ubsan_fixture`, `::test_ub_program_not_run`.
- **AC-2.4** If the two runs differ, then capture shall fail with `NondeterministicOutput`, showing both outputs. *Test:* `test_capture.py::test_nondeterminism`.
- **AC-2.5** The capture sandbox shall deny network, writes outside its temp dir and process fork (E24). It shall cap stdout and stderr at 1 MB and memory across the process group, and clean up after a timeout or a watchdog kill. *Tests:* `tests/test_security.py::test_capture_denies_network`, `::test_denies_outside_write`, `::test_denies_fork`, `::test_output_cap`, `::test_cleanup_after_kill`.
- **AC-2.6** If `sandbox-exec` is unavailable, then capture shall exit 2 with `SandboxUnavailable` and run nothing. *Test:* `test_security.py::test_refuse_without_sandbox`.
- **AC-2.7** Every fact shall have an `expect`. If capture differs from expect, then the build shall fail with `ExpectationMismatch`, showing both. *Test:* `tests/test_model.py::test_expectation_mismatch`.
- **AC-2.8** `ptk/expect.py` shall import nothing from `ptk.capture`. *Test:* `tests/test_lint.py::test_expect_independent`.

### WP3: Still projector and style (P0)

- **AC-3.1** When the still projector runs, it shall emit wide and portrait SVG plus 2x PNG in light and dark. Every value comes from facts, and every sentence comes from claims or `chrome.json`. *Test:* `tests/test_still.py::test_variants_and_sources`.
- **AC-3.2** The style shall use only the bundled OFL fonts, with `font-variant-numeric: lining-nums tabular-nums`. Tesseract OCR of every bit and number cell shall read the expected digits. *Test:* `tests/test_visual.py::test_ocr_lining_digits`. An old-style-numeral fixture shall fail this test.
- **AC-3.3** Text contrast shall be at least 4.5:1 and rules and borders at least 3:1, in both themes, computed from the rendered tokens. Correction red and note blue shall differ in lightness by at least 15 L* in dark mode (V12). *Test:* `test_visual.py::test_contrast`.
- **AC-3.4** At 390 and 1440 px in both themes, no element shall overflow its container, no text shall render under 11 CSS px, and every storyboard key node shall be fully inside the visible area with no inner scroll (D20.3). *Test:* `test_visual.py::test_no_overflow_min_size`.
- **AC-3.5** Math shall render through MathJax `tex2svg` into the SVG, with no raw TeX left in the output. *Test:* `test_still.py::test_math_svg`.
- **AC-3.6** During the visual verify, any outbound request shall fail the build (`OutboundRequest`). *Test:* `test_visual.py::test_no_network`.
- **AC-3.7** Every value mutation applied to a still (from the mutation suite) shall fail `verify/values.py`. *Test:* `tests/test_mutation.py::test_still_value_mutations`.

### WP4: Explorer, Q&A expander, flash cards (P0)

- **AC-4.1** The explorer shall be one HTML file with the E20 CSP, keyboard operable with visible focus, respecting `prefers-reduced-motion`, with a complete `<noscript>` explanation. *Test:* `tests/test_explorer.mjs::test_a11y_csp_noscript`.
- **AC-4.2** For every input in the explorer's declared domain, and after every control step, the displayed values shall equal the `ptk/expect.py` function results. Each control's effect is asserted, not just reached (D20.4). *Test:* `test_explorer.mjs::test_full_domain`.
- **AC-4.3** The Q&A expander shall open layers in order, route each wrong option to a named misconception with its correction claim, and expand every layer when printed. *Test:* `tests/test_qa.py::test_layers_misconceptions_print`.
- **AC-4.4** Cards shall be emitted as Markdown and `.apkg`. Answers equal facts, GUIDs are stable across builds, and re-import creates no duplicates. *Tests:* `tests/test_cards.py::test_apkg_contents`, `::test_stable_guids`, `::test_anki_import` (`not-run` if no Anki).
- **AC-4.5** Card sets shall include misconception cards built from `misconceptions[]`. *Test:* `test_cards.py::test_misconception_cards`.
- **AC-4.6** When a control changes state, every sentence bound to that state shall be recomputed from the live state, and no sentence shall describe the default after a change (D20.4). *Test:* `test_explorer.mjs::test_prose_follows_state`.
- **AC-4.7** At 390 px, every key node of the explorer's mechanism shall be fully visible with no inner horizontal scroll (D20.3). *Test:* `test_explorer.mjs::test_key_nodes_visible_390`.
- **AC-4.8** Every HTML artifact shall work when opened directly from disk (`file://`) in Chrome, with no server (D20.9). *Test:* `test_explorer.mjs::test_file_protocol`.

### WP5: Narrated video (P0)

- **AC-5.1** The video projector shall generate one HyperFrames sub-composition per storyboard scene, and `hyperframes check` shall pass with 0 errors and 0 warnings. *Test:* `tests/test_video.py::test_per_scene_check` (slow).
- **AC-5.2** TTS shall synthesise every narration segment in one `kokoro-onnx` process, applying `lexicon/c.json` respellings. If Kokoro is unavailable, ptk shall fall back to `hyperframes tts`, then `say`, and status shall be `degraded`. *Tests:* `tests/test_tts.py::test_batch_one_process`, `::test_lexicon_applied`, `::test_fallback_degraded`.
- **AC-5.3** Cue times shall be scheduled from measured segment durations. *Test:* `tests/test_video.py::test_schedule_from_durations`.
- **AC-5.4** The media gate shall require:
  - integrated −16 ± 1 LUFS and true peak ≤ −1 dBTP;
  - 1920x1080 at 30 fps;
  - H.264 plus AAC;
  - a WebVTT captions file and a chapters file.

  *Test:* `tests/test_media.py::test_media_thresholds`, with out-of-range fixtures failing.
- **AC-5.5** The sync gate shall compare whisper word timestamps from the final MP4 with each cue's start and end, within 0.5 s, and non-code WER at most 10%. Shifted-audio, truncated-speech and mispronounced-token fixtures shall each fail. *Tests:* `test_media.py::test_sync_gate`, `::test_sync_fixtures_fail`.
- **AC-5.6** Snapshots at each scene midpoint shall pass the AC-3.4 overflow, size and key-node visibility checks. Each summary view shall be paired with its mechanism step (D20.5). *Test:* `test_video.py::test_scene_snapshots`.
- **AC-5.7** Narration, captions, chapter titles and transcript shall not state the answer to an open storyboard question before its answer cue (M20). *Test:* `test_video.py::test_no_answer_leak_text`.

### WP6: Interactive video explorer (P0)

- **AC-6.1** The IVE page shall play the MP4 with a WebVTT `metadata` track whose cues carry `{scene_id, state_id}`. Each question gets a question cue and an answer cue (D18.2). *Test:* `tests/test_ive.mjs::test_cue_track`.
- **AC-6.2** When the learner pauses, seeks or jumps to a chapter, the page shall show the explorer at the last state already shown. The video clock is the only source of time. Chapters are half-open windows `[start, end)`, and a seek within one frame of a boundary resolves to the later window (D20.6). *Test:* `test_ive.mjs::test_pause_state`.
- **AC-6.3** When paused 0.1 s before an answer cue, the DOM, the alt text and the transcript shown so far shall not contain the answer. *Test:* `test_ive.mjs::test_no_leak_before_answer`.
- **AC-6.4** The page shall offer captions on and off, a chapter list and a synced transcript with click-to-seek. Without JS, it shall show the poster sequence and the full transcript. *Test:* `test_ive.mjs::test_controls_and_noscript`.
- **AC-6.5** Navigation in the IVE shall never write learner-attempt events, only `navigation` events (schema v2). *Test:* `tests/test_state.py::test_navigation_not_attempt`.
- **AC-6.6** The IVE shall run a FILM / EXPLORE / RETURN state machine. In EXPLORE, every lesson's IVE shall offer at least one live control that changes the shown state (step-through alone does not pass, D23.5), and live edits are visibly separate from the recorded film. RETURN resumes the film at the paused time with the film's state, not the edited state (D20.6). *Test:* `test_ive.mjs::test_film_explore_return`, run on all four lessons.
- **AC-6.8** By default the IVE film plays through and explains; it does not stop at a prediction. The prediction pause runs only when the learner turns on practice mode (a visible toggle, off by default). *Test:* `test_ive.mjs::test_explanation_first_default`, `::test_practice_mode_pauses`.
- **AC-6.7** The IVE, including the MP4 and every WebVTT track, shall work when opened directly from disk (`file://`) in Chrome (D20.9). *Test:* `test_ive.mjs::test_file_protocol`.

### WP7: Claims gate (P0)

- **AC-7.1** `ptk build` shall write one claims job per lesson for each of 3 independent reviewers, plus up to 12 mutation jobs paired with clean controls. Each job holds a manifest: the sha256 of the model, every artifact text, the sources and the rubric version. *Test:* `tests/test_claims.py::test_jobs_and_manifest`.
- **AC-7.2** `ptk claims check` shall reject a review whose manifest hash doesn't match the current inputs. *Test:* `test_claims.py::test_stale_review_rejected`.
- **AC-7.3** Every teaching sentence in every artifact shall map to a claim ID. Any that doesn't fails with `ClaimsUnmapped`. Fixed UI strings must be in `chrome.json` (E4). *Tests:* `test_claims.py::test_unmapped_sentence`, `tests/test_lint.py::test_no_literal_sentences_in_templates`.
- **AC-7.4** Malformed, empty or refusal reviews shall be retried once with a schema reminder, then fail (`ClaimsReviewInvalid`). *Test:* `test_claims.py::test_invalid_reviews`.
- **AC-7.5** Against the real reviewer subagent, the suite shall catch at least 90% of claim mutations and 100% of value mutations, and accept at least 95% of controls. Schema rejections are counted separately. *Test:* `tests/test_mutation.py::test_real_reviewer_rates` (agent-tests).
- **AC-7.7** Every claim that cites a source (C17/N2176 clause, a book section, a manual page) shall have the cited passage stored with the lesson under `sources/`, with its sha256 in the job manifest. Jobs carry the passage, and the rubric tells reviewers to judge only against it. A cited passage that is missing fails the build (`SourceExcerptMissing`). *Test:* `test_claims.py::test_source_excerpts_bound`.
- **AC-7.8** `verified` requires all 3 lesson-job reviews to accept. Any disagreement is listed in the report with each reviewer's finding, and the status is `failed` until the claim is fixed or the rubric clarified. *Test:* `test_claims.py::test_three_reviewers_agree`.
- **AC-7.9** The rubric shall say how transcript, chapter-title and context sentences are judged, with one worked example each. *Test:* `test_claims.py::test_rubric_sentence_classes`.
- **AC-7.6** The claim "printf never changes the bits; the format string only decides how to read them", applied to `printf("%f", (double)a)`, shall be rejected by the real reviewer. *Test:* `tests/test_regression_f_cast.py::test_same_bits_claim_rejected` (agent-tests, **CRITICAL**).

### WP8: Packaging, hosts, ports (P0)

- **AC-8.1** `ptk package` shall produce an install tree of at most 5 MB (fonts included), with no `/Users/` strings, no `__pycache__` and no nested `SKILL.md` other than the root. *Test:* `tests/test_packaging.py::test_tree_limits`.
- **AC-8.2** Under throwaway `HOME`s, Claude Code, Codex, Hermes and OpenCode discovery shall each see exactly one `prax-teach` entry. *Test:* `tests/test_hosts.py::test_one_entry_per_host`.
- **AC-8.3** The ported v2 renderer shall emit inline SVG, MathJax SVG and `<video>` with `<track>`, keep source-hash provenance, and pass on Node 22 and 24. *Tests:* `tests/test_render.mjs::test_svg_math_video`, run under both Node versions.
- **AC-8.4** The state engine shall read v1 state unchanged, migrate to schema v2 with `navigation` and `evidence` kinds, and keep the v2 consent rules. *Tests:* `tests/test_state.py::test_v1_reads`, `::test_migration`, plus the ported v2 tests listed in `plan/PROTECTED-MAP.md`.
- **AC-8.5** `registry/tools.json` shall rank alternatives per artifact type, using report 05's top entries, each with a binary probe and a fallback order. `ptk host probe` shall report what's runnable now. *Test:* `tests/test_registry.py::test_ranked_with_probes`.
- **AC-8.6** Install and rollback per host shall be tested: the rollback restores the v2 link and the learner-state snapshot, and prints how many events it lost. *Test:* `tests/test_hosts.py::test_install_rollback`.
- **AC-8.7** Only `ptk/node.py` and `ptk/host.py` shall call `subprocess` for Node or external tools, and the env contract in §5.5 shall be applied. *Test:* `tests/test_lint.py::test_subprocess_boundary`, `tests/test_host.py::test_env_contract`.
- **AC-8.8** No `except Exception` and no bare `except:` anywhere in `ptk/`. *Test:* `test_lint.py::test_no_broad_except`.

### WP9: Exemplars (P0)

- **AC-9.1** "One byte, four views" (with the `%f` cast claim corrected and the `m.samebits` misconception) shall build all six media and finish `verified`. *Test:* `tests/test_exemplars.py::test_one_byte` (agent-tests).
- **AC-9.2** "factorial(3) on the call stack" shall build all six media from a trace, and finish `verified`. *Test:* `test_exemplars.py::test_factorial_stack` (agent-tests).
- **AC-9.3** Screenshot review of both exemplars shall record verdicts for the 6 non-automated aesthetics items in the build report, judged against the accepted Neuron Atlas reference (D20.1). *Test:* `test_exemplars.py::test_design_verdicts_recorded`.
- **AC-9.4 (P1)** The Neuron Atlas neuron lesson (one weighted sum, bias and ReLU, with toy values) shall build through v2.1 in all six media and finish `verified`, as the unrelated-subject test (D20.10). *Test:* `test_exemplars.py::test_neuron_unrelated_subject`.

### WP10: Visual quality (P0, v2.2 Track B)

Each measure is a check script written and independently reviewed before the visual work it measures.

- **AC-10.1** Every lesson's wide still shall be landscape: width ≥ 1.5 × height. It is figure-led: the elements marked `data-role="figure"` cover ≥ 50% of the canvas, and the still carries no code block and no hash text (provenance moves to the caption, alt text and metadata). A portrait variant exists for phones. *Test:* `tests/test_still_layout.py`.
- **AC-10.2** Each lesson shall draw its mechanism, with every drawn value taken from captured facts: switch, a control-path figure; factorial, a stack column with return values flowing up; one-byte, all 4 bytes of `a` with the low byte marked, plus the double's 8 bytes; neuron, its existing panels. *Test:* `tests/test_mechanism_figures.py`.
- **AC-10.3** In the 1080p video: output text is at least as large as its code line; teaching text is ≥ 28 px; the mechanism figure covers ≥ 55% of the frame in mechanism scenes; no empty region larger than 20% of the frame. On a 390 × 844 viewport the IVE shows the figure above the fold. *Test:* `tests/test_video_layout.py`.
- **AC-10.4** Every explorer and IVE sentence that describes state shall be bound to live state and re-checked after each control step. The neuron `z = 1.11022e-16` case is explained as binary64 rounding. *Test:* `tests/test_live_captions.py`.
- **AC-10.5** Narration shall be ≤ 170 words per minute per line, measured from the audio; contain no phrase from the hedge list outside claims that need it; repeat no sentence verbatim; and say code tokens from the lexicon correctly ("unsigned char"). Values appear on screen when spoken. *Test:* `tests/test_narration.py`.
- **AC-10.6** An independent five-lens reviewer scores every lesson Looks ≥ 8 and Explanation ≥ 8 (reviewer judgments), and Prax's visual verdict per lesson against Atlas is recorded. Prax's verdict is the final gate. *Evidence:* `reviews/v2.2-five-lens.md`, Prax's verdict.

### WP11: Learner-state privacy (P0, v2.2 Track A6)

- **AC-11.1** When the workspace sits inside a folder Google Drive for desktop backs up, `ptk.state` shall refuse to create learner state unless the learner opts in explicitly; the opt-in is recorded with consent. *Test:* `tests/test_state_privacy.py::test_drive_folder_refused_by_default`.
- **AC-11.2** The consent text shall name Google Drive when it backs up the folder. Warnings say "Google Drive", never "macOS backup". *Test:* `::test_consent_names_drive`.
- **AC-11.3** `delete` shall report every surviving copy it can find outside the workspace (for example in `.tmp.driveupload`), and shall not report `all_state_deleted` while one exists. *Test:* `::test_delete_reports_surviving_copies`.
- **AC-11.4** Read-only commands shall write nothing, extended attributes included, when consent is absent or withdrawn. *Test:* `::test_read_only_writes_nothing_without_consent`.

### P1 (after acceptance, D17.16)

- Chapter thumbnails.
- Provenance "show me the real run" links.
- `ptk report --html`.
- LLDB traces.

### P2 (future)

- The compile-and-trace server.
- Topic packs.
- The Manim math track.
- cpx integration.
- A Linux `bwrap` sandbox.

## 7. Success metrics

- **Leading** (during the run, from the build reports):
  - share of WP acceptance criteria passing;
  - number of `not-run` gates (target 0);
  - mutation catch rates;
  - the media measurements.
- **Lagging** (after acceptance, needs Prax):
  - his live usability session completed;
  - lessons he requests that build `verified` on the first try (target ≥ 80% across his first 10 requests);
  - lessons where he reports a wrong fact (target 0).

## 8. Assumptions (made autonomously; overturnable)

1. **Font choice:** Source Serif 4, JetBrains Mono and Caveat, all OFL, fetched in setup from their upstream GitHub releases. Source Serif 4 supports lining figures via `lnum`.
2. **Whisper model:** `ggml-base.en` is accurate enough for the sync gate. If WER fixtures fail on clean audio, use `small.en` (about 466 MB) instead.
3. **HyperFrames:** the 0.8.169 sub-composition API matches the proof's usage.
4. **Hosts:** Hermes and OpenCode discovery can be simulated with throwaway `HOME`s and their documented skill paths, as listed in the reports.
5. **Anki:** if no Anki CLI or package is present, the import test reports `not-run`, which is allowed only for that one test. It never counts for the AC-0.4 slice.

## 9. Open questions

All of these are non-blocking for implementation.

- **For Prax:** approve or edit `plan/ACCEPTANCE-PROPOSAL.md` §1–§8, including the install-path amendment and the stop-rule interpretation.
- **For Prax:** a live usability session, explanation-first (usability feedback only; never a substitute for correctness checks).
- **For Prax:** the BasicTeX or Typst install for Manim math (P2).

## 10. Phasing and budget

- **Order:** WP0 → (WP1 ∥ WP2) → (WP3 ∥ WP4 ∥ WP5 ∥ WP7) → WP6 → WP8 → WP9.
- **Budget:** 18 implement-and-review rounds in total, and at most 3 per package. Two rounds in a row with no newly passing AC park a package, and its dependents stop.
- **v2.2 repair run (FREEZE-v2):** Track A (A1 → A2 → A3–A6; WP1 amendments, WP7 AC-7.7 to 7.9, WP11) at most 5 rounds; Track B (WP10, AC-6.6, AC-6.8) at most 5 rounds; at most 2 rounds per deliverable. A3–A6 and Track B run in parallel on separate files after A1 and A2.
- **Templates:** to avoid merge conflicts, the still lane owns `templates/svg/` and the HTML lane owns `templates/html/` and `templates/ive/`.
