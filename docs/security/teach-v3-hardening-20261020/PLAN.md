# Teach v3 security and release hardening plan

Date: 2026-10-20
Status: completed and published as v3.0.1
Owner: Codex
Branch: `fix/teach-v3-security-hardening-20261020`

## Frozen baseline

- Published repository baseline: `dc6a49857d07643e3bcf6bfece9272f6f28f1bb7`.
- Published release tag: `prax-teach-v3.0.0` at `d2becc0`.
- Accepted product source recorded by the release: `0d20ff7722910d12256240af0897070255cfc4f3`.
- Rollback pointer for source review: Git commit `dc6a49857d07643e3bcf6bfece9272f6f28f1bb7`.
- The private evaluation bank, frozen runner, acceptance thresholds, and historical evidence are protected. This run does not edit them.

## Objective

Make the published general teaching skill safe to install and operate while preserving its original goal: teach any subject with explanation-first, mechanism-led visuals and first-class stills, explorers, cards, narrated video, and interactive video.

## Scope

This run changes product code, product documentation, packaging, and ordinary regression tests. It does not change the governing evaluator or use new acceptance rules to certify its own patch.

### Protected paths

- `deliverables/teach-pro-max/codex/governance/`
- private evaluation inputs and runner outside this repository
- previously published raw evidence and historical archives, except for clearly labelled errata
- release tag `prax-teach-v3.0.0`

### Mutable paths

- `skills/teacher/`
- `skills/teach-pro-max/`
- `skills/transcript-pipeline/`
- `skills/skillpack-check/`
- installation and release documentation
- new focused security regression tests and this hardening dossier

## Work sequence

1. **Release integrity and teaching precedence**
   - make `teach-pro-max` useful when installed alone;
   - remove the divergent nested copy;
   - restore a passing embedded-engine integrity check;
   - make explanation-first override conflicting bundled references unless the learner explicitly requests practice;
   - remove unrelated Codex CLI configuration material from teaching deliverables;
   - correct release claims without rewriting historical evidence.
2. **Filesystem and publication boundaries**
   - confine course paths and public uploads to validated regular files beneath their roots;
   - harden journal creation, reads, writes, and deletion against links and permissive modes;
   - allow only safe citation URL schemes.
3. **Network and credential boundaries**
   - separate authenticated exact-host sessions from generic resource fetching;
   - block local, private, loopback, link-local, and metadata targets before and after redirects;
   - stream remote resources through explicit byte, page, and disk budgets;
   - pin mutable installation examples.
4. **Untrusted execution boundary**
   - remove shell `eval` from skillpack health actions;
   - stop routine lesson validation from executing authored code on the host;
   - require an explicit sandboxed execution mode for Python, JavaScript, and C/C++ examples.
5. **Verification and release readiness**
   - run focused exploit reproductions and legitimate controls;
   - run the existing teacher, browser, packaging, and repository checks without changing their rules;
   - independently inspect the final diff for bypasses and regressions;
   - publish only after a separate release decision.

## Budget and stop rule

- Four implementation waves plus one read-only verification wave.
- Stop after two consecutive implementation waves produce no verified security or product gain.
- Do not weaken a check, alter the frozen evaluator, or expand the objective to obtain a pass.

## External operations kept separate

Deleting public branches or rewriting public history is destructive and is not part of the source patch. The branch/privacy inventory will be prepared, but execution requires a separately reviewed deletion plan. Repairing the local rollback snapshot is also an operational change and will be verified separately from repository changes.
