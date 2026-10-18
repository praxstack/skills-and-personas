"""Shim for the ported v2 tests: `prax_teach.py <args>` runs the v2.1 port, `python -m ptk.state`."""
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from ptk.state.cli import main  # noqa: E402

raise SystemExit(main())
