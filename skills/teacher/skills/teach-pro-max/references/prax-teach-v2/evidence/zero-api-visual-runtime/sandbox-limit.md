# Verification environment limitation

The host exposes `/usr/bin/sandbox-exec`, but nested sandbox execution is denied by the surrounding Codex desktop sandbox (`sandbox_apply: Operation not permitted`). An in-sandbox run is therefore environment-limited. The final full verifier was rerun outside that nested boundary with escalation; the trusted macOS sandbox E2E passed and is recorded in `evidence/verification/full.json`. `PRAX_DISABLE_MACOS_SANDBOX_TESTS=1` remains available for diagnostics only and is never treated as evidence that the trusted sandbox boundary passed.
