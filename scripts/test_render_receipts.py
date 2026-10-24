import json
from pathlib import Path
import tempfile
import unittest
from check_render_receipts import check


class Receipts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.write('lesson-status.json', {'returncode': 0})
        self.write('visual-status.json', {'returncode': 0})
        self.evidence = {'checks': [{'name': 'actual video playback advances', 'ok': True}], 'errors': [], 'network': []}
        self.write('render-evidence.json', self.evidence)

    def write(self, name, value):
        (self.root / name).write_text(json.dumps(value))

    def test_valid(self):
        self.assertEqual(check(self.root), 1)

    def test_qa_failure_even_with_successful_export(self):
        for label in ('lesson', 'visual'):
            with self.subTest(label=label):
                self.write(f'{label}-status.json', {'returncode': 1})
                with self.assertRaises(ValueError): check(self.root)
                self.write(f'{label}-status.json', {'returncode': 0})

    def test_bad_evidence(self):
        for key, value in [('checks', []), ('checks', [{'ok': False}]), ('errors', ['error']), ('network', ['https://example.com']), ('errors', None)]:
            with self.subTest(key=key, value=value):
                self.write('render-evidence.json', {**self.evidence, key: value})
                with self.assertRaises(ValueError): check(self.root)

    def test_missing_playback(self):
        self.evidence['checks'][0]['name'] = 'static check'
        self.write('render-evidence.json', self.evidence)
        with self.assertRaises(ValueError): check(self.root)
        self.assertEqual(check(self.root, require_video=False), 1)

    def test_missing_receipt(self):
        (self.root / 'visual-status.json').unlink()
        with self.assertRaises(FileNotFoundError): check(self.root)


if __name__ == '__main__': unittest.main()
