"""Boundary tests; set COURSE_SANDBOX_IMAGE for actual Docker integration tests."""
from __future__ import annotations

import io
import json
import os
import signal
import shutil
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import time
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sandbox_course as sandbox

IMAGE = os.environ.get('COURSE_SANDBOX_IMAGE')
CONTEXT = os.environ.get('COURSE_SANDBOX_CONTEXT', 'colima-teach-security')
EXAMPLE = sandbox.SKILLS / 'explorable/assets/examples/seasons.lesson.js'
ESCAPE = "const p=console.log.constructor('return process')();const require=p.getBuiltinModule('module').createRequire('/tmp/authored.js');\n"


def fixture(root: Path, prefix: str = '') -> Path:
    course = root / 'course'
    course.mkdir()
    (course / 'lesson.lesson.js').write_text(prefix + EXAMPLE.read_text())
    (course / 'course.json').write_text(json.dumps({'id': 'seasons', 'title': 'Seasons', 'lessons': [
        {'id': 'seasons', 'title': 'Why seasons happen', 'file': 'lesson.lesson.js', 'needs': [], 'minutes': 3, 'summary': 'Tilt changes the light.'}]}))
    return course


class ArchiveTests(unittest.TestCase):
    def make_tar(self, path, members):
        with tarfile.open(path, 'w', format=tarfile.USTAR_FORMAT) as archive:
            for name, kind, size in members:
                row = tarfile.TarInfo(name)
                row.type = kind
                row.size = size
                if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE):
                    row.linkname = '/tmp/escape'
                archive.addfile(row, io.BytesIO(b'x' * size) if row.isfile() else None)

    def test_archive_rejects_paths_links_special_and_duplicates(self):
        bad = [[(name, tarfile.REGTYPE, 1)] for name in ('../escape', '/absolute', 'a/../escape', 'a\\escape', './escape', 'a//b')]
        bad += [[('x', kind, 0)] for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE)]
        bad += [[('x', tarfile.REGTYPE, 1), ('x', tarfile.REGTYPE, 1)]]
        for rows in bad:
            with self.subTest(rows=rows), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                self.make_tar(root / 'out.tar', rows)
                with self.assertRaises(ValueError):
                    sandbox.publish_archive(root / 'out.tar', root / 'published')
                self.assertFalse((root / 'published').exists())
                self.assertFalse((root / 'escape').exists())

    def test_budget_and_no_overwrite_or_link_following(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            self.make_tar(root / 'out.tar', [('a/b.txt', tarfile.REGTYPE, 4)])
            with mock.patch.object(sandbox, 'OUTPUT_LIMIT', 3):
                with self.assertRaises(ValueError):
                    sandbox.publish_archive(root / 'out.tar', root / 'too-large')
            sandbox.publish_archive(root / 'out.tar', root / 'new')
            self.assertEqual((root / 'new/a/b.txt').read_bytes(), b'xxxx')
            with self.assertRaises(FileExistsError):
                sandbox.publish_archive(root / 'out.tar', root / 'new')
            (root / 'link').symlink_to(root / 'new', target_is_directory=True)
            with self.assertRaises(OSError):
                sandbox.publish_archive(root / 'out.tar', root / 'link/child')
            self.assertFalse((root / 'new/child').exists())

    def test_empty_and_member_count(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            self.make_tar(root / 'out.tar', [])
            with self.assertRaises(ValueError):
                sandbox.publish_archive(root / 'out.tar', root / 'empty')
            self.make_tar(root / 'out.tar', [('a', tarfile.REGTYPE, 1), ('b', tarfile.REGTYPE, 1)])
            with mock.patch.object(sandbox, 'FILE_LIMIT', 1):
                with self.assertRaises(ValueError):
                    sandbox.publish_archive(root / 'out.tar', root / 'many')

    def test_missing_runtime_image_and_invalid_modes_fail_closed(self):
        image = 'sha256:' + '0' * 64
        with mock.patch.object(sandbox.shutil, 'which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'Docker unavailable'):
                sandbox.execute(Path('absent'), Path('new'), image)
        with mock.patch.object(sandbox.shutil, 'which', return_value='/docker'), mock.patch.object(sandbox.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1)):
            with self.assertRaisesRegex(RuntimeError, 'runtime or reviewed local image unavailable'):
                sandbox.execute(Path('absent'), Path('new'), image)
        for mode, img in [('narrate', image), ('build', 'node:latest')]:
            with self.assertRaises(ValueError):
                sandbox.execute(Path('absent'), Path('new'), img, mode=mode)

    def test_lifecycle_cleanup_after_create_start_and_copy_failures(self):
        for phase in ('create', 'start', 'copy'):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                course = fixture(root)
                calls = []
                def docker_run(command, **kwargs):
                    calls.append(command)
                    if 'create' in command and phase == 'create':
                        return subprocess.CompletedProcess(command, 1)
                    state = b'{"Running":false,"ExitCode":0,"OOMKilled":false}'
                    return subprocess.CompletedProcess(command, 0, stdout=state)
                capture = mock.Mock(return_value=0)
                if phase == 'start':
                    capture.side_effect = TimeoutError('injected startup timeout')
                with mock.patch.object(sandbox.subprocess, 'run', side_effect=docker_run), mock.patch.object(sandbox, 'capture', capture), mock.patch.object(sandbox, 'publish_archive', side_effect=ValueError('injected invalid archive')), mock.patch.object(sandbox.shutil, 'which', return_value='/docker'):
                    with self.assertRaises((RuntimeError, TimeoutError, ValueError)):
                        sandbox.execute(course, root / 'output', 'sha256:' + '0' * 64)
                self.assertTrue(any('rm' in call and '--force' in call for call in calls))
                self.assertFalse((root / 'output').exists())

    def test_cli_missing_runtime_and_local_image(self):
        command = [sys.executable, str(sandbox.HERE / 'sandbox_course.py'), 'build', 'absent', '-o', 'new', '--image', 'sha256:' + '0' * 64, '--docker-context', CONTEXT]
        missing_runtime = subprocess.run(command, capture_output=True, text=True, env={**os.environ, 'PATH': '/nonexistent'}, timeout=10)
        self.assertEqual(missing_runtime.returncode, 2)
        self.assertIn('Docker unavailable', missing_runtime.stderr)
        missing_image = subprocess.run(command, capture_output=True, text=True, timeout=20)
        self.assertEqual(missing_image.returncode, 2)
        self.assertIn('runtime or reviewed local image unavailable', missing_image.stderr)

    def test_cancellation_handlers_restore_and_reject_worker_threads(self):
        signals = (signal.SIGTERM, signal.SIGHUP, signal.SIGINT)
        previous = {number: signal.getsignal(number) for number in signals}
        for number in signals:
            with self.assertRaises(sandbox.SandboxCancelled):
                with sandbox.cancellation_handlers():
                    signal.getsignal(number)(number, None)
            self.assertEqual(previous, {item: signal.getsignal(item) for item in signals})
        with self.assertRaises(sandbox.SandboxCancelled):
            with sandbox.cancellation_handlers() as state:
                state['cleaning'] = True
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                self.assertEqual(state['signal'], signal.SIGTERM)
        failures = []
        def worker():
            try:
                sandbox.execute(Path('absent'), Path('new'), 'sha256:' + '0' * 64)
            except RuntimeError as exc:
                failures.append(str(exc))
        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=2)
        self.assertEqual(len(failures), 1)
        self.assertIn('main Python thread', failures[0])
        self.assertEqual(previous, {item: signal.getsignal(item) for item in signals})

    def test_input_links_and_aggregate_budget_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            course = fixture(root)
            (course / 'lesson.lesson.js').unlink()
            (course / 'lesson.lesson.js').symlink_to(EXAMPLE)
            with self.assertRaises(OSError):
                with sandbox.bounded_inputs(course):
                    self.fail('link admitted')
        with tempfile.TemporaryDirectory() as temp:
            course = fixture(Path(temp).resolve())
            with mock.patch.object(sandbox, 'INPUT_LIMIT', 1024):
                with self.assertRaises(ValueError):
                    with sandbox.bounded_inputs(course):
                        self.fail('oversize admitted')


@unittest.skipUnless(IMAGE, 'set COURSE_SANDBOX_IMAGE to run actual Docker boundary tests')
class DockerTests(unittest.TestCase):
    def setUp(self):
        self.owned_names = set()
        real_uuid4 = sandbox.uuid.uuid4
        def tracked_uuid4():
            value = real_uuid4()
            self.owned_names.add('teacher-course-' + value.hex)
            return value
        self.uuid_patch = mock.patch.object(sandbox.uuid, 'uuid4', side_effect=tracked_uuid4)
        self.uuid_patch.start()

    def run_course(self, prefix='', *, mode='extract', timeout=30):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            course = fixture(root, prefix)
            output = root / 'output'
            sandbox.execute(course, output, IMAGE, mode=mode, context=CONTEXT, timeout=timeout)
            return {p.relative_to(output).as_posix(): p.read_bytes() for p in output.rglob('*') if p.is_file()}

    def cancellation_control(self, signum, *, mode='extract', prefix=None):
        token = sandbox.uuid.uuid4().hex
        name = 'teacher-course-' + token
        docker = ['docker', '--context', CONTEXT]
        staging = None
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            source = prefix if prefix is not None else ESCAPE + "require('child_process').spawnSync('python3',['-c','while True: pass']);"
            course = fixture(root, source)
            private_temp = root / 'host-temporaries'
            private_temp.mkdir(mode=0o700)
            # Fix only this invocation's UUID so cancellation never touches or
            # attributes another concurrently running invocation's container.
            driver = "import sys,uuid;sys.path.insert(0,sys.argv.pop(1));import sandbox_course as s;token=sys.argv.pop(1);s.uuid.uuid4=lambda:uuid.UUID(hex=token);sys.exit(s.main())"
            command = [sys.executable, '-c', driver, str(sandbox.HERE), token, mode, str(course), '-o', str(root / 'output'), '--image', IMAGE, '--docker-context', CONTEXT, '--timeout', '8']
            with tempfile.TemporaryFile(mode='w+') as log:
                proc = subprocess.Popen(command, stdout=log, stderr=log, env={**os.environ, 'TMPDIR': str(private_temp)})
                started = time.monotonic()
                try:
                    running = None
                    deadline = time.monotonic() + 12
                    while time.monotonic() < deadline:
                        result = subprocess.run([*docker, 'inspect', name], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            row = json.loads(result.stdout)[0]
                            if row['State']['Running']:
                                running = row
                                break
                        if proc.poll() is not None:
                            break
                        time.sleep(0.05)
                    self.assertIsNotNone(running, 'owned container never started')
                    staging = Path(next(item['Source'] for item in running['Mounts'] if item['Destination'] == '/input')).parent
                    self.assertEqual(staging.parent, Path.home().resolve())
                    self.assertTrue(staging.name.startswith('.teacher-course-'))
                    # Wait for actual native/browser authored execution, rather
                    # than merely a live dependency preflight or supervisor.
                    marker_deadline = time.monotonic() + 6
                    while time.monotonic() < marker_deadline:
                        check = subprocess.run([*docker, 'top', name, '-eo', 'pid,args'], capture_output=True, text=True, timeout=5)
                        if (mode == 'extract' and 'python3 -c while True: pass' in check.stdout) or (mode == 'validate' and 'test_lesson.mjs' in check.stdout and 'headless_shell' in check.stdout):
                            break
                        time.sleep(0.05)
                    else:
                        self.fail(f'authored process did not start before cancellation; top={check.stdout!r}; error={check.stderr!r}')
                    proc.send_signal(signum)
                    proc.wait(timeout=20)
                    if signum != signal.SIGKILL:
                        self.assertEqual(proc.returncode, 128 + signum)
                        inspect = subprocess.run([*docker, 'inspect', name], capture_output=True, text=True, timeout=5)
                        self.assertNotEqual(inspect.returncode, 0, 'catchable cancellation leaked container')
                        self.assertFalse(staging.exists(), 'catchable cancellation leaked staging')
                        self.assertEqual(list(private_temp.iterdir()), [])
                    else:
                        self.assertEqual(proc.returncode, -signal.SIGKILL)
                        end = started + 13
                        stopped = None
                        while time.monotonic() < end:
                            result = subprocess.run([*docker, 'inspect', '--format', '{{json .State}}', name], capture_output=True, text=True, timeout=5)
                            self.assertEqual(result.returncode, 0)
                            state = json.loads(result.stdout)
                            if not state['Running']:
                                stopped = state
                                break
                            time.sleep(0.1)
                        self.assertIsNotNone(stopped, 'container deadline failed after host SIGKILL')
                        self.assertEqual(stopped['ExitCode'], 124)
                        self.assertTrue(staging.exists(), 'SIGKILL recovery limitation changed')
                    self.assertFalse((root / 'output').exists())
                    elapsed = time.monotonic() - started
                    print(f'cancellation control: {signal.Signals(signum).name}, mode={mode}, stopped in {elapsed:.2f}s, no publication')
                finally:
                    if proc.poll() is None:
                        proc.kill()
                        proc.wait(timeout=5)
                    subprocess.run([*docker, 'rm', '--force', name], capture_output=True, timeout=15)
                    if staging is not None and staging.parent == Path.home().resolve() and staging.name.startswith('.teacher-course-'):
                        for path in staging.rglob('*'):
                            if path.is_dir():
                                path.chmod(0o700)
                        shutil.rmtree(staging, ignore_errors=True)

    def test_host_sigterm_cleans_infinite_native_child(self):
        self.cancellation_control(signal.SIGTERM)

    def test_host_sigkill_container_deadline_stops_infinite_native_child(self):
        self.cancellation_control(signal.SIGKILL)

    def test_host_sigkill_deadline_stops_detached_descendant(self):
        prefix = ESCAPE + "require('child_process').spawn('python3',['-c','while True: pass'],{detached:true,stdio:'ignore'}).unref();require('child_process').spawnSync('python3',['-c','while True: pass']);"
        self.cancellation_control(signal.SIGKILL, prefix=prefix)

    def test_host_sigkill_deadline_stops_browser_authored_js(self):
        if os.environ.get('COURSE_SANDBOX_BROWSER') != '1':
            self.skipTest('set COURSE_SANDBOX_BROWSER=1 for reviewed browser image')
        self.cancellation_control(signal.SIGKILL, mode='validate', prefix="if(typeof document!=='undefined'){while(true){}};")

    def test_legitimate_extract_and_build_offline(self):
        self.assertIn('course.json', self.run_course())
        built = self.run_course(mode='build')
        self.assertIn('index.html', built)
        self.assertIn('seasons.html', built)
        self.assertIn(b'Why seasons happen', built['seasons.html'])

    def test_fs_env_network_memory_boundary(self):
        with tempfile.TemporaryDirectory() as temp:
            sentinel = Path(temp).resolve() / 'host-secret'
            sentinel.write_text('host-only-value')
            prefix = ESCAPE + f'''
const fs=require('fs'), cp=require('child_process');
if(fs.existsSync({json.dumps(str(sentinel))}) || p.env.COURSE_SANDBOX_SECRET) throw Error('host data exposed');
for(const file of ['/input/course/lesson.lesson.js','/tools/supervisor.py','/host-write']) {{
  let denied=false;try{{fs.writeFileSync(file,'evil')}}catch(e){{denied=true}};if(!denied)throw Error('write escaped');
}}
if(fs.readFileSync('/sys/fs/cgroup/memory.max','utf8').trim() !== '536870912') throw Error('memory unbounded');
if(fs.readFileSync('/sys/fs/cgroup/pids.max','utf8').trim() !== '64') throw Error('pids unbounded');
const n=cp.spawnSync('python3',['-c',"import socket; socket.create_connection(('1.1.1.1',80),1)"],{{timeout:2000}});
if(n.status===0) throw Error('network escaped');
'''
            with mock.patch.dict(os.environ, {'COURSE_SANDBOX_SECRET': 'not-forwarded'}):
                self.assertIn('course.json', self.run_course(prefix))
            self.assertEqual(sentinel.read_text(), 'host-only-value')

    def test_adopted_browser_style_exits_reaped_during_live_job(self):
        # The owned Node job stays alive while a Python child forks an orphan.
        # Without PID 1 reaping during its wait, that orphan remains a zombie.
        prefix = ESCAPE + r"""
const fs=require('fs'), cp=require('child_process');
for(let i=0;i<4;i++){
  const r=cp.spawnSync('python3',['-c','import os,time; pid=os.fork(); time.sleep(0.05) if pid==0 else None; os._exit(0)']);
  if(r.status!==0)throw Error('orphan fixture failed');
}
const deadline=Date.now()+2000;
let zombies=[];
do{
  zombies=fs.readdirSync('/proc').filter(x=>/^\d+$/.test(x)).filter(pid=>{
    try{const s=fs.readFileSync('/proc/'+pid+'/status','utf8');return /^PPid:\s*1$/m.test(s)&&/^State:\s*Z/m.test(s)}catch{return false}
  });
}while(zombies.length&&Date.now()<deadline);
if(zombies.length)throw Error('PID 1 retained adopted zombie exits: '+zombies);
"""
        self.assertIn('course.json', self.run_course(prefix))

    def test_adopted_exit_does_not_mask_owned_failure(self):
        prefix = ESCAPE + "require('child_process').spawnSync('python3',['-c','import os,time; pid=os.fork(); time.sleep(0.05) if pid==0 else None; os._exit(0)']);p.exit(7);"
        with self.assertRaisesRegex(RuntimeError, 'course process failed'):
            self.run_course(prefix)

    def test_detached_setsid_descendant_is_killed_before_packaging(self):
        prefix = ESCAPE + "require('child_process').spawn('node',['-e',\"setTimeout(()=>require('fs').writeFileSync('/tmp/output/escaped','bad'),1000);setInterval(()=>{},1000)\"],{detached:true,stdio:'ignore'}).unref();\n"
        self.assertEqual(set(self.run_course(prefix)), {'course.json'})

    def test_infinite_loop_log_flood_artifact_flood_and_process_exhaustion(self):
        attacks = [
            (ESCAPE + "require('child_process').spawnSync('python3',['-c','while True: pass']);", 2),
            (ESCAPE + "while(true)p.stderr.write('x'.repeat(65536));", 20),
            (ESCAPE + "const fs=require('fs');for(let i=0;i<1100;i++)fs.writeFileSync('/tmp/output/f'+i,'x');", 20),
            (ESCAPE + "require('child_process').spawnSync('python3',['-c','x=bytearray(1024**3)']);", 15),
            (ESCAPE + "require('fs').symlinkSync('/etc/passwd','/tmp/output/unsafe-link');", 20),
            (ESCAPE + "require('child_process').spawnSync('python3',['-c',\"import subprocess,time; children=[subprocess.Popen(['sleep','60'],start_new_session=True) for _ in range(100)]; time.sleep(60)\"]);", 5),
        ]
        for source, timeout in attacks:
            with self.subTest(source=source[:70]):
                with self.assertRaises((RuntimeError, TimeoutError)):
                    self.run_course(source, timeout=timeout)

    def test_linked_course_video_manifest_and_local_assets(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            course = fixture(root)
            (course / 'videos').mkdir()
            (course / 'videos/seasons.vtt').write_text('WEBVTT\n\n00:00.000 --> 00:01.000\nHello\n')
            catalog = root / 'catalog'
            catalog.mkdir()
            (catalog / 'linked').symlink_to(course, target_is_directory=True)
            (catalog / 'videos.json').write_text('{"seasons/seasons.mp4":"https://example.com/film.mp4"}')
            sandbox.execute(catalog / 'linked', root / 'remote', IMAGE, mode='build', context=CONTEXT)
            self.assertIn('https://example.com/film.mp4', (root / 'remote/index.html').read_text())
            self.assertTrue((root / 'remote/videos/seasons.vtt').is_file())
            (course / 'videos/seasons.mp4').write_bytes(b'local-video-fixture')
            sandbox.execute(course, root / 'local', IMAGE, mode='build', context=CONTEXT)
            self.assertEqual((root / 'local/videos/seasons.mp4').read_bytes(), b'local-video-fixture')
            self.assertIn('videos/seasons.mp4', (root / 'local/index.html').read_text())

    def test_browser_validation_passes_consent_v2(self):
        if os.environ.get('COURSE_SANDBOX_BROWSER') != '1':
            self.skipTest('set COURSE_SANDBOX_BROWSER=1 for reviewed browser image')
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
            root = Path(temp).resolve()
            course = fixture(root)
            with mock.patch.object(sandbox.sys, 'stderr', log):
                sandbox.execute(course, root / 'output', IMAGE, mode='validate', context=CONTEXT, timeout=180)
            self.assertTrue((root / 'output/index.html').is_file())
            self.assertTrue((root / 'output/seasons.html').is_file())
            log.seek(0)
            result = log.read()
            self.assertIn('interactions 59/59, looks clean', result)
            self.assertIn('course page: 26 passed, 0 failed', result)
            self.assertIn('ok   course page looks', result)
            self.assertIn('seasons: 1 lessons, all passed', result)
            print('browser evidence: 59/59 lesson interactions, consent v2 26/26, lesson/course visual QA passed; output published')

    def test_browser_validation_propagates_real_course_check_failure(self):
        if os.environ.get('COURSE_SANDBOX_BROWSER') != '1':
            self.skipTest('set COURSE_SANDBOX_BROWSER=1 for reviewed browser image')
        # Corrupt only this test's private tool snapshot. A genuine course-page
        # JavaScript error must fail v2 and prevent publication, even though the
        # otherwise valid lesson and visual checks still pass.
        copy_tools = sandbox.copy_tools
        def inject_page_error(destination):
            copy_tools(destination)
            engine = destination / 'course/assets/engine/course.js'
            with engine.open('a') as sink:
                sink.write('\nthrow new Error("intentional-course-validation-control");\n')
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
            root = Path(temp).resolve()
            course = fixture(root)
            with mock.patch.object(sandbox, 'copy_tools', side_effect=inject_page_error), mock.patch.object(sandbox.sys, 'stderr', log):
                with self.assertRaisesRegex(RuntimeError, 'course process failed'):
                    sandbox.execute(course, root / 'output', IMAGE, mode='validate', context=CONTEXT, timeout=180)
            self.assertFalse((root / 'output').exists())
            log.seek(0)
            result = log.read()
            self.assertIn('interactions 59/59, looks clean', result)
            self.assertIn('FAIL no page errors intentional-course-validation-control', result)
            self.assertIn('course page: 25 passed, 1 failed', result)
            print('browser evidence: deliberate real course-page error failed v2 and prevented publication')

    def test_browser_infinite_authored_js_is_stopped(self):
        if os.environ.get('COURSE_SANDBOX_BROWSER') != '1':
            self.skipTest('set COURSE_SANDBOX_BROWSER=1 for reviewed browser image')
        with self.assertRaises(TimeoutError):
            self.run_course("if(typeof document!=='undefined'){while(true){}};", mode='validate', timeout=15)

    def tearDown(self):
        self.uuid_patch.stop()
        result = subprocess.run(['docker', '--context', CONTEXT, 'ps', '-a', '--filter', 'name=teacher-course-', '--format', '{{.Names}}'], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.owned_names.intersection(result.stdout.splitlines()), 'owned sandbox container leaked')


if __name__ == '__main__':
    unittest.main()
