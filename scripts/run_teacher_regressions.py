#!/usr/bin/env python3
"""Run required CI controls and reject missing-prerequisite skips."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
_REQUIRED = ('scripts/test_render_receipts.py', 'scripts/test_candidate_packaging.py',
             'scripts/test_portfolio_repair.py', 'scripts/package_teacher_handoff.py',
             'new-skills/transcript-pipeline/scripts/resource_enrichment.py')
if not (ROOT / '.git').exists() or any(not (ROOT / name).is_file() for name in _REQUIRED):
    sys.exit('Full regression validation requires the complete exact Git checkout, '
             'including Git metadata, test utilities and the new-skills mirror. '
             'Source archives are unsupported; no tests were run.')
SUITES = [
    ('skills/teacher/scripts/tests', 'test_network_policy.py'),
    ('skills/teacher/scripts/tests', 'test_find_tool.py'),
    ('skills/teacher/scripts/tests', 'test_manim_resolution.py'),
    ('skills/transcript-pipeline/scripts', 'test_resource*.py'),
    ('skills/transcript-pipeline/scripts', 'test_browser_transport.py'),
    ('skills/teacher/skills/explorable/scripts', 'test_sandbox_code.py'),
    ('skills/teacher/skills/course/scripts', 'test_sandbox_course.py'),
    ('skills/transcript-pipeline/scripts', 'test_sandbox_resource_enrichment.py'),
    ('skills/teacher/skills/course/scripts', 'test_chromium_wrapper.py'),
    ('skills/teacher/skills/course/scripts', 'test_render_refusal.py'),
    ('skills/teacher/skills/course/scripts', 'test_supervisor_reaping.py'),
    ('scripts', 'test_render_receipts.py'),
    ('scripts', 'test_candidate_packaging.py'),
    ('scripts', 'test_portfolio_repair.py'),
    ('skills/transcript-pipeline/scripts', 'test_safe_output.py'),
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
