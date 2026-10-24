"""Product packaging checks; does not change portfolio lint/scanner acceptance."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/transcript-pipeline/scripts'
COPY = ROOT / 'new-skills/transcript-pipeline/scripts'
STAGES = ('stage1-refine', 'stage2-synthesize', 'stage3-enhance')


def tracked_sources():
    paths = subprocess.check_output(
        ['git', 'ls-files', '-z', 'skills/transcript-pipeline/scripts/'], cwd=ROOT
    ).decode().split('\0')
    return {Path(p).relative_to('skills/transcript-pipeline/scripts').as_posix()
            for p in paths if p}


def assert_parity(case, source, copy):
    expected = tracked_sources()
    actual = {p.relative_to(copy).as_posix() for p in copy.rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    case.assertEqual(expected, actual, 'Restored tree must contain all and only tracked sources')
    for name in sorted(expected):
        original = (source / name).read_bytes()
        restored = (copy / name).read_bytes()
        if name == 'run_chat_pipeline.py':
            for stage in STAGES:
                old = f'docs/prompts/stages/{stage}.md'.encode()
                new = f'references/{stage}.md'.encode()
                case.assertEqual(original.count(old), 1)
                case.assertEqual(restored.count(new), 1)
                original = original.replace(old, new)
        case.assertEqual(original, restored, name)
        case.assertEqual((source / name).stat().st_mode & 0o111,
                         (copy / name).stat().st_mode & 0o111, name)


class PipelinePackagingTests(unittest.TestCase):
    def run_python(self, *args, expected=0, cwd=None):
        result = subprocess.run([sys.executable, '-B', *map(str, args)], cwd=cwd,
                                capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_source_parity(self):
        assert_parity(self, SOURCE, COPY)

    def test_parity_rejects_runtime_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'scripts'
            shutil.copytree(COPY, copy, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            with (copy / 'resource_budget.py').open('a') as out:
                out.write('\n# unauthorized second-codepath drift\n')
            with self.assertRaises(AssertionError):
                assert_parity(self, SOURCE, copy)

    def test_parity_rejects_fourth_path_substitution(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'scripts'
            shutil.copytree(COPY, copy, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            runner = copy / 'run_chat_pipeline.py'
            runner.write_text(runner.read_text().replace('references/stage1-refine.md', 'references/other.md'))
            with self.assertRaises(AssertionError):
                assert_parity(self, SOURCE, copy)

    def test_local_imports_and_cli_help(self):
        modules = sorted(p.stem for p in COPY.glob('*.py') if not p.name.startswith('test_'))
        self.run_python('-c', '; '.join(f'import {name}' for name in modules), cwd=COPY)
        for module in modules:
            if module in {'resource_budget', 'safe_resource_output'}:
                continue  # Shared library, not a CLI.
            with self.subTest(module=module):
                result = self.run_python(COPY / (module + '.py'), '--help')
                self.assertIn('usage:', result.stdout.lower())

    def test_synthetic_ingestion_and_stage_handoff(self):
        with tempfile.TemporaryDirectory(prefix='portfolio-repair-') as tmp:
            session = Path(tmp)
            transcript = session / 'meeting_saved_closed_caption.txt'
            text = '[Teacher] 00:00:01\nA stack uses last in first out order.\n[Student] 00:00:05\nokay\n'
            transcript.write_text(text)
            self.run_python(COPY / 'ingest_zoom_captions.py', transcript)
            pipeline = session / '.pipeline'
            ledger = pipeline / 'segment_ledger.jsonl'
            original = ledger.read_bytes()
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            self.assertEqual([r['type'] for r in rows], ['content', 'noise'])
            self.assertEqual(rows[0]['raw_text'], 'A stack uses last in first out order.')
            manifest_rows = [json.loads(line) for line in (pipeline / 'segment_manifest.jsonl').read_text().splitlines()]
            self.assertEqual([r['segment_id'] for r in rows], [r['segment_id'] for r in manifest_rows])
            self.run_python(COPY / 'run_chat_pipeline.py', 'run', transcript,
                            '--non-interactive', expected=3)
            self.assertEqual(original, ledger.read_bytes())
            self.assertEqual(transcript.read_text(), text)
            handoff = (pipeline / 'stage1_chat_handoff.md').read_text()
            self.assertIn(str(COPY.parent / 'references/stage1-refine.md'), handoff)
            self.assertIn(str(pipeline / 'refined_transcript.md'), handoff)
            state = json.loads((pipeline / 'run_manifest.json').read_text())
            self.assertEqual(state['status'], 'waiting_for_chat_stage')
            self.assertEqual(state['stages']['ingest'], 'completed')
            for stage in STAGES:
                self.assertTrue((COPY.parent / 'references' / (stage + '.md')).is_file())
            self.assertFalse((session / '.resources').exists())


if __name__ == '__main__':
    unittest.main()
