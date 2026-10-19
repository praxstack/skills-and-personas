# Checking untrusted lesson code

The default checker is structural: it does not run authored code. To compare
shown Python/C++ against a lesson's model without giving it host access, use
`--sandbox`. This runs the whole JavaScript loader, compiler and programs inside
a disposable Docker container. Node's VM context alone is not a sandbox.

## Explicit setup

A working Docker daemon is required. Build the bundled image after reviewing its
Dockerfile. Building downloads the pinned Node image and Debian compiler/Python
packages; it is a setup operation with network access, not an offline teaching
step. Compiler packages can receive security updates, so record the final local
image ID. Runtime invocation accepts only that immutable ID and never pulls.

```bash
docker build -t teacher-code-sandbox:local assets/sandbox
docker image inspect teacher-code-sandbox:local --format '{{.Id}}'
```

Pass the returned `sha256:...` ID explicitly:

```bash
node scripts/check_code.mjs lesson.js --sandbox --sandbox-image sha256:REPLACE_WITH_FULL_IMAGE_ID
```

Add `--include shared.js` for shared models. `--docker-context NAME` selects an
existing runtime without changing the machine's default. If Docker or the image
is unavailable, execution fails closed. It never falls back to the host.

## Boundary and limits

Only private snapshots of the lesson/includes and the checker are mounted,
read-only. Host home, credentials and Docker sockets are not mounted. The
container runs as the invoking non-root UID, with no network, a read-only root,
no capabilities, no privilege escalation, one CPU, 512 MiB memory, 32 processes,
64 descriptors and 128 MiB writable scratch. C++ binaries execute only there.
Output is limited to 1 MiB and the outer deadline is 90 seconds. Cleanup removes
the container after success, error, timeout or excessive output.

Run the client as a non-root user. The host Docker daemon is trusted; an operator
must review the sandbox image. Containers share the runtime's kernel and do not
promise protection against an unknown kernel or container-runtime exploit.
On macOS the container runs inside the configured Linux VM.

This adapter checks executable examples. Rendering or extracting an entire
third-party course is a separate operation: do not bypass its review gate with
`--trust-authored-code`. Use a separately restricted environment for that work.
The trust flag remains for reviewed first-party content and grants host access.
