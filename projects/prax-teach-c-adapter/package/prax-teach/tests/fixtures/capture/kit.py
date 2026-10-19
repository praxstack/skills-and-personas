"""Builds throwaway lessons around the capture fixtures (not a test module).

make_lesson() writes a schema-valid lesson.json into a fresh dir under $PTK_STATE/tmp, with the
given programs copied into programs/. Each test states its own programs, facts and claims;
the trace and storyboard are the smallest valid ones.
"""
import json
import shutil
from pathlib import Path

from ptk import host

HERE = Path(__file__).resolve().parent
PROBE = HERE.parent / "sandbox-probe" / "probe.c"

SOURCE = [{"title": "ISO/IEC 9899:2018 (C17)", "clause": "7.21.6.1"}]


def program(pid, fixture, ub=False, run=True, args=None):
    p = {"id": pid, "path": f"programs/{Path(fixture).name}", "std": "c17", "ub": ub, "run": run,
         "_fixture": str(fixture if Path(fixture).is_absolute() else HERE / fixture)}
    if args:
        p["args"] = list(args)
    return p


def program_text(pid, name, text, ub=False, run=True):
    """A program whose source is given inline (written into programs/<name> by make_lesson)."""
    p = {"id": pid, "path": f"programs/{name}", "std": "c17", "ub": ub, "run": run, "_text": text}
    return p


def fact(fid, pid, line=None, expect=None, stream="stdout", key=None):
    sel = {"stream": stream}
    if line is not None:
        sel["line"] = line
    if key is not None:
        sel["key"] = key
    return {"id": fid, "program": pid, "kind": "stdout-line" if stream == "stdout" else "value", "select": sel,
            "expect": expect or {"value": "", "reviewed": True}}


def claim(cid, text="This sentence teaches one thing about the program.", kind="mechanism", facts=None,
          programs=None):
    c = {"id": cid, "text": text, "kind": kind, "justification": "Fixture claim for the capture tests.",
         "sources": SOURCE}
    if facts:
        c["facts"] = list(facts)
    if programs:
        c["programs"] = list(programs)
    return c


def make_lesson(prefix, programs, facts, claims=None):
    tmp = host.make_tmp(prefix)
    (tmp / "programs").mkdir()
    progs = []
    for p in programs:
        p = dict(p)
        if "_text" in p:
            (tmp / p["path"]).write_text(p.pop("_text"))
        else:
            shutil.copyfile(p.pop("_fixture"), tmp / p["path"])
        progs.append(p)
    claims = claims or [claim("c.x")]
    data = {
        "schema": "prax-teach/lesson@1", "id": "fixture", "title": "Capture fixture", "topic": "capture",
        "language": "c", "programs": progs, "facts": facts, "claims": claims, "misconceptions": [],
        "trace": [{"id": "s0", "label": "start", "state": {"program": progs[0]["id"], "line": 1, "output": []},
                   "reveals": []}],
        "storyboard": [{"id": "sc1", "title": "Start", "state": "s0",
                        "narration": [{"text": claims[0]["text"], "claims": [claims[0]["id"]]}]}],
        "requested_media": ["still"],
    }
    (tmp / "lesson.json").write_text(json.dumps(data, indent=2))
    return tmp


def cleanup(tmp):
    shutil.rmtree(tmp, ignore_errors=True)
