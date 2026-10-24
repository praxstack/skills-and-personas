#!/usr/bin/env python3
"""Launch the pinned sandbox browser with bounded foreground pool scheduling."""
from __future__ import annotations

import os
import re
import sys

BROWSER = '/ms-playwright/chromium_headless_shell-1208/chrome-linux/headless_shell'
BASE_ARGS = ['--no-zygote', '--renderer-process-limit=1', '--num-raster-threads=1',
             '--disable-gpu', '--disable-software-rasterizer']
POOL_FEATURE = 'BrowserThreadPoolAdjustment'


def browser_arguments(arguments: list[str]) -> list[str]:
    """Merge feature switches without dropping Playwright's other defaults.

    This wrapper owns the pool feature's parameter. Replace conflicting copies
    with the reviewed min/2 value while retaining unrelated features and args.
    Chromium otherwise treats duplicate switches as replacement, not a merge.
    """
    retained, features = [], []
    incoming = iter(arguments)
    for argument in incoming:
        if argument == '--enable-features':
            value = next(incoming, None)
            if value is None or value.startswith('--'):
                raise ValueError('--enable-features requires a value')
        elif argument.startswith('--enable-features='):
            value = argument.partition('=')[2]
        else:
            retained.append(argument)
            continue
        features.extend(feature for feature in value.split(',') if feature
                        and re.split(r'[:<]', feature, maxsplit=1)[0] != POOL_FEATURE)
    features.append(POOL_FEATURE + ':min/2')
    return [*BASE_ARGS, *retained, '--enable-features=' + ','.join(features)]


if __name__ == '__main__':
    os.execv(BROWSER, [BROWSER, *browser_arguments(sys.argv[1:])])
