#!/usr/bin/env python3
"""Run original assertions against an explicitly selected synthetic lesson and workspace.

This changes fixture locations in memory, never assertions or source tests. Results are
local regression diagnostics, not independent acceptance. PTK_STATE must be outside
Developer/Study; tools must already be provisioned. Does not run setup or reviewers.
"""
import argparse
import os
from pathlib import Path
import sys

parser = argparse.ArgumentParser()
parser.add_argument('-k', required=True)
parser.add_argument('--lesson-copy', required=True)
a = parser.parse_args()
state = Path(os.environ['PTK_STATE']).resolve()
assert str(state).startswith('/private/tmp/prax-teach-c-v3-'), state
os.environ['PRAX_TEACH_SYNC_ROOTS'] = ''
root = Path(__file__).resolve().parents[3]
pkg = root / 'projects/prax-teach-c-adapter/package/prax-teach'
sys.path[:0] = [str(pkg), str(pkg / 'tests')]
import _util
from ptk import selftest
_util.SLICE = Path(a.lesson_copy).resolve()
assert str(_util.SLICE).startswith('/private/tmp/prax-teach-c-v3-')
_util.report.__defaults__ = (_util.SLICE,)
original_load = selftest._load

def load(path):
    module = original_load(path)
    if hasattr(module, 'C_WORKSPACE'):
        module.C_WORKSPACE = state / 'synthetic-c-workspace'
    return module

selftest._load = load
raise SystemExit(selftest.run(pattern=a.k))
