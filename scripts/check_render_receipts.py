#!/usr/bin/env python3
"""Consume existing render QA receipts; this does not grant human acceptance."""
import argparse
import json
from pathlib import Path


def check(root, require_video=True):
    for label in ('lesson', 'visual'):
        status = json.loads((root / f'{label}-status.json').read_text())
        if type(status.get('returncode')) is not int or status['returncode'] != 0:
            raise ValueError(f'{label} QA failed: {status}')
    evidence = json.loads((root / 'render-evidence.json').read_text())
    checks = evidence.get('checks')
    if not isinstance(checks, list) or not checks or any(
        not isinstance(c, dict) or c.get('ok') is not True for c in checks
    ):
        raise ValueError('missing or failed render checks')
    for key in ('errors', 'network'):
        if evidence.get(key) != []:
            raise ValueError(f'missing or nonempty {key}')
    if require_video and not any(c.get('name') == 'actual video playback advances' for c in checks):
        raise ValueError('actual playback evidence missing')
    return len(checks)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--no-video', action='store_true')
    args = parser.parse_args()
    print(f'{check(args.output, not args.no_video)} render checks and both QA statuses passed; full-course/human acceptance separate')
