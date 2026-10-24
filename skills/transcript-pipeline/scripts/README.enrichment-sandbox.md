# Explicit single-session resource sandbox

`sandbox_resource_enrichment.py` isolates one enrichment job's processes and resource consumption. The direct `resource_enrichment.py` CLI and imports remain **unsandboxed**. This runner never silently falls back to them on the host.

## Run

Supply a reviewed, already-local immutable image ID. An ID identifies bytes; it does not itself establish review. Docker must be available before the job starts. No runtime image pulls, dependency downloads, account discovery or browser login occurs.

```sh
python3 skills/transcript-pipeline/scripts/sandbox_resource_enrichment.py \
  --session-dir /absolute/session \
  --out /absolute/session/.resources \
  --image sha256:6bae2ca9852061ba0abebef8b07f9f3ea96a799c9f7ef4d31f0a6f135ae5ea6c \
  --docker-context colima-teach-security --timeout 120
```

The output must not exist and its parent must exist without symlink components. Alternate `--out` paths retain a separate result; the report's `output_files` remain relative to the logical `session` (for example `.resources/example.html`), not the alternate output directory. Existing output is never replaced. HTML artifacts are untrusted: the runner does not open them.

Only `.pipeline/resource_manifest.json` enters the input mount: at most 1 MiB and 100 entries. No transcript, media, existing `.resources`, home tree, repository tree, browser profile or Docker socket is mounted. Optional credentials are explicit files, never token command-line arguments or ambient environment variables:

- `--cookies-json FILE`: a list of `{ "name": "...", "value": "...", "domain": "exact.example", "path": "/" }` objects. Broad/leading-dot domains are rejected. The existing transport restricts these sessions to that exact HTTPS origin on port 443.
- `--notion-credentials FILE`: exactly `{ "token_v2": "...", "active_user": "..." }`. The existing Notion API transport targets `www.notion.so` only.
- `--canva-storage-state FILE`: Playwright state with `cookies` and `origins`. Cookies require exact lowercase Canva domains without a leading dot and `secure: true`, plus the standard path/expires/httpOnly/sameSite fields; origins require exact `https://HOST` or `https://HOST:443`, no path/query/credentials, and Canva hostnames. Cookie and origin recipients form an explicit allowlist. The runner passes it to the browser transport, which strips Cookie/Authorization outside those HTTPS443 origins, including other Canva subdomains. Redirect requests are rechecked individually. Legacy direct calls preserve their existing provider-wide policy.

Cookie/Canva files are capped at 1 MiB, Notion JSON at 64 KiB, all inputs at 4 MiB. Broader browser exports fail before container creation; they are not silently narrowed. Restricted state may not support every Canva login. Provider JavaScript can read its state and send data in request bodies; exact header restrictions do not guarantee secret non-exfiltration. Supplied cookies, `authenticated: true`, HTTP200 and a successful browser launch do **not** prove provider authentication. No personal authentication has been tested.

Snapshots and outputs use private directories (0700), files (0600), read-only container mounts and descriptor-bound no-follow reads. Worker diagnostics are discarded and bounded, not echoed. Reports contain credential-presence booleans and generic error/notes in place of raw exceptions. Fetched documents can themselves contain private content.

## Limits and lifecycle

Fixed ceilings: 1 CPU, 1 GiB memory/no additional swap, 128 PIDs/threads, 256 file descriptors, 64 MiB per file, zero core dumps, 512 MiB `/tmp`, 64 MiB `/dev/shm`, 256 MiB aggregate output, 1,024 archive entries, 1 MiB diagnostic log, archive at most output plus 2 MiB, wall time at most 600 seconds. Existing JobBudget ceilings remain 100 resources, 1,000 requests and 256 MiB transfer/output. CLI timeout can only lower the wall ceiling. Browser profiles, artifacts and tmpfs compete for memory. Missing Python dependencies or Chromium fail the mandatory preflight; even HTTP-only manifests preflight the browser.

The container uses a non-root UID, read-only root, no capabilities, no-new-privileges, default Docker seccomp and a normal isolated bridge. Hardened Python transport validates public addresses and supplies browser HTTP responses; dead-proxy/DNS/WebSocket/service-worker restrictions remain. **The outbound bridge is not kernel-enforced public-only egress against native compromise.** A compromised process could bypass application checks. General egress isolation is outside this runner's scope.

An external deadline starts before image inspection/create; the trusted PID1 has its own alarm, so worker and descendant execution stops after host-client loss. SIGTERM/SIGHUP/SIGINT trigger owned-container removal; repeated signals cannot interrupt cleanup. PID1 kills/reaps namespace descendants, including detached sessions, before archiving. Internal log overflow also stops execution without a host reader. Failed/nonzero/OOM jobs publish nothing; clean jobs can still contain per-resource failure reports. Archive validation rejects extension records, traversal, duplicate names, prefix collisions, links, special files and excessive bytes/counts before exclusive local publication.

After SIGKILL or host failure, the stopped container and private host snapshots may remain because no host cleanup process survives. The internal deadline limits execution, not automatic garbage collection. Remove only the specific owned `resource-enrichment-*` container and matching `.enrichment-*` snapshot after checking its mounts. Normal/catchable cancellation verifies removal. Cleanup verification failure is reported explicitly. Publication I/O failure can leave a new partial private output directory; the runner does not recursively delete a path another local process may have substituted.

## Explicit image setup (tested Linux ARM64 only)

The standalone-built local base is `sha256:cd98c1146024024c8588e3064ef8297d2838b921223daf755afbe56b18afaf57`, containing Debian12 Python3.11.2 and Chromium/headless-shell revision1208. Build it explicitly from the included `Dockerfile.enrichment-base` when absent (commands below). This is an ARM64 setup. On another architecture, select/review an equivalent immutable base and platform wheel hashes and rerun the controls; do not bypass the existing hashes. No runtime cross-skill imports are used.

The included base recipe starts with a registry-pinned Debian12 Node image, installs the pinned browser-library versions listed below, and downloads Chromium1208 through Playwright1.58.0. If those exact Debian package versions become unavailable, setup fails; updating pins is a new image review, not runtime fallback. The immutable resulting image also fixes the installed OS transitive dependencies. The base build was executed successfully on this ARM64 Docker context.

```sh
mkdir -p /tmp/enrichment-base-setup
docker --context colima-teach-security build --pull=false \
  -f skills/transcript-pipeline/scripts/Dockerfile.enrichment-base \
  -t teach-enrichment-base:task7 /tmp/enrichment-base-setup
docker --context colima-teach-security image inspect teach-enrichment-base:task7 --format '{{.Id}}'
```

A first setup may fetch the registry-pinned base and named browser artifacts. Record/review the returned base ID and use it as `--build-arg BASE_IMAGE=sha256:...` in the next build. The default base ID in the final Dockerfile is this run's exact local result; rebuilt layer timestamps can produce a different ID.

A clean checkout with that reviewed base can reproduce the wheel preparation below using any host pip with cross-platform download support. No unpublished wheel path is needed. Use a fresh directory containing only `wheels/` as the build context. Dockerfile pins each wheel SHA256 and rejects additions/missing files before extracting them. All dependencies, including transitive ones, are pinned:

```sh
mkdir -p /tmp/enrichment-image-setup/wheels
python3 -m pip download --only-binary=:all: \
  --platform manylinux2014_aarch64 --platform manylinux_2_24_aarch64 \
  --platform manylinux_2_28_aarch64 --python-version 3.11 --implementation cp --abi cp311 \
  --dest /tmp/enrichment-image-setup/wheels \
  requests==2.34.2 urllib3==2.6.3 certifi==2026.2.25 charset-normalizer==3.4.4 \
  idna==3.11 playwright==1.58.0 pyee==13.0.1 greenlet==3.3.2 typing-extensions==4.15.0

cp skills/transcript-pipeline/scripts/enrichment-wheels-arm64.json /tmp/enrichment-image-setup/

docker --context colima-teach-security build --pull=false --network=none \
  -f skills/transcript-pipeline/scripts/Dockerfile.enrichment \
  -t teach-enrichment-reviewed:task7 /tmp/enrichment-image-setup

docker --context colima-teach-security image inspect teach-enrichment-reviewed:task7 --format '{{.Id}}'
```

Use the returned full ID after review. The observed build ID was `sha256:6bae2ca9852061ba0abebef8b07f9f3ea96a799c9f7ef4d31f0a6f135ae5ea6c`; rebuilding can change the ID through image-layer timestamps. BuildKit is not required. Python Playwright includes its own Node driver, whose executable permission is restored during assembly. No Python package installation occurs during a job.

Browser library inventory, immutable in the reviewed base: `libasound2 1.2.8-1+b1`, `libatk-bridge2.0-0/libatk1.0-0 2.46.0-5`, `libcairo2 1.16.0-7`, `libcups2 2.4.2-3+deb12u9`, `libdbus-1-3 1.14.10-1~deb12u1`, `libdrm2 2.4.114-1+b1`, `libgbm1 22.3.6-1+deb12u2`, `libnspr4 2:4.35-1`, `libnss3 2:3.87.1-1+deb12u4`, `libpango-1.0-0 1.50.12+ds-1`, `libx11-6 2:1.8.4-2+deb12u2`, `libxcb1 1.15-1`, `libxcomposite1 1:0.4.5-1`, `libxdamage1 1:1.1.6-1`, `libxext6 2:1.3.4-1+b1`, `libxfixes3 1:6.0.0-2`, `libxkbcommon0 1.5.0-1`, `libxrandr2 2:1.5.2-2+b1`.

## Verification

```sh
python3 -m unittest discover -s skills/transcript-pipeline/scripts -p test_sandbox_resource_enrichment.py -v
# Existing transport/budget tests also require requests in the test Python environment.
python3 -m unittest discover -s skills/transcript-pipeline/scripts -p 'test_resource*.py' -v

# Explicit opt-in: creates bounded synthetic containers and fetches example.com publicly.
ENRICHMENT_TEST_IMAGE=sha256:6bae2ca9852061ba0abebef8b07f9f3ea96a799c9f7ef4d31f0a6f135ae5ea6c \
ENRICHMENT_TEST_CONTEXT=colima-teach-security \
python3 -m unittest discover -s skills/transcript-pipeline/scripts -p test_sandbox_resource_enrichment.py -v
```

Tests cover real Chromium/public subresources/private-URL refusal, real callback transfer-budget exhaustion, CPU/memory/PID/tmpfs/log/artifact exhaustion, detached descendant termination, SIGTERM, host SIGKILL/internal deadline, private snapshots, archive guards and cleanup failures. All inputs are synthetic. No account login or provider-authentication claim follows from these tests.
