#!/usr/bin/env python3
"""Run required CI controls and reject missing-prerequisite skips."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
SUITES = [
    ('skills/teacher/scripts/tests', 'test_network_policy.py'),
    ('skills/transcript-pipeline/scripts', 'test_resource*.py'),
    ('skills/transcript-pipeline/scripts', 'test_browser_transport.py'),
    ('skills/teacher/skills/explorable/scripts', 'test_sandbox_code.py'),
    ('skills/teacher/skills/course/scripts', 'test_sandbox_course.py'),
    ('skills/transcript-pipeline/scripts', 'test_sandbox_resource_enrichment.py'),
    ('skills/teacher/skills/course/scripts', 'test_render_refusal.py'),
    ('skills/teacher/skills/course/scripts', 'test_supervisor_reaping.py'),
    ('scripts', 'test_render_receipts.py'),
    ('scripts', 'test_candidate_packaging.py'),
]
if len(sys.argv) == 1:
    for directory, pattern in SUITES:
        subprocess.run([sys.executable, __file__, directory, pattern], check=True)
else:
    directory, pattern = sys.argv[1:]
    sys.path.insert(0, str(ROOT / directory))
    suite = unittest.defaultTestLoader.discover(directory, pattern=pattern)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if result.skipped:
        print('REQUIRED CONTROLS SKIPPED:', result.skipped)
    sys.exit(0 if result.wasSuccessful() and result.testsRun and not result.skipped else 1)
