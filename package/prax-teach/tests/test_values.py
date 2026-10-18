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
