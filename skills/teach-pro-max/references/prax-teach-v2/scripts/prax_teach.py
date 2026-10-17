#!/usr/bin/env python3
"""Executable entrypoint for the dependency-free Prax Teach learner core."""

from __future__ import annotations

import sys

# Read-only routing must also be read-only on a fresh installed tree.
sys.dont_write_bytecode = True

from praxteach.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
