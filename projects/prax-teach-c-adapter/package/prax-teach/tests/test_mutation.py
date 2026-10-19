"""AC-3.7: every value mutation applied to a still fails verify/values.py; the clean still passes.

The still value mutations (D17.5): swap a value for another fact's value, misspell one, reorder two
output lines, drop one, duplicate one, unmark one (drop its data-fact), relabel one with another
program's fact that has the same text, change the comparison's value, change the alt text's values,
renumber a code line, and edit a code line.
"""
import re
import shutil

from _util import SLICE
from ptk import host, model
from ptk.project import still
from ptk.verify import values


def _value_el(src, fid):
    m = re.search(rf'<text [^>]*data-fact="{re.escape(fid)}"[^>]*>[^<]*</text>', src)
    assert m, f"no element for {fid}"
    return m


def still_value_mutations(src, lesson):
    """[(name, mutated svg text)] for one still variant."""
    fig = lesson.data["figure"]
    final = lesson.state(fig["states"][-1])["state"]["output"]
    cmp = lesson.state(fig["compare"]["state"])["state"]["output"]
    facts = lesson.by_id("facts")
    v = lambda fid: facts[fid]["value"]
    a, b = _value_el(src, final[0]), _value_el(src, final[1])
    out = []
    out.append(("swap-value", src.replace(f'>{v(final[0])}</text>', f'>{v(final[1])}</text>', 1)))
    out.append(("misspell", src[:b.start()] + b.group(0).replace(f">{v(final[1])}<", f">{v(final[1])[:-1]}<")
                + src[b.end():]))
    out.append(("reorder", src[:a.start()] + b.group(0).replace(re.search(r' y="[^"]+"', b.group(0)).group(0),
                                                                   re.search(r' y="[^"]+"', a.group(0)).group(0))
                + src[a.end():b.start()] + a.group(0).replace(re.search(r' y="[^"]+"', a.group(0)).group(0),
                                                              re.search(r' y="[^"]+"', b.group(0)).group(0))
                + src[b.end():]))
    out.append(("drop", src[:b.start()] + src[b.end():]))
    out.append(("duplicate", src[:b.end()] + b.group(0) + src[b.end():]))
    out.append(("unmark", src[:b.start()] + b.group(0).replace(f' data-fact="{final[1]}"', ' data-label="value"')
                + src[b.end():]))
    twin = next(f for f in cmp if v(f) == v(final[0]))
    out.append(("relabel-same-text", src[:a.start()] + a.group(0).replace(f'data-fact="{final[0]}"',
                                                                         f'data-fact="{twin}"') + src[a.end():]))
    c = _value_el(src, cmp[-1])
    out.append(("compare-value", src[:c.start()] + c.group(0).replace(f">{v(cmp[-1])}<", f">{v(final[1])}<")
                + src[c.end():]))
    shown = ", ".join(v(f) for f in final)
    out.append(("alt-text", src.replace(f": {shown}.", f": {', '.join(v(f) for f in cmp)}.", 1)))
    n = re.search(r'(<text [^>]*data-label="line-number"[^>]*data-line="12"[^>]*>)12<', src)
    out.append(("renumber-line", src[:n.start()] + n.group(1) + "13<" + src[n.end():]))
    code = re.search(r'(<text [^>]*data-code="p1"[^>]*data-src-line="9"[^>]*>)(.*?)</text>', src)
    out.append(("edit-code", src[:code.start(2)] + code.group(2).replace("two", "one") + src[code.end(2):]))
    return out


def test_still_value_mutations():
    lesson = model.load(SLICE)
    tmp = host.make_tmp("still-mutations-")
    try:
        svgs = still.project(lesson, tmp)
        rows, missed = [], []
        for s in svgs:
            path = tmp / s
            clean = path.read_text()
            n, bad = values.check_svg(path, lesson)
            assert n and not bad, f"clean control {s} failed: {bad}"
            for name, body in still_value_mutations(clean, lesson):
                assert body != clean, f"mutation {name} did not change {s}"
                mpath = tmp / f"mut-{name}-{s}"
                mpath.write_text(body)
                _n, bad = values.check_svg(mpath, lesson)
                rows.append({"svg": s, "mutation": name, "caught": bool(bad)})
                if not bad:
                    missed.append((s, name))
        assert not missed, f"value mutations not caught: {missed}"
        return {"mutations": len(rows), "caught": sum(r["caught"] for r in rows), "controls_clean": len(svgs)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
