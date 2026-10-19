"""Execution-path geometry shared by the still, the video and the IVE (review P2-7, P3-7).

Everything here is in source-line units, so each projector maps lines to its own y and the
still and the video draw the same picture:

    executed lines   4 5 8 9 10 11 12 16
    segments         4-5 run, 5-8 jump, 8-9 run, 9-10 run, 10-11 run, 11-12 run, 12-16 jump
    tags             8 "enters here" (landing of the first jump onto a case label)
                     6, 13 "skipped" (case labels between the first and last executed line)
                     12 "leaves the switch" (the executed `break;`)
    badge            "no break" between 9 and 10 (a run straight into a case label)
"""
import re


def body_range(src_lines):
    """1-based (first, last) of main's body: the line after `main(` through `return`."""
    main = next((i for i, ln in enumerate(src_lines) if "main(" in ln), 0)
    last = next((i + 1 for i, ln in enumerate(src_lines) if ln.strip().startswith("return")), len(src_lines))
    return main + 2, last


def executed(paths):
    """Union of several paths, in first-seen order."""
    out = []
    for p in paths:
        for n in p:
            if n not in out:
                out.append(n)
    return out


def segments(run):
    """[(a, b, 'run' | 'jump')] between consecutive executed lines."""
    return [(a, b, "run" if b == a + 1 else "jump") for a, b in zip(run, run[1:])]


def jump_lanes(run):
    """{(a, b): (side, lane)} for every jump of a run, so the arcs never cross (B5: a recursive path's calls, returns
    and skips tangled on one shared bulge). A jump spans the lines between its ends. Jumps go on the left of the rail,
    each one lane further out than every jump nested inside it; a jump that partly overlaps a left jump (neither
    holds the other) goes on the right, laned the same way. side is -1 (left) or 1 (right); lane counts from 1."""
    spans = sorted({(min(a, b), max(a, b)) for a, b, k in segments(run) if k == "jump"}, key=lambda s: (s[1] - s[0], s))
    cross = lambda p, q: p[0] < q[0] < p[1] < q[1] or q[0] < p[0] < q[1] < p[1]  # noqa: E731
    inside = lambda p, q: q[0] <= p[0] and p[1] <= q[1] and p != q  # p nested in q  # noqa: E731
    placed = {}
    for sp in spans:
        side = -1 if not any(cross(sp, o) for o, (sd, _l) in placed.items() if sd == -1) else 1
        lane = 1 + max([ln for o, (sd, ln) in placed.items() if sd == side and inside(o, sp)] + [0])
        placed[sp] = (side, lane)
    return {(a, b): placed[(min(a, b), max(a, b))] for a, b, k in segments(run) if k == "jump"}


def nobreak_after(src_lines, run):
    """The executed line after which execution runs straight into a case label, or None."""
    for a, b, kind in segments(run):
        if kind == "run" and src_lines[b - 1].strip().startswith("case"):
            return a
    return None


def break_line(src_lines, run):
    return next((n for n in run if src_lines[n - 1].strip() == "break;"), None)


def enter_line(src_lines, run):
    """Landing line of the first jump that lands on a case label."""
    return next((b for a, b, kind in segments(run) if kind == "jump" and src_lines[b - 1].strip().startswith("case")),
                None)


def skipped_cases(src_lines, run, shown):
    return [n for n in shown if n not in run and min(run) < n < max(run) and src_lines[n - 1].strip().startswith("case")]


def tags(src_lines, run, shown):
    """[(line, chrome key, tone)] for one executed run; tone is 'path' or 'muted'."""
    out = []
    enter = enter_line(src_lines, run)
    if enter:
        out.append((enter, "enter_label", "path"))
    brk = break_line(src_lines, run)
    if brk:
        out.append((brk, "exit_label", "path"))
    out += [(n, "skipped_label", "muted") for n in skipped_cases(src_lines, run, shown)]
    return out


def listing(lesson, pid):
    """1-based (first, last) lines a listing of program `pid` shows: the program's `show` range, else
    main's body (a program with a function before main sets `show` to include it)."""
    prog = lesson.program(pid)
    if prog.get("show"):
        return prog["show"]["from"], prog["show"]["to"]
    return body_range(lesson.program_source(pid).split("\n"))


PRINT_CALL = re.compile(r'\b(puts|printf)\s*\(\s*"((?:[^"\\]|\\.)*)"')
CONV = re.compile(r"%([-+ #0]*)(\d*)(?:\.(\d+))?(hh|h|ll|l|z|j|t|L)?([diuxXfFeEgGcs%])")


def format_regex(src_line):
    """The output a printf/puts call on this line can print, as a regex (None for any other line)."""
    m = PRINT_CALL.search(src_line)
    if not m:
        return None
    fmt = bytes(m.group(2), "utf-8").decode("unicode_escape").rstrip("\n")
    if m.group(1) == "puts":
        return re.compile(re.escape(fmt))
    out, pos = "", 0
    for c in CONV.finditer(fmt):
        out += re.escape(fmt[pos:c.start()])
        conv = c.group(5)
        out += {"d": r"[-+ ]?\d+", "i": r"[-+ ]?\d+", "u": r"\d+", "x": r"(?:0x)?[0-9a-f]+", "X": r"(?:0X)?[0-9A-F]+",
                "c": r".", "s": r".*", "%": "%"}.get(conv, r"[-+ ]?[\d.]+(?:[eE][-+]?\d+)?")
        pos = c.end()
    return re.compile(out + re.escape(fmt[pos:]))


def print_lines(src_lines, path, outputs):
    """The source line that printed each output text (D20.5: each summary value paired with the step that
    printed it). One print call per output, in path order, maps one to one; a call that runs several
    times (a loop, a recursive function) is found by matching each output against the format strings
    on the path, and must match exactly one. None when an output cannot be paired."""
    calls = [n for n in executed([path]) if format_regex(src_lines[n - 1])]
    if len(calls) == len(outputs):
        return calls
    out = []
    for text in outputs:
        hits = [n for n in calls if format_regex(src_lines[n - 1]).fullmatch(text)]
        if len(hits) != 1:
            return None
        out.append(hits[0])
    return out
