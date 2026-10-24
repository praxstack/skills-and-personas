"""Default trust refusal for the fixed render helpers; no authored code runs."""
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parent

class RenderRefusalTests(unittest.TestCase):
    def test_python_refuses_before_input_or_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'must-not-exist'
            result=subprocess.run([sys.executable,str(HERE/'render_course.py'),str(Path(tmp)/'missing-course'),'--out',str(out)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('refusing authored execution without --trust-authored-code',result.stderr)
            self.assertFalse(out.exists())

    @unittest.skipUnless(shutil.which('node'),'Node unavailable')
    def test_javascript_refuses_before_browser_or_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'must-not-exist'
            result=subprocess.run(['node',str(HERE/'render_course.mjs'),str(Path(tmp)/'missing.html'),str(out)],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('authored execution requires --trust-authored-code',result.stderr)
            self.assertFalse(out.exists())

if __name__=='__main__':unittest.main()
