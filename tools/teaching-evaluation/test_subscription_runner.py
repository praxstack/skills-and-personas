import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('runner', Path(__file__).with_name('subscription_runner.py'))
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)

class RunnerTests(unittest.TestCase):
    def test_grader_data_omitted(self):
        with self.assertRaises(ValueError):
            r.validate_scenario({'id': 'x', 'turns': ['hello'], 'rubric': 'answer'})
        with self.assertRaises(ValueError):
            r.validate_scenario({'id': '../escape', 'turns': ['hello']})

    def test_path_escape_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'link').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                r.tree(root)

    def test_initial_hardlinks_rejected_final_metadata_diagnostic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'file').write_text('public snapshot')
            r.os.link(root / 'file', root / 'alias')
            with self.assertRaises(ValueError):
                r.tree(root)
            self.assertEqual(r.tree(root, reject_hardlinks=False)['file'], r.digest(b'public snapshot'))
            (root / 'escape').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                r.tree(root, reject_hardlinks=False)

    def test_output_retention_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p / 'lesson.txt').write_text('actual lesson')
            self.assertEqual(r.tree(p), {'lesson.txt': r.digest(b'actual lesson')})
            self.assertEqual((p / 'lesson.txt').read_text(), 'actual lesson')

    def test_pair_separation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'SKILL.md').write_text('public teaching skill')
            for arm in ('baseline', 'candidate'):
                r.shutil.copytree(source, root / arm / 'package')
            (root / 'baseline/response.txt').write_text('baseline only')
            self.assertFalse((root / 'candidate/response.txt').exists())
            self.assertEqual(r.tree(root / 'baseline/package'), r.tree(root / 'candidate/package'))

    def test_no_tools_and_no_grader_fields(self):
        self.assertTrue(r.no_tools(b'{"type":"item.completed","item":{"type":"agent_message","text":"hello"}}\n'))
        self.assertFalse(r.no_tools(b'{"type":"item.completed","item":{"type":"command_execution"}}\n'))
        self.assertFalse(r.no_tools(b'{"type":"mcp_tool_call.started"}\n'))

    def test_excluded_dependencies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / '.venv').mkdir()
            (root / '.venv/ignored').symlink_to('/etc/passwd')
            (root / 'SKILL.md').write_text('skill')
            self.assertEqual(set(r.tree(root)), {'SKILL.md'})

    def test_paired_run_error_is_retained_and_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'SKILL.md').write_text('public skill')
            auth = root / 'public-auth-placeholder'
            auth.write_text('not a credential')
            output = root / 'receipts'
            with patch.object(r.shutil, 'which', return_value='/bin/echo'), \
                 patch.object(r, 'execute', return_value=(7, b'', b'deterministic failure', False)):
                self.assertFalse(r.run(source, source, {'id': 'error', 'turns': ['public user']},
                                       output, 'public-model', repetitions=1, auth=auth))
            self.assertFalse(json.loads((output / 'result.json').read_text())['transport_passed'])
            for arm in ('baseline', 'candidate'):
                self.assertEqual((output / ('1-' + arm) / 'turn-1.stderr.txt').read_text(), 'deterministic failure')
                self.assertEqual(json.loads((output / ('1-' + arm) / 'turn-1.json').read_text())['exit_code'], 7)
            self.assertTrue((output / 'manifest.json').exists())

    def test_failure_propagation(self):
        with patch.object(r.subprocess, 'Popen') as popen:
            popen.return_value.communicate.return_value = (b'failure', b'error')
            popen.return_value.returncode = 7
            self.assertEqual(r.execute(['fake'], 'request', {}, 1), (7, b'failure', b'error', False))

    def test_timeout_kills_process_group_and_retains(self):
        with patch.object(r.subprocess, 'Popen') as popen, patch.object(r.os, 'killpg') as kill:
            popen.return_value.pid = 42
            popen.return_value.returncode = -9
            popen.return_value.communicate.side_effect = [subprocess.TimeoutExpired('fake', 1), (b'partial', b'')]
            self.assertEqual(r.execute(['fake'], 'request', {}, 1), (-9, b'partial', b'', True))
            kill.assert_called_once_with(42, r.signal.SIGKILL)

    def test_missing_scoring_inspection_refused(self):
        for value in ({}, {'independent_grader': True}, {'independent_grader': True, 'inspection_passed': True}):
            with self.assertRaises(ValueError):
                r.validate_grading(value)
        self.assertEqual(r.validate_grading({'independent_grader': True, 'inspection_passed': True,
                                            'dimensions': [2, 2, 2, 2, 2], 'protected_failures': []}), 10)

    def test_fixed_numeric_gates(self):
        records = []
        for family in range(6):
            for rep in (1, 2, 3):
                for arm in ('baseline', 'candidate'):
                    records.append({'family': str(family), 'replicate': rep, 'arm': arm,
                                    'independent_grader': True, 'inspection_passed': True,
                                    'protected_failures': [],
                                    'dimensions': [1, 1, 1, 1, 1] if arm == 'baseline' else [2, 2, 2, 2, 2]})
        checks = {key: True for key in ('protected_public_probes_passed', 'deterministic_regressions_passed',
                  'rendered_inspection_passed', 'frozen_boundary_review_passed', 'receipts_integrity_passed', 'budget_passed')}
        self.assertTrue(r.aggregate_scores(records, checks)['accepted'])
        checks['rendered_inspection_passed'] = False
        self.assertFalse(r.aggregate_scores(records, checks)['accepted'])
        with self.assertRaises(ValueError):
            r.aggregate_scores(records[:-1], checks)
        with self.assertRaises(ValueError):
            r.aggregate_scores(records, {})

if __name__ == '__main__':
    unittest.main()
