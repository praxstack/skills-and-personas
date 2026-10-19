# Teach v3 hardening specification

## Security invariants

1. A lesson, course manifest, transcript manifest, workspace, or health report is untrusted input.
2. Untrusted paths cannot select bytes outside their declared root, including through symbolic links, hard links, traversal, absolute paths, or validation-to-use swaps.
3. Credentials are sent only to an exact approved origin. Generic resource URLs never inherit authenticated cookies.
4. Network retrieval rejects unsafe schemes and private destinations, rechecks redirects, and enforces transfer and artifact budgets.
5. Routine validation does not execute authored code with the user's host privileges. Execution requires an explicit sandbox boundary.
6. Public upload binds validation, hashing, and upload to the same regular file.
7. Learner journals are private regular files in a private directory and cannot be redirected through workspace links.
8. Generated HTML permits only safe citation schemes and ships a restrictive content security policy where practical.
9. Installation instructions use immutable reviewed revisions and verified bytes.
10. A public skill entry works when installed by the command shown on its own skills.sh page.

## Teaching and release invariants

1. General teaching explains first. Practice-first is used only when the learner explicitly requests practice, a quiz, or an attempt before explanation.
2. Bundled reference skills cannot silently override the general teacher's style, privacy, or safety rules.
3. `teacher` is the canonical general implementation. `teach-pro-max` is a compatible public entry with a complete local fallback when `teacher` is absent.
4. Integrity manifests describe the shipped bytes and pass before publication.
5. Automated scores, human judgments, and unrun checks are reported separately.
6. Historical evidence stays immutable; corrections are additive errata.

## Acceptance tests

### Release and teaching

- Installing only `teach-pro-max` leaves no required relative reference missing.
- Installing `teacher --with-subskills` cannot expose a divergent `teach-pro-max` implementation.
- `verify_distribution.py` succeeds for every shipped teach-pro-max copy.
- Teacher and bundled reference text contain no unconditional practice-first rule for interview preparation, vocabulary, or resumed sessions.
- The teaching deliverable contains no Codex CLI configuration or rollback helper.

### Filesystem and upload

- traversal identifiers, absolute paths, symlinked inputs, and swapped links are rejected;
- an ordinary in-root regular video still publishes through the same API contract;
- course shared files, lesson files, and output identifiers are validated before any build side effect;
- journal init, resume, log, and forget work with mode `0700` for directories and `0600` for files while link attacks fail.

### Network and HTML

- domainless cookie maps are rejected;
- cookies never appear on a different host or redirect target;
- loopback, RFC1918, link-local, IPv6 local, and cloud metadata targets are rejected;
- oversized bodies and captures stop before exceeding configured limits;
- `javascript:` and active `data:` citations are omitted or rendered inert while `https:` citations remain usable.

### Execution and installers

- health actions are fixed identifiers mapped to fixed argument vectors; report strings never reach a shell parser;
- default lesson checks are structural and do not launch authored JS, Python, C, or C++;
- explicit code execution fails closed without the supported sandbox and succeeds inside it for a benign fixture;
- installer examples identify immutable revisions and a digest/signature verification step.

## Compatibility requirements

- Existing safe lesson/course manifests remain valid.
- Existing local-only lessons still build without network access.
- Public CLI flags keep their meaning unless the unsafe behavior cannot be preserved.
- Error messages identify the rejected field or resource without leaking credentials or unrelated paths.

## Evidence contract

Each fixed finding needs a failing pre-fix reproducer, a post-fix negative test, and a legitimate control through the same boundary. Existing evaluator results are not reused as proof of these repairs.
