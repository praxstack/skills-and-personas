"""Independent expectations for the neuron explorer's sliders (round 18).

The page only looks values up; this module computes them. It reproduces programs/neuron.c in IEEE 754
binary64 (C17 Annex F) in the program's own order of operations, and prints like its printf calls:

    t1 = x1 * w1;  t2 = x2 * w2;  z = t1 + t2 + b  (left to right);  a = fmax(0.0, z)
    terms  %+g      bias  %+g      z, a  %g (6 significant digits, trailing zeros removed)

It imports nothing from ptk, like expect.py, so neither the page script nor a captured run can feed it.
The lesson's `figure.explore.checks` name variant programs that were compiled and run at a few slider
points; ptk/project/stepper.py compares their captured lines with `lines()` here.
"""


def g(v, sign=False):
    """printf("%g") / ("%+g") of a double; -0.0 prints as -0 in C and here."""
    return f"{float(v):{'+' if sign else ''}g}"


def steps(lo, hi, step):
    """The slider's values: lo, lo + step, ... hi, each the double nearest its decimal (what a C literal
    with that decimal gives), so 0.1 steps never accumulate error."""
    n = int(round((hi - lo) / step))
    digits = max(0, -int(f"{step:e}".split("e")[1]))
    return [float(f"{lo + k * step:.{digits}f}") for k in range(n + 1)]


def point(x1, w1, x2, w2, b):
    t1 = float(x1) * float(w1)
    t2 = float(x2) * float(w2)
    z = t1 + t2
    z = z + float(b)
    a = z if z > 0.0 else 0.0  # fmax(0.0, z): z for z > 0, else 0.0 (for z == 0 both are 0)
    return {"t1": t1, "t2": t2, "z": z, "a": a}


def shown(x1, w1, x2, w2, b):
    """The strings the program would print at this point, and the doubles behind them."""
    p = point(x1, w1, x2, w2, b)
    return {"w2": g(w2), "b": g(b, True), "t1": g(p["t1"], True), "t2": g(p["t2"], True), "z": g(p["z"]),
            "a": g(p["a"]), "num": p}


def lines(x1, w1, x2, w2, b):
    """The four stdout lines of neuron.c at this point."""
    s = shown(x1, w1, x2, w2, b)
    return [f"{g(x1)} * {g(w1)} = {s['t1']}", f"{g(x2)} * {g(w2)} = {s['t2']}", f"b = {s['b']}  z = {s['z']}",
            f"a = {s['a']}"]


def grid(x1, w1, x2, sliders):
    """{"w2": [...], "b": [...], "rows": {"<w2>|<b>": shown}} over the two sliders."""
    ws = steps(sliders["w2"]["min"], sliders["w2"]["max"], sliders["w2"]["step"])
    bs = steps(sliders["b"]["min"], sliders["b"]["max"], sliders["b"]["step"])
    rows = {}
    for w2 in ws:
        for b in bs:
            s = shown(x1, w1, x2, w2, b)
            rows[f"{g(w2)}|{g(b)}"] = {k: v for k, v in s.items() if k != "num"} | {
                "zf": s["num"]["z"], "af": s["num"]["a"], "t2f": s["num"]["t2"], "t1f": s["num"]["t1"]}
    return {"w2": [g(w) for w in ws], "b": [g(b) for b in bs], "rows": rows}
