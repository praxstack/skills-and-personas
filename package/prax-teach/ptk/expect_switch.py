"""Independent expectation for the switch explorer's path (WP4, AC-4.2).

expect.py gives the printed lines (switch_output). The explorer also shows *how* control moves:
where it enters, which cases run, and why the switch ends. This module computes that from the
C rules alone, with the same `cases` shape as expect.py:

    cases: [{"label": int | "default", "out": [str, ...], "brk": bool}, ...] in source order

    C17 6.8.4.2p5   jump to the matching label, else to default, else skip the whole body
    C17 6.8.1p4     a label does not stop control, so the next case runs too
    C17 6.8.6.3p2   break ends the switch
    end of body     the switch is complete; control goes on after it

It imports nothing (not ptk, not capture), like expect.py, so neither the explorer's own
script nor a captured run can feed it.
"""


def switch_trace(cases, n):
    """{"enter": label | None, "ran": [labels in order], "exit": "break" | "end" | "nomatch",
    "output": [lines printed by the switch body]}"""
    start = next((i for i, c in enumerate(cases) if c["label"] == n), None)
    if start is None:
        start = next((i for i, c in enumerate(cases) if c["label"] == "default"), None)
    if start is None:
        return {"enter": None, "ran": [], "exit": "nomatch", "output": []}
    ran, out, ended = [], [], "end"
    for c in cases[start:]:
        ran.append(c["label"])
        out.extend(c["out"])
        if c["brk"]:
            ended = "break"
            break
    return {"enter": cases[start]["label"], "ran": ran, "exit": ended, "output": out}


def falls(cases, n):
    """[(from_label, into_label)] for every case boundary crossed without a break."""
    ran = switch_trace(cases, n)["ran"]
    return list(zip(ran, ran[1:]))
