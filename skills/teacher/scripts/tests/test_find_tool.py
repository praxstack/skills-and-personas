"""Ordinary discovery checks: no network or installed packages required."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('find_tool', ROOT / 'scripts/find_tool.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
REG = json.loads((ROOT / 'assets/registry.json').read_text())
TOOLS = {t['id']: t for t in REG['tools']}


class Discovery(unittest.TestCase):
    def inspect(self, name, **kwargs):
        return f.inspect_tool(TOOLS[name], net=kwargs.get('net', False), mcp=kwargs.get('mcp', set()))

    def test_empty_external_probes_are_unknown(self):
        for name in ('d3', 'roughjs', 'canvas', 'browser-voice'):
            with self.subTest(name=name), mock.patch.object(f, 'has_net') as network:
                result = self.inspect(name)
                self.assertFalse(result['available'])
                self.assertEqual(result['status'], 'unknown')
                self.assertTrue(result['missing'])
                network.assert_not_called()

    def test_host_declarations(self):
        with mock.patch.dict(os.environ, {'TEACHER_HOST_TOOLS': 'canvas,host:browser-voice'}):
            hosts = f.host_tools(['mcp:excalidraw'])
        for name in ('canvas', 'browser-voice', 'excalidraw'):
            result = self.inspect(name, mcp=hosts)
            self.assertTrue(result['available'])
            self.assertEqual(result['status'], 'declared')

    def test_network_is_reachability_only(self):
        for name in ('d3', 'kroki'):
            for reachable in (True, False):
                with self.subTest(name=name, reachable=reachable), mock.patch.object(f, 'has_net', return_value=reachable) as network:
                    result = self.inspect(name, net=True)
                    network.assert_called_once()
                    self.assertFalse(result['available'])
                    self.assertEqual(result['status'], 'reachable' if reachable else 'unknown')

    def test_instruction_asset_and_svg(self):
        self.assertEqual(self.inspect('lesson-notebook')['status'], 'instructions')
        self.assertTrue(self.inspect('svg')['available'])
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(f, 'ROOT', Path(tmp)):
            result = self.inspect('lesson-notebook')
            self.assertFalse(result['available'])
            self.assertEqual(result['status'], 'missing')

    def test_manim_module_or_isolated_cli(self):
        for module, cli, expected in ((False, True, True), (True, False, True), (False, False, False)):
            with self.subTest(module=module, cli=cli), mock.patch.object(f, 'has_py', return_value=module), mock.patch.object(f, 'has_bin', return_value=cli), mock.patch.object(f.subprocess, 'run') as execute:
                result = self.inspect('manim')
                self.assertEqual(result['available'], expected)
                self.assertEqual(result['status'], 'detected' if expected else 'missing')
                execute.assert_not_called()

    def test_inventory_offline_overrides_net_without_requests(self):
        output = io.StringIO()
        with mock.patch.object(sys, 'argv', ['find_tool.py', '--inventory', '--offline', '--net', '--json']), mock.patch.object(f, 'has_net') as network, mock.patch.object(f, 'has_bin', return_value=False), mock.patch.object(f, 'has_py', return_value=False), mock.patch.object(f, 'has_node', return_value=False), contextlib.redirect_stdout(output):
            self.assertEqual(f.main(), 0)
        network.assert_not_called()
        rows = json.loads(output.getvalue())
        self.assertTrue(rows)
        self.assertTrue(all(TOOLS[r['id']]['offline'] for r in rows))
        self.assertNotIn('canvas', [r['id'] for r in rows])
        self.assertNotIn('d3', [r['id'] for r in rows])
        self.assertTrue(all(isinstance(r['available'], bool) for r in rows))
        self.assertTrue(all('missing' in r and 'score' in r and 'how' in r for r in rows))


if __name__ == '__main__':
    unittest.main()
