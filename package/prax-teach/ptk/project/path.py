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
