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


# Declared target ABIs (review WP2 P2-5). A sizeof expectation names the data model the lesson's
# claims assume; capture's probe is compared against this table, never against itself.
# LP64: macOS and Linux on arm64/x86_64. LLP64: 64-bit Windows. ILP32: 32-bit targets.
TARGET_ABI = {
    "LP64": {"char": 1, "short": 2, "int": 4, "long": 8, "long long": 8, "float": 4, "double": 8, "void*": 8},
    "LLP64": {"char": 1, "short": 2, "int": 4, "long": 4, "long long": 8, "float": 4, "double": 8, "void*": 8},
    "ILP32": {"char": 1, "short": 2, "int": 4, "long": 4, "long long": 8, "float": 4, "double": 8, "void*": 4},
}


def sizeof_abi(ctype, abi="LP64"):
    """sizeof(ctype) on the declared data model, as printf("%zu") shows it."""
    return str(TARGET_ABI[abi][ctype])


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


def double_bits_hex(value):
    """The object representation of (double)value as printf("%#llx") shows it after a memcpy into an
    unsigned long long: IEEE 754 binary64 (C17 Annex F), so 66 becomes 0x4050800000000000."""
    import struct
    return "0x" + format(struct.unpack(">Q", struct.pack(">d", float(value)))[0], "x")


OBJECT_FORMATS = {"int": ("i", 4), "double": ("d", 8)}  # 32-bit two's complement int; IEEE 754 binary64 double


def object_byte(ctype, value, offset, order):
    """printf("%02x") of byte `offset` (0 = the lowest address) of the object representation of `value` stored in
    a `ctype` object (C17 6.2.6.1p4: the bytes memcpy copies into unsigned char[n]), in the declared byte order
    `order` ("little": least significant byte first). int is 32-bit two's complement, double is binary64."""
    import struct
    fmt, size = OBJECT_FORMATS[ctype]
    if order not in ("little", "big"):
        raise ValueError(f"byte order {order!r} is not little or big")
    if not 0 <= int(offset) < size:
        raise ValueError(f"offset {offset} is outside a {size}-byte {ctype}")
    raw = struct.pack(("<" if order == "little" else ">") + fmt, int(value) if ctype == "int" else float(value))
    return format(raw[int(offset)], "02x")


def call_label(fn, arg):
    """How a call is written: call_label("factorial", 2) -> "factorial(2)"."""
    return f"{fn}({int(arg)})"


# ---- recursion: the lines an instrumented factorial(n) prints (C17 6.5.2.2p11: recursive calls)
#
#   int factorial(int n) { printf("enter factorial(%d)\n", n); int r = 1; if (n > 1) r = n * factorial(n - 1);
#                          printf("factorial(%d) = %d\n", n, r); return r; }
#   main: int r = factorial(n); printf("main got %d\n", r);
#
# Each call prints on entry, finishes its own callee first, then prints its result: the entries come out
# in the order n, n-1, ..., 1 and the results in the reverse order, then main prints what it got.

def factorial_events(n):
    out = []

    def call(k):
        out.append(f"enter factorial({k})")
        r = 1
        if k > 1:
            r = k * call(k - 1)
        out.append(f"factorial({k}) = {r}")
        return r
    out.append(f"main got {call(int(n))}")
    return out


def factorial_event(n, line):
    """The 1-based line `line` of the instrumented run's stdout."""
    return factorial_events(n)[int(line) - 1]


def factorial_stdout(n):
    return "".join(s + "\n" for s in factorial_events(n))


# ---- one artificial neuron in C doubles (IEEE 754 binary64, in the C program's own order of operations)

def printf_g(value, sign=False):
    """printf("%g") of a double, or "%+g" with sign: 6 significant digits, trailing zeros removed."""
    return f"{float(value):{'+' if sign else ''}g}"


def _neuron_z(xs, ws, b):
    t = [float(x) * float(w) for x, w in zip(xs, ws)]
    z = t[0]
    for v in t[1:]:
        z = z + v
    return z + float(b)


def neuron_term(x, w):
    """printf("%+g", x * w)."""
    return printf_g(float(x) * float(w), sign=True)


def neuron_term_line(x, w):
    """printf("%g * %g = %+g\\n", x, w, x * w) without the newline."""
    return f"{printf_g(x)} * {printf_g(w)} = {neuron_term(x, w)}"


def neuron_sum_line(xs, ws, b):
    """printf("b = %+g  z = %g\\n", b, z) without the newline."""
    return f"b = {printf_g(b, sign=True)}  z = {neuron_sum(xs, ws, b)}"


def neuron_relu_line(xs, ws, b):
    """printf("a = %g\\n", fmax(0.0, z)) without the newline."""
    return f"a = {neuron_relu(xs, ws, b)}"


def neuron_sum(xs, ws, b):
    """printf("%g", t1 + t2 + ... + b) with t_i = x_i * w_i, added left to right as C does."""
    return printf_g(_neuron_z(xs, ws, b))


def neuron_relu(xs, ws, b):
    """printf("%g", fmax(0.0, z)): ReLU of the weighted sum."""
    z = _neuron_z(xs, ws, b)
    return printf_g(z if z > 0.0 else 0.0)


# ---- the double format a lesson's claims assume ----
#
# The <float.h> values of an IEC 60559 binary64 double (C17 5.2.4.2.2 EXAMPLE 2). A lesson that says
# "double is binary64 on this machine" expects these; a platform with another double format fails capture.
BINARY64_FLOAT_H = {"FLT_RADIX": 2, "DBL_MANT_DIG": 53, "DBL_MIN_EXP": -1021, "DBL_MAX_EXP": 1024}


def binary64_float_h(name):
    """printf("%d", <name>) on a platform whose double is IEC 60559 binary64."""
    return str(BINARY64_FLOAT_H[name])


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
    "printf_x": printf_x, "printf_c": printf_c, "ascii": ascii_, "sizeof_abi": sizeof_abi,
    "sum": sum_, "factorial": factorial, "factorial_frames": factorial_frames, "switch_line": switch_line,
    "switch_stdout": switch_stdout, "double_bits_hex": double_bits_hex, "call_label": call_label,
    "factorial_event": factorial_event, "factorial_stdout": factorial_stdout, "printf_g": printf_g,
    "neuron_term": neuron_term, "neuron_sum": neuron_sum, "neuron_relu": neuron_relu,
    "neuron_term_line": neuron_term_line, "neuron_sum_line": neuron_sum_line, "neuron_relu_line": neuron_relu_line,
    "binary64_float_h": binary64_float_h, "object_byte": object_byte,
}
# Functions that take the captured platform as their first argument; `args` omits it. Empty on
# purpose: an expectation read from the capture can never disagree with it (review WP2 P2-5).
PLATFORM_FUNCTIONS = set()


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
