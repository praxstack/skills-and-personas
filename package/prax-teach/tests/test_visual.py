"""AC-3.2, AC-3.3, AC-3.4, AC-3.6: the still's visual gates, each with a fixture that must fail."""
import copy
import re
import shutil

from _util import SLICE
from ptk import errors, fonts, host, model
from ptk.project import still
from ptk.verify import visual


def _build(tmp, tokens=None):
    lesson = model.load(SLICE)
    out = tmp / "still"
    svgs = still.project(lesson, out, tokens=tokens)
    return lesson, out, svgs


def _ocr(out, svgs, work):
    jobs = [{"id": f"ocr:{s}", "type": "ocr-crops", "url": (out / s).resolve().as_uri(),
             "width": 1200 if "-wide-" in s else 400, "height": 3000, "scale": 3,
             "outDir": str(work / s.replace(".svg", ""))} for s in svgs]
    res = visual.shoot(jobs, work)
    crops = []
    for r in res["results"]:
        assert r["ok"], r.get("error")
        s = r["id"].split(":", 1)[1]
        crops += [{**c, "dark": "-dark" in s} for c in r["crops"]]
    return visual.ocr_crops(crops)


def _digits_svg(numeric, features):
    """A one-line figure of the ten digits in the bundled serif, with the given numeral style."""
    t = fonts.tokens()["themes"]["light"]
    css = fonts.face_css({"serif": "0123456789"})
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 80" width="400" height="80">'
            f'<defs><style>{css}text{{font-variant-numeric:{numeric};font-feature-settings:{features}}}</style></defs>'
            f'<rect id="frame-bg" width="400" height="80" fill="{t["ground"]}"/>'
            f'<text x="20" y="52" font-family="{fonts.FAMILY["serif"]}" font-size="30" fill="{t["ink"]}" '
            f'letter-spacing="8" data-label="digits" data-ocr="0123456789">0123456789</text></svg>')


def test_ocr_lining_digits():
    """Tesseract reads every value and number cell of every variant, and every digit cell passes the lining
    geometry check. An old-style-numeral fixture fails; the same figure with lining numerals passes."""
    tmp = host.make_tmp("visual-ocr-")
    try:
        lesson, out, svgs = _build(tmp)
        cells = _ocr(out, svgs, tmp / "ocr")
        bad = [c for c in cells if not c["ok"]]
        assert cells and not bad, bad
        digit_cells = [c for c in cells if c["lining"]]
        assert len(digit_cells) >= 4 * 2, f"too few digit cells checked: {len(digit_cells)}"
        fx = tmp / "fixture"
        fx.mkdir()
        (fx / "oldstyle.svg").write_text(_digits_svg("oldstyle-nums proportional-nums", "'onum' 1"))
        (fx / "lining.svg").write_text(_digits_svg("lining-nums tabular-nums", "'lnum' 1,'tnum' 1"))
        got = {c["crop"].split("/")[0]: c for c in _ocr(fx, ["oldstyle.svg", "lining.svg"], tmp / "ocr-fx")}
        assert got["lining"]["ok"], got["lining"]
        assert not got["oldstyle"]["ok"], f"old-style numerals passed: {got['oldstyle']}"
        assert not got["oldstyle"]["lining"]["ok"], got["oldstyle"]
        m, _ob = visual.measure_svgs(fx, ["oldstyle.svg"], [])
        assert any(p["kind"] == "numeric" for p in m["oldstyle.svg"]["problems"]), "numeric style not flagged"
        return {"cells": len(cells), "digit_cells": len(digit_cells), "oldstyle": got["oldstyle"]["lining"]["bad"][:3]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_contrast():
    """Every declared role pair in both themes meets 4.5 (text) or 3 (rules); note vs correction differ by
    >= 15 L* (V12 asks it of dark; light keeps it too); the rendered stills agree. Atlas's own rule colour as a label, and its salmon as the
    correction colour, each fail."""
    rows, seps = visual.token_contrast()
    assert rows and all(r["ok"] for r in rows), [r for r in rows if not r["ok"]]
    assert {r["theme"] for r in rows} == {"light", "dark"}
    assert seps and all(s["ok"] for s in seps), seps
    tmp = host.make_tmp("visual-contrast-")
    try:
        lesson, out, svgs = _build(tmp)
        m, _ob = visual.measure_svgs(out, svgs, visual.required_keys(lesson))
        for s, r in m.items():
            low = [c for c in r["contrast"] if c["ratio"] < c["min"]]
            assert r["contrast"] and not low, (s, low)
        dls = {s: min(abs(a - b) for a in r["tones"]["note"] for b in r["tones"]["correction"]) for s, r in m.items()}
        assert min(dls.values()) >= 15, dls
        dl = min(d for s, d in dls.items() if "-dark" in s)
        # fixture 1: a label colour too close to the ground
        tk = copy.deepcopy(fonts.tokens())
        tk["themes"]["dark"]["label"] = "#3d4b62"
        rows_bad, _ = visual.token_contrast(tk)
        assert any(not r["ok"] and r["fg"] == "label" for r in rows_bad)
        bad_dir = tmp / "bad"
        _l, out2, svgs2 = _build(bad_dir, tokens=tk)
        dark2 = [s for s in svgs2 if "-dark" in s]
        m2, _ob = visual.measure_svgs(out2, dark2, [])
        assert all(any(c["ratio"] < c["min"] for c in m2[s]["contrast"]) for s in dark2), "low label contrast passed"
        # fixture 2: lavender and salmon at the same lightness (the Atlas pair as-is)
        tk3 = copy.deepcopy(fonts.tokens())
        tk3["themes"]["dark"]["correction"] = "#ffaaa0"
        _rows, seps3 = visual.token_contrast(tk3)
        assert any(not s["ok"] for s in seps3), seps3
        return {"token_pairs": len(rows), "dark_delta_L_rendered": round(dl, 1),
                "min_text": min(r["ratio"] for r in rows if r["kind"] == "text"),
                "min_rule": min(r["ratio"] for r in rows if r["kind"] == "rule")}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_overflow_min_size():
    """At 390 (portrait) and 1440 (wide), both themes: no overflow, no text under 11 px, and every key node
    fully visible. Fixtures that shrink text, overflow a box, push a key node off-screen or make one
    taller than the screen each fail."""
    tmp = host.make_tmp("visual-layout-")
    try:
        lesson, out, svgs = _build(tmp)
        keys = visual.required_keys(lesson)
        assert set(keys) >= {"code", "output", "note", "compare"}, keys
        m, _ob = visual.measure_svgs(out, svgs, keys)
        for s, r in m.items():
            assert not r["problems"], (s, r["problems"])
            assert r["minPx"] >= 11, (s, r["minPx"])
            assert set(r["keys"]) >= set(keys), (s, r["keys"])
            want = 390 if "-portrait-" in s else 1440
            assert r["viewport"][0] == want, (s, r["viewport"])
        port = next(s for s in svgs if "-portrait-light" in s)
        src = (out / port).read_text()
        fx = {
            "small": re.sub(r'font-size="12"( fill="[^"]+" data-chrome="provenance")', r'font-size="9"\1', src, count=1),
            "overflow": re.sub(r'(data-fact="f\.p1\.l3"[^>]*>)done<', r"\1done done done done done done<", src, count=1),
            "offscreen": src.replace('<g data-key="compare"', '<g transform="translate(260 0)" data-key="compare"', 1),
            "tall": src.replace('<g data-key="code"', '<g transform="translate(0 -1800) scale(1 3)" data-key="code"', 1),
        }
        for name, body in fx.items():
            assert body != src, f"fixture {name} did not change the figure"
            (out / f"fx-{name}.svg").write_text(body)
        mf, _ob = visual.measure_svgs(out, [f"fx-{n}.svg" for n in fx], keys)
        kinds = {n: {p["kind"] for p in mf[f"fx-{n}.svg"]["problems"]} for n in fx}
        assert "min-size" in kinds["small"], kinds["small"]
        assert "overflow" in kinds["overflow"], kinds["overflow"]
        assert kinds["offscreen"] & {"key-node-offscreen", "key-node-clipped"}, kinds["offscreen"]
        assert "key-node-taller-than-viewport" in kinds["tall"], kinds["tall"]
        return {"views": {s: r["viewport"] for s, r in m.items()}, "fixtures": {n: sorted(k) for n, k in kinds.items()}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_no_network():
    """A still that asks for a remote resource is blocked in the browser and fails the build: PNG export
    raises OutboundRequest and the network gate fails with that reason."""
    tmp = host.make_tmp("visual-network-")
    try:
        lesson, out, svgs = _build(tmp)
        s = next(x for x in svgs if "-wide-light" in x)
        body = (out / s).read_text().replace(
            "</svg>", '<image href="http://ptk-canary.invalid/pixel.png" x="0" y="0" width="1" height="1"/></svg>')
        (out / s).write_text(body)
        try:
            visual.make_pngs(out, [s], lesson.sha256())
        except errors.OutboundRequest as e:
            assert e.exit_code == errors.EXIT_GATE and e.detail["requests"], e.detail
        else:
            raise AssertionError("PNG export of a still with a remote image did not fail")
        gates = {gt["id"]: gt for gt in visual.still_gates(lesson, out, svgs)}
        net = gates["visual.still.network"]
        assert net["status"] == "failed" and net["reason"] == "OutboundRequest", net
        assert any("ptk-canary.invalid" in r["url"] for r in net["measured"]["outbound_requests"]), net
        return {"blocked": [r["url"] for r in net["measured"]["outbound_requests"]][:3]}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
