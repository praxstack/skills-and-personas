# External inputs: three independent sessions (read 2026-10-18)

Treated as evidence with less context than this run. None of them overrides FREEZE.md. Each adopted idea is a two-way door, recorded as D20.x.

## Sources

1. **Claude Code session export:** `~/.claude/projects/-Users-prax/memory/2026-10-18-105839-...txt`.
   - Audited the v2 ZIP and ran a four-vendor council (Codex GPT, Grok, Cursor Composer, Claude Opus).
   - Built an uncommitted media-routing fix on `candidate/media-routing-20261018`, in the worktree `~/Developer/skills-and-personas-recovery-20261016/.worktrees/media-routing-20261018`. It took the registry from 38 to 41 tools, with 65 routing tests and 13 registry tests passing.
   - Outputs: `~/Developer/prax-teach-evaluation-20261016/review-20261018/`.
2. **Codex session:** `~/codex-session-01a14ba6-d02a-7180-a198-5047ec3cea8b.md`.
   - Built a ten-chapter "neuron to deep learning" course, which Prax rejected as "looks horrible" even though every gate passed.
   - Ran a MoA review. Its verdict: mostly an execution failure, plus missing art direction, one runtime, and no proven video or TTS.
   - Then ran its own CEO, eng, spec, implement and review loop. The result was **Neuron Atlas**, one neuron lesson in six formats: an 83 s Manim CE film with Kokoro narration via `hyperframes tts`, stills and an explorer. Prax said it "looks good".
   - Outputs: `~/Developer/prax-teach-visual-audit-20261018/production-v2/` (bundle zip 16.7 MB) and `council-next-steps-20261018/CONCLUSION.md`.
3. **Claude desktop session `session_019X3PnGRsDY2WNFxYmXJdAk`:** not reachable from this session. It's neither a local session nor a visible cloud peer. Prax needs to export it or give its link.

## Adopted (D20.x)

| ID | Idea (source) | Why | Where |
|---|---|---|---|
| D20.1 | **Neuron Atlas is the accepted visual reference** (Codex). The dark theme takes its palette and type: navy ground, lavender, salmon and mint accents, sans display plus mono, three-panel mechanism layout. | Prax approved it. That's stronger evidence of his taste than any gate or vote. | STYLE.md, WP3 (dark theme tokens), WP9 |
| D20.2 | **Taste is a human step** (both). Gates passed the course Prax called horrible, so acceptance needs his verdict on the exemplars against the Atlas reference. | Gates can't measure taste. | ACCEPTANCE-PROPOSAL §4 |
| D20.3 | **Mechanism visibility, not page overflow** (Codex). Every storyboard "key node" must be fully inside the visible area at 390 px and 1440 px, with no inner scroll. | The Codex phone layout scrolled the neuron output off-screen while the overflow test passed. | AC-3.4, AC-4.7, AC-5.6 |
| D20.4 | **Controls assert their effect, and prose follows the live state** (Codex). Each control step checks the displayed values against `expect`, and every sentence under a control is recomputed from state. | "58 states" were endpoints with no assertions, and the paragraph kept describing the default after the controls moved. | AC-4.2, new AC-4.6 |
| D20.5 | **Mechanism, not metrics** (Codex). Every summary view (loss, output, totals) is paired with the mechanism step that produced it. This is a reviewer rubric item. | The training chapter showed falling loss but never the network. | LESSON-MODEL rule, claims and design rubric (WP7) |
| D20.6 | **The video clock is the single source of truth** (Codex). Chapters are half-open windows `[start, end)`, and seeks allow one frame of tolerance for browser time rounding. A FILM / EXPLORE / RETURN state machine means live edits never look like they change the film. | Codex hit a real bug where chapter seeks landed on the wrong side of a boundary. | AC-6.2 refined, new AC-6.6 |
| D20.7 | **"Answer now" beats predict-first** (Codex, Prax's own words). An explicit "answer now", "just explain" or "build the full course" overrides the workspace's predict-first default. | Prax turned down a prediction question and asked for the course directly. | AC-1.3 amended |
| D20.8 | **Narration is a layer over a visual** (Claude export). Negative fixtures: "promo video" stays ordinary, and "narrated animation" means video plus narration, never audio only. | It stops narration-only routing and false positives. | WP1 dev set (AC-1.1) |
| D20.9 | **Everything works from `file://`** (Claude export). Every HTML artifact, including MP4 plus WebVTT tracks, is tested opened directly from disk in Chrome. | The v2 Visual Lab only mounts over HTTP. | new AC-4.8, AC-6.7 |
| D20.10 | **Test on an unrelated subject** (both). Rebuild the Neuron Atlas neuron lesson through v2.1 as a non-C exemplar. | It shows the compiler isn't C-only. It also compares v2.1 directly with the output Prax accepted. | new AC-9.4 (P1) |
| D20.11 | **Pick the renderer for the job** (Codex). Manim CE 0.22 (no LaTeX) is a valid film renderer for maths and mechanism scenes, and HyperFrames for code traces. The video projector interface is renderer-neutral. | Codex shipped an accepted film with Manim. | registry ranking, WP5 interface (P1 for the Manim backend) |
| D20.12 | **Don't port the known traps:** v2's static-only validator, which rejects scripts; the checkbox inputs v2's renderer emits but its validator rejects (finding 48); self-approving counts (the 41-tool registry approved itself); hardcoded Playwright paths. | All four were found by the other sessions. | WP8 tests |
| D20.13 | **Five review lenses for code review and acceptance** (Codex): maths, explanation, looks, interaction, media and portability. | Gives each round of review full coverage. | the review loop |

## Not adopted

- **The 41-tool registry from the media-routing branch.** Its count approved itself. v2.1 ports the 38 tools and corrects them (D20.12).
- **Kokoro only through `hyperframes tts`.** v2.1 runs kokoro-onnx in one process (AC-5.2), with `hyperframes tts` as the fallback. Both sessions confirm Kokoro needs its own venv plus `HYPERFRAMES_PYTHON` for the HyperFrames route.
- **Continuing the neural-network course as the next slice.** Prax's goal is C for GATE 2027. Neuron Atlas is used only as the reference and as the unrelated-subject test.

## Needs Prax

- **Which of the three candidate lines is the one to keep?** Recommendation: v2.1 is the integration line, and Neuron Atlas is imported as the taste reference and second exemplar. The media-routing branch is superseded, but its routing fixtures come into WP1.
- **Export of `session_019X3PnGRsDY2WNFxYmXJdAk`** if it should be included.
