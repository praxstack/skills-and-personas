"""Trusted interpreter controls only: never import authored scenes or render."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


r = load('render_manim', ROOT / 'skills/manim-video/scripts/render_manim.py')
f = load('find_tool', ROOT / 'scripts/find_tool.py')
MANIM = next(t for t in json.loads(f.REGISTRY.read_text())['tools'] if t['id'] == 'manim')


class Resolution(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='manim resolution ')
        self.addCleanup(self.tmp.cleanup)
        self.project = Path(self.tmp.name)
        self.env = self.project / 'isolated env'
        subprocess.run([sys.executable, '-m', 'venv', '--without-pip', str(self.env)], check=True)
        self.py = str(self.env / 'bin/python')
        site = next((self.env / 'lib').glob('python*/site-packages'))
        (site / 'manim.py').write_text('# Trusted import-only test control.\n')
        self.cli = self.env / 'bin/manim'
        self.cli.write_text(f'#!{self.py}\nraise RuntimeError("CLI must never execute")\n')
        self.cli.chmod(0o755)
        self.link = self.project / 'manim link'
        self.link.symlink_to(self.cli)
        self.enterContext(mock.patch.dict(os.environ, {'MANIM_PYTHON': ''}))
        self.enterContext(mock.patch.object(sys, 'executable', str(self.project / 'missing-python')))
        self.enterContext(mock.patch.object(r.shutil, 'which', return_value=str(self.link)))
        self.enterContext(mock.patch.object(os, 'getcwd', return_value=str(self.project)))

    def selected(self, given=None):
        return r.find_python(str(self.project), str(self.project / 'source'), given)

    def discovery(self):
        return f.inspect_tool(MANIM, net=False, mcp=set(), trusted_runtime_probe=True)

    def test_isolated_cli_symlink_and_spaces_shared_with_discovery(self):
        self.assertEqual(self.selected(), self.py)
        found = self.discovery()
        self.assertTrue(found['available'])
        self.assertIn(self.py, found['evidence'][-1])

    def test_module_only_existing_current_interpreter(self):
        with mock.patch.object(r.shutil, 'which', return_value=None), mock.patch.object(sys, 'executable', self.py):
            self.assertEqual(self.selected(), self.py)
            self.assertTrue(self.discovery()['available'])

    def test_explicit_and_environment_priority(self):
        with mock.patch.dict(os.environ, {'MANIM_PYTHON': self.py}), mock.patch.object(r, 'run', return_value=mock.Mock(returncode=0)) as run:
            self.assertEqual(self.selected(sys._base_executable), sys._base_executable)
            run.assert_called_once_with([sys._base_executable, '-c', 'import manim'], timeout=10)
        with mock.patch.dict(os.environ, {'MANIM_PYTHON': self.py}):
            self.assertEqual(self.selected(), self.py)
            self.assertTrue(self.discovery()['available'])

    def test_project_then_source_venv_precedence(self):
        project_py = self.project / '.venv/bin/python'
        project_py.parent.mkdir(parents=True)
        project_py.touch()
        source_py = self.project / 'source/.venv/bin/python'
        source_py.parent.mkdir(parents=True)
        source_py.touch()
        with mock.patch.object(r, 'run', return_value=mock.Mock(returncode=0)):
            self.assertEqual(self.selected(), str(project_py))
            project_py.unlink()
            self.assertEqual(self.selected(), str(source_py))

    def test_malformed_project_state_does_not_crash_discovery(self):
        state = self.project / '.video-state.json'
        for contents in ('{', '[]', '{"config": []}', '{"config": {"source": 3}}'):
            with self.subTest(contents=contents):
                state.write_text(contents)
                self.assertTrue(self.discovery()['available'])

    def test_absent_tool(self):
        with mock.patch.object(r.shutil, 'which', return_value=None):
            self.assertFalse(self.discovery()['available'])
            with self.assertRaisesRegex(SystemExit, 'no Python with manim'):
                self.selected()

    def test_unsupported_shell_and_env_shims_are_never_executed(self):
        for shebang in ('#!/bin/sh', '#!/usr/bin/env python', f'#!{self.py} -I'):
            with self.subTest(shebang=shebang):
                self.cli.write_text(shebang + '\nexit 99\n')
                with mock.patch.object(r.subprocess, 'run') as run:
                    self.assertFalse(self.discovery()['available'])
                    with self.assertRaises(SystemExit):
                        self.selected()
                    run.assert_not_called()

    def test_invalid_import_and_timeout_fail_closed(self):
        for outcome in (mock.Mock(returncode=1), subprocess.TimeoutExpired('python', 10)):
            kw = {'side_effect': outcome} if isinstance(outcome, Exception) else {'return_value': outcome}
            with mock.patch.object(r.subprocess, 'run', **kw):
                self.assertFalse(self.discovery()['available'])
                with self.assertRaises(SystemExit):
                    self.selected()

    def test_selected_python_flows_to_introspection_and_render(self):
        py = self.selected()
        info = {'problems': [], 'segments': [{'id': 'trusted', 'scene': 'Trusted', 'key': 'x', 'frames': 1, 'from': 0, 'to': 1/30}], 'total': 1/30, 'hash': 'x'}
        with mock.patch.object(r, 'run', return_value=mock.Mock(returncode=0, stdout='SEGJSON' + json.dumps(info))) as run:
            self.assertEqual(r.list_segments(py, str(self.project), 30), info)
            self.assertEqual(run.call_args.args[0][0], py)
        proc = mock.Mock(returncode=1)
        proc.poll.return_value = 1
        with mock.patch.object(r, 'find_python', return_value=py), mock.patch.object(sys, 'argv', ['render_manim.py', '--project', str(self.project), '--bench']), mock.patch.object(r, 'list_segments', return_value=info) as segments, mock.patch.object(r.subprocess, 'Popen', return_value=proc) as launch, contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):
                r.main()
            self.assertEqual(segments.call_args.args[0], py)
            self.assertEqual(launch.call_args.args[0][:4], [py, '-m', 'manim', 'render'])


if __name__ == '__main__':
    unittest.main()
