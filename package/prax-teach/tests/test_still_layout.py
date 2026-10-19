"""AC-10.1 (SPEC v1.4 WP10): every lesson's wide still is a landscape, figure-led picture with no code block and
no hash text, and a portrait variant exists.

Measured on the rendered SVG in Playwright (each SVG at its natural size):
  landscape      width >= 1.5 x height, for the viewBox, the rendered <svg> box and the 2x PNG when present.
  figure-led     the union of the hulls of the painted content of each [data-role="figure"] element covers
                 >= 50% of the canvas. Painted content is text, media and shapes with a visible fill or stroke;
                 a fill-only rect larger than 10% of the canvas is a background and does not count.
  no code block  no 3 or more monospace text runs that read as C source lines (a source line of the lesson's
                 programs, a [data-src-line] element, or a line that looks like C) stacked as consecutive lines.
  no hash text   no visible text holding "sha256"/"sha-256", a 7+ character prefix of any sha256 in lesson.json,
                 or a run of 7+ lowercase hex characters with at least one digit and one letter that is not
                 part of a 0x literal.
  portrait       <id>-portrait-light.svg and -dark.svg exist and are taller than wide.
Both themes of the wide still are measured. The portrait is checked for existence and orientation; hash text
on it is reported, not gated (AC-10.1 names the wide still).
"""
import json
import re
from pathlib import Path

import _b0

MIN_RATIO = 1.5
MIN_FIGURE = 0.50
CODE_RUN = 3
HEX_RUN = re.compile(r"(?<![0-9A-Za-z])[0-9a-f]{7,}(?![0-9A-Za-z])")
SHA_PREFIX = re.compile(r"(?<![0-9a-z])[0-9a-f]{7,64}(?![0-9a-z])")
SHA_WORD = re.compile(r"\bsha-?256\b", re.I)
SHA64 = re.compile(r"\b[0-9a-f]{64}\b")
C_LINE = re.compile(r"[;{}]\s*$|^\s*(#include|case\b.*:|default\s*:|switch\s*\(|if\s*\(|for\s*\(|while\s*\(|return\b|"
                    r"(unsigned\s+)?(int|double|char|long|float|void)\s+[\w*]|printf\s*\(|puts\s*\()")
MONO = re.compile(r"mono|courier|menlo|consolas|monospace", re.I)


def _png_size(p):
    head = Path(p).read_bytes()[16:24]
    return int.from_bytes(head[:4], "big"), int.from_bytes(head[4:], "big")


def context(data, program_texts):
    """What the hash and code rules compare against: the lesson's source lines and every sha256 it names."""
    lines = {ln.strip() for src in program_texts for ln in src.split("\n") if len(ln.strip()) >= 6}
    shas = set(SHA64.findall(json.dumps(data)))
    return {"source_lines": lines, "shas": shas}


def code_blocks(m, ctx):
    """Runs of >= CODE_RUN stacked monospace source-like lines."""
    src = []
    for it in m["items"]:
        if it["k"] != "text" or it.get("o", 1) < 0.05 or not MONO.search(it.get("ff") or ""):
            continue
        t = it["t"].strip()
        if it.get("srcline") or t in ctx["source_lines"] or C_LINE.search(t):
            src.append(it)
    src.sort(key=lambda it: (it["b"][1], it["b"][0]))
    blocks, cur = [], []
    for it in src:
        if cur:
            p = cur[-1]
            dy = it["b"][1] - p["b"][1]
            px = max(p.get("px") or 12, it.get("px") or 12)
            overlap = min(p["b"][0] + p["b"][2], it["b"][0] + it["b"][2]) - max(p["b"][0], it["b"][0])
            if 0.5 * px <= dy <= 2.4 * px and (overlap > 0 or abs(it["b"][0] - p["b"][0]) <= 200):
                cur.append(it)
                continue
            if len(cur) >= CODE_RUN:
                blocks.append(cur)
            cur = []
        cur = [it]
    if len(cur) >= CODE_RUN:
        blocks.append(cur)
    return [{"lines": len(b), "first": b[0]["t"][:60], "box_top": b[0]["b"][1]} for b in blocks]


def hash_texts(m, ctx):
    found = []
    for it in m["items"]:
        if it["k"] != "text" or it.get("o", 1) < 0.05:
            continue
        t = it["t"]
        why = None
        if SHA_WORD.search(t):
            why = "names sha256"
        elif any(sha.startswith(run) for run in SHA_PREFIX.findall(t.lower()) for sha in ctx["shas"]):
            why = "sha256 prefix from lesson.json"
        else:
            for run in HEX_RUN.findall(t):
                if re.search(r"\d", run) and re.search(r"[a-f]", run):
                    why = f"hex run {run}"
                    break
        if why:
            found.append({"text": t[:80], "why": why})
    return found


def measure_wide(m, ctx, png=None):
    if not m or m.get("error"):
        return {"problems": [{"kind": "render-failed", "error": (m or {}).get("error")}]}
    W, H = m["W"], m["H"]
    vb, rb = m.get("viewBox") or [W, H], m.get("rendered") or [0, 0, W, H]
    ratio = lambda w, h: round(w / h, 3) if h else 0.0
    ratios = {"viewBox": ratio(vb[0], vb[1]), "rendered": ratio(rb[2], rb[3])}
    if png and Path(png).is_file():
        ratios["png"] = ratio(*_png_size(png))
    fig, hulls = _b0.group_coverage(m, "fig")
    blocks = code_blocks(m, ctx)
    hashes = hash_texts(m, ctx)
    problems = []
    if min(ratios.values()) < MIN_RATIO:
        problems.append({"kind": "not-landscape", "ratios": ratios, "size": [round(vb[0]), round(vb[1])]})
    if fig < MIN_FIGURE:
        problems.append({"kind": "figure-coverage", "coverage": fig, "figures": len(m["figures"])})
    if blocks:
        problems.append({"kind": "code-block", "blocks": blocks})
    if hashes:
        problems.append({"kind": "hash-text", "texts": hashes[:5]})
    return {"size": [round(vb[0]), round(vb[1])], "ratios": ratios, "figure_coverage": fig, "figure_hulls": hulls,
            "figure_elements": len(m["figures"]), "rc1_panel_coverage_info": _b0.panel_coverage(m),
            "code_blocks": blocks, "hash_texts": hashes, "problems": problems}


def evaluate(still_dir, lesson_id, ctx):
    """All AC-10.1 measures for one still folder. Returns (result, problems)."""
    still_dir = Path(still_dir)
    wide = [still_dir / f"{lesson_id}-wide-{th}.svg" for th in ("light", "dark")]
    port = [still_dir / f"{lesson_id}-portrait-{th}.svg" for th in ("light", "dark")]
    problems, out = [], {"wide": {}, "portrait": {}}
    present = [p for p in wide + port if p.is_file()]
    ext, outbound = _b0.extract_svgs(present, "still") if present else ({}, [])
    for p in wide:
        if not p.is_file():
            problems.append({"kind": "wide-missing", "svg": p.name})
            continue
        r = measure_wide(ext.get(str(p)), ctx, p.with_suffix(".png"))
        out["wide"][p.name] = r
        problems += [{**pr, "svg": p.name} for pr in r["problems"]]
    for p in port:
        if not p.is_file():
            problems.append({"kind": "portrait-missing", "svg": p.name})
            continue
        m = ext.get(str(p)) or {}
        vb = m.get("viewBox") or list(_b0.svg_size(p))
        info = {"size": [round(vb[0]), round(vb[1])], "hash_texts_info": hash_texts(m, ctx) if m.get("items") else []}
        out["portrait"][p.name] = info
        if vb[1] <= vb[0]:
            problems.append({"kind": "portrait-not-portrait", "svg": p.name, "size": info["size"]})
    if outbound:
        problems.append({"kind": "outbound-request", "requests": outbound[:5]})
    return out, problems


def _summary(out):
    return {n: {"size": r.get("size"), "ratio": (r.get("ratios") or {}).get("viewBox"),
                "figure": r.get("figure_coverage"), "panel_info": r.get("rc1_panel_coverage_info"),
                "code_blocks": len(r.get("code_blocks") or []), "hash_texts": len(r.get("hash_texts") or [])}
            for n, r in out["wide"].items()}


# ---------------------------------------------------------------- fixtures: the check can pass and can fail

FIX_CTX = {"source_lines": {"int main(void) {", "double z = t1 + t2 + b;", "printf(\"a = %g\\n\", a);"},
           "shas": {"38ae3b01ef4a" + "0" * 52, "1234567890" + "a" * 54}}


def test_fixture_good_still_passes():
    """A landscape, figure-led fixture still with a portrait variant passes every AC-10.1 measure."""
    out, problems = evaluate(_b0.FIXTURES / "still-pass", "fx", FIX_CTX)
    assert not problems, problems
    return _summary(out)


def test_fixture_bad_still_fails():
    """A tall poster fixture with a small figure, a code block and a hash footer, and no portrait, fails each
    measure for the right reason."""
    out, problems = evaluate(_b0.FIXTURES / "still-fail", "fx", FIX_CTX)
    kinds = {p["kind"] for p in problems}
    want = {"not-landscape", "figure-coverage", "code-block", "hash-text", "portrait-missing"}
    assert want <= kinds, (sorted(kinds), problems)
    return {"kinds": sorted(kinds), **_summary(out)}


def test_hash_rule_spares_values():
    """0x literals and long decimal values are not hashes; a sha prefix and a bare hex digest are."""
    m = {"items": [{"k": "text", "t": t, "o": 1} for t in
                   ("0x4050800000000000", "4294967295", "01000010", "stdout 5f2a0b8378e7", "run 38ae3b0",
                    "sha256 of the run", "deadbeefcafe", "id 1234567", "n 7654321")]}
    got = {h["text"] for h in hash_texts(m, FIX_CTX)}
    assert got == {"stdout 5f2a0b8378e7", "run 38ae3b0", "sha256 of the run", "id 1234567"}, got
    return sorted(got)


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "still")
    lesson = _b0.load(slug)
    texts = [lesson.program_source(p["id"]) for p in lesson.data["programs"]]
    out, problems = evaluate(b / "still", lesson.id, context(lesson.data, texts))
    rec = _b0.record(f"ac10.1-{slug}", {"lesson": slug, "result": out, "problems": problems})
    assert not problems, json.dumps({"summary": _summary(out), "problems": [p["kind"] + ":" + p.get("svg", "")
                                                                            for p in problems], "record": rec})
    return {"summary": _summary(out), "record": rec}


_b0.lesson_tests(globals(), "AC-10.1 still layout", _lesson)
