"""AC-10.1 (SPEC v1.4 WP10): every lesson's wide still is a landscape, figure-led picture with no code block and
no hash text, a portrait variant carries the same figure, and provenance lives off the picture.

Measured on the rendered SVG in Playwright (each SVG at its natural size):
  landscape      width >= 1.5 x height, for the viewBox, the rendered <svg> box and the 2x PNG when present.
  figure-led     what the [data-role="figure"] elements actually paint covers >= 50% of the canvas. The page is
                 shot with the figure shown and with it hidden; 20 px cells where any pixel changes by more than
                 12 levels in a channel are counted after a one-cell dilation. Marks drawn at under 0.3 effective
                 opacity are hidden in both shots, so faint dots, ground-coloured strokes or fills and empty images
                 count for nothing.
  no code block  no 3 or more monospace text lines that read as C source lines (a source line of the lesson's
                 programs, a [data-src-line] element, or a line that looks like C) stacked as consecutive lines.
                 Each drawn line is measured on its own, including tspans inside one <text>.
  no hash text   no visible text naming "sha" or "sha256" (any case), holding a 7+ character prefix of any sha256
                 in lesson.json, or holding a run of 7+ hex characters (any case) with at least one digit and one
                 letter that is not part of a 0x literal.
  portrait       <id>-portrait-light.svg and -dark.svg exist, are taller than wide, and their figure paints >= 25%
                 of the canvas and draws the same set of facts as the wide figure.
  provenance     each program's stdout sha256 prefix (7 characters) is in the SVG's <title>, <desc>, <metadata> or
                 data-provenance, or in the still page (still/index.html: alt text, caption or meta).
Both themes are measured. Hash text on the portrait is gated too.
"""
import json
import re
from pathlib import Path

import _b0

MIN_RATIO = 1.5
MIN_FIGURE = 0.50
MIN_PORTRAIT_FIGURE = 0.25
CODE_RUN = 3
HEX_RUN = re.compile(r"(?<![0-9a-z])[0-9a-f]{7,}(?![0-9a-z])")
SHA_PREFIX = re.compile(r"(?<![0-9a-z])[0-9a-f]{7,64}(?![0-9a-z])")
SHA_WORD = re.compile(r"\bsha(?:-?\d+)?\b", re.I)
SHA64 = re.compile(r"\b[0-9a-f]{64}\b")
C_LINE = re.compile(r"[;{}]\s*$|^\s*(#include|case\b.*:|default\s*:|switch\s*\(|if\s*\(|for\s*\(|while\s*\(|return\b|"
                    r"(unsigned\s+)?(int|double|char|long|float|void)\s+[\w*]|printf\s*\(|puts\s*\()")
MONO = re.compile(r"mono|courier|menlo|consolas|monospace", re.I)


def context(data, program_texts):
    """What the hash, code and provenance rules compare against: the lesson's source lines, every sha256 it names,
    and each program's stdout sha256 (the provenance that must live off the picture)."""
    lines = {ln.strip() for src in program_texts for ln in src.split("\n") if len(ln.strip()) >= 6}
    shas = set(SHA64.findall(json.dumps(data)))
    prov = sorted({f["source"]["stdout_sha256"] for f in data.get("facts", [])
                   if (f.get("source") or {}).get("stdout_sha256")})
    return {"source_lines": lines, "shas": shas, "provenance": prov}


def code_blocks(m, ctx):
    """Runs of >= CODE_RUN stacked monospace source-like lines (each drawn line is its own item)."""
    src = []
    for it in m["items"]:
        if it["k"] != "text" or it.get("o", 1) < _b0.MIN_OPACITY or not MONO.search(it.get("ff") or ""):
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
        if it["k"] != "text" or it.get("o", 1) < _b0.MIN_OPACITY:
            continue
        t, low = it["t"], it["t"].lower()
        why = None
        if SHA_WORD.search(t):
            why = "names sha"
        elif any(sha.startswith(run) for run in SHA_PREFIX.findall(low) for sha in ctx["shas"]):
            why = "sha256 prefix from lesson.json"
        else:
            for run in HEX_RUN.findall(low):
                if re.search(r"\d", run) and re.search(r"[a-f]", run):
                    why = f"hex run {run}"
                    break
        if why:
            found.append({"text": t[:80], "why": why})
    return found


def figure_facts(m):
    return sorted({it["d"]["fact"] for it in m["items"] if it["k"] == "text" and it.get("fig") is not None
                   and (it.get("d") or {}).get("fact") and it.get("o", 1) >= _b0.MIN_OPACITY})


def measure_wide(m, ctx, png=None):
    if not m or m.get("error"):
        return {"problems": [{"kind": "render-failed", "error": (m or {}).get("error")}]}
    W, H = m["W"], m["H"]
    vb, rb = m.get("viewBox") or [W, H], m.get("rendered") or [0, 0, W, H]
    ratio = lambda w, h: round(w / h, 3) if h else 0.0
    ratios = {"viewBox": ratio(vb[0], vb[1]), "rendered": ratio(rb[2], rb[3])}
    if png and Path(png).is_file():
        ratios["png"] = ratio(*_b0.png_size(png))
    fig = m["diff"][_b0.FIG_SEL]
    blocks = code_blocks(m, ctx)
    hashes = hash_texts(m, ctx)
    problems = []
    if min(ratios.values()) < MIN_RATIO:
        problems.append({"kind": "not-landscape", "ratios": ratios, "size": [round(vb[0]), round(vb[1])]})
    if fig["coverage"] < MIN_FIGURE:
        problems.append({"kind": "figure-coverage", "coverage": fig["coverage"], "figures": len(m["figures"])})
    if blocks:
        problems.append({"kind": "code-block", "blocks": blocks})
    if hashes:
        problems.append({"kind": "hash-text", "texts": hashes[:5]})
    return {"size": [round(vb[0]), round(vb[1])], "ratios": ratios, "figure_coverage": fig["coverage"],
            "figure_painted_box": fig["painted_box"], "figure_elements": len(m["figures"]),
            "figure_facts": figure_facts(m), "rc1_panel_coverage_info": _b0.panel_coverage(m),
            "code_blocks": blocks, "hash_texts": hashes, "problems": problems}


def provenance_problems(still_dir, ext, ctx):
    """Each stdout sha256 prefix must be findable off the picture: SVG title/desc/metadata or the still page."""
    page = still_dir / "index.html"
    html = re.sub(r"<!--.*?-->", "", page.read_text(), flags=re.S).lower() if page.is_file() else ""
    meta = " ".join((m or {}).get("meta", "") for m in ext.values()).lower()
    missing = [sha[:12] for sha in ctx.get("provenance", []) if sha[:7] not in html and sha[:7] not in meta]
    return [{"kind": "provenance-not-in-metadata", "missing": missing}] if missing else []


def evaluate(still_dir, lesson_id, ctx):
    """All AC-10.1 measures for one still folder. Returns (result, problems)."""
    still_dir = Path(still_dir)
    wide = [still_dir / f"{lesson_id}-wide-{th}.svg" for th in ("light", "dark")]
    port = [still_dir / f"{lesson_id}-portrait-{th}.svg" for th in ("light", "dark")]
    problems, out = [], {"wide": {}, "portrait": {}}
    present = [p for p in wide + port if p.is_file()]
    ext, outbound = _b0.extract_svgs(present, "still", diffs=(_b0.FIG_SEL,)) if present else ({}, [])
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
        if m.get("error") or not m.get("items") and not m.get("diff"):
            problems.append({"kind": "render-failed", "svg": p.name, "error": m.get("error")})
            continue
        vb = m.get("viewBox") or list(_b0.svg_size(p))
        fig = m["diff"][_b0.FIG_SEL]
        facts = figure_facts(m)
        twin = out["wide"].get(p.name.replace("-portrait-", "-wide-"), {})
        info = {"size": [round(vb[0]), round(vb[1])], "figure_coverage": fig["coverage"], "figure_facts": facts,
                "hash_texts": hash_texts(m, ctx)}
        out["portrait"][p.name] = info
        if vb[1] <= vb[0]:
            problems.append({"kind": "portrait-not-portrait", "svg": p.name, "size": info["size"]})
        if fig["coverage"] < MIN_PORTRAIT_FIGURE:
            problems.append({"kind": "portrait-figure-empty", "svg": p.name, "coverage": fig["coverage"]})
        if twin.get("figure_facts") is not None and facts != twin["figure_facts"]:
            problems.append({"kind": "portrait-figure-differs", "svg": p.name, "portrait": facts, "wide": twin["figure_facts"]})
        if info["hash_texts"]:
            problems.append({"kind": "hash-text", "svg": p.name, "texts": info["hash_texts"][:3]})
    problems += provenance_problems(still_dir, ext, ctx)
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
           "shas": {"38ae3b01ef4a" + "0" * 52, "1234567890" + "a" * 54},
           "provenance": ["38ae3b01ef4a" + "0" * 52]}


def test_fixture_good_still_passes():
    """A landscape still whose figure is a real drawing (three gridded panels with values), a portrait with the
    same figure, and provenance in <desc>, passes every AC-10.1 measure."""
    out, problems = evaluate(_b0.FIXTURES / "still-pass", "fx", FIX_CTX)
    assert not problems, problems
    return _summary(out)


def test_fixture_bad_still_fails():
    """A tall poster fixture with a small figure, a code block and a hash footer, and no portrait, fails each
    measure for the right reason."""
    out, problems = evaluate(_b0.FIXTURES / "still-fail", "fx", FIX_CTX)
    kinds = {p["kind"] for p in problems}
    want = {"not-landscape", "figure-coverage", "code-block", "hash-text", "portrait-missing", "provenance-not-in-metadata"}
    assert want <= kinds, (sorted(kinds), problems)
    return {"kinds": sorted(kinds), **_summary(out)}


ADVERSARIAL = {  # the independent review's crafted inputs (reviews/b0-measures.md, "Review findings")
    "g1": {"figure-coverage"},                              # two corner dots at 0.06 opacity
    "g2": {"figure-coverage"},                              # a full-canvas stroke in the ground colour
    "g3": {"figure-coverage"},                              # a full-canvas path filled with the ground colour
    "g4": {"figure-coverage"},                              # a full-canvas <image> with no picture
    "g5": {"figure-coverage", "code-block", "hash-text"},   # corner dots, code as tspans, "SHA 38AE3B01EF4A"
}


def test_fixture_adversarial_stills_fail():
    """Each crafted still from the independent review fails for the reason it was built to slip past."""
    got = {}
    for name, want in ADVERSARIAL.items():
        out, problems = evaluate(_b0.FIXTURES / "adversarial" / f"still-{name}", "fx", FIX_CTX)
        kinds = {p["kind"] for p in problems}
        assert want <= kinds, (name, sorted(kinds), _summary(out))
        got[name] = {"kinds": sorted(kinds), "figure": [r.get("figure_coverage") for r in out["wide"].values()]}
    return got


def test_hash_rule_spares_values():
    """0x literals and long decimal values are not hashes; a sha prefix and a bare hex digest are, in any case."""
    m = {"items": [{"k": "text", "t": t, "o": 1} for t in
                   ("0x4050800000000000", "0xC8", "4294967295", "01000010", "stdout 5f2a0b8378e7", "run 38ae3b0",
                    "sha256 of the run", "deadbeefcafe", "id 1234567", "n 7654321", "stdout SHA 38AE3B01EF4A",
                    "digest 5F2A0B8378E7")]}
    got = {h["text"] for h in hash_texts(m, FIX_CTX)}
    assert got == {"stdout 5f2a0b8378e7", "run 38ae3b0", "sha256 of the run", "id 1234567", "stdout SHA 38AE3B01EF4A",
                   "digest 5F2A0B8378E7"}, got
    return sorted(got)


# ---------------------------------------------------------------- the built lessons

def _lesson(slug):
    b = _b0.need(slug, "still")
    lesson = _b0.load(slug)
    texts = [lesson.program_source(p["id"]) for p in lesson.data["programs"]]
    out, problems = evaluate(b / "still", lesson.id, context(lesson.data, texts))
    rec = _b0.record(f"ac10.1-{slug}", {"lesson": slug, "result": out, "problems": problems})
    kinds = {}
    for p in problems:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    assert not problems, json.dumps({"problems": kinds, "summary": _summary(out), "record": rec})
    return {"summary": _summary(out), "record": rec}


_b0.lesson_tests(globals(), "AC-10.1 still layout", _lesson)
