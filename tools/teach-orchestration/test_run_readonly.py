import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("run_readonly", Path(__file__).with_name("run_readonly.py"))
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class WorkerTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.pack = self.root / "input"
        self.pack.mkdir()
        self.task = self.pack / "TASK.md"
        self.task.write_text("Read only.")
        self.worker = self.root / "fake-worker"

    def execute(self, code, timeout=2):
        self.worker.write_text("#!/usr/bin/env python3\n" + code)
        self.worker.chmod(0o700)
        with patch.object(runner.shutil, "which", return_value=str(self.worker)):
            return runner.run("grok", self.task, self.pack, self.root / "output", timeout)

    def test_success_is_not_content_acceptance(self):
        receipt = self.execute("print('{}')\n")
        self.assertEqual(receipt["status"], "returned_requires_review")
        self.assertEqual(receipt["acceptance"], "not_reviewed")
        self.assertEqual(receipt["changed_input_files"], [])
        self.assertNotIn("receipt.json", receipt["output_inventory"])

    def test_provider_error_is_not_completion(self):
        receipt = self.execute("import sys\nsys.exit(7)\n")
        self.assertEqual(receipt["status"], "provider_failed")
        self.assertEqual(receipt["exit_code"], 7)

    def test_timeout_leaves_receipt(self):
        receipt = self.execute("import time\ntime.sleep(30)\n", timeout=1)
        self.assertEqual(receipt["status"], "local_process_timed_out")
        self.assertLess(receipt["elapsed_seconds"], 7)
        self.assertTrue((self.root / "output" / "receipt.json").is_file())

    def test_worker_write_rejected_even_with_zero_exit(self):
        receipt = self.execute("from pathlib import Path\nPath('TASK.md').write_text('changed')\n")
        self.assertEqual(receipt["status"], "input_modified_reject")
        self.assertEqual(receipt["changed_input_files"], ["TASK.md"])

    def test_api_key_not_inherited(self):
        with patch.dict(os.environ, {"CURSOR_API_KEY": "synthetic-not-a-real-key"}):
            receipt = self.execute("import os, json\nprint(json.dumps({'key_present': 'CURSOR_API_KEY' in os.environ}))\n")
        result = json.loads((self.root / "output" / "stdout.json").read_text())
        self.assertFalse(result["key_present"])
        self.assertEqual(receipt["status"], "returned_requires_review")

    def test_symlink_escape_refused_before_launch(self):
        (self.pack / "escape").symlink_to(self.root)
        with self.assertRaises(ValueError):
            self.execute("print('{}')\n")


if __name__ == "__main__":
    unittest.main()
