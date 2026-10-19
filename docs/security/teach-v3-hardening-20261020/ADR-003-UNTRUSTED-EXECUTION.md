# ADR-003: fail closed before executing authored lesson code

Status: accepted for this repair branch
Date: 2026-10-20

## Context

The lesson checker evaluated lesson JavaScript and ran extracted Python and
C/C++ directly on the user's host. Browser renderers also execute the lesson
page. A VM language context is not an operating-system security boundary, and
a command timeout is not a sandbox.

## Decision

- Default code checking is structural and reports authored code as unverified.
- Host execution requires the explicit `--trust-authored-code` flag after the
  user or operator has reviewed every lesson and include.
- Course extraction, narration, and course tests fail closed unless that trust
  decision is supplied.
- Third-party or learner-supplied executable lessons must use an external
  disposable sandbox with no credentials, no network by default, a confined
  filesystem, and CPU, memory, process, time, and output limits.
- The trust flag is an interim compatibility path. It is not described as a
  sandbox and does not certify hostile content as safe.

## Consequences

- Routine validation no longer silently runs authored Python, C++, or lesson
  JavaScript on the host.
- Reviewed first-party course workflows need one explicit flag.
- The bundled Docker adapter now isolates the whole code checker, including
  JavaScript loading, compilation and program execution. Its setup and limits
  are documented in the explorable sandbox guide. Whole untrusted-course
  rendering remains behind the external-sandbox/review boundary.

## Rejected alternatives

- Treating Node `vm`, Chromium, or a timeout as a sandbox: none constrains host
  file, process, credential, and network access as required.
- Silently trusting content because it came from a course manifest: manifests
  and the files they name are untrusted inputs.
