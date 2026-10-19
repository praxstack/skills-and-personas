#!/usr/bin/env python3
"""Execute the whole lesson checker in a restricted disposable Docker container.

Requires a locally built, reviewed image ID (sha256:...), never pulls implicitly.
No source code is evaluated on the host. Missing prerequisites fail closed.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import selectors
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

COURSE = Path(__file__).resolve().parents[2] / "course" / "scripts"
sys.path.insert(0, str(COURSE))
from safe_course import read_bound_file


def execute(lesson: Path, includes: list[Path], image: str, *, context: str | None = None,
            timeout: float = 90, output_limit: int = 1024 * 1024) -> int:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("sandbox image must be an immutable local sha256 image ID")
    if not shutil.which("docker"):
        raise RuntimeError("Docker is unavailable; no authored code ran")
    docker = ["docker", *(["--context", context] if context else [])]
    inspected = subprocess.run([*docker, "image", "inspect", image], capture_output=True, timeout=15)
    if inspected.returncode:
        raise RuntimeError("sandbox runtime or reviewed image unavailable; no authored code ran")
    name = "teacher-check-" + uuid.uuid4().hex
    if os.getuid() == 0:
        raise RuntimeError("run the sandbox client as a non-root user")
    # Home is shared by macOS VM runtimes; private /var/folders temp is not.
    with tempfile.TemporaryDirectory(prefix=".teacher-check-", dir=Path.home()) as temp:
        root = Path(temp).resolve()
        root.chmod(0o700)
        for i, path in enumerate([lesson, *includes]):
            path = Path(os.path.abspath(path))
            content = read_bound_file(path.parent.resolve(strict=True), path.name, limit=8 * 1024 * 1024)
            (root / f"source-{i}.js").write_bytes(content)
        shutil.copyfile(Path(__file__).with_name("check_code.mjs"), root / "check_code.mjs")
        for path in root.iterdir():
            path.chmod(0o444)
        command = [*docker, "run", "--rm", "--pull=never", "--name", name,
                   "--network=none", "--read-only", f"--user={os.getuid()}:{os.getgid()}",
                   "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=32",
                   "--memory=512m", "--memory-swap=512m", "--cpus=1",
                   "--ulimit=nofile=64:64",
                   "--ulimit=fsize=16777216:16777216", "--ulimit=core=0:0",
                   "--tmpfs=/tmp:rw,nosuid,nodev,size=128m,mode=1777,exec",
                   "--mount", f"type=bind,src={root},dst=/input,readonly",
                   "--workdir=/tmp", "--env=HOME=/tmp", "--env=TMPDIR=/tmp",
                   "--entrypoint=node", image,
                   "/input/check_code.mjs", "/input/source-0.js", "--trust-authored-code"]
        for i in range(len(includes)):
            command += ["--include", f"/input/source-{i+1}.js"]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        selector = selectors.DefaultSelector()
        selector.register(proc.stdout, selectors.EVENT_READ)
        start, total = time.monotonic(), 0
        try:
            while selector.get_map():
                if time.monotonic() - start > timeout:
                    raise TimeoutError("sandbox wall-clock budget exhausted")
                for key, _ in selector.select(timeout=0.1):
                    data = os.read(key.fileobj.fileno(), 65536)
                    if not data:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(data)
                    if total > output_limit:
                        raise RuntimeError("sandbox output budget exhausted")
                    sys.stdout.buffer.write(data)
                    sys.stdout.buffer.flush()
            return proc.wait(timeout=5)
        finally:
            selector.close()
            # Kill the container, not only its docker client, on every exit path.
            try:
                removed = subprocess.run([*docker, "rm", "-f", name], stdout=subprocess.DEVNULL,
                                         stderr=subprocess.DEVNULL, timeout=15)
                if removed.returncode:
                    remaining = subprocess.run([*docker, "ps", "-a", "--filter", f"name=^/{name}$", "--format", "{{.ID}}"],
                                               capture_output=True, timeout=15)
                    if remaining.returncode or remaining.stdout.strip():
                        raise RuntimeError("could not verify sandbox container removal")
            finally:
                if proc.poll() is None:
                    proc.kill()
                proc.wait(timeout=5)
                proc.stdout.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("lesson", type=Path)
    parser.add_argument("--include", type=Path, action="append", default=[])
    parser.add_argument("--image", required=True)
    parser.add_argument("--docker-context")
    parser.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args()
    if not 0 < args.timeout <= 300:
        parser.error("timeout must be between 0 and 300 seconds")
    try:
        return execute(args.lesson, args.include, args.image, context=args.docker_context, timeout=args.timeout)
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError) as exc:
        print(f"sandbox failed closed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
