#!/usr/bin/env python3
"""motion_fill.py: put the numbers from the clip's datasets into the narration, so a revised CSV changes what is
said as well as what is drawn.

script.template.json is script.json with references where numbers go, the same references film.json uses:
    {{speeds.fps:max}}           dataset.column:aggregate (sum avg min max first last count)
    {{speeds.fps[kit=gsap]}}     the column in the first row where kit is gsap
    {{speeds.fps:max|0.0}}       with a format (int, 0.0, pct, pct0.0, compact, x, money, money:X, time)
In `cap` a number is written with its format (default: whole numbers as is, else one decimal under 10 and
none above, like the blocks draw it). In `say` it is spelled out
in words for the voice ("ten thousand eight hundred", "zero point six"); `|digits` keeps digits there.
The datasets are the ones source/film.json lists under "data" (paths relative to source/). In a delivered
package, film.json sits beside script.json in deliver/source/, so run it there: --project deliver/source.

Usage:
  python3 motion_fill.py --project .            write script.json from script.template.json
  python3 motion_fill.py --project . --check    exit 1 if script.json is not what the template and data give
Then re-voice, so the timing follows the new words (it prints the command for the folder it ran in):
  in a project            python3 $S/voice.py --project . --emit source/timing.js   (only changed lines are re-spoken)
  in deliver/source/      python3 pipeline/voice.py --project . --emit timing.js
                          cp voice/narration.wav ../voice/narration.wav   (the page there plays ../voice/narration.wav)
"""
import argparse
import csv
import decimal
import json
import math
import os
import re
import shlex
import sys

REF = re.compile(r"\{\{\s*([A-Za-z0-9_-]+)\.([^:\[\]|}]+?)(?::(sum|avg|min|max|first|last|count)|\[([^=\]]+)=([^\]]+)\])?"
                 r"\s*(?:\|\s*([^}]+?))?\s*\}\}")
NUM = re.compile(r"^-?\d+(\.\d+)?([eE][+-]?\d+)?$")


def cell(x):
    if isinstance(x, (int, float)) and not isinstance(x, bool):  # JSON numbers, inline or from a .json file
        return float(x)
    if not isinstance(x, str):
        return x
    v = x.strip()
    if v and NUM.match(v.replace(",", "")):
        return float(v.replace(",", ""))
    return v


def load_sets(source):
    film_path = os.path.join(source, "film.json")
    with open(film_path, encoding="utf-8") as f:
        film = json.load(f)
    sets = {}
    for name, src in (film.get("data") or {}).items():
        if isinstance(src, list):
            sets[name] = [{k: cell(v) for k, v in r.items()} for r in src]
            continue
        # a relative path inside source/, with either slash (Windows), and still inside once links are resolved
        if not isinstance(src, str) or re.match(r"^[a-z]+:|^[/\\]", src, re.I) or re.search(r"(^|[/\\])\.\.([/\\]|$)", src):
            sys.exit(f"film.json data.{name}: give a relative path inside source/ or inline rows")
        base = os.path.realpath(source)
        p = os.path.realpath(os.path.join(base, *re.split(r"[/\\]", src)))
        try:
            inside = os.path.commonpath([base, p]) == base
        except ValueError:  # on Windows, a link to another drive shares no folder with source/
            inside = False
        if not inside:
            sys.exit(f"film.json data.{name}: {src} leads outside source/")
        with open(p, encoding="utf-8-sig", newline="") as f:  # -sig: a spreadsheet export's BOM, as the browser drops it
            if src.lower().endswith(".json"):  # by the name film.json gives, as the browser decides
                sets[name] = [{k: cell(v) for k, v in r.items()} for r in json.load(f)]
            else:
                sets[name] = [{k.strip(): cell(v) for k, v in row.items()} for row in csv.DictReader(f)]
    return sets


def value(sets, name, col, agg, key, want, where):
    if name not in sets:
        sys.exit(f"{where}: no dataset '{name}' (film.json data has: {', '.join(sets) or 'none'})")
    rows = sets[name]
    if rows and col not in rows[0]:
        sys.exit(f"{where}: dataset '{name}' has no column '{col}' (columns: {', '.join(rows[0])})")
    if key:
        for r in rows:
            if str(r.get(key.strip())).strip() == want.strip() or (isinstance(r.get(key.strip()), float) and cell(want) == r.get(key.strip())):
                return r[col]
        sys.exit(f"{where}: no row in '{name}' where {key} = {want}")
    if agg == "count":  # rows that have a value in the column, numbers or not (as the browser counts)
        return float(sum(1 for r in rows if r.get(col) not in ("", None)))
    vals = [r[col] for r in rows if isinstance(r.get(col), float)]
    if not vals:
        sys.exit(f"{where}: column '{col}' of '{name}' has no numbers")
    agg = agg or "last"
    return {"sum": sum(vals), "avg": sum(vals) / len(vals), "min": min(vals), "max": max(vals),
            "first": vals[0], "last": vals[-1], "count": float(len(vals))}[agg]


def js_round(v):
    """Math.round: halves go up (2.5 -> 3, -2.5 -> -2), where Python's round() goes to even."""
    f = math.floor(v)
    return int(f + 1 if v - f >= 0.5 else f)


def fixed(v, d):
    """toLocaleString with d decimals: halves go away from zero on the shortest decimal that reads back as the
    same double (0.35 -> 0.4, 1.005 -> 1.01), as ICU does in the browser."""
    q = decimal.Decimal(repr(v)).quantize(decimal.Decimal(1).scaleb(-d), rounding=decimal.ROUND_HALF_UP)
    return f"{q:,.{d}f}"


def fmt_num(v, fmt):
    """The same formats, and the same rounding, as M.fmtNum in engine/core.js."""
    if not isinstance(v, float):
        return str(v)
    dec = re.match(r"^(?:pct)?0\.(0+)$", fmt or "")
    if fmt == "int":
        return f"{js_round(v):,}"
    if dec and not fmt.startswith("pct"):
        return fixed(v, len(dec.group(1)))
    if fmt == "pct":
        return f"{js_round(v):,}%"
    if dec:
        return fixed(v, len(dec.group(1))) + "%"
    if fmt == "x":
        return fixed(v, 1 if v < 10 else 0) + "x"
    if fmt == "compact":
        a = abs(v)
        return (fixed(v / 1e9, 1) + "B" if a >= 1e9 else fixed(v / 1e6, 1) + "M" if a >= 1e6
                else fixed(v / 1e3, 1) + "k" if a >= 1e4 else f"{js_round(v):,}")
    # a negative amount or duration takes one sign in front: -$1,200 and -0:30 (not $-1,200 or -1:30)
    if fmt and fmt.startswith("money"):
        r = js_round(v)
        return ("-" if r < 0 else "") + (fmt.split(":", 1)[1] if ":" in fmt else "$") + f"{abs(r):,}"
    if fmt == "time":
        r = js_round(v)
        return ("-" if r < 0 else "") + f"{abs(r) // 60}:{abs(r) % 60:02d}"
    if v == int(v):
        return f"{int(v):,}"
    return fixed(v, 1 if abs(v) < 10 else 0)


ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
       "seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def int_words(n):
    if n < 0:
        return "minus " + int_words(-n)
    if n < 20:
        return ONES[n]
    if n < 100:
        return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    if n < 1000:
        return ONES[n // 100] + " hundred" + ("" if n % 100 == 0 else " " + int_words(n % 100))
    for size, word in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= size:
            return int_words(n // size) + " " + word + ("" if n % size == 0 else " " + int_words(n % size))
    return str(n)


def words(v, fmt):
    """A number as the voice should say it, after the same rounding the format applies."""
    if not isinstance(v, float):
        return str(v)
    if fmt == "time":  # 90 -> "one minute thirty seconds", as M:SS is read aloud
        m, s = divmod(abs(js_round(v)), 60)
        parts = [f"{int_words(m)} minute{'s' if m != 1 else ''}"] if m else []
        if s or not m:
            parts.append(f"{int_words(s)} second{'s' if s != 1 else ''}")
        return ("minus " if js_round(v) < 0 else "") + " ".join(parts)
    shown = fmt_num(v, fmt or "auto")
    suffix = ""
    if shown.endswith("%"):
        suffix, shown = " percent", shown[:-1]
    elif shown.endswith("x") and fmt == "x":
        suffix, shown = " times", shown[:-1]
    elif fmt and fmt.startswith("money"):
        sign, shown = ("-", shown[1:]) if shown.startswith("-") else ("", shown)
        shown = sign + shown[len(fmt.split(":", 1)[1] if ":" in fmt else "$"):]  # the whole prefix ($, ₹, USD)
        suffix = " dollars" if fmt == "money" else ""
    scale = ""
    if fmt == "compact" and shown[-1] in "kMB":
        scale = {"k": " thousand", "M": " million", "B": " billion"}[shown[-1]]
        shown = shown[:-1]
    s = shown.replace(",", "")
    neg = s.startswith("-")
    s = s.lstrip("-")
    whole, _, frac = s.partition(".")
    out = int_words(int(whole or 0))
    if frac:
        out += " point " + " ".join(ONES[int(d)] for d in frac)
    return ("minus " if neg else "") + out + scale + suffix


def fill(text, sets, where, spoken):
    def sub(m):
        name, col, agg, key, want, fmt = m.groups()
        v = value(sets, name, col.strip(), agg, key, want, where)
        if spoken and fmt != "digits":
            w = words(v, fmt)
            # a sentence this reference starts begins with a capital ("Ten kits."); the rest of the text is left alone
            return w[:1].upper() + w[1:] if re.search(r"(^|[.!?]\s+)$", m.string[:m.start()]) else w
        return fmt_num(v, "auto" if fmt in (None, "digits") else fmt)
    return REF.sub(sub, text)


def source_of(project):
    """the folder with film.json: <project>/source, or the project itself in a delivered package (deliver/source)"""
    s = os.path.join(project, "source")
    return project if not os.path.isfile(os.path.join(s, "film.json")) and os.path.isfile(os.path.join(project, "film.json")) else s


def build(project, template):
    with open(template, encoding="utf-8") as f:
        sc = json.load(f)
    sets = load_sets(source_of(project))
    for ln in sc.get("lines", []):
        for k in ("cap", "say"):
            if isinstance(ln.get(k), str):
                ln[k] = fill(ln[k], sets, f"script line {ln.get('id')} {k}", spoken=(k == "say"))
                if "{{" in ln[k]:
                    sys.exit(f"script line {ln.get('id')} {k}: a reference was not understood: {ln[k]}")
    return sc


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--project", default=".")
    ap.add_argument("--template", default="script.template.json")
    ap.add_argument("--out", default="script.json")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    root = os.path.abspath(a.project)
    tpl = os.path.join(root, a.template)
    if not os.path.exists(tpl):
        sys.exit(f"{a.template} not found: copy script.json to it and put {{{{set.col:agg}}}} where numbers go")
    sc = build(root, tpl)
    text = json.dumps(sc, ensure_ascii=False, indent=1) + "\n"
    out = os.path.join(root, a.out)
    if a.check:
        try:
            cur = json.load(open(out, encoding="utf-8"))
        except (OSError, ValueError):
            cur = None
        if cur != sc:
            print(f"{a.out} is stale: the template or the data changed. Run motion_fill.py, then voice.py.")
            sys.exit(1)
        print(f"{a.out} matches the template and the data")
        return
    with open(out, "w", encoding="utf-8") as f:
        f.write(text)
    n = sum(len(REF.findall(json.dumps(ln))) for ln in json.load(open(tpl, encoding="utf-8")).get("lines", []))
    print(f"wrote {a.out}: {n} references filled from {', '.join(load_sets(source_of(root)))}")
    # what to run next where it ran: in a delivered package (deliver/source/) voice.py is in pipeline/, the page's
    # timing.js is beside film.json, and the page plays the narration one folder up
    src = source_of(root)
    voice = os.path.join(os.path.dirname(os.path.abspath(__file__)), "voice.py")
    def q(x, start=os.curdir):
        try:
            return shlex.quote(os.path.relpath(x, start))
        except ValueError:  # on Windows, a path on another drive has no relative form
            return shlex.quote(os.path.abspath(x))
    print(f"next, re-voice: python3 {q(voice)} --project {q(root)} --emit {q(os.path.join(src, 'timing.js'), root)}")
    if src == root:
        print(f"then, for the preview: cp {q(os.path.join(root, 'voice', 'narration.wav'))} "
              f"{q(os.path.join(root, '..', 'voice', 'narration.wav'))}")


if __name__ == "__main__":
    main()
