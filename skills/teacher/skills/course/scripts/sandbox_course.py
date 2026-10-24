#!/usr/bin/env python3
"""Run course extraction, build or browser validation in an explicit Docker sandbox.

Only immutable locally present images are accepted. Authored code and all child
processes run inside the container; output is published only after it exits.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path, PurePosixPath
import re
import selectors
import signal
import stat
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import uuid

from safe_course import open_directory, read_bound_file, snapshot_course, validate_course_manifest

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
INPUT_LIMIT = 64 * 1024 * 1024
OUTPUT_LIMIT = 64 * 1024 * 1024
ARCHIVE_LIMIT = OUTPUT_LIMIT + 2 * 1024 * 1024
LOG_LIMIT = 1024 * 1024
FILE_LIMIT = 1024

# PID 1 is trusted, uses no authored imports, and does not forward its stdout to
# children. kill(-1) includes processes that escaped the child's session via
# setsid; Linux excludes PID 1 and the caller. No descendants survive packaging.
SUPERVISOR = r'''
import json, os, pathlib, signal, stat, subprocess, sys, tarfile
mode = sys.argv[1]
# PID 1 owns an independent deadline. Exiting the namespace init also causes
# Linux to kill namespace descendants, even if the host client disappeared.
def deadline(signum, frame):
    try:
        os.kill(-1, signal.SIGKILL)
    except ProcessLookupError:
        pass
    finally:
        os._exit(124)
signal.signal(signal.SIGALRM, deadline)
signal.setitimer(signal.ITIMER_REAL, float(sys.argv[2]))
base = '/tools/course/scripts/'
sys.path.insert(0, base)
from supervisor_reaping import wait_reaping
env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp',
       'PYTHONDONTWRITEBYTECODE': '1', 'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright',
       'CHROMIUM_PATH': '/tools/chromium', 'UV_THREADPOOL_SIZE': '1', 'NODE_OPTIONS': '--v8-pool-size=1'}
os.makedirs('/tmp/output', exist_ok=False)
if mode == 'extract':
    command = ['node', base+'extract.mjs', '/input/course', '--trust-authored-code']
    output = open('/tmp/output/course.json', 'wb')
else:
    command = ['python3', base+('test_course.py' if mode == 'validate' else 'render_course.py' if mode == 'render' else 'build_course.py'),
               '/input/course', '--out', '/tmp/output', '--trust-authored-code']
    output = sys.stderr
if mode in {'validate', 'render'}:
    probe = subprocess.Popen(['node', '--input-type=module', '-e',
        "import {loadPlaywright,launch} from '/tools/visual-qa/scripts/pw.mjs'; "
        "const {chromium}=await loadPlaywright();const b=await launch(chromium);await b.newPage();await b.close();"],
        env=env, stdout=sys.stderr, stderr=sys.stderr)
    if wait_reaping(probe):
        sys.exit('reviewed Playwright/Chromium dependencies unavailable; no authored code ran')
child = subprocess.Popen(command, stdout=output, stderr=sys.stderr, env=env, start_new_session=True)
try:
    code = wait_reaping(child)
finally:
    try:
        os.kill(-1, signal.SIGKILL)
    except ProcessLookupError:
        pass
    while True:
        try:
            os.waitpid(-1, 0)
        except ChildProcessError:
            break
if mode == 'extract':
    output.close()
if code:
    sys.exit(code if code > 0 else 1)
root = pathlib.Path('/tmp/output')
files = sorted(root.rglob('*'))
if len(files) > 1024:
    sys.exit('sandbox artifact count budget exhausted')
total = 0
for path in files:
    info = path.lstat()
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)) or info.st_nlink != (2 if stat.S_ISDIR(info.st_mode) else 1):
        # Directory link counts vary with subdirectories; only regular hardlinks matter.
        if not stat.S_ISDIR(info.st_mode):
            sys.exit('sandbox output contains a link or special file')
    if stat.S_ISREG(info.st_mode):
        total += info.st_size
    if total > 67108864:
        sys.exit('sandbox artifact byte budget exhausted')
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
    for path in files:
        archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
'''


@contextmanager
def bounded_inputs(course: Path):
    """Capture descriptor-bound bytes with aggregate limits before snapshot_course."""
    base = Path.cwd()
    pwd = os.environ.get('PWD', '')
    if pwd and os.path.isabs(pwd):
        try:
            if os.path.samefile(pwd, base):
                base = Path(pwd)
        except OSError:
            pass
    logical = Path(os.path.abspath(base / course))
    original = course.resolve(strict=True)
    manifest = read_bound_file(original, 'course.json', limit=1024 * 1024)
    data = json.loads(manifest)
    if not isinstance(data, dict) or not isinstance(data.get('lessons'), list) or not 1 <= len(data['lessons']) <= 128:
        raise ValueError('course must have between 1 and 128 lessons')
    shared = data.get('shared', [])
    if not isinstance(shared, list) or len(shared) > 128:
        raise ValueError('course shared must be a bounded array')
    with tempfile.TemporaryDirectory(prefix='teacher-bounded-') as temp:
        root = Path(temp) / 'course'
        root.mkdir(mode=0o700)
        (root / 'course.json').write_bytes(manifest)
        total = len(manifest)
        inputs = [*shared]
        for lesson in data['lessons']:
            if not isinstance(lesson, dict):
                raise ValueError('course lesson must be an object')
            from safe_course import safe_id
            ident = safe_id(lesson.get('id'), 'lesson id')
            inputs.append(lesson.get('file'))
            inputs += [f'videos/{ident}.mp4', f'videos/{ident}.vtt']
        if not all(isinstance(relative, str) for relative in inputs):
            raise ValueError('course input path must be a string')
        for relative in dict.fromkeys(inputs):
            try:
                contents = read_bound_file(original, relative, limit=INPUT_LIMIT - total)
            except FileNotFoundError:
                if relative.startswith('videos/'):
                    continue
                raise
            total += len(contents)
            target = root / relative
            target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            target.write_bytes(contents)
        try:
            contents = read_bound_file(logical.parent.resolve(strict=True), 'videos.json', limit=INPUT_LIMIT - total)
        except FileNotFoundError:
            pass
        else:
            (root.parent / 'videos.json').write_bytes(contents)
        validate_course_manifest(root)
        with snapshot_course(root) as captured:
            yield captured


def unpack_archive(archive: Path, destination: Path) -> None:
    """Validate every member before writing; never call tarfile.extract()."""
    if archive.stat().st_size > ARCHIVE_LIMIT:
        raise ValueError('sandbox archive exceeds byte budget')
    with tarfile.open(archive, mode='r:') as source:
        members, seen, total = [], set(), 0
        for member in source:
            name = member.name
            parts = PurePosixPath(name).parts
            if (not parts or len(parts) > 16 or len(name.encode('utf-8')) > 240 or name.startswith('/') or '\\' in name or
                    any(p in {'', '.', '..'} for p in name.split('/')) or
                    any(ord(c) < 32 or ord(c) == 127 for c in name) or
                    name in seen or member.type not in {tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE} or
                    member.pax_headers or member.sparse):
                raise ValueError('sandbox archive contains an unsafe or duplicate member')
            seen.add(name)
            total += member.size
            members.append(member)
            if len(members) > FILE_LIMIT or total > OUTPUT_LIMIT or member.size < 0:
                raise ValueError('sandbox archive exceeds artifact budget')
        if not members:
            raise ValueError('sandbox produced no artifacts')
        for member in members:
            path = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                path.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with source.extractfile(member) as incoming, path.open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)


def publish_archive(archive: Path, output: Path) -> None:
    """Exclusive descriptor-anchored destination; existing files never overwritten."""
    output = Path(os.path.abspath(output))
    parent = open_directory(output.parent)
    created = False
    try:
        # Validate in a private directory before making the public destination.
        with tempfile.TemporaryDirectory(prefix='teacher-unpack-') as temp:
            staged = Path(temp)
            unpack_archive(archive, staged)
            os.mkdir(output.name, mode=0o700, dir_fd=parent)
            created = True
            fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                def copy_tree(src: Path, target_fd: int):
                    for child in src.iterdir():
                        if child.is_dir():
                            os.mkdir(child.name, mode=0o700, dir_fd=target_fd)
                            nested = os.open(child.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=target_fd)
                            try:
                                copy_tree(child, nested)
                            finally:
                                os.close(nested)
                        else:
                            dest = os.open(child.name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=target_fd)
                            with os.fdopen(dest, 'wb') as sink, child.open('rb') as source:
                                shutil.copyfileobj(source, sink)
                copy_tree(staged, fd)
            finally:
                os.close(fd)
    except BaseException:
        # A failed publish may leave a partial new private directory; never
        # recursively remove a path that another host process could have swapped.
        if created:
            print('sandbox publication failed; partial new output may remain', file=sys.stderr)
        raise
    finally:
        os.close(parent)


def copy_tools(destination: Path) -> None:
    for skill in ('course', 'explorable', 'concept-animation', 'lesson-notebook', 'visual-qa'):
        for directory in ('scripts', 'assets'):
            source = SKILLS / skill / directory
            if not source.is_dir():
                continue
            for path in source.rglob('*'):
                if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts and path.suffix != '.pyc':
                    target = destination / skill / directory / path.relative_to(source)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    # Trusted installation files may have canonical hardlink mirrors.
                    # Inputs still require one link; tools are captured through a
                    # no-follow descriptor and never mounted from their live tree.
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
                    with os.fdopen(fd, 'rb') as incoming:
                        info = os.fstat(incoming.fileno())
                        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                            raise ValueError('sandbox tool must be an owned regular file')
                        contents = incoming.read(8 * 1024 * 1024 + 1)
                        if len(contents) > 8 * 1024 * 1024:
                            raise ValueError('sandbox tool exceeds byte budget')
                        target.write_bytes(contents)


def capture(command: list[str], archive: Path, timeout: float) -> int:
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ, 'archive')
    selector.register(proc.stderr, selectors.EVENT_READ, 'log')
    started = time.monotonic()
    totals = {'archive': 0, 'log': 0}
    try:
        with archive.open('xb') as sink:
            while selector.get_map():
                if time.monotonic() - started > timeout:
                    raise TimeoutError('sandbox wall-clock budget exhausted')
                for key, _ in selector.select(timeout=0.1):
                    chunk = os.read(key.fileobj.fileno(), 65536)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    kind = key.data
                    totals[kind] += len(chunk)
                    if totals[kind] > (ARCHIVE_LIMIT if kind == 'archive' else LOG_LIMIT):
                        raise RuntimeError(f'sandbox {kind} byte budget exhausted')
                    if kind == 'archive':
                        sink.write(chunk)
                    else:
                        sys.stderr.buffer.write(chunk)
                        sys.stderr.buffer.flush()
            return proc.wait(timeout=5)
    finally:
        selector.close()
        if proc.poll() is None:
            proc.kill()
        proc.wait(timeout=5)
        proc.stdout.close()
        proc.stderr.close()


class SandboxCancelled(RuntimeError):
    def __init__(self, signum: int):
        self.signum = signum
        super().__init__(f'cancelled by {signal.Signals(signum).name}; sandbox cleanup attempted')


@contextmanager
def cancellation_handlers():
    if threading.current_thread() is not threading.main_thread():
        raise RuntimeError('sandbox execution requires the main Python thread for cancellation handling; no authored code ran')
    state = {'cleaning': False, 'signal': None}
    previous = {}

    def cancelled(signum, frame):
        state['signal'] = signum
        if not state['cleaning']:
            state['cleaning'] = True
            raise SandboxCancelled(signum)

    try:
        for signum in (signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
            previous[signum] = signal.signal(signum, cancelled)
        yield state
        if state['signal'] is not None:
            raise SandboxCancelled(state['signal'])
    finally:
        for signum, handler in previous.items():
            signal.signal(signum, handler)


def execute(course: Path, output: Path, image: str, *, mode: str = 'build',
            context: str | None = None, timeout: float = 90) -> None:
    with cancellation_handlers() as cancellation:
        _execute(course, output, image, mode=mode, context=context, timeout=timeout,
                 cancellation=cancellation)


def _execute(course: Path, output: Path, image: str, *, mode: str,
             context: str | None, timeout: float, cancellation: dict) -> None:
    if mode not in {'extract', 'build', 'validate', 'render'}:
        raise ValueError('supported modes: extract, build, validate, render; narration is unsupported')
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('sandbox image must be an immutable local sha256 image ID')
    if not 0 < timeout <= 300:
        raise ValueError('timeout must be between 0 and 300 seconds')
    if not shutil.which('docker'):
        raise RuntimeError('Docker unavailable; no authored code ran')
    if os.getuid() == 0:
        raise RuntimeError('run the sandbox client as a non-root user')
    docker = ['docker', *(['--context', context] if context else [])]
    inspected = subprocess.run([*docker, 'image', 'inspect', image], capture_output=True, timeout=15)
    if inspected.returncode:
        raise RuntimeError('sandbox runtime or reviewed local image unavailable; no authored code ran')
    # Fail before execution if the destination already exists or its parent links.
    parent = open_directory(Path(os.path.abspath(output)).parent)
    try:
        try:
            os.stat(output.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('sandbox output must be a new destination')
    finally:
        os.close(parent)
    name = 'teacher-course-' + uuid.uuid4().hex
    with bounded_inputs(course) as captured, tempfile.TemporaryDirectory(prefix='.teacher-course-', dir=Path.home()) as temp:
        staging = Path(temp).resolve()
        inputs = staging / 'input'
        tools = staging / 'tools'
        shutil.copytree(captured.parent, inputs)
        tools.mkdir()
        copy_tools(tools)
        (tools / 'supervisor.py').write_text(SUPERVISOR)
        (tools / 'chromium').write_text('#!/bin/sh\nexec python3 /tools/course/scripts/chromium_wrapper.py "$@"\n')
        for path in staging.rglob('*'):
            path.chmod(0o500 if path.is_dir() else 0o400)
        (tools / 'chromium').chmod(0o500)
        staging.chmod(0o700)
        command = [*docker, 'create', '--pull=never', '--init=false', '--name', name,
                   '--network=none', '--log-driver=none', '--read-only', f'--user={os.getuid()}:{os.getgid()}',
                   '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=64',
                   '--memory=512m', '--memory-swap=512m', '--cpus=1',
                   '--ulimit=nofile=128:128', '--ulimit=fsize=67108864:67108864', '--ulimit=core=0:0',
                   '--tmpfs=/tmp:rw,nosuid,nodev,size=256m,mode=1777,exec',
                   '--tmpfs=/dev/shm:rw,nosuid,nodev,noexec,size=64m',
                   '--mount', f'type=bind,src={inputs},dst=/input,readonly',
                   '--mount', f'type=bind,src={tools},dst=/tools,readonly',
                   '--workdir=/tmp', '--env=HOME=/tmp', '--env=TMPDIR=/tmp',
                   '--env=PYTHONDONTWRITEBYTECODE=1', '--entrypoint=python3', image,
                   '/tools/supervisor.py', mode, str(timeout)]
        try:
            created = subprocess.run(command, capture_output=True, timeout=20)
            if created.returncode:
                raise RuntimeError('sandbox container creation failed; no authored code ran')
            # Archive is not bind-mounted and is never writable by authored code.
            archive = staging / 'output.tar'
            exit_code = capture([*docker, 'start', '--attach', name], archive, timeout)
            if exit_code == 124:
                raise TimeoutError('sandbox container wall-clock budget exhausted')
            if exit_code:
                raise RuntimeError('sandbox course process failed; no output published')
            state = subprocess.run([*docker, 'inspect', '--format', '{{json .State}}', name], capture_output=True, timeout=15)
            if state.returncode:
                raise RuntimeError('cannot verify sandbox process exit; no output published')
            status = json.loads(state.stdout)
            if status.get('Running') or status.get('ExitCode') != 0 or status.get('OOMKilled'):
                raise RuntimeError('sandbox did not exit cleanly; no output published')
            publish_archive(archive, output)
        finally:
            cancellation['cleaning'] = True
            try:
                removed = subprocess.run([*docker, 'rm', '--force', name], capture_output=True, timeout=15)
                if removed.returncode:
                    remaining = subprocess.run([*docker, 'ps', '-a', '--filter', f'name=^/{name}$', '--format', '{{.ID}}'], capture_output=True, timeout=15)
                    if remaining.returncode or remaining.stdout.strip():
                        raise RuntimeError('could not verify sandbox container removal')
            finally:
                for path in staging.rglob('*'):
                    if path.is_dir():
                        path.chmod(0o700)
                staging.chmod(0o700)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['extract', 'build', 'validate', 'render'])
    parser.add_argument('course', type=Path)
    parser.add_argument('-o', '--out', required=True, type=Path)
    parser.add_argument('--image', required=True)
    parser.add_argument('--docker-context')
    parser.add_argument('--timeout', type=float, default=90)
    args = parser.parse_args()
    try:
        execute(args.course, args.out, args.image, mode=args.mode, context=args.docker_context, timeout=args.timeout)
    except SandboxCancelled as exc:
        print(f'sandbox failed closed: {exc}', file=sys.stderr)
        return 128 + exc.signum
    except (OSError, ValueError, RuntimeError, TimeoutError, subprocess.SubprocessError, tarfile.TarError) as exc:
        print(f'sandbox failed closed: {exc}', file=sys.stderr)
        return 2
    print(f'sandbox {args.mode} published to {args.out}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
