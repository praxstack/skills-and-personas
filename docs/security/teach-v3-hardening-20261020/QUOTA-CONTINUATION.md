# Aggregate resource quotas

Candidate changes after v3.0.1; not yet installed or published.

The enrichment CLI shares one budget across sessions and provider fallbacks:
100 resources, 1,000 HTTP requests, 256 MiB decoded response bytes, 256 MiB
cumulative artifact writes and a 600-second deadline. Manifests are limited to
1 MiB and 100 entries each. Existing per-response limits still apply.

Consumed bytes count even when a request fails. Output counts encoded bytes,
including replacements, screenshots, PDFs and reports. Once exhausted, the job
stops instead of resetting its allowance for the next resource or converting
the error into a successful fallback.

The POSIX CLI uses an alarm to interrupt blocking operations. Direct Python
library callers receive cooperative deadline checks; they need an outer
supervisor for blocking calls. These controls do **not** establish browser
process memory/CPU limits or constrain browser temporary disk. SEC-009 remains
partial until those boundaries are independently verified.

## Verification

- Existing HTTP security tests: 11 passed.
- New aggregate-budget tests: 9 passed. Covers failed streams, cumulative
  sessions, output overwrite accounting, reports, valid controls, fallback
  propagation, manifest size/count, real blocking-call interruption and nested
  scopes that cannot reset the job.
- Real Chrome tests: 2 passed, including tiny quota rejection and normal
  navigation, private HTTP rejection and upstream WebSocket isolation.
- Independent candidate reviewer reproduced a real bypass: Playwright route
  callbacks execute in a new greenlet and lost the ContextVar. The correction
  captures the original budget at callback registration and explicitly binds
  it during every callback. The real browser regression exercises that boundary.

Commands from repository root:

```sh
uv run --with requests==2.34.2 python -m unittest discover \
  -s skills/transcript-pipeline/scripts -p 'test_resource*.py' -v
TEACHER_BROWSER_TESTS=1 \
CHROMIUM_PATH='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome' \
uv run --with requests==2.34.2 --with playwright==1.58.0 python \
  -m unittest discover -s skills/transcript-pipeline/scripts \
  -p test_browser_transport.py -v
```

The browser tests use an actual browser with controlled broker responses.
They verify callback dispatch and browser behavior, not live authenticated Canva.
