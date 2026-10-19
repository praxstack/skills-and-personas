# Error and recovery review

Status: Section 2 inspected. Candidate behavior is proposed, not implemented. No state, lesson or installed package was changed.

## Existing typed runtime failures

Source: scripts/praxteach/errors.py and cli.py:475-487. These are observed error contracts; no new execution test is claimed.

| Path | Failure / exception | Existing handling | Proposed user experience |
|---|---|---|---|
| Initialize or update state | ConsentRequired, exit 3 | CLI prints error; initialization checks consent before writing | Continue ephemerally; do not imply saving succeeded |
| Destructive state operation | ConfirmationRequired, exit 4 | CLI rejects missing confirmation | Preview exact state scope; retain sibling lessons as approved |
| Resolve/read/write state | SafetyError, exit 5 | Fail closed for unsafe paths, permissions, identity changes | Explain that saved progress is unavailable; never bypass path checks |
| Input/schema/projected state | ValidationError, exit 6 | CLI rejects unsupported or inconsistent data | Report the specific unsupported state; preserve bytes and avoid invented recovery |
| Missing state | StateNotFound, exit 7 | CLI reports missing workspace or required file | Distinguish never initialized from damaged existing state; never invent history |
| Filesystem/encoding | OSError or UnicodeError, exit 8 | CLI prints a safe-operation failure | Say changes were not confirmed saved; allow teaching without new persistent writes |
| Empty teaching request | ValueError translated into ValidationError | route dispatch validates input | Ask for the missing topic, not a full intake interview |
| Visual route/receipt mismatch | ValidationError | Rejects malformed or pre-claimed checks | Repair actual route/output consistency; do not edit receipts to claim success |

Broad exception catches in io.py:210,310,317 close file descriptors and re-raise. These are cleanup paths, not swallowed failures; do not rewrite them merely to remove the word Exception.

## New behavior boundaries

| Boundary | Failure | Required handling and evidence |
|---|---|---|
| Save explicit preferences or resume pointer | Existing learner schema rejects extra fields | A versioned continuity record needs guarded operations; never stuff preferences into legacy learner.json or fabricate scored observations |
| Resume | show_state succeeds after consent withdrawal | Inspect returned active-consent flag before automatic use/update; successful inspection is not authorization |
| Render | Tool missing, timeout, refusal, empty output or invalid artifact | Distinguish each host-reported result; exact exception class is adapter-dependent, not invented here |
| Verify visual meaning | Wrong labels, causal arrows, formula mapping or misleading contrast | Reject/repair the explanation; a successful render is insufficient |
| Inspect delivery | Browser or playback unavailable | State that rendering/interaction inspection was unavailable; do not claim it was checked |
| Requested animation or interaction unavailable | No suitable capability can produce it | Pending user decision below; do not silently call a static artifact the requested animation |
| Repair | Repeated failure or no semantic improvement | Bound automatic repairs, preserve useful material and tell learner the limitation; no unbounded retry loop |
| Optional check skipped | No performance evidence | Save coverage/continuation only when consented; leave mastery unknown and do not create scheduler ratings |

For host failures, save only minimal diagnostics needed for the requested artifact; do not log whole learner messages, keys or unrelated context. The skill remains portable and does not invent a universal TimeoutError type for every tool provider.

## Proposed tests for implementation plan
- Missing, declined and withdrawn consent prevent new state writes.
- A continuation update preserves evidence counts and inferred mastery when no practice occurred.
- Unsupported/malformed continuity data produces a named error, leaves bytes intact and never overwrites valid prior state.
- Missing preferred tool, failed alternate tool, empty output and uninspectable output produce distinct honest delivery responses.
- Explicit requested animation is not mislabeled as delivered when only a static fallback exists.
- Skipped optional practice does not block explanation or resumption.
- Forget-progress leaves sibling lesson hashes unchanged.

## Resolved delivery-policy decision
After suitable alternatives have been tried, should a requested rich visual that cannot be produced fall back to a complete static explanation with a clear limitation, or pause and ask the learner to choose a different delivery method?

Recommendation: deliver the best accurate static explanation and disclose the missing capability. Never represent that as fulfilling an explicitly required animation/interaction. If the learner said a particular medium is essential, pause rather than substitute.

User accepted the recommended fallback policy, including the essential-medium exception.
