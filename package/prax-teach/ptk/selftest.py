"""Test runner for `ptk selftest` (automatic tests) and `ptk agent-tests` (agent-mediated tests).

Tests are plain functions named test_* in tests/test_*.py. A function with `agent = True`
belongs to the agent suite. A test raises NotRun(reason) when it cannot run; that is
reported as not-run (exit 5), never as passed.
"""
import importlib.util
import json
import os
import secrets
import sys
import time
import traceback

from . import errors, host
from .state.errors import PraxTeachError

TESTS = host.PKG / "tests"
EXPECTED_FAILURES = (AssertionError, errors.PtkError, OSError, KeyError, ValueError, TypeError, IndexError,
                     AttributeError, LookupError, RuntimeError, json.JSONDecodeError,
                     PraxTeachError)


class NotRun(Exception):
    pass


class AgentPending(Exception):
    """Agent-mediated work is needed (claims jobs written); exit 4."""


def _load(path):
    spec = importlib.util.spec_from_file_location(f"ptk_tests.{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def report_path(suite):
    """A fresh report file per run (WP8 bug fix): runs in parallel never share or overwrite a report.
    $PTK_STATE/selftest/<suite>-<UTC time>-<pid>-<random>.json, created exclusively."""
    root = host.state_path("selftest")
    root.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    while True:
        p = root / f"{suite}-{stamp}-{os.getpid()}-{secrets.token_hex(4)}.json"
        try:
            with open(p, "x"):
                return p
        except FileExistsError:
            continue


def run(suite="auto", pattern=None):
    for p in (str(host.PKG), str(TESTS)):
        if p not in sys.path:
            sys.path.insert(0, p)
    results = []
    for path in sorted(TESTS.glob("test_*.py")):
        mod = _load(path)
        for name in sorted(n for n in dir(mod) if n.startswith("test_")):
            fn = getattr(mod, name)
            is_agent = getattr(fn, "agent", False)
            if (suite == "agent") != is_agent:
                continue
            tid = f"tests/{path.name}::{name}"
            if pattern and pattern not in tid:
                continue
            t0 = time.monotonic()
            try:
                detail = fn()
                status = "passed"
            except NotRun as e:
                status, detail = "not-run", str(e)
            except AgentPending as e:
                status, detail = "claims-pending", str(e)
            except EXPECTED_FAILURES as e:
                status, detail = "failed", "".join(traceback.format_exception_only(type(e), e)).strip()[-1500:]
            results.append({"test": tid, "status": status, "seconds": round(time.monotonic() - t0, 1),
                            "detail": detail})
            print(f"{status:<14} {tid}  ({results[-1]['seconds']} s)", file=sys.stderr)
    out = report_path(suite)
    tmp = out.with_name(out.name + ".part")
    tmp.write_text(json.dumps({"suite": suite, "pattern": pattern, "pid": os.getpid(), "results": results},
                              indent=1, default=str))
    tmp.replace(out)
    print(json.dumps({"suite": suite, "results": [{k: r[k] for k in ("test", "status")} for r in results],
                      "report": str(out)}, indent=1))
    st = {r["status"] for r in results}
    if not results:
        return errors.EXIT_INCOMPLETE
    if "failed" in st:
        return errors.EXIT_GATE
    if "claims-pending" in st:
        return errors.EXIT_CLAIMS_PENDING
    if "not-run" in st:
        return errors.EXIT_INCOMPLETE
    return errors.EXIT_OK
