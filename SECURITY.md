# Security Policy

## Reporting a vulnerability

Do not put vulnerability details, credentials, learner data, or exploit artifacts
in a public issue or pull request. The GitHub private vulnerability reporting
entry point for this repository is:

https://github.com/praxstack/skills-and-personas/security/advisories/new

Availability depends on the repository's private reporting settings; this policy
does not establish that reporting is enabled. If that page does not offer a
private report, contact the maintainer through an existing private channel, or
open a public issue containing only a request to enable private reporting. Wait
for a confirmed private channel before sharing sensitive details. GitHub does
not provide a general direct-message fallback.

Include the affected revision or release, component, prerequisites, reproduction
steps, expected and observed behavior, and potential impact. Use synthetic data
and redact tokens and personal information.

## Scope

Reports may concern skill instructions and persona documents; executable Python,
JavaScript, shell and container tooling; installers and bootstrap commands;
packaged `.skill` archives, release ZIPs and embedded runtimes; generated HTML,
media and other artifacts; dependency loading and network access; authentication,
uploads, filesystem handling, and learner journals or other private state.
Integration vulnerabilities in third-party services should also be reported to
that service through its own security channel.

Instructions and `allowed-tools` declarations are not runtime sandboxes.
Executable content, remote resources and generated artifacts have distinct trust
boundaries. Focused regression tests do not certify every engine, installation
path, artifact or historical release. See
[the coverage matrix](docs/security/teach-v3-hardening-20261020/COVERAGE-MATRIX.md)
for the recorded scope and unresolved findings.

## Response and supported versions

There is no published response-time guarantee or supported-version matrix.
Reports should identify the exact affected revision. Fixes and coordinated
public disclosure can be discussed through the confirmed private reporting
channel. Do not assume an old archive receives a fix merely because the current
source tree changed.
