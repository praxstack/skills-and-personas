# Acceptance proposal (needs Prax's approval to become FREEZE v2)

Status: PROPOSED on 2026-10-18. It does not change the frozen evaluator. Until Prax approves it, these checks run only as the candidate's internal tests.

## Why

Codex and the spec reviewer both found that the frozen evaluator can pass while the product fails. The routing holdout plus two known exemplars could pass while new lessons come out wrong. "World-class" also has no rule that decides pass or fail.

## Proposed additions

1. **Unfamiliar end-to-end set.**
   - 6 requests that no implementer sees. Each one asks for one medium, and together they cover all six artifact types.
   - They're written by Prax, or written now and hashed like the holdout.
   - Each must produce a build report with every gate `passed` and none `not-run`.
2. **Media thresholds.**
   - Integrated loudness −16 ± 1 LUFS, true peak ≤ −1.0 dBTP.
   - Every caption cue starts within 0.5 s of the spoken word.
   - Word error rate ≤ 10% on non-code words.
   - 1080p30, H.264 plus AAC, with a WebVTT captions track and a chapters track present.
3. **Correctness.**
   - 100% of value mutations and at least 90% of claim mutations are caught, using the real reviewer.
   - The `%f` "same bits" regression must fail.
4. **Aesthetics rule.** Report 02's 15-item still-explainer bar, of which 9 items are automated:
   - contrast ≥ 4.5 for text and ≥ 3 for rules and borders;
   - lining numerals, checked by OCR digit reading;
   - no overflow at 390 and 1440 px;
   - light and dark variants;
   - portrait variant;
   - bundled fonts only;
   - no outbound requests;
   - alt text present;
   - figure source linked.

   The other 6 items are reviewed by screenshot, and the verdicts are written into the report. Prax judges the final look of both exemplars against the accepted Neuron Atlas reference (D20.2), because gates passed a course he called horrible.
5. **Teaching protocol.** The scripted multi-turn transcript tests pass. One live predict-first session with Prax is a human step, recorded but not automated.
6. **Hosts.** Install and rollback are tested on Claude Code, Codex, Hermes and OpenCode, with exactly one entry each.

7. **FREEZE amendment: install paths.** After acceptance, allow writes to:
   - `~/.agents/skill-library/prax-teach-v2.1/` (the install);
   - `~/.local/share/prax-teach/` (user-scope venvs, models and the pinned HyperFrames install, fetched only by `ptk host setup` with a yes);
   - the `~/.agents/skills/prax-teach-v2` symlink. Prax performs the flip, or approves it at the time.
8. **Stop-rule interpretation.** "Newly passing acceptance check" in FREEZE means a newly passing EARS criterion in `spec/SPEC.md` for that work package. The hidden holdout runs only at acceptance.

## Approval

Reply "approve acceptance v2" to adopt this as FREEZE v2, or name the items to drop.
