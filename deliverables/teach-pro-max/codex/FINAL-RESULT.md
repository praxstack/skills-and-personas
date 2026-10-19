# Prax Teach v3 — delivered development candidate

The implementation and real review artifacts are delivered. This is not an accepted release and nothing is installed. Final product source: `0d20ff7722910d12256240af0897070255cfc4f3`.

Three public non-C lessons—language, probability and diffusion—each have a mechanism-led landscape still, an explorer, layered Q&A, cards, narrated video and interactive video. The connected course and complete static explanation are included. Open `index.html` after extracting the full review ZIP.

## Verified

- Fixed private routing: **24/24**, versus **23/24** for the byte-identical original/current general-teacher baselines.
- Fixed private E2E: **52/56**, eight subjects. Four required human listening verdicts are **NOT_RUN**, so release readiness is **false**. Baseline E2E was not run; no comparative E2E improvement is claimed.
- Controls, reported separately: **8/8 valid accepted**; **8/8 intended invalid propositions detected**. One blind reviewer and a small set do not establish population reliability.
- Actual six-format/browser exports: **173/173**; explanation-first, consent and resume: **65/65**. Real MP4s, static fallback, desktop/mobile and captions were exercised.
- Framework regression passed with required browser/video tools. The two downstream-site-only tests are expressly inapplicable; the standalone course was exercised directly.
- Preserved legacy distribution: **8/8 gates**, including 238 Python tests, 20 Node tests, 12 registry tests and 41 HTML parity pairs. Runtime failures and their repairs remain in `evidence/distribution/REPORT.md`; no source, lock, digest or validator relaxation was used.
- Independent numeric audit: 53,550 probability states, 14,091 diffusion states, 28,182 drawing-width checks. Original authored wording/timing defects and after-repair evidence are retained.
- One independent reviewer scored final public stills/explorers/sampled frames 8 for Looks and Explanation, with Atlas at 9. This is not Prax's acceptance or a learning-outcome study.

## What remains

1. Listen to the four private evaluation videos and record actual verdicts. The local listening page is provided separately; its lessons/prompts are deliberately absent from this public pack.
2. Prax's visual and voice acceptance. If a concrete failure is found, retain it and repair only that defect within the remaining frozen budget. Do not label an unheard voice natural or a machine score world-class.
3. The optional C adapter remains unaccepted and separate. Its reports retain struct OCR, protected-check conflicts and missing real four-lesson claims acceptance. It is not required for ordinary teaching.
4. The older standalone-course diagnostic is still 20/21 because it expects automatic persistence. Its checker was not changed. The current explicit-consent behavior has separate evidence.

## Versioning and limits

`RUNS.json` records four completed candidates and their exact commits. The final candidate gains two strict UI criteria with no protected regression. Governing changes preceded product changes; frozen checks were not changed during candidate runs. Native Grok batches were bounded; Claude quota and paid API fallback were not used. The private bank remains private, and no real learner/Drive files or installed skill links were changed.

Codex CLI settings are separately applied and tested. Arbitrary new message-box borders/header are not established supported settings. The report contains a backup and rollback route.

Sources/metadata are committed; new rendered media and C working fixtures are GitHub prerelease assets. No historical archive migration, history rewriting or install is implied. `RELEASE-ASSETS.json` lives outside the archives it hashes. See `REPRODUCE.md`, `IMPLEMENTATION.md`, `governance/FREEZE.md` and the raw receipts for exact scope.
