"""Boundary tests; set COURSE_SANDBOX_IMAGE for actual Docker integration tests."""
from __future__ import annotations

import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
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

    def test_browser_validation_propagates_existing_course_check_failure(self):
        if os.environ.get('COURSE_SANDBOX_BROWSER') != '1':
            self.skipTest('set COURSE_SANDBOX_BROWSER=1 for reviewed browser image')
        # The public checker expects persistence without selecting the course
        # consent checkbox. Preserve that governing check and prove propagation.
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryFile(mode='w+', encoding='utf-8') as log:
            root = Path(temp).resolve()
            course = fixture(root)
            with mock.patch.object(sandbox.sys, 'stderr', log):
                with self.assertRaisesRegex(RuntimeError, 'course process failed'):
                    sandbox.execute(course, root / 'output', IMAGE, mode='validate', context=CONTEXT, timeout=180)
            self.assertFalse((root / 'output').exists())
            log.seek(0)
            result = log.read()
            self.assertIn('interactions 59/59, looks clean', result)
            self.assertIn('FAIL status survives a reload', result)
            self.assertIn('ok   course page looks', result)
            print('browser evidence: 59/59 lesson interactions, lesson/course visual QA passed; existing consent-check failure propagated')

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
