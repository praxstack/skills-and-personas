import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from package_teacher_release import package, git, CANDIDATE_PATHS
from package_teacher_handoff import package as handoff


class Candidate(unittest.TestCase):
    def test_committed_repeat_and_preservation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with contextlib.redirect_stdout(io.StringIO()):
                package('HEAD', '3.0.2', root/'one', candidate=True)
                package('HEAD', '3.0.2', root/'two', candidate=True)
            for path in (root/'one').glob('*.zip'):
                self.assertEqual(path.read_bytes(), (root/'two'/path.name).read_bytes())
            with zipfile.ZipFile(root/'one/transcript-pipeline.zip') as z:
                self.assertIn('transcript-pipeline/SKILL.md', z.namelist())
            with zipfile.ZipFile(root/'one/prax-teach-v3.0.2-source.zip') as z:
                self.assertIn('examples/teach-visual-candidate/base-rates/source/course.json', z.namelist())
                self.assertIn(b'UNACCEPTED CANDIDATE', z.read('START-HERE.md'))
                for topic in ('merge-sort-stability', 'momentum'):
                    self.assertIn(f'examples/teach-visual-candidate/{topic}/source/lesson.lesson.js', z.namelist())
                    self.assertIn(f'examples/teach-visual-candidate/{topic}/bundle/static.html', z.namelist())
                expected = set(git('ls-tree', '-r', '--name-only', 'HEAD', '--', 'skills/teacher', 'skills/teach-pro-max', *CANDIDATE_PATHS).decode().splitlines())
                expected = {n for n in expected if not any(part in {'node_modules', '__pycache__', '.tmp.driveupload'} for part in Path(n).parts)}
                self.assertEqual(set(z.namelist()), expected | {'START-HERE.md', 'LICENSE', 'docs/teach-pro-max/USAGE-GUIDE.md'})
            manifest = json.loads((root/'one/RELEASE-MANIFEST.json').read_text())
            import hashlib
            for asset in manifest['assets']:
                with zipfile.ZipFile(root/'one'/asset['name']) as z:
                    self.assertEqual(z.namelist(), [m['name'] for m in asset['members']])
                    for member in asset['members']:
                        self.assertEqual(hashlib.sha256(z.read(member['name'])).hexdigest(), member['sha256'])
            for component in ('teacher', 'teach-pro-max', 'transcript-pipeline'):
                with zipfile.ZipFile(root/'one'/f'{component}.zip') as z:
                    notice = z.read(f'{component}/CANDIDATE-STATUS.txt')
                    self.assertIn(b'UNACCEPTED CANDIDATE', notice)
                    commit = json.loads((root/'one/RELEASE-MANIFEST.json').read_text())['source_commit']
                    self.assertIn(commit.encode(), notice)
            with self.assertRaises(ValueError): package('HEAD', '3.0.2', root/'one', candidate=True)
            media=root/'media'; media.mkdir()
            for name in ['still.png','explorer.html','qa.html','cards.html','lesson.mp4','interactive-video.html']: (media/name).write_bytes(b'fixture')
            history=root/'history'; history.mkdir(); (history/'old.zip').write_bytes(b'historical fixture')
            sentinel = root/'one/uncommitted-note.txt'; sentinel.write_text('must never ship')
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'extra-file','fixture')
            self.assertFalse((root/'extra-file').exists())
            sentinel.unlink()
            extra_dir = root/'one/extra-directory'; extra_dir.mkdir()
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'extra-directory','fixture')
            self.assertFalse((root/'extra-directory').exists())
            extra_dir.rmdir()
            handoff(root/'one',media,history,root/'handoff','synthetic test only')
            with zipfile.ZipFile(root/'handoff/complete-dot-handoff-candidate.zip') as z:
                self.assertEqual(z.read('historical-artifacts/old.zip'), b'historical fixture')
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'handoff','fixture')
            (media/'link').symlink_to(history/'old.zip')
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'unsafe','fixture')


if __name__ == '__main__': unittest.main()
