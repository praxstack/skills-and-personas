"""Independent expectations: pure functions that compute what a fact should be.

This module imports nothing from ptk, so capture code can never feed it (AC-2.8, D17.5;
tests/test_lint.py::test_expect_independent). A fact's `expect` is either
{"fn": name, "args": [...]} naming a function here, or {"value": ..., "reviewed": true}.
Every function returns a str, because facts store displayed text. Each computes the answer
from the C rules directly (two's complement widths, printf conversions, switch semantics),
never by running or parsing a program.
"""


def bits(value, width=8):
    v = int(value) & ((1 << int(width)) - 1)
    return format(v, f"0{int(width)}b")


def hex_(value, width=2):
    return "0x" + format(int(value) & ((1 << (4 * int(width))) - 1), f"0{int(width)}X")


def printf_d(value):
    return str(int(value))


def printf_u(value, width_bits=32):
    return str(int(value) & ((1 << int(width_bits)) - 1))


def printf_x(value, width_bits=32):
    """%x of an unsigned value of the given width: lower-case hex, no prefix."""
    return format(int(value) & ((1 << int(width_bits)) - 1), "x")


def printf_f(value, precision=6):
    return f"{float(value):.{int(precision)}f}"


def printf_c(value):
    return chr(int(value) & 0xFF)


def ascii_(code):
    c = int(code)
    if c < 32 or c == 127:
        return f"non-printable (code {c})"
    return chr(c)


def sizeof_from_platform(platform, ctype):
    return str(platform["sizeof"][ctype])


def sum_(values):
    return str(sum(int(v) for v in values))


def factorial(n):
    out = 1
    for k in range(2, int(n) + 1):
        out *= k
    return str(out)


def factorial_frames(n):
    """Call-stack frames for factorial(n), outermost first, as 'factorial(k)'."""
    return ",".join(f"factorial({k})" for k in range(int(n), 0, -1))


# ---- switch statement semantics (C17 6.8.4.2, 6.8.1, 6.8.6.4) ----
#
# cases: [{"label": int | "default", "out": [str, ...], "brk": bool}, ...] in source order.
# Control jumps to the matching case label (or default, or past the body), then runs
# every following statement in order. Labels do not stop it; only `break` (brk=True)
# or the end of the body leaves the switch. `tail` is what the program prints after.

def switch_output(cases, n, tail=()):
    start = next((i for i, c in enumerate(cases) if c["label"] == n), None)
    if start is None:
        start = next((i for i, c in enumerate(cases) if c["label"] == "default"), None)
    out = []
    if start is not None:
        for c in cases[start:]:
            out.extend(c["out"])
            if c["brk"]:
                break
    return out + list(tail)


def switch_line(cases, n, tail, line):
    """The 1-based line `line` of the program's stdout."""
    return switch_output(cases, n, tail)[int(line) - 1]


def switch_stdout(cases, n, tail):
    return "".join(s + "\n" for s in switch_output(cases, n, tail))


FUNCTIONS = {
    "bits": bits, "hex": hex_, "printf_d": printf_d, "printf_u": printf_u, "printf_f": printf_f,
    "printf_x": printf_x, "printf_c": printf_c, "ascii": ascii_, "sizeof_from_platform": sizeof_from_platform,
    "sum": sum_, "factorial": factorial, "factorial_frames": factorial_frames, "switch_line": switch_line,
    "switch_stdout": switch_stdout,
}
# Functions that take the captured platform as their first argument; `args` omits it.
PLATFORM_FUNCTIONS = {"sizeof_from_platform"}


def evaluate(expect, platform=None):
    """Return the expected display string for one fact's `expect` block."""
    if "fn" not in expect:
        return expect["value"]
    fn = FUNCTIONS.get(expect["fn"])
    if fn is None:
        raise KeyError(f"unknown expect function {expect['fn']!r}")
    args = list(expect["args"])
    if expect["fn"] in PLATFORM_FUNCTIONS:
        args = [platform or {}, *args]
    return fn(*args)
