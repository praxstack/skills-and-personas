"""Real temporary filesystem controls; no network or credentials."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import resource_enrichment as enrichment
import safe_resource_output as output


class OutputConfinementTests(unittest.TestCase):
    def session(self, root):
        return enrichment.enrich_session(root, None, None, None, None, False)

    def test_zero_resource_directory_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'session'; root.mkdir()
            outside = Path(tmp) / 'outside'; outside.mkdir()
            (root / '.resources').symlink_to(outside, target_is_directory=True)
            with self.assertRaises((ValueError, OSError)):
                self.session(root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_zero_resource_report_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'session'; (root / '.resources').mkdir(parents=True)
            outside = Path(tmp) / 'outside'; outside.write_bytes(b'untouched')
            (root / '.resources/resource_enrichment_report.json').symlink_to(outside)
            with self.assertRaises((ValueError, OSError)):
                self.session(root)
            self.assertEqual(outside.read_bytes(), b'untouched')

    def test_zero_resource_report_hardlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'session'; (root / '.resources').mkdir(parents=True)
            outside = Path(tmp) / 'outside'; outside.write_bytes(b'untouched')
            os.link(outside, root / '.resources/resource_enrichment_report.json')
            with self.assertRaises((ValueError, OSError)):
                self.session(root)
            self.assertEqual(outside.read_bytes(), b'untouched')

    def test_output_directory_swap_after_open_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'session'; (root / '.resources').mkdir(parents=True)
            outside = Path(tmp) / 'outside'; outside.mkdir()
            def swap():
                (root / '.resources').rename(root / 'original-resources')
                (root / '.resources').symlink_to(outside, target_is_directory=True)
                return mock.Mock()
            with mock.patch.object(enrichment, '_new_session', side_effect=swap):
                with self.assertRaises((ValueError, OSError)):
                    self.session(root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_selected_session_swap_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'session'; root.mkdir()
            outside = Path(tmp) / 'outside'; outside.mkdir()
            def swap():
                root.rename(root.with_name('original-session'))
                root.symlink_to(outside, target_is_directory=True)
                return mock.Mock()
            with mock.patch.object(enrichment, '_new_session', side_effect=swap):
                with self.assertRaises((ValueError, OSError)): self.session(root)
            self.assertEqual(list(outside.iterdir()), [])

    def test_report_fifo_is_rejected_without_opening(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.resources').mkdir()
            os.mkfifo(root / '.resources/resource_enrichment_report.json')
            with self.assertRaises(ValueError):
                self.session(root)

    def test_destination_swap_during_staging_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); resources = root / '.resources'; resources.mkdir()
            outside = root / 'outside'; outside.write_bytes(b'untouched')
            destination = resources / 'resource_enrichment_report.json'
            destination.write_bytes(b'original')
            check = output.OutputDirectory.check
            calls = []
            def swap(directory):
                calls.append(1)
                if len(calls) == 2:
                    destination.unlink(); destination.symlink_to(outside)
                check(directory)
            with mock.patch.object(output.OutputDirectory, 'check', swap):
                with self.assertRaises(ValueError): self.session(root)
            self.assertEqual(outside.read_bytes(), b'untouched')
            self.assertEqual([p.name for p in resources.iterdir()], ['resource_enrichment_report.json'])

    def test_artifact_link_is_rejected_by_same_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.resources').mkdir()
            outside = root / 'outside'; outside.write_bytes(b'untouched')
            for hardlink in (False, True):
                artifact = root / '.resources/demo.html'
                if hardlink: os.link(outside, artifact)
                else: artifact.symlink_to(outside)
                with output.session_output(root, False):
                    with self.assertRaises(ValueError): enrichment.save_bytes(artifact, b'unsafe', False)
                self.assertEqual(outside.read_bytes(), b'untouched')
                artifact.unlink()

    def test_active_session_rejects_output_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); outside = root / 'outside'
            with output.session_output(root, False):
                with self.assertRaises(ValueError): enrichment.save_bytes(outside, b'unsafe', False)
            self.assertFalse(outside.exists())

    def test_valid_report_and_artifact_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); (root / '.pipeline').mkdir()
            (root / '.pipeline/resource_manifest.json').write_text(json.dumps({'resources': [{'name':'demo', 'url':'https://8.8.8.8/'}]}))
            response = mock.Mock(status_code=200, url='https://8.8.8.8/', encoding='utf-8')
            with mock.patch.object(enrichment, 'fetch_limited', return_value=(response, b'<title>safe</title>')):
                for _ in range(2):
                    report = self.session(root)
                    self.assertEqual(report['results'][0]['status'], 'ok')
                    self.assertEqual((root / '.resources/demo.html').read_bytes(), b'<title>safe</title>')
                    self.assertEqual(json.loads((root / '.resources/resource_enrichment_report.json').read_text()), report)
            self.assertEqual(sorted(p.name for p in (root / '.resources').iterdir()), ['demo.html', 'resource_enrichment_report.json'])


if __name__ == '__main__': unittest.main()
