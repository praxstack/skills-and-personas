#!/usr/bin/env python3
"""Run one resource manifest in an explicit Docker process-resource sandbox.

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


HERE = Path(__file__).resolve().parent
OUTPUT_LIMIT = 256 * 1024 * 1024
ARCHIVE_LIMIT = OUTPUT_LIMIT + 2 * 1024 * 1024
LOG_LIMIT = 1024 * 1024
FILE_LIMIT = 1024


def open_directory(path):
    """Resolve every path component through a no-follow directory descriptor."""
    path = Path(os.path.abspath(path))
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
            os.close(fd)
            fd = child
        return fd
    except BaseException:
        os.close(fd)
        raise


def read_bound_file(path, limit):
    path = Path(os.path.abspath(path))
    parent = open_directory(path.parent)
    try:
        fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > limit:
                raise ValueError('input must be a bounded, single-link regular file')
            result = source.read(limit + 1)
            if len(result) > limit:
                raise ValueError('input byte budget exhausted')
            after = os.fstat(source.fileno())
            if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('input changed during snapshot')
            return result
    finally:
        os.close(parent)


def private_write(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as sink:
        sink.write(data)


def credential_data(path, kind):
    from urllib.parse import urlsplit
    raw = read_bound_file(path, 65536 if kind == 'notion' else 1024 * 1024)
    try:
        data = json.loads(raw)
        if kind == 'notion':
            if (not isinstance(data, dict) or set(data) != {'token_v2', 'active_user'} or
                    not all(isinstance(v, str) and v and len(v) < 32768 and not any(ord(c) < 32 for c in v) for v in data.values())):
                raise ValueError()
        else:
            rows = data if kind == 'cookies' else data['cookies']
            if not isinstance(rows, list) or len(rows) > 1000:
                raise ValueError()
            for row in rows:
                domain = row['domain']
                if (not isinstance(domain, str) or not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?', domain) or '..' in domain or
                        not isinstance(row['name'], str) or not row['name'] or not isinstance(row['value'], str)):
                    raise ValueError()
                if kind == 'canva' and not (domain == 'canva.com' or domain.endswith('.canva.com')):
                    raise ValueError()
                if not isinstance(row.get('path', '/'), str) or not row.get('path', '/').startswith('/'):
                    raise ValueError()
                if any(ord(c) < 32 or ord(c) == 127 for c in row['name'] + row['value'] + row.get('path', '/')):
                    raise ValueError()
                if kind == 'canva':
                    import math
                    if (set(row) != {'name', 'value', 'domain', 'path', 'expires', 'httpOnly', 'secure', 'sameSite'} or
                            row.get('secure') is not True or not isinstance(row.get('httpOnly'), bool) or
                            row.get('sameSite') not in {'Strict', 'Lax', 'None'} or
                            type(row.get('expires')) not in {int, float} or not math.isfinite(row['expires'])):
                        raise ValueError()
            if kind == 'canva':
                if set(data) != {'cookies', 'origins'} or not isinstance(data['origins'], list) or len(data['origins']) > 1000:
                    raise ValueError()
                for row in data['origins']:
                    origin = row['origin']
                    parsed = urlsplit(origin)
                    if (parsed.scheme != 'https' or parsed.port not in {None, 443} or parsed.username or parsed.password or
                            parsed.path or parsed.query or parsed.fragment or not parsed.hostname or
                            not (parsed.hostname == 'canva.com' or parsed.hostname.endswith('.canva.com')) or
                            origin not in {'https://' + parsed.hostname, 'https://' + parsed.hostname + ':443'}):
                        raise ValueError()
                    if not isinstance(row['localStorage'], list):
                        raise ValueError()
                    for item in row['localStorage']:
                        if not isinstance(item['name'], str) or not isinstance(item['value'], str):
                            raise ValueError()
    except (ValueError, TypeError, KeyError, AttributeError):
        raise ValueError('invalid explicit credential file: ' + kind) from None
    return raw


def snapshot(session, staging, cookies=None, notion=None, canva=None):
    raw = read_bound_file(session / '.pipeline/resource_manifest.json', 1024 * 1024)
    try:
        manifest = json.loads(raw)
        if not isinstance(manifest, dict) or not isinstance(manifest.get('resources'), list) or len(manifest['resources']) > 100:
            raise ValueError()
    except (ValueError, TypeError):
        raise ValueError('invalid resource manifest') from None
    private_write(staging / 'input/session/.pipeline/resource_manifest.json', raw)
    (staging / 'secrets').mkdir(mode=0o700)
    total = len(raw)
    for kind, path in [('cookies', cookies), ('notion', notion), ('canva', canva)]:
        if path is not None:
            data = credential_data(path, kind)
            total += len(data)
            if total > 4 * 1024 * 1024:
                raise ValueError('aggregate input byte budget exhausted')
            private_write(staging / 'secrets' / (kind + '.json'), data)
    for name in ('resource_enrichment.py', 'resource_budget.py', 'safe_resource_output.py'):
        # Installation tools may use hardlink mirrors. Read an owned descriptor.
        fd = os.open(HERE / name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        with os.fdopen(fd, 'rb') as source:
            info = os.fstat(source.fileno())
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_size > 1024 * 1024:
                raise ValueError('untrusted installation tool')
            data = source.read(1024 * 1024 + 1)
            if len(data) > 1024 * 1024:
                raise ValueError('installation tool byte budget exhausted')
        private_write(staging / 'tools' / name, data)
    private_write(staging / 'tools/worker.py', WORKER.encode())
    private_write(staging / 'tools/supervisor.py', SUPERVISOR.encode())
    private_write(staging / 'tools/chromium', CHROMIUM.encode())
    for directory in staging.rglob('*'):
        if directory.is_dir():
            directory.chmod(0o700)
    (staging / 'tools/chromium').chmod(0o700)


def unpack_archive(archive: Path, destination: Path, check_deadline=lambda: None) -> None:
    """Validate every member before writing; never call tarfile.extract()."""
    if archive.stat().st_size > ARCHIVE_LIMIT:
        raise ValueError('sandbox archive exceeds byte budget')
    # Inspect physical headers as tarfile transparently consumes PAX/GNU records.
    with archive.open('rb') as raw:
        while True:
            check_deadline()
            header = raw.read(512)
            if not header or header == b'\0' * 512:
                for tail in iter(lambda: raw.read(65536), b''):
                    check_deadline()
                    if any(tail):
                        raise ValueError('sandbox archive contains trailing records')
                break
            if len(header) != 512 or header[156:157] not in {b'0', b'\0', b'5'} or header[124] & 0x80:
                raise ValueError('sandbox archive contains extension or special records')
            try:
                size = int(header[124:136].rstrip(b'\0 ').strip() or b'0', 8)
            except ValueError:
                raise ValueError('invalid sandbox archive size') from None
            if size < 0 or size > 64 * 1024 * 1024:
                raise ValueError('sandbox member exceeds byte budget')
            raw.seek((size + 511) // 512 * 512, 1)
    with tarfile.open(archive, mode='r:') as source:
        members, seen, total = [], set(), 0
        for member in source:
            check_deadline()
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
            if len(members) > FILE_LIMIT or total > OUTPUT_LIMIT or member.size < 0 or member.size > 64 * 1024 * 1024 or (member.isdir() and member.size):
                raise ValueError('sandbox archive exceeds artifact budget')
        kinds = {m.name: m.isdir() for m in members}
        for name in kinds:
            parents = PurePosixPath(name).parents
            if any(str(p) in kinds and not kinds[str(p)] for p in parents):
                raise ValueError('sandbox archive has a file/directory prefix collision')
        if not members:
            raise ValueError('sandbox produced no artifacts')
        for member in members:
            check_deadline()
            path = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                path.mkdir(mode=0o700, parents=True, exist_ok=True)
            else:
                path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
                with source.extractfile(member) as incoming, os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as outgoing:
                    for chunk in iter(lambda: incoming.read(1024 * 1024), b''):
                        check_deadline()
                        outgoing.write(chunk)


def publish_archive(archive: Path, output: Path, check_deadline=lambda: None) -> None:
    """Exclusive descriptor-anchored destination; existing files never overwritten."""
    output = Path(os.path.abspath(output))
    parent = open_directory(output.parent)
    created = False
    try:
        # Validate in a private directory before making the public destination.
        with tempfile.TemporaryDirectory(prefix='teacher-unpack-') as temp:
            staged = Path(temp)
            unpack_archive(archive, staged, check_deadline)
            check_deadline()
            os.mkdir(output.name, mode=0o700, dir_fd=parent)
            created = True
            fd = os.open(output.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=parent)
            try:
                def copy_tree(src: Path, target_fd: int):
                    for child in src.iterdir():
                        check_deadline()
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
                                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                                    check_deadline()
                                    sink.write(chunk)
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


def capture(command: list[str], archive: Path, timeout: float) -> int:
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ, 'archive')
    selector.register(proc.stderr, selectors.EVENT_READ, 'log')
    started = time.monotonic()
    totals = {'archive': 0, 'log': 0}
    try:
        with os.fdopen(os.open(archive, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), 'wb') as sink:
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
                    # Child diagnostics are deliberately discarded: they can contain credentials.
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



CHROMIUM = '''#!/bin/sh
exec /ms-playwright/chromium_headless_shell-1208/chrome-linux/headless_shell --no-zygote --renderer-process-limit=1 --num-raster-threads=1 --disable-gpu --disable-software-rasterizer "$@"
'''

WORKER = r'''
import json, os, pathlib, shutil
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import resource_enrichment as enrichment
from resource_budget import JobBudget
os.umask(0o077)
root = pathlib.Path('/tmp/session')
(root / '.pipeline').mkdir(parents=True)
shutil.copyfile('/input/session/.pipeline/resource_manifest.json', root / '.pipeline/resource_manifest.json')
# Preflight is mandatory, even when the manifest currently needs HTTP only.
with sync_playwright() as p:
    browser, context = enrichment.new_public_browser_context(p, executable_path='/tools/chromium', auth_origins=set())
    context.close()
    browser.close()
notion = pathlib.Path('/secrets/notion.json')
cookies = pathlib.Path('/secrets/cookies.json')
canva = pathlib.Path('/secrets/canva.json')
values = json.loads(notion.read_text()) if notion.exists() else {}
origins = set()
if canva.exists():
    state = json.loads(canva.read_text())
    origins.update('https://' + row['domain'] for row in state['cookies'])
    origins.update('https://' + urlsplit(row['origin']).hostname for row in state['origins'])
budget = JobBudget(seconds=float(os.environ['JOB_SECONDS']))
report = enrichment.enrich_session(root, values.get('token_v2'), values.get('active_user'),
    canva if canva.exists() else None, cookies if cookies.exists() else None, False,
    budget=budget, auth_origins=origins,
    browser_executable='/tools/chromium')
report['session_dir'] = 'session'
report['auth'] = {'notion_credentials_present': notion.exists(), 'cookies_present': cookies.exists(),
                  'canva_state_present': canva.exists(), 'provider_authentication_verified': False}
# Exception messages can contain request headers. Keep status, omit raw diagnostics.
for item in report['results']:
    if item.get('error'):
        item['error'] = 'Resource request failed; raw diagnostic omitted.'
    item['notes'] = ['Resource processing note omitted by isolated runner.'] if item.get('notes') else []
report['path_base'] = 'logical session; output_files are relative to session, not the --out directory'
with enrichment.budgets.job_scope(budget):
    enrichment.save_text(root / '.resources/resource_enrichment_report.json', json.dumps(report, indent=2) + '\n', False)
'''

SUPERVISOR = r'''
import os, pathlib, selectors, signal, stat, subprocess, sys, tarfile, time
os.umask(0o077)
def stop(signum, frame):
    try:
        os.kill(-1, signal.SIGKILL)
    except ProcessLookupError:
        pass
    os._exit(124)
for sig in (signal.SIGALRM, signal.SIGTERM, signal.SIGHUP, signal.SIGINT):
    signal.signal(sig, stop)
seconds = float(sys.argv[1])
signal.setitimer(signal.ITIMER_REAL, seconds)
env = {'PATH': '/usr/local/bin:/usr/bin:/bin', 'HOME': '/tmp', 'TMPDIR': '/tmp',
       'PYTHONDONTWRITEBYTECODE': '1', 'PYTHONPATH': '/opt/enrichment',
       'PLAYWRIGHT_BROWSERS_PATH': '/ms-playwright', 'JOB_SECONDS': str(seconds)}
child = subprocess.Popen(['python3', '/tools/worker.py'], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, start_new_session=True)
selector = selectors.DefaultSelector()
selector.register(child.stdout, selectors.EVENT_READ)
count = 0
try:
    while child.poll() is None:
        for key, _ in selector.select(0.05):
            data = os.read(key.fileobj.fileno(), 65536)
            if not data:
                selector.unregister(key.fileobj)
                continue
            count += len(data)
            if count > 1048576:
                stop(None, None)
    code = child.wait()
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
# Drain buffered diagnostics after descendants are dead; never print their contents.
for data in iter(lambda: child.stdout.read(65536), b''):
    count += len(data)
child.stdout.close()
selector.close()
if code or count > 1048576:
    sys.exit(1)
root = pathlib.Path('/tmp/session/.resources')
if not root.is_dir() or root.is_symlink():
    sys.exit(1)
files = []
total = 0
for directory, dirs, names in os.walk(root, followlinks=False):
    for name in dirs + names:
        path = pathlib.Path(directory) / name
        info = path.lstat()
        if not (stat.S_ISDIR(info.st_mode) or (stat.S_ISREG(info.st_mode) and info.st_nlink == 1)):
            sys.exit(1)
        if stat.S_ISREG(info.st_mode):
            total += info.st_size
            if info.st_size > 67108864:
                sys.exit(1)
        files.append(path)
        if total > 268435456 or len(files) > 1024:
            sys.exit(1)
if not files:
    sys.exit(1)
with tarfile.open(fileobj=sys.stdout.buffer, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
    for path in sorted(files):
        archive.add(path, arcname=path.relative_to(root).as_posix(), recursive=False)
'''


def container_command(docker, name, image, staging, timeout):
    return [*docker, 'create', '--pull=never', '--init=false', '--name', name,
            '--network=bridge', '--log-driver=none', '--read-only', f'--user={os.getuid()}:{os.getgid()}',
            '--cap-drop=ALL', '--security-opt=no-new-privileges', '--pids-limit=128',
            '--memory=1g', '--memory-swap=1g', '--cpus=1', '--ulimit=nofile=256:256',
            '--ulimit=fsize=67108864:67108864', '--ulimit=core=0:0',
            '--tmpfs=/tmp:rw,nosuid,nodev,size=512m,mode=1777,exec',
            '--tmpfs=/dev/shm:rw,nosuid,nodev,noexec,size=64m',
            '--mount', f'type=bind,src={staging / "input"},dst=/input,readonly',
            '--mount', f'type=bind,src={staging / "secrets"},dst=/secrets,readonly',
            '--mount', f'type=bind,src={staging / "tools"},dst=/tools,readonly',
            '--workdir=/tmp', '--env=HOME=/tmp', '--env=TMPDIR=/tmp',
            '--env=PYTHONDONTWRITEBYTECODE=1', '--env=PYTHONPATH=/opt/enrichment',
            '--entrypoint=python3', image, '/tools/supervisor.py', str(timeout)]


def execute(session, output, image, *, context=None, timeout=600, cookies=None, notion=None, canva=None):
    with cancellation_handlers() as cancellation:
        _execute(session, output, image, context=context, timeout=timeout, cookies=cookies,
                 notion=notion, canva=canva, cancellation=cancellation)


def _execute(session, output, image, *, context, timeout, cookies, notion, canva, cancellation):
    if not re.fullmatch(r'sha256:[0-9a-f]{64}', image):
        raise ValueError('image must be an immutable local sha256 image ID')
    if not 0 < timeout <= 600:
        raise ValueError('timeout must be greater than zero and at most 600 seconds')
    if not shutil.which('docker') or os.getuid() == 0:
        raise RuntimeError('Docker and a non-root client are required')
    output = Path(os.path.abspath(output))
    parent = open_directory(output.parent)
    try:
        try:
            os.stat(output.name, dir_fd=parent, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            raise FileExistsError('output must be a new destination')
    finally:
        os.close(parent)
    docker = ['docker', *(['--context', context] if context else [])]
    deadline = time.monotonic() + timeout
    def remaining(maximum):
        left = deadline - time.monotonic()
        if left <= 0:
            raise TimeoutError('sandbox external deadline exhausted')
        return min(maximum, left)
    inspected = subprocess.run([*docker, 'image', 'inspect', image], capture_output=True, timeout=remaining(15))
    if inspected.returncode:
        raise RuntimeError('Docker daemon or reviewed local image unavailable')
    name = 'resource-enrichment-' + uuid.uuid4().hex
    # Home is Docker-shareable on macOS; only private explicitly selected snapshots enter the VM.
    with tempfile.TemporaryDirectory(prefix='.enrichment-', dir=Path.home()) as temp:
        staging = Path(temp).resolve()
        snapshot(Path(session), staging, cookies, notion, canva)
        try:
            command = container_command(docker, name, image, staging, remaining(600))
            created = subprocess.run(command, capture_output=True, timeout=remaining(20))
            if created.returncode:
                raise RuntimeError('sandbox container creation failed')
            archive = staging / 'output.tar'
            code = capture([*docker, 'start', '--attach', name], archive, remaining(600))
            if code:
                raise RuntimeError('sandbox process failed or exhausted its budget; nothing published')
            state = subprocess.run([*docker, 'inspect', '--format', '{{json .State}}', name],
                                   capture_output=True, timeout=remaining(15))
            if state.returncode:
                raise RuntimeError('cannot verify sandbox exit')
            status = json.loads(state.stdout)
            if status.get('Running') or status.get('ExitCode') != 0 or status.get('OOMKilled'):
                raise RuntimeError('sandbox did not exit cleanly; nothing published')
            remaining(1)
            publish_archive(archive, output, lambda: remaining(1))
        finally:
            cancellation['cleaning'] = True
            try:
                subprocess.run([*docker, 'rm', '--force', name], capture_output=True, timeout=15)
                remaining_containers = subprocess.run([*docker, 'ps', '-a', '--filter', f'name=^/{name}$',
                    '--format', '{{.ID}}'], capture_output=True, timeout=15)
                if remaining_containers.returncode or remaining_containers.stdout.strip():
                    raise RuntimeError('could not verify owned sandbox removal')
            except subprocess.SubprocessError:
                raise RuntimeError('could not verify owned sandbox removal') from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session-dir', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--image', required=True)
    parser.add_argument('--docker-context')
    parser.add_argument('--timeout', type=float, default=600)
    parser.add_argument('--cookies-json', type=Path)
    parser.add_argument('--notion-credentials', type=Path)
    parser.add_argument('--canva-storage-state', type=Path)
    args = parser.parse_args()
    try:
        execute(args.session_dir, args.out, args.image, context=args.docker_context, timeout=args.timeout,
                cookies=args.cookies_json, notion=args.notion_credentials, canva=args.canva_storage_state)
    except SandboxCancelled as exc:
        print(str(exc), file=sys.stderr)
        return 128 + exc.signum
    except RuntimeError as exc:
        if 'could not verify owned sandbox removal' in str(exc):
            print('Enrichment failed; could not verify owned sandbox removal.', file=sys.stderr)
        else:
            print('Enrichment failed closed; runtime, cancellation or budget failure.', file=sys.stderr)
        return 2
    except (OSError, ValueError, subprocess.SubprocessError, tarfile.TarError):
        # Host exception paths/data can contain private names or credentials.
        print('Enrichment failed closed; no completed result. Check input/runtime limits. '
              'Publication failure can leave a partial new private output directory.', file=sys.stderr)
        return 2
    print('Isolated enrichment completed and published locally.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
