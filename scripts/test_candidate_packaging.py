import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from package_teacher_release import package
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
            with self.assertRaises(ValueError): package('HEAD', '3.0.2', root/'one', candidate=True)
            media=root/'media'; media.mkdir()
            for name in ['still.png','explorer.html','qa.html','cards.html','lesson.mp4','interactive-video.html']: (media/name).write_bytes(b'fixture')
            history=root/'history'; history.mkdir(); (history/'old.zip').write_bytes(b'historical fixture')
            handoff(root/'one',media,history,root/'handoff','synthetic test only')
            with zipfile.ZipFile(root/'handoff/complete-dot-handoff-candidate.zip') as z:
                self.assertEqual(z.read('historical-artifacts/old.zip'), b'historical fixture')
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'handoff','fixture')
            (media/'link').symlink_to(history/'old.zip')
            with self.assertRaises(ValueError): handoff(root/'one',media,history,root/'unsafe','fixture')


if __name__ == '__main__': unittest.main()
