"""Values in the still's alt text are checked against the facts (review P2-4)."""
import shutil

from _util import SLICE
from ptk import host, model
from ptk.project import still
from ptk.verify import values


def test_alt_output_sentence_is_value_checked():
    lesson = model.load(SLICE)
    tmp = host.make_tmp("alt-values-")
    try:
        name = still.project(lesson, tmp)[0]
        svg = tmp / name
        n, bad = values.check_svg(svg, lesson)
        assert not bad, bad
        src = svg.read_text()
        assert ": two, three, done." in src, "fixture changed: alt sentence not found"
        svg.write_text(src.replace(": two, three, done.", ": two, done."))
        _n, bad = values.check_svg(svg, lesson)
        assert any(b.get("where", "").endswith("<desc>") for b in bad), f"tampered alt text passed: {bad}"
        return {"values_checked": n}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_binary64_float_h_is_the_ieee_double():
    """The <float.h> expectation for a binary64 double agrees with this Python's float (an IEEE 754 double)."""
    import sys

    from ptk import expect
    fi = sys.float_info
    names = ("FLT_RADIX", "DBL_MANT_DIG", "DBL_MIN_EXP", "DBL_MAX_EXP")
    assert [expect.binary64_float_h(n) for n in names] == [str(v) for v in (fi.radix, fi.mant_dig, fi.min_exp,
                                                                              fi.max_exp)]
