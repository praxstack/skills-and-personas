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


def test_object_byte_is_the_memory_layout():
    """AC-10.2 (one-byte): object_byte gives each byte of an int or a double's object representation (C17 6.2.6.1p4,
    memcpy into unsigned char[n]) in the declared byte order, computed with struct, not read from a capture. The
    bytes rebuild the value: an int's two's-complement bits and the double's binary64 bits (double_bits_hex)."""
    from ptk import expect
    a = [expect.object_byte("int", 66, k, "little") for k in range(4)]
    assert a == ["42", "00", "00", "00"], a
    assert [expect.object_byte("int", 66, k, "big") for k in range(4)] == ["00", "00", "00", "42"]
    assert [expect.object_byte("int", -1, k, "little") for k in range(4)] == ["ff"] * 4
    assert [expect.object_byte("int", 321, k, "little") for k in range(2)] == ["41", "01"]
    d = [expect.object_byte("double", 66, k, "little") for k in range(8)]
    assert d == ["00", "00", "00", "00", "00", "80", "50", "40"], d
    assert "0x" + "".join(reversed(d)).lstrip("0") == expect.double_bits_hex(66)
    for bad in (("int", 66, 4, "little"), ("double", 66, 8, "little"), ("long", 66, 0, "little"), ("int", 66, 0, "middle")):
        try:
            expect.object_byte(*bad)
        except (ValueError, KeyError):
            continue
        raise AssertionError(f"object_byte{bad} did not fail")
    return {"int": a, "double": d}
