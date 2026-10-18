"""AC-3.1 and AC-3.5: the still projector's variants, sources and math."""
import copy
import re
import shutil
import xml.etree.ElementTree as ET

from _util import SLICE
from ptk import errors, fonts, host, model
from ptk.project import still
from ptk.verify import claims, values, visual

SVG_NS = "{http://www.w3.org/2000/svg}"
SOURCES = ("data-claim", "data-chrome", "data-fact", "data-code", "data-label")


def _png_size(p):
    head = p.read_bytes()[16:24]
    return int.from_bytes(head[:4], "big"), int.from_bytes(head[4:], "big")


def test_variants_and_sources():
    """Wide and portrait SVG plus 2x PNG in light and dark; every value from facts, every sentence from
    claims or chrome.json, every colour and family from tokens."""
    lesson = model.load(SLICE)
    tmp = host.make_tmp("still-variants-")
    try:
        out = tmp / "still"
        svgs = still.project(lesson, out)
        assert sorted(svgs) == sorted(f"{lesson.id}-{lay}-{th}.svg" for lay in ("wide", "portrait")
                                      for th in ("light", "dark")), svgs
        pngs, failed, outbound = visual.make_pngs(out, svgs, lesson.sha256())
        assert not failed and not outbound, (failed, outbound)
        tk = fonts.tokens()
        for s, p in zip(svgs, pngs):
            root = ET.parse(out / s).getroot()
            vb = [float(v) for v in root.get("viewBox").split()]
            w, h = _png_size(out / p)
            assert (w, h) == (round(vb[2] * 2), round(vb[3] * 2)), (s, (w, h), vb)
            theme = root.get("data-theme")
            assert root.find(f"{SVG_NS}rect").get("fill") == tk["themes"][theme]["ground"], s
            for el in root.iter(f"{SVG_NS}text"):
                assert any(el.get(a) is not None for a in SOURCES), (s, "".join(el.itertext()))
            facts = [el.get("data-fact") for el in root.iter() if el.get("data-fact")]
            final = lesson.state(lesson.data["figure"]["states"][-1])["state"]["output"]
            cmp = lesson.state(lesson.data["figure"]["compare"]["state"])["state"]["output"]
            assert facts == final + cmp, (s, facts)
            n, bad = values.check_svg(out / s, lesson)
            assert n and not bad, (s, bad)
        items = claims.collect_texts(lesson, tmp)
        gate = claims.mapping_gate(lesson, items)
        assert gate["status"] == "passed", gate["measured"]["unmapped"]
        src = (host.PKG / "ptk" / "project" / "still.py").read_text()
        assert not re.search(r"#[0-9a-fA-F]{6}\b", src), "still.py names a hex colour"
        assert not any(f["family"] in src for f in tk["fonts"].values()), "still.py names a font family"
        return {"svgs": len(svgs), "pngs": len(pngs), "texts_mapped": len(items)}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _math_lesson():
    """The slice lesson plus one caption claim holding an equation (a test fragment, not a shipped lesson)."""
    base = model.load(SLICE)
    data = copy.deepcopy(base.data)
    data["claims"].append({"id": "c.count", "kind": "framing",
                           "text": r"The program prints \(1 + 1 + 1 = 3\) lines, and \(\frac{3}{3} = 1\) of them is done.",
                           "justification": "test fragment", "sources": [{"title": "fallthrough.c", "url": "programs/fallthrough.c"}],
                           "facts": []})
    data["figure"]["caption_claims"] = list(data["figure"].get("caption_claims", [])) + ["c.count"]
    return model.Lesson(base.path, data)


def test_math_svg():
    """TeX in a claim renders through MathJax tex2svg into the SVG (glyph paths); no raw TeX is left in the output."""
    lesson = _math_lesson()
    tmp = host.make_tmp("still-math-")
    try:
        svgs = still.project(lesson, tmp)
        for s in svgs:
            body = (tmp / s).read_text()
            root = ET.fromstring(body)
            maths = [el for el in root.iter() if el.get("data-math") == "mathjax-tex2svg"]
            assert len(maths) == 2, (s, len(maths))
            for m in maths:
                assert m.get("data-claim") == "c.count" and m.get("data-tex-sha256"), s
                assert any(e.tag == f"{SVG_NS}path" for e in m.iter()), f"{s}: formula has no glyph paths"
                _x, _y, w, h = map(float, m.get("data-box").split())
                assert w > 10 and h > 8, s
            assert len(list(root.iter(f"{SVG_NS}svg"))) == 1, f"{s}: one root svg only"
            assert not re.search(r"\\[A-Za-z]+|\\\(|\\\)|\$", body), f"{s}: raw TeX left in the output"
            desc = root.find(f"{SVG_NS}desc").text
            assert "1 + 1 + 1 = 3" in desc and "(3)/(3) = 1" in desc, desc
        pngs, failed, outbound = visual.make_pngs(tmp, svgs, lesson.sha256())
        assert not failed and not outbound
        m, _ob = visual.measure_svgs(tmp, svgs, visual.required_keys(lesson), lesson.sha256())
        for s, r in m.items():
            assert "error" not in r, (s, r)
            math_c = [c for c in r["contrast"] if c.get("text") == "math"]
            assert len(math_c) == 2 and all(c["ratio"] >= 4.5 for c in math_c), (s, math_c)
            assert not [p for p in r["problems"] if p["kind"] in ("overflow", "min-size")], (s, r["problems"])
        try:
            still.render_math([r"\frac{1}{"])
        except errors.ModelSchemaError:
            pass
        else:
            raise AssertionError("bad TeX did not fail")
        try:
            still.tex_to_text(r"\weird{x}")
        except errors.ModelSchemaError:
            pass
        else:
            raise AssertionError("TeX with no alt-text reading did not fail")
        return {"svgs": len(svgs), "formulas_per_svg": 2}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
